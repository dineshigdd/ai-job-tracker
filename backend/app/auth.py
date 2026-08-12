from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Request, Response, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from app.database import get_db
from app.models import User
from app.utils import verify_password

load_dotenv()

# --- CONFIGURATION ---
SECRET_KEY = os.getenv("SECRET_KEY")

# If it's missing, crash the app immediately on startup rather than using a weak fallback
if not SECRET_KEY:
    raise ValueError("CRITICAL ERROR: SECRET_KEY environment variable is missing!")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# --- COOKIE CONFIGURATION ---
COOKIE_NAME = os.getenv("COOKIE_NAME", "access_token")
# Secure=True requires HTTPS, so it stays off in local development
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
# "lax" works for a same-site frontend; use "none" (with Secure=True) for cross-site
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    """Reads the JWT from the HttpOnly cookie first, then falls back to the
    Authorization header so Swagger UI's "Authorize" button keeps working."""

    async def __call__(self, request: Request) -> Optional[str]:
        token = request.cookies.get(COOKIE_NAME)
        if token:
            return token
        return await super().__call__(request)


# This tells FastAPI where the login endpoint is located to retrieve tokens
oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="login", auto_error=False)


def set_auth_cookie(response: Response, token: str) -> None:
    """Stores the JWT in an HttpOnly cookie so JavaScript can never read it."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Removes the auth cookie (logout)."""
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/",
    )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Generates a signed JWT token containing user data."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(db: Session, email: str, password: str):
    """Validates user credentials against database records."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Dependency that decodes the JWT token and returns the current active user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user