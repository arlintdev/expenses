"""add_vehicle_mileage_tracking

Revision ID: add_vehicle_mileage_tracking
Revises: add_recurring_expenses
Create Date: 2025-12-16 20:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision: str = 'add_vehicle_mileage_tracking'
down_revision: Union[str, Sequence[str], None] = 'add_recurring_expenses'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""

    # Create vehicles table
    op.create_table('vehicles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('make', sa.String(), nullable=True),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('license_plate', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vehicles_id'), 'vehicles', ['id'], unique=False)
    op.create_index(op.f('ix_vehicles_user_id'), 'vehicles', ['user_id'], unique=False)
    op.create_index('ix_vehicles_user_active', 'vehicles', ['user_id', 'is_active'], unique=False)
    op.create_index(op.f('ix_vehicles_is_active'), 'vehicles', ['is_active'], unique=False)

    # Create mileage_logs table
    op.create_table('mileage_logs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('vehicle_id', sa.String(36), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False),
        sa.Column('odometer_start', sa.Integer(), nullable=False),
        sa.Column('odometer_end', sa.Integer(), nullable=False),
        sa.Column('personal_miles', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('irs_rate', sa.Float(), nullable=False),
        sa.Column('linked_expense_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['linked_expense_id'], ['expenses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mileage_logs_id'), 'mileage_logs', ['id'], unique=False)
    op.create_index(op.f('ix_mileage_logs_user_id'), 'mileage_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_mileage_logs_vehicle_id'), 'mileage_logs', ['vehicle_id'], unique=False)
    op.create_index(op.f('ix_mileage_logs_date'), 'mileage_logs', ['date'], unique=False)
    op.create_index(op.f('ix_mileage_logs_linked_expense_id'), 'mileage_logs', ['linked_expense_id'], unique=True)

    # Create mileage_log_tags junction table
    op.create_table('mileage_log_tags',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('mileage_log_id', sa.String(36), nullable=False),
        sa.Column('user_tag_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['mileage_log_id'], ['mileage_logs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_tag_id'], ['user_tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mileage_log_tags_id'), 'mileage_log_tags', ['id'], unique=False)
    op.create_index(op.f('ix_mileage_log_tags_mileage_log_id'), 'mileage_log_tags', ['mileage_log_id'], unique=False)
    op.create_index(op.f('ix_mileage_log_tags_user_tag_id'), 'mileage_log_tags', ['user_tag_id'], unique=False)

    # Create irs_mileage_rates table
    op.create_table('irs_mileage_rates',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('rate', sa.Float(), nullable=False),
        sa.Column('effective_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_irs_mileage_rates_id'), 'irs_mileage_rates', ['id'], unique=False)
    op.create_index(op.f('ix_irs_mileage_rates_year'), 'irs_mileage_rates', ['year'], unique=True)

    # Seed IRS mileage rates for 2024-2025
    # Check if database is SQLite or PostgreSQL to use appropriate UUID generation
    import uuid6
    rate_2024_id = str(uuid6.uuid6())
    rate_2025_id = str(uuid6.uuid6())

    op.execute(
        f"""
        INSERT INTO irs_mileage_rates (id, year, rate, effective_date, created_at, updated_at)
        VALUES
            ('{rate_2024_id}', 2024, 0.67, '2024-01-01', datetime('now'), datetime('now')),
            ('{rate_2025_id}', 2025, 0.67, '2025-01-01', datetime('now'), datetime('now'))
        """
    )

    # Add linked_mileage_log_id to expenses table
    op.add_column('expenses', sa.Column('linked_mileage_log_id', sa.String(36), nullable=True))
    op.create_foreign_key('fk_expenses_linked_mileage_log', 'expenses', 'mileage_logs', ['linked_mileage_log_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_expenses_linked_mileage_log_id', 'expenses', ['linked_mileage_log_id'], unique=True)

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_expenses_linked_mileage_log_id', table_name='expenses')
    op.drop_constraint('fk_expenses_linked_mileage_log', 'expenses', type_='foreignkey')
    op.drop_column('expenses', 'linked_mileage_log_id')

    op.drop_index(op.f('ix_irs_mileage_rates_year'), table_name='irs_mileage_rates')
    op.drop_index(op.f('ix_irs_mileage_rates_id'), table_name='irs_mileage_rates')
    op.drop_table('irs_mileage_rates')

    op.drop_index(op.f('ix_mileage_log_tags_user_tag_id'), table_name='mileage_log_tags')
    op.drop_index(op.f('ix_mileage_log_tags_mileage_log_id'), table_name='mileage_log_tags')
    op.drop_index(op.f('ix_mileage_log_tags_id'), table_name='mileage_log_tags')
    op.drop_table('mileage_log_tags')

    op.drop_index(op.f('ix_mileage_logs_linked_expense_id'), table_name='mileage_logs')
    op.drop_index(op.f('ix_mileage_logs_date'), table_name='mileage_logs')
    op.drop_index(op.f('ix_mileage_logs_vehicle_id'), table_name='mileage_logs')
    op.drop_index(op.f('ix_mileage_logs_user_id'), table_name='mileage_logs')
    op.drop_index(op.f('ix_mileage_logs_id'), table_name='mileage_logs')
    op.drop_table('mileage_logs')

    op.drop_index('ix_vehicles_user_active', table_name='vehicles')
    op.drop_index(op.f('ix_vehicles_is_active'), table_name='vehicles')
    op.drop_index(op.f('ix_vehicles_user_id'), table_name='vehicles')
    op.drop_index(op.f('ix_vehicles_id'), table_name='vehicles')
    op.drop_table('vehicles')
