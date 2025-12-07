"""
MusicManager - Coordinates music playback with library search and TTS announcements.
"""

import logging
from pathlib import Path
from typing import Optional

from bruno.abilities.media_library import MediaLibrary, Track
from bruno.abilities.music_player import MusicPlayer
from bruno.tts.windows_tts import WindowsTTS
from bruno.utils.config import BrunoConfig


class MusicManager:
    """
    Coordinates music playback with library and TTS.
    High-level interface for music commands.
    """
    
    def __init__(self, config: BrunoConfig):
        """
        Initialize music manager.
        
        Args:
            config: Bruno configuration
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        media_dir = Path(config.get('music.media_directory', 'media'))
        self.library = MediaLibrary(media_dir)
        self.player = MusicPlayer()
        
        # Initialize TTS
        tts_config = {
            'rate': config.get('tts.rate', 0),
            'volume': config.get('tts.volume', 100)
        }
        self.tts = WindowsTTS(**tts_config)
        
        # Set volume from config
        volume = config.get('music.default_volume', 0.7)
        self.player.set_volume(volume)
        
        self.logger.info(f"✅ Music manager initialized ({len(self.library.tracks)} tracks)")
    
    def play_by_query(self, query: str, announce: bool = True, play_all: bool = False) -> dict:
        """
        Search library and play matching track(s).
        
        Args:
            query: Search query (e.g., "meditation", "jazz")
            announce: Whether to announce via TTS
            play_all: If True, play all matching tracks; if False, play only first
            
        Returns:
            Dictionary with 'success', 'track_name', 'track_count', 'category'
        """
        # Search library - get more results if play_all is True
        max_results = 1000 if play_all else 10
        matches = self.library.search(query, max_results=max_results)
        
        if not matches:
            self.logger.warning(f"⚠️  No tracks found for: {query}")
            if announce:
                # Show available categories
                categories = self.library.get_categories()
                if categories:
                    cat_list = ", ".join(categories)
                    self.tts.speak(f"Sorry, I couldn't find any {query} music. Available categories: {cat_list}", blocking=False)
                else:
                    self.tts.speak(f"Sorry, I couldn't find any {query} music in your library.", blocking=False)
            return {'success': False, 'track_name': None, 'track_count': 0, 'category': None}
        
        if play_all:
            # Play all matching tracks
            track_paths = [track.file_path for track in matches]
            
            # Play first track
            first_track = matches[0]
            success = self.player.play(first_track.file_path)
            
            if success:
                # Queue remaining tracks
                if len(matches) > 1:
                    self.player.set_playlist([track.file_path for track in matches[1:]])
                
                self.logger.info(f"🎵 Playing {len(matches)} tracks starting with: {first_track.title}")
                if announce:
                    category_name = first_track.category.replace('_', ' ').title()
                    self.tts.speak(f"Playing {len(matches)} {category_name} songs", blocking=False)
                
                return {
                    'success': True,
                    'track_name': first_track.title,
                    'track_count': len(matches),
                    'category': first_track.category
                }
        else:
            # Play first match only
            track = matches[0]
            success = self.player.play(track.file_path)
            
            if success:
                self.logger.info(f"🎵 Playing: {track.title} (category: {track.category})")
                if announce:
                    # Just say "playing" - don't need full title
                    category_name = track.category.replace('_', ' ').title()
                    self.tts.speak(f"Playing {category_name} music", blocking=False)
                
                return {
                    'success': True,
                    'track_name': track.title,
                    'track_count': 1,
                    'category': track.category
                }
        
        return {'success': False, 'track_name': None, 'track_count': 0, 'category': None}
    
    def play_track(self, track: Track, announce: bool = True) -> bool:
        """
        Play specific track.
        
        Args:
            track: Track to play
            announce: Whether to announce via TTS
            
        Returns:
            True if playback started successfully
        """
        success = self.player.play(track.file_path)
        
        if success and announce:
            self.tts.speak(f"Now playing {track.title}")
        
        return success
    
    def play_all_tracks(self, announce: bool = True) -> bool:
        """
        Play all tracks in library.
        
        Args:
            announce: Whether to announce via TTS
            
        Returns:
            True if playback started successfully
        """
        all_tracks = self.library.get_all_tracks()
        
        if not all_tracks:
            self.logger.warning("⚠️  No tracks in library")
            if announce:
                self.tts.speak("Your music library is empty.", blocking=False)
            return False
        
        # Play first track
        first_track = all_tracks[0]
        success = self.player.play(first_track.file_path)
        
        if success:
            # Queue remaining tracks
            if len(all_tracks) > 1:
                self.player.set_playlist([track.file_path for track in all_tracks[1:]])
            
            self.logger.info(f"🎵 Playing all {len(all_tracks)} tracks")
            if announce:
                self.tts.speak(f"Playing all {len(all_tracks)} songs", blocking=False)
        
        return success
    
    def skip_track(self, announce: bool = True) -> dict:
        """
        Skip to next track in playlist.
        
        Args:
            announce: Whether to announce via TTS
            
        Returns:
            Dictionary with 'success', 'track_name'
        """
        success = self.player.skip()
        
        if success:
            current = self.player.get_current_file()
            track_name = current.name if current else None
            
            if announce:
                if track_name:
                    self.tts.speak(f"Skipping to {track_name}", blocking=False)
                else:
                    self.tts.speak("Skipping", blocking=False)
            
            return {
                'success': True,
                'track_name': track_name
            }
        else:
            if announce:
                self.tts.speak("No more tracks", blocking=False)
            
            return {
                'success': False,
                'track_name': None
            }
    
    def update_playback(self):
        """
        Update playback state and auto-advance to next track if needed.
        Call this periodically (e.g., in main loop).
        """
        self.player.check_and_advance()
    
    def pause(self, announce: bool = True) -> dict:
        """
        Pause current playback.
        
        Args:
            announce: Whether to announce via TTS
            
        Returns:
            Dictionary with 'success', 'track_name'
        """
        success = self.player.pause()
        
        if success:
            current = self.player.get_current_file()
            track_name = current.name if current else None
            
            if announce:
                self.tts.speak("Music paused")
            
            return {
                'success': True,
                'track_name': track_name
            }
        else:
            if announce:
                self.tts.speak("Nothing is playing")
            
            return {
                'success': False,
                'track_name': None
            }
    
    def resume(self, announce: bool = True) -> dict:
        """
        Resume paused playback.
        
        Args:
            announce: Whether to announce via TTS
            
        Returns:
            Dictionary with 'success', 'track_name'
        """
        success = self.player.resume()
        
        if success:
            current = self.player.get_current_file()
            track_name = current.name if current else None
            
            if announce:
                self.tts.speak("Music resumed")
            
            return {
                'success': True,
                'track_name': track_name
            }
        else:
            if announce:
                self.tts.speak("Nothing to resume")
            
            return {
                'success': False,
                'track_name': None
            }
    
    def stop(self, announce: bool = True) -> dict:
        """
        Stop current playback.
        
        Args:
            announce: Whether to announce via TTS
            
        Returns:
            Dictionary with 'success', 'track_name'
        """
        # Get track name before stopping
        current = self.player.get_current_file()
        track_name = current.name if current else None
        
        success = self.player.stop()
        
        if success:
            if announce:
                self.tts.speak("Music stopped")
            
            return {
                'success': True,
                'track_name': track_name
            }
        else:
            if announce:
                self.tts.speak("Nothing is playing")
            
            return {
                'success': False,
                'track_name': None
            }
    
    def set_volume(self, level: float, announce: bool = True) -> bool:
        """
        Set volume level.
        
        Args:
            level: Volume (0.0 to 1.0)
            announce: Whether to announce via TTS
            
        Returns:
            True if volume set successfully
        """
        success = self.player.set_volume(level)
        
        if success and announce:
            self.tts.speak(f"Volume set to {int(level * 100)} percent")
        
        return success
    
    def get_current_status(self) -> dict:
        """
        Get current playback status.
        
        Returns:
            Dictionary with status information
        """
        current_file = self.player.get_current_file()
        
        return {
            'is_playing': self.player.is_active(),
            'is_paused': self.player.is_paused,
            'current_file': current_file.name if current_file else None,
            'volume': self.player.get_volume(),
            'position': self.player.get_position(),
            'playlist_count': self.player.get_playlist_count()
        }
    
    def search_library(self, query: str, max_results: int = 5) -> list:
        """
        Search library for tracks.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of matching tracks
        """
        return self.library.search(query, max_results)
    
    def get_categories(self) -> list:
        """
        Get all music categories.
        
        Returns:
            List of category names
        """
        return self.library.get_categories()
    
    def refresh_library(self) -> int:
        """
        Refresh media library.
        
        Returns:
            Number of tracks found
        """
        count = self.library.refresh()
        self.logger.info(f"🔄 Library refreshed: {count} tracks")
        return count
    
    def shutdown(self):
        """Cleanup and shutdown music manager."""
        self.player.shutdown()
        self.logger.info("👋 Music manager shutdown")
