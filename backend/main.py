from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import joinedload
from typing import List, Optional
import os
from pathlib import Path
from dotenv import load_dotenv
import base64
from datetime import datetime, timedelta
import time
import structlog
import csv
import io

from models import init_db, get_db, Expense, User, UserTag, ExpenseTag, AsyncSessionLocal
from schemas import (
    ExpenseCreate, ExpenseResponse, VoiceTranscriptionResponse,
    GoogleAuthRequest, AuthResponse, UserResponse,
    SummaryStats, TagSpending, ByTagResponse, DateSpending, ByDateResponse,
    TagCreate, SubmitCsvResponse, CsvRowResult,
    AdminUserSummary, AdminUsersResponse
)
from claude_service import ClaudeService
from auth import verify_google_token, create_access_token, get_current_user, get_or_create_user, get_admin_user
import time

# Load .env from the backend directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.JSONRenderer() if os.getenv("ENVIRONMENT") == "production" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.testing.LogCapture if os.getenv("TESTING") else structlog.make_filtering_bound_logger(20),
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=True,
)

# Get a logger
logger = structlog.get_logger()

app = FastAPI(title="Expense Tracker API", version="1.0.0")

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Extract user info from auth header if available
    user_info = "anonymous"
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            # We'll just log that auth is present, not decode the full token
            user_info = "authenticated"
        except Exception:
            user_info = "invalid_auth"

    # Log the incoming request
    logger.info(
        "request_started",
        method=request.method,
        url=str(request.url),
        path=request.url.path,
        query_params=dict(request.query_params),
        user_type=user_info,
        user_agent=request.headers.get("user-agent", ""),
        client_ip=request.client.host if request.client else "unknown"
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log the response
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=round(process_time, 4),
            user_type=user_info
        )

        return response

    except Exception as e:
        process_time = time.time() - start_time

        # Log the error
        logger.error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            error_type=type(e).__name__,
            process_time=round(process_time, 4),
            user_type=user_info,
            exc_info=True
        )

        # Re-raise the exception so FastAPI can handle it
        raise

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    # Initialize database FIRST (create tables if needed)
    await init_db()

    # THEN check if we need to migrate from SQLite to PostgreSQL
    try:
        from models import is_postgres
        if is_postgres:
            from migrate_sqlite_to_postgres import check_and_migrate
            migration_success = await check_and_migrate()
            if migration_success:
                logger.info("sqlite_to_postgres_migration_completed")
    except Exception as e:
        logger.warning("migration_check_failed", error=str(e), message="Continuing with initialization")

    # Verify database connection
    try:
        from models import AsyncSessionLocal, is_postgres
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            if is_postgres:
                # Check PostgreSQL version
                result = await session.execute(text("SELECT version()"))
                version = result.scalar()
                logger.info("database_initialized", db_type="postgresql", version=version[:50])
            else:
                # Check SQLite WAL mode
                result = await session.execute(text("PRAGMA journal_mode"))
                journal_mode = result.scalar()
                logger.info("database_initialized", db_type="sqlite", journal_mode=journal_mode)
                if journal_mode != "wal":
                    logger.warning("wal_mode_not_enabled", current_mode=journal_mode)
    except Exception as e:
        logger.error("database_check_failed", error=str(e))

# Initialize Claude service
claude_service = ClaudeService()

# Log environment configuration at startup
print("\n" + "="*60)
print("🚀 Expense Tracker Starting Up")
print("="*60)
print(f"CORS Origins: {os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000')}")
print(f"Database URL: {os.getenv('DATABASE_URL', 'sqlite:///./expenses.db')}")
print(f"Google Client ID: {os.getenv('GOOGLE_CLIENT_ID', 'Not set')[:20]}...")
print(f"Anthropic API Key: {'Set ✓' if os.getenv('ANTHROPIC_API_KEY') else 'Not set ✗'}")
print(f"JWT Secret Key: {'Set ✓' if os.getenv('JWT_SECRET_KEY') else 'Not set ✗'}")
print("="*60 + "\n")

# Root endpoint is defined later for serving static files if they exist

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/config")
def get_config():
    """
    Get public configuration for the frontend.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    return {
        "googleClientId": client_id
    }

# Authentication endpoints
@app.post("/api/auth/google", response_model=AuthResponse)
async def google_auth(auth_request: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user with Google OAuth token and return JWT access token.

    This endpoint:
    1. Verifies the Google ID token with timeout protection
    2. Creates or updates user record in database
    3. Issues a JWT access token for subsequent API calls
    """
    import time
    auth_start_time = time.time()

    # Log authentication attempt (no sensitive data)
    logger.info(
        "auth_attempt_started",
        token_length=len(auth_request.token),
        has_google_client_id=bool(os.getenv("GOOGLE_CLIENT_ID"))
    )

    try:
        # Verify Google token (includes timeout protection)
        verify_start = time.time()
        user_info = await verify_google_token(auth_request.token)
        verify_duration = (time.time() - verify_start) * 1000
        logger.info("auth_step_verify_complete", duration_ms=round(verify_duration, 2))

        # Get or create user in database
        db_start = time.time()
        user = await get_or_create_user(db, user_info)
        db_duration = (time.time() - db_start) * 1000
        logger.info("auth_step_database_complete", duration_ms=round(db_duration, 2))

        # Generate JWT token
        jwt_start = time.time()
        access_token = create_access_token(data={"user_id": user.id})
        jwt_duration = (time.time() - jwt_start) * 1000
        logger.debug("auth_step_jwt_complete", duration_ms=round(jwt_duration, 2))

        total_auth_time = (time.time() - auth_start_time) * 1000
        logger.info(
            "auth_success",
            user_id=user.id,
            email_domain=user.email.split('@')[1] if '@' in user.email else "unknown",
            is_new_user=user.created_at > (datetime.utcnow() - timedelta(seconds=5)),
            total_duration_ms=round(total_auth_time, 2)
        )

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                picture=user.picture,
                is_admin=user.is_admin,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
        )

    except HTTPException:
        # Re-raise HTTPExceptions from verify_google_token (already logged)
        raise
    except Exception as e:
        logger.error(
            "auth_failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=401,
            detail="Authentication failed. Please try again."
        )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture=current_user.picture,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

# Admin endpoints
@app.get("/api/admin/users", response_model=AdminUsersResponse)
async def list_all_users(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin-only: List all users with expense counts.
    Returns user list with expense statistics (counts only, no amounts).
    """
    # Query users with expense counts using LEFT JOIN
    query = select(
        User,
        func.count(Expense.id).label('expense_count')
    ).outerjoin(Expense).group_by(User.id).order_by(User.created_at.desc())

    result = await db.execute(query)
    rows = result.all()

    users = [
        AdminUserSummary(
            id=row.User.id,
            email=row.User.email,
            name=row.User.name,
            is_admin=row.User.is_admin,
            expense_count=row.expense_count,
            created_at=row.User.created_at,
            updated_at=row.User.updated_at
        )
        for row in rows
    ]

    total_admins = sum(1 for u in users if u.is_admin)

    logger.info(
        "admin_users_listed",
        admin_id=admin.id,
        total_users=len(users),
        total_admins=total_admins
    )

    return AdminUsersResponse(
        users=users,
        total_users=len(users),
        total_admins=total_admins
    )


@app.post("/api/admin/users/{user_id}/elevate", status_code=200)
async def elevate_user_to_admin(
    user_id: str,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin-only: Elevate a user to administrator role.
    Requires existing admin to perform elevation.
    """
    # Prevent self-modification
    if user_id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot modify your own admin status"
        )

    # Find target user
    result = await db.execute(select(User).filter(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.is_admin:
        raise HTTPException(
            status_code=400,
            detail="User is already an administrator"
        )

    # Elevate to admin
    target_user.is_admin = True
    await db.commit()

    logger.info(
        "user_elevated_to_admin",
        admin_id=admin.id,
        admin_email=admin.email,
        elevated_user_id=user_id,
        elevated_user_email=target_user.email
    )

    return {
        "message": f"User {target_user.email} elevated to administrator successfully",
        "user_id": user_id,
        "is_admin": True
    }


@app.get("/api/settings")
async def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user settings including expense context.
    """
    return {
        "expense_context": current_user.expense_context or ""
    }

@app.patch("/api/settings")
async def update_user_settings(
    settings: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user settings including expense context.
    """
    if "expense_context" in settings:
        expense_context = settings["expense_context"]

        # Validate character limit (400 characters)
        if expense_context and len(expense_context) > 400:
            raise HTTPException(
                status_code=400,
                detail="Expense context cannot exceed 400 characters"
            )

        current_user.expense_context = expense_context if expense_context else None

    await db.commit()
    await db.refresh(current_user)

    return {
        "expense_context": current_user.expense_context or ""
    }

# Analytics endpoints
@app.get("/api/analytics/summary", response_model=SummaryStats)
async def get_summary_stats(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary statistics for the current user's expenses.
    date_from: ISO format date string (YYYY-MM-DD)
    date_to: ISO format date string (YYYY-MM-DD)
    """
    try:
        query = select(
            func.coalesce(func.sum(Expense.amount), 0).label('total_amount'),
            func.count(Expense.id).label('expense_count'),
            func.coalesce(func.avg(Expense.amount), 0).label('average_amount')
        ).filter(Expense.user_id == current_user.id)

        parsed_date_from = None
        parsed_date_to = None

        if date_from:
            parsed_date_from = datetime.fromisoformat(date_from)
            query = query.filter(Expense.date >= parsed_date_from)

        if date_to:
            parsed_date_to = datetime.fromisoformat(date_to)
            query = query.filter(Expense.date < parsed_date_to + timedelta(days=1))

        result = await db.execute(query)
        row = result.first()

        return SummaryStats(
            total_amount=float(row.total_amount) if row.total_amount else 0.0,
            expense_count=int(row.expense_count) if row.expense_count else 0,
            average_amount=float(row.average_amount) if row.average_amount else 0.0,
            date_from=parsed_date_from,
            date_to=parsed_date_to
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary stats: {str(e)}")

@app.get("/api/analytics/by-tag", response_model=ByTagResponse)
async def get_spending_by_tag(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get spending grouped by tag for the current user.
    Returns tags with their total spending and percentage of total.
    """
    try:
        # First get total amount for percentage calculation
        total_query = select(
            func.coalesce(func.sum(Expense.amount), 0).label('total')
        ).filter(Expense.user_id == current_user.id)

        if date_from:
            parsed_date_from = datetime.fromisoformat(date_from)
            total_query = total_query.filter(Expense.date >= parsed_date_from)

        if date_to:
            parsed_date_to = datetime.fromisoformat(date_to)
            total_query = total_query.filter(Expense.date < parsed_date_to + timedelta(days=1))

        total_result = await db.execute(total_query)
        total_amount = float(total_result.scalar() or 0.0)

        # Query spending by tag (using new UserTag + ExpenseTag system)
        query = select(
            UserTag.name,
            func.sum(Expense.amount).label('total_amount'),
            func.count(Expense.id).label('expense_count')
        ).join(ExpenseTag, UserTag.id == ExpenseTag.user_tag_id
        ).join(Expense, ExpenseTag.expense_id == Expense.id
        ).filter(
            Expense.user_id == current_user.id,
            UserTag.user_id == current_user.id
        ).group_by(UserTag.name).order_by(func.sum(Expense.amount).desc())

        if date_from:
            parsed_date_from = datetime.fromisoformat(date_from)
            query = query.filter(Expense.date >= parsed_date_from)

        if date_to:
            parsed_date_to = datetime.fromisoformat(date_to)
            query = query.filter(Expense.date < parsed_date_to + timedelta(days=1))

        result = await db.execute(query)
        rows = result.all()

        tag_data = []
        for row in rows:
            percentage = (row.total_amount / total_amount * 100) if total_amount > 0 else 0
            tag_data.append(TagSpending(
                tag=row.name,
                total_amount=float(row.total_amount),
                expense_count=int(row.expense_count),
                percentage=round(percentage, 2)
            ))

        # Handle expenses without tags
        untagged_query = select(
            func.sum(Expense.amount).label('total_amount'),
            func.count(Expense.id).label('expense_count')
        ).outerjoin(Tag).filter(
            Expense.user_id == current_user.id,
            Tag.id == None
        )

        if date_from:
            parsed_date_from = datetime.fromisoformat(date_from)
            untagged_query = untagged_query.filter(Expense.date >= parsed_date_from)

        if date_to:
            parsed_date_to = datetime.fromisoformat(date_to)
            untagged_query = untagged_query.filter(Expense.date < parsed_date_to + timedelta(days=1))

        untagged_result = await db.execute(untagged_query)
        untagged_row = untagged_result.first()

        if untagged_row and untagged_row.total_amount:
            percentage = (untagged_row.total_amount / total_amount * 100) if total_amount > 0 else 0
            tag_data.append(TagSpending(
                tag="Untagged",
                total_amount=float(untagged_row.total_amount),
                expense_count=int(untagged_row.expense_count),
                percentage=round(percentage, 2)
            ))

        return ByTagResponse(data=tag_data, total_amount=total_amount)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch spending by tag: {str(e)}")

@app.get("/api/analytics/by-date", response_model=ByDateResponse)
async def get_spending_by_date(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get spending grouped by date for trend analysis.
    Returns daily totals for the specified date range.
    """
    try:
        # Query spending by date
        query = select(
            func.date(Expense.date).label('expense_date'),
            func.sum(Expense.amount).label('total_amount'),
            func.count(Expense.id).label('expense_count')
        ).filter(
            Expense.user_id == current_user.id
        ).group_by(func.date(Expense.date)).order_by(func.date(Expense.date))

        if date_from:
            parsed_date_from = datetime.fromisoformat(date_from)
            query = query.filter(Expense.date >= parsed_date_from)

        if date_to:
            parsed_date_to = datetime.fromisoformat(date_to)
            query = query.filter(Expense.date < parsed_date_to + timedelta(days=1))

        result = await db.execute(query)
        rows = result.all()

        date_data = []
        for row in rows:
            date_data.append(DateSpending(
                date=str(row.expense_date),
                amount=float(row.total_amount),
                expense_count=int(row.expense_count)
            ))

        return ByDateResponse(data=date_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch spending by date: {str(e)}")

# Expense endpoints
@app.post("/api/expenses", response_model=ExpenseResponse, status_code=201)
async def create_expense(
    expense: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new expense entry with tags for the current user.
    """
    try:
        # Create expense without tags first
        db_expense = Expense(
            description=expense.description,
            recipient=expense.recipient,
            materials=expense.materials,
            hours=expense.hours,
            amount=expense.amount,
            date=expense.date,
            user_id=current_user.id
        )
        db.add(db_expense)
        await db.flush()  # Get expense ID without committing

        # Create tags if provided (using new UserTag + ExpenseTag system)
        if expense.tags:
            for tag_name in expense.tags:
                if tag_name and tag_name.strip():
                    tag_name = tag_name.strip()

                    # Get or create UserTag
                    user_tag_result = await db.execute(
                        select(UserTag).filter(
                            UserTag.user_id == current_user.id,
                            UserTag.name == tag_name
                        )
                    )
                    user_tag = user_tag_result.scalar_one_or_none()

                    if not user_tag:
                        # Create new UserTag
                        user_tag = UserTag(
                            name=tag_name,
                            user_id=current_user.id
                        )
                        db.add(user_tag)
                        await db.flush()  # Get UserTag ID

                    # Create ExpenseTag relationship
                    expense_tag = ExpenseTag(
                        expense_id=db_expense.id,
                        user_tag_id=user_tag.id
                    )
                    db.add(expense_tag)

        await db.commit()
        expense_id = db_expense.id

        # Reload expense with tags
        result = await db.execute(
            select(Expense)
            .options(joinedload(Expense.expense_tags))
            .where(Expense.id == expense_id)
        )
        created_expense = result.unique().scalar_one()
        return created_expense
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create expense: {str(e)}")

@app.get("/api/expenses", response_model=List[ExpenseResponse])
async def get_expenses(
    skip: int = 0,
    limit: int = 20,
    month: Optional[str] = None,
    year: Optional[int] = None,
    tags: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get expenses for current user with pagination and filtering.
    month: 1-12 for January-December
    year: 4-digit year
    tags: comma-separated tag names to filter by (e.g., "food,travel")
    """
    try:
        query = select(Expense).filter(
            Expense.user_id == current_user.id,
            Expense.amount > 0,  # Exclude zero amount expenses
            ~Expense.description.like("[Tag holder for:%")  # Exclude tag holders
        )

        # Add eager loading for expense_tags with proper join
        query = query.options(joinedload(Expense.expense_tags).joinedload(ExpenseTag.user_tag))

        # Month/year filtering
        if year and month:
            from datetime import datetime
            month_int = int(month)
            start_date = datetime(year, month_int, 1)
            if month_int == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month_int + 1, 1)
            query = query.filter(Expense.date >= start_date, Expense.date < end_date)
        elif year:
            from datetime import datetime
            start_date = datetime(year, 1, 1)
            end_date = datetime(year + 1, 1, 1)
            query = query.filter(Expense.date >= start_date, Expense.date < end_date)

        # Tag filtering - using new UserTag + ExpenseTag system
        if tags:
            tag_list = [t.strip() for t in tags.split(',') if t.strip()]
            if tag_list:
                # Filter for expenses that have at least one of the specified tags
                tag_exists = select(ExpenseTag.expense_id).join(UserTag).filter(
                    ExpenseTag.expense_id == Expense.id,
                    UserTag.name.in_(tag_list)
                ).exists()
                query = query.filter(tag_exists)

        query = query.order_by(Expense.date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        expenses = result.unique().scalars().all()  # unique() prevents duplicates from joins

        return expenses
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch expenses: {str(e)}")

@app.get("/api/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific expense by ID (only if it belongs to current user).
    """
    result = await db.execute(
        select(Expense)
        .options(joinedload(Expense.expense_tags).joinedload(ExpenseTag.user_tag))
        .filter(
            Expense.id == expense_id,
            Expense.user_id == current_user.id
        )
    )
    expense = result.unique().scalar_one_or_none()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense

@app.patch("/api/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: str,
    expense_update: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an expense (only if it belongs to current user).
    """
    try:
        result = await db.execute(
            select(Expense)
            .options(joinedload(Expense.expense_tags).joinedload(ExpenseTag.user_tag))
            .filter(
                Expense.id == expense_id,
                Expense.user_id == current_user.id
            )
        )
        expense = result.unique().scalar_one_or_none()
        if expense is None:
            raise HTTPException(status_code=404, detail="Expense not found")


        # Update allowed fields
        if "description" in expense_update:
            expense.description = expense_update["description"]
        if "recipient" in expense_update:
            expense.recipient = expense_update["recipient"] if expense_update["recipient"] else None
        if "materials" in expense_update:
            expense.materials = expense_update["materials"] if expense_update["materials"] else None
        if "hours" in expense_update:
            expense.hours = float(expense_update["hours"]) if expense_update["hours"] else None
        if "amount" in expense_update:
            expense.amount = float(expense_update["amount"])
        if "date" in expense_update:
            # Parse date string to datetime object
            date_str = expense_update["date"]
            if isinstance(date_str, str):
                # Try parsing ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
                try:
                    expense.date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except ValueError:
                    # If parsing fails, try just the date portion
                    expense.date = datetime.strptime(date_str.split('T')[0], '%Y-%m-%d')
            elif isinstance(date_str, datetime):
                expense.date = date_str

        # Handle tags update (using new UserTag + ExpenseTag system)
        if "tags" in expense_update:
            # Delete existing expense_tags
            await db.execute(
                delete(ExpenseTag).where(ExpenseTag.expense_id == expense_id)
            )
            await db.flush()

            # Add new tags
            tags = expense_update["tags"]
            if isinstance(tags, list):
                for tag_name in tags:
                    if tag_name and tag_name.strip():
                        tag_name = tag_name.strip()

                        # Get or create UserTag
                        user_tag_result = await db.execute(
                            select(UserTag).filter(
                                UserTag.user_id == current_user.id,
                                UserTag.name == tag_name
                            )
                        )
                        user_tag = user_tag_result.scalar_one_or_none()

                        if not user_tag:
                            # Create new UserTag
                            user_tag = UserTag(
                                name=tag_name,
                                user_id=current_user.id
                            )
                            db.add(user_tag)
                            await db.flush()

                        # Create ExpenseTag relationship
                        expense_tag = ExpenseTag(
                            expense_id=expense_id,
                            user_tag_id=user_tag.id
                        )
                        db.add(expense_tag)

        await db.commit()

        # Close the session to clear any cached data
        await db.close()

        # Create a new session and query for the expense with fresh tags
        async with AsyncSessionLocal() as fresh_db:
            result = await fresh_db.execute(
                select(Expense)
                .options(joinedload(Expense.expense_tags).joinedload(ExpenseTag.user_tag))
                .where(Expense.id == expense_id)
            )
            reloaded_expense = result.unique().scalar_one()

            # Debug: print tags before returning

            return reloaded_expense
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update expense: {str(e)}")

@app.delete("/api/expenses/{expense_id}", status_code=204)
async def delete_expense(
    expense_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an expense by ID (only if it belongs to current user).
    """
    result = await db.execute(
        select(Expense).filter(
            Expense.id == expense_id,
            Expense.user_id == current_user.id
        )
    )
    expense = result.scalar_one_or_none()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    await db.delete(expense)
    await db.commit()
    return None

@app.post("/api/expenses/bulk/delete")
async def bulk_delete_expenses(
    request_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete multiple expenses by IDs (only if they belong to current user).
    """
    expense_ids = request_data.get("expense_ids", [])

    if not expense_ids:
        raise HTTPException(status_code=400, detail="No expense IDs provided")

    # Verify all expenses belong to current user
    result = await db.execute(
        select(Expense).filter(
            Expense.id.in_(expense_ids),
            Expense.user_id == current_user.id
        )
    )
    expenses = result.scalars().all()

    if len(expenses) != len(expense_ids):
        raise HTTPException(status_code=403, detail="Some expenses not found or don't belong to you")

    # Delete all expenses
    for expense in expenses:
        await db.delete(expense)

    await db.commit()
    return {"deleted_count": len(expenses)}

# Tag management endpoints
@app.post("/api/tags", status_code=201)
async def create_tag(
    tag_data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new standalone tag for the current user.
    """
    try:
        tag_name = tag_data.name.strip()
        if not tag_name:
            raise HTTPException(status_code=400, detail="Tag name cannot be empty")

        # Check if tag already exists for this user
        existing_tag_query = select(UserTag).filter(
            UserTag.user_id == current_user.id,
            UserTag.name == tag_name
        )
        result = await db.execute(existing_tag_query)
        existing_tag = result.scalar_one_or_none()

        if existing_tag:
            raise HTTPException(status_code=409, detail="Tag already exists")

        # Create the standalone user tag
        db_user_tag = UserTag(
            name=tag_name,
            user_id=current_user.id
        )
        db.add(db_user_tag)

        await db.commit()
        return {"message": "Tag created successfully", "name": tag_name}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create tag: {str(e)}")

@app.get("/api/user-tags")
async def get_user_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all user tags with their usage counts and spending amounts.
    """
    try:
        # Fetch all UserTags for this user
        user_tags_query = select(UserTag).filter(UserTag.user_id == current_user.id).order_by(UserTag.name)
        result = await db.execute(user_tags_query)
        user_tags = result.scalars().all()

        # Calculate usage counts and total spending for each tag
        tags_with_stats = []
        for user_tag in user_tags:
            # Count expenses and sum amounts
            stats_query = select(
                func.count(ExpenseTag.id).label('usage_count'),
                func.coalesce(func.sum(Expense.amount), 0).label('total_amount')
            ).select_from(ExpenseTag).outerjoin(
                Expense, ExpenseTag.expense_id == Expense.id
            ).filter(ExpenseTag.user_tag_id == user_tag.id)

            stats_result = await db.execute(stats_query)
            stats = stats_result.one()

            tags_with_stats.append({
                "id": user_tag.id,
                "name": user_tag.name,
                "usage_count": stats.usage_count or 0,
                "total_amount": float(stats.total_amount),
                "created_at": user_tag.created_at.isoformat()
            })

        return {"tags": tags_with_stats}
    except Exception as e:
        logger.error("Error fetching user tags", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to fetch tags")

@app.patch("/api/tags/{tag_name}/rename")
async def rename_tag(
    tag_name: str,
    new_name: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Rename a user tag. All expenses with this tag will be updated.
    """
    try:
        # Validate new name
        if not new_name or not new_name.strip():
            raise HTTPException(status_code=400, detail="Tag name cannot be empty")

        new_name = new_name.strip()

        # Check if new name already exists
        existing_tag = await db.execute(
            select(UserTag).filter(
                UserTag.user_id == current_user.id,
                UserTag.name == new_name
            )
        )
        if existing_tag.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Tag '{new_name}' already exists")

        # Find the tag to rename
        result = await db.execute(
            select(UserTag).filter(
                UserTag.user_id == current_user.id,
                UserTag.name == tag_name
            )
        )
        user_tag = result.scalar_one_or_none()

        if not user_tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        # Rename the tag
        old_name = user_tag.name
        user_tag.name = new_name
        await db.commit()

        logger.info(
            "tag_renamed",
            user_id=current_user.id,
            old_name=old_name,
            new_name=new_name
        )

        return {"message": f"Tag renamed from '{old_name}' to '{new_name}'", "new_name": new_name}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to rename tag: {str(e)}")


@app.post("/api/tags/merge")
async def merge_tags(
    source_tag: str = Body(...),
    target_tag: str = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Merge source tag into target tag. All expenses tagged with source will be
    retagged with target, then source tag is deleted.
    """
    try:
        if source_tag == target_tag:
            raise HTTPException(status_code=400, detail="Cannot merge tag with itself")

        # Find both tags
        source_result = await db.execute(
            select(UserTag).filter(
                UserTag.user_id == current_user.id,
                UserTag.name == source_tag
            )
        )
        source_user_tag = source_result.scalar_one_or_none()

        target_result = await db.execute(
            select(UserTag).filter(
                UserTag.user_id == current_user.id,
                UserTag.name == target_tag
            )
        )
        target_user_tag = target_result.scalar_one_or_none()

        if not source_user_tag:
            raise HTTPException(status_code=404, detail=f"Source tag '{source_tag}' not found")
        if not target_user_tag:
            raise HTTPException(status_code=404, detail=f"Target tag '{target_tag}' not found")

        # Get all expenses that have the source tag
        expense_tags_result = await db.execute(
            select(ExpenseTag).filter(ExpenseTag.user_tag_id == source_user_tag.id)
        )
        expense_tags = expense_tags_result.scalars().all()

        merged_count = 0
        deleted_count = 0

        for expense_tag in expense_tags:
            # Check if expense already has target tag
            existing = await db.execute(
                select(ExpenseTag).filter(
                    ExpenseTag.expense_id == expense_tag.expense_id,
                    ExpenseTag.user_tag_id == target_user_tag.id
                )
            )
            if not existing.scalar_one_or_none():
                # Expense doesn't have target tag, update to target
                expense_tag.user_tag_id = target_user_tag.id
                merged_count += 1
            else:
                # Expense already has target tag, delete the duplicate source relationship
                await db.delete(expense_tag)
                deleted_count += 1

        # Flush to process updates/deletes before deleting the source tag
        await db.flush()

        # Delete source tag
        await db.delete(source_user_tag)
        await db.commit()

        logger.info(
            "tags_merged",
            user_id=current_user.id,
            source_tag=source_tag,
            target_tag=target_tag,
            expenses_updated=merged_count,
            duplicates_removed=deleted_count
        )

        return {
            "message": f"Merged '{source_tag}' into '{target_tag}'",
            "expenses_updated": merged_count,
            "duplicates_removed": deleted_count,
            "source_tag": source_tag,
            "target_tag": target_tag
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to merge tags: {str(e)}")


@app.delete("/api/tags/{tag_name}", status_code=204)
async def delete_tag(
    tag_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a user tag and remove it from all expenses for the current user.
    """
    try:
        # Find the UserTag for this user
        user_tag_query = select(UserTag).filter(
            UserTag.user_id == current_user.id,
            UserTag.name == tag_name
        )
        result = await db.execute(user_tag_query)
        user_tag = result.scalar_one_or_none()

        if not user_tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        # Delete all ExpenseTag relationships for this UserTag
        delete_expense_tags_query = delete(ExpenseTag).where(
            ExpenseTag.user_tag_id == user_tag.id
        )
        await db.execute(delete_expense_tags_query)

        # Delete the UserTag itself
        await db.delete(user_tag)

        await db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete tag: {str(e)}")

@app.post("/api/cleanup-orphaned-tags", status_code=204)
async def cleanup_orphaned_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Clean up orphaned expense_tags that reference non-existent expenses or user_tags.
    """
    try:
        # Find and delete expense_tags that reference non-existent expenses
        orphaned_query = select(ExpenseTag).outerjoin(Expense).filter(
            Expense.id == None
        )
        result = await db.execute(orphaned_query)
        orphaned = result.scalars().all()

        count = 0
        for expense_tag in orphaned:
            await db.delete(expense_tag)
            count += 1

        await db.commit()
        return None
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cleanup: {str(e)}")

@app.post("/api/transcribe-audio")
async def transcribe_audio_file(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Transcribe audio file using Claude AI (for Safari and other browsers without Web Speech API).
    """
    try:
        # Read audio file
        audio_content = await audio.read()

        # Convert to base64 for Claude API
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')

        # Determine media type
        media_type = audio.content_type or 'audio/webm'

        # Use Claude to transcribe the audio
        transcription = await claude_service.transcribe_audio(audio_base64, media_type)

        return {"transcription": transcription}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to transcribe audio: {str(e)}")

@app.post("/api/process-image", response_model=VoiceTranscriptionResponse)
async def process_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process uploaded image (receipt, screenshot) and extract expense information using Claude Vision.
    """
    try:
        # Read and encode image
        image_content = await image.read()
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        media_type = image.content_type or 'image/jpeg'


        # Get user's existing tags for context
        result = await db.execute(
            select(Tag.name)
            .join(Expense)
            .filter(Expense.user_id == current_user.id)
            .distinct()
        )
        existing_tags = result.scalars().all()
        tag_names = list(existing_tags) if existing_tags else []

        # Get user's custom expense context
        user_context = current_user.expense_context

        # Extract expense data from image
        parsed_expense, warning = claude_service.extract_expense_from_image(
            image_base64, media_type, tag_names, user_context
        )


        return VoiceTranscriptionResponse(
            transcription="[Image processed]",
            parsed_expense=ExpenseCreate(**parsed_expense),
            warning=warning
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")

@app.post("/api/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe_text(
    transcription: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process voice transcription and extract expense information using Claude.
    Includes user's existing tags as context for better parsing.
    """
    if not transcription or not transcription.strip():
        raise HTTPException(status_code=400, detail="Transcription text is required")

    try:
        # Get unique tag names from existing expenses
        result = await db.execute(
            select(Tag.name)
            .join(Expense)
            .filter(Expense.user_id == current_user.id)
            .distinct()
        )
        existing_tags = result.scalars().all()
        tag_names = list(existing_tags) if existing_tags else []

        # Get user's custom expense context
        user_context = current_user.expense_context

        parsed_expense, warning = claude_service.parse_expense_from_text(transcription, tag_names, user_context)

        return VoiceTranscriptionResponse(
            transcription=transcription,
            parsed_expense=ExpenseCreate(**parsed_expense),
            warning=warning
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process transcription: {str(e)}")

@app.post("/api/submit-csv", response_model=SubmitCsvResponse)
async def submit_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process CSV file for bulk expense submission.
    Each row is processed independently with column headers as context.
    Returns detailed results for each row.
    """
    try:
        # Read CSV file
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="CSV file is empty")

        # Parse CSV
        text_content = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(text_content))

        if csv_reader.fieldnames is None or len(csv_reader.fieldnames) == 0:
            raise HTTPException(status_code=400, detail="CSV file has no headers")

        # Get user's existing tags and context for processing
        tag_result = await db.execute(
            select(Tag.name)
            .join(Expense)
            .filter(Expense.user_id == current_user.id)
            .distinct()
        )
        existing_tags = list(tag_result.scalars().all()) if tag_result.scalars().all() else []
        user_context = current_user.expense_context

        results = []
        row_number = 1

        for row in csv_reader:
            row_number += 1
            try:
                # Format row data as text for Claude to parse
                row_text = ", ".join([f"{key}: {value}" for key, value in row.items() if value])

                if not row_text.strip():
                    results.append(CsvRowResult(
                        row_number=row_number,
                        status="error",
                        error_message="Row is empty"
                    ))
                    continue

                # Parse the row using Claude
                parsed_expense, warning = claude_service.parse_expense_from_text(
                    row_text,
                    existing_tags,
                    user_context
                )

                # Create expense in database
                db_expense = Expense(
                    description=parsed_expense["description"],
                    recipient=parsed_expense["recipient"],
                    materials=parsed_expense.get("materials"),
                    hours=parsed_expense.get("hours"),
                    amount=parsed_expense["amount"],
                    date=parsed_expense.get("date") or datetime.utcnow(),
                    user_id=current_user.id
                )
                db.add(db_expense)
                await db.flush()

                # Create tags if provided (using new UserTag + ExpenseTag system)
                if parsed_expense.get("tags"):
                    for tag_name in parsed_expense["tags"]:
                        if tag_name and tag_name.strip():
                            tag_name = tag_name.strip()

                            # Get or create UserTag
                            user_tag_result = await db.execute(
                                select(UserTag).filter(
                                    UserTag.user_id == current_user.id,
                                    UserTag.name == tag_name
                                )
                            )
                            user_tag = user_tag_result.scalar_one_or_none()

                            if not user_tag:
                                user_tag = UserTag(name=tag_name, user_id=current_user.id)
                                db.add(user_tag)
                                await db.flush()

                            # Create ExpenseTag relationship
                            expense_tag = ExpenseTag(
                                expense_id=db_expense.id,
                                user_tag_id=user_tag.id
                            )
                            db.add(expense_tag)

                await db.flush()
                expense_id = db_expense.id

                # Reload expense with tags
                expense_result = await db.execute(
                    select(Expense)
                    .options(joinedload(Expense.expense_tags).joinedload(ExpenseTag.user_tag))
                    .where(Expense.id == expense_id)
                )
                created_expense = expense_result.unique().scalar_one()

                results.append(CsvRowResult(
                    row_number=row_number,
                    status="success",
                    expense=created_expense,
                    error_message=None
                ))

            except ValueError as e:
                results.append(CsvRowResult(
                    row_number=row_number,
                    status="error",
                    error_message=f"Validation error: {str(e)}"
                ))
            except Exception as e:
                results.append(CsvRowResult(
                    row_number=row_number,
                    status="error",
                    error_message=f"Processing error: {str(e)}"
                ))

        # Commit all successful changes
        await db.commit()

        # Calculate summary
        successful = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status == "error")

        return SubmitCsvResponse(
            total_rows=len(results),
            successful=successful,
            failed=failed,
            results=results
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Error processing CSV", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")

@app.post("/api/submit-csv-stream")
async def submit_csv_stream(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Process CSV file with streaming progress updates.
    Yields JSON lines with per-row results as they're processed.
    """
    # Extract user data and read file before streaming starts
    user_id = current_user.id
    user_context = current_user.expense_context

    # Read file content immediately while request context is active
    file_content = await file.read()
    if not file_content:
        return StreamingResponse(
            (json.dumps({"type": "error", "message": "CSV file is empty"}) + "\n" for _ in [None]),
            media_type="application/x-ndjson"
        )

    async def process_csv_stream():
        stream_db = AsyncSessionLocal()
        try:
            # Parse CSV
            text_content = file_content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(text_content))

            if csv_reader.fieldnames is None or len(csv_reader.fieldnames) == 0:
                yield json.dumps({"type": "error", "message": "CSV file has no headers"}) + "\n"
                return

            # Get user's existing tags and context for processing
            tag_result = await stream_db.execute(
                select(Tag.name)
                .join(Expense)
                .filter(Expense.user_id == user_id)
                .distinct()
            )
            existing_tags = list(tag_result.scalars().all()) if tag_result.scalars().all() else []

            # Send start signal
            yield json.dumps({"type": "start"}) + "\n"

            successful = 0
            failed = 0
            row_number = 1

            for row in csv_reader:
                row_number += 1
                try:
                    # Format row data as text for Claude to parse
                    row_text = ", ".join([f"{key}: {value}" for key, value in row.items() if value])

                    if not row_text.strip():
                        yield json.dumps({
                            "type": "row",
                            "row_number": row_number,
                            "status": "error",
                            "error": "Row is empty"
                        }) + "\n"
                        failed += 1
                        continue

                    # Parse the row using Claude
                    parsed_expense, warning = claude_service.parse_expense_from_text(
                        row_text,
                        existing_tags,
                        user_context
                    )

                    # Create expense in database
                    db_expense = Expense(
                        description=parsed_expense["description"],
                        recipient=parsed_expense["recipient"],
                        materials=parsed_expense.get("materials"),
                        hours=parsed_expense.get("hours"),
                        amount=parsed_expense["amount"],
                        date=parsed_expense.get("date") or datetime.utcnow(),
                        user_id=user_id
                    )
                    stream_db.add(db_expense)
                    await stream_db.flush()

                    # Create tags if provided (using new UserTag + ExpenseTag system)
                    if parsed_expense.get("tags"):
                        for tag_name in parsed_expense["tags"]:
                            if tag_name and tag_name.strip():
                                tag_name = tag_name.strip()

                                # Get or create UserTag
                                user_tag_result = await stream_db.execute(
                                    select(UserTag).filter(
                                        UserTag.user_id == user_id,
                                        UserTag.name == tag_name
                                    )
                                )
                                user_tag = user_tag_result.scalar_one_or_none()

                                if not user_tag:
                                    user_tag = UserTag(name=tag_name, user_id=user_id)
                                    stream_db.add(user_tag)
                                    await stream_db.flush()

                                # Create ExpenseTag relationship
                                expense_tag = ExpenseTag(
                                    expense_id=db_expense.id,
                                    user_tag_id=user_tag.id
                                )
                                stream_db.add(expense_tag)

                    await stream_db.flush()
                    await stream_db.commit()

                    yield json.dumps({
                        "type": "row",
                        "row_number": row_number,
                        "status": "success",
                        "description": parsed_expense["description"],
                        "amount": parsed_expense["amount"]
                    }) + "\n"
                    successful += 1

                except ValueError as e:
                    yield json.dumps({
                        "type": "row",
                        "row_number": row_number,
                        "status": "error",
                        "error": f"Validation error: {str(e)}"
                    }) + "\n"
                    failed += 1
                except Exception as e:
                    yield json.dumps({
                        "type": "row",
                        "row_number": row_number,
                        "status": "error",
                        "error": f"Processing error: {str(e)}"
                    }) + "\n"
                    failed += 1

            # Send completion signal
            yield json.dumps({
                "type": "complete",
                "total_rows": row_number - 1,
                "successful": successful,
                "failed": failed
            }) + "\n"

        except Exception as e:
            logger.error("Error in CSV stream processing", error=str(e), user_id=user_id)
            yield json.dumps({"type": "error", "message": f"Processing error: {str(e)}"}) + "\n"
        finally:
            await stream_db.close()

    return StreamingResponse(
        process_csv_stream(),
        media_type="application/x-ndjson",
        headers={"X-Content-Type-Options": "nosniff"}
    )

# Mount static files for serving frontend (Docker deployment)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/")
    async def serve_root():
        """Serve the React SPA at root"""
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Expense Tracker API", "version": "1.0.0"}

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for all non-API routes"""
        # Don't intercept API routes
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")

        # Serve index.html for all other routes (SPA routing)
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
