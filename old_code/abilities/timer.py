"""
Timer - Individual timer instance with progress tracking.
"""

import logging
import threading
import time
from typing import Callable, Optional


class Timer:
    """
    Individual timer instance with progress tracking.
    Runs in background thread and provides callbacks for progress and completion.
    """
    
    def __init__(
        self,
        timer_id: str,
        duration_seconds: int,
        label: str,
        on_progress: Callable[[int, int], None],  # (elapsed, remaining)
        on_complete: Callable[[str], None],  # (timer_id)
        progress_interval: int = 60,  # Announce every N seconds
        enable_30s_warning: bool = True
    ):
        """
        Initialize timer.
        
        Args:
            timer_id: Unique identifier for this timer
            duration_seconds: Total duration in seconds
            label: Human-readable label for the timer
            on_progress: Callback for progress updates (elapsed, remaining)
            on_complete: Callback when timer completes (timer_id)
            progress_interval: Seconds between progress announcements (default: 60)
            enable_30s_warning: Whether to announce 30-second warning
        """
        self.timer_id = timer_id
        self.duration = duration_seconds
        self.label = label
        self.start_time = None
        self.end_time = None
        self.cancelled = False
        self.paused = False
        self.pause_time = None
        self.pause_duration = 0
        
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.progress_interval = progress_interval
        self.enable_30s_warning = enable_30s_warning
        
        self.thread = None
        self.running = False
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self._3min_warning_given = False
    
    def start(self):
        """Start the timer in background thread."""
        if self.running:
            self.logger.warning(f"Timer {self.timer_id} is already running")
            return
        
        self.start_time = time.time()
        self.end_time = self.start_time + self.duration
        self.running = True
        
        self.thread = threading.Thread(
            target=self._run,
            daemon=True,
            name=f"Timer-{self.timer_id}"
        )
        self.thread.start()
        self.logger.info(f"✅ Timer started: {self.timer_id} ({self.label})")
    
    def _run(self):
        """
        Timer execution loop with progress updates.
        Runs in background thread.
        """
        last_announcement = 0
        
        while self.running and not self.cancelled:
            current_time = time.time()
            elapsed = current_time - self.start_time - self.pause_duration
            remaining = self.duration - elapsed
            
            # Check if timer completed
            if remaining <= 0:
                self.running = False
                if self.on_complete:
                    try:
                        self.on_complete(self.timer_id)
                    except Exception as e:
                        self.logger.error(f"Error in completion callback: {e}")
                break
            
            # Special 3-minute warning (only announce once at 3 minutes remaining)
            if not self._3min_warning_given and 175 < remaining <= 180:
                self._3min_warning_given = True
                if self.on_progress:
                    try:
                        self.on_progress(int(elapsed), int(remaining))
                    except Exception as e:
                        self.logger.error(f"Error in 3-minute warning callback: {e}")
            
            # Sleep for 1 second before next check
            time.sleep(1)
        
        self.logger.info(f"Timer {self.timer_id} finished running")
    
    def cancel(self):
        """Cancel the timer."""
        self.cancelled = True
        self.running = False
        self.logger.info(f"❌ Timer cancelled: {self.timer_id}")
    
    def pause(self):
        """Pause the timer."""
        if not self.paused and self.running:
            self.paused = True
            self.pause_time = time.time()
            self.logger.info(f"⏸️  Timer paused: {self.timer_id}")
    
    def resume(self):
        """Resume the timer."""
        if self.paused:
            self.pause_duration += time.time() - self.pause_time
            self.paused = False
            self.pause_time = None
            self.logger.info(f"▶️  Timer resumed: {self.timer_id}")
    
    def remaining_time(self) -> int:
        """
        Get remaining time in seconds.
        
        Returns:
            Seconds remaining (0 if timer is complete or cancelled)
        """
        if not self.running or self.cancelled:
            return 0
        
        current_time = time.time()
        elapsed = current_time - self.start_time - self.pause_duration
        remaining = self.duration - elapsed
        return max(0, int(remaining))
    
    def elapsed_time(self) -> int:
        """
        Get elapsed time in seconds.
        
        Returns:
            Seconds elapsed (accounting for pauses)
        """
        if not self.start_time:
            return 0
        
        current_time = time.time()
        elapsed = current_time - self.start_time - self.pause_duration
        return max(0, int(elapsed))
    
    def status(self) -> dict:
        """
        Get timer status.
        
        Returns:
            Dictionary with timer details
        """
        return {
            'id': self.timer_id,
            'label': self.label,
            'duration': self.duration,
            'remaining': self.remaining_time(),
            'elapsed': self.elapsed_time(),
            'running': self.running,
            'paused': self.paused,
            'cancelled': self.cancelled
        }
