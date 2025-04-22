from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import  func
from sqlalchemy.sql import text
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Path
from pydantic import BaseModel
from src.config.db import default_engine, extract_subdomain_from_request, get_tenant_db
from src.authorization.utils import verify_access_token
from src.common.query import (get_users_tenant)
from src.common.portal.models import Base, ConUser, conRoleMaster, ConRoleMenuMap
from src.authorization.utils import get_password_hash
from src.common.utils import get_org_id_from_subdomain


router = APIRouter()

@router.get("/get_users_portal")
async def get_roles(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    search: Optional[str] = None,
    token_data: dict = Depends(verify_access_token),  # Use the new dependency
    tenant_session: Session = Depends(get_tenant_db),  # Renamed to tenant_session for clarity
):
    print("Starting users_tenant_admin endpoint")
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
        query = get_users_tenant(search)
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

