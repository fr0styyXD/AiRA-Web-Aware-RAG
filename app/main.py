from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional
import uvicorn

from app.database import MetadataDB
from app.queue import RedisQueue
from app.vector_store import VectorStore
from app.llm import LLMHandler
from app.config import API_HOST, API_PORT

# Initialize FastAPI app
app = FastAPI(
    title="AiRA - AI-powered RAG Engine",
    description="A scalable web-aware RAG system for ingesting and querying web content",
    version="1.0.0"
)

# Initialize components
db = MetadataDB()
queue = RedisQueue()
vector_store = VectorStore()
llm = LLMHandler()

# Request models
class IngestURLRequest(BaseModel):
    url: HttpUrl

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

# Response models
class IngestURLResponse(BaseModel):
    message: str
    url: str
    status: str
    job_id: Optional[int] = None

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: list
    num_sources: int

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "AiRA RAG Engine is running!",
        "status": "healthy",
        "redis_connected": queue.is_connected(),
        "total_documents": vector_store.get_collection_count()
    }

@app.post("/ingest-url", response_model=IngestURLResponse, status_code=202)
async def ingest_url(request: IngestURLRequest):
    """
    Submit a URL for asynchronous processing
    
    The URL will be validated, added to the database with 'pending' status,
    and pushed to the Redis queue for background processing.
    """
    url = str(request.url)
    
    # Check if Redis is connected
    if not queue.is_connected():
        raise HTTPException(status_code=503, detail="Queue service is not available")
    
    try:
        # Add URL to database
        job_id = db.add_url(url)
        
        # Add to processing queue
        queue.enqueue(url)
        
        return IngestURLResponse(
            message="URL submitted for processing",
            url=url,
            status="pending",
            job_id=job_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit URL: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query the knowledge base
    
    Searches the vector database for relevant content and generates
    a grounded answer using an LLM.
    """
    try:
        # Search vector store
        results = vector_store.search(request.query, top_k=request.top_k)
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail="No relevant documents found. Please ingest some URLs first."
            )
        
        # Generate answer using LLM
        response = llm.generate_answer_with_sources(request.query, results)
        
        return QueryResponse(
            query=request.query,
            answer=response["answer"],
            sources=response["sources"],
            num_sources=response["num_sources"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/status/{url:path}")
async def get_url_status(url: str):
    """Get the processing status of a specific URL"""
    status = db.get_url_status(url)
    
    if not status:
        raise HTTPException(status_code=404, detail="URL not found")
    
    return status

@app.get("/status")
async def get_all_status():
    """Get the status of all URLs"""
    urls = db.get_all_urls()
    return {
        "total_urls": len(urls),
        "urls": urls
    }

@app.get("/queue-info")
async def queue_info():
    """Get information about the processing queue"""
    return {
        "queue_length": queue.get_queue_length(),
        "redis_connected": queue.is_connected()
    }

if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
