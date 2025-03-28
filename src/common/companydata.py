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
from src.common.query import get_menu_for_user1_query, get_menu_for_othuser_query
# Example definition for get_menu_for_othuser_query (replace with actual implementation)

router = APIRouter()

from fastapi import Request, Query, Cookie, HTTPException
from sqlalchemy.sql import text
from sqlalchemy.orm import Session

@router.get("/console_menu_items")
def compmenuitems(
    request: Request,
    subdomain: str = Query(...),
    user_id: str = Query(...),
    token_data: dict = Depends(verify_access_token),  # Use the new dependency
):
    subdomain = request.headers.get("X-Subdomain", "default")
    print(subdomain)

    # # Validate the cookie
    # if not access_token:
    #     raise HTTPException(status_code=403, detail="No access token cookie provided")

    # # Example: Assuming the cookie contains user_id or some identifier
    # # Replace this with your actual cookie validation logic (e.g., decode JWT, check session store)
    # user_id_from_cookie = access_token  # For now, assuming access_token is the user_id; adjust as needed

    # print(user_id, user_id_from_cookie)
    # if str(user_id) != str(user_id_from_cookie):  # Ensure correct user
    #     raise HTTPException(status_code=403, detail="Unauthorized access via cookie")

    # New: Extract user_id from the decoded token
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

    print(request)
    params = {}
    print('starting ', user_id)  
    if int(user_id) == 1:
        sql_query = get_menu_for_user1_query()
        params = {"userid": user_id} 
    else:
        sql_query = get_menu_for_othuser_query()
        params = {"userid": user_id} 
 
    # print(sql_query,params)
        
        
    
    with Session(default_engine) as session:
        # user = session.execute(text(sql_query), params if params else {}).fetchall()
        user = session.execute(sql_query, params if params else {}).fetchall()
        # print('queruserr', sql_query, user)


    column_names = ['id', 'title', 'path', 'icon', 'parent_id', 'mmenu_id', 'company_id', 'user_id']
    results = [dict(zip(column_names, row)) for row in user]
    # print('results', results)

    mainMenus = [item for item in results if item['parent_id'] == 0]
    subMenus = [item for item in results if item['parent_id'] != 0]

    # print('main', mainMenus)
    # print('sub', subMenus)

    menuData = []
    for main in mainMenus:
        submenuItems = [{
            'id': sub['id'],
            'title': sub['title'],
            'path': sub['path'],
            'icon': sub['icon'],
        } for sub in subMenus if sub['parent_id'] == main['id']]

        menuData.append({
            'id': main['id'],
            'title': main['title'],
            'path': main['path'],
            'icon': main['icon'],
            'submenu': submenuItems if submenuItems else None,
        })

    return {
        "data": menuData
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
        






