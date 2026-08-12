from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import timedelta

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse
from app.utils import hash_password
from app.auth import get_current_user, authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# Note: Keeping registration public so new users can sign up!
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account with a securely hashed password."""
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )

    secure_hashed_password = hash_password(user.password)
    new_user = User(
        email=user.email,
        hashed_password=secure_hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Login endpoint to obtain JWT token for authenticated users
@router.post("/login")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login. 
    Exchanges user email (passed as 'username') and password for a JWT access token.
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
    
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(response: UserResponse):
    """Clears the HTTP-only authentication cookie to log the user out."""
    response.delete_cookie(key="access_token")
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Fetch the profile of the currently logged-in user using their JWT token."""
    return current_user

@router.put("/me", response_model=UserResponse)
def update_current_user_profile(
    user_update: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the currently logged-in user's email or password."""
    # Check if the updated email is already taken by another account
    email_check = db.query(User).filter(User.email == user_update.email, User.id != current_user.id).first()
    if email_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already in use by another account"
        )

    user_query = db.query(User).filter(User.id == current_user.id)
    updated_data = {
        "email": user_update.email,
        "hashed_password": hash_password(user_update.password)
    }

    user_query.update(updated_data, synchronize_session=False)
    db.commit()
    return user_query.first()

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete the currently logged-in user's account."""
    user = db.query(User).filter(User.id == current_user.id).first()
    if user:
        db.delete(user)
        db.commit()
    return None

# Optional: Keep an admin-only or general list endpoint if needed for debugging, 
# or remove it entirely so list of users isn't publicly exposed.
@router.get("/", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetch all registered users (secured behind authentication)."""
    return db.query(User).all()