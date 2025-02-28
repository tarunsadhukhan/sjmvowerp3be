from pydantic import BaseModel

# ✅ Country Schema for API Response
class CountrySchema(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
        
class StateSchema(BaseModel):
    state_id: int
    state_name: str
    country_id:int
    state_code:str

    class Config:
        from_attributes = True


class StatusSchema(BaseModel):
    con_status_id: int
    con_status_name: str
   
    class Config:
        from_attributes = True
