# System Architecture Overview: FinanceIQ

_This document defines the technical architecture for FinanceIQ, a multi-agent RAG system for intelligent financial document analysis. The architecture prioritizes rapid development, modern AI/ML practices, and portfolio-quality code._

---

## 1. AI/ML & Agent Framework Stack

**Core Intelligence Layer - The heart of the multi-agent RAG system**

- **LLM Provider:** OpenAI API (GPT-4 for production demo, GPT-3.5-turbo for development/testing)
  - Industry-standard reliability and performance
  - Excellent for complex financial reasoning tasks
  - Well-documented with robust Python SDK

- **Agent Orchestration Framework:** LangChain + LangGraph
  - LangGraph provides explicit state machine management for multi-agent workflows
  - LangChain handles LLM interactions, RAG components, and tool integrations
  - Demonstrates advanced architectural skills for portfolio

- **Embedding Model:** OpenAI text-embedding-3-small
  - Cost-effective and fast
  - Seamless integration with OpenAI ecosystem
  - Optimized for semantic search in RAG applications

- **Agent Architecture:**
  - Query Analyzer Agent: Determines query intent and complexity
  - Query Decomposer Agent: Breaks complex queries into sub-queries
  - Retrieval Agent: Performs semantic search against Qdrant
  - Reasoning/Synthesis Agent: Aggregates results and generates final answers

---

## 2. Data & Persistence

**Storage Layer - Vector database and document management**

- **Vector Database:** Qdrant (local instance via Docker)
  - Modern, Python-native vector search engine
  - Excellent performance for RAG applications
  - Built-in metadata/payload support eliminates need for separate database
  - Easy migration path to Qdrant Cloud if needed post-demo

- **Document Storage:** Local File System
  - Simple and sufficient for portfolio demo
  - Uploaded PDFs stored in local directory structure
  - No cloud storage costs during development

- **Metadata Management:** Qdrant Payload Fields
  - Store document metadata (filename, upload date, page count, etc.) directly in Qdrant
  - Eliminates complexity of separate metadata database
  - Keeps architecture simple and focused

---

## 3. Application & Technology Stack

**Core Development Stack - Languages, frameworks, and libraries**

- **Backend Language:** Python 3.10+
  - Perfect ecosystem match for LangChain/LangGraph
  - Extensive AI/ML library support
  - Modern type hints for better code quality

- **Frontend Framework:** Streamlit
  - Rapid development for ML/AI demos
  - Python-native (single-language stack)
  - Built-in chat interface components
  - Clean, professional UI out-of-the-box

- **PDF Processing:** pypdf
  - Reliable Python library for PDF text extraction
  - Handles standard financial documents (10-Ks, earnings reports)
  - Lightweight with minimal dependencies

- **Dependency Management:** uv
  - Modern, blazingly fast Python package manager
  - Shows up-to-date Python development practices
  - Superior performance over pip/Poetry

---

## 4. Infrastructure & Deployment

**Development and Deployment Environment**

- **Development Environment:** Local development
  - All development on local machine
  - Fast iteration cycles
  - No cloud infrastructure costs

- **Qdrant Deployment:** Docker container (local)
  - Run via `docker run -p 6333:6333 qdrant/qdrant`
  - Persistent storage to local disk
  - Realistic production-like setup

- **Deployment Target:** Local/Demo deployment
  - Portfolio/demo focus (not production deployment)
  - Run locally or share via Docker container
  - Optional: Simple Dockerfile for easy demo setup

- **Version Control:** Git + GitHub
  - Essential for portfolio presentation
  - Clean commit history demonstrates development process
  - README and documentation in repository

---

## 5. External Services & APIs

**Third-Party Integrations**

- **OpenAI API:**
  - LLM completions (GPT-4/GPT-3.5-turbo)
  - Text embeddings (text-embedding-3-small)
  - API key stored in `.env` file (excluded from git)
  - Cost optimization: Use GPT-3.5-turbo during development

- **No Authentication Services:** Single-user demo application (not in v1 scope)

- **No External Data Sources:** Works exclusively with uploaded documents (no real-time financial APIs)

---

## 6. Development Practices & Code Quality

**Professional Standards for Portfolio Presentation**

- **Code Quality Tools:**
  - **Ruff:** Modern, fast linter and formatter (replaces Black + isort + flake8)
  - **Type Hints:** Full type annotation coverage throughout codebase
  - Shows advanced Python development skills

- **Project Structure:**
  ```
  FinanceIQ/
  ├── src/
  │   ├── agents/          # Agent implementations
  │   ├── graph/           # LangGraph workflow definitions
  │   ├── rag/             # RAG pipeline (chunking, embedding, retrieval)
  │   └── ui/              # Streamlit interface
  ├── tests/               # Unit tests (if time permits)
  ├── data/                # Sample financial documents
  ├── .env.example         # Environment variable template
  ├── pyproject.toml       # uv project configuration
  ├── Dockerfile           # Optional containerization
  └── README.md            # Comprehensive documentation
  ```

- **Logging & Debugging:**
  - Python `logging` module for agent workflow visibility
  - Structured logs for debugging multi-step reasoning
  - Optional: LangSmith tracing (post-v1 enhancement)

- **Documentation:**
  - **README.md** with:
    - Architecture diagram
    - Setup instructions
    - Usage examples
    - Sample queries
  - **Inline docstrings** for all public functions and classes
  - Clear code comments explaining agent logic

---

## 7. Architecture Diagram (High-Level)

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Web UI                        │
│  (Document Upload + Chat Interface + Visualization)         │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              LangGraph Orchestration Layer                  │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │Query Analyzer│→ │  Decomposer  │→ │ Retrieval Agent │  │
│  └──────────────┘  └──────────────┘  └────────┬────────┘  │
│                                                │            │
│  ┌──────────────────────────────────────┐     │            │
│  │     Reasoning/Synthesis Agent        │ ←───┘            │
│  └──────────────────────────────────────┘                  │
└─────────────────┬──────────────────────┬────────────────────┘
                  │                      │
                  ▼                      ▼
         ┌────────────────┐    ┌──────────────────┐
         │  OpenAI API    │    │  Qdrant Vector   │
         │  (LLM +        │    │  Database        │
         │   Embeddings)  │    │  (Embeddings +   │
         └────────────────┘    │   Metadata)      │
                               └──────────────────┘
                                        │
                                        ▼
                               ┌──────────────────┐
                               │  Local File      │
                               │  System          │
                               │  (PDF Storage)   │
                               └──────────────────┘
```

---

## 8. Key Architectural Decisions & Rationale

**1. LangGraph over Simple Chains:**
- Provides explicit state management for complex multi-agent workflows
- Better visibility into agent execution flow
- Demonstrates advanced orchestration skills for portfolio

**2. Qdrant over Alternatives (Pinecone, Weaviate, ChromaDB):**
- Python-native with excellent developer experience
- Production-ready performance
- Can run locally (no cloud costs) but scales to cloud easily
- Built-in metadata support

**3. Streamlit over FastAPI + React:**
- Faster development (critical for 1-week timeline)
- Python-native (avoids context switching)
- Professional-looking UI with minimal code
- Perfect for ML/AI demos

**4. Local Deployment over Cloud:**
- Aligns with portfolio/demo scope
- Zero infrastructure costs
- Faster iteration during development
- Easy to containerize later if needed

**5. Simple Storage over Complex Infrastructure:**
- Local filesystem + Qdrant payload metadata sufficient for demo
- Avoids over-engineering for v1
- Keeps focus on AI/ML capabilities, not DevOps

---

**Next Step:** With the architecture defined, you're ready to dive into implementation details. Define the functional specifications for the upcoming feature by running `/awos:spec` or create a detailed technical specification with `/awos:tech`.
