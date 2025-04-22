from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import  func
from sqlalchemy.sql import text
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Path
from pydantic import BaseModel
from src.config.db import default_engine, extract_subdomain_from_request, get_tenant_db
from src.authorization.utils import verify_access_token
from src.common.query import (get_roles_tenant)
from src.common.portal.models import Base, ConUser, conRoleMaster, ConRoleMenuMap
from src.authorization.utils import get_password_hash
from src.common.utils import get_org_id_from_subdomain


router = APIRouter()

@router.get("/get_roles_portal")
async def get_roles(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    search: Optional[str] = None,
    token_data: dict = Depends(verify_access_token),  # Use the new dependency
    tenant_session: Session = Depends(get_tenant_db),  # Renamed to tenant_session for clarity
):
    print("Starting roles_tenant_admin endpoint")
    try:
        user_id = token_data.get("user_id")  
        if not user_id:
            raise HTTPException(status_code=403, detail="User ID not found in token")

        offset = (page - 1) * limit
        print(f"Calculated offset: {offset} for page: {page} and limit: {limit}")
        # subdomain = extract_subdomain_from_request(request)
    except HTTPException as he:
        print(f"HTTP Exception in get_roles: {str(he)}")
            
    try:
        # Create query with org_id
        query = get_roles_tenant(search)
        print(f"Executing query for search: {search}")
        roles = tenant_session.execute(query, {"limit": limit, "offset": offset, "search": f"%{search}%" if search else None}).fetchall()
        # roles = result.fetchall()
        print(f"Query returned {len(roles) if roles else 0} results")
    except Exception as query_error:
        print(f"Query execution error: {query_error}")
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(query_error)}")

    try: 
        roles = [dict(r._mapping) for r in roles]
        print(f"Converted {len(roles)} rows to dictionaries")
        total = len(roles)
    except Exception as conversion_error:
        print(f"Data conversion error: {conversion_error}")
        raise HTTPException(status_code=500, detail=f"Data conversion error: {str(conversion_error)}")
       
    return { "data": roles, "total": total }

@router.get("/portal_menu_full")
async def get_portal_menu_full(  # Use the new dependency  
    tenant_session: Session = Depends(get_tenant_db),
    ):
    try:
            query = text(f"SELECT menu_id, menu_name, menu_parent_id FROM menu_mst where active =1")
            result = tenant_session.execute(query).fetchall()
            print(f"Query returned {len(result)} results")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")
    try:
        menus = [dict(row._mapping) for row in result]  # Use _mapping to convert rows to dictionaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data conversion error: {str(e)}")
            
    return {"data": menus}

@router.get("/portal_menu_by_roleid/{role_id}")
async def get_admin_tenant_menu_by_roleid(
    _: dict = Depends(verify_access_token), 
    role_id: int = Path(..., description="Role ID to filter menus"),
    tenant_session: Session = Depends(get_tenant_db),  
):
    try:
            # Fetch menus for the given role_id
            menu_query = text("""
                SELECT mm.menu_id, mm.menu_name, mm.menu_parent_id, rmm.role_id 
                FROM menu_mst mm 
                LEFT JOIN role_menu_map rmm 
                ON rmm.menu_id = mm.menu_id AND rmm.role_id = :role_id
            """).bindparams(role_id=role_id)
            menu_result = tenant_session.execute(menu_query).fetchall()
            print(f"Menu query returned {len(menu_result)} results")

            # Fetch role name for the given role_id
            role_query = text("""
                SELECT role_name 
                FROM role_mst
                WHERE role_id = :role_id
            """).bindparams(role_id=role_id)
            role_result = tenant_session.execute(role_query).fetchone()
            print(f"Role query returned: {role_result}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")

    try:
        # Convert menu query results to dictionaries
        menus = [dict(row._mapping) for row in menu_result]  # row._mapping works across SQLAlchemy versions
        role_name = role_result[0] if role_result else None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data conversion error: {str(e)}")
    return {"data": menus, "roleName": role_name}

# Create a Pydantic model for the role creation request
class CreateRoleTenantAdminRequest(BaseModel):
    roleName: str
    selectedMenuIds: List[int]

# Add new Pydantic model after CreateRoleTenantAdminRequest
class EditRoleTenantAdminRequest(BaseModel):
    roleId: int
    selectedMenuIds: List[int]

