from fastapi import Depends, Request, HTTPException,APIRouter
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_db_names,default_engine, get_tenant_db
from src.authorization.utils import verify_access_token
from src.common.companyAdmin.schemas import MenuResponse
from src.common.companyAdmin.models import ConMenuMaster, ConUserRoleMapping, ConRoleMenuMap

router = APIRouter()

@router.get("/portal_menu_items", response_model=MenuResponse)
async def compmenuitems(
    request: Request,
    token_data: dict = Depends(verify_access_token),
      tenant_session: Session = Depends(get_tenant_db),  # Use the new dependency
):
    # Extract subdomain from host header
    host = request.headers.get("host", "")
    subdomain = host.split('.')[0] if '.' in host else "default"
    
    user_id_ck = token_data.get("user_id")
    print(f" Token user_id: {user_id_ck}")  # Debug
    if not user_id_ck:
        raise HTTPException(status_code=403, detail="User ID not found in token")
    print(f"✅ Authorized Request: Subdomain: {subdomain}, Cookie User: {user_id_ck}")

    with Session(default_engine) as session:
        # Get all menu items
        menu_items = session.query(ConMenuMaster).filter(ConMenuMaster.active == True).order_by(ConMenuMaster.order_by).all()
        
        # Separate main menus and submenus
        main_menus = [item for item in menu_items if item.con_menu_parent_id is None or item.con_menu_parent_id == 0]
        sub_menus = [item for item in menu_items if item.con_menu_parent_id is not None and item.con_menu_parent_id > 0]

        # Format the response
        menu_data = []
        for main in main_menus:
            submenu_items = [{
                'id': sub.con_menu_id,
                'title': sub.con_menu_name,
                'path': sub.con_menu_path,
                'icon': sub.con_menu_icon,
            } for sub in sub_menus if sub.con_menu_parent_id == main.con_menu_id]

            menu_data.append({
                'id': main.con_menu_id,
                'title': main.con_menu_name,
                'path': main.con_menu_path,
                'icon': main.con_menu_icon,
                'submenu': submenu_items if submenu_items else None,
            })

    return {
        "data": menu_data
    }