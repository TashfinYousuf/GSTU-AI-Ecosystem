# backend_v2/app/core/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fetch the direct PostgreSQL connection string
SQLALCHEMY_DATABASE_URL = os.getenv("SUPABASE_DB_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("⚠️ SUPABASE_DB_URL is missing in .env file!")

# Create Engine (PostgreSQL Engine)
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all database models
Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()