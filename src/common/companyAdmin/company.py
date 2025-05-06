from fastapi import Depends, Request, HTTPException,APIRouter, Query
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_db_names,default_engine, get_tenant_db
from src.authorization.utils import verify_access_token
from src.common.ctrldskAdmin.schemas import MenuResponse, OrgCreate
from src.common.companyAdmin.models import ConMenuMaster, ConUserRoleMapping, ConRoleMenuMap, ConOrgMaster
from src.common.query import get_co_all_query, get_co_all_count_query, get_org_by_id_query, get_org_modules_query,all_countries_query, get_all_modules_query, all_states_query, get_all_status_query
from typing import Optional, List
from pydantic import BaseModel


router = APIRouter()

@router.get("/get_co_data_all")
async def getOrgsFull(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    search: Optional[str] = None,
    token_data: dict = Depends(verify_access_token),  # Use the new dependency  
    db: Session = Depends(get_tenant_db)
    ):
    offset = (page - 1) * limit
    try:

            query = get_co_all_query(search, offset, limit)
            # text(f"SELECT con_menu_id, con_menu_name, con_menu_parent_id FROM con_menu_master where active =1")
            params = {
                "search": f"%{search}%" if search else None,
                "limit": limit,
                "offset": offset
            }
            query_count = get_co_all_count_query(search)
            count_params = {
                "search": f"%{search}%" if search else None
            }
            coData = db.execute(query, params).fetchall()
            result_count = db.execute(query_count, count_params).scalar()
            # total_count = session.execute(count_query, count_params).scalar()
            result = [dict(r._mapping) for r in coData]
            return {
                "data": result,
                "total": result_count,
            }

    except HTTPException as he:
        print(f"HTTP Exception in get_users_tenant_admin: {str(he)}")
        raise
    except Exception as e:
        print(f"Unexpected error in get_users_tenant_admin: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    
    # # ---------------------------------------------------------------------------
    # # Schemas
    # # ---------------------------------------------------------------------------
    # class OrgCreate(BaseModel):
    #     org_name: str
    #     org_code: str
    #     description: Optional[str] = None
    #     is_active: bool = True


    # class OrgUpdate(BaseModel):
    #     org_name: Optional[str] = None
    #     org_code: Optional[str] = None
    #     description: Optional[str] = None
    #     is_active: Optional[bool] = None


    # # ---------------------------------------------------------------------------
    # # End-points
    # # ---------------------------------------------------------------------------
    # ---------------------------------------------------------------------------
    # End-points
    # ---------------------------------------------------------------------------


# @router.get("/get_org_data_by_id/{org_id}")
# async def get_org_data_by_id(
#     org_id: int,
#     token_data: dict = Depends(verify_access_token),
# ):
#     try:
#         with Session(default_engine) as session:
#             query = get_org_by_id_query(org_id)
#             org_details = session.execute(query, {"org_id": org_id}).fetchone()
#             # if not org_details:
#             #     raise HTTPException(status_code=404, detail="Organisation not found")

#             selected_org_modules = session.execute(
#                 get_org_modules_query(org_id), {"org_id": org_id}
#             ).fetchall()

#             all_modules = session.execute(get_all_modules_query()).fetchall()
#             countries   = session.execute(all_countries_query()).fetchall()
#             states      = session.execute(all_states_query()).fetchall()
#             status_all  = session.execute(get_all_status_query()).fetchall()

#             return {
#                 "data": dict(org_details._mapping),
#                 "selectedModules": [dict(m._mapping) for m in selected_org_modules],
#                 "allModules":      [dict(m._mapping) for m in all_modules],
#                 "countries":       [dict(c._mapping) for c in countries],
#                 "states":          [dict(s._mapping) for s in states],
#                 "statusAll":       [dict(st._mapping) for st in status_all],
#             }
#     except HTTPException:
#         raise
#     except Exception as exc:
#         print(f"Unexpected error in get_org_data_by_id: {exc}")
#         import traceback; traceback.print_exc()
#         raise HTTPException(status_code=500, detail="Internal server error")
    

# @router.get("/create_org_setup_data")
# async def create_org_setup_data(
#     # org_id: int,
#     token_data: dict = Depends(verify_access_token),
# ):
#     try:
#         with Session(default_engine) as session:
#             all_modules = session.execute(get_all_modules_query()).fetchall()
#             countries   = session.execute(all_countries_query()).fetchall()
#             states      = session.execute(all_states_query()).fetchall()
#             status_all  = session.execute(get_all_status_query()).fetchall()
#             return {
#                 "allModules":      [dict(m._mapping) for m in all_modules],
#                 "countries":       [dict(c._mapping) for c in countries],
#                 "states":          [dict(s._mapping) for s in states],
#                 "statusAll":       [dict(st._mapping) for st in status_all],
#             }
#     except HTTPException:
#         raise
#     except Exception as exc:
#         print(f"Unexpected error in get_org_data_by_id: {exc}")
#         import traceback; traceback.print_exc()
#         raise HTTPException(status_code=500, detail="Internal server error")
    
# @router.post("/create_org_data")
# async def create_org_data(
#     payload: OrgCreate,
#     token_data: dict = Depends(verify_access_token),
# ):
#     """
#     Insert a new organisation record using the ORM model and return its id.
#     """
#     try:
#         with Session(default_engine) as session:
#             # Create the organization first
#             new_org = ConOrgMaster(
#                 con_org_name=payload.con_org_name,
#                 con_org_shortname=payload.con_org_shortname,
#                 con_org_contact_person=payload.con_org_contact_person,
#                 con_org_email_id=payload.con_org_email_id,
#                 con_org_mobile=payload.con_org_mobile,
#                 con_org_address=payload.con_org_address,
#                 con_org_pincode=payload.con_org_pincode,
#                 con_org_state_id=payload.con_org_state_id,
#                 con_org_remarks=payload.con_org_remarks,
#                 active=payload.active,
#                 con_org_master_status=payload.con_org_master_status,
#                 con_org_main_url=payload.con_org_main_url,
#                 created_by=token_data.get("user_id"),
#                 con_modules_selected=payload.con_modules_selected
#             )
#             session.add(new_org)
#             session.flush()  # Get the ID without committing
            
            
#             session.commit()
#             return {"message": "Organisation created", "org_id": new_org.con_org_id}
#     except HTTPException:
#         raise
#     except Exception as exc:
#         print(f"Unexpected error in create_org_data: {exc}")
#         import traceback; traceback.print_exc()
#         raise HTTPException(status_code=500, detail="Internal server error")
    
# @router.post("/edit_org_data")
# async def edit_org_data(
#     payload: OrgCreate,
#     token_data: dict = Depends(verify_access_token),
# ):
#     """
#     Update an existing organisation record and its module mappings.
#     """
#     try:
#         with Session(default_engine) as session:
#             # Make sure the primary-key is supplied in the request body
#             # if not getattr(payload, "org_id", None):
#             #     raise HTTPException(status_code=400, detail="org_id is required for update")

#             org: ConOrgMaster | None = session.get(ConOrgMaster, payload.con_org_id)
#             if org is None:
#                 raise HTTPException(status_code=404, detail="Organisation not found")

#             # Update organization fields
#             org.con_org_name = payload.con_org_name
#             org.con_org_shortname = payload.con_org_shortname
#             org.con_org_contact_person = payload.con_org_contact_person
#             org.con_org_email_id = payload.con_org_email_id
#             org.con_org_mobile = payload.con_org_mobile
#             org.con_org_address = payload.con_org_address
#             org.con_org_pincode = payload.con_org_pincode
#             org.con_org_state_id = payload.con_org_state_id
#             org.con_org_remarks = payload.con_org_remarks
#             org.active = payload.active
#             org.con_org_master_status = payload.con_org_master_status
#             org.con_org_main_url = payload.con_org_main_url
#             org.con_modules_selected = payload.con_modules_selected


            
#             session.commit()
#             return {"message": "Organisation updated", "org_id": org.con_org_id}
#     except HTTPException:
#         raise
#     except Exception as exc:
#         print(f"Unexpected error in edit_org_data: {exc}")
#         import traceback; traceback.print_exc()
#         raise HTTPException(status_code=500, detail="Internal server error")


