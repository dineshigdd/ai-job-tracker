from passlib.context import CryptContext

# Setup password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Takes a plaintext password and returns a secure hash string."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)