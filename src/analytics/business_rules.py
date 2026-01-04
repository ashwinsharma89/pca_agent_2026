
from typing import Dict, Any, List

class BusinessRules:
    """
    Marketing business logic and thresholds.
    """
    
    # Benchmarks (can be dynamic later)
    THRESHOLDS = {
        'ctr': {'low': 0.5, 'high': 1.5},  # %
        'roas': {'low': 1.0, 'high': 4.0}, # x
        'cpc': {'high': 5.0}              # $
    }
    
    @staticmethod
    def evaluate_performance(metrics: Dict[str, float]) -> Dict[str, str]:
        """
        Evaluate performance against benchmarks.
        Returns a dictionary of status labels (e.g., 'good', 'poor', 'average').
        """
        status = {}
        
        # CTR Evaluation
        if 'ctr' in metrics:
            ctr = metrics['ctr']
            if ctr < BusinessRules.THRESHOLDS['ctr']['low']:
                status['ctr'] = 'poor'
            elif ctr > BusinessRules.THRESHOLDS['ctr']['high']:
                status['ctr'] = 'good'
            else:
                status['ctr'] = 'average'
                
        # ROAS Evaluation
        if 'roas' in metrics:
            roas = metrics['roas']
            if roas < BusinessRules.THRESHOLDS['roas']['low']:
                status['roas'] = 'critical'
            elif roas > BusinessRules.THRESHOLDS['roas']['high']:
                status['roas'] = 'excellent'
            else:
                status['roas'] = 'good'
                
        return status

    @staticmethod
    def is_significant(spend: float, total_spend: float) -> bool:
        """Filter out insignificant entities (less than 1% of spend)."""
        if total_spend == 0:
            return False
        return (spend / total_spend) > 0.01
