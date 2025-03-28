from fastapi import Request, HTTPException
from sqlmodel import Session, create_engine
from sqlalchemy.sql import text
from dotenv import load_dotenv
import os
import pymysql

# Load environment variables
load_dotenv("env/database.env")

def get_engine(db_url: str):
    return create_engine(db_url, pool_pre_ping=True)

# Default (main) database connection

DEFAULT_DATABASE_URL = f"mysql+pymysql://{os.getenv('DATABASE_USER')}:{os.getenv('DATABASE_PASSWORD')}@" \
                       f"{os.getenv('DATABASE_HOST')}:{os.getenv('DATABASE_PORT')}/{os.getenv('DATABASE_DEFAULT')}"
print ('DE',DEFAULT_DATABASE_URL)                       
default_engine = get_engine(DEFAULT_DATABASE_URL)

def get_db_names(request: Request):
    """Fetches dynamic database mappings and assigns database engines."""
    #host = "vowsls3.vowerp.co.in"
    host = request.headers.get("X-Subdomain", "default")  # ✅ Extract from headers
    subdomain = host.split(".")[0] if "." in host else "default"
    print(f"Extracted subdomain: {subdomain}")  # Debugging

    db_engines = {"default": default_engine}
    db_names_array = []  # ✅ Array to store database names


    print("Final Database Mappings:", db_engines)
    print("Final Database Names Array:", db_names_array)

    return {
        "db_engines": db_engines,  # ✅ Return dictionary of database engines
        "db_names_array": db_names_array  # ✅ Return array of database names
    }

# Dependency function to get the correct database session
def get_db(request: Request):
    """Returns the correct database session dynamically."""
    db_engines = get_db_names(request)
    yield db_engines
