"""
Action executor for Bruno actions.

Executes BrunoActions on local system (timers, music, TTS, etc.).
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger("bruno.core.executor")


class ActionExecutor:
    """
    Executes BrunoActions on local system.
    
    This is separate from the interface so Discord can decide
    which actions to execute (e.g., TTS only if user wants it).
    """
    
    def __init__(self, timer_manager=None, music_manager=None, tts_engine=None, alarm_manager=None):
        """
        Initialize with Bruno subsystems.
        
        Args:
            timer_manager: TimerManager instance (optional)
            music_manager: MusicManager instance (optional)
            tts_engine: TTS engine instance (optional)
            alarm_manager: AlarmManager instance (optional)
        """
        self.timer_manager = timer_manager
        self.music_manager = music_manager
        self.tts_engine = tts_engine
        self.alarm_manager = alarm_manager
        
        logger.info("✅ ActionExecutor initialized")
    
    def execute(self, actions: List[Dict[str, Any]], 
                enable_tts: bool = True,
                enable_timers: bool = True,
                enable_music: bool = True,
                enable_alarms: bool = True) -> Dict[str, Any]:
        """
        Execute list of actions.
        
        Args:
            actions: List of BrunoAction dicts
            enable_tts: Whether to execute TTS actions
            enable_timers: Whether to execute timer actions
            enable_music: Whether to execute music actions
            enable_alarms: Whether to execute alarm actions
            
        Returns:
            Dict with execution results and any errors
        """
        results = {
            'success': True,
            'executed': [],
            'skipped': [],
            'errors': []
        }
        
        for action in actions:
            action_type = action.get('type')
            
            try:
                if action_type in ['timer_set', 'timer_status', 'timer_cancel']:
                    if enable_timers:
                        success = self.execute_timer_action(action)
                        if success:
                            results['executed'].append(action_type)
                        else:
                            results['errors'].append(f"Failed: {action_type}")
                    else:
                        results['skipped'].append(action_type)
                
                elif action_type in ['alarm_set', 'alarm_status', 'alarm_cancel']:
                    if enable_alarms:
                        success = self.execute_alarm_action(action)
                        if success:
                            results['executed'].append(action_type)
                        else:
                            results['errors'].append(f"Failed: {action_type}")
                    else:
                        results['skipped'].append(action_type)
                
                elif action_type in ['music_play', 'music_pause', 'music_resume', 
                                    'music_stop', 'music_next', 'music_skip', 'music_volume']:
                    if enable_music:
                        success = self.execute_music_action(action)
                        if success:
                            results['executed'].append(action_type)
                        else:
                            results['errors'].append(f"Failed: {action_type}")
                    else:
                        results['skipped'].append(action_type)
                
                elif action_type == 'speak':
                    if enable_tts:
                        success = self.execute_speak_action(action)
                        if success:
                            results['executed'].append(action_type)
                        else:
                            results['errors'].append(f"Failed: {action_type}")
                    else:
                        results['skipped'].append(action_type)
                
                else:
                    logger.warning(f"⚠️  Unknown action type: {action_type}")
                    results['skipped'].append(action_type)
            
            except Exception as e:
                logger.error(f"❌ Error executing {action_type}: {e}")
                results['errors'].append(f"{action_type}: {str(e)}")
                results['success'] = False
        
        logger.info(f"✅ Executed {len(results['executed'])} actions, "
                   f"skipped {len(results['skipped'])}, "
                   f"errors {len(results['errors'])}")
        
        return results
    
    def execute_timer_action(self, action: Dict[str, Any]) -> bool:
        """
        Execute timer-related action.
        
        Args:
            action: BrunoAction dict
            
        Returns:
            True if successful, False otherwise
        """
        if not self.timer_manager:
            logger.warning("⚠️  Timer manager not available")
            return False
        
        action_type = action.get('type')
        
        try:
            if action_type == 'timer_set':
                duration = action.get('duration_seconds')
                label = action.get('label', 'Discord Timer')
                
                timer_id = self.timer_manager.create_timer(duration, label)
                if timer_id:
                    logger.info(f"⏰ Created timer: {timer_id} ({label}, {duration}s)")
                    return True
                else:
                    logger.warning("⚠️  Failed to create timer (max limit reached?)")
                    return False
            
            elif action_type == 'timer_status':
                # Status is read-only, always succeeds
                logger.info("⏰ Timer status queried")
                return True
            
            elif action_type == 'timer_cancel':
                if self.timer_manager.has_active_timers():
                    self.timer_manager.cancel_all_timers()
                    logger.info("⏰ All timers cancelled")
                    return True
                else:
                    logger.info("⏰ No timers to cancel")
                    return True
            
            else:
                logger.warning(f"⚠️  Unknown timer action: {action_type}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Timer action failed: {e}")
            return False
    
    def execute_alarm_action(self, action: Dict[str, Any]) -> bool:
        """
        Execute alarm-related action.
        
        Args:
            action: BrunoAction dict
            
        Returns:
            True if successful, False otherwise
        """
        if not self.alarm_manager:
            logger.warning("⚠️  Alarm manager not available")
            return False
        
        action_type = action.get('type')
        
        try:
            if action_type == 'alarm_set':
                trigger_time = action.get('trigger_time')
                label = action.get('label', 'Discord Alarm')
                recurring = action.get('recurring', False)
                recurrence_interval = action.get('recurrence_interval')
                
                alarm_id = self.alarm_manager.create_alarm(
                    trigger_time=trigger_time,
                    label=label,
                    recurring=recurring,
                    recurrence_interval=recurrence_interval
                )
                
                if alarm_id:
                    logger.info(f"⏰ Created alarm: {alarm_id} ({label}, {trigger_time})")
                    return True
                else:
                    logger.warning("⚠️  Failed to create alarm (max limit reached?)")
                    return False
            
            elif action_type == 'alarm_status':
                # Status is read-only, always succeeds
                logger.info("⏰ Alarm status queried")
                return True
            
            elif action_type == 'alarm_cancel':
                if self.alarm_manager.has_active_alarms():
                    self.alarm_manager.cancel_all_alarms()
                    logger.info("⏰ All alarms cancelled")
                    return True
                else:
                    logger.info("⏰ No alarms to cancel")
                    return True
            
            else:
                logger.warning(f"⚠️  Unknown alarm action: {action_type}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Alarm action failed: {e}")
            return False
    
    def execute_music_action(self, action: Dict[str, Any]) -> bool:
        """
        Execute music-related action.
        
        Args:
            action: BrunoAction dict
            
        Returns:
            True if successful, False otherwise
        """
        if not self.music_manager:
            logger.warning("⚠️  Music manager not available")
            return False
        
        action_type = action.get('type')
        
        try:
            if action_type == 'music_play':
                query = action.get('query', '')
                if query:
                    # Default to playing all matching songs
                    result = self.music_manager.play_by_query(query, announce=False, play_all=True)
                    if result['success']:
                        # Store track info for retrieval by interface
                        action['_result'] = result
                        logger.info(f"🎵 Playing music: {result.get('track_name', query)}")
                    return result['success']
                else:
                    # No query - play all songs in library
                    self.music_manager.play_all_tracks(announce=False)
                    logger.info("🎵 Playing all music")
                    return True
            
            elif action_type == 'music_pause':
                result = self.music_manager.pause(announce=False)
                if result['success']:
                    action['_result'] = result
                    logger.info(f"🎵 Music paused: {result.get('track_name', 'unknown')}")
                return result['success']
            
            elif action_type == 'music_resume':
                result = self.music_manager.resume(announce=False)
                if result['success']:
                    action['_result'] = result
                    logger.info(f"🎵 Music resumed: {result.get('track_name', 'unknown')}")
                return result['success']
            
            elif action_type == 'music_stop':
                result = self.music_manager.stop(announce=False)
                if result['success']:
                    action['_result'] = result
                    logger.info(f"🎵 Music stopped: {result.get('track_name', 'unknown')}")
                return result['success']
            
            elif action_type in ['music_skip', 'music_next']:
                result = self.music_manager.skip_track(announce=False)
                if result['success']:
                    # Store track info for retrieval by interface
                    action['_result'] = result
                    logger.info(f"🎵 Skipped to: {result.get('track_name', 'next track')}")
                return result['success']
            
            elif action_type == 'music_volume':
                level = action.get('volume', 0.7)
                self.music_manager.set_volume(level, announce=False)
                logger.info(f"🎵 Volume set to {level}")
                return True
            
            else:
                logger.warning(f"⚠️  Unknown music action: {action_type}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Music action failed: {e}")
            return False
    
    def execute_speak_action(self, action: Dict[str, Any]) -> bool:
        """
        Execute TTS action.
        
        Args:
            action: BrunoAction dict
            
        Returns:
            True if successful, False otherwise
        """
        if not self.tts_engine:
            logger.warning("⚠️  TTS engine not available")
            return False
        
        try:
            text = action.get('text', '')
            if text:
                # Use non-blocking mode to prevent Discord heartbeat issues
                # Check which TTS engine and call appropriate method
                if hasattr(self.tts_engine, 'speak'):
                    # Check function signature to determine which parameter to use
                    import inspect
                    sig = inspect.signature(self.tts_engine.speak)
                    
                    if 'blocking' in sig.parameters:
                        # WindowsTTS with blocking parameter
                        self.tts_engine.speak(text, blocking=False)
                    elif 'wait' in sig.parameters:
                        # PiperTTS with wait parameter
                        self.tts_engine.speak(text, wait=False)
                    else:
                        # Old TTS engine without non-blocking support
                        self.tts_engine.speak(text)
                else:
                    logger.warning("⚠️  TTS engine has no speak method")
                    return False
                
                logger.info(f"🔊 Spoke: '{text[:50]}...'")
                return True
            else:
                logger.warning("⚠️  No text to speak")
                return False
        
        except Exception as e:
            logger.error(f"❌ TTS action failed: {e}")
            return False
