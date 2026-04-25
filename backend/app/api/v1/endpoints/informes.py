"""
Financial Reports endpoint.

GET /api/v1/users/{user_id}/reports

Returns computed financial metrics (balance, savings rate, avg daily
expense, top categories, ant expenses) over a configurable date range
(default: last 30 days).

All monetary values are calculated "al vuelo" — the balance is NEVER
read from a stored column.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.informes import InformesResponse
from app.services.informes_service import generar_informe_financiero

router = APIRouter(prefix="/users", tags=["informes"])


async def _resolve_user(public_id: str, db: AsyncSession) -> User:
    """Look up a user by public_id (8-char hex slug) or raise 404."""
    stmt = select(User).where(User.public_id == public_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get(
    "/{public_id}/reports",
    response_model=InformesResponse,
    summary="Financial report for a user",
    description=(
        "Returns balance, savings rate, average daily expense, top 3 "
        "expense categories, and ant-expense totals.  Defaults to the "
        "last 30 days when no dates are provided."
    ),
)
@limiter.limit("15/minute")
async def get_financial_report(
    request: Request,
    public_id: str,
    start_date: date | None = Query(
        None,
        description="Start of period (YYYY-MM-DD). Default: 30 days ago.",
    ),
    end_date: date | None = Query(
        None,
        description="End of period (YYYY-MM-DD). Default: today.",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute and return a full financial report.

    Validates that ``start_date <= end_date`` when both are provided,
    then delegates all heavy SQL to ``informes_service``.
    """
    # ── Validate date ordering ──────────────────────────────────
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date must be <= end_date",
        )

    # ── Resolve user by public_id → internal integer PK ─────────
    user = await _resolve_user(public_id, db)

    # ── Delegate to the service layer (uses integer user.id) ────
    report = await generar_informe_financiero(
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
        db=db,
    )

    return report
