from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import UserResponse
from app.auth import (
    authenticate_user,
    create_access_token,
    set_auth_cookie,
    clear_auth_cookie,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from datetime import timedelta

router = APIRouter(tags=["Authentication"])


def _credentials_error() -> HTTPException:
    # One message for "no such email" and "wrong password" alike, so the endpoint
    # can't be used to enumerate which addresses have accounts.
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/login", response_model=UserResponse)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Browser login: sets the session as an HttpOnly cookie.

    The JWT is deliberately NOT in the response body. Putting it there would let
    any script on the page read it — including an XSS payload that hooks `fetch`
    to capture the login response — which is exactly the exposure the HttpOnly
    cookie exists to prevent.

    Returns the user's profile instead, so the client has something to render
    without a follow-up round-trip to /users/me.

    Note: OAuth2PasswordRequestForm expects form fields named 'username'
    (which will be your email) and 'password'.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise _credentials_error()

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    set_auth_cookie(response, access_token)
    return user


@router.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 token endpoint for non-browser clients (Swagger UI, curl, CI).

    Hands back a bearer token to callers that have no cookie jar. Sets no
    cookie — browsers should use /login instead so the token stays out of
    JavaScript's reach.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise _credentials_error()

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response):
    """Clears the auth cookie."""
    clear_auth_cookie(response)
    return {"message": "Successfully logged out"}
