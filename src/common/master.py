from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from src.database import get_db
from src.common.schemas import CountrySchema,StateSchema,StatusSchema

router = APIRouter()

# ✅ Fetch All Countries API

def create_response(data=None, message="Success", status="success"):
    return { "data": data}

@router.get("/status", response_model=list[StatusSchema])
def get_all_countries(db: Session = Depends(get_db)):
    try:
        query = "SELECT con_status_id,con_status_name FROM con_status_master"
        result = db.execute(text(query)).fetchall()

        params=[]
        # ✅ Convert result into a list of dictionaries
        data = db.execute(text(query),params).mappings().all()

        #data = [{"con_status_id": row[0], "con_status_name": row[1]} for row in result]

        return data # ✅ Correct JSON response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 