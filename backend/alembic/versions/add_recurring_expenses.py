"""add_recurring_expenses

Revision ID: add_recurring_expenses
Revises: migrate_all_to_uuid
Create Date: 2025-12-16 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_recurring_expenses'
down_revision: Union[str, Sequence[str], None] = 'add_is_admin'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add columns to expenses table
    op.add_column('expenses', sa.Column('recurring', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('expenses', sa.Column('recurring_expense_id', sa.String(36), nullable=True))

    op.create_table('recurring_expenses',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('recipient', sa.String(), nullable=False),
        sa.Column('materials', sa.String(), nullable=True),
        sa.Column('hours', sa.Float(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('start_month', sa.Integer(), nullable=False),
        sa.Column('start_year', sa.Integer(), nullable=False),
        sa.Column('end_month', sa.Integer(), nullable=False),
        sa.Column('end_year', sa.Integer(), nullable=False),
        sa.Column('day_of_month', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recurring_expenses_id'), 'recurring_expenses', ['id'], unique=False)

    op.create_table('recurring_expense_tags',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('recurring_expense_id', sa.String(36), nullable=False),
        sa.Column('user_tag_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['recurring_expense_id'], ['recurring_expenses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_tag_id'], ['user_tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recurring_expense_tags_id'), 'recurring_expense_tags', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_recurring_expense_tags_id'), table_name='recurring_expense_tags')
    op.drop_table('recurring_expense_tags')
    op.drop_index(op.f('ix_recurring_expenses_id'), table_name='recurring_expenses')
    op.drop_table('recurring_expenses')
    op.drop_column('expenses', 'recurring_expense_id')
    op.drop_column('expenses', 'recurring')
