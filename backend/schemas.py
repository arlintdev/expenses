from pydantic import BaseModel, Field, field_validator
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

# Expense schemas
class ExpenseBase(BaseModel):
    description: str = Field(..., min_length=1, description="What the expense is for")
    recipient: str = Field(..., min_length=1, description="Who the expense is for")
    materials: Optional[str] = Field(None, description="Materials used (optional)")
    hours: Optional[float] = Field(None, ge=0, description="Hours worked (optional)")
    tags: Optional[List[str]] = Field(default_factory=list, description="Expense tags (optional)")
    amount: float = Field(..., gt=0, description="Amount of the expense")
    date: Optional[datetime] = Field(None, description="Date of the expense")

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseResponse(ExpenseBase):
    id: int
    user_id: int
    materials: Optional[str]
    hours: Optional[float]
    tags: List[str] = []
    created_at: datetime
    date: datetime

    model_config = {"from_attributes": True}

    @field_validator('tags', mode='before')
    @classmethod
    def extract_tag_names(cls, v):
        """Convert Tag objects to list of tag names."""
        print(f"Validator called with: {v}, type: {type(v)}")
        if isinstance(v, list) and len(v) > 0:
            if hasattr(v[0], 'name'):
                result = [tag.name for tag in v]
                print(f"Extracted tag names: {result}")
                return result
        print(f"Returning as-is: {v}")
        return v if v else []

class VoiceTranscriptionRequest(BaseModel):
    audio_data: str = Field(..., description="Base64 encoded audio data")

class VoiceTranscriptionResponse(BaseModel):
    transcription: str
    parsed_expense: Optional[ExpenseCreate] = None
    warning: Optional[str] = None
