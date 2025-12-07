"""
MusicPlayer - Handles audio playback using pygame mixer.
Runs in background, non-blocking music playback.
"""

import logging
from pathlib import Path
from typing import Optional, List
from collections import deque

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    

class MusicPlayer:
    """
    Handles music playback using pygame mixer.
    Non-blocking playback that runs in background.
    """
    
    def __init__(self):
        """Initialize music player."""
        self.current_file: Optional[Path] = None
        self.is_playing = False
        self.is_paused = False
        self.volume = 0.7  # Default volume (0.0 to 1.0)
        self.playlist: deque = deque()  # Queue of songs to play
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if not PYGAME_AVAILABLE:
            self.logger.error("❌ pygame not installed. Install: pip install pygame")
            raise ImportError("pygame required for music playback")
        
        # Initialize pygame mixer (if not already initialized by TTS)
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                self.logger.info("✅ Music player initialized (pygame mixer)")
            else:
                self.logger.info("✅ Music player initialized (using existing pygame mixer)")
            
            # Set up end event for auto-advancing playlist
            pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize pygame mixer: {e}")
            raise
    
    def play(self, file_path: Path, queue_mode: bool = False) -> bool:
        """
        Play audio file.
        
        Args:
            file_path: Path to audio file
            queue_mode: If True, don't clear the playlist queue
            
        Returns:
            True if playback started successfully
        """
        try:
            # Stop current playback if any (but keep queue if queue_mode)
            if not queue_mode:
                self.stop()
            else:
                pygame.mixer.music.stop()
            
            # Verify file exists
            if not file_path.exists():
                self.logger.error(f"❌ File not found: {file_path}")
                return False
            
            # Load and play new file
            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
            
            self.current_file = file_path
            self.is_playing = True
            self.is_paused = False
            
            self.logger.info(f"🎵 Playing: {file_path.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to play {file_path}: {e}")
            return False
    
    def pause(self) -> bool:
        """
        Pause current playback.
        
        Returns:
            True if paused successfully
        """
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.logger.info("⏸️  Music paused")
            return True
        return False
    
    def resume(self) -> bool:
        """
        Resume paused playback.
        
        Returns:
            True if resumed successfully
        """
        if self.is_playing and self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.logger.info("▶️  Music resumed")
            return True
        return False
    
    def stop(self) -> bool:
        """
        Stop current playback and clear playlist.
        
        Returns:
            True if stopped successfully
        """
        if self.is_playing or self.is_paused:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            self.current_file = None
            self.playlist.clear()
            self.logger.info("⏹️  Music stopped")
            return True
        return False
    
    def set_volume(self, level: float) -> bool:
        """
        Set volume level.
        
        Args:
            level: Volume (0.0 to 1.0)
            
        Returns:
            True if volume set successfully
        """
        if 0.0 <= level <= 1.0:
            self.volume = level
            if self.is_playing:
                pygame.mixer.music.set_volume(level)
            self.logger.info(f"🔊 Volume: {int(level * 100)}%")
            return True
        else:
            self.logger.warning(f"⚠️  Invalid volume level: {level} (must be 0.0-1.0)")
            return False
    
    def get_volume(self) -> float:
        """
        Get current volume level.
        
        Returns:
            Volume level (0.0 to 1.0)
        """
        return self.volume
    
    def is_active(self) -> bool:
        """
        Check if music is currently playing (not paused).
        
        Returns:
            True if actively playing
        """
        return self.is_playing and not self.is_paused and pygame.mixer.music.get_busy()
    
    def get_position(self) -> float:
        """
        Get current playback position in seconds.
        
        Returns:
            Position in seconds
        """
        if self.is_playing:
            # pygame returns position in milliseconds
            return pygame.mixer.music.get_pos() / 1000.0
        return 0.0
    
    def get_current_file(self) -> Optional[Path]:
        """
        Get currently loaded file.
        
        Returns:
            Path to current file or None
        """
        return self.current_file
    
    def set_playlist(self, file_paths: List[Path]) -> int:
        """
        Set playlist of songs to play.
        
        Args:
            file_paths: List of file paths to queue
            
        Returns:
            Number of tracks queued
        """
        self.playlist.clear()
        for path in file_paths:
            if path.exists():
                self.playlist.append(path)
        
        self.logger.info(f"📝 Playlist set: {len(self.playlist)} tracks")
        return len(self.playlist)
    
    def add_to_playlist(self, file_path: Path) -> bool:
        """
        Add a track to the end of the playlist.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            True if added successfully
        """
        if file_path.exists():
            self.playlist.append(file_path)
            self.logger.info(f"➕ Added to playlist: {file_path.name}")
            return True
        return False
    
    def play_next(self) -> bool:
        """
        Play next track in playlist.
        
        Returns:
            True if next track started playing
        """
        if not self.playlist:
            self.logger.info("📭 Playlist empty")
            self.is_playing = False
            return False
        
        next_file = self.playlist.popleft()
        return self.play(next_file, queue_mode=True)
    
    def skip(self) -> bool:
        """
        Skip to next track.
        
        Returns:
            True if skipped successfully
        """
        if self.playlist:
            self.logger.info("⏭️  Skipping to next track")
            return self.play_next()
        else:
            self.logger.info("⚠️  No more tracks in playlist")
            self.stop()
            return False
    
    def check_and_advance(self) -> bool:
        """
        Check if current song finished and advance to next.
        Call this periodically when playlist is active.
        
        Returns:
            True if advanced to next track
        """
        # Check if music has finished
        if self.is_playing and not self.is_paused and not pygame.mixer.music.get_busy():
            self.logger.info("✅ Track finished")
            if self.playlist:
                return self.play_next()
            else:
                self.logger.info("🏁 Playlist completed")
                self.is_playing = False
                return False
        return False
    
    def get_playlist_count(self) -> int:
        """
        Get number of tracks remaining in playlist.
        
        Returns:
            Number of tracks
        """
        return len(self.playlist)
    
    def shutdown(self):
        """Cleanup and shutdown player."""
        self.stop()
        try:
            pygame.mixer.quit()
            self.logger.info("👋 Music player shutdown")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
