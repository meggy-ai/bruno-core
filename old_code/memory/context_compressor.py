"""
ContextCompressor - LLM-based conversation compression and summarization.

This module handles:
- Conversation summarization using Ollama
- Multi-level compression (quick vs detailed)
- Key fact extraction from conversations
- Memory consolidation
- Token budget management
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from bruno.llm.ollama_client import OllamaClient
from bruno.memory.memory_store import MemoryStore

logger = logging.getLogger(__name__)


class ContextCompressor:
    """
    Compresses conversation context using LLM-based summarization.
    
    Features:
    - Conversation summarization (quick and detailed)
    - Key fact extraction
    - Memory consolidation
    - STM to LTM promotion
    - Token-aware compression
    """
    
    # Summarization prompts
    QUICK_SUMMARY_PROMPT = """Summarize this conversation in 2-3 sentences, focusing on the main topics and user's needs:

{conversation}

Summary:"""

    DETAILED_SUMMARY_PROMPT = """Provide a detailed summary of this conversation, including:
1. Main topics discussed
2. User's requests and needs
3. Important context or preferences revealed
4. Any actionable information

Conversation:
{conversation}

Detailed Summary:"""

    FACT_EXTRACTION_PROMPT = """Extract key facts about the user from this conversation. Focus on:
- User preferences and likes/dislikes
- Personal information (name, habits, schedule)
- Recurring behaviors or patterns
- Important context for future interactions

Format as JSON list of facts with category and importance (0.0-1.0):
[
  {{"fact": "...", "category": "preference|profile|habit|knowledge", "importance": 0.0-1.0}},
  ...
]

Conversation:
{conversation}

Facts (JSON only):"""

    MEMORY_CONSOLIDATION_PROMPT = """Consolidate these related memories into a single, comprehensive fact:

Memories:
{memories}

Provide:
1. Consolidated fact (single sentence)
2. Confidence level (0.0-1.0)
3. Category

Format as JSON:
{{"fact": "...", "category": "...", "confidence": 0.0-1.0}}

Consolidated Memory (JSON only):"""

    def __init__(
        self,
        memory_store: MemoryStore,
        llm_client: OllamaClient,
        compression_threshold: int = 50,
        max_context_tokens: int = 2000
    ):
        """
        Initialize ContextCompressor.
        
        Args:
            memory_store: MemoryStore instance
            llm_client: OllamaClient for LLM operations
            compression_threshold: Message count to trigger compression
            max_context_tokens: Maximum tokens for context (rough estimate)
        """
        self.memory_store = memory_store
        self.llm_client = llm_client
        self.compression_threshold = compression_threshold
        self.max_context_tokens = max_context_tokens
        
        logger.info(
            f"✅ ContextCompressor initialized "
            f"(threshold: {compression_threshold}, max_tokens: {max_context_tokens})"
        )
    
    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages into readable conversation text.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Formatted conversation string
        """
        lines = []
        for msg in messages:
            role = msg.get('role', 'unknown').capitalize()
            content = msg.get('content', '')
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count (rough approximation).
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        # Rough estimate: 1 token ≈ 4 characters
        return len(text) // 4
    
    def _extract_json_from_response(self, response: str) -> Optional[Any]:
        """
        Extract JSON from LLM response (handles markdown code blocks).
        
        Args:
            response: LLM response text
            
        Returns:
            Parsed JSON object or None
        """
        try:
            # Try direct parsing first
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract from markdown code block
            import re
            json_match = re.search(r'```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON-like structure
            json_match = re.search(r'(\[.*?\]|\{.*?\})', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
        
        logger.warning(f"⚠️  Failed to extract JSON from response")
        return None
    
    def summarize_conversation_quick(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a quick 2-3 sentence summary of conversation.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Summary text
        """
        if not messages:
            return "No conversation to summarize."
        
        conversation_text = self._format_conversation(messages)
        prompt = self.QUICK_SUMMARY_PROMPT.format(conversation=conversation_text)
        
        logger.info(f"📝 Generating quick summary ({len(messages)} messages)...")
        
        try:
            summary = self.llm_client.generate(prompt, use_history=False)
            logger.info(f"✅ Quick summary generated: {len(summary)} chars")
            return summary.strip()
        except Exception as e:
            logger.error(f"❌ Failed to generate quick summary: {e}")
            return f"Summary of {len(messages)} messages (compression failed)"
    
    def summarize_conversation_detailed(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a detailed summary of conversation.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Detailed summary text
        """
        if not messages:
            return "No conversation to summarize."
        
        conversation_text = self._format_conversation(messages)
        prompt = self.DETAILED_SUMMARY_PROMPT.format(conversation=conversation_text)
        
        logger.info(f"📝 Generating detailed summary ({len(messages)} messages)...")
        
        try:
            summary = self.llm_client.generate(prompt, use_history=False)
            logger.info(f"✅ Detailed summary generated: {len(summary)} chars")
            return summary.strip()
        except Exception as e:
            logger.error(f"❌ Failed to generate detailed summary: {e}")
            return f"Detailed summary of {len(messages)} messages (compression failed)"
    
    def extract_facts(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract key facts from conversation for memory storage.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of fact dictionaries with category and importance
        """
        if not messages:
            return []
        
        conversation_text = self._format_conversation(messages)
        prompt = self.FACT_EXTRACTION_PROMPT.format(conversation=conversation_text)
        
        logger.info(f"🔍 Extracting facts from {len(messages)} messages...")
        
        try:
            response = self.llm_client.generate(prompt, use_history=False)
            facts = self._extract_json_from_response(response)
            
            if facts and isinstance(facts, list):
                logger.info(f"✅ Extracted {len(facts)} facts")
                return facts
            else:
                logger.warning(f"⚠️  No valid facts extracted")
                return []
        except Exception as e:
            logger.error(f"❌ Failed to extract facts: {e}")
            return []
    
    def consolidate_memories(
        self,
        memories: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Consolidate multiple related memories into one.
        
        Args:
            memories: List of memory dictionaries to consolidate
            
        Returns:
            Consolidated memory dictionary or None
        """
        if not memories or len(memories) < 2:
            return None
        
        # Format memories
        memory_texts = []
        for i, mem in enumerate(memories, 1):
            fact = mem.get('fact', '')
            category = mem.get('category', 'unknown')
            memory_texts.append(f"{i}. {fact} (category: {category})")
        
        memories_text = "\n".join(memory_texts)
        prompt = self.MEMORY_CONSOLIDATION_PROMPT.format(memories=memories_text)
        
        logger.info(f"🔗 Consolidating {len(memories)} memories...")
        
        try:
            response = self.llm_client.generate(prompt, use_history=False)
            consolidated = self._extract_json_from_response(response)
            
            if consolidated and isinstance(consolidated, dict):
                logger.info(f"✅ Memories consolidated: {consolidated.get('fact', '')[:50]}...")
                return consolidated
            else:
                logger.warning(f"⚠️  Memory consolidation failed")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to consolidate memories: {e}")
            return None
    
    def compress_conversation(
        self,
        conversation_id: int,
        mode: str = 'detailed'
    ) -> bool:
        """
        Compress a conversation and update database.
        
        Args:
            conversation_id: Conversation database ID
            mode: 'quick' or 'detailed' summary
            
        Returns:
            True if compression succeeded
        """
        # Get conversation and messages
        conv = self.memory_store.get_conversation_by_id(conversation_id)
        if not conv:
            logger.error(f"❌ Conversation {conversation_id} not found")
            return False
        
        messages = self.memory_store.get_messages(conversation_id)
        if not messages:
            logger.warning(f"⚠️  No messages to compress")
            return False
        
        logger.info(
            f"🗜️  Compressing conversation {conversation_id} "
            f"({len(messages)} messages, mode: {mode})"
        )
        
        # Generate summary
        if mode == 'quick':
            summary = self.summarize_conversation_quick(messages)
        else:
            summary = self.summarize_conversation_detailed(messages)
        
        # Extract facts for STM
        facts = self.extract_facts(messages)
        
        # Update conversation with summary
        self.memory_store.update_conversation(
            conv['session_id'],
            compressed_summary=summary
        )
        
        # Store facts in STM
        for fact_data in facts:
            fact = fact_data.get('fact', '')
            category = fact_data.get('category', 'general')
            importance = fact_data.get('importance', 0.5)
            
            if fact:
                self.memory_store.add_short_term_memory(
                    fact=fact,
                    category=category,
                    confidence=importance
                )
        
        logger.info(
            f"✅ Compression complete: "
            f"{len(summary)} char summary, {len(facts)} facts extracted"
        )
        
        return True
    
    def promote_to_ltm(
        self,
        stm_entries: List[Dict[str, Any]],
        consolidate: bool = True
    ) -> int:
        """
        Promote STM entries to LTM, optionally consolidating them.
        
        Args:
            stm_entries: List of STM dictionaries
            consolidate: Whether to consolidate before promoting
            
        Returns:
            Number of LTM entries created
        """
        if not stm_entries:
            return 0
        
        logger.info(f"💎 Promoting {len(stm_entries)} STM entries to LTM...")
        
        promoted_count = 0
        
        if consolidate and len(stm_entries) > 1:
            # Try to consolidate related memories
            consolidated = self.consolidate_memories(stm_entries)
            
            if consolidated:
                # Add consolidated memory to LTM
                ltm_id = self.memory_store.add_long_term_memory(
                    fact=consolidated['fact'],
                    category=consolidated['category'],
                    importance=consolidated['confidence'],
                    confidence=consolidated['confidence']
                )
                
                if ltm_id:
                    promoted_count += 1
                    
                    # Remove original STM entries
                    for stm in stm_entries:
                        self.memory_store.delete_short_term_memory(stm['id'])
                    
                    logger.info(f"✅ Consolidated and promoted to LTM: {ltm_id}")
            else:
                # Consolidation failed, promote individually
                consolidate = False
        
        if not consolidate:
            # Promote individually without consolidation
            for stm in stm_entries:
                ltm_id = self.memory_store.add_long_term_memory(
                    fact=stm['fact'],
                    category=stm.get('category', 'general'),
                    importance=stm.get('relevance_score', 0.7),
                    confidence=stm.get('confidence', 0.8)
                )
                
                if ltm_id:
                    promoted_count += 1
                    # Remove from STM
                    self.memory_store.delete_short_term_memory(stm['id'])
        
        logger.info(f"✅ Promoted {promoted_count} entries to LTM")
        return promoted_count
    
    def should_compress(self, conversation_id: int) -> bool:
        """
        Check if conversation should be compressed.
        
        Args:
            conversation_id: Conversation database ID
            
        Returns:
            True if compression recommended
        """
        message_count = self.memory_store.get_message_count(conversation_id)
        
        if message_count >= self.compression_threshold:
            logger.info(
                f"🗜️  Compression recommended: "
                f"{message_count}/{self.compression_threshold} messages"
            )
            return True
        
        return False
    
    def auto_compress_and_promote(
        self,
        conversation_id: int,
        stm_entries: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Automatically compress conversation and promote memories.
        
        Args:
            conversation_id: Conversation database ID
            stm_entries: Optional STM entries to promote (retrieves if None)
            
        Returns:
            Dictionary with compression results
        """
        results = {
            'compressed': False,
            'promoted_count': 0,
            'summary_length': 0,
            'facts_extracted': 0
        }
        
        # Check if compression needed
        if not self.should_compress(conversation_id):
            logger.info(f"ℹ️  Compression not needed for conversation {conversation_id}")
            return results
        
        # Compress conversation
        success = self.compress_conversation(conversation_id, mode='detailed')
        results['compressed'] = success
        
        if success:
            # Get conversation to check summary
            conv = self.memory_store.get_conversation_by_id(conversation_id)
            if conv and conv.get('compressed_summary'):
                results['summary_length'] = len(conv['compressed_summary'])
        
        # Promote STM to LTM if provided or fetch candidates
        if stm_entries is None:
            # This would typically use MemoryRetriever to suggest candidates
            # For now, just log that no entries provided
            logger.info(f"ℹ️  No STM entries provided for promotion")
        else:
            promoted = self.promote_to_ltm(stm_entries, consolidate=True)
            results['promoted_count'] = promoted
        
        logger.info(
            f"✅ Auto compression complete: "
            f"compressed={results['compressed']}, "
            f"promoted={results['promoted_count']}"
        )
        
        return results
    
    def extract_profile_from_conversation(
        self,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract user profile information from conversation using LLM.
        
        Args:
            messages: List of message dictionaries (role, content)
            
        Returns:
            Dictionary with profile data:
            {
                'name': str or None,
                'preferences': dict,
                'habits': list,
                'schedule': dict,
                'personal_notes': list
            }
        """
        if not messages:
            return self._empty_profile()
        
        conversation_text = self._format_messages_for_llm(messages)
        
        prompt = f"""Extract user profile information from this conversation.
Only extract information the user explicitly mentions. Do not infer or assume.

Return JSON with this structure:
{{
  "name": "user's name if mentioned, otherwise null",
  "preferences": {{"category": "specific preference"}},
  "habits": ["habit description"],
  "schedule": {{"time/day": "activity"}},
  "personal_notes": ["any other relevant personal info"]
}}

Conversation:
{conversation_text}

Profile (JSON only):"""
        
        try:
            logger.info("🔍 Extracting profile from conversation...")
            response = self.llm.generate(prompt, use_history=False)
            
            # Parse JSON response
            profile_data = self._parse_json_response(response)
            
            if profile_data:
                # Count what was extracted
                extracted = []
                if profile_data.get('name'):
                    extracted.append('name')
                if profile_data.get('preferences'):
                    extracted.append(f"{len(profile_data['preferences'])} preferences")
                if profile_data.get('habits'):
                    extracted.append(f"{len(profile_data['habits'])} habits")
                if profile_data.get('schedule'):
                    extracted.append(f"{len(profile_data['schedule'])} schedule items")
                
                logger.info(f"✅ Profile extracted: {', '.join(extracted) if extracted else 'nothing new'}")
                return profile_data
            else:
                logger.warning("⚠️  LLM returned no valid profile data")
                return self._empty_profile()
                
        except Exception as e:
            logger.error(f"❌ Profile extraction failed: {e}")
            return self._empty_profile()
    
    def _empty_profile(self) -> Dict[str, Any]:
        """Return empty profile structure."""
        return {
            'name': None,
            'preferences': {},
            'habits': [],
            'schedule': {},
            'personal_notes': []
        }
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ContextCompressor "
            f"threshold={self.compression_threshold} "
            f"max_tokens={self.max_context_tokens}>"
        )
