"""add updated_at to all tables

Revision ID: add_updated_at
Revises: migrate_all_to_uuid
Create Date: 2025-12-16

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_updated_at'
down_revision = 'migrate_all_to_uuid'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add updated_at timestamp columns to all tables."""
    
    connection = op.get_bind()
    now = datetime.utcnow()
    
    # Add updated_at to users
    op.add_column('users', sa.Column('updated_at', sa.DateTime(), nullable=True))
    connection.execute(sa.text("UPDATE users SET updated_at = :now"), {"now": now})
    op.alter_column('users', 'updated_at', nullable=False)
    
    # Add updated_at to user_tags
    op.add_column('user_tags', sa.Column('updated_at', sa.DateTime(), nullable=True))
    connection.execute(sa.text("UPDATE user_tags SET updated_at = :now"), {"now": now})
    op.alter_column('user_tags', 'updated_at', nullable=False)
    
    # Add updated_at to expenses
    op.add_column('expenses', sa.Column('updated_at', sa.DateTime(), nullable=True))
    connection.execute(sa.text("UPDATE expenses SET updated_at = :now"), {"now": now})
    op.alter_column('expenses', 'updated_at', nullable=False)
    
    # Add updated_at to tags
    op.add_column('tags', sa.Column('updated_at', sa.DateTime(), nullable=True))
    connection.execute(sa.text("UPDATE tags SET updated_at = :now"), {"now": now})
    op.alter_column('tags', 'updated_at', nullable=False)
    
    # Add updated_at to expense_tags
    op.add_column('expense_tags', sa.Column('updated_at', sa.DateTime(), nullable=True))
    connection.execute(sa.text("UPDATE expense_tags SET updated_at = :now"), {"now": now})
    op.alter_column('expense_tags', 'updated_at', nullable=False)


def downgrade() -> None:
    """Remove updated_at columns."""
    op.drop_column('users', 'updated_at')
    op.drop_column('user_tags', 'updated_at')
    op.drop_column('expenses', 'updated_at')
    op.drop_column('tags', 'updated_at')
    op.drop_column('expense_tags', 'updated_at')
