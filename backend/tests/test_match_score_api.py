"""Test cases for the ATS match score endpoints.

Covers `routers/match_score.py` - `POST`/`GET /jobs/{job_id}/match-score` - and the
`min_score`/`max_score` filters added to `GET /jobs/` (ATS-matching-scorer.md §5.4).

The scorer itself is exercised in `test_match_score.py`; these tests are about the
wiring: ownership, error codes, what gets persisted, and what the response exposes.
No AI mocking is needed - scoring is local, deterministic and makes no network calls.
"""
import pytest
from fastapi import status
from uuid import uuid4

from app.models import Job, JobStatus, Resume, User

JOB_DESCRIPTION = (
    "Senior Backend Developer. Required: Python, Django, PostgreSQL, REST APIs. "
    "Requires 5+ years of experience. Nice to have: AWS, Kubernetes, GraphQL. "
    "Excellent communication and collaboration skills."
)
RESUME_TEXT = (
    "Senior Python Developer with 8 years of experience. "
    "Skills: Python, Django, FastAPI, PostgreSQL, AWS, Docker. "
    "Strong communication and collaboration."
)


@pytest.fixture
def scored_job(db_session, test_user):
    """A job with a description rich enough to score against."""
    job = Job(
        id=uuid4(),
        user_id=test_user.id,
        company_name="Acme",
        job_title="Senior Backend Developer",
        job_description=JOB_DESCRIPTION,
        status=JobStatus.APPLIED,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def active_resume(db_session, test_user):
    resume = Resume(
        user_id=test_user.id,
        filename="cv.pdf",
        extracted_text=RESUME_TEXT,
        content_hash="f" * 64,
        is_active=True,
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


class TestCalculateMatchScore:
    """POST /jobs/{job_id}/match-score"""

    def test_empty_body_uses_the_active_resume(self, client, scored_job, active_resume):
        """Scoring the job you are looking at against the resume you already uploaded
        is the common case, so it must not require a body at all."""
        response = client.post(f"/jobs/{scored_job.id}/match-score")

        assert response.status_code == status.HTTP_200_OK, response.text
        data = response.json()
        assert data["job_id"] == str(scored_job.id)
        assert data["resume_id"] == str(active_resume.id)
        assert 0 <= data["match_score"] <= 100

    def test_explicit_resume_id(self, client, db_session, test_user, scored_job,
                                active_resume):
        """A second, inactive resume can be scored without activating it first."""
        other = Resume(
            user_id=test_user.id,
            filename="older.pdf",
            extracted_text="Java Spring Boot developer, 3 years",
            content_hash="e" * 64,
            is_active=False,
        )
        db_session.add(other)
        db_session.commit()
        db_session.refresh(other)

        response = client.post(
            f"/jobs/{scored_job.id}/match-score", json={"resume_id": str(other.id)}
        )

        assert response.status_code == status.HTTP_200_OK, response.text
        assert response.json()["resume_id"] == str(other.id)

    def test_score_is_persisted_on_the_job(self, client, db_session, scored_job,
                                           active_resume):
        assert scored_job.match_score is None

        data = client.post(f"/jobs/{scored_job.id}/match-score").json()

        db_session.refresh(scored_job)
        assert scored_job.match_score == data["match_score"]

    def test_returns_200_not_201(self, client, scored_job, active_resume):
        """§5.1: this updates an existing job, it does not create a resource."""
        response = client.post(f"/jobs/{scored_job.id}/match-score")
        assert response.status_code == status.HTTP_200_OK

    def test_missing_job_description_falls_back_to_the_title(
        self, client, db_session, test_user, active_resume
    ):
        """§11.3: a job with no description is scored from its title, not rejected."""
        job = Job(
            id=uuid4(),
            user_id=test_user.id,
            company_name="Acme",
            job_title="Senior Python Developer",
            job_description=None,
            status=JobStatus.APPLIED,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        response = client.post(f"/jobs/{job.id}/match-score")

        assert response.status_code == status.HTTP_200_OK, response.text
        data = response.json()
        assert "Python" in data["breakdown"]["hard_skills"]["matched_skills"]
        # Evidence ceiling: one skill is not grounds for "Excellent match"
        assert data["match_score"] <= 69
        assert data["notes"]


class TestGetMatchScore:
    """GET /jobs/{job_id}/match-score"""

    def test_returns_the_breakdown(self, client, scored_job, active_resume):
        response = client.get(f"/jobs/{scored_job.id}/match-score")

        assert response.status_code == status.HTTP_200_OK, response.text
        breakdown = response.json()["breakdown"]
        assert breakdown["hard_skills"]["matched_skills"]
        assert breakdown["experience"]["user_experience"] == "8 years"
        assert breakdown["experience"]["required_experience"] == "5 years"

    def test_does_not_write(self, client, db_session, scored_job, active_resume):
        """GET previews; only POST commits."""
        client.get(f"/jobs/{scored_job.id}/match-score")

        db_session.refresh(scored_job)
        assert scored_job.match_score is None

    def test_resume_id_query_parameter(self, client, scored_job, active_resume):
        response = client.get(
            f"/jobs/{scored_job.id}/match-score?resume_id={active_resume.id}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["resume_id"] == str(active_resume.id)

    def test_repeated_calls_agree(self, client, scored_job, active_resume):
        first = client.get(f"/jobs/{scored_job.id}/match-score").json()
        second = client.get(f"/jobs/{scored_job.id}/match-score").json()

        first.pop("calculated_at")
        second.pop("calculated_at")
        assert first == second


class TestMatchScoreErrors:
    """§5.5 error contract."""

    def test_no_resume_is_400(self, client, scored_job):
        response = client.post(f"/jobs/{scored_job.id}/match-score")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "resume" in response.json()["detail"].lower()

    def test_unknown_job_is_404(self, client, active_resume):
        response = client.post(f"/jobs/{uuid4()}/match-score")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unknown_resume_id_is_404(self, client, scored_job, active_resume):
        response = client.post(
            f"/jobs/{scored_job.id}/match-score", json={"resume_id": str(uuid4())}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_malformed_job_id_is_422(self, client, active_resume):
        response = client.post("/jobs/not-a-uuid/match-score")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_other_users_job_is_404_not_403(self, client, db_session, active_resume):
        """Reported as "not found" so the endpoint never confirms the id exists."""
        other_user = User(
            id=uuid4(), email=f"other_{uuid4().hex[:8]}@example.com",
            hashed_password="hash",
        )
        db_session.add(other_user)
        db_session.commit()

        job = Job(
            id=uuid4(),
            user_id=other_user.id,
            company_name="Other Co",
            job_title="Developer",
            job_description=JOB_DESCRIPTION,
            status=JobStatus.APPLIED,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert client.post(f"/jobs/{job.id}/match-score").status_code == 404
        assert client.get(f"/jobs/{job.id}/match-score").status_code == 404

    def test_other_users_resume_is_404(self, client, db_session, scored_job,
                                       active_resume):
        other_user = User(
            id=uuid4(), email=f"other_{uuid4().hex[:8]}@example.com",
            hashed_password="hash",
        )
        db_session.add(other_user)
        db_session.commit()

        their_resume = Resume(
            user_id=other_user.id, filename="theirs.pdf",
            extracted_text="Python developer", content_hash="d" * 64, is_active=True,
        )
        db_session.add(their_resume)
        db_session.commit()
        db_session.refresh(their_resume)

        response = client.post(
            f"/jobs/{scored_job.id}/match-score",
            json={"resume_id": str(their_resume.id)},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMatchScoreResponseShape:
    def test_internal_fields_are_not_exposed(self, client, scored_job, active_resume):
        """Component weights and parsed year figures are implementation detail."""
        breakdown = client.post(f"/jobs/{scored_job.id}/match-score").json()["breakdown"]

        for component in breakdown.values():
            assert "weight" not in component
        assert "user_years" not in breakdown["experience"]
        assert "required_years" not in breakdown["experience"]

    def test_reports_which_resume_and_algorithm_produced_it(
        self, client, scored_job, active_resume
    ):
        """`resume_version` is the content hash, so a stored score can be checked for
        staleness without diffing the text."""
        data = client.post(f"/jobs/{scored_job.id}/match-score").json()

        assert data["resume_version"] == active_resume.content_hash
        assert data["resume_filename"] == "cv.pdf"
        assert data["algorithm_version"]

    def test_unavailable_component_carries_a_reason(self, client, db_session, test_user,
                                                    active_resume):
        """§3.4: the UI must be able to explain a missing section, not show a blank."""
        job = Job(
            id=uuid4(), user_id=test_user.id, company_name="Acme",
            job_title="Engineer",
            job_description="Required: Python, Django, PostgreSQL and AWS.",
            status=JobStatus.APPLIED,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        breakdown = client.get(f"/jobs/{job.id}/match-score").json()["breakdown"]

        # No soft skills stated in the posting, so the component is excluded entirely
        assert breakdown["soft_skills"]["available"] is False
        assert breakdown["soft_skills"]["score"] is None
        assert breakdown["soft_skills"]["reason"]


class TestScoreRangeFilter:
    """GET /jobs/?min_score=&max_score= (§5.4)"""

    @pytest.fixture
    def jobs_with_scores(self, db_session, test_user):
        for name, score in [("High", 90), ("Middle", 60), ("Unscored", None)]:
            db_session.add(Job(
                id=uuid4(), user_id=test_user.id, company_name=name, job_title=name,
                status=JobStatus.APPLIED, match_score=score,
            ))
        db_session.commit()

    def test_min_score(self, client, jobs_with_scores):
        items = client.get("/jobs/?min_score=70").json()["items"]
        assert [j["company_name"] for j in items] == ["High"]

    def test_max_score(self, client, jobs_with_scores):
        items = client.get("/jobs/?max_score=70").json()["items"]
        assert [j["company_name"] for j in items] == ["Middle"]

    def test_range(self, client, jobs_with_scores):
        items = client.get("/jobs/?min_score=50&max_score=80").json()["items"]
        assert [j["company_name"] for j in items] == ["Middle"]

    def test_unscored_jobs_are_excluded(self, client, jobs_with_scores):
        """"Not yet scored" is not the same as "scored badly"."""
        items = client.get("/jobs/?min_score=0").json()["items"]
        assert "Unscored" not in [j["company_name"] for j in items]

    def test_no_filter_returns_everything(self, client, jobs_with_scores):
        assert client.get("/jobs/").json()["total"] == 3

    def test_total_reflects_the_filter(self, client, jobs_with_scores):
        assert client.get("/jobs/?min_score=70").json()["total"] == 1

    def test_combines_with_other_filters(self, client, db_session, test_user,
                                         jobs_with_scores):
        db_session.add(Job(
            id=uuid4(), user_id=test_user.id, company_name="High",
            job_title="Rejected role", status=JobStatus.REJECTED, match_score=95,
        ))
        db_session.commit()

        items = client.get("/jobs/?min_score=70&status=Applied").json()["items"]
        assert [j["job_title"] for j in items] == ["High"]

    @pytest.mark.parametrize("query", ["min_score=101", "min_score=-1", "max_score=101"])
    def test_out_of_range_is_422(self, client, query):
        assert client.get(f"/jobs/?{query}").status_code == 422
