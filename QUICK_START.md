# Quick Start Guide - Qdrant Setup

## Prerequisites
- Docker Desktop must be running

## Quick Start (3 Steps)

### 1. Start Docker Desktop
Open Docker Desktop and wait for it to fully start.

### 2. Start Qdrant
```bash
cd /home/dona/projects/IBMProject
./scripts/start_qdrant.sh
```

### 3. Verify Setup
```bash
./scripts/verify_qdrant_setup.sh
```

## Manual Commands

### Start Qdrant
```bash
docker compose up -d
```

### Check Status
```bash
docker ps | grep qdrant
```

### Health Check
```bash
curl http://localhost:6333/health
```

### View Logs
```bash
docker compose logs -f qdrant
```

### Stop Qdrant
```bash
docker compose down
```

## Access Points
- REST API: http://localhost:6333
- Dashboard: http://localhost:6333/dashboard
- gRPC API: localhost:6334

## Troubleshooting
See `QDRANT_SETUP.md` for detailed troubleshooting guide.
