from sqlalchemy import Table, Column, Integer, String,Text, DateTime, Boolean, JSON
from src.database import metadata
from sqlalchemy.sql import func
from src.database import Base  # Ensure Base is imported from your database setup



# ✅ Country Master Table
country = Table(
    "con_country_master",
    metadata,
    Column("country_id", Integer, primary_key=True, index=True),
    Column("country_name", String(100), nullable=False)
)

status = Table(
    "con_status_master",
    metadata,
    Column("con_status_id", Integer, primary_key=True, index=True),
    Column("con_status_name", String(100), nullable=False)
)





class ConOrgMaster(Base):
    __tablename__ = "con_org_master"

    id = Column(Integer, primary_key=True, index=True)
    con_org_name = Column(String(255), nullable=False)
    con_org_address = Column(String(255), nullable=False)
    con_org_pincode = Column(String(10), nullable=True)
    con_org_state_id = Column(Integer, nullable=True)
    con_org_country_id = Column(Integer, nullable=True)
    con_org_email_id = Column(String(255), nullable=True)
    con_org_mobile = Column(String(20), nullable=True)
    con_org_contact_person = Column(String(255), nullable=True)
    con_org_shortname = Column(String(50), nullable=True)
    con_org_remarks = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    con_org_master_status = Column(Integer, default=1)
    created_date_time = Column(DateTime, default=func.now())
    con_modules_selected = Column(JSON, nullable=True)
    custom_modules = Column(Text, nullable=True)
