from datetime import datetime, timedelta
# from sqlmodel import Session, select
# from passlib.context import CryptContext
# import jwt
import os
from fastapi import Depends, Query, Request, HTTPException,APIRouter, Header
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_db_names,default_engine
from src.authorization.utils import verify_access_token
from collections import defaultdict
# Example definition for get_menu_for_othuser_query (replace with actual implementation)
from pydantic import BaseModel
from typing import Optional
from src.common.companyAdmin.schemas import MenuResponse, MenuItem, SubMenuItem
from src.common.companyAdmin.models import ConMenuMaster

router = APIRouter()

from fastapi import Request, Query, Cookie, HTTPException
from sqlalchemy.sql import text
from sqlalchemy.orm import Session



@router.get("/company_console_menu_items", response_model=MenuResponse)
def compmenuitems(
    request: Request,
    subdomain: str = Query(...),
    user_id: str = Query(...),
    token_data: dict = Depends(verify_access_token),  # Use the new dependency
):
    subdomain = request.headers.get("X-Subdomain", "default")
    print(subdomain)

    user_id_from_cookie = token_data.get("user_id")
    print(f"Query user_id: {user_id}, Token user_id: {user_id_from_cookie}")  # Debug
    if not user_id_from_cookie:
        raise HTTPException(status_code=403, detail="User ID not found in token")

    if str(user_id) != str(user_id_from_cookie):
        print(f"User ID mismatch: Query user_id={user_id}, Token user_id={user_id_from_cookie}")  # Debug
        raise HTTPException(status_code=403, detail="Unauthorized access via cookie")

    print(f"✅ Authorized Request: Subdomain: {subdomain}, User ID: {user_id}, Cookie User: {user_id_from_cookie}")
    host = subdomain.strip()
    print(host)

    # Fetch menu data from database
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