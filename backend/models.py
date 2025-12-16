from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

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

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    google_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    expense_context = Column(String, nullable=True)  # Custom context for expense generation
    created_at = Column(DateTime, default=datetime.utcnow)

    expenses = relationship("Expense", back_populates="user", cascade="all, delete-orphan")
    user_tags = relationship("UserTag", back_populates="user", cascade="all, delete-orphan")

class UserTag(Base):
    """Standalone tags that belong to a user, not tied to specific expenses."""
    __tablename__ = "user_tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="user_tags")

class ExpenseTag(Base):
    """Junction table for many-to-many relationship between expenses and user tags."""
    __tablename__ = "expense_tags"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    user_tag_id = Column(Integer, ForeignKey("user_tags.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    expense = relationship("Expense", back_populates="expense_tags")
    user_tag = relationship("UserTag", backref="expense_tags")

# Keep old Tag model for backward compatibility during migration
class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    expense = relationship("Expense", back_populates="tags")

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    materials = Column(String, nullable=True)
    hours = Column(Float, nullable=True)
    amount = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="expenses")
    tags = relationship("Tag", back_populates="expense", cascade="all, delete-orphan")  # Old relationship
    expense_tags = relationship("ExpenseTag", back_populates="expense", cascade="all, delete-orphan")  # New relationship

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

async def init_db():
    """Initialize database tables and run migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    run_migrations()

async def get_db():
    """Async database session dependency for FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
