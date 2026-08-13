from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth import get_current_user
from app.schemas import DashboardStats
from app.services.dashboard_service import DEFAULT_RANGE, RANGE_WINDOWS, get_dashboard_stats

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    # `range` shadows the builtin, so the parameter is aliased rather than renamed
    range_key: str = Query(
        DEFAULT_RANGE,
        alias="range",
        pattern=f"^({'|'.join(RANGE_WINDOWS)})$",
        description="Window for recent activity and trend. Funnel and rates are always lifetime."
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aggregated statistics for the signed-in user's job hunt (US-07).

    Returns the whole dashboard in one response: pipeline funnel, conversion rates,
    recent activity, upcoming interviews and application trend. Four separate
    endpoints would mean four auth checks and four connection checkouts to draw one
    screen, and the widgets could disagree if data changed between calls.
    """
    return get_dashboard_stats(db, current_user.id, range_key)
