from datetime import datetime, timedelta
from sqlmodel import Session, select
from passlib.context import CryptContext
import jwt
import os
from fastapi import Depends, Request, HTTPException
from sqlalchemy.sql import text
from src.config.db import get_db_names,default_engine  # ✅ Ensure correct import
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Config
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()  

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials  # Extract token from header
    print('token',token)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")

        if exp and datetime.utcnow() > datetime.utcfromtimestamp(exp):
            raise HTTPException(status_code=401, detail="Token has expired")

        return payload  # ✅ Return the decoded payload (user details)
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
 




def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)




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
    return {
        "access_token": token,
        "token_type": "bearer",
        "status_code": 200,  # Success
        "message": "Login successful",
        "user_id": user_id
    }
        
   


def login_user_console (
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
    
    
 
    
    print('2nd ',request)
    if "default" not in dbs:
        return {
            "access_token": "",
            "token_type": "",
            "status_code": 500,  # Internal Server Error
            "message": "Database connection failed: Default database missing"
        }
        
        
      
        #raise HTTPException(status_code=400, detail="Invalid subdomain")
    
    
   
    #engine = create_engine(dbs["default"])
    with Session(default_engine) as session:
        query = text("""select * from vowconsole3.con_user_master cum
        	where con_user_login_email_id = :username and cum.con_user_id =1
        	and cum.con_user_type =0
        """)
        print('querr', query)
        user = session.execute(query, { "username": username}).fetchone()
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
    return {
        "access_token": token,
        "token_type": "bearer",
        "status_code": 200,  # Success
        "message": "Login successful",
        "user_id": user_id
    }
        
   
