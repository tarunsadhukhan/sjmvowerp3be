from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from src.database import get_db
from src.common.schemas import CountrySchema

router = APIRouter()