"""
Automatic SQLite to PostgreSQL migration script.
Runs once on first PostgreSQL startup if SQLite data exists.
"""
import os
import asyncio
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import structlog

logger = structlog.get_logger(__name__)

async def migrate_sqlite_to_postgres(sqlite_path: str, postgres_url: str) -> bool:
    """
    Migrate data from SQLite to PostgreSQL.

    Args:
        sqlite_path: Path to SQLite database file
        postgres_url: PostgreSQL connection URL

    Returns:
        bool: True if migration successful, False if skipped or failed
    """
    # Check if SQLite database exists
    if not os.path.exists(sqlite_path):
        logger.info("sqlite_not_found", path=sqlite_path)
        return False

    logger.info("migration_started", source="sqlite", target="postgresql")

    try:
        # Create engines
        sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
        postgres_sync_url = postgres_url.replace("+asyncpg", "")
        postgres_engine = create_engine(postgres_sync_url)

        # Check if PostgreSQL tables already have data
        inspector = inspect(postgres_engine)
        tables = inspector.get_table_names()

        if tables:
            # Check if any table has data
            with postgres_engine.connect() as conn:
                for table in tables:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    if count > 0:
                        logger.info("postgres_has_data", message="PostgreSQL already has data, skipping migration")
                        return False

        # Get list of tables from SQLite
        sqlite_inspector = inspect(sqlite_engine)
        sqlite_tables = sqlite_inspector.get_table_names()

        if not sqlite_tables:
            logger.info("sqlite_empty", message="SQLite database is empty, nothing to migrate")
            return False

        logger.info("migration_tables_found", count=len(sqlite_tables), tables=sqlite_tables)

        # Migrate each table
        migrated_rows = {}
        with sqlite_engine.connect() as sqlite_conn:
            with postgres_engine.connect() as postgres_conn:
                for table in sqlite_tables:
                    try:
                        # Read all data from SQLite table
                        result = sqlite_conn.execute(text(f"SELECT * FROM {table}"))
                        rows = result.fetchall()

                        if not rows:
                            logger.debug("table_empty", table=table)
                            migrated_rows[table] = 0
                            continue

                        # Get column names
                        columns = result.keys()

                        # Build insert statement
                        placeholders = ", ".join([f":{col}" for col in columns])
                        insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

                        # Insert data into PostgreSQL
                        row_count = 0
                        for row in rows:
                            row_dict = dict(zip(columns, row))
                            postgres_conn.execute(text(insert_sql), row_dict)
                            row_count += 1

                        migrated_rows[table] = row_count
                        logger.info("table_migrated", table=table, rows=row_count)

                    except Exception as e:
                        logger.error("table_migration_failed", table=table, error=str(e))
                        raise

                # Commit all changes
                postgres_conn.commit()

        # Update sequences for tables with auto-increment IDs
        with postgres_engine.connect() as postgres_conn:
            for table in sqlite_tables:
                try:
                    # Get max ID from table
                    result = postgres_conn.execute(text(f"SELECT MAX(id) FROM {table}"))
                    max_id = result.scalar()

                    if max_id:
                        # Update sequence
                        sequence_name = f"{table}_id_seq"
                        postgres_conn.execute(text(f"SELECT setval('{sequence_name}', {max_id})"))
                        logger.debug("sequence_updated", table=table, sequence=sequence_name, value=max_id)
                except Exception as e:
                    # Not all tables have sequences, ignore errors
                    logger.debug("sequence_update_skipped", table=table, reason=str(e))

            postgres_conn.commit()

        logger.info("migration_completed", migrated_rows=migrated_rows, total_rows=sum(migrated_rows.values()))

        # Create migration marker file
        migration_marker = Path(sqlite_path).parent / ".postgres_migrated"
        migration_marker.write_text("Migration completed successfully")
        logger.info("migration_marker_created", path=str(migration_marker))

        return True

    except Exception as e:
        logger.error("migration_failed", error=str(e), error_type=type(e).__name__)
        return False
    finally:
        sqlite_engine.dispose()
        postgres_engine.dispose()


async def check_and_migrate():
    """
    Check if migration is needed and perform it.
    Called during app startup if using PostgreSQL.
    """
    from dotenv import load_dotenv

    # Load environment variables
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path)

    database_url = os.getenv("DATABASE_URL", "")

    # Only run if using PostgreSQL
    if "postgresql" not in database_url:
        return False

    # Check for SQLite database to migrate
    sqlite_paths = [
        "/app/data/expenses.db",  # Docker path
        "./data/expenses.db",  # Relative path
        "./expenses.db",  # Current directory
    ]

    sqlite_path = None
    for path in sqlite_paths:
        if os.path.exists(path):
            sqlite_path = path
            break

    if not sqlite_path:
        logger.info("no_sqlite_found", message="No SQLite database found to migrate")
        return False

    # Check if migration already done
    migration_marker = Path(sqlite_path).parent / ".postgres_migrated"
    if migration_marker.exists():
        logger.info("migration_already_done", marker=str(migration_marker))
        return False

    # Perform migration
    logger.info("starting_automatic_migration", sqlite_path=sqlite_path)
    success = await migrate_sqlite_to_postgres(sqlite_path, database_url)

    if success:
        logger.info("automatic_migration_success")
    else:
        logger.info("automatic_migration_skipped")

    return success


if __name__ == "__main__":
    # Can be run standalone for testing
    asyncio.run(check_and_migrate())
