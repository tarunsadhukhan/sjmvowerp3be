from sqlalchemy import Table, Column, Integer, String
from src.database import metadata

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