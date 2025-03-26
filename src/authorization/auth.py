
from src.authorization.utils import create_access_token, create_refresh_token, verify_password
from fastapi import Request, HTTPException, Response  # ✅ Import Response
from sqlalchemy.sql import text
from src.config.db import get_db_names,default_engine  # ✅ Ensure correct import
from src.config.db import Session  # ✅ Import default_engine
from fastapi.responses import JSONResponse  # ✅ Import JSONResponse


def login_user_console(
    request: Request,
    username: str,
    password: str,
    logintype: str,
    subdomain: str,
):
    """Login logic - Queries user table where username, password, and subdomain match"""
    # 1. Get database connections
    db_data = get_db_names(request)
    print('DEBUG: db_data =', db_data)

    dbs = db_data["db_engines"]
    dbn = db_data["db_names_array"]

    print("DEBUG: db_engines =", dbs)
    print("DEBUG: db_names_array =", dbn)

    dbfl1 = dbn[0] if len(dbn) > 0 else None
    dbfl2 = dbn[1] if len(dbn) > 1 else None

    print(f"Assigned dbfl1: {dbfl1}, dbfl2: {dbfl2}")

    # 2. Check for default DB
    if "default" not in dbs:
        return JSONResponse(
            content={
                "access_token": "",
                "token_type": "",
                "status": 500,
                "message": "Database connection failed: Default database missing",
            },
            status_code=500,
        )

    # 3. Authenticate user
    with Session(default_engine) as session:
        query = text("""
            SELECT * FROM vowconsole3.con_user_master cum
            WHERE con_user_login_email_id = :username 
              AND cum.con_user_id = 1
              AND cum.con_user_type = 0
        """)
        print('Query:', query)
        user = session.execute(query, {"username": username}).fetchone()
        print('User result:', user)
        userid=user.con_user_id
        print('User id:', userid)

        if not user or not verify_password(password, user.con_user_login_password):
            return JSONResponse(
                content={
                    "access_token": "",
                    "token_type": "",
                    "status": 401,
                    "message": "Invalid username or password",
                },
                status_code=401,
            )

        # 4. Create tokens
        token = create_access_token({"user_id": user.con_user_id})
        refresh_token = create_refresh_token({"user_id": user.con_user_id})
        
        # 5. Update refresh token in DB
        try:
            query = text("""
                UPDATE vowconsole3.con_user_master 
                SET refresh_token = :refresh_token 
                WHERE con_user_login_email_id = :username
            """)
            session.execute(query, {
                "username": username,
                "refresh_token": refresh_token
            })
            session.commit()
            print('Refresh token updated for:', username)
        except Exception as e:
            print('Error updating refresh token:', str(e))
            raise HTTPException(status_code=500, detail="Failed to update refresh token")

    # 6. Send cookie with response
    response = JSONResponse(
        content={
            "message": "Login successful",
            "status": 200,
            "access_token": token,
            "user_id": userid
                    },
        status_code=200
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=False,
        secure=False,        # True in prod (HTTPS)
        samesite="lax",      # Use 'none' if needed and secure=True
        path="/",
        # domain="admin.localhost"   # Required for admin.localhost subdomain
    )
    return response  # Ensure this is inside the appropriate function
        


def login_user(
    request: Request,
    username: str,
    password: str,
    logintype: str,
    subdomain: str,
    #dbs: dict = Depends(get_db_names),  # ✅ Ensure `Depends` is resolved correctly
):
    """Login logic - Queries usertable where user_name, password, and mainurl (subdomain) match"""
  

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
        query = text("""select * from vowconsole3.con_user_master cum
        left join vowconsole3.con_org_master com on com.con_org_id = cum.con_org_id
        where com.active = 1 and com.con_org_master_status = 3 and con_org_main_url
        = :host and con_user_login_email_id = :username""")
        print('querr', query)
        user = session.execute(query, {"host": host, "username": username}).fetchone()
        print('queruserr', query, user)

        if not user or not verify_password(password, user.con_user_login_password):
            return {
                "access_token": "",
                "token_type": "",
                "status_code": 401,  # Unauthorized
                "message": "Invalid username or password"
            }
        
        
        print('ff', user.con_user_login_password)

        if not verify_password(password, user.con_user_login_password):
            raise HTTPException(status_code=401, detail="Invalid username or credentials")

        #token = create_access_token({"sub": username})
        #token = create_access_token({"sub": username, "user_id": user.con_user_id})
        token = create_access_token({"user_id": user.con_user_id})

        user_id=user.con_user_id

    response = Response(
        content="Login successful",
        status_code=200  # Success
    )
    response.set_cookie(key="access_token", value=token, httponly=True, secure=True)
    return response