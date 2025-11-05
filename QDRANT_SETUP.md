# Qdrant Docker Setup Guide

## Overview

This guide explains the Qdrant vector database setup for the RAG Query System & Chat Interface.

## Configuration Details

### Docker Compose Configuration
- **File**: `docker-compose.yml`
- **Service Name**: qdrant
- **Container Name**: qdrant_financial_docs
- **Image**: qdrant/qdrant:latest

### Network Configuration
- **REST API Port**: 6333 (mapped to host)
- **gRPC Port**: 6334 (mapped to host, optional for advanced usage)
- **Health Check Endpoint**: http://localhost:6333/health

### Storage Configuration
- **Volume Name**: qdrant_storage
- **Mount Point**: /qdrant/storage
- **Driver**: local (persistent across container restarts)

### Vector Database Settings (for collection setup later)
- **Collection Name**: financial_docs
- **Vector Dimensions**: 1536 (OpenAI text-embedding-3-small)
- **Distance Metric**: Cosine similarity

## Setup Instructions

### Prerequisites
- Docker Desktop must be installed and running
- Windows WSL 2 integration enabled (if on Windows)

### Step 1: Start Docker Desktop
1. Open Docker Desktop application on your machine
2. Wait for Docker to fully start (check the system tray/menu bar icon)
3. Verify Docker is running by executing:
   ```bash
   docker ps
   ```

### Step 2: Start Qdrant Service
Navigate to the project root directory and run:

```bash
docker compose up -d
```

Expected output:
```
[+] Running 2/2
 ✔ Volume "ibmproject_qdrant_storage"  Created
 ✔ Container qdrant_financial_docs     Started
```

### Step 3: Verify Qdrant is Running
Check container status:
```bash
docker ps | grep qdrant
```

### Step 4: Health Check
Verify Qdrant health endpoint responds:
```bash
curl http://localhost:6333/health
```

Expected response:
```json
{"title":"qdrant - vector search engine","version":"<version>"}
```

Or using the Web API endpoint:
```bash
curl http://localhost:6333/
```

## Management Commands

### View Logs
```bash
docker compose logs qdrant
```

### Follow Logs in Real-time
```bash
docker compose logs -f qdrant
```

### Stop Qdrant
```bash
docker compose down
```

### Stop and Remove Volume (CAUTION: Deletes all data)
```bash
docker compose down -v
```

### Restart Qdrant
```bash
docker compose restart qdrant
```

## Troubleshooting

### Issue: Container won't start
1. Check Docker Desktop is running
2. Verify port 6333 is not in use:
   ```bash
   netstat -an | grep 6333
   ```
3. Check container logs:
   ```bash
   docker compose logs qdrant
   ```

### Issue: Health check fails
1. Wait 30-40 seconds for Qdrant to fully initialize
2. Check if container is running:
   ```bash
   docker ps
   ```
3. Inspect container health:
   ```bash
   docker inspect qdrant_financial_docs | grep -A 10 Health
   ```

### Issue: Data not persisting
1. Verify volume exists:
   ```bash
   docker volume ls | grep qdrant
   ```
2. Inspect volume:
   ```bash
   docker volume inspect ibmproject_qdrant_storage
   ```

## Next Steps

After successful setup:
1. Create the `financial_docs` collection with 1536 dimensions
2. Configure collection for cosine similarity
3. Integrate with the RAG pipeline for document ingestion
4. Connect the query interface to Qdrant

## Additional Resources

- Qdrant Documentation: https://qdrant.tech/documentation/
- Docker Compose Documentation: https://docs.docker.com/compose/
- Qdrant API Reference: https://qdrant.github.io/qdrant/redoc/index.html
