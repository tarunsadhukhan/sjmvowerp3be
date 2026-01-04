from fastapi import Depends, Request, HTTPException, APIRouter
import logging
from sqlalchemy.orm import Session
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.juteProcurement.query import (
    get_jute_po_table_query,
    get_jute_po_table_count_query,
    get_jute_po_by_id_query,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/get_jute_po_table")
async def get_jute_po_table(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get paginated list of Jute Purchase Orders.
    
    Query params:
    - co_id: Company ID (required)
    - page: Page number (default: 1)
    - limit: Records per page (default: 10)
    - search: Search term for po_num, supplier_name, broker_name, or mukam
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
            limit = min(100, max(1, int(q_limit)))  # Clamp between 1 and 100
        except ValueError:
            page = 1
            limit = 10

        offset = (page - 1) * limit

        # Build search parameter
        search_param = f"%{q_search}%" if q_search else None

        # Get total count
        count_query = get_jute_po_table_count_query(co_id=co_id, search=q_search if q_search else None)
        count_params = {"co_id": co_id}
        if search_param:
            count_params["search"] = search_param

        count_result = db.execute(count_query, count_params).fetchone()
        total = count_result.total if count_result else 0

        # Get paginated data
        data_query = get_jute_po_table_query(co_id=co_id, search=q_search if q_search else None)
        data_params = {"co_id": co_id, "limit": limit, "offset": offset}
        if search_param:
            data_params["search"] = search_param

        result = db.execute(data_query, data_params).fetchall()
        rows = [dict(r._mapping) for r in result]

        # Format dates for JSON serialization
        for row in rows:
            if row.get("po_date"):
                row["po_date"] = str(row["po_date"])
            if row.get("updated_date_time"):
                row["updated_date_time"] = str(row["updated_date_time"])

        return {
            "data": rows,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if limit > 0 else 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching Jute PO table")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_jute_po_by_id/{jute_po_id}")
async def get_jute_po_by_id(
    jute_po_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get a single Jute PO by ID.
    
    Path params:
    - jute_po_id: Jute PO ID
    
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

        query = get_jute_po_by_id_query()
        result = db.execute(query, {"jute_po_id": jute_po_id, "co_id": co_id}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Jute PO not found")

        row = dict(result._mapping)

        # Format dates for JSON serialization
        if row.get("po_date"):
            row["po_date"] = str(row["po_date"])
        if row.get("updated_date_time"):
            row["updated_date_time"] = str(row["updated_date_time"])
        if row.get("mod_on"):
            row["mod_on"] = str(row["mod_on"])
        if row.get("contract_date"):
            row["contract_date"] = str(row["contract_date"])

        return row

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching Jute PO by ID")
        raise HTTPException(status_code=500, detail=str(e))
