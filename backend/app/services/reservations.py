from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from app.core.database_pool import db_pool


async def _fetch_one(query: str, params: Dict[str, Any], db_session=None):
    from sqlalchemy import text

    if db_session is not None:
        result = await db_session.execute(text(query), params)
        return result.fetchone()

    if db_pool.session_factory is None:
        await db_pool.initialize()
    if db_pool.session_factory is None:
        raise RuntimeError("Database pool is not available")

    async with db_pool.get_session() as session:
        result = await session.execute(text(query), params)
        return result.fetchone()


async def calculate_monthly_revenue_summary(
    property_id: str,
    tenant_id: str,
    month: int,
    year: int,
    db_session=None,
) -> Dict[str, Any]:
    """
    Calculates revenue for a property's local calendar month.
    """
    start_date = datetime(year, month, 1)
    if month < 12:
        end_date = datetime(year, month + 1, 1)
    else:
        end_date = datetime(year + 1, 1, 1)

    query = """
        SELECT COALESCE(SUM(r.total_amount), 0) AS total_revenue,
               COUNT(*) AS reservation_count
        FROM reservations AS r
        JOIN properties AS p
          ON p.id = r.property_id AND p.tenant_id = r.tenant_id
        WHERE r.property_id = :property_id
          AND r.tenant_id = :tenant_id
          AND (r.check_in_date AT TIME ZONE p.timezone) >= :start_date
          AND (r.check_in_date AT TIME ZONE p.timezone) < :end_date
    """

    row = await _fetch_one(query, {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "start_date": start_date,
        "end_date": end_date,
    }, db_session)
    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "total": str(Decimal(str(row.total_revenue or 0))),
        "currency": "USD",
        "count": row.reservation_count,
    }


async def calculate_monthly_revenue(
    property_id: str,
    month: int,
    year: int,
    tenant_id: str,
    db_session=None,
) -> Decimal:
    """Return the exact revenue total for one tenant's local calendar month."""
    summary = await calculate_monthly_revenue_summary(
        property_id, tenant_id, month, year, db_session
    )
    return Decimal(summary["total"])

async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    query = """
        SELECT COALESCE(SUM(total_amount), 0) AS total_revenue,
               COUNT(*) AS reservation_count
        FROM reservations
        WHERE property_id = :property_id AND tenant_id = :tenant_id
    """
    row = await _fetch_one(query, {
        "property_id": property_id,
        "tenant_id": tenant_id,
    })
    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "total": str(Decimal(str(row.total_revenue or 0))),
        "currency": "USD",
        "count": row.reservation_count,
    }
