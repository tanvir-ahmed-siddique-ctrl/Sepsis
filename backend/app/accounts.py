"""Local site accounts: scrypt passwords, lockout, TOTP, ward PIN, token revocation.

Passwords never leave the server. Tokens carry a ``jti`` that can be revoked on
password change, PIN change, or admin disable. Demo headers still work only
while ``DEMO_MODE=true``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import base64
import struct
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.records import RecordStore, revoked_tokens, site_users, utc_now

ROLES = {"clinician", "nurse", "admin", "operator"}
LOCKOUT_AFTER = 5
LOCKOUT_SECONDS = 15 * 60
PIN_LENGTHS = {4, 5, 6}
SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_DK = 2**14, 8, 1, 32


def _encode_hash(algorithm: str, salt: bytes, digest: bytes, **params: int) -> str:
    packed = ",".join(f"{key}={value}" for key, value in params.items())
    return f"{algorithm}${packed}${salt.hex()}${digest.hex()}"


def hash_secret(secret: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(secret.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_DK)
    return _encode_hash("scrypt", salt, digest, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dk=SCRYPT_DK)


def verify_secret(secret: str, stored: str) -> bool:
    try:
        algorithm, packed, salt_hex, digest_hex = stored.split("$")
        params = dict(part.split("=") for part in packed.split(",") if part)
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
        if algorithm == "scrypt":
            actual = hashlib.scrypt(
                secret.encode(),
                salt=salt,
                n=int(params["n"]),
                r=int(params["r"]),
                p=int(params["p"]),
                dklen=int(params["dk"]),
            )
        else:
            return False
        return hmac.compare_digest(actual, expected)
    except (ValueError, KeyError):
        return False


def _hotp(secret: bytes, counter: int) -> str:
    digest = hmac.new(secret, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 1_000_000:06d}"


def totp_now(secret_b32: str, timestamp: float | None = None, window: int = 1) -> list[str]:
    secret = _b32decode(secret_b32)
    step = int((timestamp or time.time()) // 30)
    return [_hotp(secret, step + delta) for delta in range(-window, window + 1)]


def _b32decode(value: str) -> bytes:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    bits = "".join(f"{alphabet.index(ch):05b}" for ch in value.strip().upper().replace("=", "") if ch in alphabet)
    return bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits) - len(bits) % 8, 8))


def new_totp_secret() -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    return "".join(alphabet[b % 32] for b in os.urandom(20))


def _fernet() -> Fernet:
    material = (settings.account_encryption_key or settings.jwt_secret).encode()
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(material).digest()))


def _seal(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def _unseal(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as error:
        raise ValueError("Stored authenticator secret cannot be decrypted; check ACCOUNT_ENCRYPTION_KEY") from error


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": row["user_id"],
        "display_name": row["display_name"],
        "role": row["role"],
        "units": json.loads(row["units"]) if row["units"] else None,
        "disabled": bool(row["disabled"]),
        "must_change_password": bool(row["must_change_password"]),
        "totp_enabled": bool(row["totp_secret"]) and not str(row["totp_secret"]).startswith("pending:"),
        "pin_set": bool(row["pin_hash"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_login_at": row.get("last_login_at"),
    }


class AccountStore:
    def __init__(self, records: RecordStore) -> None:
        self.records = records

    def get(self, user_id: str) -> dict[str, Any] | None:
        rows = self.records.select(site_users, site_users.c.user_id == user_id.lower())
        return rows[0] if rows else None

    def list_users(self) -> list[dict[str, Any]]:
        return [public_user(row) for row in self.records.select(site_users, order_by=site_users.c.user_id)]

    def count(self) -> int:
        return len(self.records.select(site_users))

    def active_admin_count(self) -> int:
        return len(
            self.records.select(
                site_users,
                site_users.c.role == "admin",
                site_users.c.disabled == 0,
            )
        )

    def create(
        self,
        user_id: str,
        display_name: str,
        role: str,
        password: str,
        *,
        units: list[str] | None,
        actor_id: str,
        must_change_password: bool = True,
    ) -> dict[str, Any]:
        if role not in ROLES:
            raise ValueError("Role must be clinician, nurse, admin or operator")
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters")
        key = user_id.strip().lower()
        if not key or len(key) > 64:
            raise ValueError("User id must be 1–64 characters")
        row = {
            "user_id": key,
            "display_name": display_name.strip() or key,
            "role": role,
            "units": json.dumps(units) if units else None,
            "password_hash": hash_secret(password),
            "pin_hash": None,
            "totp_secret": None,
            "must_change_password": int(must_change_password),
            "disabled": 0,
            "failed_logins": 0,
            "locked_until": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "created_by": actor_id,
            "last_login_at": None,
        }
        if not self.records.insert(site_users, row):
            raise ValueError("User already exists")
        return public_user(row)

    def update(self, user_id: str, **changes: Any) -> dict[str, Any]:
        row = self.get(user_id)
        if row is None:
            raise LookupError("User not found")
        payload = {**row, **changes, "updated_at": utc_now()}
        self.records.upsert(site_users, "user_id", payload)
        return public_user(payload)

    def authenticate_password(self, user_id: str, password: str) -> dict[str, Any]:
        row = self._require_active(user_id)
        if not verify_secret(password, row["password_hash"]):
            self._fail(row)
            raise PermissionError("Invalid user or password")
        return self._succeed(row)

    def authenticate_pin(self, user_id: str, pin: str) -> dict[str, Any]:
        row = self._require_active(user_id)
        if not row["pin_hash"] or not verify_secret(pin, row["pin_hash"]):
            self._fail(row)
            raise PermissionError("Invalid user or PIN")
        return self._succeed(row)

    def set_password(self, user_id: str, new_password: str, *, current: str | None = None, admin: bool = False) -> None:
        row = self._require_active(user_id, allow_disabled=admin)
        if not admin:
            if current is None or not verify_secret(current, row["password_hash"]):
                raise PermissionError("Current password is wrong")
        if len(new_password) < 12:
            raise ValueError("Password must be at least 12 characters")
        self.update(user_id, password_hash=hash_secret(new_password), must_change_password=0, failed_logins=0, locked_until=None)
        self.revoke_user(user_id, "password_changed")

    def set_pin(self, user_id: str, pin: str) -> None:
        if not pin.isdigit() or len(pin) not in PIN_LENGTHS:
            raise ValueError("PIN must be 4–6 digits")
        self._require_active(user_id)
        self.update(user_id, pin_hash=hash_secret(pin))
        self.revoke_user(user_id, "pin_changed")

    def begin_totp(self, user_id: str) -> str:
        self._require_active(user_id)
        secret = new_totp_secret()
        self.update(user_id, totp_secret=f"pending:{_seal(secret)}")
        return secret

    def confirm_totp(self, user_id: str, code: str) -> None:
        row = self._require_active(user_id)
        stored = row["totp_secret"] or ""
        if not stored.startswith("pending:"):
            raise ValueError("No TOTP enrolment in progress")
        secret = _unseal(stored.split(":", 1)[1])
        if code not in totp_now(secret):
            raise PermissionError("Authenticator code is wrong")
        self.update(user_id, totp_secret=_seal(secret))

    def verify_totp(self, row: dict[str, Any], code: str) -> None:
        stored = row.get("totp_secret") or ""
        if not stored or stored.startswith("pending:"):
            return
        secret = _unseal(stored)
        if code not in totp_now(secret):
            raise PermissionError("Authenticator code is required")

    def disable(self, user_id: str, disabled: bool) -> dict[str, Any]:
        updated = self.update(user_id, disabled=int(disabled))
        if disabled:
            self.revoke_user(user_id, "disabled")
        return updated

    def reset_factors(self, user_id: str) -> dict[str, Any]:
        self._require_active(user_id, allow_disabled=True)
        updated = self.update(user_id, pin_hash=None, totp_secret=None)
        self.revoke_user(user_id, "authentication_factors_reset")
        return updated

    def delete(self, user_id: str) -> None:
        row = self.get(user_id)
        if row is None:
            raise LookupError("User not found")
        # Audit events retain the stable user_id string, while credentials and
        # the directory profile are removed.
        self.revoke_user(user_id, "account_deleted")
        self.records.delete(site_users, site_users.c.user_id == user_id.lower())

    def revoke_user(self, user_id: str, reason: str) -> None:
        self.records.insert(
            revoked_tokens,
            {
                "jti": f"user:{user_id.lower()}:{utc_now()}",
                "user_id": user_id.lower(),
                "revoked_at": utc_now(),
                "reason": reason,
            },
        )

    def revoke_jti(self, jti: str, user_id: str, reason: str) -> None:
        self.records.insert(
            revoked_tokens,
            {"jti": jti, "user_id": user_id.lower(), "revoked_at": utc_now(), "reason": reason},
        )

    def is_revoked(self, jti: str, user_id: str, issued_at: datetime) -> bool:
        rows = self.records.select(revoked_tokens, revoked_tokens.c.user_id == user_id.lower())
        for row in rows:
            if row["jti"] == jti:
                return True
            if row["jti"].startswith(f"user:{user_id.lower()}:") and row["revoked_at"] >= issued_at.isoformat():
                return True
        return False

    def _require_active(self, user_id: str, allow_disabled: bool = False) -> dict[str, Any]:
        row = self.get(user_id)
        if row is None:
            raise PermissionError("Invalid user or password")
        if row["disabled"] and not allow_disabled:
            raise PermissionError("Account is disabled")
        locked = row.get("locked_until")
        if locked and locked > utc_now():
            raise PermissionError("Account is locked after too many failed attempts")
        return row

    def _fail(self, row: dict[str, Any]) -> None:
        failed = int(row["failed_logins"] or 0) + 1
        locked_until = None
        if failed >= LOCKOUT_AFTER:
            locked_until = (datetime.now(timezone.utc) + timedelta(seconds=LOCKOUT_SECONDS)).isoformat()
        self.update(row["user_id"], failed_logins=failed, locked_until=locked_until)

    def _succeed(self, row: dict[str, Any]) -> dict[str, Any]:
        self.update(row["user_id"], failed_logins=0, locked_until=None, last_login_at=utc_now())
        return self.get(row["user_id"]) or row
