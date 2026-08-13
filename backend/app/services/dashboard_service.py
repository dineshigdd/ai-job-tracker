"""Aggregation queries behind GET /dashboard/stats (US-07).

Everything here aggregates in the database and returns scalars or small row sets.
Loading Job rows to count them in Python would drag every job_description and
ai_cover_letter blob across the wire just to produce an integer.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models import (
    Job, JobStatus, JobStatusEvent, STATUS_ORDER, SUBMITTED_STATUSES,
)

logger = logging.getLogger(__name__)

# range -> window in days. None means "all time".
RANGE_WINDOWS = {"30d": 30, "90d": 90, "1y": 365, "all": None}
DEFAULT_RANGE = "90d"

RECENT_ACTIVITY_LIMIT = 10
UPCOMING_INTERVIEW_LIMIT = 5

SUBMITTED_VALUES = [s.value for s in SUBMITTED_STATUSES]


def _window_start(range_key: str, now: datetime) -> Optional[datetime]:
    days = RANGE_WINDOWS[range_key]
    return None if days is None else now - timedelta(days=days)


def _bucket_for(range_key: str) -> str:
    """Weekly buckets read well up to a quarter; beyond that they get too noisy."""
    return "week" if range_key in ("30d", "90d") else "month"


def _bucket_start(moment: datetime, bucket: str) -> date:
    d = moment.date()
    if bucket == "month":
        return d.replace(day=1)
    return d - timedelta(days=d.weekday())  # Monday, matching date_trunc('week')


def _next_bucket(current: date, bucket: str) -> date:
    if bucket == "month":
        return (current.replace(day=28) + timedelta(days=4)).replace(day=1)
    return current + timedelta(days=7)


def _funnel(db: Session, user_id) -> dict:
    """Sub-feature 1: counts per pipeline stage."""
    rows = (
        db.query(Job.status, func.count())
        .filter(Job.user_id == user_id)
        .group_by(Job.status)
        .all()
    )

    # Zero-fill: SQL returns no row for a status with no jobs, and a missing key
    # would render as a gap in the funnel rather than a stage with nothing in it
    counts = {s.value: 0 for s in STATUS_ORDER}
    for status_value, count in rows:
        if status_value not in counts:
            # Only reachable on rows predating the CHECK constraint. Keep them in
            # the payload so the totals still reconcile, but make the noise visible.
            logger.warning("Job status %r is not a known JobStatus", status_value)
        counts[status_value] = counts.get(status_value, 0) + count

    return counts


def _ever_reached(db: Session, user_id) -> dict:
    """How many distinct jobs ever hit each status, from the event log.

    This is what makes conversion rates correct: a job that went
    Applied -> Interviewing -> Rejected sits in Rejected today, so counting
    current status would report zero interviews for someone who interviewed.
    """
    rows = (
        db.query(JobStatusEvent.to_status, func.count(distinct(JobStatusEvent.job_id)))
        .filter(JobStatusEvent.user_id == user_id)
        .group_by(JobStatusEvent.to_status)
        .all()
    )
    return dict(rows)


def _responded_count(db: Session, user_id) -> int:
    """Jobs that moved out of Applied in any direction."""
    return (
        db.query(func.count(distinct(JobStatusEvent.job_id)))
        .filter(
            JobStatusEvent.user_id == user_id,
            JobStatusEvent.from_status == JobStatus.APPLIED.value,
        )
        .scalar()
    ) or 0


def _recent_activity(db: Session, user_id, since: Optional[datetime]) -> list:
    """Sub-feature 3a: the most recent status transitions."""
    query = (
        db.query(
            JobStatusEvent.job_id,
            JobStatusEvent.from_status,
            JobStatusEvent.to_status,
            JobStatusEvent.changed_at,
            Job.company_name,
            Job.job_title,
        )
        .join(Job, JobStatusEvent.job_id == Job.id)
        .filter(JobStatusEvent.user_id == user_id)
    )
    if since is not None:
        query = query.filter(JobStatusEvent.changed_at >= since)

    rows = query.order_by(JobStatusEvent.changed_at.desc()).limit(RECENT_ACTIVITY_LIMIT).all()

    return [
        {
            "type": "status_change",
            "job_id": row.job_id,
            "company_name": row.company_name,
            "job_title": row.job_title,
            "from_status": row.from_status,
            "to_status": row.to_status,
            "occurred_at": row.changed_at,
        }
        for row in rows
    ]


def _upcoming_interviews(db: Session, user_id, now: datetime) -> list:
    """Sub-feature 3b. Rejected jobs are excluded: an interview that was scheduled
    before the rejection landed is not something to go and prepare for."""
    rows = (
        db.query(Job.id, Job.company_name, Job.job_title, Job.interview_date)
        .filter(
            Job.user_id == user_id,
            Job.interview_date.isnot(None),
            Job.interview_date > now,
            Job.status != JobStatus.REJECTED.value,
        )
        .order_by(Job.interview_date.asc())
        .limit(UPCOMING_INTERVIEW_LIMIT)
        .all()
    )
    return [
        {
            "job_id": row.id,
            "company_name": row.company_name,
            "job_title": row.job_title,
            "interview_date": row.interview_date,
        }
        for row in rows
    ]


def _trend(db: Session, user_id, bucket: str, since: Optional[datetime], now: datetime) -> list:
    """Sub-feature 4: applications submitted per period.

    Buckets on the date a job was first *submitted* (its earliest non-Wishlist
    event), not on created_at — a job can sit in Wishlist for weeks before it is
    actually sent, and dating it by row creation would credit the wrong period.
    """
    first_submitted = (
        db.query(
            JobStatusEvent.job_id.label("job_id"),
            func.min(JobStatusEvent.changed_at).label("submitted_at"),
        )
        .filter(
            JobStatusEvent.user_id == user_id,
            JobStatusEvent.to_status.in_(SUBMITTED_VALUES),
        )
        .group_by(JobStatusEvent.job_id)
        .subquery()
    )

    # Bucket in UTC explicitly. date_trunc on a timestamptz otherwise follows the
    # session TimeZone, so the same data could land in different weeks per client.
    period = func.date_trunc(
        bucket, func.timezone("UTC", first_submitted.c.submitted_at)
    ).label("period")

    query = db.query(period, func.count()).group_by(period)
    if since is not None:
        query = query.filter(first_submitted.c.submitted_at >= since)

    rows = query.order_by(period).all()
    by_period = {_bucket_start(p, bucket): n for p, n in rows}

    if not by_period:
        return []

    # Zero-fill every bucket in the window; a period with no applications is a
    # meaningful zero, and skipping it would draw a misleadingly continuous line
    start = _bucket_start(since, bucket) if since is not None else min(by_period)
    start = min(start, min(by_period))
    end = _bucket_start(now, bucket)

    points = []
    current = start
    while current <= end:
        points.append({"period_start": current, "applications": by_period.get(current, 0)})
        current = _next_bucket(current, bucket)
    return points


def get_dashboard_stats(db: Session, user_id, range_key: str = DEFAULT_RANGE) -> dict:
    now = datetime.now(timezone.utc)
    since = _window_start(range_key, now)
    bucket = _bucket_for(range_key)

    counts = _funnel(db, user_id)
    ever = _ever_reached(db, user_id)

    # Denominator for every rate: jobs that were actually submitted. Wishlist
    # entries were never sent anywhere, so including them would deflate all rates.
    total_applications = (
        db.query(func.count(distinct(JobStatusEvent.job_id)))
        .filter(
            JobStatusEvent.user_id == user_id,
            JobStatusEvent.to_status.in_(SUBMITTED_VALUES),
        )
        .scalar()
    ) or 0

    def rate(n: int) -> Optional[float]:
        # None, never 0.0 — a new user has no rate, they have not failed to convert
        if not total_applications:
            return None
        return round(n / total_applications, 4)

    return {
        "generated_at": now,
        "range": range_key,
        "funnel": {
            "counts": counts,
            "total_tracked": sum(counts.values()),
            "total_applications": total_applications,
        },
        "rates": {
            "interview_rate": rate(ever.get(JobStatus.INTERVIEWING.value, 0)),
            "offer_rate": rate(ever.get(JobStatus.OFFER.value, 0)),
            "response_rate": rate(_responded_count(db, user_id)),
        },
        "recent_activity": _recent_activity(db, user_id, since),
        "upcoming_interviews": _upcoming_interviews(db, user_id, now),
        "trend": {"bucket": bucket, "points": _trend(db, user_id, bucket, since, now)},
    }
