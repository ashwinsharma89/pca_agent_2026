"""
Test suite for SQL Agent improvements.
Tests daily CTR trend, average CTR calculation, and security filter.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.query_engine.nl_to_sql import NaturalLanguageQueryEngine
from src.query_engine.safe_query import SafeQueryExecutor, SQLInjectionError


def create_agent():
    """Create a test agent instance."""
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        # Try to load from .env file
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    
    return NaturalLanguageQueryEngine(api_key=api_key)


def test_daily_ctr_trend(agent):
    """Test: Daily CTR trend - should use daily granularity"""
    question = "What's our daily CTR trend for the last month?"
    print(f"\n📝 Question: {question}")
    
    result = agent.ask(question)
    sql = result.get('sql', '')
    print(f"📊 Generated SQL:\n{sql[:500]}...")
    
    # Assertions
    errors = []
    
    # Should be daily, not weekly
    if 'DATE_TRUNC' in sql and 'week' in sql.lower() and 'day' not in sql.lower():
        errors.append("Should be daily, not weekly")
    
    # Should calculate CTR
    if not ('CTR' in sql.upper() or ('Clicks' in sql and 'Impressions' in sql)):
        errors.append("Should calculate CTR (Clicks/Impressions)")
    
    # Should have time filter
    if 'WHERE' not in sql.upper():
        errors.append("Should have time filter (WHERE clause)")
    
    # Should group by date
    if 'GROUP BY' not in sql.upper():
        errors.append("Should group by date")
    
    if errors:
        print(f"❌ Daily CTR trend test FAILED:")
        for e in errors:
            print(f"   - {e}")
        return False
    else:
        print("✅ Daily CTR trend test PASSED")
        return True


def test_average_ctr(agent):
    """Test: Average CTR calculation - should NOT use AVG on calculated metric"""
    question = "What's the average CTR?"
    print(f"\n📝 Question: {question}")
    
    result = agent.ask(question)
    sql = result.get('sql', '')
    print(f"📊 Generated SQL:\n{sql[:500]}...")
    
    errors = []
    
    # Should use SUM, not AVG
    if 'SUM(' not in sql.upper() and 'AVG(CTR)' in sql.upper():
        errors.append("Should use SUM, not AVG on calculated metric")
    
    # Should handle division by zero
    if 'NULLIF' not in sql.upper() and '/' in sql:
        errors.append("Should handle division by zero with NULLIF")
    
    if errors:
        print(f"❌ Average CTR test FAILED:")
        for e in errors:
            print(f"   - {e}")
        return False
    else:
        print("✅ Average CTR test PASSED")
        return True


def test_underperforming_campaigns(agent):
    """Test: Recently underperforming campaigns - security filter should NOT block valid SQL"""
    question = "Show me recently underperforming campaigns"
    print(f"\n📝 Question: {question}")
    
    try:
        result = agent.ask(question)
        sql = result.get('sql', '')
        error = result.get('error', '')
        
        if error:
            if 'token detected' in error.lower():
                print(f"❌ Security filter too aggressive - blocks valid SQL")
                print(f"   Error: {error}")
                return False
            else:
                print(f"⚠️ Query had error but not security related: {error[:100]}")
        
        print(f"📊 Generated SQL:\n{sql[:500] if sql else 'No SQL generated'}...")
        print("✅ Security filter allows valid SQL")
        return True
        
    except SQLInjectionError as e:
        if 'token detected' in str(e).lower():
            print(f"❌ Security filter too aggressive - blocks valid SQL")
            print(f"   Error: {e}")
            return False
        raise
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return False


def test_security_blocks_dangerous(agent):
    """Test: Security filter should block dangerous SQL"""
    dangerous_queries = [
        "DROP TABLE campaigns",
        "SELECT * FROM campaigns; DELETE FROM users;",
    ]
    
    print(f"\n📝 Testing security blocks dangerous operations...")
    
    all_blocked = True
    for query in dangerous_queries:
        try:
            # Try to validate directly
            SafeQueryExecutor.validate_query_against_schema(
                query, ['campaigns', 'all_campaigns'], ['Date', 'CTR']
            )
            print(f"❌ Should have blocked: {query[:50]}")
            all_blocked = False
        except SQLInjectionError:
            print(f"✅ Correctly blocked: {query[:50]}")
    
    return all_blocked


def main():
    print("=" * 60)
    print("SQL Agent Improvement Tests")
    print("=" * 60)
    
    agent = create_agent()
    
    results = {
        "daily_ctr_trend": test_daily_ctr_trend(agent),
        "average_ctr": test_average_ctr(agent),
        "underperforming_campaigns": test_underperforming_campaigns(agent),
        "security_blocks_dangerous": test_security_blocks_dangerous(agent),
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit(main())
