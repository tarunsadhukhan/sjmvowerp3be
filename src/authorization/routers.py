from fastapi import APIRouter, Request, HTTPException, Header  # Add Header to the imports
from starlette.status import HTTP_401_UNAUTHORIZED
from fastapi.responses import JSONResponse
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
import os
from src.authorization.utils import (
    decode_access_token,
    verify_access_token,
    create_access_token,
    SECRET_KEY,
    ALGORITHM
)
from src.authorization.auth import login_user, login_user_console
from src.config.db import default_engine
from datetime import datetime
import jwt

from src.authorization.models import LoginRequest
common_router = APIRouter()


@common_router.post("/login")
def login_route(request: Request, login_data: LoginRequest):
    """Login Route (calls login_user from auth.py)"""
    print("\n=== Starting Login Process ===")
    print(f"🔄 Received login request for user: {login_data.username}")
    print(f"🔍 Login type: {login_data.logintype}")
    print(f"🔒 Remember me: {login_data.rememberMe}")

    # Extract subdomain
    subdomain = request.headers.get("X-Subdomain", "default")
    print(f"🌐 Using subdomain: {subdomain}")
    
    # Print all headers for debugging
    print("\n📋 Request Headers:")
    for header, value in request.headers.items():
        print(f"   {header}: {value}")
    
    try:
        result = login_user(
            request,
            login_data.username,
            login_data.password,
            login_data.logintype,
            subdomain
        )
        print("✅ Login function completed successfully")
        return result
    except Exception as e:
        print(f"❌ Login error in router: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        raise

@common_router.post("/loginconsole")
def login_console_route(request: Request, login_data: LoginRequest):
    """Login Route (calls login_user_console from auth.py)"""
    print("Login User")

    # ✅ Extract `X-Subdomain` before calling `login_user()`
    subdomain = request.headers.get("X-Subdomain", "default")
    print(f"DEBUG: Extracted Subdomain = {subdomain}")  # Debugging
    print('hhhsub=====',subdomain)
    return login_user_console(
        request,
        login_data.username,
        login_data.password,
        login_data.logintype,
        subdomain  # ✅ Pass extracted subdomain
    )




@common_router.get("/protected")
def protected_route(request: Request, authorization: str = Header(None)):
    """Protected Route"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    username = decode_access_token(token)  # Decode the token to get the username
    return {"message": f"Hello, {username}"}

@common_router.get("/verify-session")
async def verify_session(request: Request):
    """
    Verify session validity.
    Returns 200 { ok: true } if valid, 401 if not.
    """
    try:
        access_token = request.cookies.get("access_token")

        # Try to verify access token first if it exists
        if access_token:
            try:
                payload = verify_access_token(access_token)
                return {"ok": True}
            except HTTPException as he:
                if he.status_code != 401:
                    raise
                
                # Access token is expired, try refresh using stored token
                try:
                    # Get user_id from expired token to look up refresh token
                    expired_payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
                    user_id = expired_payload.get("user_id")

                    if not user_id:
                        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

                    # Get refresh token from database
                    with Session(default_engine) as session:
                        result = session.execute(
                            text("""
                                SELECT refresh_token 
                                FROM con_user_master 
                                WHERE con_user_id = :user_id
                                AND active = 1
                            """),
                            {"user_id": user_id}
                        ).fetchone()

                        # Verify stored refresh token exists and is valid
                        if not result or not result[0]:
                            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)
                            
                        stored_token = result[0]
                        
                        # Verify the stored refresh token is still valid
                        try:
                            jwt.decode(stored_token, SECRET_KEY, algorithms=[ALGORITHM])
                        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

                        # Create new access token
                        new_access_token = create_access_token({"user_id": user_id})

                        # Create response with just ok:true
                        response = JSONResponse(content={"ok": True})

                        # Set only the new access token cookie
                        ENV = os.getenv("ENV", "development")
                        COOKIE_DOMAIN = ".vowerp.co.in" if ENV == "production" else None
                        SECURE = True if ENV == "production" else False
                        SAMESITE = "None" if ENV == "production" else "Lax"

                        response.set_cookie(
                            key="access_token",
                            value=new_access_token,
                            httponly=True,
                            secure=SECURE,
                            samesite=SAMESITE,
                            path="/",
                            domain=COOKIE_DOMAIN
                        )

                        return response

                except:
                    raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)