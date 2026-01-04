
from typing import List, Dict, Any
from .business_rules import BusinessRules

class RecommendationEngine:
    """
    Advisor class that generates specific marketing recommendations.
    """
    
    @staticmethod
    def generate_recommendations(metrics: Dict[str, float], status: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Generate a list of recommendations based on performance status.
        """
        recs = []
        
        # ROAS Analysis
        if status.get('roas') == 'critical':
            recs.append({
                'type': 'budget_cut',
                'severity': 'high',
                'message': f"Critical ROAS ({metrics.get('roas', 0):.2f}). Immediate budget reduction recommended.",
                'action': 'Reduce daily budget by 50%'
            })
        elif status.get('roas') == 'excellent':
            recs.append({
                'type': 'budget_increase',
                'severity': 'medium',
                'message': f"Excellent ROAS ({metrics.get('roas', 0):.2f}). Opportunity to scale.",
                'action': 'Increase daily budget by 20% to test saturation'
            })
            
        # CTR Analysis
        if status.get('ctr') == 'poor':
            recs.append({
                'type': 'creative_refresh',
                'severity': 'medium',
                'message': f"Low CTR ({metrics.get('ctr', 0):.2f}%). Creative fatigue likely.",
                'action': 'Rotate new ad creatives'
            })
            
        return recs

    @staticmethod
    def _format_for_llm(recs: List[Dict[str, Any]]) -> str:
        """Format recommendations for LLM context."""
        return "\n".join([f"- [{r['severity'].upper()}] {r['message']} Action: {r['action']}" for r in recs])
