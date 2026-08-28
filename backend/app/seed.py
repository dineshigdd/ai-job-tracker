import random
from datetime import datetime, timedelta, timezone

from app.database import engine, SessionLocal
from app.models import (
    Base, User, Job, JobStatus, JobStatusEvent, Resume, hash_resume_text,
)
from passlib.context import CryptContext

# Password hashing setup (using bcrypt, matching your requirements.txt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fixed seed so every run produces the same numbers; dashboard work is much easier
# to verify when the expected interview rate does not move between runs.
rng = random.Random(42)
# Resumes draw from their own stream, so adding or changing resume seed data cannot
# shift a single job's match score or interview date.
resume_rng = random.Random(1337)

NOW = datetime.now(timezone.utc)


def hash_password(password: str):
    safe_password = password[:72]
    return pwd_context.hash(safe_password)


# --- Sample job pool -------------------------------------------------------------

COMPANIES = [
    ("Google", "Full Stack Engineer"), ("Stripe", "Backend Developer"),
    ("OpenAI", "AI Integration Engineer"), ("Datadog", "Platform Engineer"),
    ("Shopify", "Senior Python Engineer"), ("Cloudflare", "Systems Engineer"),
    ("Atlassian", "Backend Engineer"), ("Netflix", "Data Platform Engineer"),
    ("Airbnb", "API Engineer"), ("Notion", "Product Engineer"),
    ("Figma", "Infrastructure Engineer"), ("Linear", "Full Stack Developer"),
    ("Vercel", "Developer Experience Engineer"), ("Supabase", "Database Engineer"),
    ("Anthropic", "Backend Engineer"), ("Ramp", "Payments Engineer"),
    ("Plaid", "Integrations Engineer"), ("Twilio", "API Platform Engineer"),
    ("Databricks", "Distributed Systems Engineer"), ("Snowflake", "Query Engine Engineer"),
    ("HashiCorp", "Cloud Engineer"), ("GitLab", "Backend Engineer"),
    ("Elastic", "Search Engineer"), ("MongoDB", "Solutions Engineer"),
    ("Redis", "Core Engineer"), ("Confluent", "Streaming Engineer"),
    ("Canva", "Backend Engineer"), ("Miro", "Platform Engineer"),
]

DESCRIPTION = (
    "Design, build and operate {role} systems. You will work with Python, FastAPI and "
    "PostgreSQL, own services end to end, and partner closely with product teams. "
    "Requirements: 3+ years backend experience, strong SQL, REST API design, and "
    "familiarity with cloud infrastructure and CI/CD."
)

# Each trajectory is the ordered list of statuses an application passed through.
# Weights are tuned to look like a real job hunt: most applications go nowhere,
# a quarter reach an interview, a couple convert.
TRAJECTORIES = [
    ([JobStatus.WISHLIST], 3),
    ([JobStatus.APPLIED], 7),
    ([JobStatus.APPLIED, JobStatus.REJECTED], 13),
    ([JobStatus.APPLIED, JobStatus.INTERVIEWING], 4),
    ([JobStatus.APPLIED, JobStatus.INTERVIEWING, JobStatus.REJECTED], 3),
    ([JobStatus.APPLIED, JobStatus.INTERVIEWING, JobStatus.OFFER], 2),
]


# --- Sample resumes --------------------------------------------------------------
# Written the way pypdf actually returns text: plain lines, no styling, no columns.
# Scoring reads this text, so it carries real skill keywords worth matching against.

BACKEND_RESUME_V1 = """A. DEVELOPER
Bangalore, India | a.developer@example.com | github.com/adeveloper

SUMMARY
Backend engineer with 4 years building REST APIs and data services.

EXPERIENCE
Backend Engineer, Zeta Systems (2022 - Present)
- Built and maintained REST APIs in Python and Flask serving 40k daily requests.
- Migrated a monolithic reporting job to Celery workers, cutting runtime from 50 to 9 minutes.
- Wrote integration tests with pytest, raising coverage on the billing module to 82%.

Software Engineer, Orbit Retail (2020 - 2022)
- Developed order-management endpoints backed by PostgreSQL.
- Added Redis caching to the catalogue service, reducing p95 latency by 35%.

SKILLS
Python, Flask, PostgreSQL, Redis, Celery, Docker, Git, pytest, REST APIs, Linux

EDUCATION
B.E. Computer Science, Anna University, 2020
"""

BACKEND_RESUME_V2 = """A. DEVELOPER
Bangalore, India | a.developer@example.com | github.com/adeveloper | linkedin.com/in/adeveloper

SUMMARY
Backend engineer with 5 years designing, shipping and operating Python services on AWS.
Owns systems end to end, from schema design to on-call.

EXPERIENCE
Senior Backend Engineer, Zeta Systems (2022 - Present)
- Designed a FastAPI service replacing a legacy Flask monolith, now serving 120k requests/day.
- Modelled the PostgreSQL schema and tuned slow queries, cutting p95 read latency from 400ms to 90ms.
- Built the CI/CD pipeline in GitHub Actions with automated migrations and blue/green deploys.
- Introduced structured logging and dashboards, reducing mean time to detect incidents to under 5 minutes.
- Mentored two junior engineers through their first production services.

Software Engineer, Orbit Retail (2020 - 2022)
- Developed order-management endpoints backed by PostgreSQL and SQLAlchemy.
- Added Redis caching to the catalogue service, reducing p95 latency by 35%.
- Containerised six services with Docker, standardising local development.

SKILLS
Python, FastAPI, Flask, SQLAlchemy, PostgreSQL, Redis, Celery, Docker, Kubernetes,
AWS (ECS, RDS, S3), GitHub Actions, CI/CD, pytest, REST API design, SQL, Linux

EDUCATION
B.E. Computer Science, Anna University, 2020
"""

DATA_RESUME = """P. APPLICANT
Remote | p.applicant@example.com

SUMMARY
Data platform engineer with 3 years building batch and streaming pipelines.

EXPERIENCE
Data Engineer, Northwind Analytics (2023 - Present)
- Built Airflow DAGs ingesting 2TB/day into Snowflake.
- Wrote dbt models powering the executive revenue dashboard.
- Cut warehouse spend 22% by rewriting three full-refresh models as incremental.

Junior Data Engineer, Cinder Labs (2021 - 2023)
- Maintained Python ETL scripts loading event data into PostgreSQL.
- Added data quality checks that caught schema drift before it reached reporting.

SKILLS
Python, SQL, Airflow, dbt, Snowflake, PostgreSQL, Spark, Kafka, Docker, Git

EDUCATION
B.Sc. Statistics, University of Delhi, 2021
"""

# (filename, text, is_active, days_ago). One user carries two versions so the
# "resume history" and version-comparison paths have something to read; the older
# one is inactive because the partial unique index allows only one active per user.
RESUMES = {
    "user1": [
        ("a-developer-resume-2024.pdf", BACKEND_RESUME_V1, False, 210),
        ("a-developer-resume-backend.pdf", BACKEND_RESUME_V2, True, 45),
    ],
    "user2": [
        ("p-applicant-data-engineer.pdf", DATA_RESUME, True, 30),
    ],
    # user3 deliberately has none, so the "upload your first resume" empty state
    # and the "cannot score without a resume" error path are both testable
    "user3": [],
}


def build_resume(user, filename, extracted_text, is_active, days_ago):
    """Creates a Resume row exactly as the upload endpoint would after parsing a PDF."""
    return Resume(
        user_id=user.id,
        filename=filename,
        extracted_text=extracted_text,
        content_hash=hash_resume_text(extracted_text),
        is_active=is_active,
        created_at=NOW - timedelta(days=days_ago, hours=resume_rng.randint(0, 23)),
    )


def build_job(user, company, title, first_seen, trajectory):
    """Creates a Job plus the JobStatusEvent rows describing how it got there."""
    job = Job(
        user_id=user.id,
        company_name=company,
        job_title=title,
        job_description=DESCRIPTION.format(role=title.lower()),
        status=trajectory[-1].value,
        match_score=rng.randint(58, 98),
        created_at=first_seen,
        updated_at=first_seen,
    )

    # Roughly two thirds of applications got an AI cover letter
    if trajectory[0] is not JobStatus.WISHLIST and rng.random() < 0.65:
        job.ai_cover_letter = (
            f"Dear {company} Hiring Team,\n\nI am writing to apply for the {title} role. "
            "My background in backend engineering with Python and PostgreSQL maps "
            "closely to what you are building...\n\nSincerely,\nA. Developer"
        )
        job.cover_letter_generated_at = first_seen + timedelta(hours=rng.randint(1, 30))

    events = []
    changed_at = first_seen
    previous = None
    for status in trajectory:
        events.append(JobStatusEvent(
            job=job,
            user_id=user.id,
            from_status=previous.value if previous else None,
            to_status=status.value,
            changed_at=changed_at,
        ))
        previous = status
        # Real pipelines move in fits and starts
        changed_at = changed_at + timedelta(days=rng.randint(3, 18))

    job.updated_at = events[-1].changed_at

    # Give every job that reached Interviewing a real interview date. Anything still
    # sitting in Interviewing gets a future one, so "upcoming interviews" is populated.
    if JobStatus.INTERVIEWING in trajectory:
        interview_event = next(e for e in events if e.to_status == JobStatus.INTERVIEWING.value)
        if trajectory[-1] is JobStatus.INTERVIEWING:
            job.interview_date = NOW + timedelta(days=rng.randint(1, 12), hours=rng.randint(0, 8))
        else:
            job.interview_date = interview_event.changed_at + timedelta(days=rng.randint(2, 7))

    return job, events


def seed_database():
    print("🌱 Starting database seeding...")

    # 1. Recreate all tables (Drops old data and builds fresh tables)
    print("Dropping existing tables and recreating them...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # 2. Open a database session
    db = SessionLocal()
    # Keep in-memory values usable after commit, for the summary printed at the end
    db.expire_on_commit = False

    try:
        # 3. Create sample users
        print("Creating sample users...")
        # 3. Create sample users
        print("Creating sample users...")
        user1 = User(
            first_name="Alex",
            last_name="Developer",
            email="developer@example.com",
            hashed_password=hash_password("password123")
        )
        user2 = User(
            first_name="Priya",
            last_name="Applicant",
            email="applicant@example.com",
            hashed_password=hash_password("securepassword")
        )
        # Deliberately left with no jobs, so the dashboard's empty state is testable
        user3 = User(
            first_name="Sam",
            last_name="Newcomer",
            email="newcomer@example.com",
            hashed_password=hash_password("password123")
        )

        db.add_all([user1, user2, user3])
        db.commit()  # Commit to generate user IDs

        for user in (user1, user2, user3):
            db.refresh(user)

        # 4. Create sample resumes (parsed text only, as the upload endpoint stores it)
        print("Creating sample resumes...")
        resumes = []
        for key, user in (("user1", user1), ("user2", user2), ("user3", user3)):
            for filename, resume_text, is_active, days_ago in RESUMES[key]:
                resumes.append(build_resume(user, filename, resume_text, is_active, days_ago))

        db.add_all(resumes)
        db.commit()

        # 5. Create sample jobs with full status histories
        print("Creating sample jobs and status histories...")

        # Draw trajectories from a shuffled deck rather than sampling with
        # replacement, so the resulting rates actually match the weights above
        # instead of drifting with the random draw.
        deck = [t for t, weight in TRAJECTORIES for _ in range(weight)]
        rng.shuffle(deck)
        pool = COMPANIES[:]
        rng.shuffle(pool)

        records = []
        # user1 gets a dense five-month history; user2 a smaller one, which also
        # proves the dashboard's per-user filtering actually isolates data
        drawn = 0
        for user, count, span_days in ((user1, 22, 150), (user2, 6, 60)):
            for company, title in pool[:count]:
                first_seen = NOW - timedelta(
                    days=rng.randint(20, span_days), hours=rng.randint(0, 23)
                )
                trajectory = deck[drawn % len(deck)]
                drawn += 1
                records.append(build_job(user, company, title, first_seen, trajectory))
            pool = pool[count:]

        for job, events in records:
            db.add(job)
            db.add_all(events)
        db.commit()

        # 6. Report what was created, so the numbers the dashboard should show are known
        jobs = [job for job, _ in records]
        events = [e for _, evs in records for e in evs]
        user1_jobs = [j for j in jobs if j.user_id == user1.id]
        submitted = [j for j in user1_jobs if j.status != JobStatus.WISHLIST.value]
        user1_events = [e for e in events if e.user_id == user1.id]
        reached = lambda s: len({e.job_id for e in user1_events if e.to_status == s.value})

        print(f"\n✨ Seeded {len(jobs)} jobs, {len(events)} status events "
              f"and {len(resumes)} resumes.")
        for user, label in ((user1, "developer@example.com"),
                            (user2, "applicant@example.com"),
                            (user3, "newcomer@example.com")):
            owned = [r for r in resumes if r.user_id == user.id]
            active = next((r for r in owned if r.is_active), None)
            print(f"   {label:<24} {len(owned)} resume(s), "
                  f"active: {active.filename if active else 'none'}")

        print(f"\ndeveloper@example.com — {len(user1_jobs)} jobs, {len(submitted)} submitted")
        for status in JobStatus:
            print(f"   {status.value:<13} {sum(1 for j in user1_jobs if j.status == status.value)}")
        if submitted:
            print(f"   Interview Rate  {reached(JobStatus.INTERVIEWING) / len(submitted):.1%}"
                  f"  ({reached(JobStatus.INTERVIEWING)}/{len(submitted)} ever reached)")
            print(f"   Offer Rate      {reached(JobStatus.OFFER) / len(submitted):.1%}"
                  f"  ({reached(JobStatus.OFFER)}/{len(submitted)} ever reached)")
        print(f"   Upcoming interviews  {sum(1 for j in user1_jobs if j.interview_date and j.interview_date > NOW)}")
        print("\n✨ Database seeding completed successfully!")

    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
