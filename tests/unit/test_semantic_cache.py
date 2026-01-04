"""
Tests for Semantic Cache

Verifies:
- Cache hits for similar questions
- Cache misses for different questions
- Cache insertion
"""

import pytest
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np
from src.intelligence.semantic_cache import SemanticCache, get_semantic_cache
from src.intelligence.lancedb_manager import LanceDBManager

TEST_DB_PATH = Path("data/test_semantic_cache_db")

@pytest.fixture
def mock_semantic_cache():
    """Fixture for SemanticCache with test path."""
    if TEST_DB_PATH.exists():
        shutil.rmtree(TEST_DB_PATH)
    
    # Mock LanceDBManager to use test path
    with patch("src.intelligence.lancedb_manager.DB_PATH", TEST_DB_PATH):
        # Also need to mock SentenceTransformer inside LanceDBManager
        with patch("src.intelligence.lancedb_manager.SentenceTransformer") as mock_model_cls:
            mock_model = Mock()
            # Mock encode to return different vectors for different inputs to test similarity
            def mock_encode(text):
                if isinstance(text, list):
                    return np.array([mock_encode(t) for t in text])
                # Simple deterministic vector generation based on string length/content
                val = 0.1 if "spend" in text.lower() else 0.9
                return np.array([val] * 384)
            
            mock_model.encode.side_effect = mock_encode
            mock_model_cls.return_value = mock_model
            
            # Initialize manager with TEST_DB_PATH
            manager = LanceDBManager(db_path=TEST_DB_PATH)
            
            # Inject manager
            cache = SemanticCache(db_manager=manager)
            yield cache
            
            if TEST_DB_PATH.exists():
                shutil.rmtree(TEST_DB_PATH)
            LanceDBManager._instance = None

def test_cache_miss_initially(mock_semantic_cache):
    """Test cache miss when empty."""
    result = mock_semantic_cache.get("How much spend?")
    assert result is None

def test_cache_set_and_hit(mock_semantic_cache):
    """Test setting cache and retrieving it."""
    question = "What is the total spend?"
    sql = "SELECT SUM(spend) FROM campaigns"
    
    mock_semantic_cache.set(question, sql)
    
    # Exact match hit
    result = mock_semantic_cache.get(question)
    assert result is not None
    assert result['sql'] == sql
    assert result['similarity'] >= 0.95

def test_semantic_hit(mock_semantic_cache):
    """Test semantic similarity hit."""
    # "Total spend?" and "How much spend?" should have similar vectors in our mock
    # because both contain "spend" (mock vector [0.1...])
    
    mock_semantic_cache.set("Total spend?", "SELECT sum from table")
    
    # Should hit because "How much spend?" also generates [0.1...] vector
    # resulting in score 1.0 (perfect match in this simple mock)
    result = mock_semantic_cache.get("How much spend?")
    
    assert result is not None
    assert result['original_question'] == "Total spend?"

def test_cache_miss_different_topic(mock_semantic_cache):
    """Test cache miss for different topic."""
    mock_semantic_cache.set("Total spend?", "SELECT sum...")
    
    # "Impressions?" -> contains "impressions", not "spend" -> mock val 0.9
    # Vector distance will be large -> low score
    result = mock_semantic_cache.get("Count impressions?")
    
    assert result is None
