from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

# User schemas
class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    picture: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class GoogleAuthRequest(BaseModel):
    token: str = Field(..., description="Google ID token")

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Category schemas
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Category name")

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Expense schemas
class ExpenseBase(BaseModel):
    description: str = Field(..., min_length=1, description="What the expense is for")
    recipient: str = Field(..., min_length=1, description="Who the expense is for")
    materials: Optional[str] = Field(None, description="Materials used (optional)")
    hours: Optional[float] = Field(None, ge=0, description="Hours worked (optional)")
    category: Optional[str] = Field(None, description="Expense category (optional)")
    amount: float = Field(..., gt=0, description="Amount of the expense")
    date: Optional[datetime] = Field(None, description="Date of the expense")

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseResponse(ExpenseBase):
    id: int
    user_id: int
    materials: Optional[str]
    hours: Optional[float]
    category: Optional[str]
    created_at: datetime
    date: datetime

    class Config:
        from_attributes = True

class VoiceTranscriptionRequest(BaseModel):
    audio_data: str = Field(..., description="Base64 encoded audio data")

class VoiceTranscriptionResponse(BaseModel):
    transcription: str
    parsed_expense: Optional[ExpenseCreate] = None
    warning: Optional[str] = None
