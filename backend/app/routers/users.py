from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import timedelta

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserUpdate , UserResponse
from app.utils import hash_password
from app.auth import get_current_user, authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(tags=["Users"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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
        first_name=user.first_name,
        last_name=user.last_name,
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

@router.patch("/me", response_model=UserResponse)
@router.put("/me", response_model=UserResponse)
def update_current_user_profile(
    user_update: UserUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the currently logged-in user's profile, email, or password."""
    # 1. Extract only the fields sent in the request body
    update_data = user_update.model_dump(exclude_unset=True)

    # 2. Check email uniqueness if email is being changed
    if "email" in update_data and update_data["email"] != current_user.email:
        email_check = db.query(User).filter(
            User.email == update_data["email"], 
            User.id != current_user.id
        ).first()

        if email_check:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already in use by another account"
            )
    # 3. Hash password ONLY if it was explicitly passed in the update payload
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))

    # 4. Apply changes dynamically to the current_user ORM object
    for key, value in update_data.items():
        setattr(current_user, key, value)

   # 5. Commit & refresh
    db.commit()
    db.refresh(current_user)
    return current_user

    
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