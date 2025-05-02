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


