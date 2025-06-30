from fastapi import Depends, Request, HTTPException, APIRouter, Response
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_db_names, default_engine, get_tenant_db
from src.authorization.utils import get_current_user_with_refresh
from src.common.companyAdmin.schemas import MenuResponse
from src.common.companyAdmin.models import ConMenuMaster, ConUserRoleMapping, ConRoleMenuMap
from src.common.portal.query import get_portal_user_menus

router = APIRouter()

@router.get("/portal_menu_items")
async def compmenuitems(
    request: Request,
    response: Response,
    token_data: dict = Depends(get_current_user_with_refresh),
    tenant_session: Session = Depends(get_tenant_db),
):
    user_id = token_data.get("user_id")
    print(f" Token user_id: {user_id}")  # Debug
    if not user_id:
        raise HTTPException(status_code=403, detail="User ID not found in token")
    print(f"✅ Authorized Request: Cookie User: {user_id}")
    try:
        # Get menus for this user
        menu_query = get_portal_user_menus(user_id=user_id)
        menu_result = tenant_session.execute(menu_query, {"user_id": user_id}).fetchall()
        print(f"Found {len(menu_result)} menu entries for user {user_id}")
        
        # Process results into nested structure
        companies = {}
        
        for row in menu_result:
            co_id = row.co_id
            co_name = row.co_name
            branch_id = row.branch_id
            branch_name = row.branch_name
            menu_id = row.menu_id
            menu_name = row.menu_name
            menu_path = row.menu_path
            menu_parent_id = row.menu_parent_id
            
            # Skip if menu is None (could happen if role doesn't have menu mappings)
            if menu_id is None:
                continue
            
            # Add company if not exists
            if co_id not in companies:
                companies[co_id] = {
                    "co_id": co_id,
                    "co_name": co_name,
                    "branches": {}
                }
            
            # Add branch if not exists for this company
            if branch_id not in companies[co_id]["branches"]:
                companies[co_id]["branches"][branch_id] = {
                    "branch_id": branch_id,
                    "branch_name": branch_name,
                    "menus": {}
                }
            
            # Add menu to branch
            companies[co_id]["branches"][branch_id]["menus"][menu_id] = {
                "menu_id": menu_id,
                "menu_name": menu_name,
                "menu_path": menu_path,
                "menu_parent_id": menu_parent_id
            }
        
        # Convert to final structure
        result = []
        for co_id, company in companies.items():
            company_data = {
                "co_id": company["co_id"],
                "co_name": company["co_name"],
                "branches": []
            }
            
            for branch_id, branch in company["branches"].items():
                branch_data = {
                    "branch_id": branch["branch_id"],
                    "branch_name": branch["branch_name"],
                    "menus": list(branch["menus"].values())
                }
                company_data["branches"].append(branch_data)
            
            result.append(company_data)
        
        return result
    except Exception as e:
        print(f"Error getting portal menu items: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting portal menu items: {str(e)}")

