"""
Jute Material Receipt (MR) API endpoints.
Provides endpoints for viewing and managing jute MR records.
"""

from fastapi import Depends, Request, HTTPException, APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.juteProcurement.query import (
    get_jute_mr_table_query,
    get_jute_mr_table_count_query,
    get_jute_mr_by_id_query,
    get_jute_mr_line_items_query,
    get_all_active_company_branches_query,
    get_agent_map_options_query,
    get_warehouse_options_query,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class MRLineItemUpdate(BaseModel):
    """Model for updating a jute_mr_li record."""
    jute_mr_li_id: int
    actual_item_id: Optional[int] = None
    actual_quality: Optional[int] = None
    actual_qty: Optional[float] = None
    actual_weight: Optional[float] = None
    allowable_moisture: Optional[float] = None
    actual_moisture: Optional[str] = None
    claim_dust: Optional[float] = None
    shortage_kgs: Optional[int] = None
    accepted_weight: Optional[float] = None
    rate: Optional[float] = None
    claim_rate: Optional[float] = None
    claim_quality: Optional[str] = None
    water_damage_amount: Optional[float] = None
    premium_amount: Optional[float] = None
    remarks: Optional[str] = None
    warehouse_id: Optional[int] = None


class MRUpdateRequest(BaseModel):
    """Request model for updating MR header and line items."""
    mr_weight: Optional[float] = None
    party_branch_id: Optional[int] = None
    remarks: Optional[str] = None
    src_com_id: Optional[int] = None
    line_items: List[MRLineItemUpdate] = []


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/get_mr_table")
async def get_jute_mr_table(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get paginated list of jute MR records.
    
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
            limit = min(100, max(1, int(q_limit)))
        except ValueError:
            page = 1
            limit = 10

        offset = (page - 1) * limit

        # Build search parameter
        search_param = f"%{q_search}%" if q_search else None

        # Get total count
        count_query = get_jute_mr_table_count_query(co_id=co_id, search=q_search if q_search else None)
        count_params = {"co_id": co_id}
        if search_param:
            count_params["search"] = search_param

        count_result = db.execute(count_query, count_params).fetchone()
        total = count_result.total if count_result else 0

        # Get paginated data
        data_query = get_jute_mr_table_query(co_id=co_id, search=q_search if q_search else None)
        data_params = {"co_id": co_id, "limit": limit, "offset": offset}
        if search_param:
            data_params["search"] = search_param

        result = db.execute(data_query, data_params).fetchall()
        rows = [dict(r._mapping) for r in result]

        # Format dates for JSON serialization
        for row in rows:
            for field in ["jute_mr_date", "challan_date", "po_date", "jute_gate_entry_date", "updated_date_time"]:
                if row.get(field):
                    dt = row[field]
                    if isinstance(dt, (datetime, date)):
                        row[field] = str(dt) if isinstance(dt, date) else dt.isoformat()

        return {
            "data": rows,
            "total": total,
            "page": page,
            "page_size": limit,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching jute MR table")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_agent_options")
async def get_agent_options(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get agent options from jute_agent_map table.
    Returns agent branches that have been mapped for the current company.
    """
    try:
        q_co_id = request.query_params.get("co_id")
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        try:
            co_id = int(q_co_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid co_id")

        query = get_agent_map_options_query()
        result = db.execute(query, {"co_id": co_id}).fetchall()
        branches = [dict(r._mapping) for r in result]

        return {
            "branches": branches,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching agent options")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_warehouse_options")
async def get_warehouse_options(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get warehouse options for a specific branch.
    Returns warehouses with hierarchical path (e.g., 'Main-Section A-Bin 1').
    """
    try:
        q_branch_id = request.query_params.get("branch_id")
        if not q_branch_id:
            raise HTTPException(status_code=400, detail="branch_id is required")
        
        try:
            branch_id = int(q_branch_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid branch_id")

        query = get_warehouse_options_query()
        result = db.execute(query, {"branch_id": branch_id}).fetchall()
        warehouses = [dict(r._mapping) for r in result]

        return {
            "warehouses": warehouses,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching warehouse options")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_party_branches")
async def get_party_branches(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get party branches for a specific party.
    Returns party branches with address info for the dropdown.
    Used in MR edit to select party branch (mandatory field).
    
    Query params:
    - party_id: Party ID (required)
    """
    try:
        q_party_id = request.query_params.get("party_id")
        if not q_party_id:
            raise HTTPException(status_code=400, detail="party_id is required")
        
        try:
            party_id = int(q_party_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid party_id")

        query = text("""
            SELECT 
                pbm.party_mst_branch_id,
                pbm.party_id,
                pbm.address,
                pbm.gst_no,
                pm.supp_name AS party_name,
                CONCAT(COALESCE(pm.supp_name, ''), ' - ', COALESCE(pbm.address, '')) AS display
            FROM party_branch_mst pbm
            LEFT JOIN party_mst pm ON pm.party_id = pbm.party_id
            WHERE pbm.party_id = :party_id
                AND pbm.active = 1
            ORDER BY pbm.address
        """)
        result = db.execute(query, {"party_id": party_id}).fetchall()
        branches = [dict(r._mapping) for r in result]

        return {
            "branches": branches,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching party branches")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_mr_by_id")
async def get_jute_mr_by_id(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get a single jute MR with line items.
    
    Query params:
    - id: MR ID (required)
    """
    try:
        q_id = request.query_params.get("id")
        if not q_id:
            raise HTTPException(status_code=400, detail="id is required")
        
        try:
            mr_id = int(q_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid id")

        # Get header data
        header_query = get_jute_mr_by_id_query()
        header_result = db.execute(header_query, {"mr_id": mr_id}).fetchone()
        
        if not header_result:
            raise HTTPException(status_code=404, detail="MR not found")

        header = dict(header_result._mapping)

        # Format dates
        for field in ["jute_mr_date", "challan_date", "po_date", "jute_gate_entry_date", "updated_date_time"]:
            if header.get(field):
                dt = header[field]
                if isinstance(dt, (datetime, date)):
                    header[field] = str(dt) if isinstance(dt, date) else dt.isoformat()

        # Get line items
        line_items_query = get_jute_mr_line_items_query()
        line_items_result = db.execute(line_items_query, {"mr_id": mr_id}).fetchall()
        line_items = [dict(r._mapping) for r in line_items_result]

        return {
            "header": header,
            "line_items": line_items,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching jute MR by ID")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update_mr/{mr_id}")
async def update_jute_mr(
    mr_id: int,
    request: Request,
    body: MRUpdateRequest,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Update jute MR header and line items.
    Recalculates accepted_weight for each line item and updates mr_weight as sum of accepted weights.
    """
    try:
        q_co_id = request.query_params.get("co_id")
        if not q_co_id:
            raise HTTPException(status_code=400, detail="co_id is required")
        
        try:
            co_id = int(q_co_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid co_id")

        # Verify MR exists
        header_query = get_jute_mr_by_id_query()
        header_result = db.execute(header_query, {"mr_id": mr_id}).fetchone()
        
        if not header_result:
            raise HTTPException(status_code=404, detail="MR not found")

        # Get user info for audit
        user_id = token_data.get("user_id")
        now = datetime.now()

        # Update line items and calculate accepted weights
        total_accepted_weight = 0.0
        
        for item in body.line_items:
            # Calculate shortage_kgs and accepted_weight
            actual_weight = float(item.actual_weight or 0.0)
            allowable_moisture = float(item.allowable_moisture) if item.allowable_moisture is not None else None
            actual_moisture_str = item.actual_moisture or "0"
            try:
                actual_moisture = float(actual_moisture_str)
            except (ValueError, TypeError):
                actual_moisture = 0.0
            
            claim_dust = float(item.claim_dust) if item.claim_dust is not None else 0.0
            
            # Calculate shortage_kgs first
            shortage_kgs = 0.0
            accepted_weight = actual_weight
            
            if actual_weight > 0:
                moisture_diff = 0.0
                if allowable_moisture is not None and actual_moisture > allowable_moisture:
                    moisture_diff = actual_moisture - allowable_moisture
                
                deduction_percentage = moisture_diff + claim_dust
                if deduction_percentage > 0:
                    # Formula: shortage_kgs = actual_weight * (moisture diff % + claim_dust%)
                    shortage_kgs = actual_weight * deduction_percentage / 100.0
                    # Formula: accepted_weight = actual_weight - shortage_kgs
                    accepted_weight = actual_weight - shortage_kgs
                    accepted_weight = max(0.0, accepted_weight)  # Ensure non-negative
                
                total_accepted_weight += accepted_weight
            
            # Update line item
            update_query = text("""
                UPDATE jute_mr_li
                SET actual_item_id = :actual_item_id,
                    actual_quality = :actual_quality,
                    actual_qty = :actual_qty,
                    actual_weight = :actual_weight,
                    allowable_moisture = :allowable_moisture,
                    actual_moisture = :actual_moisture,
                    claim_dust = :claim_dust,
                    shortage_kgs = :shortage_kgs,
                    accepted_weight = :accepted_weight,
                    rate = :rate,
                    claim_rate = :claim_rate,
                    claim_quality = :claim_quality,
                    water_damage_amount = :water_damage_amount,
                    premium_amount = :premium_amount,
                    remarks = :remarks,
                    warehouse_id = :warehouse_id,
                    updated_date_time = :updated_date_time
                WHERE jute_mr_li_id = :jute_mr_li_id
            """)
            
            db.execute(update_query, {
                "jute_mr_li_id": item.jute_mr_li_id,
                "actual_item_id": item.actual_item_id,
                "actual_quality": item.actual_quality,
                "actual_qty": item.actual_qty,
                "actual_weight": item.actual_weight,
                "allowable_moisture": item.allowable_moisture,
                "actual_moisture": item.actual_moisture,
                "claim_dust": item.claim_dust,
                "shortage_kgs": shortage_kgs,
                "accepted_weight": accepted_weight,
                "rate": item.rate,
                "claim_rate": item.claim_rate,
                "claim_quality": item.claim_quality,
                "water_damage_amount": item.water_damage_amount,
                "premium_amount": item.premium_amount,
                "remarks": item.remarks,
                "warehouse_id": item.warehouse_id,
                "updated_date_time": now,
            })

        # Update MR header with calculated weight
        mr_weight = body.mr_weight if body.mr_weight is not None else total_accepted_weight
        
        update_header_query = text("""
            UPDATE jute_mr
            SET mr_weight = :mr_weight,
                party_branch_id = :party_branch_id,
                remarks = :remarks,
                src_com_id = :src_com_id,
                updated_by = :updated_by,
                updated_date_time = :updated_date_time
            WHERE jute_mr_id = :mr_id
        """)
        
        db.execute(update_header_query, {
            "mr_id": mr_id,
            "mr_weight": mr_weight,
            "party_branch_id": body.party_branch_id,
            "remarks": body.remarks,
            "src_com_id": body.src_com_id,
            "updated_by": user_id,
            "updated_date_time": now,
        })

        db.commit()

        return {
            "success": True,
            "message": "MR updated successfully",
            "mr_id": mr_id,
            "mr_weight": mr_weight,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error updating jute MR")
        raise HTTPException(status_code=500, detail=str(e))
