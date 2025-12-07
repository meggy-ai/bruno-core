"""
MediaLibrary - Manages the media library (scans, indexes, searches audio files).
"""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Track:
    """Represents an audio track in the library."""
    id: str                    # Unique identifier (hash of path)
    file_path: Path            # Absolute path to file
    filename: str              # Original filename
    title: str                 # Display title (from filename or ID3)
    category: str              # Inferred category (e.g., "meditation", "rock")
    format: str                # File format (mp3, wav, flac)
    duration: Optional[float]  # Duration in seconds (if available)
    size: int                  # File size in bytes


class MediaLibrary:
    """
    Manages the media library - scans, indexes, and searches audio files.
    """
    
    SUPPORTED_FORMATS = ['.mp3', '.wav', '.flac', '.ogg', '.m4a']
    
    def __init__(self, media_dir: Path):
        """
        Initialize media library.
        
        Args:
            media_dir: Root directory containing media files
        """
        self.media_dir = media_dir
        self.tracks: List[Track] = []
        self.track_index: Dict[str, Track] = {}  # ID -> Track
        self.category_index: Dict[str, List[Track]] = {}  # Category -> Tracks
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Scan library on initialization
        self.scan_library()
    
    def scan_library(self) -> int:
        """
        Scan media directory for audio files and build index.
        
        Returns:
            Number of tracks found
        """
        self.tracks.clear()
        self.track_index.clear()
        self.category_index.clear()
        
        songs_dir = self.media_dir / "songs"
        if not songs_dir.exists():
            self.logger.warning(f"⚠️  Songs directory not found: {songs_dir}")
            songs_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"✅ Created songs directory: {songs_dir}")
            return 0
        
        # Scan for audio files
        for file_path in songs_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                track = self._create_track(file_path)
                self.tracks.append(track)
                self.track_index[track.id] = track
                
                # Index by category
                if track.category not in self.category_index:
                    self.category_index[track.category] = []
                self.category_index[track.category].append(track)
        
        self.logger.info(f"📚 Scanned library: {len(self.tracks)} tracks, "
                        f"{len(self.category_index)} categories")
        return len(self.tracks)
    
    def _create_track(self, file_path: Path) -> Track:
        """
        Create Track object from file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Track object
        """
        # Generate unique ID from file path
        track_id = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
        
        # Extract category from parent directory or filename
        filename_lower = file_path.stem.lower()
        parent_dir = file_path.parent.name
        category = self._extract_category(filename_lower, parent_dir)
        
        # Create display title
        title = file_path.stem.replace('_', ' ').title()
        
        return Track(
            id=track_id,
            file_path=file_path,
            filename=file_path.name,
            title=title,
            category=category,
            format=file_path.suffix[1:].lower(),
            duration=None,  # Could extract from file metadata in future
            size=file_path.stat().st_size
        )
    
    def _extract_category(self, filename: str, parent_dir: str = '') -> str:
        """
        Extract category from parent directory or filename.
        
        Args:
            filename: Lowercase filename (without extension)
            parent_dir: Parent directory name
            
        Returns:
            Category name
        """
        # Use parent directory name as category if available
        if parent_dir and parent_dir != 'songs':
            return parent_dir.lower().replace('_', ' ').replace('-', ' ')
        
        # Common categories to detect from filename
        categories = [
            'meditation', 'relaxation', 'focus', 'sleep', 'calm',
            'rock', 'jazz', 'classical', 'pop', 'ambient', 'electronic',
            'hip hop', 'country', 'blues', 'metal', 'folk', 'reggae',
            'recommendations', 'favorites', 'playlist'
        ]
        
        for cat in categories:
            if cat in filename:
                return cat
        
        return 'general'  # Default category
    
    def search(self, query: str, max_results: int = 10) -> List[Track]:
        """
        Search for tracks matching query.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of matching tracks, sorted by relevance
        """
        query_lower = query.lower().strip()
        
        if not query_lower:
            # Return random tracks if no query
            return self.tracks[:max_results] if self.tracks else []
        
        # First, try exact category match
        for category, tracks in self.category_index.items():
            if query_lower in category or category in query_lower:
                self.logger.info(f"🎯 Found category match: {category}")
                return tracks[:max_results]
        
        matches = []
        
        for track in self.tracks:
            score = 0
            
            # Exact category match (highest priority)
            if query_lower == track.category:
                score += 100
            # Category contains query
            elif query_lower in track.category:
                score += 50
            
            # Title contains query
            if query_lower in track.title.lower():
                score += 30
            
            # Filename contains query
            if query_lower in track.filename.lower():
                score += 20
            
            # Title starts with query (bonus)
            if track.title.lower().startswith(query_lower):
                score += 10
            
            if score > 0:
                matches.append((score, track))
        
        # Sort by score (descending)
        matches.sort(reverse=True, key=lambda x: x[0])
        
        return [track for score, track in matches[:max_results]]
    
    def get_track_by_id(self, track_id: str) -> Optional[Track]:
        """
        Get track by ID.
        
        Args:
            track_id: Track identifier
            
        Returns:
            Track object or None if not found
        """
        return self.track_index.get(track_id)
    
    def get_categories(self) -> List[str]:
        """
        Get list of all categories.
        
        Returns:
            Sorted list of category names
        """
        return sorted(self.category_index.keys())
    
    def get_tracks_by_category(self, category: str) -> List[Track]:
        """
        Get all tracks in a category.
        
        Args:
            category: Category name
            
        Returns:
            List of tracks in category
        """
        return self.category_index.get(category.lower(), [])
    
    def get_all_tracks(self) -> List[Track]:
        """
        Get all tracks in library.
        
        Returns:
            List of all tracks
        """
        return self.tracks.copy()
    
    def refresh(self) -> int:
        """
        Refresh library (rescan directory).
        
        Returns:
            Number of tracks found
        """
        self.logger.info("🔄 Refreshing library...")
        return self.scan_library()
