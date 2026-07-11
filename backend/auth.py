import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .schemas import TokenData

DEFAULT_SECRET = "khai-bao-cang-vu-secret-key-2026"
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET)

# Fail-fast check for production readiness
# Allow default only when running test suite (which sets TEST_DATABASE_URL)
if SECRET_KEY == DEFAULT_SECRET and not os.getenv("TEST_DATABASE_URL"):
    raise SystemExit(
        "CRITICAL CONFIGURATION ERROR: SECRET_KEY must be set in environment variables (non-default value) outside local tests."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")  # Point to actual login endpoint

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin đăng nhập",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=payload.get("role"))
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    # Check if user is disabled
    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa."
        )
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)):
    return current_user
