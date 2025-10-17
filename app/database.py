import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

class MetadataDB:
    """Simple SQLite database to track URL ingestion status and metadata"""
    
    def __init__(self, db_path: str = "metadata.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                error_message TEXT,
                chunks_count INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_url(self, url: str) -> int:
        """Add a new URL with pending status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        try:
            cursor.execute("""
                INSERT INTO urls (url, status, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (url, "pending", now, now))
            
            url_id = cursor.lastrowid
            conn.commit()
            return url_id
        except sqlite3.IntegrityError:
            # URL already exists
            cursor.execute("SELECT id FROM urls WHERE url = ?", (url,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()
    
    def update_status(self, url: str, status: str, error_message: Optional[str] = None, chunks_count: int = 0):
        """Update the status of a URL"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE urls
            SET status = ?, updated_at = ?, error_message = ?, chunks_count = ?
            WHERE url = ?
        """, (status, now, error_message, chunks_count, url))
        
        conn.commit()
        conn.close()
    
    def get_url_status(self, url: str) -> Optional[Dict]:
        """Get the status of a specific URL"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM urls WHERE url = ?", (url,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return {
                "id": result[0],
                "url": result[1],
                "status": result[2],
                "created_at": result[3],
                "updated_at": result[4],
                "error_message": result[5],
                "chunks_count": result[6]
            }
        return None
    
    def get_all_urls(self) -> List[Dict]:
        """Get all URLs with their status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM urls ORDER BY created_at DESC")
        results = cursor.fetchall()
        
        conn.close()
        
        urls = []
        for result in results:
            urls.append({
                "id": result[0],
                "url": result[1],
                "status": result[2],
                "created_at": result[3],
                "updated_at": result[4],
                "error_message": result[5],
                "chunks_count": result[6]
            })
        
        return urls
