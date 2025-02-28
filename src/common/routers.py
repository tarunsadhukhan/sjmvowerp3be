from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from src.database import get_db
from src.common.schemas import CountrySchema,StateSchema

router = APIRouter()

# ✅ Fetch All Countries API

def create_response(data=None, message="Success", status="success"):
    return { "data": data}

@router.get("/countries", response_model=list[CountrySchema])
def get_all_countries(db: Session = Depends(get_db)):
    try:
        query = text("SELECT country_id,country_name FROM con_country_master")
        result = db.execute(query).fetchall()

       

        # ✅ Convert result into a list of dictionaries
        countries = [{"id": row[0], "name": row[1]} for row in result]

        return countries  # ✅ Correct JSON response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    
# ✅ Fetch All States API
@router.get("/states", response_model=list[StateSchema])
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
            "SELECT state_id, state_name, country_id, state_code "
            "FROM con_state_master WHERE 1=1"
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

        states = db.execute(text(query), params).mappings().all()

        return states  # ✅ Correct JSON response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
