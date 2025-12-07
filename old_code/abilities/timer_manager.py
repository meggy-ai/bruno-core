"""
TimerManager - Manages multiple timers with progress tracking.
"""

import logging
import platform
import threading
from typing import Dict, List, Optional

from .timer import Timer
from bruno.utils.config import BrunoConfig

# Import winsound only on Windows
try:
    if platform.system() == 'Windows':
        import winsound
    else:
        winsound = None
except ImportError:
    winsound = None


class TimerManager:
    """
    Manages multiple concurrent timers with progress tracking.
    Handles timer creation, progress announcements, and completion notifications.
    """
    
    def __init__(self, tts_engine, config: BrunoConfig, external_callback=None):
        """
        Initialize timer manager.
        
        Args:
            tts_engine: TTS engine for voice announcements
            config: Bruno configuration
            external_callback: Optional callback for external notifications (e.g., Discord messages)
                              Format: callback(event_type, message_text, timer_info)
                              where event_type is 'progress' or 'complete'
        """
        self.tts = tts_engine
        self.config = config
        self.external_callback = external_callback
        self.timers: Dict[str, Timer] = {}
        self.timer_counter = 0
        self.lock = threading.RLock()  # Use RLock for reentrant lock acquisition
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Configuration
        self.progress_interval = config.get('bruno.timer.progress_interval', 60)
        self.enable_30s_warning = config.get('bruno.timer.enable_30s_warning', True)
        self.max_concurrent = config.get('bruno.timer.max_concurrent_timers', 5)
        
        self.logger.info("✅ TimerManager initialized")
    
    def set_external_callback(self, callback):
        """
        Set external callback for timer notifications.
        
        Args:
            callback: Callback function(event_type, message, timer_info)
                     where event_type is 'progress' or 'complete'
        """
        self.external_callback = callback
        self.logger.info("✅ External callback registered for timer notifications")
    
    def create_timer(
        self,
        duration_seconds: int,
        label: Optional[str] = None
    ) -> Optional[str]:
        """
        Create and start a new timer.
        
        Args:
            duration_seconds: Duration in seconds
            label: Optional label for the timer
            
        Returns:
            Timer ID if successful, None if max timers reached
        """
        with self.lock:
            # Check max concurrent timers
            if len(self.timers) >= self.max_concurrent:
                self.logger.warning(f"Maximum concurrent timers ({self.max_concurrent}) reached")
                return None
            
            self.timer_counter += 1
            timer_id = f"timer_{self.timer_counter}"
            
            # Generate label if not provided
            if label is None:
                label = self._format_duration(duration_seconds) + " timer"
            
            # Create timer
            timer = Timer(
                timer_id=timer_id,
                duration_seconds=duration_seconds,
                label=label,
                on_progress=self._on_timer_progress,
                on_complete=self._on_timer_complete,
                progress_interval=self.progress_interval,
                enable_30s_warning=self.enable_30s_warning
            )
            
            self.timers[timer_id] = timer
            timer.start()
            
            self.logger.info(f"✅ Timer created: {timer_id} ({label}, {duration_seconds}s)")
            return timer_id
    
    def _on_timer_progress(self, elapsed: int, remaining: int):
        """
        Callback for timer progress updates.
        Announces remaining time via TTS and external callback.
        
        Args:
            elapsed: Seconds elapsed
            remaining: Seconds remaining
        """
        time_str = self._format_time_remaining(remaining)
        message = f"⏱️ {time_str} remaining"
        
        self.logger.info(f"⏱️  Timer progress: {time_str} remaining")
        
        # Speak remaining time
        if self.tts:
            try:
                self.tts.speak(f"{time_str} remaining")
            except Exception as e:
                self.logger.error(f"Error speaking progress: {e}")
        
        # Send to external callback (e.g., Discord)
        if self.external_callback:
            try:
                self.external_callback('progress', message, {'elapsed': elapsed, 'remaining': remaining})
            except Exception as e:
                self.logger.error(f"Error in external callback: {e}")
    
    def _on_timer_complete(self, timer_id: str):
        """
        Callback when timer completes.
        Announces completion and removes timer.
        
        Args:
            timer_id: ID of completed timer
        """
        with self.lock:
            timer = self.timers.get(timer_id)
            if timer:
                message = f"⏰ Timer is up! {timer.label} completed."
                self.logger.info(f"⏰ Timer completed: {timer_id} ({timer.label})")
                
                # Play alarm sound (3 beeps) - Windows only
                if winsound:
                    try:
                        for _ in range(3):
                            winsound.Beep(1000, 300)  # 1000 Hz for 300ms
                    except Exception as e:
                        self.logger.warning(f"⚠️  Could not play alarm sound: {e}")
                else:
                    self.logger.debug("Alarm sound not available on this platform")
                
                # Alert user via TTS
                if self.tts:
                    try:
                        self.tts.speak(f"Timer is up! {timer.label} completed.")
                    except Exception as e:
                        self.logger.error(f"Error speaking completion: {e}")
                
                # Send to external callback (e.g., Discord)
                if self.external_callback:
                    try:
                        self.external_callback('complete', message, {'timer_id': timer_id, 'label': timer.label})
                    except Exception as e:
                        self.logger.error(f"Error in external callback: {e}")
                
                # Remove completed timer
                del self.timers[timer_id]
    
    def cancel_timer(self, timer_id: str) -> bool:
        """
        Cancel a specific timer.
        
        Args:
            timer_id: ID of timer to cancel
            
        Returns:
            True if timer was cancelled, False if not found
        """
        with self.lock:
            timer = self.timers.get(timer_id)
            if timer:
                timer.cancel()
                del self.timers[timer_id]
                self.logger.info(f"❌ Timer cancelled: {timer_id}")
                return True
            return False
    
    def cancel_last_timer(self) -> bool:
        """
        Cancel the most recently created timer.
        
        Returns:
            True if timer was cancelled, False if no timers exist
        """
        with self.lock:
            if not self.timers:
                return False
            
            # Get most recent timer (highest counter)
            latest_id = max(self.timers.keys(), key=lambda k: int(k.split('_')[1]))
            return self.cancel_timer(latest_id)
    
    def cancel_all_timers(self):
        """Cancel all active timers."""
        with self.lock:
            for timer in list(self.timers.values()):
                timer.cancel()
            self.timers.clear()
            self.logger.info("❌ All timers cancelled")
    
    def list_active_timers(self) -> List[dict]:
        """
        Get list of all active timers.
        
        Returns:
            List of timer status dictionaries
        """
        with self.lock:
            return [timer.status() for timer in self.timers.values()]
    
    def get_timer_status(self, timer_id: str) -> Optional[dict]:
        """
        Get status of specific timer.
        
        Args:
            timer_id: ID of timer
            
        Returns:
            Timer status dictionary or None if not found
        """
        with self.lock:
            timer = self.timers.get(timer_id)
            return timer.status() if timer else None
    
    def has_active_timers(self) -> bool:
        """
        Check if any timers are active.
        
        Returns:
            True if at least one timer is running
        """
        with self.lock:
            return len(self.timers) > 0
    
    def _format_time_remaining(self, seconds: int) -> str:
        """
        Format seconds into human-readable time.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted string (e.g., "5 minutes", "2 hours and 30 minutes")
        """
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''}"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            if secs > 0:
                return f"{minutes} minute{'s' if minutes != 1 else ''} and {secs} second{'s' if secs != 1 else ''}"
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours} hour{'s' if hours != 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}"
            return f"{hours} hour{'s' if hours != 1 else ''}"
    
    def _format_duration(self, seconds: int) -> str:
        """
        Format duration for timer label (concise version).
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted string (e.g., "5-minute", "2-hour")
        """
        if seconds < 60:
            return f"{seconds}-second"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}-minute"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}-hour-{minutes}-minute"
            return f"{hours}-hour"
    
    def shutdown(self):
        """Shutdown timer manager and cancel all timers."""
        self.logger.info("Shutting down TimerManager...")
        self.cancel_all_timers()
        self.logger.info("👋 TimerManager shutdown complete")
