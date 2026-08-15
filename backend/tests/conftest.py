"""Pytest fixtures for testing the FastAPI backend."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from app.main import app
from app.database import get_db, Base
from app.models import User, Job, JobStatus, JobStatusEvent, Resume
from app.auth import get_current_user

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create all tables before tests run
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables before any tests run."""
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables after tests complete
    Base.metadata.drop_all(bind=engine)


# Dependency override for database session
@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


# Create a unique user for each test session
@pytest.fixture(scope="function")
def test_user(db_session):
    """Create a unique user for each test function."""
    user = User(
        id=uuid4(),
        email=f"test_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed_password_placeholder"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# Dependency override for authentication
@pytest.fixture(scope="function")
def mock_current_user(test_user):
    """Return the test user for authentication."""
    return test_user


# Override dependencies for testing
@pytest.fixture(scope="function")
def client(db_session, test_user):
    """Create a test client with overridden dependencies."""
    
    def get_test_db():
        yield db_session
    
    def get_test_current_user():
        return test_user
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = get_test_current_user
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up overrides
    app.dependency_overrides.clear()


# Fixture to create test jobs
@pytest.fixture(scope="function")
def create_test_jobs(db_session, test_user):
    """Create a set of test jobs for filtering and searching."""
    user = test_user
    
    jobs_data = [
        {
            "company_name": "Google",
            "job_title": "Senior Backend Engineer",
            "job_description": "Build scalable systems",
            "status": JobStatus.APPLIED,
        },
        {
            "company_name": "Microsoft",
            "job_title": "Software Engineer",
            "job_description": "Work on Azure services",
            "status": JobStatus.INTERVIEWING,
        },
        {
            "company_name": "Amazon",
            "job_title": "Backend Developer",
            "job_description": "AWS cloud development",
            "status": JobStatus.APPLIED,
        },
        {
            "company_name": "Meta",
            "job_title": "Senior Engineer",
            "job_description": "Social media infrastructure",
            "status": JobStatus.OFFER,
        },
        {
            "company_name": "Netflix",
            "job_title": "Data Engineer",
            "job_description": "Big data pipelines",
            "status": JobStatus.REJECTED,
        },
        {
            "company_name": "Google",
            "job_title": "Frontend Engineer",
            "job_description": "React development",
            "status": JobStatus.WISHLIST,
        },
        {
            "company_name": "Apple",
            "job_title": "iOS Developer",
            "job_description": "Mobile app development",
            "status": JobStatus.INTERVIEWING,
        },
        {
            "company_name": "Senior Solutions",
            "job_title": "Backend Architect",
            "job_description": "System design",
            "status": JobStatus.APPLIED,
        },
        {
            "company_name": "Anthropic",
            "job_title": "Backend Engineer",
            "job_description": "AI platform development",
            "status": JobStatus.INTERVIEWING,
        },
    ]
    
    jobs = []
    for job_data in jobs_data:
        job = Job(
            **job_data,
            user_id=user.id
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        # Add status event for each job
        event = JobStatusEvent(
            job_id=job.id,
            user_id=user.id,
            from_status=None,
            to_status=job.status
        )
        db_session.add(event)
        jobs.append(job)
    
    db_session.commit()
    return jobs


# Fixture for special character search tests
@pytest.fixture(scope="function")
def create_special_char_jobs(db_session, test_user):
    """Create jobs with special characters for escape testing."""
    user = test_user
    
    jobs_data = [
        {
            "company_name": "100% Remote",
            "job_title": "Backend Engineer",
            "status": JobStatus.APPLIED,
        },
        {
            "company_name": "Company_A",
            "job_title": "Developer",
            "status": JobStatus.APPLIED,
        },
        {
            "company_name": "Test\\Backslash",
            "job_title": "Engineer",
            "status": JobStatus.APPLIED,
        },
    ]
    
    jobs = []
    for job_data in jobs_data:
        job = Job(
            **job_data,
            user_id=user.id
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        jobs.append(job)
    
    db_session.commit()
    return jobs


# Resume fixtures
@pytest.fixture(scope="function")
def test_resume(db_session, test_user):
    """Create a test resume for the test user."""
    resume = Resume(
        user_id=test_user.id,
        filename="test_resume.pdf",
        extracted_text="Python Django developer with 5 years of experience",
        content_hash="a" * 64,
        is_active=True
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


@pytest.fixture(scope="function")
def inactive_resume(db_session, test_user):
    """Create an inactive test resume for the test user."""
    resume = Resume(
        user_id=test_user.id,
        filename="inactive_resume.pdf",
        extracted_text="Old resume content",
        content_hash="b" * 64,
        is_active=False
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


@pytest.fixture(scope="function")
def test_job(db_session, test_user):
    """Create a single test job for the test user."""
    job = Job(
        id=uuid4(),
        user_id=test_user.id,
        company_name="Test Company",
        job_title="Test Job",
        job_description="Test job description",
        status=JobStatus.APPLIED
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture(scope="function")
def test_job_with_description(db_session, test_user):
    """Create a test job with a description."""
    job = Job(
        id=uuid4(),
        user_id=test_user.id,
        company_name="Test Company",
        job_title="Senior Developer",
        job_description="Looking for experienced Python developer",
        status=JobStatus.APPLIED
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture(scope="function")
def test_job_without_description(db_session, test_user):
    """Create a test job without a description."""
    job = Job(
        id=uuid4(),
        user_id=test_user.id,
        company_name="Test Company",
        job_title="Developer",
        job_description=None,
        status=JobStatus.APPLIED
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture(scope="function")
def test_job_with_cover_letter(db_session, test_user):
    """Create a test job with an existing cover letter."""
    import datetime
    job = Job(
        id=uuid4(),
        user_id=test_user.id,
        company_name="Test Company",
        job_title="Developer",
        job_description="Python developer needed",
        status=JobStatus.APPLIED,
        ai_cover_letter="Existing cover letter content",
        cover_letter_generated_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job
