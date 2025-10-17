"""
Background worker for processing URLs from the Redis queue
"""
import time
from app.queue import RedisQueue
from app.database import MetadataDB
from app.vector_store import VectorStore
from app.scraper import WebScraper

def main():
    """Main worker loop"""
    print("Starting worker...")
    
    # Initialize components
    queue = RedisQueue()
    db = MetadataDB()
    vector_store = VectorStore()
    scraper = WebScraper()
    
    print("Worker initialized. Waiting for jobs...")
    
    while True:
        try:
            # Get next job from queue
            job = queue.dequeue()
            
            if job:
                url = job['url']
                print(f"\nProcessing URL: {url}")
                
                try:
                    # Update status to processing
                    db.update_status(url, "processing")
                    
                    # Scrape and process the URL
                    chunks, metadatas = scraper.process_url(url)
                    print(f"Extracted {len(chunks)} chunks from {url}")
                    
                    # Store in vector database
                    vector_store.add_documents(chunks, metadatas, url)
                    print(f"Stored chunks in vector database")
                    
                    # Update status to completed
                    db.update_status(url, "completed", chunks_count=len(chunks))
                    print(f"✓ Successfully processed {url}")
                
                except Exception as e:
                    # Update status to failed
                    error_msg = str(e)
                    db.update_status(url, "failed", error_message=error_msg)
                    print(f"✗ Failed to process {url}: {error_msg}")
            
            else:
                # No jobs available, wait a bit
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("\nWorker stopped by user")
            break
        
        except Exception as e:
            print(f"Worker error: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    main()
