"""
Yarn Master API endpoints.
Provides CRUD operations for jute yarn master data.

Schema (jute_yarn_mst):
- jute_yarn_id: int (PK, auto)
- jute_yarn_count: float (nullable)
- jute_yarn_type_id: int (FK to jute_yarn_type_mst)
- jute_yarn_remarks: str (nullable)
- jute_yarn_name: str (nullable)
- co_id: int
- updated_date_time: datetime
- updated_by: int
"""

from fastapi import Depends, Request, HTTPException, APIRouter, Response
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.models.jute import JuteYarnMst
from datetime import datetime

router = APIRouter()


def get_yarn_list_query():
    """
    Get all yarn masters for a company with yarn type name joined.
    """
    return text("""
        SELECT 
            ym.jute_yarn_id,
            ym.jute_yarn_name,
            ym.jute_yarn_count,
            ym.jute_yarn_type_id,
            yt.jute_yarn_type_name,
            ym.jute_yarn_remarks,
            ym.co_id,
            ym.updated_by,
            ym.updated_date_time
        FROM jute_yarn_mst ym
        LEFT JOIN jute_yarn_type_mst yt ON ym.jute_yarn_type_id = yt.jute_yarn_type_id
        WHERE ym.co_id = :co_id
        ORDER BY ym.jute_yarn_id DESC
    """)


def get_yarn_list_with_search_query():
    """
    Get all yarn masters for a company with search filter.
    """
    return text("""
        SELECT 
            ym.jute_yarn_id,
            ym.jute_yarn_name,
            ym.jute_yarn_count,
            ym.jute_yarn_type_id,
            yt.jute_yarn_type_name,
            ym.jute_yarn_remarks,
            ym.co_id,
            ym.updated_by,
            ym.updated_date_time
        FROM jute_yarn_mst ym
        LEFT JOIN jute_yarn_type_mst yt ON ym.jute_yarn_type_id = yt.jute_yarn_type_id
        WHERE ym.co_id = :co_id
          AND (
              ym.jute_yarn_name LIKE :search
              OR yt.jute_yarn_type_name LIKE :search
              OR ym.jute_yarn_remarks LIKE :search
          )
        ORDER BY ym.jute_yarn_id DESC
    """)


def get_yarn_types_for_company():
    """
    Get all yarn types for dropdown.
    """
    return text("""
        SELECT 
            jute_yarn_type_id,
            jute_yarn_type_name
        FROM jute_yarn_type_mst
        WHERE co_id = :co_id
        ORDER BY jute_yarn_type_name
    """)


@router.get("/get_yarn_table")
async def get_yarn_table(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
    search: str = None,
    page: int = 1,
    limit: int = 10,
):
    """
    Get paginated list of yarn masters for the current company.
    """
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        # Prepare search parameter for LIKE if provided
        search_param = f"%{search}%" if search else None

        # Choose query based on search
        if search_param:
            query = get_yarn_list_with_search_query()
            params = {"co_id": int(co_id), "search": search_param}
        else:
            query = get_yarn_list_query()
            params = {"co_id": int(co_id)}

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


@router.get("/get_yarn_by_id/{yarn_id}")
async def get_yarn_by_id(
    yarn_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get a single yarn master record by ID.
    """
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        query = text("""
            SELECT 
                ym.jute_yarn_id,
                ym.jute_yarn_name,
                ym.jute_yarn_count,
                ym.jute_yarn_type_id,
                yt.jute_yarn_type_name,
                ym.jute_yarn_remarks,
                ym.co_id,
                ym.updated_by,
                ym.updated_date_time
            FROM jute_yarn_mst ym
            LEFT JOIN jute_yarn_type_mst yt ON ym.jute_yarn_type_id = yt.jute_yarn_type_id
            WHERE ym.jute_yarn_id = :yarn_id
              AND ym.co_id = :co_id
        """)

        result = db.execute(query, {"yarn_id": yarn_id, "co_id": int(co_id)}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Yarn master record not found")

        return {"data": dict(result._mapping)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/yarn_create_setup")
async def yarn_create_setup(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get setup data for creating a new yarn master record.
    Returns list of yarn types for dropdown.
    """
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        # Get yarn types for dropdown
        yarn_types_result = db.execute(get_yarn_types_for_company(), {"co_id": int(co_id)}).fetchall()
        yarn_types = [dict(row._mapping) for row in yarn_types_result]

        return {
            "yarn_types": yarn_types
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/yarn_edit_setup/{yarn_id}")
async def yarn_edit_setup(
    yarn_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get setup data for editing a yarn master record.
    Returns the existing yarn details and yarn types for dropdown.
    """
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        # Get the existing yarn record
        query = text("""
            SELECT 
                ym.jute_yarn_id,
                ym.jute_yarn_name,
                ym.jute_yarn_count,
                ym.jute_yarn_type_id,
                yt.jute_yarn_type_name,
                ym.jute_yarn_remarks,
                ym.co_id,
                ym.updated_by,
                ym.updated_date_time
            FROM jute_yarn_mst ym
            LEFT JOIN jute_yarn_type_mst yt ON ym.jute_yarn_type_id = yt.jute_yarn_type_id
            WHERE ym.jute_yarn_id = :yarn_id
              AND ym.co_id = :co_id
        """)

        result = db.execute(query, {"yarn_id": yarn_id, "co_id": int(co_id)}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Yarn master record not found")

        # Get yarn types for dropdown
        yarn_types_result = db.execute(get_yarn_types_for_company(), {"co_id": int(co_id)}).fetchall()
        yarn_types = [dict(row._mapping) for row in yarn_types_result]

        return {
            "yarn_details": dict(result._mapping),
            "yarn_types": yarn_types
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/yarn_create")
async def yarn_create(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Create a new yarn master record.
    """
    try:
        body = await request.json()
        co_id = body.get("co_id") or request.query_params.get("co_id")
        
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        jute_yarn_name = body.get("jute_yarn_name")
        if not jute_yarn_name:
            raise HTTPException(status_code=400, detail="Yarn name is required")

        jute_yarn_count = body.get("jute_yarn_count")
        jute_yarn_type_id = body.get("jute_yarn_type_id")
        jute_yarn_remarks = body.get("jute_yarn_remarks")

        # Check for duplicate name within same company
        check_query = text("""
            SELECT COUNT(*) as cnt FROM jute_yarn_mst 
            WHERE co_id = :co_id AND jute_yarn_name = :yarn_name
        """)
        check_result = db.execute(check_query, {
            "co_id": int(co_id),
            "yarn_name": jute_yarn_name
        }).fetchone()
        
        if check_result and check_result.cnt > 0:
            raise HTTPException(status_code=400, detail="Yarn with this name already exists")

        # Get user ID from token
        user_id = token_data.get("user_id") if token_data else None

        # Create new yarn master using ORM
        new_yarn = JuteYarnMst(
            jute_yarn_name=jute_yarn_name,
            jute_yarn_count=float(jute_yarn_count) if jute_yarn_count else None,
            jute_yarn_type_id=int(jute_yarn_type_id) if jute_yarn_type_id else None,
            jute_yarn_remarks=jute_yarn_remarks,
            co_id=int(co_id),
            updated_by=user_id,
            updated_date_time=datetime.now()
        )
        db.add(new_yarn)
        db.commit()
        db.refresh(new_yarn)

        return {
            "message": "Yarn master created successfully",
            "jute_yarn_id": new_yarn.jute_yarn_id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/yarn_edit/{yarn_id}")
async def yarn_edit(
    yarn_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Update an existing yarn master record.
    """
    try:
        body = await request.json()
        co_id = body.get("co_id") or request.query_params.get("co_id")
        
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        jute_yarn_name = body.get("jute_yarn_name")
        if not jute_yarn_name:
            raise HTTPException(status_code=400, detail="Yarn name is required")

        jute_yarn_count = body.get("jute_yarn_count")
        jute_yarn_type_id = body.get("jute_yarn_type_id")
        jute_yarn_remarks = body.get("jute_yarn_remarks")

        # Check record exists
        existing = db.query(JuteYarnMst).filter(
            JuteYarnMst.jute_yarn_id == yarn_id,
            JuteYarnMst.co_id == int(co_id)
        ).first()

        if not existing:
            raise HTTPException(status_code=404, detail="Yarn master record not found")

        # Check for duplicate name (excluding current record)
        check_query = text("""
            SELECT COUNT(*) as cnt FROM jute_yarn_mst 
            WHERE co_id = :co_id 
              AND jute_yarn_name = :yarn_name
              AND jute_yarn_id != :yarn_id
        """)
        check_result = db.execute(check_query, {
            "co_id": int(co_id),
            "yarn_name": jute_yarn_name,
            "yarn_id": yarn_id
        }).fetchone()
        
        if check_result and check_result.cnt > 0:
            raise HTTPException(status_code=400, detail="Yarn with this name already exists")

        # Get user ID from token
        user_id = token_data.get("user_id") if token_data else None

        # Update the record
        existing.jute_yarn_name = jute_yarn_name
        existing.jute_yarn_count = float(jute_yarn_count) if jute_yarn_count else None
        existing.jute_yarn_type_id = int(jute_yarn_type_id) if jute_yarn_type_id else None
        existing.jute_yarn_remarks = jute_yarn_remarks
        existing.updated_by = user_id
        existing.updated_date_time = datetime.now()
        
        db.commit()

        return {
            "message": "Yarn master updated successfully",
            "jute_yarn_id": yarn_id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
