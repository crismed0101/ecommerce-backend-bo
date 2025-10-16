#!/bin/bash

# ===========================================
# E-commerce Backend - Deployment Script
# ===========================================

set -e  # Exit on error

echo "=========================================="
echo "E-commerce Backend - Deployment"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Copy .env.example to .env and configure it first:"
    echo "  cp .env.example .env"
    exit 1
fi

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

print_info "Docker is running"

# Pull latest code (if in production)
if [ "$1" == "production" ]; then
    print_info "Pulling latest code from main branch..."
    git pull origin main
fi

# Build images
print_info "Building Docker images..."
docker-compose build --no-cache

# Stop existing containers
print_info "Stopping existing containers..."
docker-compose down

# Start containers
print_info "Starting containers..."
if [ "$1" == "production" ]; then
    # Start with nginx in production
    docker-compose --profile production up -d
else
    # Start without nginx in development
    docker-compose up -d
fi

# Wait for services to be healthy
print_info "Waiting for services to be healthy..."
sleep 10

# Check health
print_info "Checking service health..."
if docker-compose ps | grep -q "unhealthy"; then
    print_error "Some services are unhealthy!"
    docker-compose ps
    docker-compose logs --tail=50
    exit 1
fi

# Show running containers
print_info "Deployment successful!"
echo ""
echo "=========================================="
echo "Running containers:"
echo "=========================================="
docker-compose ps

echo ""
echo "=========================================="
echo "Access the API:"
echo "=========================================="
echo "  - API:         http://localhost:8000"
echo "  - Swagger UI:  http://localhost:8000/docs"
echo "  - Health:      http://localhost:8000/health"
echo ""
echo "View logs:"
echo "  docker-compose logs -f backend"
echo ""
echo "Stop services:"
echo "  docker-compose down"
echo "=========================================="
