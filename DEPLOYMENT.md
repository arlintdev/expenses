# Raspberry Pi Deployment Guide

This guide walks you through deploying the Expense Tracker application on a Raspberry Pi using Docker Compose.

## Prerequisites

1. **Raspberry Pi** with Docker and Docker Compose installed
2. **SSH access** to your Raspberry Pi
3. **Internet connection** on the Pi to pull Docker images

## Quick Start

### 1. SSH into your Raspberry Pi

```bash
ssh ubuntu@192.168.68.63
```

Password: `ubuntu`

### 2. Create deployment directory

```bash
mkdir -p ~/expenses
cd ~/expenses
```

### 3. Download deployment files from GitHub

```bash
# Download docker-compose.yml
curl -O https://raw.githubusercontent.com/arlintdev/expenses/main/docker-compose.yml

# Download deployment script
curl -O https://raw.githubusercontent.com/arlintdev/expenses/main/deploy.sh
chmod +x deploy.sh

# Create .env file with your credentials
nano .env
```

### 4. Configure environment variables

Create a `.env` file with your credentials (create it with `nano .env`):

```bash
# Anthropic API Key
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database (SQLite file will be persisted in ./data directory)
DATABASE_URL=sqlite:///./data/expenses.db

# CORS Origins (update with your Pi's IP address)
CORS_ORIGINS=http://192.168.68.63:3000,http://localhost:3000,http://192.168.68.63

# Google OAuth Credentials
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# JWT Secret Key (generate a secure random string)
JWT_SECRET_KEY=your_secure_jwt_secret_key_here
```

**Note:** Replace the placeholder values with your actual credentials.

**Important:** Update the Google OAuth redirect URIs in your Google Cloud Console:
- Add: `http://192.168.68.63:3000`
- Add: `http://192.168.68.63`

### 5. Deploy the application

```bash
./deploy.sh
```

The application will be available at: **http://192.168.68.63:3000**

## Manual Deployment Steps

If you prefer manual control:

```bash
# Create data directory
mkdir -p data

# Pull the latest image (ARM64 version will be automatically selected)
docker compose pull

# Start the container
docker compose up -d

# View logs
docker compose logs -f
```

## Container Management

### View running containers
```bash
docker compose ps
```

### View logs
```bash
docker compose logs -f
```

### Stop the application
```bash
docker compose down
```

### Restart the application
```bash
docker compose restart
```

### Update to latest version
```bash
docker compose pull
docker compose up -d
```

## Port Configuration

The application runs on **port 3000** on your Raspberry Pi:
- Container internal port: 8000
- Exposed Pi port: 3000
- URL: http://192.168.68.63:3000

## Database Persistence

The SQLite database is stored in `~/expenses/data/expenses.db` on your Pi, outside the container. This ensures your data persists across container restarts and updates.

### Backup the database
```bash
cp ~/expenses/data/expenses.db ~/expenses/data/expenses.db.backup-$(date +%Y%m%d)
```

### Restore from backup
```bash
cp ~/expenses/data/expenses.db.backup-YYYYMMDD ~/expenses/data/expenses.db
docker compose restart
```

## Troubleshooting

### Check if Docker is running
```bash
sudo systemctl status docker
```

### Check container logs for errors
```bash
docker compose logs
```

### Check if port 3000 is available
```bash
sudo lsof -i :3000
```

### Restart Docker service
```bash
sudo systemctl restart docker
```

### Check container resource usage
```bash
docker stats
```

## Updating the Application

When a new version is pushed to GitHub:

```bash
cd ~/expenses
docker compose pull
docker compose up -d
```

Docker will automatically pull the ARM64 version of the image built by GitHub Actions.

## Architecture

- **Image**: Built via GitHub Actions with multi-platform support (ARM64 + AMD64)
- **Registry**: GitHub Container Registry (ghcr.io)
- **Database**: SQLite with persistent volume
- **Network**: Bridge network for container isolation
- **Restart Policy**: `unless-stopped` (auto-restart on Pi reboot)

## Security Notes

1. The `.env.production` file contains sensitive credentials - keep it secure
2. Consider changing the JWT_SECRET_KEY for production
3. Ensure your Pi's firewall only allows necessary ports
4. Regularly backup your database

## Support

For issues or questions, check:
- GitHub Issues: https://github.com/arlintdev/expenses/issues
- Container logs: `docker compose logs -f`
- Pi system logs: `journalctl -xe`
