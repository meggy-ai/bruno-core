"""
Discord adapter for Bruno.

Bridges between Discord messages and Bruno core interface.
"""

import logging
from typing import Dict, Any, Optional
import discord
from bruno.core.bruno_interface import BrunoRequest, BrunoResponse

logger = logging.getLogger("bruno.discord.adapter")


class DiscordAdapter:
    """
    Adapter between Discord and Bruno Core.
    
    Responsibilities:
    - Convert Discord messages to BrunoRequest
    - Convert BrunoResponse to Discord messages
    - Track per-user conversation state
    - Handle Discord-specific formatting (embeds, reactions)
    """
    
    def __init__(self, bruno_interface, config):
        """
        Initialize adapter.
        
        Args:
            bruno_interface: BrunoInterface instance
            config: BrunoConfig instance
        """
        self.bruno_interface = bruno_interface
        self.config = config
        
        # Per-user context tracking
        self.user_contexts: Dict[str, Dict[str, Any]] = {}
        
        logger.info("✅ DiscordAdapter initialized")
    
    def message_to_request(self, message: discord.Message, 
                          text: str, 
                          audio_path: Optional[str] = None) -> BrunoRequest:
        """
        Convert Discord message to BrunoRequest.
        
        Args:
            message: Discord message object
            text: Message text content (or transcribed audio)
            audio_path: Path to audio file if voice message
            
        Returns:
            BrunoRequest ready for processing
        """
        # Generate user ID with discord prefix
        user_id = f"discord:{message.author.id}"
        
        # Determine channel type
        is_dm = isinstance(message.channel, discord.DMChannel)
        channel_type = "discord_dm" if is_dm else "discord_server"
        
        # Build context
        context = {
            'channel_id': message.channel.id,
            'channel_name': getattr(message.channel, 'name', 'DM'),
            'guild_id': message.guild.id if message.guild else None,
            'guild_name': message.guild.name if message.guild else None,
            'is_dm': is_dm,
            'author_name': str(message.author),
            'author_display_name': message.author.display_name
        }
        
        # Track user context
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                'first_message': message.created_at,
                'message_count': 0,
                'last_channel': message.channel.id
            }
        
        self.user_contexts[user_id]['message_count'] += 1
        self.user_contexts[user_id]['last_channel'] = message.channel.id
        self.user_contexts[user_id]['last_message'] = message.created_at
        
        request: BrunoRequest = {
            'user_id': user_id,
            'channel': channel_type,
            'text': text,
            'audio_path': audio_path,
            'context': context
        }
        
        logger.debug(f"📥 Created BrunoRequest for user {user_id}")
        
        return request
    
    def response_to_discord(self, response: BrunoResponse, 
                           use_emoji: bool = True) -> str:
        """
        Format BrunoResponse for Discord.
        
        Can add:
        - Emoji for visual appeal
        - Code blocks for formatted output
        - Embeds for rich content (Phase 2)
        
        Args:
            response: BrunoResponse from Bruno
            use_emoji: Whether to keep emoji in response
            
        Returns:
            Formatted text for Discord
        """
        text = response.get('text', '')
        
        if not text:
            return "I'm not sure how to respond to that."
        
        # Optionally strip emoji if user doesn't want them
        if not use_emoji:
            # Remove common emoji patterns
            emoji_to_remove = ['⏰', '🎵', '💾', '📂', '🔍', '📋', 
                              '⏸️', '▶️', '⏹️', '🔊', '✅', '❌']
            for emoji in emoji_to_remove:
                text = text.replace(emoji, '').strip()
        
        return text
    
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get conversation context for Discord user.
        
        Args:
            user_id: Discord user ID (with "discord:" prefix)
            
        Returns:
            User context dict
        """
        return self.user_contexts.get(user_id, {})
    
    def clear_user_context(self, user_id: str):
        """
        Clear context for a Discord user.
        
        Args:
            user_id: Discord user ID (with "discord:" prefix)
        """
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]
            logger.info(f"🗑️  Cleared context for user {user_id}")
