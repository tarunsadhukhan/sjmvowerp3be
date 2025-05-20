from pydantic import BaseModel
from typing import List, Optional

class SubMenuItem(BaseModel):
    id: int
    title: str
    path: Optional[str] = None  # Changed to Optional to allow None values
    icon: Optional[str] = None

class MenuItem(BaseModel):
    id: int
    title: str
    path: Optional[str] = None  # Changed to Optional to allow None values
    icon: Optional[str] = None
    submenu: Optional[List[SubMenuItem]] = None

class MenuResponse(BaseModel):
    data: List[MenuItem]

class CoCreate(BaseModel):
    co_name: str
    co_prefix: str
    co_address1: str
    co_address2: Optional[str] = None
    co_zipcode: int
    country_id: int
    state_id: int
    city_id: int
    co_logo: Optional[str] = None
    co_cin_no: Optional[str] = None
    co_email_id: Optional[str] = None
    co_pan_no: Optional[str] = None
    s3bucket_name: Optional[str] = None
    s3folder_name: Optional[str] = None
    tally_sync: Optional[str] = None
    alert_email_id: Optional[str] = None
    co_id: Optional[str] = None  # Added for edit operations

class BranchCreate(BaseModel):
    branch_name: str
    co_id: int
    branch_address1: str
    branch_address2: Optional[str] = None
    branch_zipcode: int
    country_id: int
    state_id: int
    city_id: int
    gst_no: Optional[str] = None
    contact_no: Optional[int] = None
    contact_person: Optional[str] = None
    branch_email: Optional[str] = None
    active: Optional[bool] = True  # Default to True if not provided
    gst_verified: Optional[bool] = False  # Default to False if not provided
    branch_id: Optional[int] = None  # Added for edit operations



