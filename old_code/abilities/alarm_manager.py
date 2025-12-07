"""
AlarmManager - Manages multiple alarms with scheduled time triggers.
"""

import logging
import platform
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .alarm import Alarm
from bruno.utils.config import BrunoConfig

# Import winsound only on Windows
try:
    if platform.system() == 'Windows':
        import winsound
    else:
        winsound = None
except ImportError:
    winsound = None


class AlarmManager:
    """
    Manages multiple concurrent alarms with scheduled time triggers.
    Handles alarm creation, triggering notifications, and recurring alarms.
    """
    
    def __init__(self, tts_engine, config: BrunoConfig, external_callback=None):
        """
        Initialize alarm manager.
        
        Args:
            tts_engine: TTS engine for voice announcements
            config: Bruno configuration
            external_callback: Optional callback for external notifications (e.g., Discord messages)
                              Format: callback(event_type, message_text, alarm_info)
                              where event_type is 'trigger'
        """
        self.tts = tts_engine
        self.config = config
        self.external_callback = external_callback
        self.alarms: Dict[str, Alarm] = {}
        self.alarm_counter = 0
        self.lock = threading.RLock()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Configuration
        self.max_concurrent = config.get('bruno.alarm.max_concurrent_alarms', 10)
        self.default_alarm_sound_beeps = config.get('bruno.alarm.sound_beeps', 5)
        
        self.logger.info("✅ AlarmManager initialized")
    
    def set_external_callback(self, callback):
        """
        Set external callback for alarm notifications.
        
        Args:
            callback: Callback function(event_type, message, alarm_info)
                     where event_type is 'trigger'
        """
        self.external_callback = callback
        self.logger.info("✅ External callback registered for alarm notifications")
    
    def create_alarm(
        self,
        trigger_time: datetime,
        label: Optional[str] = None,
        recurring: bool = False,
        recurrence_interval: Optional[int] = None
    ) -> Optional[str]:
        """
        Create and start a new alarm.
        
        Args:
            trigger_time: When the alarm should trigger
            label: Optional label for the alarm
            recurring: Whether alarm should repeat
            recurrence_interval: Seconds between recurrences (for recurring alarms)
            
        Returns:
            Alarm ID if successful, None if max alarms reached or invalid time
        """
        with self.lock:
            # Validate trigger time
            if trigger_time <= datetime.now():
                self.logger.warning("Cannot create alarm in the past")
                return None
            
            # Check max concurrent alarms
            if len(self.alarms) >= self.max_concurrent:
                self.logger.warning(f"Maximum concurrent alarms ({self.max_concurrent}) reached")
                return None
            
            self.alarm_counter += 1
            alarm_id = f"alarm_{self.alarm_counter}"
            
            # Generate label if not provided
            if label is None:
                label = f"Alarm at {trigger_time.strftime('%I:%M %p')}"
            
            # Create alarm
            alarm = Alarm(
                alarm_id=alarm_id,
                trigger_time=trigger_time,
                label=label,
                on_trigger=self._on_alarm_trigger,
                recurring=recurring,
                recurrence_interval=recurrence_interval
            )
            
            self.alarms[alarm_id] = alarm
            alarm.start()
            
            self.logger.info(f"✅ Alarm created: {alarm_id} ({label}, {trigger_time})")
            return alarm_id
    
    def create_alarm_in(
        self,
        seconds: int,
        label: Optional[str] = None,
        recurring: bool = False,
        recurrence_interval: Optional[int] = None
    ) -> Optional[str]:
        """
        Create alarm that triggers after specified seconds from now.
        
        Args:
            seconds: Seconds from now when alarm should trigger
            label: Optional label for the alarm
            recurring: Whether alarm should repeat
            recurrence_interval: Seconds between recurrences
            
        Returns:
            Alarm ID if successful, None otherwise
        """
        trigger_time = datetime.now() + timedelta(seconds=seconds)
        return self.create_alarm(trigger_time, label, recurring, recurrence_interval)
    
    def _on_alarm_trigger(self, alarm_id: str):
        """
        Callback when alarm triggers.
        Announces alarm and handles recurring logic.
        
        Args:
            alarm_id: ID of triggered alarm
        """
        with self.lock:
            alarm = self.alarms.get(alarm_id)
            if alarm:
                message = f"⏰ Alarm! {alarm.label}"
                self.logger.info(f"⏰ Alarm triggered: {alarm_id} ({alarm.label})")
                
                # Play alarm sound (5 beeps by default) - Windows only
                if winsound:
                    try:
                        for _ in range(self.default_alarm_sound_beeps):
                            winsound.Beep(1200, 400)  # 1200 Hz for 400ms
                    except Exception as e:
                        self.logger.warning(f"⚠️  Could not play alarm sound: {e}")
                else:
                    self.logger.debug("Alarm sound not available on this platform")
                
                # Alert user via TTS
                if self.tts:
                    try:
                        self.tts.speak(f"Alarm! {alarm.label}")
                    except Exception as e:
                        self.logger.error(f"Error speaking alarm: {e}")
                
                # Send to external callback (e.g., Discord)
                if self.external_callback:
                    try:
                        self.logger.info(f"📨 Calling external callback for alarm {alarm_id}")
                        self.external_callback('trigger', message, {
                            'alarm_id': alarm_id,
                            'label': alarm.label,
                            'recurring': alarm.recurring
                        })
                        self.logger.info(f"✅ External callback completed for alarm {alarm_id}")
                    except Exception as e:
                        self.logger.error(f"Error in external callback: {e}")
                else:
                    self.logger.warning(f"⚠️  No external callback set for alarm {alarm_id}")
                
                # Remove non-recurring alarms
                if not alarm.recurring:
                    del self.alarms[alarm_id]
    
    def cancel_alarm(self, alarm_id: str) -> bool:
        """
        Cancel a specific alarm.
        
        Args:
            alarm_id: ID of alarm to cancel
            
        Returns:
            True if alarm was cancelled, False if not found
        """
        with self.lock:
            alarm = self.alarms.get(alarm_id)
            if alarm:
                alarm.cancel()
                del self.alarms[alarm_id]
                self.logger.info(f"❌ Alarm cancelled: {alarm_id}")
                return True
            return False
    
    def cancel_last_alarm(self) -> bool:
        """
        Cancel the most recently created alarm.
        
        Returns:
            True if alarm was cancelled, False if no alarms exist
        """
        with self.lock:
            if not self.alarms:
                return False
            
            # Get most recent alarm (highest counter)
            latest_id = max(self.alarms.keys(), key=lambda k: int(k.split('_')[1]))
            return self.cancel_alarm(latest_id)
    
    def cancel_all_alarms(self):
        """Cancel all active alarms."""
        with self.lock:
            for alarm in list(self.alarms.values()):
                alarm.cancel()
            self.alarms.clear()
            self.logger.info("❌ All alarms cancelled")
    
    def list_active_alarms(self) -> List[dict]:
        """
        Get list of all active alarms.
        
        Returns:
            List of alarm status dictionaries sorted by trigger time
        """
        with self.lock:
            alarms = [alarm.status() for alarm in self.alarms.values()]
            # Sort by trigger time
            alarms.sort(key=lambda x: x['trigger_time'])
            return alarms
    
    def get_alarm_status(self, alarm_id: str) -> Optional[dict]:
        """
        Get status of specific alarm.
        
        Args:
            alarm_id: ID of alarm
            
        Returns:
            Alarm status dictionary or None if not found
        """
        with self.lock:
            alarm = self.alarms.get(alarm_id)
            return alarm.status() if alarm else None
    
    def has_active_alarms(self) -> bool:
        """
        Check if any alarms are active.
        
        Returns:
            True if at least one alarm is scheduled
        """
        with self.lock:
            return len(self.alarms) > 0
    
    def get_next_alarm(self) -> Optional[dict]:
        """
        Get the next alarm to trigger.
        
        Returns:
            Alarm status dictionary of next alarm, or None if no alarms
        """
        with self.lock:
            if not self.alarms:
                return None
            
            # Find alarm with earliest trigger time
            next_alarm = min(
                self.alarms.values(),
                key=lambda a: a.trigger_time
            )
            return next_alarm.status()
    
    def _format_time_until(self, seconds: float) -> str:
        """
        Format seconds into human-readable time until alarm.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted string (e.g., "in 5 minutes", "in 2 hours")
        """
        seconds = int(seconds)
        
        if seconds < 60:
            return f"in {seconds} second{'s' if seconds != 1 else ''}"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"in {minutes} minute{'s' if minutes != 1 else ''}"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"in {hours} hour{'s' if hours != 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}"
            return f"in {hours} hour{'s' if hours != 1 else ''}"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            if hours > 0:
                return f"in {days} day{'s' if days != 1 else ''} and {hours} hour{'s' if hours != 1 else ''}"
            return f"in {days} day{'s' if days != 1 else ''}"
    
    def shutdown(self):
        """Shutdown alarm manager and cancel all alarms."""
        self.logger.info("Shutting down AlarmManager...")
        self.cancel_all_alarms()
        self.logger.info("👋 AlarmManager shutdown complete")
