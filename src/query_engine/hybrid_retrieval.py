"""
Hybrid SQL Retrieval System

Combines semantic search with SQL pattern matching for better query generation.
Uses intent classification and entity extraction to find more relevant examples.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
from loguru import logger
import re


class QueryIntent(Enum):
    """Classification of query intent types."""
    RANKING = "ranking"           # best, worst, top, bottom
    COMPARISON = "comparison"     # vs, versus, compare
    TREND = "trend"              # over time, week over week
    ANOMALY = "anomaly"          # unusual, spike, drop
    AGGREGATION = "aggregation"  # total, sum, average
    BREAKDOWN = "breakdown"      # by platform, by channel
    FILTER = "filter"            # where, only, exclude
    UNKNOWN = "unknown"


class QueryComplexity(Enum):
    """Classification of query complexity."""
    SIMPLE = "simple"     # Single dimension, basic aggregation
    MEDIUM = "medium"     # Multiple dimensions, comparisons
    COMPLEX = "complex"   # Subqueries, window functions, temporal


@dataclass
class QueryEntities:
    """Extracted entities from a natural language question."""
    group_by: List[str]          # Dimensions to group by
    metrics: List[str]           # Metrics requested
    time_period: Optional[str]   # Time filter requested
    granularity: Optional[str]   # Temporal granularity (daily, weekly, monthly)
    filters: Dict[str, str]      # Column -> value filters
    limit: Optional[int]         # Number of results wanted
    order_by: Optional[str]      # Sort field


@dataclass
class RetrievalResult:
    """Result of hybrid retrieval."""
    question: str
    sql: str
    intent: QueryIntent
    complexity: QueryComplexity
    relevance_score: float
    metadata: Dict[str, Any]


class IntentClassifier:
    """Classifies the intent of a natural language question."""
    
    INTENT_PATTERNS = {
        QueryIntent.RANKING: [
            r'\b(best|worst|top|bottom|highest|lowest|most|least|leading|lagging)\b',
            r'\b(performers?|performing)\b',
            r'\blimit\s+\d+\b',
        ],
        QueryIntent.COMPARISON: [
            r'\b(vs\.?|versus|compared?|comparison|differ(ence)?)\b',
            r'\b(better|worse)\s+than\b',
            r'\b(outperform|underperform)\b',
        ],
        QueryIntent.TREND: [
            r'\b(trend|over\s+time|growth|decline|change)\b',
            r'\b(week\s+over\s+week|wow|month\s+over\s+month|mom|yoy)\b',
            r'\b(increasing|decreasing|rising|falling)\b',
            r'\b(last\s+\d+\s+(days?|weeks?|months?))\b',
        ],
        QueryIntent.ANOMALY: [
            r'\b(unusual|anomal(y|ies|ous)|spike|drop|outlier)\b',
            r'\b(sudden|unexpected|strange|weird)\b',
            r'\b(significant\s+change)\b',
        ],
        QueryIntent.AGGREGATION: [
            r'\b(total|sum|count|average|mean|median)\b',
            r'\b(overall|all|aggregate)\b',
            r'\bhow\s+much\b',
        ],
        QueryIntent.BREAKDOWN: [
            r'\b(by\s+(platform|channel|device|funnel|campaign|ad\s*type))\b',
            r'\b(breakdown|split|segment|per)\b',
            r'\b(each|every)\s+(platform|channel|device)\b',
        ],
        QueryIntent.FILTER: [
            r'\b(where|only|exclude|filter|except)\b',
            r'\b(specific|particular)\b',
            r'\bfor\s+(facebook|google|mobile|desktop)\b',
        ],
    }
    
    def classify(self, question: str) -> QueryIntent:
        """
        Classify the intent of a natural language question.
        
        Returns the most likely intent based on pattern matching.
        """
        question_lower = question.lower()
        intent_scores: Dict[QueryIntent, int] = {}
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, question_lower, re.IGNORECASE)
                score += len(matches)
            if score > 0:
                intent_scores[intent] = score
        
        if not intent_scores:
            return QueryIntent.UNKNOWN
        
        # Return intent with highest score
        return max(intent_scores, key=intent_scores.get)
    
    def get_all_intents(self, question: str) -> List[QueryIntent]:
        """Get all matching intents, ordered by relevance."""
        question_lower = question.lower()
        intent_scores: Dict[QueryIntent, int] = {}
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, question_lower, re.IGNORECASE)
                score += len(matches)
            if score > 0:
                intent_scores[intent] = score
        
        # Sort by score descending
        sorted_intents = sorted(intent_scores.keys(), key=lambda i: intent_scores[i], reverse=True)
        return sorted_intents if sorted_intents else [QueryIntent.UNKNOWN]


class EntityExtractor:
    """Extracts entities from natural language questions."""
    
    DIMENSION_PATTERNS = {
        'platform': [r'\bplatform\b', r'\bfacebook\b', r'\bgoogle\b', r'\bmeta\b', r'\bad\s*network\b'],
        'channel': [r'\bchannel\b', r'\bsem\b', r'\bdisplay\b', r'\bsocial\b', r'\bvideo\b'],
        'device': [r'\bdevice\b', r'\bmobile\b', r'\bdesktop\b', r'\btablet\b'],
        'funnel': [r'\bfunnel\b', r'\bawareness\b', r'\bconsideration\b', r'\bconversion\b'],
        'campaign': [r'\bcampaign\b', r'\bad\b', r'\bcreative\b'],
        'ad_type': [r'\bad\s*type\b', r'\bformat\b'],
    }
    
    METRIC_PATTERNS = {
        'spend': [r'\bspend\b', r'\bcost\b', r'\bbudget\b', r'\b\$\b'],
        'impressions': [r'\bimpressions?\b', r'\bviews?\b', r'\breach\b'],
        'clicks': [r'\bclicks?\b'],
        'conversions': [r'\bconversions?\b', r'\bleads?\b', r'\bsales?\b'],
        'ctr': [r'\bctr\b', r'\bclick\s*(through|rate)\b'],
        'cpc': [r'\bcpc\b', r'\bcost\s*per\s*click\b'],
        'cpa': [r'\bcpa\b', r'\bcost\s*per\s*(acquisition|action)\b'],
        'roas': [r'\broas\b', r'\breturn\s*on\s*ad\s*spend\b'],
        'cvr': [r'\bcvr\b', r'\bconversion\s*rate\b'],
    }
    
    TIME_PATTERNS = {
        'last_7_days': r'\b(last|past)\s*(7|seven)\s*days?\b',
        'last_30_days': r'\b(last|past)\s*(30|thirty)\s*days?\b',
        'last_week': r'\blast\s*week\b',
        'last_month': r'\blast\s*month\b',
        'this_week': r'\bthis\s*week\b',
        'this_month': r'\bthis\s*month\b',
        'week_over_week': r'\bweek\s*(over|vs\.?)\s*week\b',
        'month_over_month': r'\bmonth\s*(over|vs\.?)\s*month\b',
    }
    
    # Granularity patterns - CRITICAL for SQL structure matching
    GRANULARITY_PATTERNS = {
        'daily': [
            r'\bdaily\b', r'\bday\s*over\s*day\b', r'\beach\s*day\b', 
            r'\bper\s*day\b', r'\bby\s*day\b', r'\bday\s*by\s*day\b',
        ],
        'weekly': [
            r'\bweekly\b', r'\bweek\s*over\s*week\b', r'\beach\s*week\b',
            r'\bper\s*week\b', r'\bby\s*week\b', r'\bweek\s*by\s*week\b',
        ],
        'monthly': [
            r'\bmonthly\b', r'\bmonth\s*over\s*month\b', r'\beach\s*month\b',
            r'\bper\s*month\b', r'\bby\s*month\b', r'\bmonth\s*by\s*month\b',
        ],
    }
    
    def extract(self, question: str) -> QueryEntities:
        """Extract entities from a natural language question."""
        question_lower = question.lower()
        
        # Extract dimensions (group by)
        group_by = []
        for dim, patterns in self.DIMENSION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    group_by.append(dim)
                    break
        
        # Extract metrics
        metrics = []
        for metric, patterns in self.METRIC_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    metrics.append(metric)
                    break
        
        # Extract time period
        time_period = None
        for period, pattern in self.TIME_PATTERNS.items():
            if re.search(pattern, question_lower):
                time_period = period
                break
        
        # Extract granularity - CRITICAL for SQL structure
        granularity = None
        for gran, patterns in self.GRANULARITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    granularity = gran
                    break
            if granularity:
                break
        
        # Extract limit (e.g., "top 10")
        limit = None
        limit_match = re.search(r'\b(top|bottom|best|worst)\s+(\d+)\b', question_lower)
        if limit_match:
            limit = int(limit_match.group(2))
        
        # Extract order direction
        order_by = None
        if re.search(r'\b(best|top|highest|most)\b', question_lower):
            order_by = "DESC"
        elif re.search(r'\b(worst|bottom|lowest|least)\b', question_lower):
            order_by = "ASC"
        
        return QueryEntities(
            group_by=group_by,
            metrics=metrics,
            time_period=time_period,
            granularity=granularity,
            filters={},
            limit=limit,
            order_by=order_by
        )


class ComplexityClassifier:
    """Classifies the complexity of a natural language question."""
    
    def classify(self, question: str, entities: QueryEntities) -> QueryComplexity:
        """
        Classify complexity based on question and extracted entities.
        
        Returns:
            QueryComplexity: SIMPLE, MEDIUM, or COMPLEX
        """
        complexity_score = 0
        
        # Multiple dimensions = more complex
        if len(entities.group_by) > 1:
            complexity_score += 2
        elif len(entities.group_by) == 1:
            complexity_score += 1
        
        # Multiple metrics = more complex
        if len(entities.metrics) > 2:
            complexity_score += 2
        elif len(entities.metrics) > 0:
            complexity_score += 1
        
        # Time period = more complex
        if entities.time_period:
            complexity_score += 1
            # Period comparisons are extra complex
            if 'week_over' in (entities.time_period or '') or 'month_over' in (entities.time_period or ''):
                complexity_score += 2
        
        # Ranking/comparison intents are medium
        question_lower = question.lower()
        if re.search(r'\b(vs|versus|compare|top|best|worst)\b', question_lower):
            complexity_score += 1
        
        # Subqueries / advanced patterns = complex
        if re.search(r'\b(percentile|anomaly|outlier|growth|trend)\b', question_lower):
            complexity_score += 3
        
        # Classify based on score
        if complexity_score >= 5:
            return QueryComplexity.COMPLEX
        elif complexity_score >= 2:
            return QueryComplexity.MEDIUM
        else:
            return QueryComplexity.SIMPLE


class HybridSQLRetrieval:
    """
    Hybrid retrieval system combining semantic search with SQL pattern matching.
    
    Improves over pure semantic search by:
    1. Classifying query intent (ranking, comparison, trend, etc.)
    2. Extracting entities (dimensions, metrics, time periods)
    3. Filtering retrieved examples by matching SQL patterns
    4. Reranking by structural similarity
    """
    
    def __init__(self, vector_store=None):
        """
        Initialize hybrid retrieval system.
        
        Args:
            vector_store: Optional vector store for semantic search
        """
        self.vector_store = vector_store
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.complexity_classifier = ComplexityClassifier()
        
        # Example SQL patterns for different intents
        self.intent_sql_patterns = {
            QueryIntent.RANKING: ['ORDER BY', 'LIMIT', 'DESC', 'ASC'],
            QueryIntent.COMPARISON: ['GROUP BY', 'COMPARE', 'CASE WHEN'],
            QueryIntent.TREND: ['DATE_TRUNC', 'LAG', 'OVER', 'INTERVAL'],
            QueryIntent.ANOMALY: ['STDDEV', 'AVG', 'ABS', 'PERCENTILE'],
            QueryIntent.AGGREGATION: ['SUM', 'COUNT', 'AVG', 'TOTAL'],
            QueryIntent.BREAKDOWN: ['GROUP BY'],
        }
    
    def analyze_question(self, question: str) -> Dict[str, Any]:
        """
        Analyze a question and return intent, entities, and complexity.
        
        Returns:
            Dict with keys: intent, intents, entities, complexity
        """
        primary_intent = self.intent_classifier.classify(question)
        all_intents = self.intent_classifier.get_all_intents(question)
        entities = self.entity_extractor.extract(question)
        complexity = self.complexity_classifier.classify(question, entities)
        
        return {
            'intent': primary_intent,
            'intents': all_intents,
            'entities': entities,
            'complexity': complexity,
        }
    
    def get_sql_hints(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate SQL hints based on question analysis.
        
        Returns:
            List of SQL patterns/hints for the LLM to use
        """
        hints = []
        intent = analysis['intent']
        entities = analysis['entities']
        
        # Add intent-based hints
        if intent in self.intent_sql_patterns:
            hints.extend(self.intent_sql_patterns[intent])
        
        # Add entity-based hints
        if entities.group_by:
            hints.append(f"GROUP BY {', '.join(entities.group_by)}")
        
        if entities.limit:
            hints.append(f"LIMIT {entities.limit}")
        
        if entities.order_by:
            hints.append(f"ORDER BY ... {entities.order_by}")
        
        if entities.time_period:
            hints.append(f"Date filter: {entities.time_period}")
        
        return hints
    
    def retrieve_examples(self, question: str, k: int = 3) -> List[RetrievalResult]:
        """
        Retrieve relevant SQL examples using METADATA-FIRST hybrid approach.
        
        Steps:
        1. Extract query intent, metrics, and granularity
        2. Filter by metadata FIRST (intent, metric, granularity)
        3. Semantic rerank within filtered results
        4. Fallback: relax constraints if too few matches
        
        Returns:
            List of RetrievalResult with structurally matching examples
        """
        analysis = self.analyze_question(question)
        entities = analysis['entities']
        intent = analysis['intent']
        
        # If no vector store, return analysis only
        if not self.vector_store:
            logger.debug(f"No vector store, returning analysis: {intent.value}")
            return []
        
        try:
            # Build metadata filter based on extracted entities
            metadata_filter = {
                'intent': intent.value,
            }
            
            # Add metric filter if specific metric detected
            if entities.metrics:
                metadata_filter['metric'] = entities.metrics[0]  # Primary metric
            
            # Add granularity filter - CRITICAL for structure matching
            if entities.granularity:
                metadata_filter['granularity'] = entities.granularity
            
            logger.info(f"Metadata filter: {metadata_filter}")
            
            # Step 1: Try strict metadata filter first
            candidates = self._filter_by_metadata(metadata_filter, k * 5)
            
            # Step 2: If not enough matches, relax constraints progressively
            if len(candidates) < k:
                # Try without granularity
                relaxed_filter = {'intent': intent.value}
                if entities.metrics:
                    relaxed_filter['metric'] = entities.metrics[0]
                logger.debug(f"Relaxing filter to: {relaxed_filter}")
                candidates = self._filter_by_metadata(relaxed_filter, k * 5)
            
            if len(candidates) < k:
                # Try just intent
                relaxed_filter = {'intent': intent.value}
                logger.debug(f"Relaxing filter to just intent: {relaxed_filter}")
                candidates = self._filter_by_metadata(relaxed_filter, k * 5)
            
            if len(candidates) < k:
                # Fallback to pure semantic search
                logger.debug("Falling back to pure semantic search")
                candidates = self.vector_store.similarity_search(question, k=k * 3)
            
            # Step 3: Semantic rerank within filtered results
            results = self._rerank_by_similarity(question, candidates, analysis, k)
            
            return results
            
        except Exception as e:
            logger.warning(f"Hybrid retrieval failed: {e}")
            return []
    
    def _filter_by_metadata(self, metadata_filter: Dict[str, str], k: int) -> List:
        """Filter vector store by metadata constraints."""
        try:
            # Try metadata filtering if supported
            if hasattr(self.vector_store, 'similarity_search_with_filter'):
                return self.vector_store.similarity_search_with_filter(
                    "", filter=metadata_filter, k=k
                )
            elif hasattr(self.vector_store, 'filter'):
                return self.vector_store.filter(metadata=metadata_filter, k=k)
            else:
                # Fallback: get all and filter manually
                all_results = self.vector_store.similarity_search("", k=k * 10)
                filtered = []
                for result in all_results:
                    metadata = getattr(result, 'metadata', {})
                    matches = all(
                        metadata.get(key, '').lower() == value.lower()
                        for key, value in metadata_filter.items()
                    )
                    if matches:
                        filtered.append(result)
                return filtered[:k]
        except Exception as e:
            logger.debug(f"Metadata filter failed: {e}")
            return []
    
    def _rerank_by_similarity(self, question: str, candidates: List, 
                               analysis: Dict[str, Any], k: int) -> List[RetrievalResult]:
        """Rerank candidates by structural + semantic similarity."""
        scored_results = []
        entities = analysis['entities']
        
        for result in candidates:
            metadata = getattr(result, 'metadata', {})
            sql = metadata.get('sql', '')
            
            # Calculate structural match score
            score = 0.5  # Base score
            
            # Intent match bonus
            if metadata.get('intent') == analysis['intent'].value:
                score += 0.2
            
            # Granularity match bonus (most important!)
            if entities.granularity:
                result_gran = metadata.get('granularity', '')
                if result_gran == entities.granularity:
                    score += 0.3  # Big bonus for matching granularity
                elif result_gran:
                    score -= 0.2  # Penalty for wrong granularity
            
            # Metric match bonus
            for metric in entities.metrics:
                if metric.upper() in sql.upper():
                    score += 0.1
            
            # SQL pattern match bonus
            for pattern in self.intent_sql_patterns.get(analysis['intent'], []):
                if pattern.upper() in sql.upper():
                    score += 0.05
            
            scored_results.append(RetrievalResult(
                question=getattr(result, 'page_content', ''),
                sql=sql,
                intent=analysis['intent'],
                complexity=analysis['complexity'],
                relevance_score=score,
                metadata=metadata
            ))
        
        # Sort by score and return top k
        scored_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored_results[:k]


# Convenience functions for direct use
def classify_intent(question: str) -> QueryIntent:
    """Classify the intent of a question."""
    return IntentClassifier().classify(question)


def extract_entities(question: str) -> QueryEntities:
    """Extract entities from a question."""
    return EntityExtractor().extract(question)


def classify_complexity(question: str) -> QueryComplexity:
    """Classify the complexity of a question."""
    entities = EntityExtractor().extract(question)
    return ComplexityClassifier().classify(question, entities)


def analyze_question(question: str) -> Dict[str, Any]:
    """Full analysis of a question."""
    return HybridSQLRetrieval().analyze_question(question)
