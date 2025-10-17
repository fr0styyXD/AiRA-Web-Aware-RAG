# AiRA - AI-powered RAG Engine 🚀

A scalable, web-aware Retrieval-Augmented Generation (RAG) system that asynchronously ingests web content and provides grounded, fact-based answers through semantic search.

---

## Table of Contents
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Database Design](#database-design)
- [API Documentation](#api-documentation)
- [Setup Instructions](#setup-instructions)
- [Usage Examples](#usage-examples)
- [Design Decisions](#design-decisions)

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       │ HTTP Requests
       ▼
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│  ┌─────────────┐    ┌────────────────┐ │
│  │ /ingest-url │    │    /query      │ │
│  └──────┬──────┘    └────────┬───────┘ │
└─────────┼────────────────────┼─────────┘
          │                    │
          │                    │
    ┌─────▼─────┐       ┌─────▼──────┐
    │   Redis   │       │  ChromaDB  │
    │   Queue   │       │  (Vector   │
    └─────┬─────┘       │   Store)   │
          │             └─────▲──────┘
          │                   │
    ┌─────▼─────┐            │
    │  Worker   │────────────┘
    │  Process  │
    └─────┬─────┘
          │
    ┌─────▼─────┐
    │  SQLite   │
    │ Metadata  │
    │    DB     │
    └───────────┘
```

### Component Flow

1. **Ingestion Flow**:
   - User submits URL via `POST /ingest-url`
   - API validates URL and adds to SQLite with `pending` status
   - Job pushed to Redis queue
   - Returns `202 Accepted` immediately
   - Worker picks up job from queue
   - Worker fetches content, chunks it, generates embeddings
   - Embeddings stored in ChromaDB
   - Status updated to `completed` in SQLite

2. **Query Flow**:
   - User submits query via `POST /query`
   - Query embedded using same model
   - Semantic search in ChromaDB returns top-k relevant chunks
   - Chunks + query sent to OpenAI GPT-3.5
   - LLM generates grounded answer
   - Response returned with sources

---

## Technology Stack

### Core Technologies

| Component | Technology | Reasoning |
|-----------|-----------|-----------|
| **Web Framework** | FastAPI | Fast, modern, async support, automatic API docs |
| **Message Queue** | Redis | Simple, fast, reliable for job queuing |
| **Vector Database** | ChromaDB | Easy to use, good for prototyping, persistent storage |
| **Metadata Store** | SQLite | Lightweight, no setup required, sufficient for this scale |
| **Embeddings** | Sentence-Transformers | Open-source, runs locally, good quality embeddings |
| **LLM** | OpenAI GPT-3.5-turbo | Reliable, good quality, cost-effective |
| **Web Scraping** | BeautifulSoup4 | Simple, effective HTML parsing |

### Why These Choices?

1. **FastAPI**: Chosen for its async capabilities, automatic validation with Pydantic, and built-in API documentation (Swagger UI). Perfect for building REST APIs quickly.

2. **Redis**: Industry-standard for message queuing. Simple to set up and extremely fast. Provides reliable job queuing with blocking operations.

3. **ChromaDB**: Lightweight vector database that's easy to set up and use. Supports persistence and has a simple Python API. Good for development and small-to-medium scale deployments.

4. **SQLite**: No separate database server needed. Perfect for tracking metadata and job status. Can be easily migrated to PostgreSQL for production.

5. **Sentence-Transformers**: Provides high-quality embeddings without API costs. The `all-MiniLM-L6-v2` model is fast and produces good results for semantic search.

---

## Database Design

### Metadata Database (SQLite)

**Table: `urls`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key, auto-increment |
| `url` | TEXT | The URL being processed (unique) |
| `status` | TEXT | Current status: `pending`, `processing`, `completed`, `failed` |
| `created_at` | TEXT | ISO timestamp of when URL was submitted |
| `updated_at` | TEXT | ISO timestamp of last status update |
| `error_message` | TEXT | Error details if status is `failed` |
| `chunks_count` | INTEGER | Number of chunks extracted from the URL |

**Design Rationale**:
- Simple schema focused on tracking ingestion status
- `url` is unique to prevent duplicate processing
- Timestamps help with debugging and monitoring
- `chunks_count` provides insight into document size

### Vector Database (ChromaDB)

**Collection: `web_documents`**

Each document chunk is stored with:
- **Embedding**: 384-dimensional vector (from all-MiniLM-L6-v2)
- **Document Text**: The actual text chunk
- **Metadata**:
  - `url`: Source URL
  - `chunk_index`: Position in the original document
  - `total_chunks`: Total number of chunks from this URL
- **ID**: Unique identifier (`{url}_{chunk_index}`)

**Design Rationale**:
- Chunks are 500 words with 50-word overlap for context preservation
- Metadata allows tracing answers back to sources
- Unique IDs prevent duplicates and enable updates

---

## API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Health Check
```bash
GET /
```

**Response**:
```json
{
  "message": "AiRA RAG Engine is running!",
  "status": "healthy",
  "redis_connected": true,
  "total_documents": 42
}
```

---

#### 2. Ingest URL
```bash
POST /ingest-url
```

**Request Body**:
```json
{
  "url": "https://example.com/article"
}
```

**Response** (202 Accepted):
```json
{
  "message": "URL submitted for processing",
  "url": "https://example.com/article",
  "status": "pending",
  "job_id": 1
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/ingest-url" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Artificial_intelligence"}'
```

---

#### 3. Query Knowledge Base
```bash
POST /query
```

**Request Body**:
```json
{
  "query": "What is artificial intelligence?",
  "top_k": 5
}
```

**Response**:
```json
{
  "query": "What is artificial intelligence?",
  "answer": "Artificial intelligence (AI) is the simulation of human intelligence processes by machines, especially computer systems. These processes include learning, reasoning, and self-correction...",
  "sources": [
    "https://en.wikipedia.org/wiki/Artificial_intelligence"
  ],
  "num_sources": 1
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?", "top_k": 5}'
```

---

#### 4. Check URL Status
```bash
GET /status/{url}
```

**Example**:
```bash
GET /status/https://example.com/article
```

**Response**:
```json
{
  "id": 1,
  "url": "https://example.com/article",
  "status": "completed",
  "created_at": "2025-10-16T10:30:00",
  "updated_at": "2025-10-16T10:31:45",
  "error_message": null,
  "chunks_count": 15
}
```

---

#### 5. Get All URLs Status
```bash
GET /status
```

**Response**:
```json
{
  "total_urls": 3,
  "urls": [
    {
      "id": 1,
      "url": "https://example.com/article1",
      "status": "completed",
      "chunks_count": 15
    },
    {
      "id": 2,
      "url": "https://example.com/article2",
      "status": "processing",
      "chunks_count": 0
    }
  ]
}
```

---

#### 6. Queue Information
```bash
GET /queue-info
```

**Response**:
```json
{
  "queue_length": 2,
  "redis_connected": true
}
```

---

## Setup Instructions

### Prerequisites
- Python 3.8+
- Redis server
- OpenAI API key

### Step 1: Clone the Repository
```bash
git clone <your-repo-url>
cd AiRA
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=your_key_here
```

### Step 5: Start Redis
```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or install Redis locally and run
redis-server
```

### Step 6: Start the API Server
```bash
python -m uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

Interactive API docs: `http://localhost:8000/docs`

### Step 7: Start the Worker (in a new terminal)
```bash
# Activate virtual environment first
python worker.py
```

---

## Usage Examples

### Example 1: Ingest a Wikipedia Article
```bash
curl -X POST "http://localhost:8000/ingest-url" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Machine_learning"}'
```

### Example 2: Query After Ingestion
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the main types of machine learning?"}'
```

### Example 3: Check Processing Status
```bash
curl "http://localhost:8000/status/https://en.wikipedia.org/wiki/Machine_learning"
```

---

## Design Decisions

### 1. Asynchronous Processing
**Decision**: Use Redis queue with separate worker process

**Rationale**: 
- Web scraping can be slow (network latency, large pages)
- Embedding generation is CPU-intensive
- Users shouldn't wait for processing to complete
- Allows horizontal scaling of workers

### 2. Chunking Strategy
**Decision**: 500-word chunks with 50-word overlap

**Rationale**:
- Balances context preservation with retrieval precision
- Overlap ensures important information isn't split
- Works well with the embedding model's context window

### 3. Embedding Model
**Decision**: Use Sentence-Transformers locally instead of OpenAI embeddings

**Rationale**:
- No API costs for embeddings
- Faster (no network calls)
- Good quality for semantic search
- Can run offline

### 4. SQLite for Metadata
**Decision**: Use SQLite instead of PostgreSQL

**Rationale**:
- No separate database server needed
- Sufficient for tracking job status
- Easy to set up and use
- Can migrate to PostgreSQL later if needed

### 5. ChromaDB for Vectors
**Decision**: Use ChromaDB instead of Pinecone/Qdrant

**Rationale**:
- No external service required
- Easy to set up and use
- Supports persistence
- Good for development and small-to-medium scale
- Can migrate to hosted solution if needed

---

## 🔄 Scalability Considerations

### Current Architecture
- Single API server
- Single worker process
- Local Redis and ChromaDB

### Scaling Path

1. **Horizontal Scaling**:
   - Multiple API servers behind load balancer
   - Multiple worker processes
   - Redis cluster for high availability

2. **Database Scaling**:
   - Migrate SQLite to PostgreSQL
   - Use managed ChromaDB or migrate to Qdrant/Pinecone
   - Add caching layer (Redis)

3. **Performance Optimization**:
   - Batch embedding generation
   - Implement rate limiting
   - Add monitoring and metrics
   - Use CDN for static content

---

## Author

**Aksh Dhingra**
- GitHub: [@fr0styyXD](https://github.com/fr0styyXD)
- LinkedIn: [Aksh Dhingra](https://linkedin.com/in/akshdhingra)
- Email: workdhingra20@gmail.com

---

## Acknowledgments

- FastAPI for the excellent web framework
- ChromaDB for the vector database
- Sentence-Transformers for embeddings
- OpenAI for the LLM API
