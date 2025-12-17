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
    recurring: bool = False
    recurring_expense_id: Optional[str] = None
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

# Vehicle schemas
class VehicleBase(BaseModel):
    name: str = Field(..., min_length=1, description="Vehicle name/identifier")
    make: Optional[str] = Field(None, description="Vehicle make")
    model: Optional[str] = Field(None, description="Vehicle model")
    year: Optional[int] = Field(None, ge=1900, le=2100, description="Vehicle year")
    license_plate: Optional[str] = Field(None, description="License plate number")

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = Field(None, ge=1900, le=2100)
    license_plate: Optional[str] = None
    is_active: Optional[bool] = None

class VehicleResponse(VehicleBase):
    id: str
    user_id: str
    last_odometer_reading: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

# Mileage Log schemas
class MileageLogBase(BaseModel):
    vehicle_id: str = Field(..., description="Vehicle UUID")
    date: datetime = Field(..., description="Date of trip")
    purpose: str = Field(..., min_length=1, description="Business purpose")
    odometer_start: int = Field(..., ge=0, description="Starting odometer reading")
    odometer_end: int = Field(..., ge=0, description="Ending odometer reading")
    personal_miles: int = Field(default=0, ge=0, description="Personal miles during trip")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for categorization")

    @field_validator('odometer_end')
    @classmethod
    def validate_odometer(cls, v, info):
        if 'odometer_start' in info.data and v <= info.data['odometer_start']:
            raise ValueError("odometer_end must be greater than odometer_start")
        return v

    @field_validator('personal_miles')
    @classmethod
    def validate_personal_miles(cls, v, info):
        if 'odometer_start' in info.data and 'odometer_end' in info.data:
            total_miles = info.data['odometer_end'] - info.data['odometer_start']
            if v > total_miles:
                raise ValueError("personal_miles cannot exceed total trip miles")
        return v

class MileageLogCreate(MileageLogBase):
    pass

class MileageLogUpdate(BaseModel):
    vehicle_id: Optional[str] = None
    date: Optional[datetime] = None
    purpose: Optional[str] = Field(None, min_length=1)
    odometer_start: Optional[int] = Field(None, ge=0)
    odometer_end: Optional[int] = Field(None, ge=0)
    personal_miles: Optional[int] = Field(None, ge=0)
    tags: Optional[List[str]] = None

class MileageLogResponse(BaseModel):
    id: str
    user_id: str
    vehicle_id: str
    date: datetime
    purpose: str
    odometer_start: int
    odometer_end: int
    personal_miles: int
    business_miles: int
    irs_rate: float
    deductible_amount: float
    linked_expense_id: Optional[str] = None
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator('tags', mode='before')
    @classmethod
    def extract_tag_names(cls, v):
        if isinstance(v, list) and len(v) > 0:
            if hasattr(v[0], 'user_tag'):
                return [mlt.user_tag.name for mlt in v if mlt.user_tag]
            if isinstance(v[0], str):
                return v
        return v if v else []

# IRS Rate Schema
class IRSMileageRateResponse(BaseModel):
    id: str
    year: int
    rate: float
    effective_date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
