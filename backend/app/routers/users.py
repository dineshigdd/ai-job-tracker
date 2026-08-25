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

router = APIRouter(tags=["Users"])

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