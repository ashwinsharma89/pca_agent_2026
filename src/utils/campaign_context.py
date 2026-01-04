"""
Campaign Context Understanding Module.
Extracts business goals, constraints, and priorities from campaign data.
"""
import traceback
from typing import Dict, List, Any
from loguru import logger


class CampaignContextAnalyzer:
    """Analyze campaign context to understand business goals and constraints."""
    
    def __init__(self):
        self.default_min_roas = 2.0
        self.default_max_cpa = 50.0
    
    def analyze_context(self, metrics: Dict[str, Any], user_input: str = None) -> Dict[str, Any]:
        """
        Extract campaign context including goals, constraints, and priorities.
        
        Args:
            metrics: Campaign performance metrics
            user_input: Optional user-provided context (future enhancement)
            
        Returns:
            Dictionary with goals, constraints, priorities, and insights
        """
        try:
            logger.info(f"Analyzing context with metrics keys: {list(metrics.keys())}")
            
            overview = metrics.get('overview', {})
            logger.info(f"Overview type: {type(overview)}")
            if not isinstance(overview, dict):
                logger.error(f"Overview is not a dict! Value: {overview}")
                # Fallback
                overview = {}

            platform_metrics = metrics.get('by_platform', {})
            logger.info(f"Platform metrics type: {type(platform_metrics)}")

        
            # Extract goals
            goals = self._extract_goals(overview, platform_metrics)
            
            # Extract constraints
            constraints = self._extract_constraints(overview, platform_metrics)
            
            # Extract priorities
            priorities = self._extract_priorities(overview, platform_metrics)
            
            # Identify campaign stage
            stage = self._identify_campaign_stage(overview)
            
            # Generate context summary
            context_summary = self._generate_context_summary(goals, constraints, priorities, stage)
            
            return {
                'goals': goals,
                'constraints': constraints,
                'priorities': priorities,
                'stage': stage,
                'summary': context_summary,
                'recommendations_filter': self._build_recommendations_filter(goals, constraints)
            }
        
        except Exception as e:
            logger.error(f"Context analysis failed: {str(e)}")
            logger.error(traceback.format_exc())
            # Return safe default
            return {
                'goals': [],
                'constraints': {},
                'priorities': [],
                'stage': {'stage': 'unknown', 'description': 'Analysis failed'},
                'summary': 'Context analysis failed',
                'recommendations_filter': {}
            }
    
    def _extract_goals(self, overview: Dict, platform_metrics: Dict) -> List[Dict[str, Any]]:
        """Infer campaign goals from performance data."""
        goals = []
        
        avg_cpa = overview.get('avg_cpa', overview.get('overall_cpa', 0))
        avg_roas = overview.get('avg_roas', overview.get('overall_roas', 0))
        total_spend = overview.get('total_spend', 0)
        total_conversions = overview.get('total_conversions', 0)
        
        # Goal 1: CPA optimization (if CPA is high)
        if avg_cpa > 0:
            if avg_cpa > 40:
                goals.append({
                    'type': 'efficiency',
                    'metric': 'CPA',
                    'target': 'reduce',
                    'current_value': avg_cpa,
                    'target_value': 30,
                    'priority': 'high',
                    'description': f"Reduce CPA from ${avg_cpa:.2f} to $30 (33% improvement needed)"
                })
            elif avg_cpa > 25:
                goals.append({
                    'type': 'efficiency',
                    'metric': 'CPA',
                    'target': 'maintain',
                    'current_value': avg_cpa,
                    'priority': 'medium',
                    'description': f"Maintain CPA at ${avg_cpa:.2f} while scaling"
                })
        
        # Goal 2: ROAS optimization (if ROAS data available)
        if avg_roas > 0:
            if avg_roas < 2.0:
                goals.append({
                    'type': 'efficiency',
                    'metric': 'ROAS',
                    'target': 'increase',
                    'current_value': avg_roas,
                    'target_value': 3.0,
                    'priority': 'high',
                    'description': f"Increase ROAS from {avg_roas:.1f}x to 3.0x"
                })
            elif avg_roas >= 3.0:
                goals.append({
                    'type': 'growth',
                    'metric': 'ROAS',
                    'target': 'scale',
                    'current_value': avg_roas,
                    'priority': 'high',
                    'description': f"Scale campaigns while maintaining {avg_roas:.1f}x ROAS"
                })
        
        # Goal 3: Volume goals (if conversions are healthy)
        if total_conversions > 0 and avg_cpa > 0 and avg_cpa < 40:
            goals.append({
                'type': 'growth',
                'metric': 'conversions',
                'target': 'increase',
                'current_value': total_conversions,
                'target_value': int(total_conversions * 1.3),
                'priority': 'medium',
                'description': f"Increase conversions from {total_conversions:,} to {int(total_conversions * 1.3):,} (+30%)"
            })
        
        # Goal 4: Budget efficiency
        if total_spend > 0:
            goals.append({
                'type': 'efficiency',
                'metric': 'budget_allocation',
                'target': 'optimize',
                'priority': 'medium',
                'description': "Optimize budget allocation across channels for maximum ROI"
            })
        
        return goals
    
    def _extract_constraints(self, overview: Dict, platform_metrics: Dict) -> Dict[str, Any]:
        """Identify campaign constraints."""
        
        total_spend = overview.get('total_spend', 0)
        total_budget = total_spend * 1.2  # Assume 20% headroom
        
        constraints = {
            'budget': {
                'total_budget': total_budget,
                'current_spend': total_spend,
                'remaining': total_budget - total_spend,
                'utilization': (total_spend / total_budget * 100) if total_budget > 0 else 0
            },
            'performance_thresholds': {
                'min_roas': self.default_min_roas,
                'max_cpa': self.default_max_cpa,
                'min_ctr': 0.1  # 0.1% minimum CTR
            },
            'protected_channels': [],  # Channels that cannot be paused
            'scaling_limits': {
                'max_daily_budget_increase': 0.20,  # Max 20% daily increase
                'max_weekly_budget_increase': 0.50   # Max 50% weekly increase
            }
        }
        
        # Identify protected channels (high performers)
        for platform, data in platform_metrics.items():
            roas = data.get('ROAS', data.get('roas', 0))
            spend_share = data.get('spend', 0) / total_spend if total_spend > 0 else 0
            
            # Protect high ROAS channels or major spend channels
            if roas >= 3.0 or spend_share >= 0.3:
                constraints['protected_channels'].append({
                    'platform': platform,
                    'reason': 'high_roas' if roas >= 3.0 else 'major_spend_channel'
                })
        
        return constraints
    
    def _extract_priorities(self, overview: Dict, platform_metrics: Dict) -> List[Dict[str, Any]]:
        """Determine campaign priorities based on performance."""
        priorities = []
        
        avg_cpa = overview.get('avg_cpa', overview.get('overall_cpa', 0))
        avg_roas = overview.get('avg_roas', overview.get('overall_roas', 0))
        
        # Priority 1: Fix critical issues
        if avg_cpa > 50:
            priorities.append({
                'priority': 1,
                'category': 'critical_fix',
                'description': 'Reduce high CPA immediately',
                'urgency': 'immediate'
            })
        
        if avg_roas > 0 and avg_roas < 1.5:
            priorities.append({
                'priority': 1,
                'category': 'critical_fix',
                'description': 'Improve ROAS to profitable levels',
                'urgency': 'immediate'
            })
        
        # Priority 2: Optimize underperformers
        underperforming_platforms = []
        for platform, data in platform_metrics.items():
            cpa = data.get('CPA', data.get('cpa', 0))
            if cpa > avg_cpa * 1.5:
                underperforming_platforms.append(platform)
        
        if underperforming_platforms:
            priorities.append({
                'priority': 2,
                'category': 'optimization',
                'description': f'Optimize underperforming channels: {", ".join(underperforming_platforms)}',
                'urgency': 'high'
            })
        
        # Priority 3: Scale winners
        high_performers = []
        for platform, data in platform_metrics.items():
            roas = data.get('ROAS', data.get('roas', 0))
            if roas >= 3.0:
                high_performers.append(platform)
        
        if high_performers:
            priorities.append({
                'priority': 3,
                'category': 'growth',
                'description': f'Scale high-performing channels: {", ".join(high_performers)}',
                'urgency': 'medium'
            })
        
        return priorities
    
    def _identify_campaign_stage(self, overview: Dict) -> Dict[str, Any]:
        """Identify what stage the campaign is in."""
        
        total_spend = overview.get('total_spend', 0)
        total_conversions = overview.get('total_conversions', 0)
        avg_cpa = overview.get('avg_cpa', overview.get('overall_cpa', 0))
        
        # Determine stage
        if total_spend < 10000:
            stage = 'testing'
            description = 'Early testing phase - focus on learning and optimization'
        elif avg_cpa > 0 and avg_cpa > 40:
            stage = 'optimization'
            description = 'Optimization phase - focus on improving efficiency'
        elif total_conversions > 1000 and avg_cpa > 0 and avg_cpa < 35:
            stage = 'scaling'
            description = 'Scaling phase - focus on growth while maintaining efficiency'
        else:
            stage = 'mature'
            description = 'Mature phase - focus on incremental improvements'
        
        return {
            'stage': stage,
            'description': description,
            'recommended_strategy': self._get_stage_strategy(stage)
        }
    
    def _get_stage_strategy(self, stage: str) -> str:
        """Get recommended strategy for campaign stage."""
        strategies = {
            'testing': 'Test multiple audiences, creatives, and bidding strategies. Gather data before scaling.',
            'optimization': 'Pause underperformers, optimize targeting and creative, improve conversion rates.',
            'scaling': 'Increase budgets on winners, expand to similar audiences, maintain quality thresholds.',
            'mature': 'Incremental testing, refresh creative, explore new channels, maintain performance.'
        }
        return strategies.get(stage, 'Continue monitoring and optimizing')
    
    def _generate_context_summary(
        self,
        goals: List[Dict],
        constraints: Dict,
        priorities: List[Dict],
        stage: Dict
    ) -> str:
        """Generate human-readable context summary."""
        
        summary_parts = []
        
        # Stage
        summary_parts.append(f"Campaign Stage: {stage['stage'].title()} - {stage['description']}")
        
        # Top goals
        if goals:
            top_goals = [g['description'] for g in goals[:2]]
            summary_parts.append(f"Primary Goals: {'; '.join(top_goals)}")
        
        # Key constraints
        budget_info = constraints.get('budget', {})
        if budget_info:
            utilization = budget_info.get('utilization', 0)
            summary_parts.append(f"Budget Utilization: {utilization:.0f}%")
        
        # Top priority
        if priorities:
            top_priority = priorities[0]
            summary_parts.append(f"Top Priority: {top_priority['description']}")
        
        return " | ".join(summary_parts)
    
    def _build_recommendations_filter(self, goals: List[Dict], constraints: Dict) -> Dict[str, Any]:
        """Build filter criteria for recommendations based on context."""
        
        filter_criteria = {
            'focus_metrics': [],
            'avoid_actions': [],
            'preferred_actions': []
        }
        
        # Extract focus metrics from goals
        for goal in goals:
            if goal.get('metric'):
                filter_criteria['focus_metrics'].append(goal['metric'])
        
        # Add constraints-based filters
        protected = constraints.get('protected_channels', [])
        if protected:
            for channel in protected:
                filter_criteria['avoid_actions'].append(f"pause_{channel['platform']}")
        
        # Add preferred actions based on goals
        for goal in goals:
            if goal.get('target') == 'increase':
                filter_criteria['preferred_actions'].append(f"scale_{goal.get('metric', 'conversions')}")
            elif goal.get('target') == 'reduce':
                filter_criteria['preferred_actions'].append(f"optimize_{goal.get('metric', 'cpa')}")
        
        return filter_criteria
