"""
Recommendation Validator Module.
Validates recommendations for feasibility, consistency, and potential risks.
"""
from typing import Dict, List, Any
from loguru import logger


class RecommendationValidator:
    """Validate recommendations before presenting to users."""
    
    def __init__(self):
        self.max_budget_increase = 0.50  # Max 50% increase
        self.min_data_days = 7  # Minimum days of data for confident recommendations
    
    def validate_recommendation(
        self,
        recommendation: str,
        metrics: Dict[str, Any],
        campaign_context: Dict[str, Any],
        rag_context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of a recommendation.
        
        Args:
            recommendation: The recommendation text
            metrics: Campaign metrics
            campaign_context: Campaign goals, constraints, priorities
            rag_context: Retrieved knowledge chunks
            
        Returns:
            Validation result with feasibility, risks, and warnings
        """
        
        validation_result = {
            'is_valid': True,
            'feasibility_score': 1.0,
            'risks': [],
            'warnings': [],
            'suggestions': []
        }
        
        # Check 1: Feasibility
        feasibility = self._check_feasibility(recommendation, metrics, campaign_context)
        validation_result['feasibility_score'] = feasibility['score']
        if not feasibility['is_feasible']:
            validation_result['is_valid'] = False
            validation_result['warnings'].append(feasibility['reason'])
        
        # Check 2: Consistency with best practices
        consistency = self._check_consistency(recommendation, rag_context, metrics)
        if consistency['has_contradictions']:
            validation_result['warnings'].extend(consistency['contradictions'])
        
        # Check 3: Risk assessment
        risks = self._assess_risks(recommendation, metrics, campaign_context)
        validation_result['risks'] = risks
        
        # Check 4: Data sufficiency
        data_check = self._check_data_sufficiency(recommendation, metrics)
        if not data_check['sufficient']:
            validation_result['warnings'].append(data_check['warning'])
        
        # Generate improvement suggestions
        if validation_result['warnings'] or validation_result['risks']:
            validation_result['suggestions'] = self._generate_suggestions(
                recommendation, validation_result
            )
        
        return validation_result
    
    def _check_feasibility(
        self,
        recommendation: str,
        metrics: Dict[str, Any],
        campaign_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if recommendation is feasible given current constraints."""
        
        rec_lower = recommendation.lower()
        overview = metrics.get('overview', {})
        constraints = campaign_context.get('constraints', {})
        
        # Check budget feasibility
        if 'increase budget' in rec_lower or 'scale' in rec_lower:
            budget_info = constraints.get('budget', {})
            current_spend = budget_info.get('current_spend', 0)
            total_budget = budget_info.get('total_budget', current_spend * 1.2)
            remaining = total_budget - current_spend
            
            # Extract percentage if mentioned
            import re
            pct_match = re.search(r'(\d+)\s*(?:%|percent)', rec_lower)
            if pct_match:
                increase_pct = int(pct_match.group(1)) / 100.0
                required_budget = current_spend * increase_pct
                
                if required_budget > remaining:
                    return {
                        'is_feasible': False,
                        'score': 0.3,
                        'reason': f"Budget constraint: Recommendation requires ${required_budget:,.0f} but only ${remaining:,.0f} available"
                    }
                elif required_budget > remaining * 0.8:
                    return {
                        'is_feasible': True,
                        'score': 0.6,
                        'reason': f"Tight budget: Uses {required_budget/remaining*100:.0f}% of remaining budget"
                    }
        
        # Check protected channels
        if isinstance(constraints, dict):
            protected = constraints.get('protected_channels', [])
        else:
            protected = []  # constraints is a list, not dict - skip complex lookup
        if protected:
            for channel_info in protected:
                channel = channel_info['platform']
                if channel.lower() in rec_lower and ('pause' in rec_lower or 'reduce' in rec_lower):
                    return {
                        'is_feasible': False,
                        'score': 0.2,
                        'reason': f"Cannot pause/reduce {channel}: Protected channel ({channel_info['reason']})"
                    }
        
        # Check performance thresholds
        if isinstance(constraints, dict):
            thresholds = constraints.get('performance_thresholds', {})
        else:
            thresholds = {}  # constraints is a list, skip threshold lookup
        if 'scale' in rec_lower or 'increase' in rec_lower:
            # Extract platform name
            platform_metrics = metrics.get('by_platform', {})
            for platform, data in platform_metrics.items():
                if platform.lower() in rec_lower:
                    roas = data.get('ROAS', data.get('roas', 0))
                    cpa = data.get('CPA', data.get('cpa', 0))
                    
                    min_roas = thresholds.get('min_roas', 2.0)
                    max_cpa = thresholds.get('max_cpa', 50.0)
                    
                    if roas > 0 and roas < min_roas:
                        return {
                            'is_feasible': True,
                            'score': 0.5,
                            'reason': f"Risk: {platform} ROAS ({roas:.1f}x) below threshold ({min_roas}x)"
                        }
                    
                    if cpa > max_cpa:
                        return {
                            'is_feasible': True,
                            'score': 0.5,
                            'reason': f"Risk: {platform} CPA (${cpa:.2f}) above threshold (${max_cpa})"
                        }
        
        return {
            'is_feasible': True,
            'score': 1.0,
            'reason': 'Recommendation is feasible'
        }
    
    def _check_consistency(
        self,
        recommendation: str,
        rag_context: List[Dict],
        metrics: Dict
    ) -> Dict[str, Any]:
        """Check for contradictions with best practices or current performance."""
        
        contradictions = []
        rec_lower = recommendation.lower()
        
        # Check against knowledge base
        for chunk in rag_context:
            content = chunk.get('content', '').lower()
            
            # Contradiction: Recommending to scale underperformer
            if 'scale' in rec_lower or 'increase' in rec_lower:
                if any(word in content for word in ['underperform', 'inefficient', 'poor performance']):
                    # Check if same platform mentioned
                    platforms = ['dis', 'soc', 'search', 'display', 'social']
                    for platform in platforms:
                        if platform in rec_lower and platform in content:
                            contradictions.append(
                                f"Potential contradiction: Recommending to scale {platform.upper()} "
                                f"but knowledge base indicates underperformance"
                            )
            
            # Contradiction: Recommending to pause high performer
            if 'pause' in rec_lower or 'reduce' in rec_lower:
                if any(word in content for word in ['high roas', 'top performer', 'strong performance']):
                    platforms = ['dis', 'soc', 'search', 'display', 'social']
                    for platform in platforms:
                        if platform in rec_lower and platform in content:
                            contradictions.append(
                                f"Potential contradiction: Recommending to reduce {platform.upper()} "
                                f"but knowledge base indicates strong performance"
                            )
        
        # Check against actual performance
        platform_metrics = metrics.get('by_platform', {})
        for platform, data in platform_metrics.items():
            if platform.lower() in rec_lower:
                roas = data.get('ROAS', data.get('roas', 0))
                cpa = data.get('CPA', data.get('cpa', 0))
                
                # Contradiction: Scaling poor performer
                if ('scale' in rec_lower or 'increase' in rec_lower):
                    if roas > 0 and roas < 2.0:
                        contradictions.append(
                            f"Performance concern: Recommending to scale {platform} with low ROAS ({roas:.1f}x)"
                        )
                    if cpa > 50:
                        contradictions.append(
                            f"Performance concern: Recommending to scale {platform} with high CPA (${cpa:.2f})"
                        )
                
                # Contradiction: Pausing good performer
                if ('pause' in rec_lower or 'reduce' in rec_lower):
                    if roas >= 3.0:
                        contradictions.append(
                            f"Performance concern: Recommending to reduce {platform} with strong ROAS ({roas:.1f}x)"
                        )
        
        return {
            'has_contradictions': len(contradictions) > 0,
            'contradictions': contradictions
        }
    
    def _assess_risks(
        self,
        recommendation: str,
        metrics: Dict,
        campaign_context: Dict
    ) -> List[Dict[str, Any]]:
        """Assess potential risks of implementing the recommendation."""
        
        risks = []
        rec_lower = recommendation.lower()
        
        # Risk 1: Large budget changes
        import re
        pct_match = re.search(r'(\d+)\s*(?:%|percent)', rec_lower)
        if pct_match:
            change_pct = int(pct_match.group(1))
            if change_pct >= 50:
                risks.append({
                    'type': 'high_impact',
                    'severity': 'high',
                    'description': f'Large budget change ({change_pct}%) may cause instability',
                    'mitigation': 'Consider gradual increase (10-20% per week)'
                })
            elif change_pct >= 30:
                risks.append({
                    'type': 'medium_impact',
                    'severity': 'medium',
                    'description': f'Moderate budget change ({change_pct}%) requires monitoring',
                    'mitigation': 'Monitor daily for first week'
                })
        
        # Risk 2: Pausing channels
        if 'pause' in rec_lower:
            risks.append({
                'type': 'channel_pause',
                'severity': 'medium',
                'description': 'Pausing channel will lose historical data and learning',
                'mitigation': 'Consider reducing budget first before full pause'
            })
        
        # Risk 3: Limited data
        overview = metrics.get('overview', {})
        # Simplified - in production, check actual date range
        if 'test' in rec_lower or 'new' in rec_lower:
            risks.append({
                'type': 'insufficient_data',
                'severity': 'low',
                'description': 'Testing new strategies requires monitoring period',
                'mitigation': 'Run test for at least 2 weeks before scaling'
            })
        
        # Risk 4: Campaign stage mismatch
        stage = campaign_context.get('stage', {}).get('stage', 'unknown')
        if stage == 'testing' and ('scale' in rec_lower or 'increase budget' in rec_lower):
            risks.append({
                'type': 'premature_scaling',
                'severity': 'high',
                'description': 'Scaling during testing phase may waste budget',
                'mitigation': 'Complete optimization phase first'
            })
        
        return risks
    
    def _check_data_sufficiency(
        self,
        recommendation: str,
        metrics: Dict
    ) -> Dict[str, Any]:
        """Check if there's sufficient data to support the recommendation."""
        
        overview = metrics.get('overview', {})
        total_conversions = overview.get('total_conversions', 0)
        total_spend = overview.get('total_spend', 0)
        
        # Check for minimum data
        if total_spend < 1000:
            return {
                'sufficient': False,
                'warning': 'Limited spend data (< $1,000) - recommendations may not be reliable'
            }
        
        if total_conversions < 50 and 'cpa' in recommendation.lower():
            return {
                'sufficient': False,
                'warning': 'Limited conversion data (< 50) - CPA-based recommendations may be unreliable'
            }
        
        return {
            'sufficient': True,
            'warning': None
        }
    
    def _generate_suggestions(
        self,
        recommendation: str,
        validation_result: Dict
    ) -> List[str]:
        """Generate suggestions to improve the recommendation."""
        
        suggestions = []
        
        # If feasibility is low, suggest alternatives
        if validation_result['feasibility_score'] < 0.7:
            suggestions.append("Consider a more gradual approach with smaller budget changes")
        
        # If there are risks, suggest mitigation
        if validation_result['risks']:
            high_risk_count = sum(1 for r in validation_result['risks'] if r['severity'] == 'high')
            if high_risk_count > 0:
                suggestions.append("High risk detected - implement in phases with close monitoring")
        
        # If there are contradictions, suggest validation
        if validation_result['warnings']:
            suggestions.append("Validate recommendation with additional data or A/B testing")
        
        return suggestions


def validate_recommendations_batch(
    recommendations: List[str],
    metrics: Dict[str, Any],
    campaign_context: Dict[str, Any],
    rag_context: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Validate a batch of recommendations.
    
    Returns:
        List of validation results, one per recommendation
    """
    validator = RecommendationValidator()
    results = []
    
    for rec in recommendations:
        validation = validator.validate_recommendation(
            rec, metrics, campaign_context, rag_context
        )
        results.append({
            'recommendation': rec,
            'validation': validation
        })
    
    return results
