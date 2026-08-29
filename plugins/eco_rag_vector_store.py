import sqlite3
import json
import numpy as np
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SQLiteVectorStore:
    """
    A persistent, local vector database built entirely on SQLite.
    Stores dense embeddings as binary blobs and allows cosine similarity search.
    This eliminates the need for expensive vector databases like Pinecone or Weaviate
    for local, privacy-first AI applications.
    """
    
    def __init__(self, db_path: str = "eco_vector_store.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the schema for storing vectors and metadata."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id TEXT PRIMARY KEY,
                        text_content TEXT NOT NULL,
                        embedding BLOB NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create an index on ID for fast lookups
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_embeddings_id ON embeddings(id)')
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize SQLite Vector Store: {e}")

    def _serialize_embedding(self, embedding: np.ndarray) -> bytes:
        """Converts a numpy array into a binary blob for SQLite storage."""
        # Ensure it's float32 for consistency
        return embedding.astype(np.float32).tobytes()

    def _deserialize_embedding(self, blob: bytes) -> np.ndarray:
        """Converts a binary blob back into a numpy array."""
        return np.frombuffer(blob, dtype=np.float32)

    def insert(self, doc_id: str, text: str, embedding: np.ndarray, metadata: Dict[str, Any] = None):
        """
        Inserts or updates a document and its embedding in the src.core.database.
        """
        if metadata is None:
            metadata = {}
            
        embedding_blob = self._serialize_embedding(embedding)
        metadata_json = json.dumps(metadata)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO embeddings (id, text_content, embedding, metadata)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        text_content=excluded.text_content,
                        embedding=excluded.embedding,
                        metadata=excluded.metadata
                ''', (doc_id, text, embedding_blob, metadata_json))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to insert document {doc_id}: {e}")

    def insert_batch(self, documents: List[Dict[str, Any]], embeddings: List[np.ndarray]):
        """
        Optimized batch insertion for processing large datasets (e.g., parsing a whole PDF).
        Expects documents to have 'id', 'text', and optionally 'metadata'.
        """
        if len(documents) != len(embeddings):
            raise ValueError("Length of documents must match length of embeddings.")
            
        insert_data = []
        for doc, emb in zip(documents, embeddings):
            doc_id = doc.get("id")
            if not doc_id:
                raise ValueError("All documents must have a unique 'id' field.")
                
            text = doc.get("text", "")
            meta = json.dumps(doc.get("metadata", {}))
            blob = self._serialize_embedding(emb)
            insert_data.append((doc_id, text, blob, meta))
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT INTO embeddings (id, text_content, embedding, metadata)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        text_content=excluded.text_content,
                        embedding=excluded.embedding,
                        metadata=excluded.metadata
                ''', insert_data)
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Batch insert failed: {e}")

    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific document and its metadata by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT text_content, metadata FROM embeddings WHERE id = ?', (doc_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        "id": doc_id,
                        "text": row[0],
                        "metadata": json.loads(row[1])
                    }
                return None
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve document {doc_id}: {e}")
            return None

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Performs a brute-force cosine similarity search across all stored vectors.
        Highly optimized using NumPy vectorization for small-to-medium datasets (up to ~100k vectors).
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Fetch all embeddings into memory for fast numpy computation
                # In a massive production system, we'd use pgvector or HNSW, but this is perfect for local RAG
                cursor.execute('SELECT id, text_content, embedding, metadata FROM embeddings')
                rows = cursor.fetchall()
                
            if not rows:
                return []
                
            # Unpack rows
            ids = []
            texts = []
            metadatas = []
            embeddings_list = []
            
            for row in rows:
                ids.append(row[0])
                texts.append(row[1])
                metadatas.append(json.loads(row[3]))
                embeddings_list.append(self._deserialize_embedding(row[2]))
                
            # Convert list of arrays to a single 2D matrix
            db_matrix = np.vstack(embeddings_list)
            
            # Ensure query is 1D
            query_vec = query_embedding.flatten()
            
            # Compute cosine similarity manually using numpy
            # formula: dot(A, B) / (norm(A) * norm(B))
            dot_products = np.dot(db_matrix, query_vec)
            norms_db = np.linalg.norm(db_matrix, axis=1)
            norm_query = np.linalg.norm(query_vec)
            
            # Prevent division by zero
            denom = norms_db * norm_query
            denom[denom == 0] = 1e-10
            
            similarities = dot_products / denom
            
            # Get indices of top_k results
            # argpartition is much faster than sorting the entire array
            k = min(top_k, len(similarities))
            if k == len(similarities):
                top_indices = np.argsort(similarities)[::-1]
            else:
                top_indices = np.argpartition(similarities, -k)[-k:]
                # Sort exactly the top k
                top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
                
            results = []
            for idx in top_indices:
                score = similarities[idx]
                if score > 0.1: # relevance threshold
                    results.append({
                        "id": ids[idx],
                        "text": texts[idx],
                        "metadata": metadatas[idx],
                        "score": float(score)
                    })
                    
            return results
            
        except sqlite3.Error as e:
            logger.error(f"SQLite search failed: {e}")
            return []
        except Exception as e:
            logger.error(f"NumPy vector search failed: {e}")
            return []

    def delete(self, doc_id: str) -> bool:
        """Deletes a document from the vector store."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM embeddings WHERE id = ?', (doc_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    def clear(self):
        """Drops all embeddings (Useful for rebuilding the knowledge base)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM embeddings')
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to clear database: {e}")
