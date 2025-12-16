"""migrate all tables to uuidv6

Revision ID: migrate_all_to_uuid
Revises: 
Create Date: 2025-12-16

"""
from alembic import op
import sqlalchemy as sa
import uuid6

# revision identifiers, used by Alembic.
revision = 'migrate_all_to_uuid'
down_revision = 'cd67a086746f'  # Previous migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace all integer IDs with UUIDv6."""
    
    connection = op.get_bind()
    
    # Step 1: Create mapping tables
    op.execute("""
        CREATE TEMPORARY TABLE user_id_mapping (
            old_id INTEGER,
            new_id VARCHAR(36)
        )
    """)
    
    op.execute("""
        CREATE TEMPORARY TABLE user_tag_id_mapping (
            old_id INTEGER,
            new_id VARCHAR(36)
        )
    """)
    
    op.execute("""
        CREATE TEMPORARY TABLE expense_id_mapping (
            old_id INTEGER,
            new_id VARCHAR(36)
        )
    """)
    
    op.execute("""
        CREATE TEMPORARY TABLE tag_id_mapping (
            old_id INTEGER,
            new_id VARCHAR(36)
        )
    """)
    
    op.execute("""
        CREATE TEMPORARY TABLE expense_tag_id_mapping (
            old_id INTEGER,
            new_id VARCHAR(36)
        )
    """)
    
    # Step 2: Generate UUIDs for all existing records
    
    # Users
    users = connection.execute(sa.text("SELECT id FROM users ORDER BY id")).fetchall()
    for user in users:
        new_uuid = str(uuid6.uuid6())
        connection.execute(
            sa.text("INSERT INTO user_id_mapping (old_id, new_id) VALUES (:old_id, :new_id)"),
            {"old_id": user[0], "new_id": new_uuid}
        )
    
    # UserTags
    user_tags = connection.execute(sa.text("SELECT id FROM user_tags ORDER BY id")).fetchall()
    for tag in user_tags:
        new_uuid = str(uuid6.uuid6())
        connection.execute(
            sa.text("INSERT INTO user_tag_id_mapping (old_id, new_id) VALUES (:old_id, :new_id)"),
            {"old_id": tag[0], "new_id": new_uuid}
        )
    
    # Expenses
    expenses = connection.execute(sa.text("SELECT id FROM expenses ORDER BY id")).fetchall()
    for expense in expenses:
        new_uuid = str(uuid6.uuid6())
        connection.execute(
            sa.text("INSERT INTO expense_id_mapping (old_id, new_id) VALUES (:old_id, :new_id)"),
            {"old_id": expense[0], "new_id": new_uuid}
        )
    
    # Tags
    tags = connection.execute(sa.text("SELECT id FROM tags ORDER BY id")).fetchall()
    for tag in tags:
        new_uuid = str(uuid6.uuid6())
        connection.execute(
            sa.text("INSERT INTO tag_id_mapping (old_id, new_id) VALUES (:old_id, :new_id)"),
            {"old_id": tag[0], "new_id": new_uuid}
        )
    
    # ExpenseTags
    expense_tags = connection.execute(sa.text("SELECT id FROM expense_tags ORDER BY id")).fetchall()
    for et in expense_tags:
        new_uuid = str(uuid6.uuid6())
        connection.execute(
            sa.text("INSERT INTO expense_tag_id_mapping (old_id, new_id) VALUES (:old_id, :new_id)"),
            {"old_id": et[0], "new_id": new_uuid}
        )
    
    # Step 3: Add new UUID columns to all tables
    
    # Users
    op.add_column('users', sa.Column('new_id', sa.String(36), nullable=True))
    op.execute("""
        UPDATE users 
        SET new_id = (SELECT new_id FROM user_id_mapping WHERE old_id = users.id)
    """)
    
    # UserTags
    op.add_column('user_tags', sa.Column('new_id', sa.String(36), nullable=True))
    op.add_column('user_tags', sa.Column('new_user_id', sa.String(36), nullable=True))
    op.execute("""
        UPDATE user_tags 
        SET new_id = (SELECT new_id FROM user_tag_id_mapping WHERE old_id = user_tags.id),
            new_user_id = (SELECT new_id FROM user_id_mapping WHERE old_id = user_tags.user_id)
    """)
    
    # Expenses
    op.add_column('expenses', sa.Column('new_id', sa.String(36), nullable=True))
    op.add_column('expenses', sa.Column('new_user_id', sa.String(36), nullable=True))
    op.execute("""
        UPDATE expenses 
        SET new_id = (SELECT new_id FROM expense_id_mapping WHERE old_id = expenses.id),
            new_user_id = (SELECT new_id FROM user_id_mapping WHERE old_id = expenses.user_id)
    """)
    
    # Tags
    op.add_column('tags', sa.Column('new_id', sa.String(36), nullable=True))
    op.add_column('tags', sa.Column('new_expense_id', sa.String(36), nullable=True))
    op.execute("""
        UPDATE tags 
        SET new_id = (SELECT new_id FROM tag_id_mapping WHERE old_id = tags.id),
            new_expense_id = (SELECT new_id FROM expense_id_mapping WHERE old_id = tags.expense_id)
    """)
    
    # ExpenseTags
    op.add_column('expense_tags', sa.Column('new_id', sa.String(36), nullable=True))
    op.add_column('expense_tags', sa.Column('new_expense_id', sa.String(36), nullable=True))
    op.add_column('expense_tags', sa.Column('new_user_tag_id', sa.String(36), nullable=True))
    op.execute("""
        UPDATE expense_tags 
        SET new_id = (SELECT new_id FROM expense_tag_id_mapping WHERE old_id = expense_tags.id),
            new_expense_id = (SELECT new_id FROM expense_id_mapping WHERE old_id = expense_tags.expense_id),
            new_user_tag_id = (SELECT new_id FROM user_tag_id_mapping WHERE old_id = expense_tags.user_tag_id)
    """)
    
    # Step 4: Drop old foreign key constraints (PostgreSQL only)
    try:
        op.drop_constraint('expenses_user_id_fkey', 'expenses', type_='foreignkey')
        op.drop_constraint('user_tags_user_id_fkey', 'user_tags', type_='foreignkey')
        op.drop_constraint('tags_expense_id_fkey', 'tags', type_='foreignkey')
        op.drop_constraint('expense_tags_expense_id_fkey', 'expense_tags', type_='foreignkey')
        op.drop_constraint('expense_tags_user_tag_id_fkey', 'expense_tags', type_='foreignkey')
    except:
        pass  # SQLite doesn't support dropping constraints
    
    # Step 5: Drop old columns and primary keys
    
    # Drop primary keys first
    try:
        op.drop_constraint('users_pkey', 'users', type_='primary')
        op.drop_constraint('user_tags_pkey', 'user_tags', type_='primary')
        op.drop_constraint('expenses_pkey', 'expenses', type_='primary')
        op.drop_constraint('tags_pkey', 'tags', type_='primary')
        op.drop_constraint('expense_tags_pkey', 'expense_tags', type_='primary')
    except:
        pass
    
    # Drop old columns
    op.drop_column('users', 'id')
    op.drop_column('user_tags', 'id')
    op.drop_column('user_tags', 'user_id')
    op.drop_column('expenses', 'id')
    op.drop_column('expenses', 'user_id')
    op.drop_column('tags', 'id')
    op.drop_column('tags', 'expense_id')
    op.drop_column('expense_tags', 'id')
    op.drop_column('expense_tags', 'expense_id')
    op.drop_column('expense_tags', 'user_tag_id')
    
    # Step 6: Rename new columns to final names
    op.alter_column('users', 'new_id', new_column_name='id')
    op.alter_column('user_tags', 'new_id', new_column_name='id')
    op.alter_column('user_tags', 'new_user_id', new_column_name='user_id')
    op.alter_column('expenses', 'new_id', new_column_name='id')
    op.alter_column('expenses', 'new_user_id', new_column_name='user_id')
    op.alter_column('tags', 'new_id', new_column_name='id')
    op.alter_column('tags', 'new_expense_id', new_column_name='expense_id')
    op.alter_column('expense_tags', 'new_id', new_column_name='id')
    op.alter_column('expense_tags', 'new_expense_id', new_column_name='expense_id')
    op.alter_column('expense_tags', 'new_user_tag_id', new_column_name='user_tag_id')
    
    # Step 7: Make columns NOT NULL
    op.alter_column('users', 'id', nullable=False)
    op.alter_column('user_tags', 'id', nullable=False)
    op.alter_column('user_tags', 'user_id', nullable=False)
    op.alter_column('expenses', 'id', nullable=False)
    op.alter_column('expenses', 'user_id', nullable=False)
    op.alter_column('tags', 'id', nullable=False)
    op.alter_column('tags', 'expense_id', nullable=False)
    op.alter_column('expense_tags', 'id', nullable=False)
    op.alter_column('expense_tags', 'expense_id', nullable=False)
    op.alter_column('expense_tags', 'user_tag_id', nullable=False)
    
    # Step 8: Create new primary keys
    op.create_primary_key('users_pkey', 'users', ['id'])
    op.create_primary_key('user_tags_pkey', 'user_tags', ['id'])
    op.create_primary_key('expenses_pkey', 'expenses', ['id'])
    op.create_primary_key('tags_pkey', 'tags', ['id'])
    op.create_primary_key('expense_tags_pkey', 'expense_tags', ['id'])
    
    # Step 9: Create indexes
    op.create_index('ix_users_id', 'users', ['id'], unique=True)
    op.create_index('ix_user_tags_id', 'user_tags', ['id'], unique=True)
    op.create_index('ix_expenses_id', 'expenses', ['id'], unique=True)
    op.create_index('ix_tags_id', 'tags', ['id'], unique=True)
    op.create_index('ix_expense_tags_id', 'expense_tags', ['id'], unique=True)
    
    # Step 10: Create new foreign key constraints
    op.create_foreign_key('expenses_user_id_fkey', 'expenses', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('user_tags_user_id_fkey', 'user_tags', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('tags_expense_id_fkey', 'tags', 'expenses', ['expense_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('expense_tags_expense_id_fkey', 'expense_tags', 'expenses', ['expense_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('expense_tags_user_tag_id_fkey', 'expense_tags', 'user_tags', ['user_tag_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Revert to integer IDs - not recommended, backup before upgrading."""
    pass
