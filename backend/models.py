from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./expenses.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    google_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    expense_context = Column(String, nullable=True)  # Custom context for expense generation
    created_at = Column(DateTime, default=datetime.utcnow)

    expenses = relationship("Expense", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="categories")

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    materials = Column(String, nullable=True)
    hours = Column(Float, nullable=True)
    category = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="expenses")

def run_migrations():
    """
    Run Alembic migrations automatically on startup.
    """
    from alembic.config import Config
    from alembic import command
    import os
    from pathlib import Path

    try:
        print("🔄 Running database migrations...")

        # Get the directory containing this file
        backend_dir = Path(__file__).parent

        # Create Alembic config
        alembic_cfg = Config(str(backend_dir / "alembic.ini"))

        # Set the script location
        alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))

        # Set the database URL from environment or default
        database_url = os.getenv("DATABASE_URL", "sqlite:///./expenses.db")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)

        # Run migrations to head
        command.upgrade(alembic_cfg, "head")

        print("✅ Database migrations completed successfully")
    except Exception as e:
        print(f"⚠️  Migration warning: {str(e)}")
        # Don't fail startup if migrations have issues
        # This allows the app to start even if migrations fail

def init_db():
    Base.metadata.create_all(bind=engine)
    run_migrations()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
