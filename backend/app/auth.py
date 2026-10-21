"""Authentication and role/unit/scope guards.

Three credential types are accepted, in this order:

* ``Authorization: Bearer`` — locally issued HS256 tokens (``AUTH_MODE=local``, with
  rotation through ``JWT_PREVIOUS_SECRETS``) or hospital OIDC access tokens validated
  against the identity provider's JWKS (``AUTH_MODE=oidc``).
* ``X-Integration-Key: <key_id>.<secret>`` — hashed, scoped connector credentials.
* ``X-Demo-User`` / ``X-Demo-Role`` — only when ``DEMO_MODE=true``.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import jwt
from fastapi import Header, HTTPException, status

from app.accounts import AccountStore
from app.core.config import DEFAULT_EXPORT_SALT, DEFAULT_JWT_SECRET, settings

ROLES = {"clinician", "nurse", "admin", "operator", "integration"}
ROLE_PRIORITY = ("admin", "clinician", "nurse", "operator", "integration")
# Platform operators see deployment metadata only; no route that returns
# patient-level data may list "operator".
CLINICAL_ROLES = ("clinician", "nurse", "admin")
PHYSICIAN_ROLES = ("clinician", "admin")
INGEST_SCOPES = {"ingest:json", "ingest:fhir", "ingest:hl7v2"}


@dataclass(frozen=True)
class Actor:
    user_id: str
    role: str
    auth_mode: str
    roles: frozenset[str] = frozenset()
    units: tuple[str, ...] | None = None
    scopes: tuple[str, ...] | None = None
    jti: str | None = None
    must_change_password: bool = False
    totp_enabled: bool = False
    display_name: str | None = None

    def __post_init__(self) -> None:
        if not self.roles:
            object.__setattr__(self, "roles", frozenset({self.role}))

    def can_access_unit(self, unit_id: str) -> bool:
        return self.units is None or unit_id in self.units

    def has_scope(self, scope: str) -> bool:
        return self.scopes is None or scope in self.scopes


def create_access_token(
    user_id: str,
    role: str,
    units: list[str] | None = None,
    *,
    minutes: int | None = None,
    auth_mode: str = "jwt",
) -> str:
    if role not in ROLES:
        raise ValueError(f"Unknown role: {role}")
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "jti": secrets.token_urlsafe(16),
        "amr": auth_mode,
        "iat_ms": now.timestamp(),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(minutes=minutes or settings.access_token_minutes),
    }
    if units:
        payload["units"] = list(units)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_local(token: str) -> Actor:
    last_error: Exception | None = None
    for secret in [settings.jwt_secret, *settings.jwt_previous_secrets]:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[settings.jwt_algorithm],
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
                options={"require": ["sub", "role", "exp", "iat"]},
            )
            break
        except jwt.InvalidSignatureError as error:
            last_error = error
        except jwt.PyJWTError as error:
            raise _unauthorized("Invalid or expired access token") from error
    else:
        raise _unauthorized("Invalid or expired access token") from last_error
    role = str(payload["role"])
    if role not in ROLES:
        raise HTTPException(status_code=403, detail="Token has an unsupported role")
    units = payload.get("units")
    user_id = str(payload["sub"])
    issued = datetime.fromtimestamp(float(payload.get("iat_ms", payload["iat"])), tz=timezone.utc)
    jti = payload.get("jti")
    auth_mode = str(payload.get("amr") or "jwt")
    extra: dict[str, Any] = {}
    if auth_mode in {"password", "pin"} or jti:
        store = _account_store()
        if store is not None and jti and store.is_revoked(str(jti), user_id, issued):
            raise _unauthorized("Session was revoked")
        row = store.get(user_id) if store is not None else None
        if row is not None:
            if row["disabled"]:
                raise HTTPException(status_code=403, detail="Account is disabled")
            role = str(row["role"])
            extra = {
                "must_change_password": bool(row["must_change_password"]),
                "totp_enabled": bool(row["totp_secret"]) and not str(row["totp_secret"]).startswith("pending:"),
                "display_name": row["display_name"],
            }
            if row["units"]:
                import json

                units = json.loads(row["units"])
    return Actor(
        user_id=user_id,
        role=role,
        auth_mode=auth_mode,
        units=tuple(units) if units else None,
        jti=str(jti) if jti else None,
        **extra,
    )


_jwks_client: Any = None


def _get_jwks_client() -> Any:
    global _jwks_client
    if _jwks_client is None:
        if not settings.oidc_jwks_url:
            raise _unauthorized("OIDC is not configured")
        _jwks_client = jwt.PyJWKClient(settings.oidc_jwks_url, cache_keys=True, lifespan=3600)
    return _jwks_client


def _claim(payload: dict[str, Any], path: str) -> Any:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _decode_oidc(token: str) -> Actor:
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=settings.oidc_algorithms,
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
            options={"require": ["sub", "exp", "iat"]},
        )
    except HTTPException:
        raise
    except Exception as error:
        raise _unauthorized("Invalid or expired identity-provider token") from error
    raw_roles = _claim(payload, settings.oidc_role_claim) or []
    if isinstance(raw_roles, str):
        raw_roles = [raw_roles]
    roles = frozenset(settings.oidc_role_map[r] for r in raw_roles if r in settings.oidc_role_map)
    if not roles:
        raise HTTPException(status_code=403, detail="Identity has no PredictRx role")
    units = _claim(payload, settings.oidc_units_claim)
    if isinstance(units, str):
        units = [units]
    user = _claim(payload, settings.oidc_user_claim) or payload["sub"]
    return Actor(
        user_id=str(user),
        role=next(role for role in ROLE_PRIORITY if role in roles),
        auth_mode="oidc",
        roles=roles,
        units=tuple(units) if units else None,
    )


def _decode_integration_key(raw: str) -> Actor:
    key_id, _, secret = raw.partition(".")
    if not key_id or not secret:
        raise _unauthorized("Malformed integration key")
    digest = hashlib.sha256(secret.encode()).hexdigest()
    for key in settings.integration_api_keys:
        if key.key_id == key_id and hmac.compare_digest(key.sha256.lower(), digest):
            return Actor(
                user_id=f"integration-key:{key_id}",
                role="integration",
                auth_mode="integration-key",
                units=tuple(key.units) if key.units else None,
                scopes=tuple(key.scopes),
            )
    raise _unauthorized("Unknown or revoked integration key")


def authenticate(
    authorization: str | None,
    x_integration_key: str | None,
    x_demo_user: str | None,
    x_demo_role: str | None,
) -> Actor:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise _unauthorized("Expected Bearer access token")
        return _decode_oidc(token) if settings.auth_mode == "oidc" else _decode_local(token)
    if x_integration_key:
        return _decode_integration_key(x_integration_key)
    if settings.demo_mode:
        role = x_demo_role or "clinician"
        if role not in ROLES:
            raise HTTPException(status_code=403, detail="Unsupported demo role")
        return Actor(user_id=x_demo_user or "demo-clinician", role=role, auth_mode="demo-header")
    raise _unauthorized("Authentication required")


def require_roles(*allowed_roles: str, allow_temporary_password: bool = False) -> Callable:
    unknown = set(allowed_roles) - ROLES
    if unknown:
        raise ValueError(f"Unknown roles in route guard: {sorted(unknown)}")

    def dependency(
        authorization: str | None = Header(default=None),
        x_integration_key: str | None = Header(default=None),
        x_demo_user: str | None = Header(default=None),
        x_demo_role: str | None = Header(default=None),
    ) -> Actor:
        actor = authenticate(authorization, x_integration_key, x_demo_user, x_demo_role)
        if actor.must_change_password and not allow_temporary_password:
            raise HTTPException(
                status_code=403,
                detail="Change the temporary password before accessing clinical or administrative functions",
            )
        allowed = actor.roles & set(allowed_roles)
        if not allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        if actor.role not in allowed:
            actor = Actor(
                user_id=actor.user_id,
                role=next(role for role in ROLE_PRIORITY if role in allowed),
                auth_mode=actor.auth_mode,
                roles=actor.roles,
                units=actor.units,
                scopes=actor.scopes,
                jti=actor.jti,
                must_change_password=actor.must_change_password,
                totp_enabled=actor.totp_enabled,
                display_name=actor.display_name,
            )
        return actor

    return dependency


def ensure_scope(actor: Actor, scope: str) -> None:
    if not actor.has_scope(scope):
        raise HTTPException(status_code=403, detail=f"Credential lacks scope {scope}")


def ensure_unit(actor: Actor, unit_id: str) -> None:
    if not actor.can_access_unit(unit_id):
        raise HTTPException(status_code=403, detail="Not authorised for this unit")


def validate_security_configuration() -> None:
    problems: list[str] = []
    if settings.auth_mode not in {"local", "oidc"}:
        problems.append("AUTH_MODE must be 'local' or 'oidc'.")
    if settings.site_mode not in {"demo", "silent", "live"}:
        problems.append("SITE_MODE must be demo, silent, or live.")
    if not settings.demo_mode:
        if settings.auth_mode == "local" and (
            settings.jwt_secret == DEFAULT_JWT_SECRET or len(settings.jwt_secret) < 32
        ):
            problems.append("JWT_SECRET must be changed (32+ characters) when DEMO_MODE is false.")
        encryption_material = settings.account_encryption_key or settings.jwt_secret
        if settings.auth_mode == "local" and (
            encryption_material == DEFAULT_JWT_SECRET or len(encryption_material) < 32
        ):
            problems.append(
                "ACCOUNT_ENCRYPTION_KEY must be 32+ characters, or local accounts must use a non-default "
                "JWT_SECRET of that length."
            )
        if settings.auth_mode == "oidc" and not (
            settings.oidc_issuer and settings.oidc_audience and settings.oidc_jwks_url
        ):
            problems.append("OIDC_ISSUER, OIDC_AUDIENCE and OIDC_JWKS_URL are required for AUTH_MODE=oidc.")
        if settings.site_mode == "demo":
            problems.append("SITE_MODE=demo requires DEMO_MODE=true.")
        if settings.export_salt == DEFAULT_EXPORT_SALT:
            problems.append("EXPORT_SALT must be changed when DEMO_MODE is false.")
    if problems:
        raise RuntimeError(" ".join(problems))


_accounts: AccountStore | None = None


def _account_store() -> AccountStore | None:
    if _accounts is not None:
        return _accounts
    try:
        from app.services.engine import get_engine

        # Do not cache the engine-owned store: lifespan shutdown replaces the
        # engine, and a cached in-memory SQLite store then points at a closed DB.
        return AccountStore(get_engine().records)
    except Exception:
        return None


def bind_account_store(store: AccountStore | None) -> None:
    global _accounts
    _accounts = store


def production_security_ready() -> bool:
    if settings.demo_mode:
        return False
    try:
        validate_security_configuration()
    except RuntimeError:
        return False
    return True
