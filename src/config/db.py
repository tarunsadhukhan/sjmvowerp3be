from fastapi import Request
from dotenv import load_dotenv
from sqlalchemy import create_engine
import os

# Load environment variables
try:
    load_dotenv("env/database.env")
except Exception as e:
    print(f"Warning: Could not load database.env file: {e}")

def get_engine(db_url: str):
    try:
        return create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        print(f"Error creating database engine: {e}")
        raise

# Check for required environment variables
required_vars = ['DATABASE_USER', 'DATABASE_PASSWORD', 'DATABASE_HOST', 'DATABASE_PORT', 'DATABASE_DEFAULT']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Default (main) database connection
DEFAULT_DATABASE_URL = f"mysql+pymysql://{os.getenv('DATABASE_USER')}:{os.getenv('DATABASE_PASSWORD')}@" \
                       f"{os.getenv('DATABASE_HOST')}:{os.getenv('DATABASE_PORT')}/{os.getenv('DATABASE_DEFAULT')}"
print('DE', DEFAULT_DATABASE_URL)
default_engine = get_engine(DEFAULT_DATABASE_URL)

def get_db_names(request: Request):
    """Fetches dynamic database mappings and assigns database engines."""
    host = request.headers.get("X-Subdomain", "default")  # ✅ Extract from headers
    subdomain = host.split(".")[0] if "." in host else "default"
    print(f"Extracted subdomain: {subdomain}")  # Debugging

    db_engines = {"default": default_engine}
    db_names_array = []  # ✅ Array to store database names
    
    db_url = subdomain
    db_url1 = subdomain + "_c"
    db_url2 = subdomain + "_c_1"
    db_url3 = subdomain + "_c_2"
    db_url4 = subdomain + "_c_3"

    print("Final Database Mappings:", db_engines)
    print("Final Database Names Array:", db_names_array)

    return {
        "db_engines": db_engines,  # ✅ Return dictionary of database engines
        "db_names_array": db_names_array,
        "db": db_url,
        "db1": db_url1,
        "db2": db_url2,
        "db3": db_url3,
        "db4": db_url4,

        # ✅ Return array of database names
    }

# Dependency function to get the correct database session
def get_db(request: Request):
    """Returns the correct database session dynamically."""
    db_engines = get_db_names(request)
    yield db_engines
