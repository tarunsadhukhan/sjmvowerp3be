from fastapi import Depends, Request, HTTPException, APIRouter, Query
from typing import Optional
from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from src.config.db import get_db_names, default_engine
from src.authorization.utils import verify_access_token
from src.common.ctrldskAdmin.schemas  import MenuResponse, PortalMenuMstSchema
from src.common.ctrldskAdmin.models import PortalMenuMst 
from src.common.ctrldskAdmin.query import get_portal_menu_details 
from src.common.ctrldskAdmin.query import portal_parentmenudetails as get_portal_parentmenudetails, portalmodulename
from src.common.ctrldskAdmin.query import  portalmenutypedetails, get_portalmenuname_by_name,get_menu_by_id_query 

router = APIRouter()


@router.get("/portal_menu_details")
async def portal_menu_details(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    search: Optional[str] = None,
):
    print("Starting roles_tenant_admin endpointssss")
    query = get_portal_menu_details(search)
    #print(f"  after query Query: {query}")

    try:
        with Session(default_engine) as session:
            offset = (page - 1) * limit

            query = get_portal_menu_details(search)
            #print(f"Executing query for org_id:  search: {search} {query}")
            roles = session.execute(query, {"limit": limit, "offset": offset, "search": f"%{search}%" if search else None}).fetchall()
            print(f"Query returned {len(roles) if roles else 0} results")
    except Exception as query_error:
        print(f"Query execution error: {query_error}")
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(query_error)}")

    try:
        roles = [dict(r._mapping) for r in roles]
        print(f"Converted {len(roles)} rows to dictionaries")
        total = len(roles)
    except Exception as conversion_error:
        print(f"Data conversion error: {conversion_error}")
        raise HTTPException(status_code=500, detail=f"Data conversion error: {str(conversion_error)}")

    response = []
    for row in roles:
        response.append({
            "menu_id": row.get("menu_id"),
            "menu_name": row.get("menu_name"),
            "parent_id": row.get("parent_id"),
            "parent_name": row.get("parent_name"),
            "active": row.get("active"),
            "module_id": row.get("module_id"),
            "module_name": row.get("con_module_name"),
            "tooltip": {
                "menu_path": row.get("menu_path"),
                "menu_icon": row.get("menu_icon")
            }
        })

    return {"data": response, "total": total}


@router.get("/portal_parentmenudetails")
def portal_parentmenudetails():
    print("Starting roles_parent menu endpoint")

    try:
        with Session(default_engine) as session:
            # Use the imported function to get the SQL query
            query = get_portal_parentmenudetails(moduleId=0)

            #print(f"Executing query: {query}")
            roles = session.execute(query).fetchall()
            #print(f"Query returned {len(roles) if roles else 0} results")
    except Exception as query_error:
        print(f"Query execution error: {query_error}")
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(query_error)}")

    try:
        roles = [dict(r._mapping) for r in roles]
        #print(f"Converted {len(roles)} rows to dictionaries")
    except Exception as conversion_error:
        print(f"Data conversion error: {conversion_error}")
        raise HTTPException(status_code=500, detail=f"Data conversion error: {str(conversion_error)}")

    response = []
    for row in roles:
        response.append({
            "pmenu_id": row.get("menu_id"),
            "pmenu_name": row.get("menu_name"),
            "pmodule_id": row.get("module_id"),
        })

    return response


@router.get("/portalmodulename")
def portal_parentmenudetails():
    print("Starting roles_parent menu endpoint")

    try:
        with Session(default_engine) as session:
            # Use the imported function to get the SQL query
            query = portalmodulename()

            #print(f"Executing query: {query}")
            roles = session.execute(query).fetchall()
            print(f"Query returned {len(roles) if roles else 0} results")
    except Exception as query_error:
        print(f"Query execution error: {query_error}")
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(query_error)}")

    try:
        roles = [dict(r._mapping) for r in roles]
        print(f"Converted {len(roles)} rows to dictionaries")
    except Exception as conversion_error:
        print(f"Data conversion error: {conversion_error}")
        raise HTTPException(status_code=500, detail=f"Data conversion error: {str(conversion_error)}")

    response = []
    for row in roles:
        response.append({
            "module_id": row.get("con_module_id"),
            "module_name": row.get("con_module_name")
        })

    return response

@router.get("/portalmenutypedetails")
def portalmenutypedet():
    print("Starting roles_parent menu endpoint")

    try:
        with Session(default_engine) as session:
            # Use the imported function to get the SQL query
            query = portalmenutypedetails()

            #print(f"Executing query: {query}")
            roles = session.execute(query).fetchall()
            #print(f"Query returned {len(roles) if roles else 0} results")
    except Exception as query_error:
        print(f"Query execution error: {query_error}")
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(query_error)}")

    try:
        roles = [dict(r._mapping) for r in roles]
        print(f"Converted {len(roles)} rows to dictionaries")
    except Exception as conversion_error:
        print(f"Data conversion error: {conversion_error}")
        raise HTTPException(status_code=500, detail=f"Data conversion error: {str(conversion_error)}")

    response = []
    for row in roles:
        response.append({
            "menu_type_id": row.get("menu_type_id"),
            "menu_type": row.get("menu_type")
        })

    return response


@router.get("/portal_allmenu_details")
async def create_portal_allmenu_details(
    # org_id: int,
#    token_data: dict = Depends(verify_access_token),
#    db: Session = Depends(get_tenant_db),
):
    try:
        with Session(default_engine) as session:
            print("Starting fetch_portalmenuname_by_id endpoint")

            modules   = session.execute(portalmodulename()).fetchall()
            print(f"Query returned {len(modules) if modules else 0} results")
            moduleId=0
            parentnams = session.execute(get_portal_parentmenudetails()).fetchall()
            # print(f"Query returned {len(parentnams) if parentnams else 0} results")
            menutypes  = session.execute(portalmenutypedetails()).fetchall()
            # print(f"Query returned {len(menutypes) if menutypes else 0} results")
            return {
                "allModules":       [dict(c._mapping) for c in modules],
                "allparentnames":   [dict(s._mapping) for s in parentnams],
                "menutypes":       [dict(ct._mapping) for ct in menutypes],
            }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Unexpected error in allmenu_data_by_id: {exc}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/portal_allmenu_details_by_id/{co_id}")
async def portal_allmenu_details_by_id(
    co_id: int,
    # org_id: int,
#    token_data: dict = Depends(verify_access_token),
#    db: Session = Depends(get_tenant_db),
):
    try:
        with Session(default_engine) as session:
            print("Starting fetch_portalmenuname_by_id endpoint")

            query = get_menu_by_id_query(co_id)
            menu_details = session.execute(query, {"co_id": co_id}).fetchone()
            moduleId= menu_details.module_id

            modules   = session.execute(portalmodulename()).fetchall()
            print(f"Query returned {len(modules) if modules else 0} results")
            query=get_portal_parentmenudetails()
            parentnams = session.execute(query).fetchall()
            # print(f"Query returned {len(parentnams) if parentnams else 0} results")
            menutypes  = session.execute(portalmenutypedetails()).fetchall()
            # print(f"Query returned {len(menutypes) if menutypes else 0} results")
            return {
                "data": dict(menu_details._mapping),
                "allModules":       [dict(c._mapping) for c in modules],
                "allparentnames":   [dict(s._mapping) for s in parentnams],
                "menutypes":       [dict(ct._mapping) for ct in menutypes],
            }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Unexpected error in allmenu_data_by_id: {exc}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")



@router.get("/portalmenuname/{name}/{menu_id}")
async def fetch_portalmenuname_by_id(
    name: str,
    menu_id: int,
):
    print(f"Starting fetch_portalmenuname_by_id endpoint with name: {name},{menu_id}")

    try:
        with Session(default_engine) as session:
            # Execute the query with the provided name parameter
            query = get_portalmenuname_by_name(name,menu_id)
            print(f"Executing query: {query}")
            if menu_id == 0:
                result = session.execute(query, {"name": name}).fetchone()
            else:
                result = session.execute(query, {"name": name, "menu_id": menu_id}).fetchone()  
            # print(f"Query returned: {result}")

            # Check if the result is None
            if not result:
                return {"data": {"isDuplicate": False}, "count": 0}

            # Convert the result to a dictionary
            response = dict(result._mapping)

            # Determine if the menu name is a duplicate
            is_duplicate = response.get("count", 0) > 0

            return {"data": {"isDuplicate": is_duplicate}}

    except Exception as query_error:
        print(f"Query execution error: {query_error}")
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(query_error)}")



@router.post("/portalmenucreate")
async def create_portalmenucreate_data(
    request: Request,
    payload: PortalMenuMstSchema,
    token_data: dict = Depends(verify_access_token),
):
    print("Starting create_portalmenucreate_data endpoint",request)
    print(f"Starting create_portalmenucreate_data endpoint with payload: {payload}")

    """
    Insert a new portal menu record using the ORM model and return its id.
    """
    try:
        with Session(default_engine) as session:
            # Create a new portal menu entry
            new_menu = PortalMenuMst(
                menu_name=payload.menu_name,
                menu_path=payload.menu_path,
                active=payload.active,
                menu_parent_id=payload.menu_parent_id,
                menu_type_id=payload.menu_type_id,
                menu_icon=payload.menu_icon,
                module_id=payload.module_id,
                order_by=payload.order_by,
            )

            session.add(new_menu)
            session.flush()  # Get the ID without committing
            session.commit()

            return {
                "message": f"Portal menu Created successfully for {payload.menu_name}",
                "menu_id": new_menu.menu_id,
                "menu_name": payload.menu_name,
                #"module_name": payload.module_name,
                #"parent_name": payload.parent_name,
            }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Unexpected error in create_portalmenucreate_data: {exc}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(exc)}")



@router.post("/portalmenuedit")
async def create_portalmenucreate_data(
    request: Request,
    payload: PortalMenuMstSchema,
    token_data: dict = Depends(verify_access_token),
):

    try:
        with Session(default_engine) as session:
            # Extract co_id from the payload
            menu_id = payload.dict().get("menu_id")
            if menu_id is None:
                raise HTTPException(status_code=400, detail="menu_id is required in the payload")
            
            # Convert menu_id to int if it's a string
            if isinstance(menu_id, str):
                try:
                    menu_id = int(menu_id)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid menu_id format")

            # Get the existing menu
            menu = session.query(PortalMenuMst).filter(PortalMenuMst.menu_id == menu_id).first()
            if menu is None:
                raise HTTPException(status_code=404, detail="Menu not found")

            # Update the menu fields
            menu.menu_name = payload.menu_name
            menu.menu_path = payload.menu_path
            menu.active = payload.active
            menu.menu_parent_id = payload.menu_parent_id
            menu.menu_type_id = payload.menu_type_id
            menu.menu_icon = payload.menu_icon
            menu.module_id = payload.module_id
            menu.order_by = payload.order_by

            session.commit()
            
            return {"message": "Menu updated successfully for {payload.menu_name}", "menu_id": menu.menu_id}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Unexpected error in edit_menu_data: {exc}")
        import traceback; traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(exc)}")
