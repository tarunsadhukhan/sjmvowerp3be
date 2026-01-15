"""
Jute Bill Pass API endpoints.
Bill Pass is a view of approved Jute Material Receipts (MRs) with invoice details.
This module provides endpoints for viewing bill pass records from the jute_mr table.
"""

from fastapi import Depends, Request, HTTPException, APIRouter
from typing import Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.juteProcurement.query import (
    get_jute_bill_pass_table_query,
    get_jute_bill_pass_table_count_query,
    get_jute_bill_pass_by_id_query,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# CONSTANTS
# =============================================================================

STATUS_APPROVED = 3


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/get_bill_pass_list")
async def get_jute_bill_pass_list(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get paginated list of jute bill pass records.
    Bill passes are approved MRs (status_id = 3) with bill_pass_no assigned.
    
    Query params:
    - co_id: Company ID (required)
    - page: Page number (default: 1)
    - limit: Records per page (default: 10)
    - search: Search term
    """
    try:
        # Get query parameters
        q_co_id = request.query_params.get("co_id")
        q_page = request.query_params.get("page", "1")
        q_limit = request.query_params.get("limit", "10")
        q_search = request.query_params.get("search", "").strip()

        # Validate co_id
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        try:
            co_id = int(q_co_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid co_id")

        # Parse pagination
        try:
            page = max(1, int(q_page))
            limit = max(1, min(100, int(q_limit)))
        except ValueError:
            page = 1
            limit = 10

        offset = (page - 1) * limit

        # Build search param
        search_param = f"%{q_search}%" if q_search else None

        # Get total count
        count_query = get_jute_bill_pass_table_count_query(co_id, q_search)
        count_params = {"co_id": co_id}
        if search_param:
            count_params["search"] = search_param

        count_result = db.execute(count_query, count_params).fetchone()
        total = count_result[0] if count_result else 0

        # Get data
        data_query = get_jute_bill_pass_table_query(co_id, q_search)
        data_params = {
            "co_id": co_id,
            "limit": limit,
            "offset": offset,
        }
        if search_param:
            data_params["search"] = search_param

        rows = db.execute(data_query, data_params).fetchall()
        data = [dict(r._mapping) for r in rows]

        return {
            "data": data,
            "total": total,
            "page": page,
            "page_size": limit,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching jute bill pass list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_bill_pass_by_id")
async def get_jute_bill_pass_by_id(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get a single jute bill pass (approved MR) by ID.
    
    Query params:
    - co_id: Company ID (required)
    - id: Bill Pass / MR ID (required)
    """
    try:
        # Get query parameters
        q_co_id = request.query_params.get("co_id")
        q_id = request.query_params.get("id")

        # Validate required params
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        if not q_id:
            raise HTTPException(status_code=400, detail="id is required")

        try:
            co_id = int(q_co_id)
            mr_id = int(q_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid co_id or id")

        # Get bill pass details
        query = get_jute_bill_pass_by_id_query()
        result = db.execute(query, {"co_id": co_id, "jute_mr_id": mr_id}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Bill pass not found")

        return dict(result._mapping)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching jute bill pass by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))
