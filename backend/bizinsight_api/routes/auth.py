"""
Auth routes — registration, login, JWT token generation.
"""

import os
import re
import jwt
import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database import (
    create_user, get_user_by_username, verify_password, no_users_exist
)
from bizinsight_api.models.schemas import (
    RegisterRequest, LoginRequest, AuthResponse, UserInfo
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])
security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET", "bizinsight-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


def create_token(user: dict) -> str:
    """Generate a JWT token for an authenticated user."""
    payload = {
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Decode JWT token from Authorization header and return user info."""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {
            "id": payload["user_id"],
            "username": payload["username"],
            "role": payload["role"],
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")


@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    """Create a new user account."""
    if not req.username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty.")

    if not req.email.strip():
        raise HTTPException(status_code=400, detail="Email address cannot be empty.")

    email_pattern = r"^[^@]+@[^@]+\.[^@]+$"
    if not re.match(email_pattern, req.email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    # First user becomes admin
    role = "admin" if no_users_exist() else "user"

    result = create_user(req.username, req.email, req.password, role=role)

    if result == "USERNAME_EXISTS":
        raise HTTPException(status_code=409, detail="Username already exists.")
    if result == "EMAIL_EXISTS":
        raise HTTPException(status_code=409, detail="Email already registered.")
    if not result:
        raise HTTPException(status_code=500, detail="Registration failed.")

    user = get_user_by_username(req.username)
    token = create_token(user)

    return AuthResponse(
        token=token,
        user=UserInfo(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
        ),
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    """Authenticate a user and return a JWT token."""
    user = get_user_by_username(req.username)
    if not user:
        raise HTTPException(status_code=401, detail="No account found with that username.")
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect password.")

    token = create_token(user)

    return AuthResponse(
        token=token,
        user=UserInfo(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
        ),
    )


@router.get("/me", response_model=UserInfo)
def me(current_user: dict = Depends(get_current_user)):
    """Return the current authenticated user's info."""
    user = get_user_by_username(current_user["username"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserInfo(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        role=user["role"],
    )
