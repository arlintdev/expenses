"""
FastMCP Server with Google OAuth Authentication

This server integrates with FastMCP's built-in OAuth provider for zero-config
enterprise authentication. Claude Desktop automatically handles the OAuth flow.
"""

import os
from fastmcp import FastMCP
from fastmcp.auth import GoogleProvider
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, AsyncSessionLocal, Expense, Vehicle, MileageLog, UserTag
from mcp_server import (
    list_tools, handle_tool_call, UserContext,
    serialize_expense, serialize_vehicle, serialize_mileage_log
)

logger = structlog.get_logger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables required")

auth_provider = GoogleProvider(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    base_url=BASE_URL,
)

mcp = FastMCP(
    "Expenses MCP Server",
    auth=auth_provider,
)

async def get_user_from_auth_context(auth_context) -> User:
    """Extract user from FastMCP auth context."""
    email = auth_context.get("email")
    if not email:
        raise ValueError("Email not found in auth context")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).filter(User.email == email)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {email} not found")
        return user

@mcp.tool()
async def list_expenses(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
) -> dict:
    """List all user expenses with optional date filtering.

    Args:
        start_date: Start date (YYYY-MM-DD) for filtering expenses
        end_date: End date (YYYY-MM-DD) for filtering expenses
        limit: Maximum number of expenses to return (default: 100)
    """
    try:
        from datetime import datetime

        user = await get_user_from_auth_context({})

        async with AsyncSessionLocal() as db:
            query = select(Expense).filter(Expense.user_id == user.id)

            if start_date:
                start = datetime.fromisoformat(start_date)
                query = query.filter(Expense.date >= start)

            if end_date:
                end = datetime.fromisoformat(end_date)
                query = query.filter(Expense.date <= end)

            query = query.order_by(Expense.date.desc()).limit(limit)
            result = await db.execute(query)
            expenses = result.scalars().all()

            return {
                "expenses": [serialize_expense(e).model_dump() for e in expenses]
            }
    except Exception as e:
        logger.error("list_expenses_error", error=str(e))
        return {"error": str(e)}

@mcp.tool()
async def create_expense(
    description: str,
    recipient: str,
    amount: float,
    date: str | None = None,
    materials: str | None = None,
    hours: float | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Create a new expense.

    Args:
        description: What the expense is for
        recipient: Who the expense is for
        amount: Amount of the expense
        date: Date of expense (YYYY-MM-DD or ISO format)
        materials: Materials used (optional)
        hours: Hours worked (optional)
        tags: Tags for categorization (optional)
    """
    try:
        from datetime import datetime
        import uuid6

        user = await get_user_from_auth_context({})

        expense_date = None
        if date:
            expense_date = datetime.fromisoformat(date)
        else:
            expense_date = datetime.utcnow()

        async with AsyncSessionLocal() as db:
            expense = Expense(
                id=str(uuid6.uuid6()),
                user_id=user.id,
                description=description,
                recipient=recipient,
                amount=float(amount),
                date=expense_date,
                materials=materials,
                hours=float(hours) if hours else None,
            )
            db.add(expense)

            if tags:
                from models import ExpenseTag
                for tag_name in tags:
                    result = await db.execute(
                        select(UserTag).filter(
                            UserTag.user_id == user.id,
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

            return {"expense": serialize_expense(expense).model_dump()}
    except Exception as e:
        logger.error("create_expense_error", error=str(e))
        return {"error": str(e)}

@mcp.tool()
async def delete_expense(expense_id: str) -> dict:
    """Delete an expense by ID.

    Args:
        expense_id: UUID of the expense to delete
    """
    try:
        user = await get_user_from_auth_context({})

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Expense).filter(
                    Expense.id == expense_id,
                    Expense.user_id == user.id
                )
            )
            expense = result.scalar_one_or_none()

            if not expense:
                return {"error": "Expense not found"}

            await db.delete(expense)
            await db.commit()

            return {"success": True, "message": "Expense deleted"}
    except Exception as e:
        logger.error("delete_expense_error", error=str(e))
        return {"error": str(e)}

@mcp.tool()
async def list_vehicles(include_inactive: bool = False) -> dict:
    """List all vehicles registered by the user.

    Args:
        include_inactive: Include inactive vehicles (default: false)
    """
    try:
        user = await get_user_from_auth_context({})

        async with AsyncSessionLocal() as db:
            query = select(Vehicle).filter(Vehicle.user_id == user.id)

            if not include_inactive:
                query = query.filter(Vehicle.is_active == True)

            result = await db.execute(query.order_by(Vehicle.created_at.desc()))
            vehicles = result.scalars().all()

            return {
                "vehicles": [serialize_vehicle(v).model_dump() for v in vehicles]
            }
    except Exception as e:
        logger.error("list_vehicles_error", error=str(e))
        return {"error": str(e)}

@mcp.tool()
async def create_vehicle(
    name: str,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    license_plate: str | None = None,
) -> dict:
    """Register a new vehicle.

    Args:
        name: Vehicle name/identifier
        make: Vehicle make (optional)
        model: Vehicle model (optional)
        year: Vehicle year (optional)
        license_plate: License plate number (optional)
    """
    try:
        import uuid6
        user = await get_user_from_auth_context({})

        async with AsyncSessionLocal() as db:
            vehicle = Vehicle(
                id=str(uuid6.uuid6()),
                user_id=user.id,
                name=name,
                make=make,
                model=model,
                year=year,
                license_plate=license_plate,
            )
            db.add(vehicle)
            await db.commit()
            await db.refresh(vehicle)

            return {"vehicle": serialize_vehicle(vehicle).model_dump()}
    except Exception as e:
        logger.error("create_vehicle_error", error=str(e))
        return {"error": str(e)}

@mcp.tool()
async def list_mileage_logs(
    vehicle_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
) -> dict:
    """List all mileage logs for the authenticated user.

    Args:
        vehicle_id: Filter by vehicle ID (optional)
        start_date: Start date (YYYY-MM-DD) for filtering (optional)
        end_date: End date (YYYY-MM-DD) for filtering (optional)
        limit: Maximum number to return (default: 100)
    """
    try:
        from datetime import datetime
        user = await get_user_from_auth_context({})

        async with AsyncSessionLocal() as db:
            query = select(MileageLog).filter(MileageLog.user_id == user.id)

            if vehicle_id:
                query = query.filter(MileageLog.vehicle_id == vehicle_id)

            if start_date:
                start = datetime.fromisoformat(start_date)
                query = query.filter(MileageLog.date >= start)

            if end_date:
                end = datetime.fromisoformat(end_date)
                query = query.filter(MileageLog.date <= end)

            query = query.order_by(MileageLog.date.desc()).limit(limit)
            result = await db.execute(query)
            logs = result.scalars().all()

            return {
                "mileage_logs": [serialize_mileage_log(l).model_dump() for l in logs]
            }
    except Exception as e:
        logger.error("list_mileage_logs_error", error=str(e))
        return {"error": str(e)}

@mcp.tool()
async def create_mileage_log(
    vehicle_id: str,
    date: str,
    purpose: str,
    odometer_start: int,
    odometer_end: int,
    personal_miles: int = 0,
    tags: list[str] | None = None,
) -> dict:
    """Log a business mileage trip.

    Args:
        vehicle_id: UUID of the vehicle
        date: Date of trip (YYYY-MM-DD or ISO format)
        purpose: Business purpose of the trip
        odometer_start: Starting odometer reading
        odometer_end: Ending odometer reading
        personal_miles: Personal miles during trip (default: 0)
        tags: Tags for categorization (optional)
    """
    try:
        from datetime import datetime
        import uuid6

        user = await get_user_from_auth_context({})
        log_date = datetime.fromisoformat(date)

        async with AsyncSessionLocal() as db:
            log = MileageLog(
                id=str(uuid6.uuid6()),
                user_id=user.id,
                vehicle_id=vehicle_id,
                date=log_date,
                purpose=purpose,
                odometer_start=int(odometer_start),
                odometer_end=int(odometer_end),
                personal_miles=int(personal_miles),
                irs_rate=0.67,
            )
            db.add(log)

            if tags:
                from models import MileageLogTag
                for tag_name in tags:
                    result = await db.execute(
                        select(UserTag).filter(
                            UserTag.user_id == user.id,
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

            return {"mileage_log": serialize_mileage_log(log).model_dump()}
    except Exception as e:
        logger.error("create_mileage_log_error", error=str(e))
        return {"error": str(e)}

@mcp.tool()
async def delete_mileage_log(log_id: str) -> dict:
    """Delete a mileage log.

    Args:
        log_id: UUID of the mileage log to delete
    """
    try:
        user = await get_user_from_auth_context({})

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(MileageLog).filter(
                    MileageLog.id == log_id,
                    MileageLog.user_id == user.id
                )
            )
            log = result.scalar_one_or_none()

            if not log:
                return {"error": "Mileage log not found"}

            await db.delete(log)
            await db.commit()

            return {"success": True, "message": "Mileage log deleted"}
    except Exception as e:
        logger.error("delete_mileage_log_error", error=str(e))
        return {"error": str(e)}

@mcp.tool()
async def list_tags() -> dict:
    """List all tags created by the user."""
    try:
        user = await get_user_from_auth_context({})

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(UserTag).filter(UserTag.user_id == user.id).order_by(UserTag.name)
            )
            tags = result.scalars().all()

            return {
                "tags": [{"id": t.id, "name": t.name} for t in tags]
            }
    except Exception as e:
        logger.error("list_tags_error", error=str(e))
        return {"error": str(e)}

@mcp.tool()
async def create_tag(name: str) -> dict:
    """Create a new tag.

    Args:
        name: Tag name
    """
    try:
        import uuid6
        user = await get_user_from_auth_context({})

        async with AsyncSessionLocal() as db:
            tag = UserTag(
                id=str(uuid6.uuid6()),
                user_id=user.id,
                name=name
            )
            db.add(tag)
            await db.commit()
            await db.refresh(tag)

            return {"tag": {"id": tag.id, "name": tag.name}}
    except Exception as e:
        logger.error("create_tag_error", error=str(e))
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "fastmcp_server:mcp",
        host="0.0.0.0",
        port=8001,
        log_level="info",
    )
