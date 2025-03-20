from datetime import datetime, timedelta
# from sqlmodel import Session, select
# from passlib.context import CryptContext
# import jwt
import os
from fastapi import Depends, Query, Request, HTTPException,APIRouter
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.db import get_db_names,default_engine
from src.authorization.auth import verify_token
from collections import defaultdict

router = APIRouter()

@router.get("/console_menu_items")
def compmenuitems(
    request: Request,
    subdomain: str = Query(...),  # ✅ Captures subdomain from query params
    user_id: str = Query(...),  # ✅ Captures user_id from query params
    token_data: dict = Depends(verify_token),  # ✅ Validate JWT Token
):
    subdomain = request.headers.get("X-Subdomain", "default")

    print('tjadata',token_data)
    print(subdomain)
    # ✅ Extract user details from the token
    user_id_from_token = token_data.get("user_id")
    print(user_id,user_id_from_token)
    if str(user_id) != str(user_id_from_token):  # ✅ Ensure correct user
        raise HTTPException(status_code=403, detail="Unauthorized access====")

    print(f"✅ Authorized Request: Subdomain: {subdomain}, User ID: {user_id}, Token User: {user_id_from_token}")
    host = subdomain.strip()    
    print(host)

    db_data = get_db_names(request)  # ✅ Fetch the full dictionary
    print('DEBUG: db_data =', db_data)  # ✅ Print full response for debugging

    dbs = db_data["db_engines"]  # ✅ Extract database engines
    dbn = db_data["db_names_array"]  # ✅ Extract database names

    print("DEBUG: db_engines =", dbs)  # ✅ Debugging
    print("DEBUG: db_names_array =", dbn)  # ✅ Debugging

    # ✅ Assign dynamic variables based on available database names
    dbfl1 = dbn[0] if len(dbn) > 0 else None
    dbfl2 = dbn[1] if len(dbn) > 1 else None

    print(f"Assigned dbfl1: {dbfl1}, dbfl2: {dbfl2}")  # ✅ Debugging
    print(request)
    params={}
    print ('staring ',user_id)
    if int(user_id) == 1:
        print('query for ',user_id)
        sqlQuery1 = """WITH RECURSIVE MenuHierarchy AS (
        SELECT
          mm.control_desk_menu_id AS id,
          mm.control_desk_menu_name AS title,
          mm.menu_path AS path,
          null AS icon,
          mm.parent_id, mm.control_desk_menu_id mmenu_id
        FROM
          vowconsole3.control_desk_menu mm
        WHERE
        mm.parent_id = 0
        UNION ALL
        SELECT
        mm.control_desk_menu_id AS id,
        mm.control_desk_menu_name AS title,
        mm.menu_path AS path,
        null AS icon,
        mm.parent_id,
        mm.parent_id mmenu_id
        FROM
          vowconsole3.control_desk_menu mm
        INNER JOIN
          MenuHierarchy mh ON mm.parent_id = mh.id -- Recursive join to fetch submenus
        )
        SELECT mh.id,title,
        case when parent_id =66 then concat('store/',path) else path end path,icon,parent_id,mmenu_id,
        2 company_id,26586 user_id FROM MenuHierarchy mh order by mmenu_id"""
    else: 
        sqlQuery1 = """select * from (
      select menu_id id, menu_name name, case when parent_id=0 then 0 else parent_id end parent_id, mmenu_id
      from (
        SELECT menu_id, menu menu_name,
        parent_id, menu_path path, menu_state component_name, report_path component_path, menu_id mmenu_id,
        menu_icon_name icon FROM menu_master where parent_id=0
        union all
        SELECT menu_id, menu menu_name,
        parent_id, menu_path path, menu_state component_name, report_path component_path, parent_id mmenu_id
        menu_icon_name icon FROM menu_master where menu_id in
        (select menu_id from menu_master where parent_id>0)) g ORDER BY menu_id
        ) g join
        (select menu_id from user_grp_menu_master ugmm
        join user_group_map_master ugmm2 on ugmm.user_grp_id = ugmm2.user_grp_id
        where ugmm2.user_id = :userid and ugmm.is_enable = 1) v on g.id = v.menu_id order by mmenu_id limit 3290"""
        params = {"userid": user_id}
    
    with Session(default_engine) as session:
        #user = session.execute(text(sqlQuery1), params if params else {}).fetchall()
        user = session.execute(text(sqlQuery1), params if params else {}).fetchall()
        print('queruserr', sqlQuery1, user)

    column_names = ['id', 'title', 'path', 'icon','parent_id',  'mmenu_id', 'company_id', 'user_id']  
    results = [dict(zip(column_names, row)) for row in user]
    print('results',results)
    #results = [dict(row) for row in user]  # Convert SQLAlchemy result to list of dicts
    
    mainMenus = [item for item in results if item['parent_id'] == 0]
    subMenus = [item for item in results if item['parent_id'] != 0]
    
    print('main',mainMenus)
    print('sub',subMenus)
    # Map main menus and nest submenus within the correct parent
    menuData = []
    for main in mainMenus:
        submenuItems = [{
            'id': sub['id'],
            'title': sub['title'],
            'path': sub['path'],
            'icon': sub['icon'],  # Use actual value, not a string 'sub.icon'
        } for sub in subMenus if sub['parent_id'] == main['id']]
  
        menuData.append({
            'id': main['id'],
            'title': main['title'],
            'path': main['path'],
            'icon': main['icon'],
            'submenu': submenuItems if submenuItems else None,
        })

    return {
        "data": menuData  # Roll weight data
    }
    



@router.get("/companyfyyear")
def companiesfyyear(
    request: Request
    
   
 ):

    

    db_data = get_db_names(request)  # ✅ Fetch the full dictionary
    print('DEBUG: db_data =', db_data)  # ✅ Print full response for debugging

    dbs = db_data["db_engines"]  # ✅ Extract database engines
    dbn = db_data["db_names_array"]  # ✅ Extract database names

    print("DEBUG: db_engines =", dbs)  # ✅ Debugging
    print("DEBUG: db_names_array =", dbn)  # ✅ Debugging

    # ✅ Assign dynamic variables based on available database names
    dbfl1 = dbn[0] if len(dbn) > 0 else None
    dbfl2 = dbn[1] if len(dbn) > 1 else None

    print(f"Assigned dbfl1: {dbfl1}, dbfl2: {dbfl2}")  # ✅ Debugging
    print(request)
    
    
    
    
    if not isinstance(db_data, dict) or "db_engines" not in db_data:
        return {
            "access_token": "",
            "token_type": "",
            "status_code": 500,  # Internal Server Error
            "message": "Database connection failed: Invalid database configuration"
        }
       
    
    


    
    print('2nd ',request)
    if "default" not in dbs:
        return {
            "access_token": "",
            "token_type": "",
            "status_code": 500,  # Internal Server Error
            "message": "Database connection failed: Default database missing"
        }
        
        
        #raise HTTPException(status_code=500, detail="Default database connection missing")
    print('3ndddssdsdsd ',request)
    print ('Hosthdshdshd') 
    subdomain = request.headers.get("subdomain")
    host = subdomain.strip() if subdomain else None
    if not host:
           return {
             "access_token": "",
            "token_type": "",
            "status_code": 400,  # Internal Server Error
            "message": "Invalid Subdoman"   
        }
     
        #raise HTTPException(status_code=400, detail="Invalid subdomain")
    
    
    print('hhhs',host)
   
    #engine = create_engine(dbs["default"])
    with Session(default_engine) as session:
        query = text("""select hdr_id id,display_label years from dbfl1.academic_years where company_id=:cmpid order by from_date desc""")
        print('querr', query)
        cmpid=2
        user = session.execute(query, {"cmpid": cmpid}).fetchall()
        print('queruserr', query, user)

        if not user:
            return {
                "data": [],
                "status_code": 401,  # Unauthorized
                "message": "No Data Found"
            }
        
        
      
 

    return {
        "data": user,
        "status_code": 200,  # Success
        "message": "Login successful"
    }
        






