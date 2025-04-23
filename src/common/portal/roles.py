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
                SELECT mm.menu_id, mm.menu_name, mm.menu_parent_id, rmm.role_id, rmm.access_type_id
                FROM menu_mst mm 
                LEFT JOIN role_menu_map rmm 
                ON rmm.menu_id = mm.menu_id AND rmm.role_id = :role_id
            """).bindparams(role_id=role_id)
            menu_result = tenant_session.execute(menu_query).fetchall()
            print(f"Menu query returned {len(menu_result)} results")

            # Fetch role name for the given role_id
            role_query = text("""
                SELECT role_name 
                FROM roles_mst
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

# Add new Pydantic model for menu access type
class MenuAccess(BaseModel):
    menuId: int
    accessTypeId: str

# Create a Pydantic model for the role creation request
class CreateRoleTenantAdminRequest(BaseModel):
    roleName: str
    selectedMenuIds: List[int] = []
    menuAccessList: Optional[List[MenuAccess]] = []

# Add new Pydantic model after CreateRoleTenantAdminRequest
class EditRoleTenantAdminRequest(BaseModel):
    roleId: int
    selectedMenuIds: List[int]

# Add new Pydantic model for role menu access payload
class RoleMenuAccessRequest(BaseModel):
    roleId: int
    menuAccessList: List[MenuAccess]

@router.post("/create_role_portal")
async def create_role_portal(
    request: Request,
    role_data: CreateRoleTenantAdminRequest,
    token_data: dict = Depends(verify_access_token),
    tenant_session: Session = Depends(get_tenant_db)
):
    """
    Create a new role in the portal with selected menu items
    
    Args:
        role_data: Role data including name and selected menu IDs
        token_data: Authentication token data
        tenant_session: Database session for tenant database
        
    Returns:
        Dict with status and created role data
    """
    print("Starting create_role_portal endpoint")
    try:
        user_id = token_data.get("user_id")
        if not user_id:
            raise HTTPException(status_code=403, detail="User ID not found in token")
        
        print(f"Authenticated user ID: {user_id}")
        
        # Print the received data
        print(f"Received role name: {role_data.roleName}")
        if role_data.menuAccessList:
            print(f"Received menuAccessList: {[f'menuId: {item.menuId}, accessTypeId: {item.accessTypeId}' for item in role_data.menuAccessList]}")
        elif role_data.selectedMenuIds:
            print(f"Received selectedMenuIds: {role_data.selectedMenuIds}")
        
        # Get the subdomain for logging
        subdomain = extract_subdomain_from_request(request)
        print(f"Creating role for subdomain: {subdomain}")
        
        try:
            # Create a new role
            new_role = conRoleMaster(
                role_name=role_data.roleName,
                active=True,
                created_by_con_user=user_id,
                created_date_time=func.now()
            )
            
            tenant_session.add(new_role)
            tenant_session.flush()  # Flush to get the new role ID
            
            role_id = new_role.role_id
            print(f"Created new role with ID: {role_id}")
            
            # Create menu mappings for the role
            menu_mappings = []
            
            # Process menuAccessList if provided, otherwise use selectedMenuIds
            if role_data.menuAccessList:
                for menu_access in role_data.menuAccessList:
                    access_type_id = int(menu_access.accessTypeId)
                    menu_mapping = ConRoleMenuMap(
                        role_id=role_id,
                        menu_id=menu_access.menuId,
                        access_type_id=access_type_id
                    )
                    menu_mappings.append(menu_mapping)
            else:
                for menu_id in role_data.selectedMenuIds:
                    menu_mapping = ConRoleMenuMap(
                        role_id=role_id,
                        menu_id=menu_id,
                        access_type_id=1  # Default access type
                    )
                    menu_mappings.append(menu_mapping)
            
            if menu_mappings:
                tenant_session.add_all(menu_mappings)
                print(f"Added {len(menu_mappings)} menu mappings")
            
            tenant_session.commit()
            
            return {
                "status": "success",
                "message": "Role and menu mappings created successfully",
                "data": {
                    "role_id": role_id,
                    "role_name": role_data.roleName,
                    "mapped_menu_count": len(menu_mappings)
                }
            }
            
        except Exception as db_error:
            tenant_session.rollback()
            print(f"Database error: {str(db_error)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create role: {str(db_error)}"
            )
    
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Unexpected error in create_role_portal: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.put("/edit_role_portal")
async def edit_role_portal(
    request: Request,
    role_data: RoleMenuAccessRequest,
    token_data: dict = Depends(verify_access_token),
    tenant_session: Session = Depends(get_tenant_db)
):
    """
    Update role menu access permissions with specific access types for each menu
    
    Args:
        role_data: Role data including role ID and menu access list with access types
        token_data: Authentication token data
        tenant_session: Database session for tenant database
        
    Returns:
        Dict with status and updated role data
    """
    print("Starting update_role_menu_access endpoint")
    try:
        user_id = token_data.get("user_id")
        if not user_id:
            raise HTTPException(status_code=403, detail="User ID not found in token")
        
        print(f"Authenticated user ID: {user_id}")
        print(f"Updating role ID: {role_data.roleId}")
        print(f"Menu access list: {[f'menuId: {item.menuId}, accessTypeId: {item.accessTypeId}' for item in role_data.menuAccessList]}")
        
        try:
            # First verify if role exists
            role = tenant_session.query(conRoleMaster).filter(
                conRoleMaster.role_id == role_data.roleId
            ).first()
            
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Role with ID {role_data.roleId} not found"
                )
            
            # Delete existing menu mappings for this role
            print(f"Deleting existing menu mappings for role {role_data.roleId}")
            delete_query = tenant_session.query(ConRoleMenuMap).filter(
                ConRoleMenuMap.role_id == role_data.roleId
            ).delete()
            
            print(f"Deleted {delete_query} existing mappings")
            
            # Create new menu mappings with access types
            menu_mappings = []
            for menu_access in role_data.menuAccessList:
                # Convert accessTypeId from string to integer if needed
                access_type_id = int(menu_access.accessTypeId)
                
                menu_mapping = ConRoleMenuMap(
                    role_id=role_data.roleId,
                    menu_id=menu_access.menuId,
                    access_type_id=access_type_id
                )
                menu_mappings.append(menu_mapping)
            
            if menu_mappings:
                tenant_session.add_all(menu_mappings)
                print(f"Added {len(menu_mappings)} new menu mappings with access types")
            
            tenant_session.commit()
            
            return {
                "status": "success",
                "message": "Role menu access permissions updated successfully",
                "data": {
                    "role_id": role_data.roleId,
                    "role_name": role.role_name if hasattr(role, 'role_name') else None,
                    "mapped_menu_count": len(role_data.menuAccessList)
                }
            }
            
        except Exception as db_error:
            tenant_session.rollback()
            print(f"Database error: {str(db_error)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update role menu access permissions: {str(db_error)}"
            )
    
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Unexpected error in update_role_menu_access: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

