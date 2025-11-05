#!/bin/bash

# Quick start script for Qdrant service
# Usage: ./scripts/start_qdrant.sh

set -e

echo "Starting Qdrant vector database..."
echo ""

# Navigate to project root (script is in scripts/ directory)
cd "$(dirname "$0")/.."

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo "Error: Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Start Qdrant
echo "Starting Qdrant container..."
docker compose up -d

echo ""
echo "Waiting for Qdrant to be ready..."
sleep 5

# Quick health check
if curl -f http://localhost:6333/health > /dev/null 2>&1; then
    echo ""
    echo "✓ Qdrant is running successfully!"
    echo ""
    echo "Access points:"
    echo "  - REST API: http://localhost:6333"
    echo "  - Dashboard: http://localhost:6333/dashboard"
    echo ""
    echo "To view logs: docker compose logs -f qdrant"
    echo "To stop: docker compose down"
else
    echo ""
    echo "Qdrant started but health check failed."
    echo "It may still be initializing. Wait a moment and check:"
    echo "  curl http://localhost:6333/health"
    echo ""
    echo "Or check logs:"
    echo "  docker compose logs qdrant"
fi
