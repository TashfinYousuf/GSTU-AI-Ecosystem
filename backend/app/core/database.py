# backend_v2/app/core/database.py
import os
import logging
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

logger = logging.getLogger("gstu_database")

# Load environment variables
load_dotenv()

# Initialize Supabase client if credentials exist
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.warning(f"Could not initialize Supabase client: {e}")

# Direct PostgreSQL connection string
raw_db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")

engine = None
SessionLocal = None
Base = declarative_base()

if raw_db_url:
    db_url = raw_db_url.strip()

    # 1. Normalize legacy 'postgres://' schema
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # 2. Driver resolution: check if psycopg (v3) or psycopg2 is available
    if db_url.startswith("postgresql://") and "+psycopg" not in db_url:
        try:
            import psycopg  # psycopg 3 available
        except ImportError:
            try:
                import psycopg2  # fallback to psycopg2-binary
                db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            except ImportError:
                logger.warning("Neither psycopg nor psycopg2-binary detected.")

    try:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=5,
            max_overflow=10
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("✅ PostgreSQL SQLAlchemy engine initialized successfully.")
    except Exception as e:
        logger.error(f"⚠️ Warning: SQLAlchemy engine initialization failed: {e}")
        engine = None
        SessionLocal = None
else:
    logger.info("ℹ️ SUPABASE_DB_URL/DATABASE_URL not configured. Running in decoupled/Supabase REST mode.")

# Dependency for FastAPI routes
def get_db():
    if not SessionLocal:
        raise RuntimeError("PostgreSQL database session is not configured or SUPABASE_DB_URL is missing.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()