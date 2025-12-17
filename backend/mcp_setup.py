"""
Setup FastMCP integration with Google OAuth for FastAPI app.

This module creates an MCP server that can be mounted into the main FastAPI app.
"""

import os
from fastmcp import FastMCP
from fastmcp.auth import GoogleProvider
import structlog
from sqlalchemy import select

from models import User, AsyncSessionLocal, Expense, Vehicle, MileageLog, UserTag
from mcp_server import serialize_expense, serialize_vehicle, serialize_mileage_log
import uuid6

logger = structlog.get_logger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def create_mcp_app():
    """Create and configure FastMCP app with OAuth."""

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.warning("fastmcp_disabled", reason="Missing Google OAuth credentials")
        return None

    auth_provider = GoogleProvider(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        base_url=BASE_URL,
    )

    mcp = FastMCP(
        "Expenses MCP Server",
        auth=auth_provider,
    )

    @mcp.tool()
    async def list_expenses(
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
    ) -> dict:
        """List all user expenses with optional date filtering."""
        try:
            from datetime import datetime

            # Get user from auth context - FastMCP provides this automatically
            user = await get_current_user()

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

                return {"expenses": [serialize_expense(e).model_dump() for e in expenses]}
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
        """Create a new expense."""
        try:
            from datetime import datetime

            user = await get_current_user()

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
        """Delete an expense by ID."""
        try:
            user = await get_current_user()

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
        """List all vehicles registered by the user."""
        try:
            user = await get_current_user()

            async with AsyncSessionLocal() as db:
                query = select(Vehicle).filter(Vehicle.user_id == user.id)

                if not include_inactive:
                    query = query.filter(Vehicle.is_active == True)

                result = await db.execute(query.order_by(Vehicle.created_at.desc()))
                vehicles = result.scalars().all()

                return {"vehicles": [serialize_vehicle(v).model_dump() for v in vehicles]}
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
        """Register a new vehicle."""
        try:
            user = await get_current_user()

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
        """List all mileage logs for the authenticated user."""
        try:
            from datetime import datetime
            user = await get_current_user()

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

                return {"mileage_logs": [serialize_mileage_log(l).model_dump() for l in logs]}
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
        """Log a business mileage trip."""
        try:
            from datetime import datetime

            user = await get_current_user()
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
        """Delete a mileage log."""
        try:
            user = await get_current_user()

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
            user = await get_current_user()

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(UserTag).filter(UserTag.user_id == user.id).order_by(UserTag.name)
                )
                tags = result.scalars().all()

                return {"tags": [{"id": t.id, "name": t.name} for t in tags]}
        except Exception as e:
            logger.error("list_tags_error", error=str(e))
            return {"error": str(e)}

    @mcp.tool()
    async def create_tag(name: str) -> dict:
        """Create a new tag."""
        try:
            user = await get_current_user()

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

    return mcp

async def get_current_user() -> User:
    """Get the current authenticated user from FastMCP context."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("No user found")
        return user
