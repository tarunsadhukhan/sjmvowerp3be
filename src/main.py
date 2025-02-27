# src/main.py

from fastapi import FastAPI
from .database import Base, engine  # We'll create these soon

# For demonstration, ensure that our models are recognized so SQLAlchemy can create tables
# If you have models in models.py, import them here
from . import models

app = FastAPI()

# # Create database tables at startup (only for local dev/test usage)
# @app.on_event("startup")
# def on_startup():
#     Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "Welcome to our FastAPI application!"}

@app.get("/health")
def read_health():
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception:
        return {"status": "error", "database": "not connected"}

@app.get("/debug-database-url")
def debug_database_url():
    from .database import SQLALCHEMY_DATABASE_URL
    return {"database_url": SQLALCHEMY_DATABASE_URL}

# main.py

from fastapi import FastAPI
from .database import Base, engine, test_db_connection

app = FastAPI()

@app.on_event("startup")
def on_startup():
    # Optional: create tables if needed (for development/testing)
    Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "Welcome to our FastAPI application!"}

@app.get("/testdbconnection")
def test_db_connection_route():
    result = test_db_connection()
    if result["success"]:
        return {"message": "DB connection is successful."}
    else:
        return {
            "message": "DB connection failed.",
            "reason": result["error"]
        }


# @app.get("/items/{item_id}")
# def read_item(item_id: int):
#     return {"item_id": item_id, "description": "An example item."}
