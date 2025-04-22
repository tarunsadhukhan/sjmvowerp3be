from src.authorization.utils import create_access_token, create_refresh_token, verify_password
from fastapi import Request, HTTPException, Response  # ✅ Import Response
from sqlalchemy.sql import text
from src.config.db import get_db_names,default_engine  # ✅ Ensure correct import
from src.config.db import Session  # ✅ Import default_engine
from fastapi.responses import JSONResponse  # ✅ Import JSONResponse
from src.authorization.query import get_admin_login_query, get_company_admin_login_query
import os

def login_user_console(
    request: Request,
    username: str,
    password: str,
    logintype: str,
    subdomain: str,
):
    """Login logic - Queries user table where username, password, and subdomain match"""
    try:
        with Session(default_engine) as session:
            # Get appropriate query based on subdomain
            query = get_admin_login_query() if subdomain == 'admin' else get_company_admin_login_query()
            
            # Execute query and get user
            result = session.execute(query, {"username": username})
            user = result.fetchone() if result else None
            
            # Validate user exists and password matches
            if not user or not hasattr(user, 'con_user_login_password') or not verify_password(password, user.con_user_login_password):
                return JSONResponse(
                    content={
                        "access_token": "",
                        "token_type": "",
                        "status": 401,
                        "message": "Invalid username or password",
                    },
                    status_code=401,
                )

            # Create tokens
            user_id = getattr(user, 'con_user_id', None)
            if not user_id:
                raise HTTPException(status_code=500, detail="User ID not found in database")

            # Create access token for frontend
            token = create_access_token({"user_id": user_id})
            
            # Create refresh token (stored only in DB)
            refresh_token = create_refresh_token({"user_id": user_id})
            
            # Update refresh token in DB only
            try:
                update_query = text("""
                    UPDATE vowconsole3.con_user_master 
                    SET refresh_token = :refresh_token 
                    WHERE con_user_login_email_id = :username
                """)
                session.execute(update_query, {
                    "username": username,
                    "refresh_token": refresh_token
                })
                session.commit()
                print('Refresh token updated in database for:', username)
            except Exception as e:
                print('Error updating refresh token:', str(e))
                raise HTTPException(status_code=500, detail="Failed to update refresh token")

            # Create response with access token only
            response = JSONResponse(
                content={
                    "message": "Login successful",
                    "status": 200,
                    "access_token": token,
                    "user_id": user_id
                },
                status_code=200
            )

            # Set only access token cookie
            ENV = os.getenv("ENV", "development")
            COOKIE_DOMAIN = ".vowerp.co.in" if ENV == "production" else None
            SECURE = True if ENV == "production" else False
            SAMESITE = "None" if ENV == "production" else "Lax"
            
            # Set only access token cookie
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=SECURE,
                samesite=SAMESITE,
                path="/",
                domain=COOKIE_DOMAIN
            )

            return response

    except Exception as e:
        print(f"Login error: {str(e)}")
        return JSONResponse(
            content={
                "access_token": "",
                "token_type": "",
                "status": 500,
                "message": "Internal server error",
            },
            status_code=500,
        )


def login_user(
    request: Request,
    username: str,
    password: str,
    logintype: str,
    subdomain: str,
):
    """Login logic - Queries usertable where user_name, password, and mainurl (subdomain) match"""
    try:
        db_data = get_db_names(request)
        dbs = db_data.get("db_engines", {})
        dbn = db_data.get("db_names_array", [])

        if not dbs or "default" not in dbs:
            return JSONResponse(
                content={
                    "access_token": "",
                    "token_type": "",
                    "status": 500,
                    "message": "Database connection failed",
                },
                status_code=500,
            )

        host = subdomain.strip() if subdomain else None
        if not host:
            return JSONResponse(
                content={
                    "access_token": "",
                    "token_type": "",
                    "status": 400,
                    "message": "Invalid Subdomain",
                },
                status_code=400,
            )

        with Session(default_engine) as session:
            query = text("""
                SELECT * FROM vowconsole3.con_user_master cum
                LEFT JOIN vowconsole3.con_org_master com ON com.con_org_id = cum.con_org_id
                WHERE com.active = 1 
                AND com.con_org_master_status = 3 
                AND com.con_org_main_url = :host 
                AND cum.con_user_login_email_id = :username
            """)
            user = session.execute(query, {"host": host, "username": username}).fetchone()

            if not user or not verify_password(password, getattr(user, 'con_user_login_password', None)):
                return JSONResponse(
                    content={
                        "access_token": "",
                        "token_type": "",
                        "status": 401,
                        "message": "Invalid username or password",
                    },
                    status_code=401,
                )

            # Create access token for frontend
            token = create_access_token({"user_id": user.con_user_id})
            
            # Create refresh token (stored only in DB)
            refresh_token = create_refresh_token({"user_id": user.con_user_id})
            
            # Update refresh token in DB only
            try:
                update_query = text("""
                    UPDATE vowconsole3.con_user_master 
                    SET refresh_token = :refresh_token 
                    WHERE con_user_login_email_id = :username
                """)
                session.execute(update_query, {
                    "username": username,
                    "refresh_token": refresh_token
                })
                session.commit()
            except Exception as e:
                print('Error updating refresh token:', str(e))
                raise HTTPException(status_code=500, detail="Failed to update refresh token")

            # Create response with access token only
            response = JSONResponse(
                content={
                    "message": "Login successful",
                    "status": 200,
                    "access_token": token,
                    "user_id": user.con_user_id
                },
                status_code=200
            )

            # Set only access token cookie
            ENV = os.getenv("ENV", "development")
            COOKIE_DOMAIN = ".vowerp.co.in" if ENV == "production" else None
            SECURE = True if ENV == "production" else False
            SAMESITE = "None" if ENV == "production" else "Lax"
            
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=SECURE,
                samesite=SAMESITE,
                path="/",
                domain=COOKIE_DOMAIN
            )

            return response

    except Exception as e:
        print(f"Login error: {str(e)}")
        return JSONResponse(
            content={
                "access_token": "",
                "token_type": "",
                "status": 500,
                "message": "Internal server error",
            },
            status_code=500,
        )