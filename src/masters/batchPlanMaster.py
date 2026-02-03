"""
Batch Plan Master API endpoints.
Provides CRUD operations for jute batch plan master data.

Schema (jute_batch_plan):
- batch_plan_id: bigint (PK, auto)
- branch_id: int (nullable)
- plan_name: str(255) (nullable)
- updated_by: bigint
- updated_date_time: datetime

Schema (jute_batch_plan_li):
- batch_plan_li_id: bigint (PK, auto)
- batch_plan_id: bigint (FK to jute_batch_plan)
- jute_quality_id: int (FK to jute_quality_mst)
- percentage: double (nullable)
- updated_by: bigint
- updated_date_time: datetime
"""

from fastapi import Depends, Request, HTTPException, APIRouter, Response
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.models.jute import JuteBatchPlan, JuteBatchPlanLi
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class BatchPlanLineItem(BaseModel):
    """Line item for batch plan - quality and percentage."""
    jute_quality_id: int
    percentage: float
    item_id: Optional[int] = None  # For reference, not stored in line item


class BatchPlanCreate(BaseModel):
    """Request body for creating/updating a batch plan."""
    plan_name: str
    branch_id: Optional[int] = None
    line_items: List[BatchPlanLineItem]


# =============================================================================
# QUERY FUNCTIONS
# =============================================================================

def get_batch_plan_list_query():
    """
    Get all batch plans for a branch with line item count and branch name.
    """
    return text("""
        SELECT 
            bp.batch_plan_id,
            bp.plan_name,
            bp.branch_id,
            bm.branch_name,
            bp.updated_by,
            bp.updated_date_time,
            COUNT(bpli.batch_plan_li_id) AS line_item_count
        FROM jute_batch_plan bp
        LEFT JOIN jute_batch_plan_li bpli ON bp.batch_plan_id = bpli.batch_plan_id
        LEFT JOIN branch_mst bm ON bp.branch_id = bm.branch_id
        WHERE bp.branch_id = :branch_id
        GROUP BY bp.batch_plan_id, bp.plan_name, bp.branch_id, bm.branch_name, bp.updated_by, bp.updated_date_time
        ORDER BY bp.batch_plan_id DESC
    """)


def get_batch_plan_list_with_search_query():
    """
    Get all batch plans with search filter and branch name.
    """
    return text("""
        SELECT 
            bp.batch_plan_id,
            bp.plan_name,
            bp.branch_id,
            bm.branch_name,
            bp.updated_by,
            bp.updated_date_time,
            COUNT(bpli.batch_plan_li_id) AS line_item_count
        FROM jute_batch_plan bp
        LEFT JOIN jute_batch_plan_li bpli ON bp.batch_plan_id = bpli.batch_plan_id
        LEFT JOIN branch_mst bm ON bp.branch_id = bm.branch_id
        WHERE bp.branch_id = :branch_id
          AND bp.plan_name LIKE :search
        GROUP BY bp.batch_plan_id, bp.plan_name, bp.branch_id, bm.branch_name, bp.updated_by, bp.updated_date_time
        ORDER BY bp.batch_plan_id DESC
    """)


def get_batch_plan_detail_query():
    """
    Get batch plan with line items detail.
    """
    return text("""
        SELECT 
            bp.batch_plan_id,
            bp.plan_name,
            bp.branch_id,
            bp.updated_by,
            bp.updated_date_time
        FROM jute_batch_plan bp
        WHERE bp.batch_plan_id = :batch_plan_id
          AND bp.branch_id = :branch_id
    """)


def get_batch_plan_line_items_query():
    """
    Get line items for a batch plan with quality and item names.
    """
    return text("""
        SELECT 
            bpli.batch_plan_li_id,
            bpli.batch_plan_id,
            bpli.jute_quality_id,
            bpli.percentage,
            jqm.jute_quality,
            jqm.item_id,
            im.item_name
        FROM jute_batch_plan_li bpli
        LEFT JOIN jute_quality_mst jqm ON bpli.jute_quality_id = jqm.jute_qlty_id
        LEFT JOIN item_mst im ON jqm.item_id = im.item_id
        WHERE bpli.batch_plan_id = :batch_plan_id
        ORDER BY bpli.batch_plan_li_id
    """)


def get_jute_items_query():
    """
    Get all items belonging to item groups with item_type_id = 2 (Jute type) for a company.
    Filters by co_id through item_grp_mst join.
    """
    return text("""
        SELECT 
            im.item_id,
            im.item_name,
            im.item_code,
            ig.item_grp_name
        FROM item_mst im
        INNER JOIN item_grp_mst ig ON im.item_grp_id = ig.item_grp_id
        WHERE ig.co_id = :co_id
          AND ig.item_type_id = 2
          AND im.active = 1
        ORDER BY im.item_name
    """)


def get_quality_for_item_query():
    """
    Get jute qualities for a specific item and company.
    """
    return text("""
        SELECT 
            jqm.jute_qlty_id AS jute_quality_id,
            jqm.jute_quality,
            jqm.item_id
        FROM jute_quality_mst jqm
        WHERE jqm.item_id = :item_id
          AND jqm.co_id = :co_id
        ORDER BY jqm.jute_quality
    """)


def check_duplicate_plan_name_query():
    """
    Check if a batch plan with the same name exists for the branch.
    """
    return text("""
        SELECT COUNT(*) as cnt
        FROM jute_batch_plan
        WHERE plan_name = :plan_name
          AND branch_id = :branch_id
          AND (:batch_plan_id IS NULL OR batch_plan_id != :batch_plan_id)
    """)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/get_batch_plan_table")
async def get_batch_plan_table(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
    search: str = None,
    page: int = 1,
    limit: int = 10,
):
    """
    Get paginated list of batch plans for the current branch.
    """
    try:
        branch_id = request.query_params.get("branch_id")
        if not branch_id:
            raise HTTPException(status_code=400, detail="Branch ID (branch_id) is required")

        # Prepare search parameter for LIKE if provided
        search_param = f"%{search}%" if search else None

        # Choose query based on search
        if search_param:
            query = get_batch_plan_list_with_search_query()
            params = {"branch_id": int(branch_id), "search": search_param}
        else:
            query = get_batch_plan_list_query()
            params = {"branch_id": int(branch_id)}

        result = db.execute(query, params).fetchall()
        all_data = [dict(row._mapping) for row in result]

        # Calculate pagination
        total = len(all_data)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_data = all_data[start_idx:end_idx]

        return {
            "data": paginated_data,
            "total": total,
            "page": page,
            "limit": limit,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_batch_plan_by_id/{batch_plan_id}")
async def get_batch_plan_by_id(
    batch_plan_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get a single batch plan with its line items.
    """
    try:
        branch_id = request.query_params.get("branch_id")
        if not branch_id:
            raise HTTPException(status_code=400, detail="Branch ID (branch_id) is required")

        # Get batch plan header
        query = get_batch_plan_detail_query()
        result = db.execute(query, {
            "batch_plan_id": batch_plan_id,
            "branch_id": int(branch_id)
        }).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Batch plan not found")

        batch_plan = dict(result._mapping)

        # Get line items
        line_items_query = get_batch_plan_line_items_query()
        line_items_result = db.execute(line_items_query, {"batch_plan_id": batch_plan_id}).fetchall()
        line_items = [dict(row._mapping) for row in line_items_result]

        batch_plan["line_items"] = line_items

        return {"data": batch_plan}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch_plan_create_setup")
async def batch_plan_create_setup(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get setup data for creating a new batch plan.
    Returns list of jute items (item_type = 2).
    """
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        # Get jute items (item_type = 2) for this company
        items_query = get_jute_items_query()
        items_result = db.execute(items_query, {"co_id": int(co_id)}).fetchall()
        items = [dict(row._mapping) for row in items_result]

        return {
            "items": items,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch_plan_edit_setup/{batch_plan_id}")
async def batch_plan_edit_setup(
    batch_plan_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get setup data for editing a batch plan.
    Returns jute items and existing batch plan details.
    """
    try:
        co_id = request.query_params.get("co_id")
        branch_id = request.query_params.get("branch_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")
        if not branch_id:
            raise HTTPException(status_code=400, detail="Branch ID (branch_id) is required")

        # Get jute items (item_type = 2) for this company
        items_query = get_jute_items_query()
        items_result = db.execute(items_query, {"co_id": int(co_id)}).fetchall()
        items = [dict(row._mapping) for row in items_result]

        # Get batch plan details
        query = get_batch_plan_detail_query()
        result = db.execute(query, {
            "batch_plan_id": batch_plan_id,
            "branch_id": int(branch_id)
        }).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Batch plan not found")

        batch_plan = dict(result._mapping)

        # Get line items
        line_items_query = get_batch_plan_line_items_query()
        line_items_result = db.execute(line_items_query, {"batch_plan_id": batch_plan_id}).fetchall()
        line_items = [dict(row._mapping) for row in line_items_result]

        return {
            "items": items,
            "batch_plan_details": batch_plan,
            "line_items": line_items,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_qualities_for_item/{item_id}")
async def get_qualities_for_item(
    item_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get jute qualities for a specific item and company.
    Called when user selects an item in the line item grid.
    """
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        query = get_quality_for_item_query()
        result = db.execute(query, {"item_id": item_id, "co_id": int(co_id)}).fetchall()
        qualities = [dict(row._mapping) for row in result]

        return {"qualities": qualities}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch_plan_create")
async def batch_plan_create(
    payload: BatchPlanCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Create a new batch plan with line items.
    """
    try:
        branch_id = request.query_params.get("branch_id")
        if not branch_id:
            raise HTTPException(status_code=400, detail="Branch ID (branch_id) is required")

        # Validate
        if not payload.plan_name or not payload.plan_name.strip():
            raise HTTPException(status_code=400, detail="Plan name is required")
        
        if not payload.line_items or len(payload.line_items) == 0:
            raise HTTPException(status_code=400, detail="At least one line item is required")

        # Check for duplicate plan name
        duplicate_check = db.execute(check_duplicate_plan_name_query(), {
            "plan_name": payload.plan_name.strip(),
            "branch_id": int(branch_id),
            "batch_plan_id": None,
        }).fetchone()
        
        if duplicate_check and duplicate_check.cnt > 0:
            raise HTTPException(status_code=400, detail=f"A batch plan with name '{payload.plan_name}' already exists")

        # Validate total percentage
        total_percentage = sum(li.percentage for li in payload.line_items)
        if abs(total_percentage - 100.0) > 0.01:
            raise HTTPException(
                status_code=400, 
                detail=f"Total percentage must equal 100%. Current total: {total_percentage:.2f}%"
            )

        # Get user ID from token
        user_id = token_data.get("user_id", 1)

        # Create batch plan header
        batch_plan = JuteBatchPlan(
            branch_id=int(branch_id),
            plan_name=payload.plan_name.strip(),
            updated_by=user_id,
            updated_date_time=datetime.now(),
        )
        db.add(batch_plan)
        db.flush()  # Get the auto-generated ID

        # Create line items
        for li in payload.line_items:
            line_item = JuteBatchPlanLi(
                batch_plan_id=batch_plan.batch_plan_id,
                jute_quality_id=li.jute_quality_id,
                percentage=li.percentage,
                updated_by=user_id,
                updated_date_time=datetime.now(),
            )
            db.add(line_item)

        db.commit()

        return {
            "message": "Batch plan created successfully",
            "batch_plan_id": batch_plan.batch_plan_id,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/batch_plan_edit/{batch_plan_id}")
async def batch_plan_edit(
    batch_plan_id: int,
    payload: BatchPlanCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Update an existing batch plan with line items.
    """
    try:
        branch_id = request.query_params.get("branch_id")
        if not branch_id:
            raise HTTPException(status_code=400, detail="Branch ID (branch_id) is required")

        # Validate
        if not payload.plan_name or not payload.plan_name.strip():
            raise HTTPException(status_code=400, detail="Plan name is required")
        
        if not payload.line_items or len(payload.line_items) == 0:
            raise HTTPException(status_code=400, detail="At least one line item is required")

        # Check if batch plan exists
        batch_plan = db.query(JuteBatchPlan).filter(
            JuteBatchPlan.batch_plan_id == batch_plan_id,
            JuteBatchPlan.branch_id == int(branch_id),
        ).first()

        if not batch_plan:
            raise HTTPException(status_code=404, detail="Batch plan not found")

        # Check for duplicate plan name (excluding current)
        duplicate_check = db.execute(check_duplicate_plan_name_query(), {
            "plan_name": payload.plan_name.strip(),
            "branch_id": int(branch_id),
            "batch_plan_id": batch_plan_id,
        }).fetchone()
        
        if duplicate_check and duplicate_check.cnt > 0:
            raise HTTPException(status_code=400, detail=f"A batch plan with name '{payload.plan_name}' already exists")

        # Validate total percentage
        total_percentage = sum(li.percentage for li in payload.line_items)
        if abs(total_percentage - 100.0) > 0.01:
            raise HTTPException(
                status_code=400, 
                detail=f"Total percentage must equal 100%. Current total: {total_percentage:.2f}%"
            )

        # Get user ID from token
        user_id = token_data.get("user_id", 1)

        # Update batch plan header
        batch_plan.plan_name = payload.plan_name.strip()
        batch_plan.updated_by = user_id
        batch_plan.updated_date_time = datetime.now()

        # Delete existing line items
        db.query(JuteBatchPlanLi).filter(
            JuteBatchPlanLi.batch_plan_id == batch_plan_id
        ).delete()

        # Create new line items
        for li in payload.line_items:
            line_item = JuteBatchPlanLi(
                batch_plan_id=batch_plan_id,
                jute_quality_id=li.jute_quality_id,
                percentage=li.percentage,
                updated_by=user_id,
                updated_date_time=datetime.now(),
            )
            db.add(line_item)

        db.commit()

        return {
            "message": "Batch plan updated successfully",
            "batch_plan_id": batch_plan_id,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
