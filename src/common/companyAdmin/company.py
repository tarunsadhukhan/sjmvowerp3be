from fastapi import Depends, Request, HTTPException,APIRouter, Query
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_db_names,default_engine, get_tenant_db
from src.authorization.utils import verify_access_token
from src.common.ctrldskAdmin.schemas import MenuResponse, OrgCreate
from src.common.companyAdmin.models import ConMenuMaster, ConUserRoleMapping, ConRoleMenuMap, ConOrgMaster, CoMst
from src.common.companyAdmin.query import get_co_all_query, get_co_all_count_query, get_co_by_id_query
from src.common.companyAdmin.query import get_country_query, get_state_query, get_city_query
from src.common.companyAdmin.schemas import CoCreate
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


@router.get("/get_co_data_by_id/{co_id}")
async def get_org_data_by_id(
    co_id: int,
    token_data: dict = Depends(verify_access_token),
    db: Session = Depends(get_tenant_db),
):
    try:
            query = get_co_by_id_query(co_id)
            org_details = db.execute(query, {"co_id": co_id}).fetchone()
            countries   = db.execute(get_country_query()).fetchall()
            states      = db.execute(get_state_query()).fetchall()
            cities    = db.execute(get_city_query()).fetchall()
            return {
                "data": dict(org_details._mapping),
                "countries":       [dict(c._mapping) for c in countries],
                "states":          [dict(s._mapping) for s in states],
                "cities":          [dict(c._mapping) for c in cities],
            }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Unexpected error in get_org_data_by_id: {exc}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
    

@router.get("/create_co_setup_data")
async def create_org_setup_data(
    # org_id: int,
    token_data: dict = Depends(verify_access_token),
    db: Session = Depends(get_tenant_db),
):
    try:
        with Session(default_engine) as session:
            countries   = db.execute(get_country_query()).fetchall()
            states      = db.execute(get_state_query()).fetchall()
            cities  = db.execute(get_city_query()).fetchall()
            return {
                "countries":       [dict(c._mapping) for c in countries],
                "states":          [dict(s._mapping) for s in states],
                "cities":       [dict(ct._mapping) for ct in cities],
            }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Unexpected error in get_org_data_by_id: {exc}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.post("/create_co_data")
async def create_org_data(
    payload: CoCreate,
    token_data: dict = Depends(verify_access_token),
    db: Session = Depends(get_tenant_db),
):
    """
    Insert a new company record using the ORM model and return its id.
    """
    try:
        # Create the company using the tenant database
        new_company = CoMst(
            co_name=payload.co_name,
            co_prefix=payload.co_prefix,
            co_address1=payload.co_address1,
            co_address2=payload.co_address2,
            co_zipcode=payload.co_zipcode,
            country_id=payload.country_id,
            state_id=payload.state_id,
            city_id=payload.city_id,
            co_logo=payload.co_logo,
            created_by_con_user=token_data.get("user_id"),
            co_cin_no=payload.co_cin_no,
            co_email_id=payload.co_email_id,
            co_pan_no=payload.co_pan_no,
            s3bucket_name=payload.s3bucket_name,
            s3folder_name=payload.s3folder_name,
            tally_sync=payload.tally_sync,
            alert_email_id=payload.alert_email_id,
        )
        
        db.add(new_company)
        db.flush()  # Get the ID without committing
        db.commit()
        
        return {"message": "Company created successfully", "co_id": new_company.co_id}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Unexpected error in create_org_data: {exc}")
        import traceback; traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(exc)}")
    
@router.post("/edit_co_data")
async def edit_co_data(
    payload: CoCreate,
    token_data: dict = Depends(verify_access_token),
    db: Session = Depends(get_tenant_db),
):
    """
    Update an existing company record using the ORM model.
    co_id is expected to be included in the payload.
    """
    try:
        # Extract co_id from the payload
        co_id = payload.dict().get("co_id")
        if co_id is None:
            raise HTTPException(status_code=400, detail="co_id is required in the payload")
        
        # Convert co_id to int if it's a string
        if isinstance(co_id, str):
            try:
                co_id = int(co_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid co_id format")

        # Get the existing company
        company = db.query(CoMst).filter(CoMst.co_id == co_id).first()
        if company is None:
            raise HTTPException(status_code=404, detail="Company not found")

        # Update the company fields
        company.co_name = payload.co_name
        company.co_prefix = payload.co_prefix
        company.co_address1 = payload.co_address1
        company.co_address2 = payload.co_address2
        company.co_zipcode = payload.co_zipcode
        company.country_id = payload.country_id
        company.state_id = payload.state_id
        company.city_id = payload.city_id
        company.co_logo = payload.co_logo
        company.co_cin_no = payload.co_cin_no
        company.co_email_id = payload.co_email_id
        company.co_pan_no = payload.co_pan_no
        company.s3bucket_name = payload.s3bucket_name
        company.s3folder_name = payload.s3folder_name
        company.tally_sync = payload.tally_sync
        company.alert_email_id = payload.alert_email_id
        
        # # Only update active status if it's provided in the payload
        # if payload.active is not None:
        #     company.active = payload.active
        db.commit()
        
        return {"message": "Company updated successfully", "co_id": company.co_id}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Unexpected error in edit_co_data: {exc}")
        import traceback; traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(exc)}")


