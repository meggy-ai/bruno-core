"""
MemoryRetriever - Intelligent memory retrieval with relevance scoring.

This module handles:
- Relevance scoring for memories
- Keyword extraction from queries
- Semantic matching (basic TF-IDF approach)
- Memory ranking and filtering
- Context-aware retrieval
"""

import logging
import re
from typing import List, Dict, Any, Optional, Set
from collections import Counter
from datetime import datetime, timedelta

from bruno.memory.memory_store import MemoryStore
from bruno.memory.memory_cache import MemoryCache

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """
    Retrieves relevant memories based on query context.
    
    Features:
    - Keyword extraction from user queries
    - TF-IDF-like relevance scoring
    - Recency boosting
    - Category filtering
    - Access pattern tracking
    - LRU caching for fast repeated queries
    """
    
    # Common stop words to filter out
    STOP_WORDS = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'will', 'with', 'what', 'when', 'where', 'who', 'why',
        'how', 'this', 'these', 'those', 'i', 'you', 'we', 'they', 'my',
        'your', 'his', 'her', 'our', 'their', 'me', 'him', 'us', 'them'
    }
    
    # Intent-based category mapping
    INTENT_CATEGORIES = {
        'music_play': ['music_preference', 'preference'],
        'music_pause': ['music_preference'],
        'music_resume': ['music_preference'],
        'timer_set': ['schedule', 'habit'],
        'weather_query': ['location', 'preference'],
        'general': ['profile', 'preference', 'knowledge']
    }
    
    def __init__(
        self,
        memory_store: MemoryStore,
        recency_weight: float = 0.3,
        access_weight: float = 0.2,
        keyword_weight: float = 0.5,
        enable_cache: bool = True,
        cache_size: int = 100,
        cache_ttl: int = 300
    ):
        """
        Initialize MemoryRetriever.
        
        Args:
            memory_store: MemoryStore instance
            recency_weight: Weight for recency in scoring (default: 0.3)
            access_weight: Weight for access patterns (default: 0.2)
            keyword_weight: Weight for keyword matching (default: 0.5)
            enable_cache: Enable LRU caching (default: True)
            cache_size: Maximum cache entries (default: 100)
            cache_ttl: Cache TTL in seconds (default: 300)
        """
        self.memory_store = memory_store
        self.recency_weight = recency_weight
        self.access_weight = access_weight
        self.keyword_weight = keyword_weight
        
        # Initialize cache
        self.cache = MemoryCache(max_size=cache_size, ttl_seconds=cache_ttl) if enable_cache else None
        
        # Validate weights sum to 1.0
        total = recency_weight + access_weight + keyword_weight
        if not (0.99 <= total <= 1.01):
            logger.warning(
                f"⚠️  Weights sum to {total:.2f}, normalizing to 1.0"
            )
            self.recency_weight /= total
            self.access_weight /= total
            self.keyword_weight /= total
        
        logger.info(
            f"✅ MemoryRetriever initialized "
            f"(recency: {self.recency_weight:.2f}, "
            f"access: {self.access_weight:.2f}, "
            f"keyword: {self.keyword_weight:.2f})"
        )
    
    def extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """
        Extract keywords from text.
        
        Args:
            text: Input text
            top_n: Number of top keywords to return
            
        Returns:
            List of keywords
        """
        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        
        # Filter stop words
        keywords = [w for w in words if w not in self.STOP_WORDS]
        
        # Count frequencies
        word_freq = Counter(keywords)
        
        # Get top N
        top_keywords = [word for word, _ in word_freq.most_common(top_n)]
        
        logger.debug(f"📝 Extracted keywords: {top_keywords}")
        return top_keywords
    
    def calculate_keyword_score(
        self,
        memory_text: str,
        keywords: List[str]
    ) -> float:
        """
        Calculate keyword match score for a memory.
        
        Args:
            memory_text: Memory fact/content
            keywords: List of query keywords
            
        Returns:
            Score between 0.0 and 1.0
        """
        if not keywords:
            return 0.0
        
        memory_lower = memory_text.lower()
        matches = sum(1 for keyword in keywords if keyword in memory_lower)
        
        # Normalize by number of keywords
        score = matches / len(keywords)
        return score
    
    def calculate_recency_score(
        self,
        timestamp: str,
        max_age_days: float = 7.0
    ) -> float:
        """
        Calculate recency score for a memory.
        
        Args:
            timestamp: ISO format timestamp
            max_age_days: Maximum age for scoring (default: 7 days)
            
        Returns:
            Score between 0.0 and 1.0 (1.0 = most recent)
        """
        try:
            # Parse timestamp
            if isinstance(timestamp, str):
                memory_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                memory_time = timestamp
            
            # Calculate age in days
            age = (datetime.now() - memory_time).total_seconds() / 86400
            
            # Score decreases linearly over max_age_days
            if age <= 0:
                return 1.0
            elif age >= max_age_days:
                return 0.0
            else:
                return 1.0 - (age / max_age_days)
        except Exception as e:
            logger.warning(f"⚠️  Error calculating recency: {e}")
            return 0.5  # Default to middle score
    
    def calculate_access_score(
        self,
        access_count: int,
        max_count: int = 10
    ) -> float:
        """
        Calculate access pattern score.
        
        Args:
            access_count: Number of times accessed
            max_count: Maximum count for normalization
            
        Returns:
            Score between 0.0 and 1.0
        """
        return min(access_count / max_count, 1.0)
    
    def score_memory(
        self,
        memory: Dict[str, Any],
        keywords: List[str],
        memory_type: str = 'short_term'
    ) -> float:
        """
        Calculate composite relevance score for a memory.
        
        Args:
            memory: Memory dictionary
            keywords: Query keywords
            memory_type: 'short_term' or 'long_term'
            
        Returns:
            Composite score between 0.0 and 1.0
        """
        # Get memory text (fact or content)
        memory_text = memory.get('fact', '')
        
        # Keyword score
        keyword_score = self.calculate_keyword_score(memory_text, keywords)
        
        # Recency score
        timestamp = memory.get('created_at', datetime.now().isoformat())
        recency_score = self.calculate_recency_score(timestamp)
        
        # Access score
        access_count = memory.get('access_count', 0)
        access_score = self.calculate_access_score(access_count)
        
        # Composite score
        composite = (
            self.keyword_weight * keyword_score +
            self.recency_weight * recency_score +
            self.access_weight * access_score
        )
        
        # Boost by existing relevance/importance if available
        if memory_type == 'short_term':
            base_relevance = memory.get('relevance_score', 1.0)
            composite = composite * base_relevance
        elif memory_type == 'long_term':
            importance = memory.get('importance', 1.0)
            composite = composite * importance
        
        logger.debug(
            f"📊 Memory score: {composite:.3f} "
            f"(keyword: {keyword_score:.2f}, "
            f"recency: {recency_score:.2f}, "
            f"access: {access_score:.2f})"
        )
        
        return composite
    
    def retrieve_short_term_memories(
        self,
        query: str,
        intent: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant short-term memories.
        
        Args:
            query: User query text
            intent: Optional intent classification
            top_k: Maximum memories to return
            min_score: Minimum relevance score threshold
            
        Returns:
            List of relevant memory dictionaries with scores
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get_stm(query, intent)
            if cached is not None:
                return cached
        
        # Extract keywords
        keywords = self.extract_keywords(query)
        
        # Get category hints from intent
        categories = self.INTENT_CATEGORIES.get(intent, []) if intent else []
        
        # OPTIMIZED: Fetch only 2x top_k for scoring buffer (instead of 100)
        fetch_limit = top_k * 2
        
        # Pre-filter at database level
        if categories:
            all_memories = self.memory_store.get_short_term_memories(
                category=categories[0],
                min_relevance=min_score * 0.7,
                limit=fetch_limit
            )
        else:
            all_memories = self.memory_store.get_short_term_memories(
                min_relevance=min_score * 0.7,
                limit=fetch_limit
            )
        
        # Score and filter
        scored_memories = []
        for memory in all_memories:
            score = self.score_memory(memory, keywords, 'short_term')
            
            # Category boost
            if categories and memory.get('category') in categories:
                score *= 1.2  # 20% boost for matching category
            
            if score >= min_score:
                memory['retrieval_score'] = score
                scored_memories.append(memory)
        
        # Sort by score and return top K
        scored_memories.sort(key=lambda x: x['retrieval_score'], reverse=True)
        result = scored_memories[:top_k]
        
        # OPTIMIZED: Batch update access tracking (fast, single transaction)
        if result:
            memory_ids = [m['id'] for m in result]
            self.memory_store.batch_update_memory_access(memory_ids, 'short_term_memory')
        
        # Cache results
        if self.cache:
            self.cache.set_stm(query, intent, result)
        
        logger.info(
            f"🔍 Retrieved {len(result)} STM entries "
            f"(from {len(all_memories)} total, min_score: {min_score})"
        )
        
        return result
    

    
    def retrieve_long_term_memories(
        self,
        query: str,
        intent: Optional[str] = None,
        top_k: int = 3,
        min_score: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant long-term memories.
        
        Args:
            query: User query text
            intent: Optional intent classification
            top_k: Maximum memories to return
            min_score: Minimum relevance score threshold
            
        Returns:
            List of relevant memory dictionaries with scores
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get_ltm(query, intent)
            if cached is not None:
                return cached
        
        # Extract keywords
        keywords = self.extract_keywords(query)
        
        # Get category hints from intent
        categories = self.INTENT_CATEGORIES.get(intent, []) if intent else []
        
        # OPTIMIZED: Fetch only 2x top_k for scoring buffer
        fetch_limit = top_k * 2
        
        # Retrieve LTM with pre-filtering
        all_memories = self.memory_store.get_long_term_memories(limit=fetch_limit)
        
        # Score and filter
        scored_memories = []
        for memory in all_memories:
            score = self.score_memory(memory, keywords, 'long_term')
            
            # Category boost
            if categories and memory.get('category') in categories:
                score *= 1.3  # 30% boost for matching category (higher for LTM)
            
            if score >= min_score:
                memory['retrieval_score'] = score
                scored_memories.append(memory)
        
        # Sort by score and return top K
        scored_memories.sort(key=lambda x: x['retrieval_score'], reverse=True)
        result = scored_memories[:top_k]
        
        # OPTIMIZED: Batch update access tracking (fast, single transaction)
        if result:
            memory_ids = [m['id'] for m in result]
            self.memory_store.batch_update_memory_access(memory_ids, 'long_term_memory')
        
        # Cache results
        if self.cache:
            self.cache.set_ltm(query, intent, result)
        
        logger.info(
            f"🔍 Retrieved {len(result)} LTM entries "
            f"(from {len(all_memories)} total, min_score: {min_score})"
        )
        
        return result
    
    def retrieve_relevant_context(
        self,
        query: str,
        intent: Optional[str] = None,
        stm_count: int = 5,
        ltm_count: int = 3,
        min_stm_score: float = 0.3,
        min_ltm_score: float = 0.4
    ) -> Dict[str, Any]:
        """
        Retrieve all relevant context for a query.
        
        Args:
            query: User query text
            intent: Optional intent classification
            stm_count: Max STM entries to retrieve
            ltm_count: Max LTM entries to retrieve
            min_stm_score: Minimum STM score threshold
            min_ltm_score: Minimum LTM score threshold
            
        Returns:
            Dictionary with STM and LTM entries
        """
        # Check if full context is cached
        if self.cache:
            cached_context = self.cache.get_context(query, intent)
            if cached_context is not None:
                return cached_context
        
        # Retrieve STM and LTM (will use their individual caches)
        stm = self.retrieve_short_term_memories(
            query,
            intent=intent,
            top_k=stm_count,
            min_score=min_stm_score
        )
        
        ltm = self.retrieve_long_term_memories(
            query,
            intent=intent,
            top_k=ltm_count,
            min_score=min_ltm_score
        )
        
        context = {
            'short_term_memory': stm,
            'long_term_memory': ltm,
            'query': query,
            'intent': intent
        }
        
        # Cache the full context
        if self.cache:
            self.cache.set_context(query, intent, context)
        
        logger.info(
            f"📦 Retrieved context: {len(stm)} STM, {len(ltm)} LTM "
            f"for query: '{query[:50]}...'"
        )
        
        return context
    
    def suggest_ltm_candidates(
        self,
        min_access_count: int = 3,
        min_relevance: float = 0.8,
        age_days: float = 3.0
    ) -> List[Dict[str, Any]]:
        """
        Suggest STM entries that should be promoted to LTM.
        
        Args:
            min_access_count: Minimum access count for promotion
            min_relevance: Minimum relevance score
            age_days: Minimum age in days
            
        Returns:
            List of STM entries eligible for LTM promotion
        """
        all_stm = self.memory_store.get_short_term_memories(limit=200)
        
        candidates = []
        cutoff_time = datetime.now() - timedelta(days=age_days)
        
        for memory in all_stm:
            # Check criteria
            access_ok = memory.get('access_count', 0) >= min_access_count
            relevance_ok = memory.get('relevance_score', 0) >= min_relevance
            
            # Check age
            created_at = datetime.fromisoformat(
                memory['created_at'].replace('Z', '+00:00')
            )
            age_ok = created_at <= cutoff_time
            
            if access_ok and relevance_ok and age_ok:
                candidates.append(memory)
        
        # Sort by access count * relevance
        candidates.sort(
            key=lambda x: x.get('access_count', 0) * x.get('relevance_score', 0),
            reverse=True
        )
        
        logger.info(
            f"💎 Found {len(candidates)} STM candidates for LTM promotion"
        )
        
        return candidates
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<MemoryRetriever "
            f"weights=(keyword:{self.keyword_weight:.2f}, "
            f"recency:{self.recency_weight:.2f}, "
            f"access:{self.access_weight:.2f})>"
        )
