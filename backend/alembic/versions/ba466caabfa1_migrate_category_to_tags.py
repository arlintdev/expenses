"""migrate_category_to_tags

Revision ID: ba466caabfa1
Revises: ee0421ab0679
Create Date: 2025-12-14 00:43:54.377569

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = 'ba466caabfa1'
down_revision: Union[str, Sequence[str], None] = 'ee0421ab0679'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade: Create tags table and migrate data from category column."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
    )

    # Create indexes for performance
    op.create_index('idx_tags_expense_id', 'tags', ['expense_id'])
    op.create_index('idx_tags_name', 'tags', ['name'])

    # 2. Migrate existing categories to tags
    # Define temporary table representations for data migration
    expenses_table = table('expenses',
        column('id', sa.Integer),
        column('category', sa.String)
    )
    tags_table = table('tags',
        column('name', sa.String),
        column('expense_id', sa.Integer),
        column('created_at', sa.DateTime)
    )

    # Fetch all expenses with non-null categories
    expenses_with_category = conn.execute(
        sa.select(expenses_table.c.id, expenses_table.c.category)
        .where(expenses_table.c.category.isnot(None))
        .where(expenses_table.c.category != '')
    ).fetchall()

    # Insert tags for each expense
    if expenses_with_category:
        tag_data = [
            {
                'name': expense.category.strip(),
                'expense_id': expense.id,
                'created_at': datetime.utcnow()
            }
            for expense in expenses_with_category
            if expense.category and expense.category.strip()
        ]

        if tag_data:
            conn.execute(tags_table.insert(), tag_data)

    # 3. Drop category column from expenses
    op.drop_column('expenses', 'category')

    # 4. Drop unused categories table if it exists
    if 'categories' in inspector.get_table_names():
        op.drop_table('categories')


def downgrade() -> None:
    """Downgrade: Restore category column and categories table."""
    conn = op.get_bind()

    # 1. Recreate category column in expenses
    op.add_column('expenses', sa.Column('category', sa.String(), nullable=True))

    # 2. Migrate first tag back to category column (loses multi-tag data)
    # Define temporary table representations
    tags_table = table('tags',
        column('id', sa.Integer),
        column('name', sa.String),
        column('expense_id', sa.Integer)
    )
    expenses_table = table('expenses',
        column('id', sa.Integer),
        column('category', sa.String)
    )

    # Get first tag for each expense
    tags_by_expense = conn.execute(
        sa.select(tags_table.c.expense_id, sa.func.min(tags_table.c.name).label('category'))
        .group_by(tags_table.c.expense_id)
    ).fetchall()

    # Update expenses with first tag
    for tag in tags_by_expense:
        conn.execute(
            expenses_table.update()
            .where(expenses_table.c.id == tag.expense_id)
            .values(category=tag.category)
        )

    # 3. Recreate categories table
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
    )

    # 4. Drop tags table
    op.drop_index('idx_tags_name', 'tags')
    op.drop_index('idx_tags_expense_id', 'tags')
    op.drop_table('tags')
