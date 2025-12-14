#!/bin/bash
# Deployment script for Raspberry Pi

set -e

echo "🚀 Starting deployment to Raspberry Pi..."

# Create data directory if it doesn't exist
mkdir -p data

echo "✅ Data directory ready"

# Pull the latest image
echo "📦 Pulling latest Docker image..."
docker compose pull

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker compose down

# Start containers
echo "🚀 Starting containers..."
docker compose up -d

# Show status
echo "📊 Container status:"
docker compose ps

echo ""
echo "✅ Deployment complete!"
echo "🌐 Application available at: http://192.168.68.63:3000"
echo ""
echo "📝 Useful commands:"
echo "  - View logs:    docker compose logs -f"
echo "  - Stop:         docker compose down"
echo "  - Restart:      docker compose restart"
echo "  - Update:       docker compose pull && docker compose up -d"
