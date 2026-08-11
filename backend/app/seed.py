from app.database import engine, SessionLocal
from app.models import Base, User, Job
from passlib.context import CryptContext

# Password hashing setup (using bcrypt, matching your requirements.txt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    safe_password = password[:72]
    return pwd_context.hash(safe_password)

def seed_database():
    print("🌱 Starting database seeding...")

    # 1. Recreate all tables (Drops old data and builds fresh tables)
    print("Dropping existing tables and recreating them...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # 2. Open a database session
    db = SessionLocal()

    try:
        # 3. Create sample users
        print("Creating sample users...")
        user1 = User(
            email="developer@example.com",
            hashed_password=hash_password("password123")
        )
        user2 = User(
            email="applicant@example.com",
            hashed_password=hash_password("securepassword")
        )
        
        db.add_all([user1, user2])
        db.commit() # Commit to generate user IDs

        # Refresh instances to get their database assigned IDs
        db.refresh(user1)
        db.refresh(user2)

        # 4. Create sample jobs tied to those users
        print("Creating sample jobs...")
        job1 = Job(
            user_id=user1.id,
            company_name="Google",
            job_title="Full Stack Engineer",
            job_description="Build scalable web applications using React, Python, and cloud services.",
            status="Interviewing",
            ai_cover_letter="Dear Hiring Manager, I am thrilled to apply...",
            match_score=92
        )
        
        job2 = Job(
            user_id=user1.id,
            company_name="Stripe",
            job_title="Backend Developer",
            job_description="Develop high-performance payment microservices with FastAPI and PostgreSQL.",
            status="Applied",
            ai_cover_letter="Dear Stripe Team, With my background in backend APIs...",
            match_score=85
        )

        job3 = Job(
            user_id=user2.id,
            company_name="OpenAI",
            job_title="AI Integration Engineer",
            job_description="Integrate cutting-edge LLMs into user-facing product workflows.",
            status="Offered",
            ai_cover_letter="Dear OpenAI Team, Passionate about safe AI systems...",
            match_score=98
        )

        db.add_all([job1, job2, job3])
        db.commit()

        print("✨ Database seeding completed successfully!")

    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()