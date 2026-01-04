#!/bin/bash

# PCA Agent Deployment Script

# Stop on error
set -e

echo "🚀 Starting Deployment..."

# 1. Pull latest code
echo "📥 Pulling latest code..."
git pull origin main

# 2. Build Containers
echo "🏗️  Building containers..."
docker compose \
    -f docker-compose.yml \
    -f docker-compose.deploy.yml \
    build

# 3. Start Services
echo "🚀 Starting services..."
docker compose \
    -f docker-compose.yml \
    -f docker-compose.deploy.yml \
    up -d

# 5. Prune old images to save space
echo "🧹 Cleaning up..."
docker image prune -f

echo "✅ Deployment Complete!"
echo "   Frontend: http://localhost (or check your public IP)"
echo "   API:      http://localhost/api/v1/health"
