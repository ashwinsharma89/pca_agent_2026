import os
import sys
import pandas as pd
import numpy as np
from loguru import logger

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.query_engine.nl_to_sql import NaturalLanguageQueryEngine

def verify_integration():
    logger.info("=== Verifying Phase 3 Integration ===")
    
    # 1. Initialize Engine
    engine = NaturalLanguageQueryEngine(api_key="fake_key_for_test")
    logger.info("Engine initialized successfully")
    
    # Verify components are present
    assert hasattr(engine, 'schema_manager'), "SchemaManager missing"
    assert hasattr(engine, 'prompt_builder'), "PromptBuilder missing"
    assert hasattr(engine, 'executor'), "QueryExecutor missing"
    assert hasattr(engine, 'cache'), "SemanticCache missing"
    logger.info("Modular components verified")
    
    # 2. Load Data
    data = {
        "Campaign_Name": ["Campaign A", "Campaign B", "Campaign C"],
        "Date": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "Spend": [1000, 2000, 1500],
        "Impressions": [10000, 25000, 18000],
        "Clicks": [500, 1000, 800],
        "Conversions": [50, 80, 60]
    }
    df = pd.DataFrame(data)
    engine.load_data(df)
    logger.info("Data loaded successfully")
    
    # Verify SchemaManager extracted schema
    assert engine.schema_info is not None
    assert engine.schema_info['row_count'] == 3
    logger.info(f"Schema extracted: {engine.schema_info['columns']}")
    
    # 3. Verify Cache Integration Logic (Mocking behavior)
    # We will manually set a cache entry and see if generate_sql uses it
    
    # Mock cache.get to return a preset SQL query
    original_get = engine.cache.get
    
    test_question = "What is the total spend?"
    test_sql = "SELECT SUM(Spend) FROM campaigns"
    
    # Inject a hit into the real cache (if accessible) or mock it
    # We'll just define a mock side_effect
    def mock_get(question):
        if question == test_question:
            return {'sql': test_sql, 'explanation': 'Cached result'}
        return None
        
    engine.cache.get = mock_get
    
    # Call generate_sql
    logger.info(f"Testing Cache Hit for: {test_question}")
    generated_sql = engine.generate_sql(test_question)
    
    if generated_sql == test_sql:
        logger.info("✅ SUCCESS: generate_sql returned cached SQL")
    else:
        logger.error(f"❌ FAILURE: generate_sql returned {generated_sql} instead of {test_sql}")
        
    # Restore cache
    engine.cache.get = original_get
    
    # 4. Verify Prompt Builder (Mocking build)
    # We want to ensure prompt_builder.build is called if no cache hit
    original_build = engine.prompt_builder.build
    
    built_prompt = []
    def mock_build(question):
        built_prompt.append(question)
        return "SELECT * FROM campaigns" # Dummy prompt return? No, build returns prompt string
    
    engine.prompt_builder.build = mock_build
    
    # We also need to mock LLM execution to avoid API calls
    # Or rely on the 'invalid/dummy query' error handling if we return junk prompt
    # Let's mock the LLM client call or just ensure build is called before failure
    
    try:
        engine.generate_sql("New unique question")
    except Exception as e:
        logger.info(f"Expected error from LLM call (since we didn't mock LLM): {e}")
        
    if built_prompt and "New unique question" in built_prompt:
        logger.info("✅ SUCCESS: PromptBuilder.build() was called")
    else:
        logger.error("❌ FAILURE: PromptBuilder.build() was NOT called")
        
    # 5. Verify Executor Integration
    # Call execute_query with valid SQL
    logger.info("Testing execution...")
    result_df = engine.execute_query("SELECT SUM(Spend) as total FROM campaigns")
    
    if not result_df.empty and result_df.iloc[0]['total'] == 4500:
        logger.info(f"✅ SUCCESS: Execution returned correct result: {result_df.iloc[0]['total']}")
    else:
        logger.error(f"❌ FAILURE: Execution returned {result_df}")

    logger.info("=== Verification Complete ===")

if __name__ == "__main__":
    verify_integration()
