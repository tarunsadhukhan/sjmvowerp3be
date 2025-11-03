import logging
import os
import jwt
from fastapi import Depends, HTTPException, APIRouter, Response, Cookie
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.config.db import get_tenant_db
from src.authorization.utils import create_access_token, SECRET_KEY, ALGORITHM
from src.common.portal.query import get_portal_user_menus

router = APIRouter()
logger = logging.getLogger(__name__)


def get_portal_token_payload(
    access_token: str = Cookie(None, alias="access_token")
) -> dict:
    if not access_token:
        raise HTTPException(status_code=403, detail="No access token cookie provided")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        payload["access_expired"] = False
        return payload
    except jwt.ExpiredSignatureError:
        try:
            payload = jwt.decode(
                access_token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"verify_exp": False},
            )
            payload["access_expired"] = True
            return payload
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(exc)}") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(exc)}") from exc

@router.get("/portal_menu_items")
async def compmenuitems(
    response: Response,
    token_data: dict = Depends(get_portal_token_payload),
    tenant_session: Session = Depends(get_tenant_db),
):
    user_id = token_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="User ID not found in token")
    logger.debug("Authorized portal menu request for user %s", user_id)
    try:
        if token_data.get("access_expired"):
            refresh_result = tenant_session.execute(
                text("SELECT refresh_token FROM user_mst WHERE user_id = :user_id AND active = 1"),
                {"user_id": user_id},
            ).fetchone()
            if not refresh_result or not refresh_result[0]:
                raise HTTPException(status_code=401, detail="No refresh token found")

            refresh_token = refresh_result[0]
            try:
                jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            except jwt.ExpiredSignatureError as exc:
                raise HTTPException(status_code=401, detail="Refresh token expired") from exc
            except jwt.InvalidTokenError as exc:
                raise HTTPException(status_code=401, detail=f"Invalid refresh token: {str(exc)}") from exc

            new_payload = {"user_id": user_id}
            if token_data.get("type"):
                new_payload["type"] = token_data.get("type")
            new_access_token = create_access_token(new_payload)
            env_value = os.getenv("ENV", "development")
            cookie_domain = ".vowerp.co.in" if env_value == "production" else None
            secure_flag = True if env_value == "production" else False
            samesite_policy = "None" if env_value == "production" else "Lax"
            response.set_cookie(
                key="access_token",
                value=new_access_token,
                httponly=True,
                secure=secure_flag,
                samesite=samesite_policy,
                path="/",
                domain=cookie_domain,
            )

        # Get menus for this user
        menu_query = get_portal_user_menus(user_id=user_id)
        menu_result = tenant_session.execute(menu_query, {"user_id": user_id}).fetchall()
        logger.debug("Found %s menu entries for user %s", len(menu_result), user_id)

        # Process results into nested structure
        companies = {}

        for row in menu_result:
            co_id = row.co_id
            co_name = row.co_name
            branch_id = row.branch_id
            branch_name = row.branch_name
            menu_id = row.menu_id
            menu_name = row.menu_name
            menu_path = row.menu_path
            menu_parent_id = row.menu_parent_id
            access_type_id = row.access_type_id
            
            # Skip if menu is None (could happen if role doesn't have menu mappings)
            if menu_id is None:
                continue

            # Add company if not exists
            if co_id not in companies:
                companies[co_id] = {
                    "co_id": co_id,
                    "co_name": co_name,
                    "branches": {}
                }

            # Add branch if not exists for this company
            if branch_id not in companies[co_id]["branches"]:
                companies[co_id]["branches"][branch_id] = {
                    "branch_id": branch_id,
                    "branch_name": branch_name,
                    "menus": {},
                }
            
            # Add menu to branch
            companies[co_id]["branches"][branch_id]["menus"][menu_id] = {
                "menu_id": menu_id,
                "menu_name": menu_name,
                "menu_path": menu_path,
                "menu_parent_id": menu_parent_id,
                "access_type_id": access_type_id
            }
        
        # Convert to final structure
        result = []
        for co_id, company in companies.items():
            company_data = {
                "co_id": company["co_id"],
                "co_name": company["co_name"],
                "branches": []
            }

            for branch_id, branch in company["branches"].items():
                branch_data = {
                    "branch_id": branch["branch_id"],
                    "branch_name": branch["branch_name"],
                    "menus": list(branch["menus"].values())
                }
                company_data["branches"].append(branch_data)

            result.append(company_data)
        
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error getting portal menu items for user %s", user_id)
        raise HTTPException(status_code=500, detail="Error getting portal menu items") from exc

