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


class OrgCreate(BaseModel):
    con_org_name: str
    con_org_shortname: str
    con_org_contact_person: str
    con_org_email_id: str
    con_org_mobile: str
    con_org_address: str
    con_org_pincode: int
    con_org_state_id: int
    con_org_remarks: Optional[str] = ""
    active: str
    con_org_master_status: int
    con_modules_selected: List[str]
    con_org_main_url: str
    con_org_id: Optional[int] = None  # For edit operations


