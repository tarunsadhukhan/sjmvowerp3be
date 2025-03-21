from fastapi import APIRouter, Request, HTTPException
from src.authorization.auth import login_user,login_user_console # ✅ Correct import


from src.authorization.models import LoginRequest
common_router = APIRouter()


@common_router.post("/login")
def login(request: Request, login_data: LoginRequest):
    """Login Route (calls login_user from auth.py)"""
    print("Login User")

    # ✅ Extract `X-Subdomain` before calling `login_user()`
    subdomain = request.headers.get("X-Subdomain", "default")
    print(f"DEBUG: Extracted Subdomain = {subdomain}")  # Debugging
    print('hhhsub',subdomain)
    return login_user(
        request,
        login_data.username,
        login_data.password,
        login_data.logintype,
        subdomain  # ✅ Pass extracted subdomain
    )

@common_router.post("/loginconsole")
def login(request: Request, login_data: LoginRequest):
    """Login Route (calls login_user from auth.py)"""
    print("Login User")

    # ✅ Extract `X-Subdomain` before calling `login_user()`
    subdomain = request.headers.get("X-Subdomain", "default")
    print(f"DEBUG: Extracted Subdomain = {subdomain}")  # Debugging
    print('hhhsub',subdomain)
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
    username = decode_access_token(token)
    return {"message": f"Hello, {username}"}
