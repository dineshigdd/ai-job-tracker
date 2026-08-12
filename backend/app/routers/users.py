from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse
from app.utils import hash_password  # Import our new helper function

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account with a securely hashed password."""
    # Check if a user with this email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )

    # Hash the plaintext password before saving to the database
    secure_hashed_password = hash_password(user.password)

    new_user = User(
        email=user.email,
        hashed_password=secure_hashed_password  # Now securely hashed!
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    """Fetch all registered users."""
    return db.query(User).all()

@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(user_id: UUID, db: Session = Depends(get_db)):
    """Fetch a specific user profile by their UUID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: UUID, user_update: UserCreate, db: Session = Depends(get_db)):
    """Update an existing user's email or password."""
    user_query = db.query(User).filter(User.id == user_id)
    existing_user = user_query.first()
    
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if the updated email is already taken by another account
    email_check = db.query(User).filter(User.email == user_update.email, User.id != user_id).first()
    if email_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already in use by another account"
        )

    # Hash the new password and update fields
    updated_data = {
        "email": user_update.email,
        "hashed_password": hash_password(user_update.password)
    }

    user_query.update(updated_data, synchronize_session=False)
    db.commit()
    
    return user_query.first()

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, db: Session = Depends(get_db)):
    """Delete a user account by their UUID."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    db.delete(user)
    db.commit()
    return None