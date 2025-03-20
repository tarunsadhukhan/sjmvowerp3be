from pydantic import BaseModel

# ✅ Define Login Request Schema in models.py
class LoginRequest(BaseModel):
    username: str
    password: str
    logintype: str  # ✅ Ensure this matches frontend request key
  
