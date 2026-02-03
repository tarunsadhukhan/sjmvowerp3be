"""
Yarn Type Master API endpoints.
Provides CRUD operations for jute yarn type data.
"""

from fastapi import Depends, Request, HTTPException, APIRouter, Response
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.models.jute import JuteYarnTypeMst
from datetime import datetime

router = APIRouter()


def get_yarn_type_list_query():
    """
    Get all yarn types for a company.
    """
    return text("""
        SELECT 
            jyt.jute_yarn_type_id,
            jyt.jute_yarn_type_name,
            jyt.co_id,
            jyt.updated_by,
            jyt.updated_date_time
        FROM jute_yarn_type_mst jyt
        WHERE jyt.co_id = :co_id
        ORDER BY jyt.jute_yarn_type_id DESC
    """)


def get_yarn_type_list_with_search_query():
    """
    Get all yarn types for a company with search filter.
    """
    return text("""
        SELECT 
            jyt.jute_yarn_type_id,
            jyt.jute_yarn_type_name,
            jyt.co_id,
            jyt.updated_by,
            jyt.updated_date_time
        FROM jute_yarn_type_mst jyt
        WHERE jyt.co_id = :co_id
          AND jyt.jute_yarn_type_name LIKE :search
        ORDER BY jyt.jute_yarn_type_id DESC
    """)


@router.get("/get_yarn_type_table")
async def get_yarn_type_table(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
    search: str = None,
    page: int = 1,
    limit: int = 10,
):
    """
    Get paginated list of yarn types for the current company.
    """
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        # Prepare search parameter for LIKE if provided
        search_param = f"%{search}%" if search else None

        # Choose query based on search
        if search_param:
            query = get_yarn_type_list_with_search_query()
            params = {"co_id": int(co_id), "search": search_param}
        else:
            query = get_yarn_type_list_query()
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


@router.get("/get_yarn_type_by_id/{yarn_type_id}")
async def get_yarn_type_by_id(
    yarn_type_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get a single yarn type record by ID.
    """
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        query = text("""
            SELECT 
                jyt.jute_yarn_type_id,
                jyt.jute_yarn_type_name,
                jyt.co_id,
                jyt.updated_by,
                jyt.updated_date_time
            FROM jute_yarn_type_mst jyt
            WHERE jyt.jute_yarn_type_id = :yarn_type_id
              AND jyt.co_id = :co_id
        """)

        result = db.execute(query, {"yarn_type_id": yarn_type_id, "co_id": int(co_id)}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Yarn type record not found")

        return {"data": dict(result._mapping)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/yarn_type_edit_setup/{yarn_type_id}")
async def yarn_type_edit_setup(
    yarn_type_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Get setup data for editing a yarn type record.
    Returns the existing yarn type details.
    """
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        # Get the existing yarn type record
        query = text("""
            SELECT 
                jyt.jute_yarn_type_id,
                jyt.jute_yarn_type_name,
                jyt.co_id,
                jyt.updated_by,
                jyt.updated_date_time
            FROM jute_yarn_type_mst jyt
            WHERE jyt.jute_yarn_type_id = :yarn_type_id
              AND jyt.co_id = :co_id
        """)

        result = db.execute(query, {"yarn_type_id": yarn_type_id, "co_id": int(co_id)}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Yarn type record not found")

        return {
            "yarn_type_details": dict(result._mapping)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/yarn_type_create")
async def yarn_type_create(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Create a new yarn type record.
    """
    try:
        body = await request.json()
        co_id = body.get("co_id") or request.query_params.get("co_id")
        
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        yarn_type_name = body.get("jute_yarn_type_name")
        if not yarn_type_name:
            raise HTTPException(status_code=400, detail="Yarn type name is required")

        # Check for duplicate name
        check_query = text("""
            SELECT COUNT(*) as cnt FROM jute_yarn_type_mst 
            WHERE co_id = :co_id AND jute_yarn_type_name = :yarn_type_name
        """)
        check_result = db.execute(check_query, {
            "co_id": int(co_id),
            "yarn_type_name": yarn_type_name
        }).fetchone()
        
        if check_result and check_result.cnt > 0:
            raise HTTPException(status_code=400, detail="Yarn type with this name already exists")

        # Get user ID from token
        user_id = token_data.get("user_id") if token_data else None

        # Create new yarn type using ORM
        new_yarn_type = JuteYarnTypeMst(
            jute_yarn_type_name=yarn_type_name,
            co_id=int(co_id),
            updated_by=user_id,
            updated_date_time=datetime.now()
        )
        db.add(new_yarn_type)
        db.commit()
        db.refresh(new_yarn_type)

        return {
            "message": "Yarn type created successfully",
            "jute_yarn_type_id": new_yarn_type.jute_yarn_type_id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/yarn_type_edit/{yarn_type_id}")
async def yarn_type_edit(
    yarn_type_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    """
    Update an existing yarn type record.
    """
    try:
        body = await request.json()
        co_id = body.get("co_id") or request.query_params.get("co_id")
        
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")

        yarn_type_name = body.get("jute_yarn_type_name")
        if not yarn_type_name:
            raise HTTPException(status_code=400, detail="Yarn type name is required")

        # Check record exists
        existing = db.query(JuteYarnTypeMst).filter(
            JuteYarnTypeMst.jute_yarn_type_id == yarn_type_id,
            JuteYarnTypeMst.co_id == int(co_id)
        ).first()

        if not existing:
            raise HTTPException(status_code=404, detail="Yarn type record not found")

        # Check for duplicate name (excluding current record)
        check_query = text("""
            SELECT COUNT(*) as cnt FROM jute_yarn_type_mst 
            WHERE co_id = :co_id 
              AND jute_yarn_type_name = :yarn_type_name
              AND jute_yarn_type_id != :yarn_type_id
        """)
        check_result = db.execute(check_query, {
            "co_id": int(co_id),
            "yarn_type_name": yarn_type_name,
            "yarn_type_id": yarn_type_id
        }).fetchone()
        
        if check_result and check_result.cnt > 0:
            raise HTTPException(status_code=400, detail="Yarn type with this name already exists")

        # Get user ID from token
        user_id = token_data.get("user_id") if token_data else None

        # Update the record
        existing.jute_yarn_type_name = yarn_type_name
        existing.updated_by = user_id
        existing.updated_date_time = datetime.now()
        
        db.commit()

        return {
            "message": "Yarn type updated successfully",
            "jute_yarn_type_id": yarn_type_id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
