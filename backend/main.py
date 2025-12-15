from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

from models import init_db, get_db, Expense, User, Tag, UserTag, ExpenseTag, AsyncSessionLocal
from schemas import (
    ExpenseCreate, ExpenseResponse, VoiceTranscriptionResponse,
    GoogleAuthRequest, AuthResponse, UserResponse,
    SummaryStats, TagSpending, ByTagResponse, DateSpending, ByDateResponse,
    TagCreate
)
from claude_service import ClaudeService
from auth import verify_google_token, create_access_token, get_current_user, get_or_create_user

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
    await init_db()

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
    print(f"📋 /api/config called - Returning Client ID: {client_id[:20]}..." if client_id else "📋 /api/config called - Client ID is EMPTY!")
    return {
        "googleClientId": client_id
    }

# Authentication endpoints
@app.post("/api/auth/google", response_model=AuthResponse)
async def google_auth(auth_request: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user with Google OAuth token and return JWT access token.
    """
    try:
        user_info = await verify_google_token(auth_request.token)
        user = await get_or_create_user(db, user_info)

        access_token = create_access_token(data={"user_id": user.id})

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                picture=user.picture,
                created_at=user.created_at
            )
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

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
        created_at=current_user.created_at
    )

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

        # Query spending by tag
        query = select(
            Tag.name,
            func.sum(Expense.amount).label('total_amount'),
            func.count(Expense.id).label('expense_count')
        ).join(Expense).filter(
            Expense.user_id == current_user.id
        ).group_by(Tag.name).order_by(func.sum(Expense.amount).desc())

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

        # Create tags if provided
        if expense.tags:
            for tag_name in expense.tags:
                if tag_name and tag_name.strip():
                    db_tag = Tag(
                        name=tag_name.strip(),
                        expense_id=db_expense.id
                    )
                    db.add(db_tag)

        await db.commit()
        expense_id = db_expense.id
        await db.close()

        # Reload with fresh session to get tags
        async with AsyncSessionLocal() as fresh_db:
            result = await fresh_db.execute(
                select(Expense)
                .options(joinedload(Expense.tags))
                .where(Expense.id == expense_id)
            )
            created_expense = result.unique().scalar_one()
            print(f"Created expense {expense_id} with tags: {[tag.name for tag in created_expense.tags]}")
            return created_expense
    except Exception as e:
        await db.rollback()
        print(f"Error creating expense: {str(e)}")
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

        # Add eager loading for tags with proper join
        query = query.options(joinedload(Expense.tags))

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

        # Tag filtering - use exists to avoid orphaned tag issues
        if tags:
            tag_list = [t.strip() for t in tags.split(',') if t.strip()]
            if tag_list:
                # Use EXISTS subquery to avoid issues with orphaned tags
                tag_exists = select(Tag.expense_id).filter(
                    Tag.expense_id == Expense.id,
                    Tag.name.in_(tag_list)
                ).exists()
                query = query.filter(tag_exists)

        query = query.order_by(Expense.date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        expenses = result.unique().scalars().all()  # unique() prevents duplicates from joins

        # Filter out any expenses with invalid tag relationships
        valid_expenses = []
        for expense in expenses:
            try:
                # Try to access the tags to ensure they're valid
                _ = [tag.name for tag in expense.tags]
                valid_expenses.append(expense)
            except Exception as e:
                print(f"Skipping expense {expense.id} due to invalid tags: {e}")
                continue

        return valid_expenses
    except Exception as e:
        print(f"Error fetching expenses: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch expenses: {str(e)}")

@app.get("/api/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific expense by ID (only if it belongs to current user).
    """
    result = await db.execute(
        select(Expense)
        .options(joinedload(Expense.tags))
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
    expense_id: int,
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
            .options(joinedload(Expense.tags))
            .filter(
                Expense.id == expense_id,
                Expense.user_id == current_user.id
            )
        )
        expense = result.unique().scalar_one_or_none()
        if expense is None:
            raise HTTPException(status_code=404, detail="Expense not found")

        print(f"Updating expense {expense_id} with data: {expense_update}")

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

        # Handle tags update
        if "tags" in expense_update:
            print(f"Updating tags to: {expense_update['tags']}")
            # Delete existing tags
            await db.execute(
                delete(Tag).where(Tag.expense_id == expense_id)
            )
            await db.flush()

            # Add new tags
            tags = expense_update["tags"]
            if isinstance(tags, list):
                for tag_name in tags:
                    if tag_name and tag_name.strip():
                        db_tag = Tag(
                            name=tag_name.strip(),
                            expense_id=expense_id
                        )
                        db.add(db_tag)

        await db.commit()

        # Close the session to clear any cached data
        await db.close()

        # Create a new session and query for the expense with fresh tags
        async with AsyncSessionLocal() as fresh_db:
            result = await fresh_db.execute(
                select(Expense)
                .options(joinedload(Expense.tags))
                .where(Expense.id == expense_id)
            )
            reloaded_expense = result.unique().scalar_one()

            # Debug: print tags before returning
            print(f"Successfully updated expense {expense_id}")
            print(f"Reloaded expense tags objects: {reloaded_expense.tags}")
            print(f"Reloaded expense tags names: {[tag.name for tag in reloaded_expense.tags]}")

            return reloaded_expense
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating expense {expense_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update expense: {str(e)}")

@app.delete("/api/expenses/{expense_id}", status_code=204)
async def delete_expense(
    expense_id: int,
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
    Get all user tags with their usage counts.
    """
    try:
        # Fetch all UserTags for this user
        user_tags_query = select(UserTag).filter(UserTag.user_id == current_user.id).order_by(UserTag.name)
        result = await db.execute(user_tags_query)
        user_tags = result.scalars().all()

        # Calculate usage counts for each tag by counting ExpenseTag relationships
        tags_with_counts = []
        for user_tag in user_tags:
            count_query = select(func.count(ExpenseTag.id)).filter(ExpenseTag.user_tag_id == user_tag.id)
            count_result = await db.execute(count_query)
            usage_count = count_result.scalar() or 0

            tags_with_counts.append({
                "name": user_tag.name,
                "usage_count": usage_count,
                "created_at": user_tag.created_at.isoformat()
            })

        return {"tags": tags_with_counts}
    except Exception as e:
        logger.error("Error fetching user tags", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to fetch tags")

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
        print(f"Successfully deleted tag '{tag_name}' for user {current_user.id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting tag '{tag_name}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete tag: {str(e)}")

@app.post("/api/cleanup-orphaned-tags", status_code=204)
async def cleanup_orphaned_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Clean up orphaned tags that reference non-existent expenses.
    """
    try:
        # Find and delete tags that reference expenses that don't exist
        orphaned_tags_query = select(Tag).outerjoin(Expense).filter(
            Expense.id == None
        )
        result = await db.execute(orphaned_tags_query)
        orphaned_tags = result.scalars().all()

        count = 0
        for tag in orphaned_tags:
            await db.delete(tag)
            count += 1

        await db.commit()
        print(f"Cleaned up {count} orphaned tags")
        return None
    except Exception as e:
        await db.rollback()
        print(f"Error cleaning orphaned tags: {str(e)}")
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

        print(f"Processing image with type: {media_type}, size: {len(image_content)} bytes")

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

        print(f"Extracted expense data: {parsed_expense}")

        return VoiceTranscriptionResponse(
            transcription="[Image processed]",
            parsed_expense=ExpenseCreate(**parsed_expense),
            warning=warning
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"Error processing image: {str(e)}")
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
