# Mireva — RAG Foundation

This repository contains the decoupled, production-grade Retrieval-Augmented Generation (RAG) foundation for **Mireva**.

The architecture retains the proven 10-stage document ingestion/indexing pipeline and 11-stage hybrid retrieval pipeline along with reusable storage integrations (Qdrant, Supabase Object Storage, PostgreSQL), completely decoupled from previous application-specific schemas, agents, and business workflows.

---

## 1. System Architecture Overview

```
                                      ┌─────────────────────────────────────────────────────────┐
                                      │                     MIREVA RAG                          │
                                      └─────────────────────────────────────────────────────────┘
                                                 │                                   │
                                                 ▼                                   ▼
                             ┌───────────────────────────────────────┐   ┌──────────────────────────────────────┐
                             │       10-Stage Indexing Pipeline      │   │     11-Stage Hybrid Retrieval        │
                             └───────────────────────────────────────┘   └──────────────────────────────────────┘
                                                 │                                   │
                ┌────────────────────────────────┼───────────────────────────────────┼────────────────────────────────┐
                ▼                                ▼                                   ▼                                ▼
┌───────────────────────────────┐ ┌───────────────────────────────┐ ┌─────────────────────────────────┐ ┌───────────────────────────────┐
│     PostgreSQL Content Store  │ │     Qdrant Vector Store       │ │      Embedding & Sparse Encoders│ │     Jina Cross-Encoder        │
│  - Text persistence           │ │  - 1024-dim dense vectors     │ │  - Cohere Embed v4 (dense)      │ │  - reranker-v3.5              │
│  - ChunkModel                 │ │  - Sparse technical vectors   │ │  - Voyage AI (optional)         │ │  - Calibrated scoring         │
│  - Short-transaction boundary │ │  - Deterministic RFC 4122 v5  │ │  - Technical Sparse Hash        │ │  - Context window truncation  │
└───────────────────────────────┘ └───────────────────────────────┘ └─────────────────────────────────┘ └───────────────────────────────┘
```

---

## 2. Core Capabilities Retained

### A. Document Indexing Pipeline (10 Stages)
1. **Acquisition**: Retrieves source files (PDF, DOCX, TXT, MD) from Supabase Object Storage.
2. **Ingestion**: Validates MIME types, byte sizes, checksums, and tenant isolation boundaries.
3. **Parsing & Extraction**: Text and structure extraction for markdown, text, docx, and PDF documents.
4. **Cleaning**: Whitespace collapse, unicode normalization, control character stripping.
5. **Normalization**: Content normalization and encoding sanitation.
6. **Chunking**: Heading-aware structural hierarchy chunking with token constraints.
7. **Metadata Enrichment**: Enriches chunks with structural coordinates, headings, and paths.
8. **Optional Contextual Enrichment**: Prepends contextual document-level summaries to chunk representation texts.
9. **Representation Generation**: Batched dense embeddings (Cohere Embed v4 / Voyage) + sparse technical hash vectors (`xxhash`).
10. **Persistence & Vector Indexing**:
    - **PostgreSQL**: Atomic chunk text and metadata persistence into `ChunkModel`.
    - **Qdrant**: Batched, idempotent vector upserts with deterministic RFC 4122 v5 UUIDs and bounded retries.
    - **Stale Vector Pruning**: Prunes superseded vectors upon successful re-indexing.

### B. Hybrid Retrieval Pipeline (11 Stages)
1. **Query Preprocessing & Validation**: Enforces length constraints and cleans input queries.
2. **Query Transformation**: Optional LLM-assisted query rewriting and expansion with graceful fallback.
3. **Query Embedding**: Computes dense query vectors with `input_type="search_query"`.
4. **Dense Vector Search**: Scoped Qdrant similarity search with project isolation filtering.
5. **Sparse Keyword Search**: Qdrant sparse vector search matching technical terms and exact tokens.
6. **Reciprocal Rank Fusion (RRF)**: Combines dense and sparse candidate rankings (`k=60`).
7. **Metadata Filtering**: Applies user-supplied payload filters (document IDs, section paths, tags).
8. **Cross-Encoder Reranking**: Jina Reranker v3.5 deep cross-attention scoring.
9. **Chunk Hydration**: Batched relational lookup in PostgreSQL `ChunkModel` by chunk IDs.
10. **Relevance Assessment & Bounded Fallback**: Validates relevance thresholds and triggers fallback if needed.
11. **Context Assembly & Formatting**: Assembles structured context items with headers, provenance, and tokens.

---

## 3. Storage Architecture & Decoupling

| Storage Subsystem | Technology | Responsibility in Mireva |
| :--- | :--- | :--- |
| **Relational Database** | PostgreSQL via SQLAlchemy (`asyncpg`) | Stores chunk verbatim text, structural hierarchy, and metadata in `ChunkModel`. Decoupled from legacy foreign keys and schemas. |
| **Vector Store** | Qdrant (`AsyncQdrantClient`) | Stores 1024-dimensional dense vectors, sparse vectors, and payload filters (`project_id`, `document_id`, `chunk_id`). |
| **Object Storage** | Supabase Storage (`storage3`) | Stores original uploaded documents and binaries with isolation path prefixes. |

---

## 4. API Endpoints

### Preserved Retrieval Endpoint
```http
POST /projects/{project_id}/retrieval
Content-Type: application/json

{
  "query": "What is the system architecture?",
  "top_k": 5,
  "enable_sparse": true,
  "enable_reranking": true
}
```

**Response**:
```json
{
  "project_id": "proj-1",
  "original_query": "What is the system architecture?",
  "retrieval_query": "What is the system architecture?",
  "chunk_count": 3,
  "chunks": [ ... ],
  "formatted_context": "RETRIEVED CONTEXT\n\n[Context 1]\n...",
  "execution_metadata": {
    "total_duration_ms": 142.5,
    "attempts_count": 1,
    "fallback_triggered": false,
    "stage_latencies_ms": { ... }
  }
}
```

### Health & Root Endpoints
- `GET /health`: Basic health check (`status`, `app_name`, `version`, `environment`).
- `GET /`: Platform welcome banner.

---

## 5. Development Setup & Verification

### Prerequisites
- Python 3.12+
- PostgreSQL (or Supabase PostgreSQL)
- Qdrant Cluster / Local Instance

### Virtual Environment Setup
```powershell
# From backend/ directory
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### Configuration
Copy `.env.example` to `.env` and provide credentials:
```powershell
cp .env.example .env
```

Key environment variables:
- `DATABASE_URL`: Asynchronous PostgreSQL connection string (`postgresql+asyncpg://...`).
- `QDRANT_URL` & `QDRANT_API_KEY`: Qdrant endpoint and API key.
- `COHERE_API_KEY`: API key for Cohere Embed v4 dense embeddings.
- `JINA_API_KEY`: API key for Jina Reranker v3.5.
- `SUPABASE_URL` & `SUPABASE_SERVICE_ROLE_KEY`: Supabase object storage credentials.

### Running Tests
Execute the full test suite with `pytest`:
```powershell
pytest backend/tests/ -v --disable-warnings
```

All 747 tests validate:
- RAG acquisition, ingestion, parsing, chunking, enrichment, and normalization.
- Cohere Embed v4 and Voyage dense embeddings.
- Sparse technical hashing and Qdrant sparse vector integration.
- Reciprocal Rank Fusion, metadata filtering, and Jina reranking.
- PostgreSQL chunk persistence, isolation, and batched hydration.
- Architectural decoupling boundaries (zero legacy dependencies).
