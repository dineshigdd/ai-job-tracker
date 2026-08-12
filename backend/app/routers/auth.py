from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import (
    authenticate_user,
    create_access_token,
    set_auth_cookie,
    clear_auth_cookie,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from datetime import timedelta

router = APIRouter(tags=["Authentication"])

@router.post("/login")
def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, gets an access token for future requests.
    Note: OAuth2PasswordRequestForm expects form fields named 'username' (which will be your email) and 'password'.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Store the JWT in an HttpOnly cookie; it is returned in the body as well
    # so the Swagger UI / non-browser clients can still use the Bearer flow.
    set_auth_cookie(response, access_token)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(response: Response):
    """Clears the auth cookie."""
    clear_auth_cookie(response)
    return {"message": "Successfully logged out"}