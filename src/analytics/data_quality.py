"""
Data Quality Engine for Campaign Analysis.
Provides transparency into data completeness and confidence levels before AI analysis.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from src.api.v1.models import PCAAnalysisInput, AttributionSettings

class DataQualityAnalyzer:
    """Analyzes campaign data quality and generates transparency reports."""
    
    @staticmethod
    def validate_input(df: pd.DataFrame, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Validate dataframe against required schema and logical constraints.
        """
        warnings = []
        missing_optional = []
        
        # 1. Check Completeness
        has_revenue = 'ROAS' in df.columns or ('Spend' in df.columns and 'Revenue' in df.columns)
        if not has_revenue:
            warnings.append("Revenue/ROAS data missing - falling back to Efficiency (CPA/CPR) focus")
            missing_optional.append("Revenue/ROAS Columns")

        has_funnel = all(col in df.columns for col in ['Impressions', 'Clicks', 'Conversions'])
        if not has_funnel:
            warnings.append("Full funnel data incomplete - Conversion Rate analysis may be limited")
            missing_optional.append("Impressions/Clicks for Funnel")
            
        has_historical = False # Default unless detected
        
        # 2. Check Sample Size
        sample_size = len(df)
        if sample_size < 50:
            warnings.append(f"Small sample size ({sample_size} rows) - statistical significance low")
            
        # 3. Check Dimensions
        platforms = df['Platform'].unique().tolist() if 'Platform' in df.columns else []
        if not platforms:
            warnings.append("No Platform column found - cross-channel comparison impossible")
            
        # 4. Calculate Score
        score = 100
        if not has_revenue: score -= 30
        if not has_funnel: score -= 20
        if sample_size < 100: score -= 10
        if not platforms: score -= 20
        
        return {
            "completeness_score": max(0, score),
            "warnings": warnings,
            "missing_optional_fields": missing_optional,
            "has_revenue": has_revenue,
            "has_funnel": has_funnel,
            "has_historical": has_historical,
            "sample_size": sample_size,
            "platforms": platforms
        }

def generate_data_quality_report(df: pd.DataFrame, context: Optional[Dict] = None) -> str:
    """Generate human-readable data quality report string for LLM context."""
    
    # Run validation
    validation = DataQualityAnalyzer.validate_input(df, context)
    
    # Context extraction
    campaign_name = context.get('campaign_name', 'Global Campaign') if context else 'Global Campaign'
    attribution = context.get('attribution_model', 'Not specified') if context else 'Not specified'
    
    # Build Report
    report = f"""
# Data Quality Report - {campaign_name}

## Overall Completeness: {validation['completeness_score']}/100

### ✅ Available Data:
- {len(validation['platforms'])} platforms detected: {', '.join(validation['platforms'][:3])}{'...' if len(validation['platforms']) > 3 else ''}
- {validation['sample_size']:,} data rows analyzed
- Funnel data: {'Yes' if validation['has_funnel'] else 'No'}
- Revenue tracking: {'Yes' if validation['has_revenue'] else 'No'}
- Attribution model: {attribution}

### ⚠️  Limitations:
"""
    
    if validation['warnings']:
        for warning in validation['warnings']:
            report += f"- {warning}\n"
    else:
        report += "- None detected. Data is robust.\n"
    
    report += "\n### 📊 Missing Optional Fields:\n"
    if validation['missing_optional_fields']:
        for field in validation['missing_optional_fields']:
            report += f"- {field}\n"
    else:
        report += "- All key fields present.\n"
    
    # Confidence Level
    confidence = 'HIGH' if validation['completeness_score'] >= 80 else \
                 'MEDIUM' if validation['completeness_score'] >= 60 else 'LOW'
                 
    report += f"""
### 🎯 Analysis Confidence: {confidence} (Score: {validation['completeness_score']}/100)
Based on data completeness and sample size.

### 💡 Recommendations to Improve Data Quality:
"""
    
    if not validation['has_funnel']:
        report += "- Track Impressions and Clicks to enable full funnel conversion rate analysis\n"
    if not validation['has_revenue']:
        report += "- Implement Revenue/Value tracking to enable ROAS and LTV analysis\n"
    if validation['sample_size'] < 100:
        report += "- Aggregate more historical data to improve statistical significance\n"
        
    return report
