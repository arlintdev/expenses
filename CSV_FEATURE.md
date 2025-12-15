# CSV Bulk Expense Submission Feature

## Overview
Added support for bulk expense submission via CSV files. Each row in the CSV is processed by Claude AI to generate a valid expense entry, using the column headers as context.

## Backend Implementation

### New Endpoint
- **POST** `/api/submit-csv` - Upload and process CSV files
- Accepts: CSV file upload
- Returns: `SubmitCsvResponse` with per-row results and summary statistics

### New Schemas (`schemas.py`)
```python
class CsvRowResult(BaseModel):
  row_number: int
  status: str  # "success" or "error"
  expense: Optional[ExpenseResponse]
  error_message: Optional[str]

class SubmitCsvResponse(BaseModel):
  total_rows: int
  successful: int
  failed: int
  results: List[CsvRowResult]
```

### Processing Flow
1. Parse CSV with DictReader to get column headers
2. For each row:
   - Format as text: "column1: value1, column2: value2, ..."
   - Send to Claude via `parse_expense_from_text()`
   - Use user's existing tags and context for interpretation
   - Create expense in database if parsing succeeds
3. Return detailed results with row numbers and error messages

## Frontend Implementation

### UI Changes
- **Bulk Upload Mode** now supports both images and CSV files
- File input accepts: `image/*` and `.csv`
- Mode button updated to say "Multiple receipts or CSV"

### CSV Processing (`AddExpenseModal.jsx`)
- New `processCsvUpload()` function handles CSV file submission
- Results display shows:
  - Row numbers instead of filenames
  - Success/failure status
  - Error messages for failed rows
- Progress tracking shows total rows, successes, and failures

### Error Display
- New `.file-error` CSS class for displaying row-level error messages
- Errors appear beneath failed row entries
- Supports dark mode styling

## CSV Format Requirements

### Expected Format
Header row + data rows with columns representing expense attributes:

```csv
description,amount,recipient,date,tags,materials,hours
Office supplies,50.00,Staples,2024-12-15,office,pens and paper,
Consulting work,200.00,Client A,2024-12-14,work,
```

### Flexible Column Interpretation
- Claude interprets column names and values naturally
- Column names don't need to match exact field names
- Example alternate columns: "item_name", "price", "vendor", "category"
- Missing columns are handled gracefully (optional fields)

## Usage Example

### 1. Prepare CSV File
```csv
item,cost,store,category
Lunch,15.50,Chipotle,food
Gas,45.00,Shell,travel
Office chair,199.99,IKEA,home office
```

### 2. Submit via UI
1. Click "Add Expense" → "Bulk Upload"
2. Select CSV file (or drag & drop)
3. View real-time progress and results

### 3. Handle Results
- Successful rows are automatically created as expenses
- Failed rows show error messages explaining why they failed
- Can upload another file or review results

## Error Handling

### Backend
- Invalid CSV format → HTTP 400
- Empty CSV → HTTP 400
- Individual row parsing failures → Recorded in results with error message
- Database errors → HTTP 500 (partial rollback if needed)

### Frontend
- Network errors → Display error message
- Validation errors → Show per-row error details
- Partial success → Show summary with both successes and failures

## Benefits

1. **Bulk Import** - Add dozens of expenses at once
2. **Flexible Format** - CSV columns interpreted intelligently by Claude
3. **Smart Parsing** - Respects user's existing tags and context
4. **Error Visibility** - Clear feedback on what failed and why
5. **User-Friendly** - Integrated into existing bulk upload UI
