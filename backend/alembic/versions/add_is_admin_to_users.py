"""add is_admin to users

Revision ID: add_is_admin
Revises: add_updated_at
Create Date: 2025-12-16

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_is_admin'
down_revision = 'add_updated_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_admin column to users table."""
    # Add is_admin column, defaulting to False for existing users
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'))
    
    # Create index for performance
    op.create_index('ix_users_is_admin', 'users', ['is_admin'])


def downgrade() -> None:
    """Remove is_admin column from users table."""
    op.drop_index('ix_users_is_admin', table_name='users')
    op.drop_column('users', 'is_admin')
