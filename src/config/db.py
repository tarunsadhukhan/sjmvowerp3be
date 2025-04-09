from fastapi import Request
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
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

# Create a sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=default_engine)

# Export the Session class
Session = SQLAlchemySession

# Default database name variables - used by other modules
# Setting default values that will be overridden during request processing
db = "default"  
db1 = "default_c"
db2 = "default_c_1"
db3 = "default_c_2"
db4 = "default_c_3"

def get_db_names(request: Request):
    """Fetches dynamic database mappings and assigns database engines."""
    subdomain = request.headers.get("X-Subdomain", "default")  # ✅ Extract from headers
    print(f"Extracted subdomain from db.py: {subdomain}")  # Debugging

    db_engines = {"default": default_engine}
    
    # Calculate database names based on subdomain
    global db, db1, db2, db3, db4  # Access the global variables
    db = subdomain
    db1 = subdomain + "_c"
    db2 = subdomain + "_c_1"
    db3 = subdomain + "_c_2"
    db4 = subdomain + "_c_3"

    print("Final Database Mappings:", db_engines)

    return {
        "db_engines": db_engines,  # ✅ Return dictionary of database engines
        "db": db,
        "db1": db1,
        "db2": db2,
        "db3": db3,
        "db4": db4,
        # ✅ Return array of database names
    }

# Dependency function to get the correct database session
def get_db(request: Request):
    """Returns the correct database session dynamically."""
    db_engines = get_db_names(request)
    yield db_engines
