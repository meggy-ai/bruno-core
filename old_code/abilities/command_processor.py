"""
CommandProcessor - Processes commands to extract intents and parameters.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional


class CommandProcessor:
    """
    Processes user commands to extract intents and parameters.
    Uses LLM for natural language understanding with fallback to regex parsing.
    """
    
    def __init__(self, llm_client):
        """
        Initialize command processor.
        
        Args:
            llm_client: LLM client for natural language understanding
        """
        self.llm = llm_client
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def parse_timer_command(self, command: str) -> Optional[dict]:
        """
        Parse timer command to extract duration and intent.
        
        Args:
            command: User command text
            
        Returns:
            Dictionary with 'action', 'duration_seconds', 'label', 'response'
            or None if not a timer command
        """
        # Use LLM to understand the command
        prompt = f"""Extract timer information from this command. Respond ONLY with valid JSON.

User command: "{command}"

If this is a timer SET command, respond with:
{{"action": "timer_set", "duration_seconds": <number>, "label": "<description>", "response": "<confirmation message>"}}

If this is checking timer STATUS, respond with:
{{"action": "timer_status", "response": "<message>"}}

If this is CANCELING a timer, respond with:
{{"action": "timer_cancel", "response": "<message>"}}

If NOT a timer command, respond with:
{{"action": "other"}}

Examples:
- "set a timer for 5 minutes" → {{"action": "timer_set", "duration_seconds": 300, "label": "5-minute timer", "response": "Starting 5-minute timer"}}
- "timer for 2 hours" → {{"action": "timer_set", "duration_seconds": 7200, "label": "2-hour timer", "response": "Starting 2-hour timer"}}
- "set timer 30 seconds" → {{"action": "timer_set", "duration_seconds": 30, "label": "30-second timer", "response": "Starting 30-second timer"}}
- "how much time is left" → {{"action": "timer_status", "response": "Checking timer status"}}
- "cancel the timer" → {{"action": "timer_cancel", "response": "Cancelling timer"}}
- "what's the weather" → {{"action": "other"}}
"""
        
        try:
            response = self.llm.generate(prompt, use_history=False)
            
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                self.logger.debug(f"Timer command JSON: {json_str}")
                parsed = json.loads(json_str)
                
                # If LLM identified timer command
                if parsed.get('action') in ['timer_set', 'timer_status', 'timer_cancel']:
                    self.logger.info(f"✅ Parsed timer command: {parsed.get('action')}")
                    
                    # Validate duration for timer_set
                    if parsed.get('action') == 'timer_set':
                        duration = parsed.get('duration_seconds')
                        if duration and duration > 0:
                            return parsed
                        else:
                            # Try fallback parsing
                            self.logger.warning("Invalid duration from LLM, trying fallback")
                            return self._parse_timer_fallback(command)
                    
                    return parsed
                
                # Not a timer command
                if parsed.get('action') == 'other':
                    self.logger.debug("Timer command: action=other, not a timer command")
                    # But check if "timer" keyword exists - LLM might be wrong
                    if 'timer' in command.lower():
                        self.logger.info("🔄 Timer keyword found, trying fallback despite LLM saying 'other'")
                        return self._parse_timer_fallback(command)
                    return None
            
            # If JSON parsing failed, try fallback
            self.logger.warning("Failed to parse LLM response, trying fallback")
            return self._parse_timer_fallback(command)
            
        except Exception as e:
            self.logger.error(f"Error parsing timer command with LLM: {e}")
            # Fall back to regex parsing
            return self._parse_timer_fallback(command)
    
    def _parse_timer_fallback(self, command: str) -> Optional[dict]:
        """
        Fallback regex-based timer command parsing.
        
        Args:
            command: User command text
            
        Returns:
            Parsed command dictionary or None
        """
        command_lower = command.lower()
        
        # Check for timer SET first (most common)
        timer_keywords = ['timer', 'set timer', 'start timer', 'create timer', 'make timer']
        has_timer_keyword = any(keyword in command_lower for keyword in timer_keywords)
        
        if has_timer_keyword:
            # Try to extract duration
            duration = self.parse_duration_manual(command_lower)
            if duration and duration > 0:
                label = self._format_duration_label(duration)
                return {
                    'action': 'timer_set',
                    'duration_seconds': duration,
                    'label': label,
                    'response': f'⏰ Timer set for {label.replace("-timer", "")}'
                }
        
        # Check for timer cancellation
        if any(keyword in command_lower for keyword in ['cancel', 'stop', 'end']):
            if 'timer' in command_lower:
                return {
                    'action': 'timer_cancel',
                    'response': 'Cancelling timer'
                }
        
        # Check for timer status
        if any(keyword in command_lower for keyword in ['how much', 'time left', 'remaining', 'status']):
            if 'timer' in command_lower or 'time' in command_lower:
                return {
                    'action': 'timer_status',
                    'response': 'Checking timer status'
                }
        
        # Check for timer creation
        if any(keyword in command_lower for keyword in ['timer', 'set', 'start', 'countdown']):
            duration = self.parse_duration_manual(command)
            if duration:
                label = self._format_duration_label(duration)
                return {
                    'action': 'timer_set',
                    'duration_seconds': duration,
                    'label': label,
                    'response': f"Starting {label}"
                }
        
        return None
    
    @staticmethod
    def parse_duration_manual(text: str) -> Optional[int]:
        """
        Manual duration parsing using regex (fallback method).
        
        Args:
            text: Text containing duration information
            
        Returns:
            Duration in seconds, or None if parsing fails
        """
        text = text.lower()
        total_seconds = 0
        
        # Parse hours
        hours_match = re.search(r'(\d+)\s*(?:hour|hr)s?', text)
        if hours_match:
            total_seconds += int(hours_match.group(1)) * 3600
        
        # Parse minutes
        minutes_match = re.search(r'(\d+)\s*(?:minute|min)s?', text)
        if minutes_match:
            total_seconds += int(minutes_match.group(1)) * 60
        
        # Parse seconds
        seconds_match = re.search(r'(\d+)\s*(?:second|sec)s?', text)
        if seconds_match:
            total_seconds += int(seconds_match.group(1))
        
        # If no units found, check for standalone number with "timer" or "for"
        if total_seconds == 0:
            # "timer for 5" or "set timer 10"
            number_match = re.search(r'(?:timer|for|set)\s+(\d+)', text)
            if number_match:
                num = int(number_match.group(1))
                # Assume minutes for numbers 1-120, seconds otherwise
                if 1 <= num <= 120:
                    total_seconds = num * 60
                else:
                    total_seconds = num
        
        return total_seconds if total_seconds > 0 else None
    
    @staticmethod
    def _format_duration_label(seconds: int) -> str:
        """
        Format duration into readable label.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted label (e.g., "5-minute timer")
        """
        if seconds < 60:
            return f"{seconds}-second timer"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}-minute timer"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}-hour {minutes}-minute timer"
            return f"{hours}-hour timer"
    
    def parse_alarm_command(self, command: str) -> Optional[dict]:
        """
        Parse alarm command to extract time and intent.
        
        Args:
            command: User command text
            
        Returns:
            Dictionary with 'action', 'trigger_time', 'label', 'response', 'recurring', 'recurrence_interval'
            or None if not an alarm command
        """
        # Use LLM to understand the command
        prompt = f"""Extract alarm information from this command. Respond ONLY with valid JSON.

User command: "{command}"

Current time is: {datetime.now().strftime('%I:%M %p')}

If this is setting an ALARM, respond with:
{{"action": "alarm_set", "time": "<HH:MM format 24-hour>", "label": "<description>", "response": "<confirmation>", "recurring": false}}

For recurring alarms:
{{"action": "alarm_set", "time": "<HH:MM>", "label": "<description>", "response": "<confirmation>", "recurring": true, "recurrence_interval": <seconds>}}

If this is CANCELING an alarm:
{{"action": "alarm_cancel", "response": "<message>"}}

If checking alarm STATUS:
{{"action": "alarm_status", "response": "<message>"}}

If NOT an alarm command:
{{"action": "other"}}

Examples:
- "set alarm for 7:30 AM" → {{"action": "alarm_set", "time": "07:30", "label": "7:30 AM alarm", "response": "Alarm set for 7:30 AM"}}
- "alarm at 2 PM" → {{"action": "alarm_set", "time": "14:00", "label": "2:00 PM alarm", "response": "Alarm set for 2:00 PM"}}
- "set alarm in 30 minutes" → {{"action": "alarm_set", "time": "RELATIVE:1800", "label": "30-minute alarm", "response": "Alarm set for 30 minutes from now"}}
- "wake me up at 6 AM" → {{"action": "alarm_set", "time": "06:00", "label": "6:00 AM wake up", "response": "Alarm set for 6:00 AM"}}
- "cancel alarm" → {{"action": "alarm_cancel", "response": "Cancelling alarm"}}
- "what alarms do I have" → {{"action": "alarm_status", "response": "Checking alarms"}}
"""
        
        try:
            response = self.llm.generate(prompt, use_history=False)
            
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                self.logger.debug(f"Alarm command JSON: {json_str}")
                parsed = json.loads(json_str)
                
                # If LLM identified alarm command
                if parsed.get('action') in ['alarm_set', 'alarm_status', 'alarm_cancel']:
                    self.logger.info(f"✅ Parsed alarm command: {parsed.get('action')}")
                    
                    # Convert time to datetime for alarm_set
                    if parsed.get('action') == 'alarm_set':
                        time_str = parsed.get('time')
                        if time_str:
                            # Handle relative time (e.g., "RELATIVE:1800" for 30 minutes)
                            if time_str.startswith('RELATIVE:'):
                                seconds = int(time_str.split(':')[1])
                                trigger_time = datetime.now() + timedelta(seconds=seconds)
                            else:
                                # Parse absolute time (HH:MM format)
                                trigger_time = self._parse_time_to_datetime(time_str)
                            
                            if trigger_time:
                                parsed['trigger_time'] = trigger_time
                                return parsed
                            else:
                                self.logger.warning("Failed to parse alarm time")
                                return self._parse_alarm_fallback(command)
                    
                    return parsed
                
                # Not an alarm command
                if parsed.get('action') == 'other':
                    self.logger.debug("Alarm command: action=other, not an alarm command")
                    # But check if "alarm" keyword exists
                    if 'alarm' in command.lower() or 'wake' in command.lower():
                        self.logger.info("🔄 Alarm keyword found, trying fallback")
                        return self._parse_alarm_fallback(command)
                    return None
            
            # If JSON parsing failed, try fallback
            self.logger.warning("Failed to parse LLM response, trying fallback")
            return self._parse_alarm_fallback(command)
            
        except Exception as e:
            self.logger.error(f"Error parsing alarm command with LLM: {e}")
            return self._parse_alarm_fallback(command)
    
    def _parse_alarm_fallback(self, command: str) -> Optional[dict]:
        """
        Fallback regex-based alarm command parsing.
        
        Args:
            command: User command text
            
        Returns:
            Parsed command dictionary or None
        """
        from datetime import timedelta
        command_lower = command.lower()
        
        # Check for alarm keywords
        alarm_keywords = ['alarm', 'wake me', 'remind me']
        has_alarm_keyword = any(keyword in command_lower for keyword in alarm_keywords)
        
        if has_alarm_keyword:
            # Try to extract time (e.g., "7:30", "7:30 AM", "14:00")
            time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', command_lower)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                am_pm = time_match.group(3)
                
                # Convert to 24-hour format if AM/PM specified
                if am_pm:
                    if am_pm == 'pm' and hour != 12:
                        hour += 12
                    elif am_pm == 'am' and hour == 12:
                        hour = 0
                
                # Create datetime for today at specified time
                trigger_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If time has passed, set for tomorrow
                if trigger_time <= datetime.now():
                    trigger_time += timedelta(days=1)
                
                label = trigger_time.strftime('%I:%M %p alarm')
                return {
                    'action': 'alarm_set',
                    'trigger_time': trigger_time,
                    'label': label,
                    'response': f'⏰ Alarm set for {trigger_time.strftime("%I:%M %p")}',
                    'recurring': False
                }
            
            # Try relative time (e.g., "in 30 minutes", "in 1 hour")
            relative_match = re.search(r'in\s+(\d+)\s*(hour|minute|min)s?', command_lower)
            if relative_match:
                amount = int(relative_match.group(1))
                unit = relative_match.group(2)
                
                if unit in ['hour']:
                    seconds = amount * 3600
                else:  # minutes
                    seconds = amount * 60
                
                trigger_time = datetime.now() + timedelta(seconds=seconds)
                label = f'{amount} {unit} alarm'
                return {
                    'action': 'alarm_set',
                    'trigger_time': trigger_time,
                    'label': label,
                    'response': f'⏰ Alarm set for {amount} {unit} from now',
                    'recurring': False
                }
        
        # Check for alarm cancellation
        if any(keyword in command_lower for keyword in ['cancel', 'stop', 'delete']):
            if 'alarm' in command_lower:
                return {
                    'action': 'alarm_cancel',
                    'response': 'Cancelling alarm'
                }
        
        # Check for alarm status
        if any(keyword in command_lower for keyword in ['what', 'show', 'list', 'check']):
            if 'alarm' in command_lower:
                return {
                    'action': 'alarm_status',
                    'response': 'Checking alarms'
                }
        
        return None
    
    def _parse_time_to_datetime(self, time_str: str) -> Optional[datetime]:
        """
        Parse time string (HH:MM) to datetime object for today.
        If time has passed, set for tomorrow.
        
        Args:
            time_str: Time in HH:MM format (24-hour)
            
        Returns:
            datetime object or None if parsing fails
        """
        from datetime import timedelta
        try:
            hour, minute = map(int, time_str.split(':'))
            trigger_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time has passed, set for tomorrow
            if trigger_time <= datetime.now():
                trigger_time += timedelta(days=1)
            
            return trigger_time
        except Exception as e:
            self.logger.error(f"Failed to parse time '{time_str}': {e}")
            return None
    
    def parse_music_command(self, command: str) -> Optional[dict]:
        """
        Parse music command to extract intent and parameters.
        
        Args:
            command: User command text
            
        Returns:
            Dictionary with 'action', 'query', 'response', etc.
            or None if not a music command
        """
        # Use LLM to understand the command
        prompt = f"""Extract music command information from this command. Respond ONLY with valid JSON.

User command: "{command}"

If this is a PLAY music command, respond with:
{{"action": "music_play", "query": "<search query>", "response": "<confirmation message>"}}

If this is PAUSE music, respond with:
{{"action": "music_pause", "response": "<message>"}}

If this is RESUME music, respond with:
{{"action": "music_resume", "response": "<message>"}}

If this is STOP music, respond with:
{{"action": "music_stop", "response": "<message>"}}

If this is SKIP/NEXT song, respond with:
{{"action": "music_next", "response": "<message>"}}

If this is checking music STATUS, respond with:
{{"action": "music_status", "response": "<message>"}}

If this is VOLUME control, respond with:
{{"action": "music_volume", "level": <0.0-1.0>, "response": "<message>"}}

If NOT a music command, respond with:
{{"action": "other"}}

Examples:
- "play some music" → {{"action": "music_play", "query": "", "response": "What type of music would you like?"}}
- "play meditation music" → {{"action": "music_play", "query": "meditation", "response": "Playing meditation music"}}
- "pause the music" → {{"action": "music_pause", "response": "Pausing music"}}
- "resume music" → {{"action": "music_resume", "response": "Resuming music"}}
- "stop music" → {{"action": "music_stop", "response": "Stopping music"}}
- "next song" → {{"action": "music_next", "response": "Skipping to next song"}}
- "skip this" → {{"action": "music_next", "response": "Skipping track"}}
- "what's playing" → {{"action": "music_status", "response": "Checking what's playing"}}
- "set volume to 50" → {{"action": "music_volume", "level": 0.5, "response": "Setting volume to 50%"}}
- "what's the weather" → {{"action": "other"}}
"""
        
        try:
            response = self.llm.generate(prompt, use_history=False)
            
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                parsed = json.loads(response[json_start:json_end])
                
                # If LLM identified music command
                if parsed.get('action') and parsed['action'].startswith('music_'):
                    self.logger.info(f"✅ Parsed music command: {parsed.get('action')}")
                    return parsed
                
                # Not a music command
                if parsed.get('action') == 'other':
                    return None
            
            # If JSON parsing failed, try fallback
            self.logger.warning("Failed to parse LLM response, trying fallback")
            return self._parse_music_fallback(command)
            
        except Exception as e:
            self.logger.error(f"Error parsing music command with LLM: {e}")
            return self._parse_music_fallback(command)
    
    def _parse_music_fallback(self, command: str) -> Optional[dict]:
        """
        Fallback regex-based music command parsing.
        
        Args:
            command: User command text
            
        Returns:
            Parsed command dictionary or None
        """
        command_lower = command.lower()
        
        # Check for pause
        if 'pause' in command_lower and ('music' in command_lower or 'song' in command_lower or 'audio' in command_lower):
            return {
                'action': 'music_pause',
                'response': 'Pausing music'
            }
        
        # Check for resume
        if any(keyword in command_lower for keyword in ['resume', 'continue', 'unpause']):
            if 'music' in command_lower or 'song' in command_lower or 'audio' in command_lower:
                return {
                    'action': 'music_resume',
                    'response': 'Resuming music'
                }
        
        # Check for stop
        if 'stop' in command_lower and ('music' in command_lower or 'song' in command_lower or 'audio' in command_lower):
            return {
                'action': 'music_stop',
                'response': 'Stopping music'
            }
        
        # Check for next/skip
        if any(keyword in command_lower for keyword in ['next song', 'skip', 'next track', 'play next']):
            return {
                'action': 'music_next',
                'response': 'Skipping to next song'
            }
        
        # Check for status
        if any(keyword in command_lower for keyword in ["what's playing", 'currently playing', 'music status', 'what song']):
            return {
                'action': 'music_status',
                'response': 'Checking music status'
            }
        
        # Check for volume
        volume_match = re.search(r'volume\s+(?:to\s+)?(\d+)', command_lower)
        if volume_match:
            level = int(volume_match.group(1)) / 100.0  # Convert percentage to 0.0-1.0
            return {
                'action': 'music_volume',
                'level': max(0.0, min(1.0, level)),
                'response': f'Setting volume to {volume_match.group(1)}%'
            }
        
        # Check for play
        if any(keyword in command_lower for keyword in ['play', 'start']):
            if 'music' in command_lower or 'song' in command_lower:
                # Extract genre/type from command
                query = self._extract_music_query(command_lower)
                return {
                    'action': 'music_play',
                    'query': query,
                    'response': f'Playing {query} music' if query else 'What type of music would you like?'
                }
        
        return None
    
    @staticmethod
    def _extract_music_query(command: str) -> str:
        """
        Extract music search query from command.
        
        Args:
            command: Lowercase command text
            
        Returns:
            Search query string
        """
        # Remove common keywords
        query = command
        for keyword in ['play', 'start', 'some', 'music', 'song', 'songs', 'the', 'a', 'an', 'next', 'another', 'different']:
            query = query.replace(keyword, ' ')
        
        # Clean up whitespace
        query = ' '.join(query.split()).strip()
        
        return query
    
    def _is_conversation_management_query(self, command: str) -> bool:
        """
        Quick LLM pre-filter: Is user asking about conversations or just having natural dialogue?
        
        Args:
            command: User command text
            
        Returns:
            True if it's a conversation management query (should parse further)
            False if it's natural dialogue (skip conversation parsing)
        """
        prompt = f"""Does this command ask to RECALL or MANAGE past conversations?

Command: "{command}"

Examples that ask about past conversations (YES):
- "what did we discuss about Python?"
- "tell me about our last conversation"
- "what was our last conversation about?"

Examples that are just natural dialogue (NO):
- "it was great" 
- "my car goes 80 km/h"
- "that was fun"

Is the command asking to recall/manage past conversations?
Answer ONLY: true or false"""

        try:
            response = self.llm.generate(prompt, use_history=False)
            if response:
                answer = response.strip().lower()
                is_conversation_query = answer == 'true'
                self.logger.debug(f"🔍 Pre-filter: '{command[:50]}...' → {is_conversation_query}")
                return is_conversation_query
            return False
        except Exception as e:
            self.logger.error(f"Error in conversation pre-filter: {e}")
            # On error, assume it might be a conversation query (safer to check)
            return True
    
    def parse_conversation_command(self, command: str) -> Optional[dict]:
        """
        Parse conversation management command to extract intent and parameters.
        Uses quick pre-filter + Hybrid 4C+4D Chain-of-Thought approach.
        
        Args:
            command: User command text
            
        Returns:
            Dictionary with 'action', 'title'/'query'/'conversation_id', 'tags', 'response'
            or None if not a conversation command
        """
        import time
        
        # QUICK PRE-FILTER: Skip expensive CoT for natural dialogue
        prefilter_start = time.time()
        if not self._is_conversation_management_query(command):
            prefilter_time = time.time() - prefilter_start
            self.logger.debug(f"⚡ Pre-filter rejected in {prefilter_time:.2f}s - natural dialogue, skipping CoT")
            return None
        
        prefilter_time = time.time() - prefilter_start
        self.logger.debug(f"✓ Pre-filter passed in {prefilter_time:.2f}s - running full classification")
        
        start_time = time.time()
        
        # Use LLM with Chain-of-Thought reasoning (Hybrid 4C+4D approach)
        prompt = f"""Classify this command by learning from examples and answering verification questions.

=== EXAMPLES OF CORRECT CLASSIFICATION (Learn from these reasoning chains) ===

Example 1:
Command: "i need to create a to do list"

Step 1 - Is this about PAST conversations?
Answer: NO - User wants to CREATE a new to-do list (future action, not retrieving past information)

Step 2 - Does it mention "conversation" explicitly or implicitly?
Answer: NO - No mention of "conversation", "discussed", "talked about", or similar terms

Step 3 - Is user trying to CREATE/BUILD/MAKE something NEW?
Answer: YES - "create a to do list" is clearly creating something new

Step 4 - Final Classification
This is NOT a conversation command because:
- It's about creating something new (not recalling past)
- Contains no conversation-related keywords
- The word "list" refers to a task list, not a conversation list

JSON Response:
{{"action": "other"}}

---

Example 2:
Command: "what did we discuss about Python?"

Step 1 - Is this asking about PAST conversations or just natural dialogue?
Answer: ASKING ABOUT PAST - "what did we discuss" explicitly asks to recall previous conversation

Step 2 - Does it mention "conversation" explicitly or implicitly?
Answer: YES (implicit) - "discuss" implies reviewing past conversation content

Step 3 - Is user trying to CREATE/BUILD/MAKE something NEW?
Answer: NO - This is retrieving/recalling past information

Step 4 - Final Classification
This IS a conversation recall command because:
- Explicitly ASKS about what was discussed (not just telling a story)
- "what did we" is interrogative, seeking past conversation info
- User wants to retrieve information from past discussions about Python

JSON Response:
{{"action": "conversation_recall", "query": "Python", "response": "Searching for Python discussions"}}

---

Example 2b:
Command: "yeah, it was great and I really enjoyed the experience"

Step 1 - Is this asking about PAST conversations or just natural dialogue?
Answer: NATURAL DIALOGUE - User is responding/continuing current conversation, telling about their experience

Step 2 - Does it mention "conversation" explicitly or implicitly?
Answer: NO - Just uses past tense naturally ("was") while telling a story, no conversation keywords

Step 3 - Is user trying to CREATE/BUILD/MAKE something NEW?
Answer: NO - Just continuing normal conversation

Step 4 - Final Classification
This is NOT a conversation recall command because:
- Not asking about past conversations, just telling a story
- "it was great" is natural storytelling, not asking "what did we discuss"
- Normal conversational response using past tense

JSON Response:
{{"action": "other"}}

---

Example 2c:
Command: "yeah, it was great but my car goes by max speed of 80 Kms per Hour so it took me lot of time"

Step 1 - Is this asking about PAST conversations or just natural dialogue?
Answer: NATURAL DIALOGUE - User is sharing details about their experience (storytelling/responding)

Step 2 - Does it mention "conversation" explicitly or implicitly?
Answer: NO - Uses past tense ("was", "took") but NOT asking about conversations, just narrating

Step 3 - Is user trying to CREATE/BUILD/MAKE something NEW?
Answer: NO - Just continuing conversation naturally

Step 4 - Final Classification
This is NOT a conversation recall command because:
- User is TELLING (not ASKING about past conversations)
- No interrogative words like "what did we", "tell me about our"
- Natural response using past tense for storytelling

JSON Response:
{{"action": "other"}}

---

Example 3:
Command: "gimme the list of songs from last conversation"

Step 1 - Is this about PAST conversations?
Answer: YES - "from last conversation" explicitly refers to past conversation

Step 2 - Does it mention "conversation" explicitly or implicitly?
Answer: YES (explicit) - Contains "last conversation"

Step 3 - Is user trying to CREATE/BUILD/MAKE something NEW?
Answer: NO - Retrieving information from past, not creating new

Step 4 - Final Classification
This IS a conversation recall command because:
- Explicitly mentions "last conversation"
- Wants to retrieve specific information (songs) from that conversation
- Even though it contains "list", the context is clearly about past conversations

JSON Response:
{{"action": "conversation_recall", "query": "songs", "response": "Recalling songs from past conversation"}}

---

Example 4:
Command: "make a shopping list for groceries"

Step 1 - Is this about PAST conversations?
Answer: NO - This is about creating a new shopping list

Step 2 - Does it mention "conversation" explicitly or implicitly?
Answer: NO - No conversation-related terms present

Step 3 - Is user trying to CREATE/BUILD/MAKE something NEW?
Answer: YES - "make a shopping list" is creating something new

Step 4 - Final Classification
This is NOT a conversation command because:
- Uses action verb "make" indicating creation
- No reference to past conversations
- "list" refers to shopping list, not conversation history

JSON Response:
{{"action": "other"}}

=== NOW CLASSIFY THIS COMMAND ===

Command: "{command}"

Step 1 - Is this asking about PAST conversations or just natural dialogue?
(RECALL indicators: "what did we discuss", "tell me about our conversation", "recall what we talked about")
(NATURAL dialogue: "it was great", "I went to", "yeah", responding to questions, telling stories)
Answer:

Step 2 - Does it mention "conversation" explicitly or implicitly?
(Explicit: "conversation", "chat", "discussion")
(Implicit: "discuss about", "talked about", "tell me about our")
(NOT implicit: just using past tense like "was", "went", "did" in storytelling)
Answer:

Step 3 - Is user trying to CREATE/BUILD/MAKE something NEW?
(Check for action verbs: "create", "make", "build", "write", "start")
(Check for forward-looking intent: "need to", "want to", "help me")
Answer:

Step 4 - Final Classification  
Reasoning:

FINAL JSON ANSWER (you MUST provide valid JSON below):
"""
        
        try:
            response = self.llm.generate(prompt, use_history=False)
            elapsed_time = time.time() - start_time
            
            if not response:
                self.logger.warning("⚠️ Empty LLM response for conversation command")
                return self._fallback_conversation_parse(command)
            
            # Parse Chain-of-Thought response
            result = self._parse_cot_response(response)
            
            if result:
                # Log performance metrics (including pre-filter time)
                estimated_tokens = len(prompt) // 4 + len(response) // 4
                total_time = prefilter_time + elapsed_time
                self.logger.debug(f"🧠 CoT Classification: {result.get('action')} | Pre-filter: {prefilter_time:.2f}s | CoT: {elapsed_time:.2f}s | Total: {total_time:.2f}s | Est. tokens: {estimated_tokens}")
                
                # If LLM identified conversation command
                if result.get('action') in ['conversation_save', 'conversation_load', 
                                           'conversation_search', 'conversation_list', 'conversation_recall']:
                    self.logger.info(f"✅ Parsed conversation command: {result.get('action')} (CoT reasoning)")
                    return result
                
                # Not a conversation command
                if result.get('action') == 'other':
                    self.logger.debug("Conversation command: action=other (not a conversation command)")
                    # Double-check with fallback to ensure we didn't miss any conversation keywords
                    fallback_result = self._fallback_conversation_parse(command)
                    if fallback_result:
                        # Fallback found conversation keywords that CoT missed
                        self.logger.info("🔄 Conversation keywords found in fallback, overriding CoT 'other'")
                        return fallback_result
                    # CoT correctly identified as 'other', return None to indicate not a conversation command
                    return None
            
            # If CoT parsing failed, try fallback
            self.logger.warning("Failed to parse CoT response, trying fallback")
            return self._fallback_conversation_parse(command)
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"⚠️ LLM returned invalid JSON, using fallback: {e}")
            return self._fallback_conversation_parse(command)
        except Exception as e:
            self.logger.error(f"❌ Error parsing conversation command: {e}")
            return self._fallback_conversation_parse(command)
    
    def _parse_cot_response(self, response: str) -> Optional[dict]:
        """
        Parse Chain-of-Thought response containing reasoning steps and final JSON.
        Uses improved JSON extraction with fallback patterns.

        The Problem:
        The LLM returns a messy response like this:
        Step 1 - Is this about PAST conversations?
        Answer: NO - User wants to CREATE a new to-do list

        Step 2 - Does it mention "conversation"?
        Answer: NO

        Step 3 - Is user CREATING something NEW?
        Answer: YES

        Step 4 - Final Classification
        This is NOT a conversation command because...

        FINAL JSON ANSWER:
        {"action": "other"}

        We need to extract: {"action": "other"}

        --> so we are trying to find the JSON object from the source
        Try 1: "Maybe it's JUST JSON?"
        Try 2: "Maybe it's in a code block?"
        Try 3: "Maybe it's after a marker?"
        Try 4: "Find ALL JSONs, take the LAST one"
        Try 5: "Just find ANY JSON"

        Reason to do this is :
        ✅ Return clean JSON: {"action": "other"}
        ✅ Put it in code blocks: ```{"action": "other"}```
        ✅ Add labels: FINAL JSON ANSWER: {"action": "other"}
        ✅ Include reasoning + JSON at the end
        ❌ Put example JSONs BEFORE the real answer (need to skip those)
        
        Args:
            response: LLM response with reasoning and JSON
            
        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            # Log reasoning if present (for debugging)
            if 'Step 1' in response or 'Answer:' in response:
                self.logger.debug(f"📝 CoT Reasoning detected in response")
            
            # Method 1: Try direct JSON parsing (if LLM only returned JSON)
            try:
                result = json.loads(response.strip())
                if isinstance(result, dict) and 'action' in result:
                    self.logger.debug("JSON parsed directly")
                    return result
            except json.JSONDecodeError:
                pass
            
            # Method 2: Extract from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
                if isinstance(result, dict) and 'action' in result:
                    self.logger.debug("JSON found in code block")
                    return result
            
            # Method 3: Look for JSON after "FINAL JSON ANSWER" or "JSON Response"
            json_marker_patterns = [
                r'FINAL JSON ANSWER[:\s]*\{',
                r'JSON Response[:\s]*\{',
                r'JSON:\s*\{',
                r'Answer:\s*\{'
            ]
            
            for pattern in json_marker_patterns:
                marker_match = re.search(pattern, response, re.IGNORECASE)
                if marker_match:
                    # Extract JSON starting from the {
                    json_start = marker_match.end() - 1  # Include the {
                    remaining = response[json_start:]
                    
                    # Find matching closing brace
                    try:
                        # Extract until we find a valid JSON object
                        brace_count = 0
                        json_end = 0
                        for i, char in enumerate(remaining):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end = i + 1
                                    break
                        
                        if json_end > 0:
                            json_str = remaining[:json_end]
                            result = json.loads(json_str)
                            if isinstance(result, dict) and 'action' in result:
                                self.logger.debug(f"JSON found after marker: {pattern}")
                                return result
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            # Method 4: Find last JSON object in response (after reasoning)
            json_matches = list(re.finditer(r'\{[^{}]*"action"[^{}]*\}', response, re.DOTALL))
            
            if json_matches:
                # Try from last to first (most recent is usually the final classification)
                for match in reversed(json_matches):
                    try:
                        json_str = match.group(0)
                        result = json.loads(json_str)
                        if isinstance(result, dict) and 'action' in result:
                            self.logger.debug("JSON found via regex match")
                            return result
                    except json.JSONDecodeError:
                        continue
            
            # Method 5: Simple find-based extraction (original method)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                if isinstance(result, dict) and 'action' in result:
                    self.logger.debug("JSON found via simple extraction")
                    return result
            
            self.logger.warning("Could not extract valid JSON from CoT response")
            self.logger.debug(f"Response sample: {response[:500]}...")
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing CoT response: {e}")
            return None
    
    def _fallback_conversation_parse(self, command: str) -> Optional[dict]:
        """
        Fallback regex-based conversation command parsing.
        Enhanced to filter out task creation commands (create/make/build list/task/etc).
        
        Args:
            command: User command text
            
        Returns:
            Dictionary with conversation command info or None
        """
        command_lower = command.lower()
        
        # FIRST: Filter out task creation commands (not conversation commands)
        # These are action verbs + task nouns that indicate NEW creation
        creation_patterns = [
            r'\b(create|make|build|write|start|add)\b.*\b(list|task|todo|note|reminder|plan)\b',
            r'\b(need|want|help|assist)\b.*\b(create|make|build|write)\b',
            r'\bi need to\b',
            r'\bhelp me (with|create|make)\b'
        ]
        
        for pattern in creation_patterns:
            if re.search(pattern, command_lower):
                self.logger.debug(f"🚫 Detected task creation pattern, not a conversation command: {pattern}")
                return None  # This is a task creation, not conversation recall
        
        # Check for save conversation
        save_keywords = ['save this conversation', 'save conversation', 'save this chat', 'remember this conversation']
        if any(keyword in command_lower for keyword in save_keywords):
            # Extract title after "as"
            title_match = re.search(r'\bas\s+(.+)$', command_lower)
            if title_match:
                title = title_match.group(1).strip()
            else:
                title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            return {
                'action': 'conversation_save',
                'title': title,
                'tags': [],
                'response': f'Saving conversation as {title}'
            }
        
        # Check for recall/search
        recall_keywords = [
            'what did we discuss', 'recall our conversation', 'what was our conversation',
            'previous conversation', 'last conversation', 'past conversation',
            'our last conversation', 'our previous conversation', 'earlier conversation',
            'what did we talk about', 'remind me what we discussed', 'from last conversation',
            'from our last chat', 'from earlier', 'from yesterday', 'from before'
        ]
        if any(keyword in command_lower for keyword in recall_keywords):
            # Extract topic after "about"
            topic_match = re.search(r'\babout\s+(.+)$', command_lower)
            query = topic_match.group(1).strip() if topic_match else ""
            
            return {
                'action': 'conversation_recall',
                'query': query,
                'response': f'Searching for conversations about {query}' if query else 'Searching conversations'
            }
        
        # Check for load conversation
        load_keywords = ['load conversation', 'open conversation', 'continue conversation', 'resume conversation']
        if any(keyword in command_lower for keyword in load_keywords):
            # Extract title/ID
            title_match = re.search(r'(?:load|open|continue|resume)\s+(?:conversation\s+)?(.+)$', command_lower)
            title = title_match.group(1).strip() if title_match else ""
            
            return {
                'action': 'conversation_load',
                'title': title,
                'response': f'Loading conversation: {title}'
            }
        
        # Check for list conversations
        list_keywords = ['show conversations', 'list conversations', 'recent conversations', 'my conversations']
        if any(keyword in command_lower for keyword in list_keywords):
            return {
                'action': 'conversation_list',
                'limit': 10,
                'response': 'Listing recent conversations'
            }
        
        return None
    
    def parse_notes_command(self, command: str) -> Optional[dict]:
        """
        Parse notes command to extract intent and parameters.
        
        Args:
            command: User command text
            
        Returns:
            Dictionary with 'action', 'note_name', 'note_id', 'entry_text', etc.
            or None if not a notes command
        """
        # Use LLM to understand the command
        prompt = f"""Extract notes command information from this command. Respond ONLY with valid JSON.

User command: "{command}"

SIMPLIFIED WORKFLOW:
- Notes are created as "Untitled" by default
- Users can rename notes later
- Entries are numbered automatically (1, 2, 3...)
- No categories (permanent/temporary removed)
- CRUD by note ID or note name

If this is CREATE NOTE command, respond with:
{{"action": "notes_create", "response": "Creating note"}}

If this is VIEW/LIST ALL notes command, respond with:
{{"action": "notes_list", "response": "Listing all notes"}}

If this is SHOW SPECIFIC NOTE by name, respond with:
{{"action": "notes_show", "note_name": "<name>", "response": "Showing note '<name>'"}}

If this is SHOW SPECIFIC NOTE by ID, respond with:
{{"action": "notes_show_by_id", "note_id": <number>, "response": "Showing note #<number>"}}

If this is RENAME NOTE, respond with:
{{"action": "notes_rename", "note_id": <id>, "new_name": "<name>", "response": "Renaming note"}}
OR:
{{"action": "notes_rename", "note_name": "<old_name>", "new_name": "<name>", "response": "Renaming note"}}

If this is ADD ENTRY to note, respond with:
{{"action": "notes_add_entry", "note_identifier": "<name_or_id>", "entry_text": "<text>", "response": "Adding entry"}}

If this is EDIT/UPDATE ENTRY, respond with:
{{"action": "notes_edit_entry", "note_identifier": "<name_or_id>", "entry_number": <number>, "new_text": "<text>", "response": "Editing entry <number>"}}

If this is DELETE ENTRY, respond with:
{{"action": "notes_delete_entry", "note_identifier": "<name_or_id>", "entry_number": <number>, "response": "Deleting entry <number>"}}

If this is DELETE NOTE, respond with:
{{"action": "notes_delete", "note_identifier": "<name_or_id>", "response": "Deleting note"}}

If NOT a notes command, respond with:
{{"action": "other"}}

Examples:
- "create a note" → {{"action": "notes_create", "response": "Creating note"}}
- "show my notes" → {{"action": "notes_list", "response": "Listing all notes"}}
- "show bruno note" → {{"action": "notes_show", "note_name": "bruno", "response": "Showing note 'bruno'"}}
- "show note 5" → {{"action": "notes_show_by_id", "note_id": 5, "response": "Showing note #5"}}
- "rename note 3 to shopping" → {{"action": "notes_rename", "note_id": 3, "new_name": "shopping", "response": "Renaming note"}}
- "add buy milk to note 2" → {{"action": "notes_add_entry", "note_identifier": "2", "entry_text": "buy milk", "response": "Adding entry"}}
- "add call mom to bruno note" → {{"action": "notes_add_entry", "note_identifier": "bruno", "entry_text": "call mom", "response": "Adding entry"}}
- "edit entry 2 in note 3 to call doctor" → {{"action": "notes_edit_entry", "note_identifier": "3", "entry_number": 2, "new_text": "call doctor", "response": "Editing entry 2"}}
- "delete entry 3 from bruno note" → {{"action": "notes_delete_entry", "note_identifier": "bruno", "entry_number": 3, "response": "Deleting entry 3"}}
- "delete note 5" → {{"action": "notes_delete", "note_identifier": "5", "response": "Deleting note"}}
- "what's the weather" → {{"action": "other"}}
"""
        
        try:
            response = self.llm.generate(prompt, use_history=False)
            
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                self.logger.debug(f"Notes command JSON: {json_str}")
                parsed = json.loads(json_str)
                
                # If LLM identified notes command
                if parsed.get('action') and parsed['action'].startswith('notes_'):
                    self.logger.info(f"✅ Parsed notes command: {parsed.get('action')}")
                    return parsed
                
                # Not a notes command
                if parsed.get('action') == 'other':
                    return None
            
            # If JSON parsing failed, try fallback
            self.logger.warning("Failed to parse LLM response, trying fallback")
            return self._parse_notes_fallback(command)
            
        except Exception as e:
            self.logger.error(f"Error parsing notes command with LLM: {e}")
            return self._parse_notes_fallback(command)
    
    def _parse_notes_fallback(self, command: str) -> Optional[dict]:
        """
        Fallback regex-based notes command parsing.
        
        Args:
            command: User command text
            
        Returns:
            Parsed command dictionary or None
        """
        command_lower = command.lower()
        
        # Check for create note
        if 'create note' in command_lower or 'new note' in command_lower:
            return {
                'action': 'notes_create',
                'response': 'Creating note'
            }
        
        # Check for list notes
        if 'list notes' in command_lower or 'show notes' in command_lower or 'my notes' in command_lower:
            return {
                'action': 'notes_list',
                'response': 'Listing all notes'
            }
        
        # Check for show specific note by ID
        show_id_match = re.search(r'(?:show|view|open)\s+note\s+#?(\d+)', command_lower)
        if show_id_match:
            return {
                'action': 'notes_show_by_id',
                'note_id': int(show_id_match.group(1)),
                'response': f"Showing note #{show_id_match.group(1)}"
            }
        
        # Check for show specific note by name
        show_name_match = re.search(r'(?:show|view|open)\s+(.+?)\s+note', command_lower)
        if show_name_match:
            return {
                'action': 'notes_show',
                'note_name': show_name_match.group(1).strip(),
                'response': f"Showing note '{show_name_match.group(1).strip()}'"
            }
        
        # Check for rename note
        rename_match = re.search(r'rename\s+note\s+#?(\d+)\s+to\s+(.+?)$', command_lower)
        if rename_match:
            return {
                'action': 'notes_rename',
                'note_id': int(rename_match.group(1)),
                'new_name': rename_match.group(2).strip(),
                'response': 'Renaming note'
            }
        
        # Check for add entry
        add_match = re.search(r'add\s+(.+?)\s+to\s+(?:note\s+)?(.+?)$', command_lower)
        if add_match and 'add' in command_lower:
            return {
                'action': 'notes_add_entry',
                'note_identifier': add_match.group(2).strip(),
                'entry_text': add_match.group(1).strip(),
                'response': 'Adding entry'
            }
        
        # Check for edit entry
        edit_match = re.search(r'edit\s+entry\s+(\d+)\s+(?:in|from)\s+(.+?)\s+to\s+(.+?)$', command_lower)
        if edit_match:
            return {
                'action': 'notes_edit_entry',
                'note_identifier': edit_match.group(2).strip(),
                'entry_number': int(edit_match.group(1)),
                'new_text': edit_match.group(3).strip(),
                'response': f"Editing entry {edit_match.group(1)}"
            }
        
        # Check for delete entry
        delete_entry_match = re.search(r'delete\s+entry\s+(\d+)\s+from\s+(.+?)$', command_lower)
        if delete_entry_match:
            return {
                'action': 'notes_delete_entry',
                'note_identifier': delete_entry_match.group(2).strip(),
                'entry_number': int(delete_entry_match.group(1)),
                'response': f"Deleting entry {delete_entry_match.group(1)}"
            }
        
        # Check for delete note
        if 'delete note' in command_lower:
            delete_match = re.search(r'delete\s+note\s+(.+?)$', command_lower)
            if delete_match:
                return {
                    'action': 'notes_delete',
                    'note_identifier': delete_match.group(1).strip(),
                    'response': 'Deleting note'
                }
        
        return None
        
        # Check for delete item
        delete_item_keywords = ['delete item', 'remove item']
        if any(keyword in command_lower for keyword in delete_item_keywords):
            # Extract item number and note name
            delete_match = re.search(
                r'(?:delete|remove)\s+item\s+(\d+)\s+(?:from|in|of)\s+(.+?)$',
                command_lower
            )
            if delete_match:
                return {
                    'action': 'notes_delete_item',
                    'item_number': int(delete_match.group(1)),
                    'note_name': delete_match.group(2).strip(),
                    'response': f"Deleting item {delete_match.group(1)}"
                }
        
        # Check for complete item
        complete_keywords = ['mark item', 'complete item', 'finish item', 'done item']
        if any(keyword in command_lower for keyword in complete_keywords):
            # Extract item number and note name
            complete_match = re.search(
                r'(?:mark|complete|finish|done)\s+item\s+(\d+)\s+(?:as\s+)?(?:complete|done|finished)?\s*(?:in|from|of)?\s*(.+?)$',
                command_lower
            )
            if complete_match:
                return {
                    'action': 'notes_complete_item',
                    'item_number': int(complete_match.group(1)),
                    'note_name': complete_match.group(2).strip() if complete_match.group(2) else None,
                    'response': f"Marking item {complete_match.group(1)} as complete"
                }
        
        # Check for delete note
        delete_note_keywords = ['delete note', 'remove note']
        if any(keyword in command_lower for keyword in delete_note_keywords):
            # Extract note name
            delete_match = re.search(r'(?:delete|remove)\s+(?:note\s+)?(.+?)(?:\s+note)?$', command_lower)
            if delete_match:
                note_name = delete_match.group(1).strip().replace(' note', '')
                return {
                    'action': 'notes_delete',
                    'note_name': note_name,
                    'response': f"Deleting note '{note_name}'"
                }
        
        return None
