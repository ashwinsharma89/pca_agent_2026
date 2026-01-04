
import pandas as pd
import sys
import os
sys.path.append(os.getcwd())
from src.analytics.auto_insights import MediaAnalyticsExpert

# Mock Data
data = {
    'Campaign': ['Campaign A', 'Campaign B', 'Campaign C'],
    'Platform': ['Meta', 'Google', 'Meta'],
    'Spend': [1000.0, 5000.0, 200.0],
    'Impressions': [10000, 50000, 2000],
    'Clicks': [100, 500, 20],
    'Conversions': [10, 50, 2],
    'Revenue': [5000.0, 20000.0, 1000.0],
    'ROAS': [5.0, 4.0, 5.0]
}
df = pd.DataFrame(data)

print("🚀 Initializing Refactored Expert...")
expert = MediaAnalyticsExpert()

print("📊 Running Analysis...")
try:
    results = expert.analyze_all(df)
    print("✅ Analysis Complete!")
    print("\nKeys returned:", list(results.keys()))
    
    print("\nMetrics Overview:")
    print(results['metrics']['overview'])
    
    print("\nBy Platform:")
    print(results['metrics'].get('by_platform'))
    
    if results['executive_summary']:
        print("\nNarrative generated (Mock/Real):")
        print(results['executive_summary'][:100] + "...")
    else:
        print("\n⚠️ No narrative generated")
        
except Exception as e:
    print(f"❌ Analysis Failed: {e}")
    import traceback
    traceback.print_exc()
