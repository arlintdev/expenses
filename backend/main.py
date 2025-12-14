from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from pathlib import Path
from dotenv import load_dotenv
import base64

from models import init_db, get_db, Expense, User, Category
from schemas import (
    ExpenseCreate, ExpenseResponse, VoiceTranscriptionResponse,
    GoogleAuthRequest, AuthResponse, UserResponse,
    CategoryCreate, CategoryResponse
)
from claude_service import ClaudeService
from auth import verify_google_token, create_access_token, get_current_user, get_or_create_user

# Load .env from the backend directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

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

# Initialize database
init_db()

# Initialize Claude service
claude_service = ClaudeService()

@app.get("/")
def read_root():
    return {"message": "Expense Tracker API", "version": "1.0.0"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

# Authentication endpoints
@app.post("/api/auth/google", response_model=AuthResponse)
async def google_auth(auth_request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Authenticate user with Google OAuth token and return JWT access token.
    """
    try:
        user_info = await verify_google_token(auth_request.token)
        user = get_or_create_user(db, user_info)

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

# Category endpoints
@app.get("/api/categories", response_model=List[CategoryResponse])
def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all categories for the current user.
    """
    categories = db.query(Category).filter(Category.user_id == current_user.id).order_by(Category.name).all()
    return categories

@app.post("/api/categories", response_model=CategoryResponse, status_code=201)
def create_category(
    category: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new category for the current user.
    """
    # Check if category already exists for this user
    existing = db.query(Category).filter(
        Category.user_id == current_user.id,
        Category.name == category.name
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    db_category = Category(
        name=category.name,
        user_id=current_user.id
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@app.delete("/api/categories/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a category by ID (only if it belongs to current user).
    """
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()
    return None

@app.post("/api/expenses", response_model=ExpenseResponse, status_code=201)
def create_expense(
    expense: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new expense entry for the current user.
    """
    try:
        db_expense = Expense(
            description=expense.description,
            recipient=expense.recipient,
            materials=expense.materials,
            hours=expense.hours,
            category=expense.category,
            amount=expense.amount,
            date=expense.date,
            user_id=current_user.id
        )
        db.add(db_expense)
        db.commit()
        db.refresh(db_expense)
        return db_expense
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create expense: {str(e)}")

@app.get("/api/expenses", response_model=List[ExpenseResponse])
def get_expenses(
    skip: int = 0,
    limit: int = 20,
    month: Optional[str] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get expenses for current user with pagination and optional month/year filtering.
    month: 1-12 for January-December
    year: 4-digit year
    """
    query = db.query(Expense).filter(Expense.user_id == current_user.id)

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

    expenses = query.order_by(Expense.date.desc()).offset(skip).limit(limit).all()
    return expenses

@app.get("/api/expenses/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific expense by ID (only if it belongs to current user).
    """
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense

@app.patch("/api/expenses/{expense_id}/category", response_model=ExpenseResponse)
def update_expense_category(
    expense_id: int,
    category: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the category of an expense (only if it belongs to current user).
    """
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    expense.category = category if category and category.strip() else None
    db.commit()
    db.refresh(expense)
    return expense

@app.delete("/api/expenses/{expense_id}", status_code=204)
def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an expense by ID (only if it belongs to current user).
    """
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    db.delete(expense)
    db.commit()
    return None

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

@app.post("/api/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe_text(
    transcription: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process voice transcription and extract expense information using Claude.
    Includes user's categories as context for better parsing.
    """
    if not transcription or not transcription.strip():
        raise HTTPException(status_code=400, detail="Transcription text is required")

    try:
        # Get unique categories from existing expenses (excluding None/empty)
        expense_categories = db.query(Expense.category).filter(
            Expense.user_id == current_user.id,
            Expense.category.isnot(None),
            Expense.category != ''
        ).distinct().all()
        category_names = [cat[0] for cat in expense_categories if cat[0]]

        parsed_expense = claude_service.parse_expense_from_text(transcription, category_names)

        return VoiceTranscriptionResponse(
            transcription=transcription,
            parsed_expense=ExpenseCreate(**parsed_expense)
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process transcription: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
