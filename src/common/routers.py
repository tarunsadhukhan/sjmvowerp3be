from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from src.database import get_db
from src.common.schemas import CountrySchema,StateSchema,CountryResponseSchema,StateResponseSchema
from src.common.utils import execute_query, create_response
router = APIRouter()

# ✅ Fetch All Countries API

 

@router.get("/countries",response_model=CountryResponseSchema)
def get_countries(db: Session = Depends(get_db)):
    """
    Fetch all countries.
    """
    try:
        query = "SELECT country_id, country_name FROM con_country_master"
        #countries = db.execute(text(query)).mappings().all()
        #return create_response(data=countries)  # ✅ Standardized response
    
        countries = execute_query(db, query)
        return {"data": countries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
# ✅ Fetch All States API
@router.get("/states", response_model=StateResponseSchema)
def get_states(
    db: Session = Depends(get_db),
    country_id: int = Query(None, description="Filter by Country ID")
):
    
    try:
        query = """SELECT state_id, state_name FROM 
        con_state_master WHERE 1=1"""
        
        params = {}

        # ✅ Dynamically build the query based on provided filters
        if country_id is not None:
            query += " AND country_id = :country_id"
            params["country_id"] = country_id
        
        print('query',query,params)
       
        

       
        states = execute_query(db, query,params)
        print('states',states)
        return {"data": states}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/countries1", response_model=list[CountrySchema])
def get_states(
    db: Session = Depends(get_db),
    country_id: int = Query(None, description="Filter by Country ID")
):
    """
    Fetch states based on multiple optional query parameters:
    - country_id: Filter by country ID
    - is_active: Filter by active/inactive states
    - status: Filter by state status (e.g., "approved", "pending")
    """
    try:
        query = (
            "SELECT  country_id,country_name "
            "FROM con_country_master WHERE 1=1"
        )
        params = {}

        # ✅ Dynamically build the query based on provided filters
        if country_id is not None:
            query += " AND country_id = :country_id"
            params["country_id"] = country_id
        
      
        # ✅ Execute query with safe parameter binding
        #result = db.execute(text(query), params).fetchall()
        

        # ✅ Convert result into JSON-compatible format
        #states = [{"state_id": row[0], "state_name": row[1], "country_id": row[2], "state_code": row[3]} for row in result]

        #countries = db.execute(text(query), params).mappings().all()
        
        #return create_response(data:countries)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
