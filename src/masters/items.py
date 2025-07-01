from fastapi import Depends, Request, HTTPException, APIRouter, Response
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_db_names, default_engine, get_tenant_db
from src.authorization.utils import  get_current_user_with_refresh
# from src.masters.schemas import MenuResponse
from src.masters.models import ItemGrpMst, ItemTypeMaster
from src.masters.query import get_item_group, get_item_group_drodown, india_gst_applicable
from datetime import datetime

router = APIRouter()


@router.get("/get_all_item_groups")
async def get_item_groups(
    request: Request,
    response: Response,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
    search: str = None
):
    try:
        # Get the item groups for the company specified in the request received
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")
        # Prepare search parameter for LIKE if provided
        search_param = f"%{search}%" if search else None
        query = get_item_group(int(co_id))
        result = db.execute(query, {"co_id": int(co_id), "search": search_param}).fetchall()
        data = [dict(row._mapping) for row in result]
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@router.get("/createItemGroupSetup")
async def create_item_group_setup(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh),
):
    is_india_gst_applicable = False  # Ensure variable is always defined
    try:
        co_id = request.query_params.get("co_id")
        if not co_id:
            raise HTTPException(status_code=400, detail="Company ID (co_id) is required")
        # No search param for setup, just get all item groups for dropdown
        query = get_item_group_drodown(int(co_id))
        result = db.execute(query, {"co_id": int(co_id), "search": None}).fetchall()
        item_groups = [dict(row._mapping) for row in result]
        # Get all item types for dropdown
        item_types = db.query(ItemTypeMaster).all()
        item_type_list = [
            {"item_type_id": t.item_type_id, "item_type_name": t.item_type_name}
            for t in item_types
        ]
        # Check if India GST is applicable for the company
        india_gst_query = india_gst_applicable()
        result = db.execute(india_gst_query, {"co_id": int(co_id)}).fetchone()
        if result and result[0] is not None:
            is_india_gst_applicable = result[0]
        return {"item_groups": item_groups, "item_types": item_type_list, "india_gst_applicable": is_india_gst_applicable}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/createItemGroup")
async def create_item_group(
    payload: dict,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(get_current_user_with_refresh)
):
    try:
        def sanitize_int(value):
            return int(value) if isinstance(value, int) or (isinstance(value, str) and value.isdigit()) else None

        parent_grp_id = sanitize_int(payload.get("parent_grp_id"))
        item_type_id = sanitize_int(payload.get("item_type_id"))
        # Use user_id from token if updated_by is not provided
        updated_by = payload.get("updated_by") or str(token_data.get("user_id"))
        new_group = ItemGrpMst(
            co_id=payload.get("co_id"),
            active=1,
            updated_by=updated_by,
            updated_date_time=payload.get("updated_date_time", datetime.utcnow()),
            item_grp_name=payload.get("item_grp_name"),
            item_grp_code=payload.get("item_grp_code"),
            item_type_id=item_type_id,
            parent_grp_id=parent_grp_id
        )
        db.add(new_group)
        db.commit()
        db.refresh(new_group)
        return {"message": "Item group created successfully", "item_grp_id": new_group.item_grp_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


