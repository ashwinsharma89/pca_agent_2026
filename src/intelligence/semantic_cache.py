"""
Semantic Cache for NL-to-SQL

Reduces LLM latency and cost by caching generated SQL for similar questions.
Uses LanceDB for vector similarity search.

Logic:
1. Receive user question.
2. Check cache for similar questions (cosine similarity > 0.95).
3. If hit, return cached SQL.
4. If miss, generate SQL and add to cache.

Design Pattern: Proxy / Caching
"""

import json
from typing import Optional, Dict, Any, Tuple
from loguru import logger
from datetime import datetime
import pandas as pd

from src.intelligence.lancedb_manager import get_lancedb_manager

class SemanticCache:
    """
    Semantic cache using LanceDB.
    """
    
    TABLE_NAME = "semantic_cache"
    similarity_threshold = 0.95
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_lancedb_manager()
        self._ensure_table()
        
    def _ensure_table(self):
        """Ensure cache table exists."""
        # Schema is inferred from data, so we rely on checks in get/set
        pass
        
    def get(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached result if a similar question exists.
        
        Args:
            question: User's natural language question
            
        Returns:
            Cached result dict or None
        """
        try:
            # Semantic search for similar questions
            results = self.db_manager.semantic_search(
                table_name=self.TABLE_NAME,
                query=question,
                limit=1
            )
            
            if not results:
                return None
            
            best_match = results[0]
            score = best_match.get('score', 0.0)
            
            # Use distance-to-score conversion if needed
            # Assuming lancedb_manager returns 'score' normalized (0-1) 
            # or we check if it's cosine distance (L2).
            # If default metric is L2, lower is better. If Cosine, higher is better?
            # SentenceTransformers uses Cosine usually, but LanceDB default is L2.
            # However, logic in lancedb_manager._format_results handles conversion:
            # score = 1.0 / (1.0 + r["_distance"])
            
            if score >= self.similarity_threshold:
                logger.info(f"Cache hit! Question: '{question}' matched '{best_match['text']}' (score: {score:.4f})")
                return {
                    "sql": best_match.get("sql_query"),
                    "explanation": best_match.get("explanation"),
                    "original_question": best_match.get("text"),
                    "similarity": score
                }
            
            logger.debug(f"Cache miss. Best match: {score:.4f} < {self.similarity_threshold}")
            return None
            
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")
            return None
    
    def set(self, question: str, sql_query: str, explanation: str = ""):
        """
        Add a new entry to the cache.
        
        Args:
            question: User's question
            sql_query: Generated SQL
            explanation: Generated explanation
        """
        try:
            self.db_manager.add_documents(
                table_name=self.TABLE_NAME,
                documents=[question],
                metadata=[{
                    "sql_query": sql_query,
                    "explanation": explanation,
                    "cached_at": datetime.now().isoformat()
                }]
            )
            logger.info(f"Cached query: '{question}'")
            
        except Exception as e:
            logger.error(f"Failed to cache query: {e}")

# Singleton accessor
def get_semantic_cache() -> SemanticCache:
    return SemanticCache()
