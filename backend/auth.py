import os
import hmac
import hashlib
import base64
import json
import time
import secrets
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends

SECRET_KEY = os.environ.get("LASTCHANCE_SECRET_KEY", "lastchance_production_secret_key_2026_secure")

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a secure salt."""
    if not salt:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{dk.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a plain password against the stored salt:hash string."""
    try:
        parts = stored_hash.split(':')
        if len(parts) != 2:
            return False
        salt, expected_hex = parts[0], parts[1]
        test_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        return hmac.compare_digest(test_hash, expected_hex)
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_in_seconds: int = 86400 * 30) -> str:
    """Creates a signed, URL-safe HMAC-SHA256 authentication token."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = dict(data)
    payload["exp"] = int(time.time()) + expires_in_seconds
    payload["iat"] = int(time.time())

    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')

    sig = hmac.new(SECRET_KEY.encode(), f"{h_b64}.{p_b64}".encode(), hashlib.sha256).digest()
    s_b64 = base64.urlsafe_b64encode(sig).decode().rstrip('=')

    return f"{h_b64}.{p_b64}.{s_b64}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and cryptographically verifies an access token."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        h_b64, p_b64, s_b64 = parts

        # Re-compute signature
        expected_sig = hmac.new(SECRET_KEY.encode(), f"{h_b64}.{p_b64}".encode(), hashlib.sha256).digest()
        actual_sig = base64.urlsafe_b64decode(s_b64 + '=' * (-len(s_b64) % 4))
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        # Decode payload
        payload_bytes = base64.urlsafe_b64decode(p_b64 + '=' * (-len(p_b64) % 4))
        payload = json.loads(payload_bytes.decode())

        if payload.get("exp", 0) < int(time.time()):
            return None # Expired

        return payload
    except Exception:
        return None

def get_optional_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """Extracts user from optional Authorization: Bearer <token> header."""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    return decode_access_token(token)

def get_required_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Requires a valid user token."""
    user = get_optional_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required or token expired.")
    return user
