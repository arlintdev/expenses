from fastmcp import Server
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
import structlog

from models import (
    get_db, Expense, User, UserTag, ExpenseTag,
    RecurringExpense, RecurringExpenseTag, Vehicle, MileageLog, MileageLogTag, AsyncSessionLocal
)
from schemas import (
    ExpenseCreate, ExpenseResponse, RecurringExpenseCreate, RecurringExpenseResponse,
    VehicleCreate, VehicleResponse, MileageLogCreate, MileageLogResponse, TagCreate
)

logger = structlog.get_logger()

server = Server("expenses-mcp")

class MCPExpenseResponse(BaseModel):
    id: str
    description: str
    recipient: str
    amount: float
    date: str
    tags: List[str]
    created_at: str

class MCPVehicleResponse(BaseModel):
    id: str
    name: str
    make: Optional[str]
    model: Optional[str]
    year: Optional[int]
    license_plate: Optional[str]
    is_active: bool

class MCPMileageLogResponse(BaseModel):
    id: str
    vehicle_id: str
    date: str
    purpose: str
    odometer_start: int
    odometer_end: int
    personal_miles: int
    business_miles: int
    deductible_amount: float
    tags: List[str]

class UserContext:
    def __init__(self, user_id: str, email: str):
        self.user_id = user_id
        self.email = email

def serialize_expense(expense: Expense) -> MCPExpenseResponse:
    return MCPExpenseResponse(
        id=expense.id,
        description=expense.description,
        recipient=expense.recipient,
        amount=expense.amount,
        date=expense.date.isoformat() if expense.date else None,
        tags=expense.tags,
        created_at=expense.created_at.isoformat() if expense.created_at else None,
    )

def serialize_vehicle(vehicle: Vehicle) -> MCPVehicleResponse:
    return MCPVehicleResponse(
        id=vehicle.id,
        name=vehicle.name,
        make=vehicle.make,
        model=vehicle.model,
        year=vehicle.year,
        license_plate=vehicle.license_plate,
        is_active=vehicle.is_active,
    )

def serialize_mileage_log(log: MileageLog) -> MCPMileageLogResponse:
    return MCPMileageLogResponse(
        id=log.id,
        vehicle_id=log.vehicle_id,
        date=log.date.isoformat() if log.date else None,
        purpose=log.purpose,
        odometer_start=log.odometer_start,
        odometer_end=log.odometer_end,
        personal_miles=log.personal_miles,
        business_miles=log.business_miles,
        deductible_amount=log.deductible_amount,
        tags=log.tags,
    )

@server.list_tools()
async def list_tools():
    return [
        {
            "name": "list_expenses",
            "description": "List all expenses for the authenticated user, optionally filtered by date range or tags",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD) for filtering expenses"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD) for filtering expenses"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of expenses to return (default: 100)",
                        "default": 100
                    }
                }
            }
        },
        {
            "name": "create_expense",
            "description": "Create a new expense",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "What the expense is for"
                    },
                    "recipient": {
                        "type": "string",
                        "description": "Who the expense is for"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount of the expense"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of expense (YYYY-MM-DD or ISO format)"
                    },
                    "materials": {
                        "type": "string",
                        "description": "Materials used (optional)"
                    },
                    "hours": {
                        "type": "number",
                        "description": "Hours worked (optional)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization"
                    }
                },
                "required": ["description", "recipient", "amount"]
            }
        },
        {
            "name": "delete_expense",
            "description": "Delete an expense by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "expense_id": {
                        "type": "string",
                        "description": "UUID of the expense to delete"
                    }
                },
                "required": ["expense_id"]
            }
        },
        {
            "name": "list_vehicles",
            "description": "List all vehicles registered by the user",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "include_inactive": {
                        "type": "boolean",
                        "description": "Include inactive vehicles (default: false)"
                    }
                }
            }
        },
        {
            "name": "create_vehicle",
            "description": "Register a new vehicle",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Vehicle name/identifier"
                    },
                    "make": {
                        "type": "string",
                        "description": "Vehicle make (optional)"
                    },
                    "model": {
                        "type": "string",
                        "description": "Vehicle model (optional)"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Vehicle year (optional)"
                    },
                    "license_plate": {
                        "type": "string",
                        "description": "License plate number (optional)"
                    }
                },
                "required": ["name"]
            }
        },
        {
            "name": "list_mileage_logs",
            "description": "List all mileage logs for the authenticated user",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "vehicle_id": {
                        "type": "string",
                        "description": "Filter by vehicle ID (optional)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD) for filtering (optional)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD) for filtering (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number to return (default: 100)",
                        "default": 100
                    }
                }
            }
        },
        {
            "name": "create_mileage_log",
            "description": "Log a business mileage trip",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "vehicle_id": {
                        "type": "string",
                        "description": "UUID of the vehicle"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of trip (YYYY-MM-DD or ISO format)"
                    },
                    "purpose": {
                        "type": "string",
                        "description": "Business purpose of the trip"
                    },
                    "odometer_start": {
                        "type": "integer",
                        "description": "Starting odometer reading"
                    },
                    "odometer_end": {
                        "type": "integer",
                        "description": "Ending odometer reading"
                    },
                    "personal_miles": {
                        "type": "integer",
                        "description": "Personal miles during trip (default: 0)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization"
                    }
                },
                "required": ["vehicle_id", "date", "purpose", "odometer_start", "odometer_end"]
            }
        },
        {
            "name": "delete_mileage_log",
            "description": "Delete a mileage log",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "log_id": {
                        "type": "string",
                        "description": "UUID of the mileage log to delete"
                    }
                },
                "required": ["log_id"]
            }
        },
        {
            "name": "list_tags",
            "description": "List all tags created by the user",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "create_tag",
            "description": "Create a new tag",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Tag name"
                    }
                },
                "required": ["name"]
            }
        },
        {
            "name": "get_expense_summary",
            "description": "Get summary statistics for expenses",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD) (optional)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD) (optional)"
                    }
                }
            }
        },
        {
            "name": "get_mileage_deduction",
            "description": "Calculate total deductible mileage amount for a date range",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD) (optional)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD) (optional)"
                    }
                }
            }
        }
    ]

@server.call_tool()
async def handle_tool_call(name: str, arguments: dict, user_context: Optional[UserContext] = None) -> str:
    if not user_context:
        return '{"error": "User authentication required"}'

    try:
        async with AsyncSessionLocal() as db:
            if name == "list_expenses":
                return await list_expenses(db, user_context, arguments)
            elif name == "create_expense":
                return await create_expense(db, user_context, arguments)
            elif name == "delete_expense":
                return await delete_expense(db, user_context, arguments)
            elif name == "list_vehicles":
                return await list_vehicles(db, user_context, arguments)
            elif name == "create_vehicle":
                return await create_vehicle(db, user_context, arguments)
            elif name == "list_mileage_logs":
                return await list_mileage_logs(db, user_context, arguments)
            elif name == "create_mileage_log":
                return await create_mileage_log(db, user_context, arguments)
            elif name == "delete_mileage_log":
                return await delete_mileage_log(db, user_context, arguments)
            elif name == "list_tags":
                return await list_tags(db, user_context, arguments)
            elif name == "create_tag":
                return await create_tag(db, user_context, arguments)
            elif name == "get_expense_summary":
                return await get_expense_summary(db, user_context, arguments)
            elif name == "get_mileage_deduction":
                return await get_mileage_deduction(db, user_context, arguments)
            else:
                return '{"error": "Unknown tool"}'
    except Exception as e:
        logger.error("mcp_tool_error", tool=name, error=str(e))
        return f'{{"error": "Tool execution failed: {str(e)}"}}'

async def list_expenses(db, user_context: UserContext, arguments: dict) -> str:
    import json
    try:
        query = select(Expense).filter(Expense.user_id == user_context.user_id)

        if "start_date" in arguments and arguments["start_date"]:
            start_date = datetime.fromisoformat(arguments["start_date"])
            query = query.filter(Expense.date >= start_date)

        if "end_date" in arguments and arguments["end_date"]:
            end_date = datetime.fromisoformat(arguments["end_date"])
            query = query.filter(Expense.date <= end_date)

        limit = arguments.get("limit", 100)
        query = query.order_by(Expense.date.desc()).limit(limit)

        result = await db.execute(query)
        expenses = result.scalars().all()

        data = [serialize_expense(e).model_dump() for e in expenses]
        return json.dumps({"expenses": data})
    except Exception as e:
        logger.error("list_expenses_error", error=str(e))
        return json.dumps({"error": str(e)})

async def create_expense(db, user_context: UserContext, arguments: dict) -> str:
    import json
    import uuid6
    try:
        expense_date = arguments.get("date")
        if expense_date:
            expense_date = datetime.fromisoformat(expense_date)
        else:
            expense_date = datetime.utcnow()

        expense = Expense(
            id=str(uuid6.uuid6()),
            user_id=user_context.user_id,
            description=arguments["description"],
            recipient=arguments["recipient"],
            amount=float(arguments["amount"]),
            date=expense_date,
            materials=arguments.get("materials"),
            hours=float(arguments["hours"]) if arguments.get("hours") else None,
        )
        db.add(expense)

        tags = arguments.get("tags", [])
        for tag_name in tags:
            result = await db.execute(
                select(UserTag).filter(
                    UserTag.user_id == user_context.user_id,
                    UserTag.name == tag_name
                )
            )
            user_tag = result.scalar_one_or_none()

            if user_tag:
                expense_tag = ExpenseTag(
                    id=str(uuid6.uuid6()),
                    expense_id=expense.id,
                    user_tag_id=user_tag.id
                )
                db.add(expense_tag)

        await db.commit()
        await db.refresh(expense)

        return json.dumps({"expense": serialize_expense(expense).model_dump()})
    except Exception as e:
        await db.rollback()
        logger.error("create_expense_error", error=str(e))
        return json.dumps({"error": str(e)})

async def delete_expense(db, user_context: UserContext, arguments: dict) -> str:
    import json
    try:
        expense_id = arguments["expense_id"]

        result = await db.execute(
            select(Expense).filter(
                Expense.id == expense_id,
                Expense.user_id == user_context.user_id
            )
        )
        expense = result.scalar_one_or_none()

        if not expense:
            return json.dumps({"error": "Expense not found"})

        await db.delete(expense)
        await db.commit()

        return json.dumps({"success": True, "message": "Expense deleted"})
    except Exception as e:
        await db.rollback()
        logger.error("delete_expense_error", error=str(e))
        return json.dumps({"error": str(e)})

async def list_vehicles(db, user_context: UserContext, arguments: dict) -> str:
    import json
    try:
        query = select(Vehicle).filter(Vehicle.user_id == user_context.user_id)

        if not arguments.get("include_inactive", False):
            query = query.filter(Vehicle.is_active == True)

        result = await db.execute(query.order_by(Vehicle.created_at.desc()))
        vehicles = result.scalars().all()

        data = [serialize_vehicle(v).model_dump() for v in vehicles]
        return json.dumps({"vehicles": data})
    except Exception as e:
        logger.error("list_vehicles_error", error=str(e))
        return json.dumps({"error": str(e)})

async def create_vehicle(db, user_context: UserContext, arguments: dict) -> str:
    import json
    import uuid6
    try:
        vehicle = Vehicle(
            id=str(uuid6.uuid6()),
            user_id=user_context.user_id,
            name=arguments["name"],
            make=arguments.get("make"),
            model=arguments.get("model"),
            year=arguments.get("year"),
            license_plate=arguments.get("license_plate"),
        )
        db.add(vehicle)
        await db.commit()
        await db.refresh(vehicle)

        return json.dumps({"vehicle": serialize_vehicle(vehicle).model_dump()})
    except Exception as e:
        await db.rollback()
        logger.error("create_vehicle_error", error=str(e))
        return json.dumps({"error": str(e)})

async def list_mileage_logs(db, user_context: UserContext, arguments: dict) -> str:
    import json
    try:
        query = select(MileageLog).filter(MileageLog.user_id == user_context.user_id)

        if arguments.get("vehicle_id"):
            query = query.filter(MileageLog.vehicle_id == arguments["vehicle_id"])

        if arguments.get("start_date"):
            start_date = datetime.fromisoformat(arguments["start_date"])
            query = query.filter(MileageLog.date >= start_date)

        if arguments.get("end_date"):
            end_date = datetime.fromisoformat(arguments["end_date"])
            query = query.filter(MileageLog.date <= end_date)

        limit = arguments.get("limit", 100)
        query = query.order_by(MileageLog.date.desc()).limit(limit)

        result = await db.execute(query)
        logs = result.scalars().all()

        data = [serialize_mileage_log(l).model_dump() for l in logs]
        return json.dumps({"mileage_logs": data})
    except Exception as e:
        logger.error("list_mileage_logs_error", error=str(e))
        return json.dumps({"error": str(e)})

async def create_mileage_log(db, user_context: UserContext, arguments: dict) -> str:
    import json
    import uuid6
    try:
        log_date = datetime.fromisoformat(arguments["date"])

        log = MileageLog(
            id=str(uuid6.uuid6()),
            user_id=user_context.user_id,
            vehicle_id=arguments["vehicle_id"],
            date=log_date,
            purpose=arguments["purpose"],
            odometer_start=int(arguments["odometer_start"]),
            odometer_end=int(arguments["odometer_end"]),
            personal_miles=int(arguments.get("personal_miles", 0)),
            irs_rate=0.67,
        )
        db.add(log)

        tags = arguments.get("tags", [])
        for tag_name in tags:
            result = await db.execute(
                select(UserTag).filter(
                    UserTag.user_id == user_context.user_id,
                    UserTag.name == tag_name
                )
            )
            user_tag = result.scalar_one_or_none()

            if user_tag:
                mileage_tag = MileageLogTag(
                    id=str(uuid6.uuid6()),
                    mileage_log_id=log.id,
                    user_tag_id=user_tag.id
                )
                db.add(mileage_tag)

        await db.commit()
        await db.refresh(log)

        return json.dumps({"mileage_log": serialize_mileage_log(log).model_dump()})
    except Exception as e:
        await db.rollback()
        logger.error("create_mileage_log_error", error=str(e))
        return json.dumps({"error": str(e)})

async def delete_mileage_log(db, user_context: UserContext, arguments: dict) -> str:
    import json
    try:
        log_id = arguments["log_id"]

        result = await db.execute(
            select(MileageLog).filter(
                MileageLog.id == log_id,
                MileageLog.user_id == user_context.user_id
            )
        )
        log = result.scalar_one_or_none()

        if not log:
            return json.dumps({"error": "Mileage log not found"})

        await db.delete(log)
        await db.commit()

        return json.dumps({"success": True, "message": "Mileage log deleted"})
    except Exception as e:
        await db.rollback()
        logger.error("delete_mileage_log_error", error=str(e))
        return json.dumps({"error": str(e)})

async def list_tags(db, user_context: UserContext, arguments: dict) -> str:
    import json
    try:
        result = await db.execute(
            select(UserTag).filter(UserTag.user_id == user_context.user_id).order_by(UserTag.name)
        )
        tags = result.scalars().all()

        data = [{"id": t.id, "name": t.name} for t in tags]
        return json.dumps({"tags": data})
    except Exception as e:
        logger.error("list_tags_error", error=str(e))
        return json.dumps({"error": str(e)})

async def create_tag(db, user_context: UserContext, arguments: dict) -> str:
    import json
    import uuid6
    try:
        tag = UserTag(
            id=str(uuid6.uuid6()),
            user_id=user_context.user_id,
            name=arguments["name"]
        )
        db.add(tag)
        await db.commit()
        await db.refresh(tag)

        return json.dumps({"tag": {"id": tag.id, "name": tag.name}})
    except Exception as e:
        await db.rollback()
        logger.error("create_tag_error", error=str(e))
        return json.dumps({"error": str(e)})

async def get_expense_summary(db, user_context: UserContext, arguments: dict) -> str:
    import json
    try:
        query = select(
            func.sum(Expense.amount),
            func.count(Expense.id),
            func.avg(Expense.amount)
        ).filter(Expense.user_id == user_context.user_id)

        if arguments.get("start_date"):
            start_date = datetime.fromisoformat(arguments["start_date"])
            query = query.filter(Expense.date >= start_date)

        if arguments.get("end_date"):
            end_date = datetime.fromisoformat(arguments["end_date"])
            query = query.filter(Expense.date <= end_date)

        result = await db.execute(query)
        total, count, average = result.one()

        return json.dumps({
            "summary": {
                "total_amount": float(total) if total else 0.0,
                "expense_count": count or 0,
                "average_amount": float(average) if average else 0.0
            }
        })
    except Exception as e:
        logger.error("get_expense_summary_error", error=str(e))
        return json.dumps({"error": str(e)})

async def get_mileage_deduction(db, user_context: UserContext, arguments: dict) -> str:
    import json
    try:
        query = select(
            func.sum(MileageLog.business_miles),
            func.sum(MileageLog.deductible_amount)
        ).filter(MileageLog.user_id == user_context.user_id)

        if arguments.get("start_date"):
            start_date = datetime.fromisoformat(arguments["start_date"])
            query = query.filter(MileageLog.date >= start_date)

        if arguments.get("end_date"):
            end_date = datetime.fromisoformat(arguments["end_date"])
            query = query.filter(MileageLog.date <= end_date)

        result = await db.execute(query)
        business_miles, deductible = result.one()

        return json.dumps({
            "mileage_deduction": {
                "business_miles": int(business_miles) if business_miles else 0,
                "deductible_amount": float(deductible) if deductible else 0.0
            }
        })
    except Exception as e:
        logger.error("get_mileage_deduction_error", error=str(e))
        return json.dumps({"error": str(e)})
