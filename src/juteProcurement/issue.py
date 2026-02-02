"""
Jute Issue API endpoints.
Provides endpoints for viewing and managing jute issue records.
Jute issue records track yarn issued against MR line items.
"""

from fastapi import Depends, Request, HTTPException, APIRouter
from typing import Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.juteProcurement.query import (
    get_jute_issue_table_query,
    get_jute_issue_table_count_query,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/get_issue_table")
async def get_jute_issue_table(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get paginated list of jute issue records.
    
    Query params:
    - co_id: Company ID (required)
    - page: Page number (default: 1)
    - limit: Records per page (default: 10)
    - search: Search term (optional)
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
            limit = max(1, min(100, int(q_limit)))  # Cap at 100 records per page
        except ValueError:
            page = 1
            limit = 10

        offset = (page - 1) * limit
        search_param = f"%{q_search}%" if q_search else None

        # Get total count
        count_query = get_jute_issue_table_count_query(co_id, q_search)
        count_result = db.execute(
            count_query,
            {"co_id": co_id, "search": search_param} if search_param else {"co_id": co_id}
        ).fetchone()
        total = count_result.total if count_result else 0

        # Get paginated data
        data_query = get_jute_issue_table_query(co_id, q_search)
        params = {"co_id": co_id, "limit": limit, "offset": offset}
        if search_param:
            params["search"] = search_param
        
        rows = db.execute(data_query, params).fetchall()
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
        logger.error(f"Error fetching jute issue table: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching jute issue records: {str(e)}")


@router.get("/get_issue_by_id/{issue_id}")
async def get_jute_issue_by_id(
    issue_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get a single jute issue record by ID.
    
    Path params:
    - issue_id: The jute issue ID
    
    Query params:
    - co_id: Company ID (required)
    """
    try:
        q_co_id = request.query_params.get("co_id")
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        try:
            co_id = int(q_co_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid co_id")

        sql = text("""
            SELECT 
                ji.jute_issue_id,
                ji.branch_id,
                bm.branch_name,
                ji.issue_date,
                ji.status_id,
                COALESCE(sm.status_name, 'Draft') AS status,
                ji.issue_value,
                ji.jute_quality_id,
                jqm.jute_quality,
                ji.jute_mr_li_id,
                mrli.jute_mr_id,
                ji.yarn_type_id,
                jytm.jute_yarn_type_name AS yarn_type_name,
                ji.quantity,
                ji.weight,
                ji.unit_conversion,
                ji.updated_by,
                ji.update_date_time
            FROM jute_issue ji
            INNER JOIN branch_mst bm ON bm.branch_id = ji.branch_id
            LEFT JOIN status_mst sm ON sm.status_id = ji.status_id
            LEFT JOIN jute_quality_mst jqm ON jqm.jute_qlty_id = ji.jute_quality_id
            LEFT JOIN jute_mr_li mrli ON mrli.jute_mr_li_id = ji.jute_mr_li_id
            LEFT JOIN jute_yarn_type_mst jytm ON jytm.jute_yarn_type_id = ji.yarn_type_id
            WHERE ji.jute_issue_id = :issue_id
            AND bm.co_id = :co_id
        """)

        result = db.execute(sql, {"issue_id": issue_id, "co_id": co_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Jute issue record not found")

        return {"data": dict(result._mapping)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching jute issue by ID: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching jute issue record: {str(e)}")
