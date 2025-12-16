"""replace integer id with uuidv6

Revision ID: replace_id_with_uuid
Revises: 
Create Date: 2025-12-16

"""
from alembic import op
import sqlalchemy as sa
import uuid6

# revision identifiers, used by Alembic.
revision = 'replace_id_with_uuid'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace integer ID with UUIDv6 as primary key."""
    
    # Create a mapping table for old ID to new UUID
    op.execute("""
        CREATE TEMPORARY TABLE expense_id_mapping (
            old_id INTEGER,
            new_id VARCHAR(36)
        )
    """)
    
    # Generate UUIDs for existing expenses and store mapping
    connection = op.get_bind()
    expenses = connection.execute(sa.text("SELECT id FROM expenses ORDER BY id")).fetchall()
    for expense in expenses:
        new_uuid = str(uuid6.uuid6())
        connection.execute(
            sa.text("INSERT INTO expense_id_mapping (old_id, new_id) VALUES (:old_id, :new_id)"),
            {"old_id": expense[0], "new_id": new_uuid}
        )
    
    # Add new uuid column to expenses
    op.add_column('expenses', sa.Column('new_id', sa.String(36), nullable=True))
    
    # Populate uuid column from mapping
    op.execute("""
        UPDATE expenses 
        SET new_id = (SELECT new_id FROM expense_id_mapping WHERE old_id = expenses.id)
    """)
    
    # Add new uuid column to tags (foreign key reference)
    op.add_column('tags', sa.Column('new_expense_id', sa.String(36), nullable=True))
    
    # Update tags foreign key references using mapping
    op.execute("""
        UPDATE tags
        SET new_expense_id = (SELECT new_id FROM expense_id_mapping WHERE old_id = tags.expense_id)
    """)
    
    # Add new uuid column to expense_tags (foreign key reference)
    op.add_column('expense_tags', sa.Column('new_expense_id', sa.String(36), nullable=True))
    
    # Update expense_tags foreign key references using mapping
    op.execute("""
        UPDATE expense_tags
        SET new_expense_id = (SELECT new_id FROM expense_id_mapping WHERE old_id = expense_tags.expense_id)
    """)
    
    # Drop old foreign key constraints
    # Note: SQLite doesn't support dropping constraints, PostgreSQL does
    try:
        op.drop_constraint('tags_expense_id_fkey', 'tags', type_='foreignkey')
        op.drop_constraint('expense_tags_expense_id_fkey', 'expense_tags', type_='foreignkey')
    except:
        pass  # SQLite doesn't have named constraints
    
    # Drop old columns
    op.drop_column('tags', 'expense_id')
    op.drop_column('expense_tags', 'expense_id')
    
    # Drop old primary key and rename new columns
    op.drop_constraint('expenses_pkey', 'expenses', type_='primary')
    op.drop_column('expenses', 'id')
    
    # Rename new columns to final names
    op.alter_column('expenses', 'new_id', new_column_name='id')
    op.alter_column('tags', 'new_expense_id', new_column_name='expense_id')
    op.alter_column('expense_tags', 'new_expense_id', new_column_name='expense_id')
    
    # Make columns NOT NULL
    op.alter_column('expenses', 'id', nullable=False)
    op.alter_column('tags', 'expense_id', nullable=False)
    op.alter_column('expense_tags', 'expense_id', nullable=False)
    
    # Create new primary key and indexes
    op.create_primary_key('expenses_pkey', 'expenses', ['id'])
    op.create_index('ix_expenses_id', 'expenses', ['id'], unique=True)
    
    # Create new foreign key constraints
    op.create_foreign_key('tags_expense_id_fkey', 'tags', 'expenses', ['expense_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('expense_tags_expense_id_fkey', 'expense_tags', 'expenses', ['expense_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Revert to integer IDs."""
    # This is complex and not recommended - better to backup before upgrading
    pass
