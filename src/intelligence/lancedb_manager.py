"""
LanceDB Manager for Hybrid RAG

Handles vector storage, embedding generation, and hybrid search (Keyword + Semantic).
Uses LanceDB as the embedded vector store and SentenceTransformers for embeddings.

Design Pattern: Repository / Manager
Features:
- Embedded Serverless Vector Store (LanceDB)
- Hybrid Search (BM25 + Vector)
- Automatic Embedding Generation
- Singleton Pattern for Connection Management
"""

import lancedb
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from loguru import logger
from sentence_transformers import SentenceTransformer
import pyarrow as pa
from datetime import datetime

# Default paths
DB_PATH = Path("data/lancedb")
MODEL_NAME = "all-MiniLM-L6-v2"  # Fast and efficient


class LanceDBManager:
    """
    Manager for LanceDB vector store operations.
    """
    
    _instance = None
    _model = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LanceDBManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: Path = DB_PATH):
        if not hasattr(self, 'initialized'):
            self.db_path = Path(db_path)
            self.db_path.mkdir(parents=True, exist_ok=True)
            self.db = lancedb.connect(self.db_path)
            self.initialized = True
            logger.info(f"LanceDB connected at {self.db_path}")

    @property
    def model(self):
        """Lazy load embedding model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {MODEL_NAME}")
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self.model.encode(text).tolist()
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        return self.model.encode(texts).tolist()
    
    def hybrid_search(
        self, 
        table_name: str, 
        query: str, 
        limit: int = 5,
        filters: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform search (Vector-based for now).
        TODO: Enable true Hybrid (BM25 + Vector) by registering embedding function.
        
        Args:
            table_name: Table to search
            query: Search query
            limit: Number of results
            filters: SQL-like filter string
        
        Returns:
            List of results with scores
        """
        if table_name not in self.db.list_tables():
            # Quick check failed, try robust check logic if needed or valid for now since list_tables call is expensive?
            # Actually, let's duplicate the logic or helper method? 
            # Duplicating for safety as this is a read op.
            _tables_result = self.db.list_tables()
            existing_tables = []
            if hasattr(_tables_result, "tables"):
                existing_tables = list(_tables_result.tables)
            else:
                existing_tables = list(_tables_result)
                
            if table_name not in existing_tables:
                logger.warning(f"Table {table_name} does not exist")
                return []
        
        tbl = self.db.open_table(table_name)
        
        # Generate query vector
        query_vec = self.get_embedding(query)
        
        try:
            # Pure Vector Search (Robust)
            search_builder = tbl.search(query_vec).limit(limit)
            
            if filters:
                search_builder = search_builder.where(filters)
            
            results = search_builder.to_list()
            
            # TODO: Add Cross-Encoder Reranking here
            
            return self._format_results(results)
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _format_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Standardize result format."""
        formatted_results = []
        for r in results:
            # Normalize score/distance
            score = 0.0
            if "_score" in r:
                score = r["_score"]
            elif "_distance" in r:
                # Convert distance to similarity score (approximate)
                # L2 Distance: 0 is best. Score: 1/(1+0)=1.0
                dist = r["_distance"]
                score = 1.0 / (1.0 + dist)
            
            # Remove internal fields to clean up response
            safe_r = {k: v for k, v in r.items() if k not in ["vector", "_score", "_distance"]}
            
            formatted_results.append({
                "score": score,
                **safe_r
            })
        return formatted_results
            
    def create_table(self, table_name: str, schema: Optional[pa.Schema] = None, mode: str = "overwrite"):
        """
        Create a new table or overwrite existing.
        
        Args:
            table_name: Name of the table
            schema: PyArrow schema (optional)
            mode: 'overwrite' or 'append'
        """
        try:
            # Check if table exists
            _tables_result = self.db.list_tables()
            existing_tables = []
            if hasattr(_tables_result, "tables"):
                existing_tables = list(_tables_result.tables)
            else:
                existing_tables = list(_tables_result)
            
            if table_name in existing_tables:
                if mode == "overwrite":
                    self.db.drop_table(table_name)
                    logger.info(f"Dropped existing table: {table_name}")
                elif mode == "append":
                    return self.db.open_table(table_name)
            
            # Create empty table if schema provided, otherwise wait for data
            if schema:
                tbl = self.db.create_table(table_name, schema=schema)
                logger.info(f"Created table: {table_name}")
                return tbl
                
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            raise
            
    def add_documents(
        self, 
        table_name: str, 
        documents: List[str], 
        metadata: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ):
        """
        Add documents to the vector store.
        """
        if not documents:
            return
        
        logger.info(f"Adding {len(documents)} documents to {table_name}")
        embeddings = self.get_embeddings(documents)
        
        data = []
        for i, (text, meta, vec) in enumerate(zip(documents, metadata, embeddings)):
            entry = {
                "vector": vec,
                "text": text,
                "created_at": datetime.now().isoformat(),
                **meta
            }
            if ids:
                entry["id"] = ids[i]
            data.append(entry)
        
        
        # Open or create table
        try:
            _tables_result = self.db.list_tables()
            # Handle API variations (iterator vs list vs object)
            existing_tables = []
            if hasattr(_tables_result, "tables"):
                existing_tables = list(_tables_result.tables)
            else:
                existing_tables = list(_tables_result)
                
            logger.info(f"Current tables: {existing_tables}")
            
            if table_name in existing_tables:
                tbl = self.db.open_table(table_name)
                tbl.add(data)
                logger.info(f"Appended to {table_name}")
            else:
                tbl = self.db.create_table(table_name, data=data)
                logger.info(f"Created new table {table_name}")
            
            # Create full text search index if not exists
            try:
                tbl.create_fts_index("text", replace=True)
            except Exception as e:
                logger.warning(f"Failed to create FTS index: {e}")
                
            logger.info(f"Added {len(data)} documents to {table_name}")
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise

    # ... (hybrid_search omitted for brevity) ...

    def semantic_search(
        self, 
        table_name: str, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Pure vector search."""
        _tables_result = self.db.list_tables()
        existing_tables = []
        if hasattr(_tables_result, "tables"):
            existing_tables = list(_tables_result.tables)
        else:
            existing_tables = list(_tables_result)
            
        logger.info(f"Semantic search: checking {table_name} in {existing_tables}")
        
        if table_name not in existing_tables:
            logger.warning(f"Table {table_name} not found")
            return []
            
        tbl = self.db.open_table(table_name)
        query_vec = self.get_embedding(query)
        
        results = tbl.search(query_vec).limit(limit).to_list()
        logger.info(f"Semantic search returned {len(results)} rows")
        return self._format_results(results)

# Singleton accessor
def get_lancedb_manager() -> LanceDBManager:
    return LanceDBManager()
