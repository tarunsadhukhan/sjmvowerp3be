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

    print("Host:", host)

    with Session(default_engine) as session:
        query = text("""select * from vowconsole3.con_db_master cdm 
        left join vowconsole3.con_org_master com on com.con_org_id =cdm.con_org_id
        where com.active =1 and com.con_org_master_status =3 and con_org_main_url
        = :host   order by cdm.con_db_sl """)
        db_data = session.execute(query, {"host": host}).fetchall()
    
    print('query',query)    

    print("Raw Query Results:", db_data)  

    database_names = {"maindatabase": os.getenv('DATABASE_DEFAULT')}
    db_engines = {"default": default_engine}
    db_names_array = []  # ✅ Array to store database names

    for idx, row in enumerate(db_data, start=1):
        db_name = row[1]  # Extract database name
        print(f"Assigning db{idx}: {db_name}")
        db_names_array.append(db_name)  # ✅ Add to array
        print(f"Assigning db{idx}: {db_name}")

        # Create a database connection for each fetched DB
        db_url = f"mysql+pymysql://{os.getenv('DATABASE_USER')}:{os.getenv('DATABASE_PASSWORD')}@" \
                 f"{os.getenv('DATABASE_HOST')}:{os.getenv('DATABASE_PORT')}/{db_name}"
        db_engines[f"db{idx}"] = get_engine(db_url)

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
