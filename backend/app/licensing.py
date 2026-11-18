"""Offline, site-bound commercial licence verification.

This record is separate from clinical approval. Expiry blocks a *new* live-mode
request when configured, but never interrupts an already running bedside system.
"""

from __future__ import annotations

import base64
import binascii
import json
from datetime import date

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.core.config import settings


def canonical(claims: dict) -> bytes:
    return json.dumps(claims, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def verify_package(package: dict, site_id: str) -> dict:
    if set(package) != {"claims", "key_id", "signature"} or not isinstance(package["claims"], dict):
        raise ValueError("Invalid licence package")
    claims = package["claims"]
    required = {"licence_id", "organization_id", "site_id", "contract_id", "modules", "unit_limit", "bed_limit", "effective_on", "expires_on", "issued_at"}
    if not required.issubset(claims) or claims["site_id"] != site_id:
        raise ValueError("Licence is not bound to this site")
    if not isinstance(claims["modules"], list) or not all(isinstance(item, str) for item in claims["modules"]):
        raise ValueError("Invalid module scope")
    if any(type(claims[key]) is not int or claims[key] < 1 for key in ("unit_limit", "bed_limit")):
        raise ValueError("Invalid entitlement limits")
    entitlement = claims.get("entitlement_status", "active")
    if entitlement not in {"active", "suspended", "revoked"}:
        raise ValueError("Invalid entitlement status")
    try:
        keys = json.loads(settings.licence_public_keys_json)
        raw = base64.b64decode(keys[package["key_id"]], validate=True)
        signature = base64.b64decode(package["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(raw).verify(signature, canonical(claims))
        effective, expires = date.fromisoformat(claims["effective_on"]), date.fromisoformat(claims["expires_on"])
    except (KeyError, ValueError, TypeError, binascii.Error, InvalidSignature) as error:
        raise ValueError("Licence signature or dates invalid") from error
    if effective >= expires:
        raise ValueError("Invalid licence period")
    return claims


def status(package: dict | None, site_id: str) -> dict:
    if not package:
        return {"status": "missing", "activation_eligible": False, "entitlement_status": None}
    try:
        claims = verify_package(package, site_id)
    except ValueError:
        return {"status": "invalid", "activation_eligible": False, "entitlement_status": None}
    entitlement = claims.get("entitlement_status", "active")
    if entitlement in {"revoked", "suspended"}:
        return {
            "status": entitlement,
            "activation_eligible": False,
            "entitlement_status": entitlement,
            "licence_id": claims["licence_id"],
            "site_id": site_id,
            "expires_on": claims["expires_on"],
            "modules": claims["modules"],
        }
    today = date.today()
    state = "not_yet_effective" if today < date.fromisoformat(claims["effective_on"]) else "expired" if today >= date.fromisoformat(claims["expires_on"]) else "current"
    return {
        "status": state,
        "activation_eligible": state == "current" and "icu_risk" in claims["modules"],
        "entitlement_status": entitlement,
        "licence_id": claims["licence_id"],
        "site_id": site_id,
        "expires_on": claims["expires_on"],
        "modules": claims["modules"],
    }
