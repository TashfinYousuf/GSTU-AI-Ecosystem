import os
import jwt
import ssl
import certifi

from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from typing import Optional


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

security = HTTPBearer()
ssl_context = ssl.create_default_context(cafile=certifi.where())

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=500, detail="Missing Supabase Env Variables")

    token = credentials.credentials

    try:
        jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"

        jwks_client = PyJWKClient(
            jwks_url,
            ssl_context=ssl_context,
            headers={"apikey": SUPABASE_ANON_KEY}
        )

        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # 🔴 The Ultimate Fix: ES256 Algorithm & Strict Audience Match
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"], 
            audience="authenticated",
            options={"verify_aud": True}
        )

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token structure.")

        return payload

    except Exception as e:
        print(f"Token Verification Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token. Access denied."
        )


async def require_active_account(current_user: dict = Depends(get_current_user)) -> dict:
    """Use this in place of `Depends(get_current_user)` on any route that
    should be unreachable by pending-verification students or
    pending-approval faculty. Admin accounts always pass.
 
    Example usage in a route:
        @router.post("/stream")
        async def chat_stream(request: ChatRequest, current_user: dict = Depends(require_active_account)):
            ...
    """
    meta = current_user.get("user_metadata", {}) or {}
    role = meta.get("role", "student")
    status = meta.get("account_status", "active")
 
    if role == "admin":
        return current_user
 
    if status == "pending":
        raise HTTPException(status_code=403, detail="Your faculty account is pending admin approval.")
    if status in {"blocked", "rejected"}:
        raise HTTPException(status_code=403, detail="This account has been suspended.")
    # "pending_verification" (students) is intentionally allowed through by
    # default — decide per-route whether unverified students should be
    # blocked entirely or just restricted from sensitive actions (e.g. block
    # it specifically on knowledge-base or admin-facing routes, not on
    # ordinary chat). Add a stricter check here if you want a hard block:
    #
    # if status == "pending_verification" and route_requires_verification:
    #     raise HTTPException(status_code=403, detail="Please verify your departmental information first.")
 
    return current_user


optional_security = HTTPBearer(auto_error=False)

def get_optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)):
    """
    Safely checks if a user is logged in. 
    Uses the exact same ES256 JWT decoding logic as get_current_user, 
    but returns None instead of throwing 401 exceptions for guests.
    """
    if not credentials:
        return None

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return None

    token = credentials.credentials

    try:
        jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"

        jwks_client = PyJWKClient(
            jwks_url,
            ssl_context=ssl_context,
            headers={"apikey": SUPABASE_ANON_KEY}
        )

        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"], 
            audience="authenticated",
            options={"verify_aud": True}
        )

        user_id = payload.get("sub")
        if user_id is None:
            return None

        # Returns the decoded JWT payload which contains sub, user_metadata, etc.
        return payload

    except Exception:
        # Silently catch token expiration or invalid tokens -> Treat as Guest
        return None