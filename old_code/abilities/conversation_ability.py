"""
ConversationAbility - User-triggered conversation management.

Handles:
- Saving conversations with custom titles
- Searching past conversations
- Loading specific conversations
- Listing recent conversations
- Tagging conversations
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from bruno.memory.memory_store import MemoryStore
from bruno.memory.conversation_manager import ConversationManager

logger = logging.getLogger(__name__)


class ConversationAbility:
    """
    Manage conversation save/load/search operations via voice commands.
    """
    
    def __init__(
        self,
        memory_store: MemoryStore,
        conversation_manager: ConversationManager
    ):
        """
        Initialize ConversationAbility.
        
        Args:
            memory_store: MemoryStore instance for database operations
            conversation_manager: ConversationManager for session handling
        """
        self.memory_store = memory_store
        self.conversation_manager = conversation_manager
        logger.info("✅ ConversationAbility initialized")
    
    def save_current_conversation(
        self, 
        title: str, 
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Save the current conversation with a user-provided title.
        
        Args:
            title: User-provided title for the conversation
            tags: Optional tags for categorization
            
        Returns:
            Dict with keys: success (bool), message (str), conversation_id (int)
        """
        if not self.conversation_manager.current_conversation_id:
            return {
                'success': False,
                'error': "No active conversation to save"
            }
        
        try:
            # Update conversation with user title
            self.memory_store.update_conversation(
                self.conversation_manager.current_session_id,
                title=title
            )
            
            # Add tags if provided
            if tags:
                self.memory_store.add_conversation_tags(
                    self.conversation_manager.current_conversation_id,
                    tags
                )
            
            logger.info(
                f"💾 Saved conversation '{title}' "
                f"(ID: {self.conversation_manager.current_conversation_id})"
            )
            
            msg_count = self.conversation_manager.message_count
            tag_text = f" with tags: {', '.join(tags)}" if tags else ""
            
            return {
                'success': True,
                'message': f"Conversation saved as '{title}'{tag_text}. {msg_count} messages stored.",
                'conversation_id': self.conversation_manager.current_conversation_id
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to save conversation: {e}")
            return {
                'success': False,
                'error': f"Failed to save conversation: {str(e)}"
            }
    
    def search_conversations(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Search for conversations by content, tags, or date.
        
        Args:
            query: Search query for content
            tags: Filter by tags
            days_back: Look back N days (default: 7)
            
        Returns:
            Dict with keys: success (bool), conversations (list), error (str)
        """
        try:
            date_from = datetime.now() - timedelta(days=days_back)
            
            conversations = self.memory_store.search_conversations(
                query=query,
                tags=tags,
                date_from=date_from
            )
            
            logger.info(f"🔍 Found {len(conversations)} matching conversations")
            return {
                'success': True,
                'conversations': conversations
            }
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return {
                'success': False,
                'conversations': [],
                'error': str(e)
            }
    
    def load_conversation(
        self,
        conversation_id: Optional[int] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load a specific conversation by ID or title.
        
        Args:
            conversation_id: Direct conversation ID
            title: Search by title
            
        Returns:
            Dict with keys: success (bool), title (str), message_count (int), error (str)
        """
        try:
            # Find conversation
            if conversation_id:
                conv = self.memory_store.get_conversation_by_id(conversation_id)
            elif title:
                # Search by title
                search_result = self.search_conversations(query=title, days_back=30)
                if not search_result['success'] or not search_result['conversations']:
                    return {
                        'success': False,
                        'error': f"No conversation found with title '{title}'"
                    }
                conv = search_result['conversations'][0]  # Take first match
                conversation_id = conv['id']
            else:
                return {
                    'success': False,
                    'error': "Must provide either conversation_id or title"
                }
            
            if not conv:
                return {
                    'success': False,
                    'error': "Conversation not found"
                }
            
            # Load conversation
            success = self.conversation_manager.resume_conversation(conversation_id)
            
            if success:
                title = conv.get('title') or f"Conversation {conversation_id}"
                msg_count = conv.get('message_count', 0)
                return {
                    'success': True,
                    'title': title,
                    'message_count': msg_count
                }
            else:
                return {
                    'success': False,
                    'error': "Failed to load conversation"
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to load conversation: {e}")
            return {
                'success': False,
                'error': f"Error loading conversation: {str(e)}"
            }
    
    def list_recent_conversations(
        self,
        limit: int = 10,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """
        List recent conversations.
        
        Args:
            limit: Maximum number of conversations to return
            days_back: Look back N days
            
        Returns:
            Dict with keys: success (bool), conversations (list), error (str)
        """
        try:
            date_from = datetime.now() - timedelta(days=days_back)
            conversations = self.memory_store.get_recent_conversations(
                limit=limit,
                date_from=date_from
            )
            
            logger.info(f"📋 Retrieved {len(conversations)} recent conversations")
            return {
                'success': True,
                'conversations': conversations
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to list conversations: {e}")
            return {
                'success': False,
                'conversations': [],
                'error': str(e)
            }
    
    def get_conversation_summary(
        self,
        conversation_id: int
    ) -> Optional[str]:
        """
        Get or generate a summary for a conversation.
        
        Args:
            conversation_id: ID of conversation
            
        Returns:
            Summary text or None
        """
        try:
            conv = self.memory_store.get_conversation_by_id(conversation_id)
            if not conv:
                return None
            
            # Return existing summary if available
            if conv.get('compressed_summary'):
                return conv['compressed_summary']
            
            # Otherwise return a basic summary
            title = conv.get('title', 'Untitled')
            msg_count = conv.get('message_count', 0)
            started = conv.get('started_at', 'Unknown time')
            
            return f"{title} - {msg_count} messages, started {started}"
            
        except Exception as e:
            logger.error(f"❌ Failed to get summary: {e}")
            return None
    
    def tag_conversation(
        self,
        conversation_id: int,
        tags: List[str]
    ) -> tuple[bool, str]:
        """
        Add tags to a conversation.
        
        Args:
            conversation_id: ID of conversation
            tags: List of tags to add
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.memory_store.add_conversation_tags(conversation_id, tags)
            logger.info(f"🏷️  Tagged conversation {conversation_id} with: {tags}")
            return True, f"Added tags: {', '.join(tags)}"
            
        except Exception as e:
            logger.error(f"❌ Failed to tag conversation: {e}")
            return False, f"Failed to add tags: {str(e)}"
    
    def delete_conversation(
        self,
        conversation_id: int
    ) -> tuple[bool, str]:
        """
        Delete a conversation.
        
        Args:
            conversation_id: ID of conversation to delete
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Don't delete active conversation
            if (self.conversation_manager.current_conversation_id == 
                conversation_id):
                return False, "Cannot delete the active conversation"
            
            self.memory_store.delete_conversation(conversation_id)
            logger.info(f"🗑️  Deleted conversation {conversation_id}")
            return True, "Conversation deleted"
            
        except Exception as e:
            logger.error(f"❌ Failed to delete conversation: {e}")
            return False, f"Failed to delete: {str(e)}"
