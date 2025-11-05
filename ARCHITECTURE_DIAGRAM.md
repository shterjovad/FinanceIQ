# Qdrant Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Host                              │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │         Qdrant Container (qdrant_financial_docs)           │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │               Qdrant Vector Database                  │  │ │
│  │  │                                                        │  │ │
│  │  │  - Vector Search Engine                               │  │ │
│  │  │  - HNSW Indexing                                      │  │ │
│  │  │  - Cosine Similarity                                  │  │ │
│  │  │  - Collection: financial_docs                         │  │ │
│  │  │  - Dimensions: 1536                                   │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                              │ │
│  │  ┌──────────────┐              ┌──────────────┐           │ │
│  │  │  REST API    │              │   gRPC API   │           │ │
│  │  │  Port 6333   │              │  Port 6334   │           │ │
│  │  └──────┬───────┘              └──────┬───────┘           │ │
│  └─────────┼─────────────────────────────┼──────────────────┘ │
│            │                              │                     │
│            │ Exposed                      │ Exposed             │
│            ↓                              ↓                     │
│  ┌─────────────────────┐       ┌─────────────────────┐        │
│  │   localhost:6333    │       │   localhost:6334    │        │
│  └─────────────────────┘       └─────────────────────┘        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Docker Volume: qdrant_storage                 │ │
│  │                                                              │ │
│  │  - Persistent storage for vector data                      │ │
│  │  - Survives container restarts                             │ │
│  │  - Mounted at: /qdrant/storage                             │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌─────────────────────┐
│  Python Application │
│   (RAG Pipeline)    │
└──────────┬──────────┘
           │
           │ qdrant-client
           │ REST API calls
           │
           ↓
    ┌──────────────┐
    │ Port 6333    │
    │ (REST API)   │
    └──────┬───────┘
           │
           ↓
┌──────────────────────┐
│  Qdrant Container    │
│                      │
│  ┌────────────────┐  │
│  │ Vector Engine  │  │
│  │   - Search     │  │
│  │   - Insert     │  │
│  │   - Update     │  │
│  │   - Delete     │  │
│  └────────┬───────┘  │
│           │          │
│           ↓          │
│  ┌────────────────┐  │
│  │ Storage Layer  │  │
│  └────────┬───────┘  │
└───────────┼──────────┘
            │
            ↓
    ┌───────────────┐
    │ Docker Volume │
    │ qdrant_storage│
    └───────────────┘
```

## Component Interactions

```
┌──────────────────────────────────────────────────────────────┐
│                      RAG System Stack                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────┐      ┌───────────────┐                   │
│  │   Document    │      │   Query       │                   │
│  │   Ingestion   │      │   Interface   │                   │
│  └───────┬───────┘      └───────┬───────┘                   │
│          │                      │                            │
│          │ 1. Extract text      │ 4. Search query           │
│          │ 2. Chunk docs        │ 5. Retrieve context       │
│          │ 3. Generate          │ 6. Generate response      │
│          │    embeddings        │                            │
│          │                      │                            │
│          ↓                      ↓                            │
│  ┌───────────────────────────────────────────┐              │
│  │        OpenAI Embedding API               │              │
│  │   (text-embedding-3-small: 1536 dims)     │              │
│  └───────────────┬───────────────────────────┘              │
│                  │                                           │
│                  │ Vector embeddings                         │
│                  │                                           │
│                  ↓                                           │
│  ┌───────────────────────────────────────────┐              │
│  │        Qdrant Vector Database             │              │
│  │                                             │             │
│  │  Collection: financial_docs                │             │
│  │  - Vectors: 1536-dimensional              │             │
│  │  - Metric: Cosine similarity              │             │
│  │  - Index: HNSW                            │             │
│  │  - Storage: Persistent volume             │             │
│  └───────────────────────────────────────────┘              │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Network Topology

```
┌────────────────────────────────────────────────────────────┐
│                      localhost                              │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────┐       │
│  │           Python Application Layer              │       │
│  │  - Flask/FastAPI server                         │       │
│  │  - RAG pipeline logic                           │       │
│  │  - Qdrant client integration                    │       │
│  └──────────────────┬──────────────────────────────┘       │
│                     │                                       │
│                     │ HTTP/REST                             │
│                     │                                       │
│  ┌──────────────────▼───────────────────────────┐          │
│  │     Docker Network (bridge)                  │          │
│  │                                                │         │
│  │  ┌─────────────────────────────────────────┐ │         │
│  │  │  Qdrant Container                       │ │         │
│  │  │  - IP: Assigned by Docker               │ │         │
│  │  │  - Hostname: qdrant                     │ │         │
│  │  │  - Ports: 6333:6333, 6334:6334          │ │         │
│  │  └─────────────────────────────────────────┘ │         │
│  │                                                │         │
│  └────────────────────────────────────────────────┘        │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

## Health Check Flow

```
Docker Compose
      │
      │ (Every 30 seconds)
      ↓
┌──────────────┐
│ Health Check │
│   Command    │
└──────┬───────┘
       │
       │ curl -f http://localhost:6333/health
       │
       ↓
┌──────────────────┐
│ Qdrant Container │
│   Health         │
│   Endpoint       │
└──────┬───────────┘
       │
       │ Response: {"title":"qdrant",...}
       ↓
┌──────────────────┐
│  Container       │
│  Status:         │
│  "healthy"       │
└──────────────────┘
```

## Volume Persistence

```
Container Lifecycle:

1. First Start
   ┌──────────────┐         ┌─────────────────┐
   │ docker       │ creates │ qdrant_storage  │
   │ compose up   ├────────→│ volume          │
   └──────────────┘         └─────────────────┘

2. Container Running
   ┌──────────────┐         ┌─────────────────┐
   │ Qdrant       │ writes  │ qdrant_storage  │
   │ Container    ├────────→│ /qdrant/storage │
   └──────────────┘         └─────────────────┘

3. Container Stop
   ┌──────────────┐         ┌─────────────────┐
   │ docker       │ preserves│ qdrant_storage │
   │ compose down │────────→│ (data retained) │
   └──────────────┘         └─────────────────┘

4. Container Restart
   ┌──────────────┐         ┌─────────────────┐
   │ docker       │ mounts  │ qdrant_storage  │
   │ compose up   ├────────→│ (existing data) │
   └──────────────┘         └─────────────────┘
                            │
                            ↓
                   ┌─────────────────┐
                   │ Data persisted! │
                   └─────────────────┘
```

## API Endpoints

```
Qdrant REST API (Port 6333)
│
├─ GET  /                    → API information
├─ GET  /health              → Health check
├─ GET  /metrics             → Prometheus metrics
├─ GET  /collections         → List collections
├─ PUT  /collections/{name}  → Create collection
├─ GET  /collections/{name}  → Get collection info
├─ POST /collections/{name}/points → Insert vectors
├─ POST /collections/{name}/points/search → Search vectors
└─ ...  (more endpoints)
```

## Collection Structure (To Be Created)

```
Collection: financial_docs
│
├─ Configuration
│  ├─ Vectors
│  │  ├─ Size: 1536
│  │  └─ Distance: Cosine
│  │
│  ├─ Indexing
│  │  └─ Type: HNSW
│  │
│  └─ Storage
│     └─ On disk: true
│
└─ Documents (Vectors + Metadata)
   │
   ├─ Point 1
   │  ├─ ID: uuid
   │  ├─ Vector: [1536 dimensions]
   │  └─ Payload:
   │     ├─ document_id
   │     ├─ chunk_id
   │     ├─ text
   │     ├─ metadata
   │     └─ timestamp
   │
   ├─ Point 2
   │  └─ ...
   │
   └─ Point N
      └─ ...
```
