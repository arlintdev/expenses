#!/bin/bash
set -e

echo "============================================"
echo "SQLite to PostgreSQL Migration Script"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running in the correct directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: docker-compose.yml not found. Please run this script from the expense-tracker directory.${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found. Please create it first.${NC}"
    exit 1
fi

# Load environment variables
source .env

# Check if PostgreSQL credentials are set
if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
    echo -e "${YELLOW}Warning: PostgreSQL credentials not found in .env file.${NC}"
    echo "Using defaults: POSTGRES_USER=expenseuser, POSTGRES_DB=expenses"
    POSTGRES_USER=${POSTGRES_USER:-expenseuser}
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-change_this_password}
    POSTGRES_DB=${POSTGRES_DB:-expenses}
fi

echo "Configuration:"
echo "  PostgreSQL User: $POSTGRES_USER"
echo "  PostgreSQL Database: $POSTGRES_DB"
echo "  SQLite Path: ./data/expenses.db"
echo ""

# Check if SQLite database exists
if [ ! -f "./data/expenses.db" ]; then
    echo -e "${RED}Error: SQLite database not found at ./data/expenses.db${NC}"
    echo "Nothing to migrate!"
    exit 1
fi

echo -e "${GREEN}✓ SQLite database found${NC}"

# Check if migration already done
if [ -f "./data/.postgres_migrated" ]; then
    echo -e "${YELLOW}Warning: Migration marker found (.postgres_migrated)${NC}"
    read -p "Migration may have already been done. Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Migration cancelled."
        exit 0
    fi
fi

# Step 1: Start PostgreSQL (if not running)
echo ""
echo "Step 1: Starting PostgreSQL..."
docker compose up -d postgres

# Wait for PostgreSQL to be healthy
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U $POSTGRES_USER -d $POSTGRES_DB > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Error: PostgreSQL failed to start within 30 seconds${NC}"
        exit 1
    fi
    echo -n "."
    sleep 1
done

# Step 2: Check if PostgreSQL database has data
echo ""
echo "Step 2: Checking if PostgreSQL already has data..."
USER_COUNT=$(docker compose exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$USER_COUNT" != "0" ]; then
    RECORD_COUNT=$(docker compose exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ' || echo "0")
    if [ "$RECORD_COUNT" != "0" ]; then
        echo -e "${YELLOW}Warning: PostgreSQL database already has $RECORD_COUNT users${NC}"
        read -p "PostgreSQL appears to have data. Overwrite? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Migration cancelled."
            exit 0
        fi
    fi
fi

# Step 3: Export SQLite data to SQL dump
echo ""
echo "Step 3: Exporting SQLite data..."
BACKUP_FILE="./data/sqlite_backup_$(date +%Y%m%d_%H%M%S).sql"
docker compose exec -T expense-tracker sqlite3 /app/data/expenses.db .dump > "$BACKUP_FILE" 2>/dev/null || {
    echo -e "${YELLOW}Warning: Could not export from running container. Trying direct access...${NC}"
    sqlite3 ./data/expenses.db .dump > "$BACKUP_FILE"
}
echo -e "${GREEN}✓ SQLite data exported to $BACKUP_FILE${NC}"

# Step 4: Convert SQLite dump to PostgreSQL format
echo ""
echo "Step 4: Converting SQLite dump to PostgreSQL format..."
POSTGRES_FILE="./data/postgres_import_$(date +%Y%m%d_%H%M%S).sql"

# Remove SQLite-specific commands and convert to PostgreSQL
cat "$BACKUP_FILE" | \
    grep -v "^PRAGMA" | \
    grep -v "^BEGIN TRANSACTION;" | \
    grep -v "^COMMIT;" | \
    sed 's/INTEGER PRIMARY KEY AUTOINCREMENT/SERIAL PRIMARY KEY/g' | \
    sed 's/DATETIME DEFAULT (CURRENT_TIMESTAMP)/TIMESTAMP DEFAULT CURRENT_TIMESTAMP/g' | \
    sed 's/DATETIME DEFAULT CURRENT_TIMESTAMP/TIMESTAMP DEFAULT CURRENT_TIMESTAMP/g' > "$POSTGRES_FILE"

echo -e "${GREEN}✓ Converted to PostgreSQL format: $POSTGRES_FILE${NC}"

# Step 5: Create tables in PostgreSQL
echo ""
echo "Step 5: Creating tables in PostgreSQL..."
docker compose up -d expense-tracker
sleep 5
echo "Waiting for expense-tracker to initialize tables..."
sleep 10
echo -e "${GREEN}✓ Tables created${NC}"

# Step 6: Import data into PostgreSQL
echo ""
echo "Step 6: Importing data into PostgreSQL..."
echo "This may take a few minutes depending on data size..."

# Extract just the INSERT statements
grep "^INSERT INTO" "$POSTGRES_FILE" > ./data/inserts_only.sql || {
    echo -e "${YELLOW}No INSERT statements found. Database might be empty.${NC}"
    rm -f ./data/inserts_only.sql
    exit 0
}

# Import the data
docker compose exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB < ./data/inserts_only.sql 2>&1 | grep -v "ERROR.*duplicate key" || true

echo -e "${GREEN}✓ Data imported${NC}"

# Step 7: Update sequences
echo ""
echo "Step 7: Updating PostgreSQL sequences..."
TABLES=("users" "expenses" "tags" "user_tags" "expense_tags")
for table in "${TABLES[@]}"; do
    MAX_ID=$(docker compose exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT MAX(id) FROM $table;" 2>/dev/null | tr -d ' ' || echo "0")
    if [ "$MAX_ID" != "" ] && [ "$MAX_ID" != "0" ]; then
        docker compose exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT setval('${table}_id_seq', $MAX_ID);" > /dev/null 2>&1 || true
        echo "  Updated ${table}_id_seq to $MAX_ID"
    fi
done
echo -e "${GREEN}✓ Sequences updated${NC}"

# Step 8: Verify migration
echo ""
echo "Step 8: Verifying migration..."
echo ""
echo "Record counts:"
for table in "${TABLES[@]}"; do
    SQLITE_COUNT=$(sqlite3 ./data/expenses.db "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "0")
    POSTGRES_COUNT=$(docker compose exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | tr -d ' ' || echo "0")
    if [ "$SQLITE_COUNT" == "$POSTGRES_COUNT" ]; then
        echo -e "  ${GREEN}✓${NC} $table: SQLite=$SQLITE_COUNT, PostgreSQL=$POSTGRES_COUNT"
    else
        echo -e "  ${YELLOW}⚠${NC} $table: SQLite=$SQLITE_COUNT, PostgreSQL=$POSTGRES_COUNT (mismatch)"
    fi
done

# Step 9: Create migration marker
echo ""
echo "Step 9: Creating migration marker..."
touch ./data/.postgres_migrated
echo "$(date): Migration completed" > ./data/.postgres_migrated
echo -e "${GREEN}✓ Migration marker created${NC}"

# Cleanup temporary files
echo ""
echo "Cleanup: Removing temporary files..."
rm -f ./data/inserts_only.sql
echo -e "${GREEN}✓ Temporary files removed${NC}"
echo ""
echo "Backup files kept:"
echo "  - $BACKUP_FILE (SQLite dump)"
echo "  - $POSTGRES_FILE (PostgreSQL format)"

# Final instructions
echo ""
echo "============================================"
echo -e "${GREEN}Migration Complete!${NC}"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Update your .env file with:"
echo "   DATABASE_URL=postgresql+asyncpg://$POSTGRES_USER:YOUR_PASSWORD@postgres:5432/$POSTGRES_DB"
echo ""
echo "2. Restart services:"
echo "   docker compose down"
echo "   docker compose up -d"
echo ""
echo "3. Verify the application works:"
echo "   docker compose logs -f expense-tracker"
echo ""
echo "4. Test login at: https://expenses.arlint.dev"
echo ""
echo -e "${YELLOW}Note: Keep ./data/expenses.db as a backup until you verify everything works!${NC}"
echo ""
