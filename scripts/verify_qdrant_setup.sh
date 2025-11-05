#!/bin/bash

# Qdrant Setup Verification Script
# This script verifies that Qdrant is properly configured and running

set -e

echo "=========================================="
echo "Qdrant Setup Verification"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
echo "1. Checking Docker availability..."
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running or not accessible${NC}"
    echo "  Please start Docker Desktop and try again"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Check if docker-compose.yml exists
echo "2. Checking docker-compose.yml..."
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}✗ docker-compose.yml not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ docker-compose.yml exists${NC}"
echo ""

# Start Qdrant if not running
echo "3. Starting Qdrant service..."
docker compose up -d
echo -e "${GREEN}✓ Qdrant service started${NC}"
echo ""

# Wait for Qdrant to be ready
echo "4. Waiting for Qdrant to initialize (max 60 seconds)..."
COUNTER=0
MAX_WAIT=60
until curl -f http://localhost:6333/health > /dev/null 2>&1; do
    COUNTER=$((COUNTER + 1))
    if [ $COUNTER -ge $MAX_WAIT ]; then
        echo -e "${RED}✗ Qdrant did not start within ${MAX_WAIT} seconds${NC}"
        echo "  Check logs with: docker compose logs qdrant"
        exit 1
    fi
    echo -n "."
    sleep 1
done
echo ""
echo -e "${GREEN}✓ Qdrant is responding${NC}"
echo ""

# Verify health endpoint
echo "5. Verifying health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:6333/health)
echo "   Response: $HEALTH_RESPONSE"
if echo "$HEALTH_RESPONSE" | grep -q "qdrant"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    exit 1
fi
echo ""

# Check container status
echo "6. Checking container status..."
docker ps | grep qdrant_financial_docs
echo -e "${GREEN}✓ Container is running${NC}"
echo ""

# Check volume
echo "7. Verifying persistent volume..."
docker volume ls | grep qdrant_storage
echo -e "${GREEN}✓ Persistent volume exists${NC}"
echo ""

# Display Qdrant info
echo "8. Fetching Qdrant information..."
curl -s http://localhost:6333/ | python3 -m json.tool 2>/dev/null || curl -s http://localhost:6333/
echo ""

echo "=========================================="
echo -e "${GREEN}✓ All checks passed!${NC}"
echo "=========================================="
echo ""
echo "Qdrant is ready for use:"
echo "  - REST API: http://localhost:6333"
echo "  - gRPC API: localhost:6334"
echo "  - Web UI: http://localhost:6333/dashboard"
echo ""
echo "Next steps:"
echo "  1. Create collection 'financial_docs' with 1536 dimensions"
echo "  2. Configure cosine similarity metric"
echo "  3. Integrate with RAG pipeline"
echo ""
