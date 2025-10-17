import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict
from app.config import CHROMA_PERSIST_DIR, COLLECTION_NAME, EMBEDDING_MODEL

class VectorStore:
    """Handles vector storage and retrieval using ChromaDB"""
    
    def __init__(self):
        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            persist_directory=CHROMA_PERSIST_DIR,
            anonymized_telemetry=False
        ))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Web documents for RAG"}
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    
    def add_documents(self, chunks: List[str], metadatas: List[Dict], url: str):
        """Add document chunks to the vector store"""
        # Generate embeddings
        embeddings = self.embedding_model.encode(chunks).tolist()
        
        # Generate unique IDs for each chunk
        ids = [f"{url}_{i}" for i in range(len(chunks))]
        
        # Add to ChromaDB
        self.collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant documents"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and len(results['documents']) > 0:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
        
        return formatted_results
    
    def get_collection_count(self) -> int:
        """Get the total number of documents in the collection"""
        return self.collection.count()
