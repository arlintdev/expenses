"""add uuid to expenses

Revision ID: add_uuid_to_expenses
Revises: 
Create Date: 2025-12-16

"""
from alembic import op
import sqlalchemy as sa
import uuid6

# revision identifiers, used by Alembic.
revision = 'add_uuid_to_expenses'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add uuid column as nullable first
    op.add_column('expenses', sa.Column('uuid', sa.String(36), nullable=True))
    
    # Generate UUIDs for existing rows
    connection = op.get_bind()
    expenses = connection.execute(sa.text("SELECT id FROM expenses")).fetchall()
    for expense in expenses:
        new_uuid = str(uuid6.uuid6())
        connection.execute(
            sa.text("UPDATE expenses SET uuid = :uuid WHERE id = :id"),
            {"uuid": new_uuid, "id": expense[0]}
        )
    
    # Make uuid NOT NULL and add unique constraint
    op.alter_column('expenses', 'uuid', nullable=False)
    op.create_index('ix_expenses_uuid', 'expenses', ['uuid'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_expenses_uuid', table_name='expenses')
    op.drop_column('expenses', 'uuid')
