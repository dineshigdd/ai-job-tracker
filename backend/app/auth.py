from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
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

# The JWT lives ONLY in this HttpOnly cookie, so no JavaScript — including
# anything an XSS injects — can read it. That guarantee only holds while the
# browser treats the cookie as first-party, which is why the frontend reaches
# this API through its own origin in every environment (Vite proxy in dev,
# Vercel rewrite in production) rather than calling the Render URL directly.
# A cross-site cookie would need SameSite=None, and Safari and Brave block
# those regardless, so there would be no way back to an HttpOnly-only design.
#
# Same-origin also means SameSite=Lax suffices, and a Lax cookie is never
# attached to a cross-site POST/PUT/PATCH/DELETE — that blocks CSRF on every
# state-changing route without a separate token.
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()

# Secure requires HTTPS. Default it on: anything that isn't local development is
# served over TLS. Dev sets ENVIRONMENT=development because Safari refuses to
# store a Secure cookie from http://localhost.
ENVIRONMENT = os.getenv("ENVIRONMENT", "production").lower()
COOKIE_SECURE = os.getenv(
    "COOKIE_SECURE", "false" if ENVIRONMENT == "development" else "true"
).lower() == "true"

# SameSite=None is only honoured alongside Secure — never let the pair be
# invalid if the API is ever deployed on a domain of its own.
if COOKIE_SAMESITE == "none":
    COOKIE_SECURE = True

# Left unset on purpose: a host-only cookie is what we want. Both "onrender.com"
# and "vercel.app" are public suffixes, so a cookie scoped to either is rejected.
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    """Reads the JWT from the HttpOnly cookie first, then falls back to the
    Authorization header.

    Browsers only ever use the cookie. The header path exists for clients that
    have nowhere safe to keep a cookie — Swagger UI's "Authorize" button, curl,
    CI — which get their token from POST /api/auth/token.
    """

    async def __call__(self, request: Request) -> Optional[str]:
        token = request.cookies.get(COOKIE_NAME)
        if token:
            return token
        return await super().__call__(request)


# Absolute path from the server root: the routers are mounted under /api, so a
# bare "login" would resolve against whatever page Swagger was opened from.
oauth2_scheme = OAuth2PasswordBearerWithCookie(
    tokenUrl="/api/auth/token", auto_error=False
)


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
    def unauthorized(detail: str) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Distinct messages so a missing credential (cookie blocked / header absent) is
    # never confused with a malformed or expired one when debugging a deployment.
    if not token:
        raise unauthorized("Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise unauthorized("Session expired, please log in again")
    except JWTError:
        raise unauthorized("Could not validate credentials")

    email: Optional[str] = payload.get("sub")
    if email is None:
        raise unauthorized("Could not validate credentials")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise unauthorized("Could not validate credentials")
    return user