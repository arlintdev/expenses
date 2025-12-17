from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
import uuid6
import uuid

# Load .env from the backend directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./expenses.db")

# Detect database type and configure accordingly
is_postgres = "postgresql" in DATABASE_URL
is_sqlite = DATABASE_URL.startswith("sqlite")

# Convert sqlite:// to sqlite+aiosqlite:// for async support
if is_sqlite:
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Create async engine with appropriate configuration
if is_postgres:
    # PostgreSQL configuration with connection pooling
    engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=False,
        pool_size=20,  # Maximum number of connections in the pool
        max_overflow=10,  # Allow up to 10 additional connections when pool is exhausted
        pool_pre_ping=True,  # Verify connections before using them
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_timeout=30,  # Wait up to 30s for a connection from the pool
    )
    print("✅ PostgreSQL async engine initialized with connection pooling")
else:
    # SQLite configuration (development/fallback)
    engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=False,
        connect_args={
            "timeout": 30,  # 30 second timeout for database locks
            "check_same_thread": False,  # Allow sharing connection across threads (safe with async)
        },
        pool_pre_ping=True,  # Verify connections before using them
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    # Enable WAL mode for SQLite to allow concurrent reads during writes
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Set SQLite pragmas for better concurrency and performance."""
        cursor = dbapi_conn.cursor()
        # WAL mode allows multiple readers even during a write
        cursor.execute("PRAGMA journal_mode=WAL")
        # Increase cache size for better performance (10MB)
        cursor.execute("PRAGMA cache_size=-10000")
        # Set busy timeout to 30 seconds
        cursor.execute("PRAGMA busy_timeout=30000")
        # Use normal synchronous mode for better performance (still safe with WAL)
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    print("✅ SQLite async engine initialized with WAL mode")

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid6.uuid6()), index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    google_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    expense_context = Column(String, nullable=True)  # Custom context for expense generation
    is_admin = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    expenses = relationship("Expense", back_populates="user", cascade="all, delete-orphan")
    recurring_expenses = relationship("RecurringExpense", back_populates="user", cascade="all, delete-orphan")
    user_tags = relationship("UserTag", back_populates="user", cascade="all, delete-orphan")
    vehicles = relationship("Vehicle", back_populates="user", cascade="all, delete-orphan")
    mileage_logs = relationship("MileageLog", back_populates="user", cascade="all, delete-orphan")

class UserTag(Base):
    """Standalone tags that belong to a user, not tied to specific expenses."""
    __tablename__ = "user_tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid6.uuid6()), index=True)
    name = Column(String, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="user_tags")

class ExpenseTag(Base):
    """Junction table for many-to-many relationship between expenses and user tags."""
    __tablename__ = "expense_tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid6.uuid6()), index=True)
    expense_id = Column(String(36), ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    user_tag_id = Column(String(36), ForeignKey("user_tags.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    expense = relationship("Expense", back_populates="expense_tags")
    user_tag = relationship("UserTag", backref="expense_tags")

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid6.uuid6()), index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    description = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    materials = Column(String, nullable=True)
    hours = Column(Float, nullable=True)
    amount = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    recurring = Column(Boolean, default=False, nullable=False)
    recurring_expense_id = Column(String(36), nullable=True)
    linked_mileage_log_id = Column(String(36), ForeignKey("mileage_logs.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="expenses")
    expense_tags = relationship("ExpenseTag", back_populates="expense", cascade="all, delete-orphan")

    # Helper property to get tag names for backward compatibility
    @property
    def tags(self):
        """Return list of tag names from expense_tags."""
        return [et.user_tag.name for et in self.expense_tags if et.user_tag]

class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid6.uuid6()), index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    description = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    materials = Column(String, nullable=True)
    hours = Column(Float, nullable=True)
    amount = Column(Float, nullable=False)
    start_month = Column(Integer, nullable=False)
    start_year = Column(Integer, nullable=False)
    end_month = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    day_of_month = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="recurring_expenses")
    recurring_expense_tags = relationship("RecurringExpenseTag", back_populates="recurring_expense", cascade="all, delete-orphan")

    @property
    def tags(self):
        """Return list of tag names from recurring_expense_tags."""
        return [ret.user_tag.name for ret in self.recurring_expense_tags if ret.user_tag]

class RecurringExpenseTag(Base):
    """Junction table for many-to-many relationship between recurring expenses and user tags."""
    __tablename__ = "recurring_expense_tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid6.uuid6()), index=True)
    recurring_expense_id = Column(String(36), ForeignKey("recurring_expenses.id", ondelete="CASCADE"), nullable=False)
    user_tag_id = Column(String(36), ForeignKey("user_tags.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    recurring_expense = relationship("RecurringExpense", back_populates="recurring_expense_tags")
    user_tag = relationship("UserTag", backref="recurring_expense_tags")

class Vehicle(Base):
    """User's vehicles for mileage tracking."""
    __tablename__ = "vehicles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid6.uuid6()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    make = Column(String, nullable=True)
    model = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    license_plate = Column(String, nullable=True)
    last_odometer_reading = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="vehicles")
    mileage_logs = relationship("MileageLog", back_populates="vehicle", cascade="all, delete-orphan")

class MileageLog(Base):
    """Business trip records for mileage tracking."""
    __tablename__ = "mileage_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid6.uuid6()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id = Column(String(36), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    purpose = Column(String, nullable=False)
    odometer_start = Column(Integer, nullable=False)
    odometer_end = Column(Integer, nullable=False)
    personal_miles = Column(Integer, default=0, nullable=False)
    irs_rate = Column(Float, nullable=False)
    linked_expense_id = Column(String(36), ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="mileage_logs")
    vehicle = relationship("Vehicle", back_populates="mileage_logs")
    mileage_log_tags = relationship("MileageLogTag", back_populates="mileage_log", cascade="all, delete-orphan")
    linked_expense = relationship("Expense", foreign_keys=[linked_expense_id], backref="mileage_log", uselist=False)

    @property
    def business_miles(self):
        """Calculate business miles: total miles minus personal miles."""
        return (self.odometer_end - self.odometer_start) - self.personal_miles

    @property
    def deductible_amount(self):
        """Calculate deductible amount: business miles * IRS rate."""
        return self.business_miles * self.irs_rate

    @property
    def tags(self):
        """Return list of tag names from mileage_log_tags."""
        return [mlt.user_tag.name for mlt in self.mileage_log_tags if mlt.user_tag]

class MileageLogTag(Base):
    """Junction table for many-to-many relationship between mileage logs and user tags."""
    __tablename__ = "mileage_log_tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid6.uuid6()), index=True)
    mileage_log_id = Column(String(36), ForeignKey("mileage_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_tag_id = Column(String(36), ForeignKey("user_tags.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    mileage_log = relationship("MileageLog", back_populates="mileage_log_tags")
    user_tag = relationship("UserTag", backref="mileage_log_tags")

class IRSMileageRate(Base):
    """Historical IRS mileage rates for tax compliance."""
    __tablename__ = "irs_mileage_rates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid6.uuid6()), index=True)
    year = Column(Integer, nullable=False, unique=True, index=True)
    rate = Column(Float, nullable=False)
    effective_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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

        # Convert async database URLs to sync for Alembic
        # Alembic runs synchronously and can't use async drivers
        sync_database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        sync_database_url = sync_database_url.replace("sqlite+aiosqlite://", "sqlite://")

        alembic_cfg.set_main_option("sqlalchemy.url", sync_database_url)

        # Run migrations to head
        command.upgrade(alembic_cfg, "head")

        print("✅ Database migrations completed successfully")
    except Exception as e:
        print(f"⚠️  Migration warning: {str(e)}")
        # Don't fail startup if migrations have issues
        # This allows the app to start even if migrations fail

async def init_db():
    """Initialize database tables and run migrations."""
    run_migrations()
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            print(f"⚠️  Note: Some tables may already exist from migrations: {str(e)[:100]}")

async def get_db():
    """Async database session dependency for FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
