from __future__ import annotations

import hmac
import crypt
from typing import Mapping


def verify_admin_password(username: str, password: str, admins: Mapping[str, str] | None) -> bool:
    if not admins:
        return False
    safe_user = (username or "").strip()
    safe_password = password or ""
    if not safe_user or not safe_password:
        return False

    stored = admins.get(safe_user)
    if not stored:
        return False

    # bcrypt hashed secret (e.g. $2b$12$...)
    if stored.startswith("$2"):
        return hmac.compare_digest(crypt.crypt(safe_password, stored), stored)

    # Plaintext fallback for local dev only.
    return hmac.compare_digest(stored, safe_password)
