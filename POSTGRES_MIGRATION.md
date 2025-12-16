# PostgreSQL Migration Guide

This guide explains how to migrate from SQLite to PostgreSQL for production deployment.

## Why PostgreSQL?

**Benefits over SQLite:**
- ✅ **True concurrent connections** - No database locking issues
- ✅ **Connection pooling** - Up to 30 concurrent connections (20 pool + 10 overflow)
- ✅ **Better performance** - Optimized for multi-user workloads
- ✅ **ACID compliance** - Full transaction support
- ✅ **Production-ready** - Designed for server environments

**When to use:**
- Production deployments
- Multiple concurrent users
- High-traffic scenarios

**When SQLite is fine:**
- Local development
- Single-user scenarios
- Testing

---

## Production Deployment (Raspberry Pi)

### Step 1: Update Production .env File

SSH to your Raspberry Pi:
```bash
ssh ubuntu@192.168.68.63
cd ~/expenses
nano .env
```

Add/update these lines:
```bash
# PostgreSQL Configuration
POSTGRES_USER=expenseuser
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE
POSTGRES_DB=expenses

# Database URL (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://expenseuser:YOUR_SECURE_PASSWORD_HERE@postgres:5432/expenses

# CORS and Environment
CORS_ORIGINS=https://expenses.arlint.dev,http://192.168.68.63:3000,http://localhost:3000
ENVIRONMENT=production

# Existing secrets
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
JWT_SECRET_KEY=your_jwt_secret
ANTHROPIC_API_KEY=your_anthropic_key
```

**IMPORTANT:** Replace `YOUR_SECURE_PASSWORD_HERE` with a strong password!

Generate a secure password:
```bash
openssl rand -base64 32
```

### Step 2: Deploy PostgreSQL Stack

Pull and start the new stack:
```bash
docker compose pull
docker compose down
docker compose up -d
```

Watch the logs:
```bash
docker compose logs -f
```

Look for:
```
✅ PostgreSQL async engine initialized with connection pooling
[info] database_initialized db_type=postgresql version=PostgreSQL 16.x
```

### Step 3: Verify Services

Check both containers are running:
```bash
docker compose ps
```

Should show:
```
expense-tracker-db    running    Healthy
expense-tracker       running    Healthy
```

Test the health endpoint:
```bash
curl https://expenses.arlint.dev/api/health
```

### Step 4: Migrate Existing Data (Optional)

If you have existing SQLite data to migrate:

**Export from SQLite:**
```bash
# On Raspberry Pi, backup SQLite data
docker exec expense-tracker sqlite3 /app/data/expenses.db .dump > expenses_backup.sql
```

**Import to PostgreSQL:**
```bash
# Convert SQLite dump to PostgreSQL format (may need manual adjustments)
# Then import:
cat expenses_backup.sql | docker exec -i expense-tracker-db psql -U expenseuser -d expenses
```

**Note:** SQLite → PostgreSQL migration may require manual adjustments due to syntax differences. For production, it's often easier to start fresh if you don't have critical data.

---

## Local Development (Keep SQLite)

For local development, SQLite is perfectly fine and simpler:

**backend/.env:**
```bash
DATABASE_URL=sqlite:///./expenses.db
ENVIRONMENT=development
```

**Run locally:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The code automatically detects SQLite vs PostgreSQL and configures appropriately!

---

## Rollback to SQLite (If Needed)

If you need to rollback to SQLite:

**Update .env:**
```bash
DATABASE_URL=sqlite:///./data/expenses.db
```

**Update docker-compose.yml environment:**
```yaml
environment:
  - DATABASE_URL=sqlite:///./data/expenses.db
```

**Restart:**
```bash
docker compose down
docker compose up -d
```

---

## Database Comparison

| Feature | SQLite (Before) | PostgreSQL (Now) |
|---------|----------------|------------------|
| Concurrent Writes | ❌ Single writer | ✅ Multiple writers |
| Connection Pool | ❌ Not supported | ✅ 20 connections + 10 overflow |
| Auth Locking | ❌ 120s waits | ✅ No blocking |
| Production Ready | ⚠️ Limited | ✅ Full featured |
| Setup Complexity | ✅ Simple | ⚠️ More complex |
| Data Persistence | ✅ File-based | ✅ Volume-based |

---

## Troubleshooting

### Can't connect to PostgreSQL

**Check PostgreSQL is running:**
```bash
docker compose ps postgres
```

**Check logs:**
```bash
docker compose logs postgres
```

**Test connection:**
```bash
docker exec -it expense-tracker-db psql -U expenseuser -d expenses
```

### Database connection errors

**Verify DATABASE_URL:**
```bash
docker exec expense-tracker env | grep DATABASE_URL
```

Should show:
```
DATABASE_URL=postgresql+asyncpg://expenseuser:password@postgres:5432/expenses
```

### Migrations failing

**Run migrations manually:**
```bash
docker exec expense-tracker alembic upgrade head
```

### PostgreSQL password issues

**Reset PostgreSQL password:**
```bash
docker compose down
docker volume rm expenses_postgres_data
# Update .env with new password
docker compose up -d
```

---

## Performance Tuning

### PostgreSQL Configuration

For production, you may want to tune PostgreSQL settings. Create `postgres.conf` and mount it:

**docker-compose.yml:**
```yaml
postgres:
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./postgres.conf:/etc/postgresql/postgresql.conf
  command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

**Recommended settings for Raspberry Pi:**
```ini
# postgres.conf
max_connections = 50
shared_buffers = 128MB
effective_cache_size = 512MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 4MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2621kB
min_wal_size = 1GB
max_wal_size = 4GB
```

### Application Connection Pool

Already configured in `backend/models.py`:
- `pool_size=20` - 20 persistent connections
- `max_overflow=10` - Up to 10 additional temporary connections
- `pool_timeout=30` - Wait up to 30s for available connection
- `pool_recycle=3600` - Refresh connections every hour

---

## Monitoring

### Check connection pool usage

```bash
docker exec expense-tracker-db psql -U expenseuser -d expenses -c "SELECT count(*) FROM pg_stat_activity;"
```

### Check database size

```bash
docker exec expense-tracker-db psql -U expenseuser -d expenses -c "SELECT pg_size_pretty(pg_database_size('expenses'));"
```

### Check slow queries

```bash
docker exec expense-tracker-db psql -U expenseuser -d expenses -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

---

## Backup Strategy

### Automated Daily Backups

Create a backup script:

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/home/ubuntu/expenses/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker exec expense-tracker-db pg_dump -U expenseuser expenses | gzip > $BACKUP_DIR/expenses_$TIMESTAMP.sql.gz

# Keep only last 7 days of backups
find $BACKUP_DIR -name "expenses_*.sql.gz" -mtime +7 -delete
```

**Add to crontab:**
```bash
crontab -e
# Add this line (daily backup at 2 AM):
0 2 * * * /home/ubuntu/expenses/backup.sh
```

### Manual Backup

```bash
docker exec expense-tracker-db pg_dump -U expenseuser expenses > expenses_backup_$(date +%Y%m%d).sql
```

### Restore from Backup

```bash
cat expenses_backup.sql | docker exec -i expense-tracker-db psql -U expenseuser -d expenses
```

---

## Security Checklist

- [ ] Change default PostgreSQL password
- [ ] Use strong password (32+ characters)
- [ ] Keep PostgreSQL port (5432) unexposed (only internal network)
- [ ] Regular backups configured
- [ ] Monitor connection logs for unusual activity
- [ ] Keep PostgreSQL updated (use `postgres:16-alpine` in docker-compose)
- [ ] Restrict PostgreSQL user permissions (done by default)

---

## Support

If you encounter issues:

1. Check logs: `docker compose logs -f`
2. Verify environment variables: `docker exec expense-tracker env`
3. Test database connection: `docker exec expense-tracker-db psql -U expenseuser -d expenses`
4. Check GitHub issues or create a new one

---

## Summary

**Automatic Migration Path:**
1. Update production `.env` with PostgreSQL credentials
2. Run `docker compose up -d`
3. Code automatically detects PostgreSQL and configures appropriately
4. No database locking issues!
5. 30 concurrent connections supported

**The code works with both SQLite (dev) and PostgreSQL (prod) automatically!**
