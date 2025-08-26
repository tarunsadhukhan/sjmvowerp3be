from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import os
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, Depends, Cookie, Request, Response
import jwt
from sqlalchemy import text


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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
 

def create_refresh_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt




def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password (str): The plain text password to hash
        
    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)

def decode_access_token(token: str) -> str:
        # Example implementation
        # Decode the token and return the username or relevant data
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token: Missing username")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
# Removed invalid return statement outside of a function


def verify_access_token(access_token: str = Cookie(None, alias="access_token")) -> dict:
    print(f"Received access_token: {access_token}")  # Debug
    if not access_token:
        raise HTTPException(status_code=403, detail="No access token cookie provided")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"Decoded payload: {payload}")  # Debug
        exp = payload.get("exp")
        if exp and datetime.utcnow() > datetime.utcfromtimestamp(exp):
            raise HTTPException(status_code=401, detail="Token has expired")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        print(f"Token verification failed: {str(e)}")  # Debug
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

def get_current_user_with_refresh(
    request: Request,
    response: Response,
    access_token: str = Cookie(None, alias="access_token")
) -> dict:
    if not access_token:
        raise HTTPException(status_code=403, detail="No access token cookie provided")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        try:
            expired_payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            user_id = expired_payload.get("user_id")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token: no user_id")
            from src.config.db import Session as DBSession, default_engine
            with DBSession(default_engine) as session:
                result = session.execute(
                    text("SELECT refresh_token FROM con_user_master WHERE con_user_id = :user_id AND active = 1"),
                    {"user_id": user_id}
                ).fetchone()
                if not result or not result[0]:
                    raise HTTPException(status_code=401, detail="No refresh token found")
                stored_token = result[0]
                jwt.decode(stored_token, SECRET_KEY, algorithms=[ALGORITHM])
                new_access_token = create_access_token({"user_id": user_id})
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
                return {"user_id": user_id}
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Refresh token expired")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid refresh token: {str(e)}")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

