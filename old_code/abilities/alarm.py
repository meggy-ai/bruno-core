"""
Alarm - Individual alarm instance with scheduled time trigger.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional


class Alarm:
    """
    Individual alarm instance that triggers at a specific time.
    Runs in background thread and provides callback when alarm time is reached.
    """
    
    def __init__(
        self,
        alarm_id: str,
        trigger_time: datetime,
        label: str,
        on_trigger: Callable[[str], None],  # (alarm_id)
        recurring: bool = False,
        recurrence_interval: Optional[int] = None  # seconds between recurrences
    ):
        """
        Initialize alarm.
        
        Args:
            alarm_id: Unique identifier for this alarm
            trigger_time: When the alarm should trigger
            label: Human-readable label for the alarm
            on_trigger: Callback when alarm triggers (alarm_id)
            recurring: Whether alarm should repeat
            recurrence_interval: Seconds between recurrences (for recurring alarms)
        """
        self.alarm_id = alarm_id
        self.trigger_time = trigger_time
        self.label = label
        self.recurring = recurring
        self.recurrence_interval = recurrence_interval
        
        self.on_trigger = on_trigger
        self.cancelled = False
        
        self.thread = None
        self.running = False
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def start(self):
        """Start the alarm in background thread."""
        if self.running:
            self.logger.warning(f"Alarm {self.alarm_id} is already running")
            return
        
        self.running = True
        
        self.thread = threading.Thread(
            target=self._run,
            daemon=True,
            name=f"Alarm-{self.alarm_id}"
        )
        self.thread.start()
        self.logger.info(f"✅ Alarm started: {self.alarm_id} ({self.label}) at {self.trigger_time}")
    
    def _run(self):
        """
        Alarm execution loop.
        Runs in background thread and waits until trigger time.
        """
        while self.running and not self.cancelled:
            current_time = datetime.now()
            
            # Check if alarm time has been reached
            if current_time >= self.trigger_time:
                self.logger.info(f"⏰ Alarm triggered: {self.alarm_id} ({self.label})")
                
                # Trigger callback
                if self.on_trigger:
                    try:
                        self.on_trigger(self.alarm_id)
                    except Exception as e:
                        self.logger.error(f"Error in trigger callback: {e}")
                
                # Handle recurring alarms
                if self.recurring and self.recurrence_interval:
                    self.trigger_time = current_time + timedelta(seconds=self.recurrence_interval)
                    self.logger.info(f"🔄 Recurring alarm rescheduled to {self.trigger_time}")
                else:
                    self.running = False
                    break
            else:
                # Sleep for a short interval before checking again
                # Use smaller interval for more precise triggering
                time_until_trigger = (self.trigger_time - current_time).total_seconds()
                sleep_time = min(1.0, max(0.1, time_until_trigger))  # Sleep 0.1-1 seconds
                time.sleep(sleep_time)
    
    def cancel(self):
        """Cancel the alarm."""
        self.cancelled = True
        self.running = False
        self.logger.info(f"❌ Alarm cancelled: {self.alarm_id}")
    
    def time_until_trigger(self) -> float:
        """
        Get seconds until alarm triggers.
        
        Returns:
            Seconds until trigger (negative if past trigger time)
        """
        return (self.trigger_time - datetime.now()).total_seconds()
    
    def status(self) -> dict:
        """
        Get alarm status.
        
        Returns:
            Dictionary with alarm information
        """
        time_remaining = self.time_until_trigger()
        
        return {
            'alarm_id': self.alarm_id,
            'label': self.label,
            'trigger_time': self.trigger_time.isoformat(),
            'time_remaining_seconds': max(0, time_remaining),
            'recurring': self.recurring,
            'recurrence_interval': self.recurrence_interval,
            'running': self.running,
            'cancelled': self.cancelled
        }
