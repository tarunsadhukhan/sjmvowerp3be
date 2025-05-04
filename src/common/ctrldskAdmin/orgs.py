from fastapi import Depends, Request, HTTPException,APIRouter, Query
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_db_names,default_engine
from src.authorization.utils import verify_access_token
from src.common.companyAdmin.schemas import MenuResponse
from src.common.companyAdmin.models import ConMenuMaster, ConUserRoleMapping, ConRoleMenuMap
from src.common.query import get_orgs_all_query, get_orgs_all_count_query, get_org_by_id_query
from typing import Optional, List


router = APIRouter()

@router.get("/get_org_data_all")
async def getOrgsFull(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    search: Optional[str] = None,
    token_data: dict = Depends(verify_access_token),  # Use the new dependency  
    ):
    offset = (page - 1) * limit
    try:
        with Session(default_engine) as session:

            query = get_orgs_all_query(search, offset, limit)
            # text(f"SELECT con_menu_id, con_menu_name, con_menu_parent_id FROM con_menu_master where active =1")
            query_count = get_orgs_all_count_query(search)
            params = {
                "search": f"%{search}%" if search else None,
                "limit": limit,
                "offset": offset
            }
            count_params = {
                "search": f"%{search}%" if search else None
            }

            result = session.execute(query, params)
            result_count = session.execute(query_count, count_params).scalar()
            # total_count = session.execute(count_query, count_params).scalar()
            orgs = result.fetchall()
            orgs = [dict(r._mapping) for r in orgs]
            return {
                "data": orgs,
                "total": result_count,
            }

    except HTTPException as he:
        print(f"HTTP Exception in get_users_tenant_admin: {str(he)}")
        raise
    except Exception as e:
        print(f"Unexpected error in get_users_tenant_admin: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
 
    
