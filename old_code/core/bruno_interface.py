"""
Unified Bruno interface for all input channels (voice, Discord, CLI, etc.).

This module provides a channel-agnostic API that works consistently
regardless of input source.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict, Literal
from enum import Enum

logger = logging.getLogger("bruno.core.interface")


class BrunoActionType(str, Enum):
    """Types of actions Bruno can perform."""
    TIMER_SET = "timer_set"
    TIMER_STATUS = "timer_status"
    TIMER_CANCEL = "timer_cancel"
    MUSIC_PLAY = "music_play"
    MUSIC_PAUSE = "music_pause"
    MUSIC_RESUME = "music_resume"
    MUSIC_STOP = "music_stop"
    MUSIC_NEXT = "music_next"
    MUSIC_VOLUME = "music_volume"
    MUSIC_STATUS = "music_status"
    NOTES_CREATE = "notes_create"
    NOTES_LIST = "notes_list"
    NOTES_SHOW = "notes_show"
    NOTES_ADD_ENTRY = "notes_add_entry"
    NOTES_EDIT_ENTRY = "notes_edit_entry"
    NOTES_DELETE_ENTRY = "notes_delete_entry"
    NOTES_COMPLETE_ENTRY = "notes_complete_entry"
    NOTES_DELETE = "notes_delete"
    SPEAK = "speak"
    CONVERSATION_SAVE = "conversation_save"
    CONVERSATION_LOAD = "conversation_load"
    CONVERSATION_SEARCH = "conversation_search"
    CONVERSATION_LIST = "conversation_list"


class BrunoAction(TypedDict, total=False):
    """Action that Bruno should execute."""
    type: str  # BrunoActionType value
    # Timer fields
    duration_seconds: Optional[int]
    label: Optional[str]
    # Music fields
    query: Optional[str]
    volume: Optional[float]
    # TTS fields
    text: Optional[str]
    # Conversation fields
    title: Optional[str]
    conversation_id: Optional[int]
    tags: Optional[List[str]]


class BrunoRequest(TypedDict, total=False):
    """Request from any input channel."""
    user_id: str           # e.g., "discord:123456" or "voice:local"
    channel: str           # "discord", "voice", "cli"
    text: str              # User's message/command
    audio_path: Optional[str]  # Path to audio file if voice message
    context: Optional[Dict[str, Any]]  # Additional metadata


class BrunoResponse(TypedDict, total=False):
    """Response to send back to user."""
    text: str              # Text reply to display/speak
    actions: List[BrunoAction]  # Actions to execute locally
    success: bool          # Whether request was processed successfully
    error: Optional[str]   # Error message if failed


class BrunoInterface:
    """
    Unified interface for all input channels (voice, Discord, CLI, etc.).
    
    This class wraps existing Bruno functionality and provides a
    clean API that works the same regardless of input source.
    """
    
    def __init__(self, config, llm_client, command_processor, 
                 timer_manager, music_manager, conversation_manager,
                 conversation_ability, memory_store, memory_retriever, 
                 tts_engine, notes_manager=None, alarm_manager=None):
        """
        Initialize with existing Bruno components.
        
        Args:
            config: BrunoConfig instance
            llm_client: LLM client (Ollama, OpenAI, Claude)
            command_processor: CommandProcessor instance
            timer_manager: TimerManager instance
            music_manager: MusicManager instance
            conversation_manager: ConversationManager instance
            conversation_ability: ConversationAbility instance
            memory_store: MemoryStore instance
            memory_retriever: MemoryRetriever instance
            tts_engine: TTS engine instance
            notes_manager: NotesManager instance (optional)
            alarm_manager: AlarmManager instance (optional)
        """
        self.config = config
        self.llm_client = llm_client
        self.command_processor = command_processor
        self.timer_manager = timer_manager
        self.alarm_manager = alarm_manager
        self.music_manager = music_manager
        self.conversation_manager = conversation_manager
        self.conversation_ability = conversation_ability
        self.memory_store = memory_store
        self.memory_retriever = memory_retriever
        self.tts_engine = tts_engine
        self.notes_manager = notes_manager
        
        # Track multi-step note workflows per user
        self.notes_conversation_state: Dict[str, Dict[str, Any]] = {}
        
        logger.info("✅ BrunoInterface initialized")
    
    def _should_parse_commands(self, text: str) -> Dict[str, bool]:
        """
        Fast keyword/regex pre-filter to skip unnecessary LLM command parsing.
        
        Args:
            text: User message text
            
        Returns:
            Dict with boolean flags for which parsers to run
        """
        text_lower = text.lower().strip()
        
        # Common greetings - skip ALL command parsing
        greetings = {
            'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon',
            'good evening', 'howdy', 'sup', 'yo', 'hiya', 'heya'
        }
        if text_lower in greetings or text_lower.startswith(('hello ', 'hi ', 'hey ')):
            logger.debug(f"🚫 Skipping command parsing for greeting: '{text}'")
            return {'skip_all': True}
        
        # Very short messages - likely not commands
        if len(text.strip()) < 4:
            return {'skip_all': True}
        
        # Check for specific command keywords
        result = {
            'skip_all': False,
            'parse_timer': False,
            'parse_alarm': False,
            'parse_music': False,
            'parse_notes': False,
            'parse_conversation': False
        }
        
        # Timer keywords (includes time units since they can be for timers or alarms)
        timer_keywords = ['timer', 'countdown', 'minutes', 'hours', 'seconds', 'remind']
        if any(keyword in text_lower for keyword in timer_keywords):
            result['parse_timer'] = True
        
        # Alarm keywords
        alarm_keywords = ['alarm', 'wake me', 'remind me at']
        if any(keyword in text_lower for keyword in alarm_keywords):
            result['parse_alarm'] = True
        
        # Music keywords  
        music_keywords = ['play', 'music', 'song', 'track', 'pause', 'resume', 'stop', 'volume', 'skip', 'next']
        if any(keyword in text_lower for keyword in music_keywords):
            result['parse_music'] = True
        
        # Notes keywords
        notes_keywords = ['note', 'notes', 'list', 'todo', 'reminder', 'jira', 'entry', 'entries']
        if any(keyword in text_lower for keyword in notes_keywords):
            result['parse_notes'] = True
        
        # Conversation recall keywords
        recall_keywords = ['discussed', 'conversation', 'talked about', 'last time', 'remember when', 'recall']
        if any(keyword in text_lower for keyword in recall_keywords):
            result['parse_conversation'] = True
        
        # If no specific keywords detected, skip all command parsing
        if not any([result['parse_timer'], result['parse_alarm'], result['parse_music'], result['parse_notes'], result['parse_conversation']]):
            result['skip_all'] = True
            logger.debug(f"🚫 No command keywords detected in: '{text}'")
        
        return result
    
    def handle_message(self, request: BrunoRequest) -> BrunoResponse:
        """
        Main entry point - process message from any channel.
        
        Args:
            request: BrunoRequest with user_id, channel, text
            
        Returns:
            BrunoResponse with text reply and actions to execute
        """
        try:
            user_id = request['user_id']
            channel = request['channel']
            text = request['text']
            
            logger.info(f"📨 Processing message from {channel} user {user_id}: '{text}'")
            
            # Save user message to memory
            if self.conversation_manager:
                self.conversation_manager.add_message(
                    role='user',
                    content=text
                )
            
            # Parse command to determine type
            actions: List[BrunoAction] = []
            response_text = ""
            
            # OPTIMIZATION: Pre-filter to skip unnecessary LLM command parsing
            parse_filters = self._should_parse_commands(text)
            
            if parse_filters.get('skip_all'):
                # Skip all command parsing for greetings and general chat
                logger.info(f"⚡ Skipping command parsing (no keywords detected)")
                timer_cmd = None
                conv_cmd = None
                music_cmd = None
                notes_cmd = None
                alarm_cmd = None
            else:
                # Parse only relevant commands based on keywords
                timer_cmd = None
                conv_cmd = None
                music_cmd = None
                notes_cmd = None
                alarm_cmd = None
                
                # Run filtered command parsing in parallel using asyncio
                async def parse_commands_parallel():
                    tasks = []
                    
                    if parse_filters.get('parse_timer') and self.command_processor and self.timer_manager:
                        tasks.append(('timer', asyncio.to_thread(self.command_processor.parse_timer_command, text)))
                    
                    if parse_filters.get('parse_alarm') and self.command_processor and self.alarm_manager:
                        tasks.append(('alarm', asyncio.to_thread(self.command_processor.parse_alarm_command, text)))
                    
                    if parse_filters.get('parse_conversation') and self.command_processor and self.conversation_ability:
                        tasks.append(('conversation', asyncio.to_thread(self.command_processor.parse_conversation_command, text)))
                    
                    if parse_filters.get('parse_music') and self.command_processor and self.music_manager:
                        tasks.append(('music', asyncio.to_thread(self.command_processor.parse_music_command, text)))
                    
                    if parse_filters.get('parse_notes') and self.command_processor and self.notes_manager:
                        tasks.append(('notes', asyncio.to_thread(self.command_processor.parse_notes_command, text)))
                    
                    if not tasks:
                        return {}
                    
                    # Execute only necessary parsers
                    task_names, task_coros = zip(*tasks)
                    results = await asyncio.gather(*task_coros, return_exceptions=True)
                    return dict(zip(task_names, results))
                
                # Execute parallel parsing only for filtered commands
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                parse_results = loop.run_until_complete(parse_commands_parallel())
                timer_cmd = parse_results.get('timer') if parse_results.get('timer') and not isinstance(parse_results.get('timer'), Exception) else None
                alarm_cmd = parse_results.get('alarm') if parse_results.get('alarm') and not isinstance(parse_results.get('alarm'), Exception) else None
                conv_cmd = parse_results.get('conversation') if parse_results.get('conversation') and not isinstance(parse_results.get('conversation'), Exception) else None
                music_cmd = parse_results.get('music') if parse_results.get('music') and not isinstance(parse_results.get('music'), Exception) else None
                notes_cmd = parse_results.get('notes') if parse_results.get('notes') and not isinstance(parse_results.get('notes'), Exception) else None
            
            # Handle timer commands first
            if timer_cmd and timer_cmd.get('action') in ['timer_set', 'timer_status', 'timer_cancel']:
                result = self._handle_timer_command(timer_cmd)
                actions.extend(result['actions'])
                response_text = result['text']
            
            # Try alarm commands if no timer command
            elif alarm_cmd and alarm_cmd.get('action') in ['alarm_set', 'alarm_status', 'alarm_cancel']:
                result = self._handle_alarm_command(alarm_cmd)
                actions.extend(result['actions'])
                response_text = result['text']
            
            # Try conversation commands if no timer/alarm command
            elif conv_cmd and conv_cmd.get('action') in [
                'conversation_save', 'conversation_load', 
                'conversation_search', 'conversation_list', 'conversation_recall'
            ]:
                result = self._handle_conversation_command(conv_cmd)
                actions.extend(result['actions'])
                response_text = result['text']
            
            # Try music commands if no timer/conversation command
            elif music_cmd and music_cmd.get('action') in [
                'music_play', 'music_pause', 'music_resume', 
                'music_stop', 'music_next', 'music_status', 'music_volume'
            ]:
                result = self._handle_music_command(music_cmd)
                actions.extend(result['actions'])
                response_text = result['text']
            # Handle music follow-ups (short responses after "what type of music")
            if not response_text and self.music_manager:
                    # Check if this might be a follow-up music request
                    # Look at conversation context to detect music-related follow-ups
                    if self.conversation_manager:
                        recent_messages = self.conversation_manager.get_messages(limit=5)
                        if recent_messages and len(recent_messages) >= 2:
                            last_assistant_msg = None
                            for msg in reversed(recent_messages):
                                if msg['role'] == 'assistant':
                                    last_assistant_msg = msg['content']
                                    break
                            
                            # If last message asked about music type, treat short answer as music query
                            if last_assistant_msg and 'what type of music' in last_assistant_msg.lower():
                                words = text.strip().split()
                                # If response is 1-3 words, treat as music category
                                if 1 <= len(words) <= 3:
                                    result = self._handle_music_command({
                                        'action': 'music_play',
                                        'query': text.strip()
                                    })
                                    actions.extend(result['actions'])
                                    response_text = result['text']
                            # Also check if user is asking for more/different music after previous play
                            elif last_assistant_msg and ('playing' in last_assistant_msg.lower() or '🎵' in last_assistant_msg):
                                # Check if current message might be requesting different music
                                text_lower = text.lower()
                                # Look for single-word music categories or short queries
                                if len(text.strip().split()) <= 3 and not any(q in text_lower for q in ['what', 'when', 'where', 'who', 'why', 'how', 'is', 'are', 'can', 'could', 'would']):
                                    # Likely a music category/genre
                                    result = self._handle_music_command({
                                        'action': 'music_play',
                                        'query': text.strip()
                                    })
                                    actions.extend(result['actions'])
                                    response_text = result['text']
            
            # Try notes commands if no timer/conversation/music command
            if not response_text and notes_cmd and notes_cmd.get('action') and notes_cmd['action'].startswith('notes_'):
                # Add original text as 'response' for conversation state workflows
                if 'response' not in notes_cmd:
                    notes_cmd['response'] = text
                result = self._handle_notes_command(notes_cmd, user_id=user_id)
                actions.extend(result['actions'])
                response_text = result['text']
            # Check if user is in notes conversation workflow even if no command detected
            elif not response_text and user_id in self.notes_conversation_state:
                # User is in middle of notes workflow - pass text as response
                result = self._handle_notes_command({'action': None, 'response': text}, user_id=user_id)
                actions.extend(result['actions'])
                response_text = result['text']
            
            # If no specific command, use LLM
            if not response_text and self.llm_client:
                response_text = self._generate_llm_response(text, user_id)
                if response_text:
                    actions.append({
                        'type': BrunoActionType.SPEAK.value,
                        'text': response_text
                    })
            
            # Save assistant response to memory
            if response_text and self.conversation_manager:
                self.conversation_manager.add_message(
                    role='assistant',
                    content=response_text
                )
            
            return {
                'text': response_text or "I'm not sure how to help with that.",
                'actions': actions,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}", exc_info=True)
            return {
                'text': f"Sorry, I encountered an error: {str(e)}",
                'actions': [],
                'success': False,
                'error': str(e)
            }
    
    def _handle_timer_command(self, timer_cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Handle timer-related commands."""
        actions = []
        text = ""
        
        action = timer_cmd.get('action')
        
        if action == 'timer_set':
            duration = timer_cmd.get('duration_seconds')
            label = timer_cmd.get('label', 'timer')
            
            actions.append({
                'type': BrunoActionType.TIMER_SET.value,
                'duration_seconds': duration,
                'label': label
            })
            
            # Format duration for response
            minutes = duration // 60
            seconds = duration % 60
            if minutes > 0 and seconds > 0:
                time_str = f"{minutes} minute{'s' if minutes != 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"
            elif minutes > 0:
                time_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
            else:
                time_str = f"{seconds} second{'s' if seconds != 1 else ''}"
            
            text = f"⏰ Timer set for {time_str}"
            
            actions.append({
                'type': BrunoActionType.SPEAK.value,
                'text': f"Timer set for {time_str}"
            })
        
        elif action == 'timer_status':
            actions.append({
                'type': BrunoActionType.TIMER_STATUS.value
            })
            
            # Get active timers
            if self.timer_manager and self.timer_manager.has_active_timers():
                timers = self.timer_manager.list_active_timers()
                timer_list = []
                for t in timers:
                    remaining = t['remaining']
                    time_str = self.timer_manager._format_time_remaining(remaining)
                    timer_list.append(f"{t['label']}: {time_str} remaining")
                text = "Active timers:\n" + "\n".join(timer_list)
            else:
                text = "No active timers"
        
        elif action == 'timer_cancel':
            actions.append({
                'type': BrunoActionType.TIMER_CANCEL.value
            })
            text = "✅ All timers cancelled"
            
            actions.append({
                'type': BrunoActionType.SPEAK.value,
                'text': "All timers cancelled"
            })
        
        return {'actions': actions, 'text': text}
    
    def _handle_alarm_command(self, alarm_cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Handle alarm-related commands."""
        actions = []
        text = ""
        
        action = alarm_cmd.get('action')
        
        if action == 'alarm_set':
            trigger_time = alarm_cmd.get('trigger_time')
            label = alarm_cmd.get('label', 'alarm')
            recurring = alarm_cmd.get('recurring', False)
            recurrence_interval = alarm_cmd.get('recurrence_interval')
            
            if trigger_time:
                actions.append({
                    'type': 'alarm_set',
                    'trigger_time': trigger_time,
                    'label': label,
                    'recurring': recurring,
                    'recurrence_interval': recurrence_interval
                })
                
                # Format time for response
                time_str = trigger_time.strftime('%I:%M %p')
                if recurring:
                    text = f"⏰ Recurring alarm set for {time_str}"
                else:
                    text = f"⏰ Alarm set for {time_str}"
                
                actions.append({
                    'type': BrunoActionType.SPEAK.value,
                    'text': text.replace('⏰ ', '')
                })
            else:
                text = "⚠️ Could not set alarm - invalid time"
        
        elif action == 'alarm_status':
            actions.append({
                'type': 'alarm_status'
            })
            
            # Get active alarms
            if self.alarm_manager and self.alarm_manager.has_active_alarms():
                alarms = self.alarm_manager.list_active_alarms()
                alarm_list = []
                for a in alarms:
                    trigger_time = datetime.fromisoformat(a['trigger_time'])
                    time_str = trigger_time.strftime('%I:%M %p')
                    alarm_list.append(f"{a['label']}: {time_str}")
                text = "Active alarms:\n" + "\n".join(alarm_list)
            else:
                text = "No active alarms"
        
        elif action == 'alarm_cancel':
            actions.append({
                'type': 'alarm_cancel'
            })
            text = "✅ All alarms cancelled"
            
            actions.append({
                'type': BrunoActionType.SPEAK.value,
                'text': "All alarms cancelled"
            })
        
        return {'actions': actions, 'text': text}
    
    def _handle_conversation_command(self, conv_cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Handle conversation management commands."""
        actions = []
        text = ""
        
        action = conv_cmd.get('action')
        
        if action == 'conversation_save':
            title = conv_cmd.get('title', 'Untitled')
            tags = conv_cmd.get('tags', [])
            
            result = self.conversation_ability.save_current_conversation(
                title=title,
                tags=tags
            )
            
            if result['success']:
                text = f"💾 Conversation saved as '{title}'"
                actions.append({
                    'type': BrunoActionType.SPEAK.value,
                    'text': f"Conversation saved as {title}"
                })
            else:
                text = f"❌ Failed to save: {result.get('error', 'Unknown error')}"
        
        elif action in ['conversation_search', 'conversation_recall']:
            query = conv_cmd.get('query', '')
            tags = conv_cmd.get('tags', [])
            days_back = conv_cmd.get('days_back', 7)
            
            result = self.conversation_ability.search_conversations(
                query=query,
                tags=tags,
                days_back=days_back
            )
            
            if result['success'] and result['conversations']:
                convs = result['conversations']
                
                # For recall, get actual messages and answer the question
                if action == 'conversation_recall' and query:
                    # Get messages from matching conversations
                    all_messages = []
                    for conv in convs[:3]:  # Look at top 3 matches
                        messages = self.memory_store.get_messages(conv['id'])
                        all_messages.extend(messages)
                    
                    if all_messages:
                        # Build context from past messages
                        context = f"Based on our past conversations about '{query}':\n\n"
                        for msg in all_messages[-10:]:  # Last 10 messages
                            role = "You" if msg['role'] == 'user' else "Bruno"
                            context += f"{role}: {msg['content']}\n"
                        
                        # Ask LLM to summarize/answer based on past context
                        if self.llm_client:
                            prompt = f"{context}\n\nQuestion: {query}\n\nPlease provide a helpful summary or answer based on our past conversation."
                            response = self.llm_client.generate(prompt, use_history=False)
                            text = response if response else "I found relevant conversations but couldn't summarize them."
                        else:
                            text = f"Found {len(convs)} relevant conversations about '{query}'"
                    else:
                        text = f"Found conversations about '{query}' but no messages to recall"
                else:
                    # For search, just list the conversations
                    if len(convs) == 1:
                        text = f"Found: {convs[0]['title']}"
                    else:
                        titles = [c['title'] for c in convs[:3]]
                        text = f"Found {len(convs)} conversations: " + ", ".join(titles)
                        if len(convs) > 3:
                            text += ", and more"
            else:
                if action == 'conversation_recall':
                    text = f"I don't recall any conversations about '{query}'"
                else:
                    text = "No matching conversations found"
        
        elif action == 'conversation_load':
            conversation_id = conv_cmd.get('conversation_id')
            title = conv_cmd.get('title')
            
            result = self.conversation_ability.load_conversation(
                conversation_id=conversation_id,
                title=title
            )
            
            if result['success']:
                text = f"📂 Loaded conversation: {result['title']}"
            else:
                text = f"❌ {result.get('error', 'Failed to load conversation')}"
        
        elif action == 'conversation_list':
            limit = conv_cmd.get('limit', 5)
            days_back = conv_cmd.get('days_back', 7)
            
            result = self.conversation_ability.list_recent_conversations(
                limit=limit,
                days_back=days_back
            )
            
            if result['success'] and result['conversations']:
                convs = result['conversations']
                titles = [c['title'] for c in convs[:3]]
                text = f"Recent conversations: " + ", ".join(titles)
                if len(convs) > 3:
                    text += f", and {len(convs) - 3} more"
            else:
                text = "No saved conversations yet"
        
        return {'actions': actions, 'text': text}
    
    def _handle_music_command(self, music_cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Handle music-related commands."""
        actions = []
        text = ""
        
        action = music_cmd.get('action')
        
        if action == 'music_play':
            query = music_cmd.get('query', '').strip()
            
            if query:
                # User specified what to play
                actions.append({
                    'type': BrunoActionType.MUSIC_PLAY.value,
                    'query': query
                })
                text = f"🎵 Playing {query} music"
            else:
                # No query - show available categories
                if self.music_manager:
                    categories = self.music_manager.get_categories()
                    if categories:
                        cat_list = ", ".join(categories)
                        text = f"🎵 What type of music would you like? Available: {cat_list}"
                    else:
                        text = "🎵 What type of music would you like?"
                else:
                    text = "🎵 What type of music would you like?"
        
        elif action == 'music_pause':
            actions.append({
                'type': BrunoActionType.MUSIC_PAUSE.value
            })
            text = "⏸️ Music paused"
        
        elif action == 'music_resume':
            actions.append({
                'type': BrunoActionType.MUSIC_RESUME.value
            })
            text = "▶️ Music resumed"
        
        elif action == 'music_next':
            actions.append({
                'type': BrunoActionType.MUSIC_NEXT.value
            })
            text = "⏭️ Skipping to next track"
        
        elif action == 'music_stop':
            actions.append({
                'type': BrunoActionType.MUSIC_STOP.value
            })
            text = "⏹️ Music stopped"
        
        elif action == 'music_status':
            if self.music_manager:
                status = self.music_manager.get_current_status()
                if status['is_playing']:
                    text = f"🎵 Currently playing: {status['current_file']}"
                elif status['is_paused']:
                    text = "⏸️ Music is paused"
                else:
                    text = "No music playing"
            else:
                text = "Music manager not available"
        
        elif action == 'music_volume':
            level = music_cmd.get('level', 0.7)
            actions.append({
                'type': BrunoActionType.MUSIC_VOLUME.value,
                'volume': level
            })
            text = f"🔊 Volume set to {int(level * 100)}%"
        
        return {'actions': actions, 'text': text}
    
    def _handle_notes_command(self, notes_cmd: Dict[str, Any], user_id: str = "local") -> Dict[str, Any]:
        """
        Handle notes with session-based navigation.
        
        Flow:
        1. List view → User selects note by ID
        2. Note view → Shows entries, user can CRUD by entry number or exit
        3. Exit note → Back to list view
        4. Exit notes → Completely exit session
        """
        actions = []
        text = ""
        
        action = notes_cmd.get('action')
        response = notes_cmd.get('response', '').strip()  # Keep original case
        response_lower = response.lower()  # Use for keyword matching only
        
        # Get current session state
        session = self.notes_conversation_state.get(user_id, {})
        current_view = session.get('view', 'closed')  # closed, list, note
        
        # === Handle exit/close commands at any level ===
        # Only check for exit keywords if they're the primary command (not part of other text)
        exit_keywords = ['exit', 'close', 'quit', 'back', 'done', 'leave']
        # Check if response is ONLY an exit keyword or starts with one (e.g., "done" or "exit now")
        is_exit_command = (
            response_lower in exit_keywords or 
            any(response_lower.startswith(keyword + ' ') for keyword in exit_keywords) or
            (response_lower.startswith('im ') and any(keyword in response_lower for keyword in ['done', 'finished'])) or
            response_lower in ['finished', "i'm done", "im done"]
        )
        
        if is_exit_command:
            if current_view == 'note':
                # Exit note → back to list
                return self._show_notes_list(user_id)
            elif current_view == 'list':
                # Exit notes completely
                self.notes_conversation_state.pop(user_id, None)
                return {'actions': [], 'text': '👋 Exited notes. Your notes are saved!'}
            else:
                return {'actions': [], 'text': '📝 Notes are not currently open.'}
        
        # === Check for direct commands (bypasses session workflow) ===
        direct_commands = [
            'notes_create', 'notes_list', 'notes_show', 'notes_show_by_id',
            'notes_rename', 'notes_add_entry', 'notes_edit_entry',
            'notes_delete_entry', 'notes_delete'
        ]
        if action in direct_commands:
            # Handle as direct command (fall through to command handlers below)
            pass
        # === notes_initiate or first entry → show list ===
        elif action == 'notes_initiate' or current_view == 'closed':
            return self._show_notes_list(user_id)
        
        # === In list view → handle note selection or CRUD ===
        if current_view == 'list':
            # Add lowercase version for keyword matching
            notes_cmd_with_lower = {**notes_cmd, 'response_lower': response_lower}
            return self._handle_list_view_command(notes_cmd_with_lower, user_id)
        
        # === In note view → handle entry CRUD ===
        if current_view == 'note':
            # Add lowercase version for keyword matching
            notes_cmd_with_lower = {**notes_cmd, 'response_lower': response_lower}
            return self._handle_note_view_command(notes_cmd_with_lower, user_id)
        
        # Handle regular note commands (not in interactive workflow)
        if action == 'notes_create':
            # Create note with provided name or default "Untitled"
            note_name = notes_cmd.get('note_name', 'Untitled')
            note_id = self.notes_manager.create_note(note_name=note_name)
            
            if note_id:
                if note_name == 'Untitled':
                    text = f"📝 Created note #{note_id} 'Untitled'. What would you like to name it?"
                    # Store in state for renaming
                    self.notes_conversation_state[user_id] = {
                        'step': 'awaiting_rename',
                        'note_id': note_id
                    }
                else:
                    text = f"📝 Created note '{note_name}'."
            else:
                text = "❌ Failed to create note."
        
        elif action == 'notes_list':
            # Use interactive session-based list view
            return self._show_notes_list(user_id)
        
        elif action == 'notes_show':
            note_name = notes_cmd.get('note_name')
            
            if note_name:
                note = self.notes_manager.get_note_by_name(note_name)
                
                if note:
                    entries = self.notes_manager.get_entries(note['id'])
                    
                    text = f"📝 Note #{note['id']}: {note['note_name']}\n"
                    
                    if entries:
                        text += f"\nEntries ({len(entries)}):\n"
                        for entry in entries:
                            text += f"{entry['entry_number']}. {entry['entry_text']}\n"
                    else:
                        text += "\nNo entries yet."
                else:
                    text = f"❌ Note '{note_name}' not found."
            else:
                text = "Please specify which note you want to view."
        
        elif action == 'notes_show_by_id':
            note_id = notes_cmd.get('note_id')
            
            if note_id:
                note = self.notes_manager.get_note_by_id(note_id)
                
                if note:
                    entries = self.notes_manager.get_entries(note['id'])
                    
                    text = f"📝 Note #{note['id']}: {note['note_name']}\n"
                    
                    if entries:
                        text += f"\nEntries ({len(entries)}):\n"
                        for entry in entries:
                            text += f"{entry['entry_number']}. {entry['entry_text']}\n"
                    else:
                        text += "\nNo entries yet."
                else:
                    text = f"❌ Note #{note_id} not found."
            else:
                text = "Please specify which note ID you want to view."
        
        elif action == 'notes_rename':
            new_name = notes_cmd.get('new_name')
            note_id = notes_cmd.get('note_id')
            note_name = notes_cmd.get('note_name')
            
            if new_name:
                # Try ID first, then name
                note = None
                if note_id:
                    note = self.notes_manager.get_note_by_id(note_id)
                elif note_name:
                    note = self.notes_manager.get_note_by_name(note_name)
                
                if note:
                    success = self.notes_manager.update_note(note['id'], note_name=new_name)
                    
                    if success:
                        text = f"✅ Renamed note to '{new_name}'."
                    else:
                        text = "❌ Failed to rename note."
                else:
                    text = "❌ Note not found."
            else:
                text = "Please specify the new name for the note."
        
        elif action == 'notes_add_entry':
            note_identifier = notes_cmd.get('note_identifier') or notes_cmd.get('note_name')
            entry_text = notes_cmd.get('entry_text')
            
            if note_identifier and entry_text:
                # Try as ID first, then name
                note = None
                try:
                    note_id = int(note_identifier)
                    note = self.notes_manager.get_note_by_id(note_id)
                except (ValueError, TypeError):
                    note = self.notes_manager.get_note_by_name(note_identifier)
                
                if note:
                    result = self.notes_manager.add_entry(note['id'], entry_text)
                    
                    if result:
                        entry_id, entry_number = result
                        text = f"✅ Added entry #{entry_number} to '{note['note_name']}': {entry_text}"
                    else:
                        text = f"❌ Failed to add entry to '{note['note_name']}'."
                else:
                    text = f"❌ Note '{note_identifier}' not found."
            else:
                text = "Please specify the note and entry text."
        
        elif action == 'notes_edit_entry':
            note_identifier = notes_cmd.get('note_identifier') or notes_cmd.get('note_name')
            entry_number = notes_cmd.get('entry_number')
            new_text = notes_cmd.get('new_text')
            
            if note_identifier and entry_number and new_text:
                # Try as ID first, then name
                note = None
                try:
                    note_id = int(note_identifier)
                    note = self.notes_manager.get_note_by_id(note_id)
                except (ValueError, TypeError):
                    note = self.notes_manager.get_note_by_name(note_identifier)
                
                if note:
                    entry = self.notes_manager.get_entry_by_number(note['id'], entry_number)
                    
                    if entry:
                        success = self.notes_manager.update_entry(entry['id'], entry_text=new_text)
                        
                        if success:
                            text = f"✅ Updated entry {entry_number} in '{note['note_name']}' to: {new_text}"
                        else:
                            text = f"❌ Failed to update entry {entry_number}."
                    else:
                        text = f"❌ Entry {entry_number} not found in '{note['note_name']}'."
                else:
                    text = f"❌ Note '{note_identifier}' not found."
            else:
                text = "Please specify the note, entry number, and new text."
        
        elif action == 'notes_delete_entry':
            note_identifier = notes_cmd.get('note_identifier') or notes_cmd.get('note_name')
            entry_number = notes_cmd.get('entry_number')
            
            if note_identifier and entry_number:
                # Try as ID first, then name
                note = None
                try:
                    note_id = int(note_identifier)
                    note = self.notes_manager.get_note_by_id(note_id)
                except (ValueError, TypeError):
                    note = self.notes_manager.get_note_by_name(note_identifier)
                
                if note:
                    entry = self.notes_manager.get_entry_by_number(note['id'], entry_number)
                    
                    if entry:
                        success = self.notes_manager.delete_entry(entry['id'])
                        
                        if success:
                            text = f"✅ Deleted entry {entry_number} from '{note['note_name']}'."
                        else:
                            text = f"❌ Failed to delete entry {entry_number}."
                    else:
                        text = f"❌ Entry {entry_number} not found in '{note['note_name']}'."
                else:
                    text = f"❌ Note '{note_identifier}' not found."
            else:
                text = "Please specify the note and entry number."
        
        elif action == 'notes_delete':
            note_identifier = notes_cmd.get('note_identifier')
            
            if note_identifier:
                # Try as ID first, then name
                note = None
                try:
                    note_id = int(note_identifier)
                    note = self.notes_manager.get_note_by_id(note_id)
                except (ValueError, TypeError):
                    note = self.notes_manager.get_note_by_name(note_identifier)
                
                if note:
                    success = self.notes_manager.delete_note(note['id'])
                    
                    if success:
                        text = f"✅ Deleted note '{note['note_name']}'."
                    else:
                        text = f"❌ Failed to delete note '{note['note_name']}'."
                else:
                    text = f"❌ Note '{note_identifier}' not found."
            else:
                text = "Please specify which note to delete."
        
        # Add speak action
        if text:
            actions.append({
                'type': BrunoActionType.SPEAK.value,
                'text': text
            })
        
        return {'actions': actions, 'text': text}
    
    def _show_notes_list(self, user_id: str) -> Dict[str, Any]:
        """Show list of all notes and enter list view."""
        notes = self.notes_manager.list_notes()
        
        if notes:
            text = "📋 **Your Notes**:\n\n"
            for note in notes:
                entry_count = note.get('entry_count', 0)
                text += f"#{note['id']}: {note['note_name']} ({entry_count} entries)\n"
            text += "\n💡 **Options**:\n"
            text += "• Say a note **ID** to open it (e.g., '1')\n"
            text += "• Say 'create [name]' to add a note\n"
            text += "• Say 'rename [ID] [new name]' to rename a note\n"
            text += "• Say 'delete [ID]' to remove a note\n"
            text += "• Say 'exit' or 'close' to leave notes"
        else:
            text = "📋 **No notes found.**\n\n"
            text += "💡 Say 'create [name]' to add your first note, or 'exit' to leave."
        
        # Set session to list view
        self.notes_conversation_state[user_id] = {'view': 'list'}
        
        return {'actions': [], 'text': text}
    
    def _show_note_view(self, note_id: int, user_id: str) -> Dict[str, Any]:
        """Show a specific note with its entries."""
        note = self.notes_manager.get_note_by_id(note_id)
        
        if not note:
            return {'actions': [], 'text': f"❌ Note #{note_id} not found."}
        
        entries = self.notes_manager.get_entries(note_id)
        
        text = f"📝 **{note['note_name']}** (Note #{note_id})\n\n"
        
        if entries:
            text += "**Entries**:\n"
            for entry in entries:
                text += f"{entry['entry_number']}. {entry['entry_text']}\n"
        else:
            text += "*No entries yet.*\n"
        
        text += "\n💡 **Options**:\n"
        text += "• Say 'add [text]' to add an entry\n"
        text += "• Say 'edit [#] [text]' to update an entry\n"
        text += "• Say 'delete [#]' to remove an entry\n"
        text += "• Say 'close' or 'exit' to return to notes list"
        
        # Set session to note view
        self.notes_conversation_state[user_id] = {
            'view': 'note',
            'note_id': note_id,
            'note_name': note['note_name']
        }
        
        return {'actions': [], 'text': text}
    
    def _handle_list_view_command(self, notes_cmd: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Handle commands in list view (note selection, create, delete)."""
        response = notes_cmd.get('response', '').strip()
        response_lower = notes_cmd.get('response_lower', response.lower())
        action = notes_cmd.get('action')
        
        # Try to parse as note ID selection
        try:
            note_id = int(response)
            return self._show_note_view(note_id, user_id)
        except (ValueError, TypeError):
            pass
        
        # Handle explicit actions
        if action == 'notes_create' or 'create' in response_lower:
            # Extract note name
            note_name = notes_cmd.get('note_name')
            if not note_name:
                # Try to extract from response
                words = response.split()
                if 'create' in words:
                    idx = words.index('create')
                    note_name = ' '.join(words[idx+1:]) if idx+1 < len(words) else 'Untitled'
                else:
                    note_name = 'Untitled'
            
            note_id = self.notes_manager.create_note(note_name=note_name)
            if note_id:
                # Automatically open the new note
                return self._show_note_view(note_id, user_id)
            else:
                return {'actions': [], 'text': f"❌ Failed to create note '{note_name}'."}
        
        elif action == 'notes_delete' or 'delete' in response_lower:
            # Extract note ID
            note_id = notes_cmd.get('note_id')
            if not note_id:
                # Try to extract from response
                words = response.split()
                for word in words:
                    try:
                        note_id = int(word)
                        break
                    except ValueError:
                        continue
            
            if note_id:
                note = self.notes_manager.get_note_by_id(note_id)
                if note:
                    success = self.notes_manager.delete_note(note_id)
                    if success:
                        text = f"✅ Deleted note '{note['note_name']}'."
                        return self._show_notes_list(user_id)
                    else:
                        return {'actions': [], 'text': f"❌ Failed to delete note."}
                else:
                    return {'actions': [], 'text': f"❌ Note #{note_id} not found."}
            else:
                return {'actions': [], 'text': "❌ Please specify a note ID to delete (e.g., 'delete 1')."}
        
        elif action == 'notes_rename' or 'rename' in response_lower:
            # Extract note ID and new name: "rename 3 new name"
            note_id = notes_cmd.get('note_id')
            new_name = notes_cmd.get('new_name')
            
            if not note_id or not new_name:
                # Try to parse from response
                words = response.split()
                if 'rename' in words:
                    idx = words.index('rename')
                    if idx+1 < len(words):
                        try:
                            note_id = int(words[idx+1])
                            new_name = ' '.join(words[idx+2:]) if idx+2 < len(words) else None
                        except ValueError:
                            pass
            
            if note_id and new_name:
                note = self.notes_manager.get_note_by_id(note_id)
                if note:
                    success = self.notes_manager.update_note(note_id, note_name=new_name)
                    if success:
                        text = f"✅ Renamed note #{note_id} to '{new_name}'."
                        return self._show_notes_list(user_id)
                    else:
                        return {'actions': [], 'text': f"❌ Failed to rename note."}
                else:
                    return {'actions': [], 'text': f"❌ Note #{note_id} not found."}
            else:
                return {'actions': [], 'text': "❌ Please specify note ID and new name (e.g., 'rename 1 My New Note')."}
        
        # Default: show help
        return {'actions': [], 'text': "💡 Please say a note **ID** to open it, 'create [name]' to add a note, 'rename [ID] [name]' to rename, or 'exit' to leave."}
    
    def _handle_note_view_command(self, notes_cmd: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Handle commands in note view (entry CRUD)."""
        session = self.notes_conversation_state.get(user_id, {})
        note_id = session.get('note_id')
        note_name = session.get('note_name', 'note')
        
        response = notes_cmd.get('response', '').strip()  # Keep original case
        response_lower = notes_cmd.get('response_lower', response.lower())
        action = notes_cmd.get('action')
        
        # Check for edit/delete first (they may contain "add" in the text)
        # Handle edit entry
        if action == 'notes_edit_entry' or response_lower.startswith('edit '):
            entry_number = notes_cmd.get('entry_number')
            new_text = notes_cmd.get('new_text')
            
            if not entry_number or not new_text:
                # Try to parse from response: "edit 1 new text"
                words = response.split()
                if 'edit' in words:
                    idx = words.index('edit')
                    if idx+1 < len(words):
                        try:
                            entry_number = int(words[idx+1])
                            new_text = ' '.join(words[idx+2:]) if idx+2 < len(words) else None
                        except ValueError:
                            pass
            
            if entry_number and new_text:
                entry = self.notes_manager.get_entry_by_number(note_id, entry_number)
                if entry:
                    success = self.notes_manager.update_entry(entry['id'], entry_text=new_text)
                    if success:
                        text = f"✅ Updated entry #{entry_number} to: {new_text}"
                        return self._show_note_view(note_id, user_id)
                    else:
                        return {'actions': [], 'text': f"❌ Failed to update entry."}
                else:
                    return {'actions': [], 'text': f"❌ Entry #{entry_number} not found."}
            else:
                return {'actions': [], 'text': "❌ Please specify entry number and new text (e.g., 'edit 1 new text')."}
        
        # Handle delete entry
        elif action == 'notes_delete_entry' or response_lower.startswith('delete '):
            entry_number = notes_cmd.get('entry_number')
            
            if not entry_number:
                # Try to parse from response: "delete 1"
                words = response.split()
                for word in words:
                    try:
                        entry_number = int(word)
                        break
                    except ValueError:
                        continue
            
            if entry_number:
                entry = self.notes_manager.get_entry_by_number(note_id, entry_number)
                if entry:
                    success = self.notes_manager.delete_entry(entry['id'])
                    if success:
                        text = f"✅ Deleted entry #{entry_number}."
                        return self._show_note_view(note_id, user_id)
                    else:
                        return {'actions': [], 'text': f"❌ Failed to delete entry."}
                else:
                    return {'actions': [], 'text': f"❌ Entry #{entry_number} not found."}
            else:
                return {'actions': [], 'text': "❌ Please specify entry number to delete (e.g., 'delete 1')."}
        
        # Handle add entry (checked last to avoid matching "add" in edit commands)
        elif action == 'notes_add_entry' or response_lower.startswith('add '):
            entry_text = notes_cmd.get('entry_text')
            if not entry_text:
                # Extract text after 'add' (preserving case)
                if 'add' in response_lower:
                    words = response.split('add', 1)
                    entry_text = words[1].strip() if len(words) > 1 else None
            
            if entry_text:
                result = self.notes_manager.add_entry(note_id, entry_text)
                if result:
                    entry_id, entry_number = result
                    text = f"✅ Added entry #{entry_number}: {entry_text}"
                    # Refresh note view
                    return self._show_note_view(note_id, user_id)
                else:
                    return {'actions': [], 'text': f"❌ Failed to add entry."}
            else:
                return {'actions': [], 'text': "❌ Please specify text to add (e.g., 'add buy groceries')."}
        
        # Default: show help
        return {'actions': [], 'text': "💡 Say 'add [text]', 'edit [#] [text]', 'delete [#]', or 'exit' to return to list."}
    
    def _generate_llm_response(self, text: str, user_id: str) -> str:
        """Generate LLM response with memory context (OPTIMIZED - single retrieval with caching)."""
        try:
            import time
            start_time = time.time()
            
            # Build context with conversation history and memories
            query_text = text
            
            if self.conversation_manager and self.memory_retriever:
                # OPTIMIZED: Single retrieval with relevance scoring and caching
                mem_start = time.time()
                memory_context = self.memory_retriever.retrieve_relevant_context(
                    query=text,
                    intent=None,
                    stm_count=5,
                    ltm_count=3
                )
                mem_time = (time.time() - mem_start) * 1000
                logger.info(f"⚡ Memory retrieval: {mem_time:.0f}ms (STM: {len(memory_context['short_term_memory'])}, LTM: {len(memory_context['long_term_memory'])})")
                
                # Get recent messages directly from conversation buffer (no DB query)
                recent_messages = self.conversation_manager.get_messages(limit=6)
                
                # Build enriched prompt with conversation history
                context_parts = []
                
                # Add long-term memories (user profile facts)
                if memory_context['long_term_memory']:
                    context_parts.append("\n[User Profile]")
                    for mem in memory_context['long_term_memory']:
                        context_parts.append(f"- {mem['fact']}")
                
                # Add relevant short-term memories
                if memory_context['short_term_memory']:
                    context_parts.append("\n[Recent Context]")
                    for mem in memory_context['short_term_memory']:
                        context_parts.append(f"- {mem['fact']}")
                
                # Add recent conversation history (last N messages)
                if recent_messages:
                    context_parts.append("\n[Conversation History]")
                    for msg in recent_messages:
                        role = msg['role'].capitalize()
                        context_parts.append(f"{role}: {msg['content']}")
                
                # Build final prompt
                if context_parts:
                    query_text = "\n".join(context_parts) + f"\n\nUser: {text}"
            
            # IMPORTANT: use_history=False because we're manually managing context above
            # This prevents double-context (our context + LLM's internal history)
            llm_start = time.time()
            response = self.llm_client.generate(query_text, use_history=False)
            llm_time = (time.time() - llm_start) * 1000
            
            total_time = (time.time() - start_time) * 1000
            logger.info(f"⚡ LLM generation: {llm_time:.0f}ms | Total: {total_time:.0f}ms")
            return response
            
        except Exception as e:
            logger.error(f"❌ LLM generation failed: {e}")
            return "I'm having trouble processing that right now."
