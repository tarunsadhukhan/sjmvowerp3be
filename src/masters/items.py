from fastapi import Depends, Request, HTTPException, APIRouter
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_db_names, default_engine, get_tenant_db
from src.authorization.utils import verify_access_token
# from src.masters.schemas import MenuResponse
from src.masters.models import ItemGrpMst
from src.masters.query import get_item_group

router = APIRouter()


@router.get("/get_all_item_groups")
async def get_item_groups(
    request: Request,
    db: Session = Depends(get_tenant_db),
    token_data: dict = Depends(verify_access_token),
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
    
# @router.post("/create_item_group")
# async def create_item_group(
