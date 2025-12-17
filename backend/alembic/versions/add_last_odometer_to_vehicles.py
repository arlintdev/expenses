"""add_last_odometer_to_vehicles

Revision ID: add_last_odometer_to_vehicles
Revises: add_vehicle_mileage_tracking
Create Date: 2025-12-16 22:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_last_odometer_to_vehicles'
down_revision: Union[str, Sequence[str], None] = 'add_vehicle_mileage_tracking'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Add last_odometer_reading to vehicles table."""
    op.add_column('vehicles', sa.Column('last_odometer_reading', sa.Integer(), nullable=True))

def downgrade() -> None:
    """Remove last_odometer_reading from vehicles table."""
    op.drop_column('vehicles', 'last_odometer_reading')
