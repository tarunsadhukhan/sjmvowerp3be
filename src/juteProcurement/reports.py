"""
Jute Procurement Report endpoints.
Provides endpoints for jute stock and related reports.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.juteProcurement.reportQueries import (
    get_jute_stock_report_query,
    get_batch_cost_report_query,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stock")
async def get_jute_stock_report(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get daily jute stock position report for a given branch and date.

    Returns opening stock, receipt, issue, closing stock, and MTD receipt/issue
    grouped by item group and item.

    Query params:
    - branch_id: Branch ID (required)
    - date: Report date in YYYY-MM-DD format (required)
    """
    try:
        q_branch_id = request.query_params.get("branch_id")
        q_date = request.query_params.get("date")

        if not q_branch_id:
            raise HTTPException(status_code=400, detail="branch_id is required")
        if not q_date:
            raise HTTPException(status_code=400, detail="date is required")

        try:
            branch_id = int(q_branch_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid branch_id")

        query = get_jute_stock_report_query()
        rows = db.execute(query, {
            "branch_id": branch_id,
            "report_date": q_date,
        }).fetchall()

        data = [dict(r._mapping) for r in rows]

        return {"data": data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching jute stock report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching jute stock report: {str(e)}",
        )


@router.get("/batch-cost")
async def get_batch_cost_report(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get batch cost report: yarn quality-wise planned vs actual jute issue.

    Compares planned issue (from batch daily assignments + batch plan percentages)
    against actual issue for a given branch and date. Returns planned weight,
    actual weight, average rate, issue value, and variance per quality.

    Query params:
    - branch_id: Branch ID (required)
    - date: Report date in YYYY-MM-DD format (required)
    """
    try:
        q_branch_id = request.query_params.get("branch_id")
        q_date = request.query_params.get("date")

        if not q_branch_id:
            raise HTTPException(status_code=400, detail="branch_id is required")
        if not q_date:
            raise HTTPException(status_code=400, detail="date is required")

        try:
            branch_id = int(q_branch_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid branch_id")

        query = get_batch_cost_report_query()
        rows = db.execute(query, {
            "branch_id": branch_id,
            "report_date": q_date,
        }).fetchall()

        data = [dict(r._mapping) for r in rows]

        return {"data": data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching batch cost report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching batch cost report: {str(e)}",
        )
