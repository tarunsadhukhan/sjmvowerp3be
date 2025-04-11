from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from .models import RolesMst, ConMenuMaster, RoleMenuMap, Base

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.sql import text
from src.config.db import get_db_names, default_engine
from src.authorization.utils import verify_access_token

# Define the API router for role endpoints
router = APIRouter(
    prefix="",
    tags=["roles"],
    responses={404: {"description": "Not found"}},
)

# Updated dependency to get the database session using the same approach as companydata.py
async def get_db(request: Request):
    try:
        db_data = get_db_names(request)
        
        # Check if db_data is properly structured
        if not isinstance(db_data, dict) or "db_engines" not in db_data:
            raise HTTPException(
                status_code=500,
                detail="Database connection failed: Invalid database configuration"
            )
        
        # Use the default engine from config
        db = Session(default_engine)
        try:
            yield db
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection error: {str(e)}"
        )

# Pydantic models for request/response
class RoleMenuMappingCreate(BaseModel):
    role_id: int
    menu_id: int
    access_type_id: int
    
class RoleMenuMappingUpdate(BaseModel):
    role_id: Optional[int] = None
    menu_id: Optional[int] = None
    access_type_id: Optional[int] = None

def get_all_roles(db: Session) -> List[Dict[str, Any]]:
    """
    Retrieve all active roles from the database.
    
    Args:
        db (Session): SQLAlchemy database session
        
    Returns:
        List of dictionaries containing role information
    """
    roles = db.execute(select(RolesMst).where(RolesMst.active == True)).scalars().all()
    return [{"role_id": role.role_id, "role_name": role.role_name} for role in roles]


def get_all_menus(db: Session) -> List[Dict[str, Any]]:
    """
    Retrieve all active menus from the database with their hierarchy.
    
    Args:
        db (Session): SQLAlchemy database session
        
    Returns:
        List of dictionaries containing menu information
    """
    menus = db.execute(select(ConMenuMaster).where(ConMenuMaster.active == True)).scalars().all()
    
    menu_dict = {}
    for menu in menus:
        menu_dict[menu.con_menu_id] = {
            "menu_id": menu.con_menu_id,
            "menu_name": menu.con_menu_name,
            "parent_id": menu.con_menu_parent_id,
            "path": menu.con_menu_path,
            "icon": menu.con_menu_icon,
            "order": menu.order_by
        }
    
    # Organize menus in hierarchical structure
    menu_tree = []
    for menu_id, menu_data in menu_dict.items():
        if menu_data["parent_id"] is None:
            # This is a root menu
            menu_tree.append(build_menu_tree(menu_id, menu_dict))
    
    return menu_tree


def build_menu_tree(menu_id: int, menu_dict: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Recursively build a menu tree structure.
    
    Args:
        menu_id: The ID of the current menu
        menu_dict: Dictionary of all menus indexed by ID
        
    Returns:
        Dictionary representing the menu and its children
    """
    menu = menu_dict[menu_id].copy()
    children = []
    
    for child_id, child_data in menu_dict.items():
        if child_data["parent_id"] == menu_id:
            children.append(build_menu_tree(child_id, menu_dict))
    
    if children:
        menu["children"] = sorted(children, key=lambda x: x.get("order", 0))
    
    return menu


def get_role_menu_mappings(db: Session) -> List[Dict[str, Any]]:
    """
    Get existing role-menu mappings.
    
    Args:
        db (Session): SQLAlchemy database session
        
    Returns:
        List of dictionaries containing role-menu mappings
    """
    mappings = db.execute(select(RoleMenuMap)).scalars().all()
    return [
        {
            "mapping_id": mapping.role_menu_mapping_id,
            "role_id": mapping.role_id,
            "menu_id": mapping.menu_id,
            "access_type_id": mapping.access_type_id
        }
        for mapping in mappings
    ]


def get_access_types(db: Session) -> List[Dict[str, Any]]:
    """
    Get all available access types.
    
    Args:
        db (Session): SQLAlchemy database session
        
    Returns:
        List of dictionaries containing access type information
    """
    # This would typically fetch from access_type table
    # Since we don't have the model defined, returning placeholder data
    return [
        {"access_type_id": 1, "access_type": "Read"},
        {"access_type_id": 2, "access_type": "Write"},
        {"access_type_id": 3, "access_type": "Full"}
    ]


def generate_role_menu_mapping_data(db: Session) -> Dict[str, Any]:
    """
    Generate complete data structure for role menu mapping UI.
    
    Args:
        db (Session): SQLAlchemy database session
        
    Returns:
        Dictionary containing all data needed for the UI table
    """
    roles = get_all_roles(db)
    menus = get_all_menus(db)
    mappings = get_role_menu_mappings(db)
    access_types = get_access_types(db)
    
    # Create a flattened menu list for UI table
    flat_menus = flatten_menu_tree(menus)
    
    return {
        "roles": roles,
        "menus": menus,
        "flat_menus": flat_menus,
        "mappings": mappings,
        "access_types": access_types,
        "table_structure": {
            "columns": [
                {"field": "role_name", "headerName": "Role", "width": 150},
                {"field": "menu_name", "headerName": "Menu", "width": 200},
                {"field": "access_type", "headerName": "Access Type", "width": 150},
                {"field": "actions", "headerName": "Actions", "width": 100}
            ],
            "rows": generate_table_rows(roles, flat_menus, mappings, access_types)
        }
    }


def flatten_menu_tree(menu_tree: List[Dict[str, Any]], parent_path: str = "") -> List[Dict[str, Any]]:
    """
    Convert hierarchical menu structure to flat list for UI table.
    
    Args:
        menu_tree: Hierarchical menu structure
        parent_path: Path string for menu breadcrumbs
        
    Returns:
        Flattened list of menus
    """
    result = []
    
    for menu in menu_tree:
        current_path = f"{parent_path} > {menu['menu_name']}" if parent_path else menu['menu_name']
        menu_entry = {
            "menu_id": menu["menu_id"],
            "menu_name": menu["menu_name"],
            "path": menu["path"],
            "menu_path": current_path  # For display in UI
        }
        result.append(menu_entry)
        
        if "children" in menu:
            result.extend(flatten_menu_tree(menu["children"], current_path))
    
    return result


def generate_table_rows(roles, flat_menus, mappings, access_types):
    """
    Generate rows for UI table based on existing mappings.
    
    Args:
        roles: List of roles
        flat_menus: Flattened list of menus
        mappings: Existing role-menu mappings
        access_types: Available access types
        
    Returns:
        List of row data for UI table
    """
    rows = []
    
    # Create a mapping dictionary for quick lookup
    role_dict = {role["role_id"]: role for role in roles}
    menu_dict = {menu["menu_id"]: menu for menu in flat_menus}
    access_type_dict = {at["access_type_id"]: at for at in access_types}
    
    for mapping in mappings:
        role = role_dict.get(mapping["role_id"])
        menu = menu_dict.get(mapping["menu_id"])
        access_type = access_type_dict.get(mapping["access_type_id"])
        
        if role and menu and access_type:
            rows.append({
                "id": mapping["mapping_id"],
                "role_id": role["role_id"],
                "role_name": role["role_name"],
                "menu_id": menu["menu_id"],
                "menu_name": menu["menu_path"],
                "access_type_id": access_type["access_type_id"],
                "access_type": access_type["access_type"]
            })
    
    return rows

# Updated endpoints to use the new database connection logic
@router.get("/menu-mapping-data")
async def get_role_menu_mapping_data(
    request: Request,
    token_data: dict = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    """
    Get all data required for the role-menu mapping UI.
    """
    try:
        # Get user_id from token for access control
        user_id = token_data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=403, 
                detail="User ID not found in token"
            )
            
        data = generate_role_menu_mapping_data(db)
        return {"status": "success", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve role menu mapping data: {str(e)}"
        )

@router.get("/roles")
async def get_roles(
    request: Request,
    token_data: dict = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    """
    Get all active roles.
    """
    try:
        # Get user_id from token for access control
        user_id = token_data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=403, 
                detail="User ID not found in token"
            )
            
        roles = get_all_roles(db)
        return {"status": "success", "data": roles}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve roles: {str(e)}"
        )

@router.get("/menus")
async def get_menus(
    request: Request,
    flat: bool = False,
    token_data: dict = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    """
    Get all active menus.
    Optional query parameter 'flat' to get flattened menu list instead of hierarchy.
    """
    try:
        # Get user_id from token for access control
        user_id = token_data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=403, 
                detail="User ID not found in token"
            )
            
        menus = get_all_menus(db)
        if flat:
            menus = flatten_menu_tree(menus)
        return {"status": "success", "data": menus}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve menus: {str(e)}"
        )

@router.get("/access-types")
async def get_access_type_list(
    request: Request,
    token_data: dict = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    """
    Get all access types.
    """
    try:
        # Get user_id from token for access control
        user_id = token_data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=403, 
                detail="User ID not found in token"
            )
            
        access_types = get_access_types(db)
        return {"status": "success", "data": access_types}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve access types: {str(e)}"
        )

@router.get("/mappings")
async def get_mappings(
    request: Request,
    token_data: dict = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    """
    Get all role-menu mappings.
    """
    try:
        # Get user_id from token for access control
        user_id = token_data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=403, 
                detail="User ID not found in token"
            )
            
        mappings = get_role_menu_mappings(db)
        return {"status": "success", "data": mappings}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve mappings: {str(e)}"
        )

@router.post("/mappings", status_code=status.HTTP_201_CREATED)
async def create_mapping(
    mapping: RoleMenuMappingCreate,
    request: Request,
    token_data: dict = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    """
    Create a new role-menu mapping.
    """
    try:
        # Get user_id from token for access control
        user_id = token_data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=403, 
                detail="User ID not found in token"
            )
            
        # Check if role exists
        roles = get_all_roles(db)
        role_exists = any(role["role_id"] == mapping.role_id for role in roles)
        if not role_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {mapping.role_id} not found"
            )
        
        # Check if menu exists
        menus = flatten_menu_tree(get_all_menus(db))
        menu_exists = any(menu["menu_id"] == mapping.menu_id for menu in menus)
        if not menu_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu with ID {mapping.menu_id} not found"
            )
        
        # Create new mapping in database
        new_mapping = RoleMenuMap(
            role_id=mapping.role_id,
            menu_id=mapping.menu_id,
            access_type_id=mapping.access_type_id
        )
        db.add(new_mapping)
        db.commit()
        db.refresh(new_mapping)
        
        return {
            "status": "success", 
            "message": "Role menu mapping created successfully",
            "data": {
                "mapping_id": new_mapping.role_menu_mapping_id,
                "role_id": new_mapping.role_id,
                "menu_id": new_mapping.menu_id,
                "access_type_id": new_mapping.access_type_id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create mapping: {str(e)}"
        )

@router.put("/mappings/{mapping_id}")
async def update_mapping(
    mapping_id: int, 
    mapping_update: RoleMenuMappingUpdate, 
    request: Request,
    token_data: dict = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    """
    Update an existing role-menu mapping.
    """
    try:
        # Get user_id from token for access control
        user_id = token_data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=403, 
                detail="User ID not found in token"
            )
            
        # Get the mapping to update
        mapping_query = db.query(RoleMenuMap).filter(RoleMenuMap.role_menu_mapping_id == mapping_id)
        existing_mapping = mapping_query.first()
        
        if not existing_mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mapping with ID {mapping_id} not found"
            )
        
        # Update only provided fields
        update_data = mapping_update.dict(exclude_unset=True)
        
        if "role_id" in update_data:
            roles = get_all_roles(db)
            role_exists = any(role["role_id"] == update_data["role_id"] for role in roles)
            if not role_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Role with ID {update_data['role_id']} not found"
                )
        
        if "menu_id" in update_data:
            menus = flatten_menu_tree(get_all_menus(db))
            menu_exists = any(menu["menu_id"] == update_data["menu_id"] for menu in menus)
            if not menu_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Menu with ID {update_data['menu_id']} not found"
                )
        
        mapping_query.update(update_data)
        db.commit()
        
        # Get the updated mapping
        updated_mapping = mapping_query.first()
        
        return {
            "status": "success", 
            "message": "Role menu mapping updated successfully",
            "data": {
                "mapping_id": updated_mapping.role_menu_mapping_id,
                "role_id": updated_mapping.role_id,
                "menu_id": updated_mapping.menu_id,
                "access_type_id": updated_mapping.access_type_id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update mapping: {str(e)}"
        )

@router.delete("/mappings/{mapping_id}")
async def delete_mapping(
    mapping_id: int, 
    request: Request,
    token_data: dict = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    """
    Delete a role-menu mapping.
    """
    try:
        # Get user_id from token for access control
        user_id = token_data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=403, 
                detail="User ID not found in token"
            )
            
        mapping = db.query(RoleMenuMap).filter(RoleMenuMap.role_menu_mapping_id == mapping_id).first()
        
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mapping with ID {mapping_id} not found"
            )
        
        db.delete(mapping)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Role menu mapping with ID {mapping_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete mapping: {str(e)}"
        )
