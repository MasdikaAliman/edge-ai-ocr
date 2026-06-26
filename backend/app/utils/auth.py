import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.user_db import get_user

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey123_change_me_in_production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")) # 24 hours default

security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    
    # Check for static API key bypass (e.g. for simple script/automation integration)
    static_key = os.getenv("STATIC_API_KEY")
    if static_key and token == static_key:
        return {"username": "SystemAPI", "role": "admin", "employee": "SYSTEM"}

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error_type": "invalid_token",
                "message": "Token tidak valid atau telah kedaluwarsa.",
            }
        )
    # Check if user still exists
    user = get_user(payload.get("employee"))
    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error_type": "user_not_found",
                "message": "Pengguna tidak ditemukan.",
            }
        )
    return payload

async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "error_type": "forbidden",
                "message": "Hanya Admin yang diizinkan untuk mengakses fitur ini.",
            }
        )
    return current_user
