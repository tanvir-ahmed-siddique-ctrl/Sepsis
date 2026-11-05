import json
import base64
import binascii
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.accounts import AccountStore
from app.auth import CLINICAL_ROLES, ROLES, Actor, create_access_token, require_roles
from app.core.config import settings
from app.records import utc_now
from app.schemas import (
    AdminPasswordResetRequest,
    LocalLoginRequest,
    LocalUserRequest,
    LocalUserUpdateRequest,
    PasswordChangeRequest,
    PinChangeRequest,
    PinLoginRequest,
    TotpConfirmRequest,
)
from app.services.engine import get_engine

router = APIRouter(tags=["auth"], prefix="/auth")
HUMAN_ROLES = (*CLINICAL_ROLES, "operator")
AUTHENTICATED = require_roles(*HUMAN_ROLES, "integration", allow_temporary_password=True)
CLINICAL = require_roles(*CLINICAL_ROLES)
HUMAN = require_roles(*HUMAN_ROLES)
PASSWORD_CHANGE = require_roles(*HUMAN_ROLES, allow_temporary_password=True)
ADMIN = require_roles("admin")


class StaffProfileUpdate(BaseModel):
    alert_notifications: bool = True
    sound: bool = False
    quiet_when_off_shift: bool = True
    escalation_minutes: int = Field(default=15, ge=5, le=120)


class BrowserDeviceRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=128)
    label: str = Field(min_length=1, max_length=100)
    user_agent: str | None = Field(default=None, max_length=500)
    notification_permission: str = Field(pattern="^(default|granted|denied|unsupported)$")


class ProfileAvatarRequest(BaseModel):
    data_url: str = Field(min_length=32, max_length=350_000)


def _validate_avatar(data_url: str) -> str:
    try:
        header, encoded = data_url.split(",", 1)
        mime = header.removeprefix("data:").removesuffix(";base64")
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise HTTPException(status_code=422, detail="Avatar must be a valid base64 image") from error
    signatures = {
        "image/png": raw.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": raw.startswith(b"\xff\xd8\xff"),
        "image/webp": len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP",
    }
    if mime not in signatures or not signatures[mime]:
        raise HTTPException(status_code=422, detail="Use a valid PNG, JPEG or WebP image")
    if len(raw) > 256 * 1024:
        raise HTTPException(status_code=413, detail="Avatar must be 256 KB or smaller")
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def _accounts() -> AccountStore:
    return AccountStore(get_engine().records)


def _account_error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, PermissionError):
        return HTTPException(status_code=401, detail=str(error))
    return HTTPException(status_code=422, detail=str(error))


def _protect_last_admin(user_id: str, *, disabling: bool = False, next_role: str | None = None) -> None:
    store = _accounts()
    row = store.get(user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    removes_active_admin = (
        row["role"] == "admin"
        and not bool(row["disabled"])
        and (disabling or (next_role is not None and next_role != "admin"))
    )
    if removes_active_admin and store.active_admin_count() <= 1:
        raise HTTPException(status_code=409, detail="The last active administrator cannot be removed")


def _validate_units(units: list[str] | None) -> None:
    if not units:
        return
    known = set(get_engine().units)
    unknown = sorted(set(units) - known)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown care units: {', '.join(unknown)}")


def _token_response(row: dict, auth_mode: str, minutes: int | None = None) -> dict:
    units = json.loads(row["units"]) if row.get("units") else None
    token = create_access_token(row["user_id"], row["role"], units, minutes=minutes, auth_mode=auth_mode)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_seconds": (minutes or settings.access_token_minutes) * 60,
        "role": row["role"],
        "units": units,
        "must_change_password": bool(row["must_change_password"]),
    }


@router.post("/demo-token")
def demo_token(
    user_id: str = Query("demo-clinician", min_length=1, max_length=128),
    role: str = Query("clinician"),
    units: str | None = Query(None, max_length=500, description="Comma-separated unit scope"),
):
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Not found")
    if role not in ROLES:
        raise HTTPException(status_code=422, detail=f"Role must be one of {sorted(ROLES)}")
    scope = [unit.strip() for unit in units.split(",") if unit.strip()] if units else None
    return {
        "access_token": create_access_token(user_id, role, scope),
        "token_type": "bearer",
        "expires_in_seconds": settings.access_token_minutes * 60,
        "role": role,
        "units": scope,
    }


@router.post("/login")
def local_login(body: LocalLoginRequest):
    if settings.auth_mode != "local":
        raise HTTPException(status_code=404, detail="Local login is not enabled")
    store = _accounts()
    try:
        row = store.authenticate_password(body.user_id, body.password)
        store.verify_totp(row, body.totp_code or "")
    except (PermissionError, ValueError) as error:
        raise _account_error(error) from error
    engine = get_engine()
    engine._log("local_login_succeeded", {"actor": row["user_id"], "actor_role": row["role"], "method": "password"})
    return _token_response(row, "password")


@router.post("/pin-login")
def pin_login(body: PinLoginRequest):
    if settings.auth_mode != "local":
        raise HTTPException(status_code=404, detail="Local login is not enabled")
    store = _accounts()
    try:
        row = store.authenticate_pin(body.user_id, body.pin)
        store.verify_totp(row, body.totp_code or "")
    except (PermissionError, ValueError) as error:
        raise _account_error(error) from error
    get_engine()._log("local_login_succeeded", {"actor": row["user_id"], "actor_role": row["role"], "method": "pin"})
    return _token_response(row, "pin", minutes=15)


@router.post("/logout")
def logout(actor: Actor = Depends(AUTHENTICATED)):
    if actor.jti:
        _accounts().revoke_jti(actor.jti, actor.user_id, "logout")
    get_engine()._log("session_logged_out", {"actor": actor.user_id, "actor_role": actor.role})
    return {"logged_out": True}


@router.get("/me")
def whoami(actor: Actor = Depends(AUTHENTICATED)):
    state = get_engine().site.state
    return {
        "user_id": actor.user_id,
        "role": actor.role,
        "roles": sorted(actor.roles),
        "units": list(actor.units) if actor.units is not None else None,
        "auth_mode": actor.auth_mode,
        "demo_mode": settings.demo_mode,
        "site_mode": state.effective_mode,
        "interruptive_alerts_enabled": state.interruptive_alerts_enabled,
        "bedside_blinded": state.blinded,
        "display_name": actor.display_name,
        "must_change_password": actor.must_change_password,
        "totp_enabled": actor.totp_enabled,
    }


def _profile_key(user_id: str) -> str:
    return f"staff:{user_id.lower()}"[:64]


def _staff_profile(actor: Actor) -> dict:
    engine = get_engine()
    stored = engine.records.load_config(_profile_key(actor.user_id)) or {}
    defaults = {
        "user_id": actor.user_id,
        "display_name": actor.display_name or actor.user_id,
        "role": actor.role,
        "units": list(actor.units) if actor.units is not None else None,
        "preferences": {
            "alert_notifications": True,
            "sound": False,
            "quiet_when_off_shift": True,
            "escalation_minutes": settings.alert_review_sla_minutes,
        },
        "devices": [],
    }
    defaults.update(stored)
    from app import shift_roster

    roster = shift_roster.load(engine)
    defaults["current_shift"] = shift_roster.current_staff(roster)
    defaults["delivery_history"] = [
        {
            "event": event["event"],
            "alert_id": event.get("alert_id"),
            "patient_id": event.get("patient_id"),
            "at": event.get("at") or event.get("source_time"),
            "reason": event.get("reason"),
        }
        for event in reversed(engine.audit)
        if event.get("actor") == actor.user_id
        and event.get("event") in {"alert_acknowledged", "alert_escalated", "alert_dismissed", "alert_snoozed"}
    ][:50]
    defaults["delivery_capability"] = {
        "installed_pwa": "client-reported",
        "browser_notifications": True,
        "closed_app_web_push": False,
        "note": (
            "Browser notifications are delivered while the PWA is running/backgrounded. "
            "Closed-app Web Push needs a hospital-approved VAPID push gateway and is not claimed in this build."
        ),
    }
    return defaults


@router.get("/profile")
def staff_profile(actor: Actor = Depends(HUMAN)):
    return _staff_profile(actor)


@router.put("/profile/avatar")
def update_profile_avatar(body: ProfileAvatarRequest, actor: Actor = Depends(HUMAN)):
    engine = get_engine()
    profile = _staff_profile(actor)
    profile["avatar_data_url"] = _validate_avatar(body.data_url)
    for key in ("current_shift", "delivery_history", "delivery_capability"):
        profile.pop(key, None)
    engine.records.save_config(_profile_key(actor.user_id), profile, actor.user_id)
    engine._log("staff_profile_avatar_updated", {"actor": actor.user_id, "actor_role": actor.role})
    return _staff_profile(actor)


@router.delete("/profile/avatar")
def delete_profile_avatar(actor: Actor = Depends(HUMAN)):
    engine = get_engine()
    profile = _staff_profile(actor)
    profile.pop("avatar_data_url", None)
    for key in ("current_shift", "delivery_history", "delivery_capability"):
        profile.pop(key, None)
    engine.records.save_config(_profile_key(actor.user_id), profile, actor.user_id)
    engine._log("staff_profile_avatar_removed", {"actor": actor.user_id, "actor_role": actor.role})
    return _staff_profile(actor)


@router.put("/profile/preferences")
def update_staff_preferences(body: StaffProfileUpdate, actor: Actor = Depends(HUMAN)):
    engine = get_engine()
    profile = _staff_profile(actor)
    profile["preferences"] = body.model_dump()
    # Derived fields are rebuilt on read and are not persisted.
    for key in ("current_shift", "delivery_history", "delivery_capability"):
        profile.pop(key, None)
    engine.records.save_config(_profile_key(actor.user_id), profile, actor.user_id)
    engine._log("staff_alert_preferences_updated", {"actor": actor.user_id, "actor_role": actor.role})
    return _staff_profile(actor)


@router.post("/profile/devices")
def enroll_browser_device(body: BrowserDeviceRequest, actor: Actor = Depends(HUMAN)):
    engine = get_engine()
    profile = _staff_profile(actor)
    devices = list(profile.get("devices") or [])
    row = {
        **body.model_dump(),
        "enrolled_at": utc_now(),
        "last_seen_at": utc_now(),
        "kind": "pwa-browser",
    }
    devices = [device for device in devices if device.get("device_id") != body.device_id]
    devices.append(row)
    profile["devices"] = devices[-10:]
    for key in ("current_shift", "delivery_history", "delivery_capability"):
        profile.pop(key, None)
    engine.records.save_config(_profile_key(actor.user_id), profile, actor.user_id)
    engine._log("staff_device_enrolled", {
        "actor": actor.user_id,
        "actor_role": actor.role,
        "device_id": body.device_id,
        "notification_permission": body.notification_permission,
    })
    return _staff_profile(actor)


@router.delete("/profile/devices/{device_id}")
def remove_browser_device(device_id: str, actor: Actor = Depends(HUMAN)):
    engine = get_engine()
    profile = _staff_profile(actor)
    profile["devices"] = [device for device in profile.get("devices") or [] if device.get("device_id") != device_id]
    for key in ("current_shift", "delivery_history", "delivery_capability"):
        profile.pop(key, None)
    engine.records.save_config(_profile_key(actor.user_id), profile, actor.user_id)
    engine._log("staff_device_removed", {"actor": actor.user_id, "actor_role": actor.role, "device_id": device_id})
    return _staff_profile(actor)


@router.post("/password")
def change_password(body: PasswordChangeRequest, actor: Actor = Depends(PASSWORD_CHANGE)):
    try:
        _accounts().set_password(actor.user_id, body.new_password, current=body.current_password)
    except (PermissionError, ValueError) as error:
        raise _account_error(error) from error
    get_engine()._log("local_password_changed", {"actor": actor.user_id, "actor_role": actor.role})
    return {"changed": True, "sign_in_again": True}


@router.post("/pin")
def set_pin(body: PinChangeRequest, actor: Actor = Depends(CLINICAL)):
    try:
        _accounts().set_pin(actor.user_id, body.pin)
    except (PermissionError, ValueError) as error:
        raise _account_error(error) from error
    get_engine()._log("ward_pin_changed", {"actor": actor.user_id, "actor_role": actor.role})
    return {"changed": True, "sign_in_again": True}


@router.post("/totp/begin")
def begin_totp(actor: Actor = Depends(HUMAN)):
    try:
        secret = _accounts().begin_totp(actor.user_id)
    except (PermissionError, ValueError) as error:
        raise _account_error(error) from error
    issuer = quote(settings.app_name)
    account = quote(f"{settings.site_id}:{actor.user_id}")
    return {
        "secret": secret,
        "otpauth_uri": f"otpauth://totp/{account}?secret={secret}&issuer={issuer}&period=30&digits=6",
        "note": "The secret is shown only during enrolment. Confirm one code before it becomes active.",
    }


@router.post("/totp/confirm")
def confirm_totp(body: TotpConfirmRequest, actor: Actor = Depends(HUMAN)):
    try:
        _accounts().confirm_totp(actor.user_id, body.code)
    except (PermissionError, ValueError) as error:
        raise _account_error(error) from error
    get_engine()._log("totp_enabled", {"actor": actor.user_id, "actor_role": actor.role})
    return {"enabled": True}


@router.get("/users")
def list_users(_: Actor = Depends(ADMIN)):
    return {"users": _accounts().list_users()}


@router.post("/users")
def create_user(body: LocalUserRequest, actor: Actor = Depends(ADMIN)):
    _validate_units(body.units)
    try:
        user = _accounts().create(
            body.user_id,
            body.display_name,
            body.role,
            body.password,
            units=body.units,
            actor_id=actor.user_id,
        )
    except ValueError as error:
        raise _account_error(error) from error
    get_engine()._log("local_user_created", {
        "actor": actor.user_id,
        "actor_role": actor.role,
        "user_id": user["user_id"],
        "role": user["role"],
        "units": user["units"],
    })
    return user


@router.patch("/users/{user_id}")
def update_user(user_id: str, body: LocalUserUpdateRequest, actor: Actor = Depends(ADMIN)):
    if user_id.lower() == actor.user_id.lower() and body.disabled:
        raise HTTPException(status_code=409, detail="An administrator cannot disable their own account")
    changes = body.model_dump(exclude_unset=True)
    if "units" in changes:
        _validate_units(changes["units"])
    if "units" in changes:
        changes["units"] = json.dumps(changes["units"]) if changes["units"] else None
    if "disabled" in changes:
        changes["disabled"] = int(changes["disabled"])
    try:
        with get_engine().lock:
            _protect_last_admin(
                user_id,
                disabling=changes.get("disabled") == 1,
                next_role=changes.get("role"),
            )
            user = _accounts().update(user_id, **changes)
            if {"role", "units", "disabled"} & changes.keys():
                _accounts().revoke_user(user_id, "account_access_changed")
    except (LookupError, ValueError) as error:
        raise _account_error(error) from error
    get_engine()._log("local_user_updated", {
        "actor": actor.user_id,
        "actor_role": actor.role,
        "user_id": user_id,
        "fields": sorted(changes),
    })
    return user


@router.post("/users/{user_id}/reset-factors")
def reset_factors(user_id: str, actor: Actor = Depends(ADMIN)):
    try:
        user = _accounts().reset_factors(user_id)
    except (LookupError, PermissionError, ValueError) as error:
        raise _account_error(error) from error
    get_engine()._log("local_factors_reset", {
        "actor": actor.user_id,
        "actor_role": actor.role,
        "user_id": user_id,
    })
    return user


@router.delete("/users/{user_id}")
def delete_user(user_id: str, actor: Actor = Depends(ADMIN)):
    if user_id.lower() == actor.user_id.lower():
        raise HTTPException(status_code=409, detail="An administrator cannot delete their own account")
    try:
        with get_engine().lock:
            _protect_last_admin(user_id, disabling=True)
            _accounts().delete(user_id)
    except LookupError as error:
        raise _account_error(error) from error
    get_engine()._log("local_user_deleted", {
        "actor": actor.user_id,
        "actor_role": actor.role,
        "user_id": user_id,
    })
    return {"deleted": True, "user_id": user_id, "audit_identity_retained": True}


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: str, body: AdminPasswordResetRequest, actor: Actor = Depends(ADMIN)):
    try:
        _accounts().set_password(user_id, body.new_password, admin=True)
        _accounts().reset_factors(user_id)
        _accounts().update(user_id, must_change_password=1)
    except (LookupError, PermissionError, ValueError) as error:
        raise _account_error(error) from error
    get_engine()._log("local_password_reset", {
        "actor": actor.user_id,
        "actor_role": actor.role,
        "user_id": user_id,
    })
    return {"reset": True, "must_change_password": True}
