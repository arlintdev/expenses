from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List

# User schemas
class UserResponse(BaseModel):
    id: str  # UUIDv6 string
    email: str
    name: Optional[str]
    picture: Optional[str]
    is_admin: bool
    created_at: datetime
    updated_at: datetime

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
    id: str  # UUIDv6 string
    user_id: str  # UUIDv6 string
    materials: Optional[str]
    hours: Optional[float]
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
    date: datetime

    model_config = {"from_attributes": True}

    @field_validator('tags', mode='before')
    @classmethod
    def extract_tag_names(cls, v):
        """Convert ExpenseTag objects to list of tag names."""
        if isinstance(v, list) and len(v) > 0:
            # Handle ExpenseTag objects (new system)
            if hasattr(v[0], 'user_tag'):
                return [et.user_tag.name for et in v if et.user_tag]
            # Handle direct tag name strings (already processed)
            if isinstance(v[0], str):
                return v
        return v if v else []

class VoiceTranscriptionRequest(BaseModel):
    audio_data: str = Field(..., description="Base64 encoded audio data")

class VoiceTranscriptionResponse(BaseModel):
    transcription: str
    parsed_expense: Optional[ExpenseCreate] = None
    warning: Optional[str] = None

class RecurringExpenseBase(BaseModel):
    description: str = Field(..., min_length=1, description="What the expense is for")
    recipient: str = Field(..., min_length=1, description="Who the expense is for")
    materials: Optional[str] = Field(None, description="Materials used (optional)")
    hours: Optional[float] = Field(None, ge=0, description="Hours worked (optional)")
    tags: Optional[List[str]] = Field(default_factory=list, description="Expense tags (optional)")
    amount: float = Field(..., gt=0, description="Amount of the expense")
    start_month: int = Field(..., ge=1, le=12, description="Start month (1-12)")
    start_year: int = Field(..., ge=2000, description="Start year")
    end_month: int = Field(..., ge=1, le=12, description="End month (1-12)")
    end_year: int = Field(..., ge=2000, description="End year")
    day_of_month: int = Field(default=1, ge=1, le=31, description="Day of month to create expense")

class RecurringExpenseCreate(RecurringExpenseBase):
    pass

class RecurringExpenseResponse(RecurringExpenseBase):
    id: str
    user_id: str
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator('tags', mode='before')
    @classmethod
    def extract_tag_names(cls, v):
        """Convert RecurringExpenseTag objects to list of tag names."""
        if isinstance(v, list) and len(v) > 0:
            if hasattr(v[0], 'user_tag'):
                return [ret.user_tag.name for ret in v if ret.user_tag]
            if isinstance(v[0], str):
                return v
        return v if v else []

# Analytics schemas
class SummaryStats(BaseModel):
    total_amount: float = Field(..., description="Total amount spent")
    expense_count: int = Field(..., description="Number of expenses")
    average_amount: float = Field(..., description="Average expense amount")
    date_from: Optional[datetime] = Field(None, description="Start date of range")
    date_to: Optional[datetime] = Field(None, description="End date of range")

class TagSpending(BaseModel):
    tag: str = Field(..., description="Tag name")
    total_amount: float = Field(..., description="Total spent for this tag")
    expense_count: int = Field(..., description="Number of expenses with this tag")
    percentage: float = Field(..., description="Percentage of total spending")

class ByTagResponse(BaseModel):
    data: List[TagSpending]
    total_amount: float

class DateSpending(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    amount: float = Field(..., description="Total amount for this date")
    expense_count: int = Field(..., description="Number of expenses on this date")

class ByDateResponse(BaseModel):
    data: List[DateSpending]

# CSV submission schemas
class CsvRowResult(BaseModel):
    row_number: int = Field(..., description="Row number in CSV (1-indexed)")
    status: str = Field(..., description="Status: 'success' or 'error'")
    expense: Optional[ExpenseResponse] = Field(None, description="Created expense if successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")

class SubmitCsvResponse(BaseModel):
    total_rows: int = Field(..., description="Total rows processed (excluding header)")
    successful: int = Field(..., description="Number of expenses created successfully")
    failed: int = Field(..., description="Number of rows that failed")
    results: List[CsvRowResult] = Field(..., description="Detailed result for each row")

# Admin schemas
class AdminUserSummary(BaseModel):
    id: str
    email: str
    name: Optional[str]
    is_admin: bool
    expense_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AdminUsersResponse(BaseModel):
    users: List['AdminUserSummary']
    total_users: int
    total_admins: int

# Tag schemas
class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Tag name")
