"""Add expense_context to users table

Revision ID: ee0421ab0679
Revises: 
Create Date: 2025-12-13 22:21:51.371553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee0421ab0679'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if column already exists before adding
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Get existing columns
    columns = [col['name'] for col in inspector.get_columns('users')]

    # Add expense_context column if it doesn't exist
    if 'expense_context' not in columns:
        op.add_column('users', sa.Column('expense_context', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove expense_context column
    op.drop_column('users', 'expense_context')
