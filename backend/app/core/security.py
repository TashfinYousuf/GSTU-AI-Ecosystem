import os
import jwt
import ssl
import certifi
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

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