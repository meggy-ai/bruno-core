"""
Discord Embed Builders for Bruno Assistant

Creates rich, formatted Discord embeds for various command responses.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import discord


def create_progress_bar(percentage: float, length: int = 10) -> str:
    """
    Create a visual progress bar using Unicode blocks.
    
    Args:
        percentage: Progress percentage (0-100)
        length: Number of blocks in the bar
    
    Returns:
        Progress bar string like: ⬛⬛⬛⬜⬜⬜⬜⬜⬜⬜ 30%
    """
    filled = int(length * percentage / 100)
    filled = max(0, min(length, filled))  # Clamp to valid range
    bar = "⬛" * filled + "⬜" * (length - filled)
    return f"{bar} {percentage:.0f}%"


def format_duration(seconds: int) -> str:
    """
    Format seconds into human-readable duration.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted string like "5m 30s" or "1h 15m"
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


class BrunoEmbeds:
    """Factory for creating Discord embeds."""
    
    def __init__(self, bot_user: Optional[discord.User] = None):
        """
        Initialize embed builder.
        
        Args:
            bot_user: Discord bot user (for avatar in footer)
        """
        self.bot_user = bot_user
    
    def _base_embed(
        self,
        title: str,
        description: Optional[str] = None,
        color: discord.Color = discord.Color.blue()
    ) -> discord.Embed:
        """
        Create base embed with common settings.
        
        Args:
            title: Embed title
            description: Optional description
            color: Embed color
        
        Returns:
            Base Discord embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        
        if self.bot_user:
            embed.set_footer(
                text="Bruno Assistant",
                icon_url=self.bot_user.avatar.url if self.bot_user.avatar else None
            )
        
        return embed
    
    # ============================================================================
    # TIMER EMBEDS
    # ============================================================================
    
    def timer_set(self, duration: str, label: Optional[str] = None) -> discord.Embed:
        """Create embed for timer set confirmation."""
        embed = self._base_embed(
            title="⏱️ Timer Set",
            description=f"Timer for {duration}" + (f" ({label})" if label else ""),
            color=discord.Color.green()
        )
        return embed
    
    def timer_list(self, timers: List[Dict[str, Any]]) -> discord.Embed:
        """
        Create embed showing all active timers.
        
        Args:
            timers: List of timer dicts with keys:
                - id: Timer ID
                - label: Optional label
                - total_seconds: Total duration
                - remaining_seconds: Time remaining
        
        Returns:
            Discord embed with timer list
        """
        if not timers:
            return self._base_embed(
                title="⏱️ Active Timers",
                description="No active timers",
                color=discord.Color.blue()
            )
        
        embed = self._base_embed(
            title="⏱️ Active Timers",
            description=f"{len(timers)} timer{'s' if len(timers) != 1 else ''} running",
            color=discord.Color.blue()
        )
        
        for timer in timers:
            timer_id = timer.get('id', '?')
            label = timer.get('label', f"Timer #{timer_id}")
            total = timer.get('total_seconds', 0)
            remaining = timer.get('remaining_seconds', 0)
            
            # Calculate percentage
            percentage = ((total - remaining) / total * 100) if total > 0 else 0
            progress_bar = create_progress_bar(percentage)
            
            # Format time
            remaining_str = format_duration(remaining)
            
            embed.add_field(
                name=f"{label}",
                value=f"{progress_bar}\n⏰ {remaining_str} remaining",
                inline=False
            )
        
        return embed
    
    def timer_completed(self, label: Optional[str] = None) -> discord.Embed:
        """Create embed for timer completion."""
        embed = self._base_embed(
            title="⏱️ Timer Complete!",
            description=label or "Your timer has finished",
            color=discord.Color.gold()
        )
        return embed
    
    def timer_cancelled(self, label: Optional[str] = None) -> discord.Embed:
        """Create embed for timer cancellation."""
        embed = self._base_embed(
            title="⏱️ Timer Cancelled",
            description=label or "Timer has been cancelled",
            color=discord.Color.orange()
        )
        return embed
    
    # ============================================================================
    # MUSIC EMBEDS
    # ============================================================================
    
    def music_playing(
        self,
        track_name: str,
        category: Optional[str] = None,
        duration: Optional[int] = None,
        elapsed: Optional[int] = None
    ) -> discord.Embed:
        """
        Create embed for currently playing music.
        
        Args:
            track_name: Name of the track
            category: Music category
            duration: Duration in seconds
            elapsed: Elapsed time in seconds
        
        Returns:
            Discord embed with music info
        """
        description = f"**{track_name}**"
        
        # Add progress bar if duration and elapsed provided
        if duration is not None and elapsed is not None:
            progress = elapsed / duration if duration > 0 else 0
            progress_bar = create_progress_bar(progress)
            duration_str = format_duration(duration)
            elapsed_str = format_duration(elapsed)
            description += f"\\n\\n{progress_bar}\\n{elapsed_str} / {duration_str}"
        
        embed = self._base_embed(
            title="🎵 Now Playing",
            description=description,
            color=discord.Color.green()
        )
        
        if category:
            embed.add_field(name="Category", value=category, inline=True)
        
        if duration and not elapsed:
            # If only duration provided (no elapsed time), show as field
            embed.add_field(
                name="Duration",
                value=format_duration(duration),
                inline=True
            )
        
        embed.add_field(
            name="Controls",
            value="⏸️ Pause | ▶️ Resume | ⏹️ Stop",
            inline=False
        )
        
        return embed
    
    def music_paused(self) -> discord.Embed:
        """Create embed for music pause."""
        embed = self._base_embed(
            title="⏸️ Music Paused",
            description="Playback paused",
            color=discord.Color.orange()
        )
        return embed
    
    def music_resumed(self) -> discord.Embed:
        """Create embed for music resume."""
        embed = self._base_embed(
            title="▶️ Music Resumed",
            description="Playback resumed",
            color=discord.Color.green()
        )
        return embed
    
    def music_stopped(self) -> discord.Embed:
        """Create embed for music stop."""
        embed = self._base_embed(
            title="⏹️ Music Stopped",
            description="Playback stopped",
            color=discord.Color.red()
        )
        return embed
    
    def music_status(
        self,
        is_playing: bool,
        track_name: Optional[str] = None,
        volume: Optional[int] = None,
        duration: Optional[int] = None,
        elapsed: Optional[int] = None
    ) -> discord.Embed:
        """
        Create embed for music status.
        
        Args:
            is_playing: Whether music is currently playing
            track_name: Name of current track
            volume: Current volume (0-100)
            duration: Total track duration in seconds
            elapsed: Elapsed time in seconds
        
        Returns:
            Discord embed with status info
        """
        if not is_playing:
            return self._base_embed(
                title="🎵 Music Status",
                description="No music playing",
                color=discord.Color.greyple()
            )
        
        description = f"**{track_name or 'Unknown'}**"
        
        # Add duration and progress if available
        if duration is not None and elapsed is not None:
            progress = elapsed / duration if duration > 0 else 0
            progress_bar = create_progress_bar(progress)
            duration_str = format_duration(duration)
            elapsed_str = format_duration(elapsed)
            description += f"\n\n{progress_bar}\n{elapsed_str} / {duration_str}"
        
        embed = self._base_embed(
            title="🎵 Music Status",
            description=description,
            color=discord.Color.green()
        )
        
        if volume is not None:
            embed.add_field(name="Volume", value=f"{volume}%", inline=True)
        
        return embed
    
    # ============================================================================
    # MEMORY EMBEDS
    # ============================================================================
    
    def memory_stats(
        self,
        total_conversations: int,
        total_messages: int,
        stm_count: int,
        ltm_count: int
    ) -> discord.Embed:
        """
        Create embed for memory statistics.
        
        Args:
            total_conversations: Number of conversations
            total_messages: Total message count
            stm_count: Short-term memory count
            ltm_count: Long-term memory count
        
        Returns:
            Discord embed with memory stats
        """
        embed = self._base_embed(
            title="🧠 Memory Statistics",
            description="Your conversation memory",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="Conversations",
            value=str(total_conversations),
            inline=True
        )
        
        embed.add_field(
            name="Total Messages",
            value=str(total_messages),
            inline=True
        )
        
        embed.add_field(
            name="Short-Term Memories",
            value=str(stm_count),
            inline=True
        )
        
        embed.add_field(
            name="Long-Term Memories",
            value=str(ltm_count),
            inline=True
        )
        
        return embed
    
    def memory_search_results(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> discord.Embed:
        """
        Create embed for memory search results.
        
        Args:
            query: Search query
            results: List of matching memory dicts
        
        Returns:
            Discord embed with search results
        """
        embed = self._base_embed(
            title="🔍 Memory Search",
            description=f"Results for: **{query}**",
            color=discord.Color.blue()
        )
        
        if not results:
            embed.add_field(
                name="No Results",
                value="No matching memories found",
                inline=False
            )
            return embed
        
        for i, result in enumerate(results[:5], 1):  # Limit to 5 results
            content = result.get('content', 'No content')
            timestamp = result.get('timestamp', 'Unknown time')
            
            embed.add_field(
                name=f"Result {i}",
                value=f"{content}\n*{timestamp}*",
                inline=False
            )
        
        if len(results) > 5:
            embed.set_footer(text=f"Showing 5 of {len(results)} results")
        
        return embed
    
    # ============================================================================
    # ERROR EMBEDS
    # ============================================================================
    
    def error(
        self,
        title: str = "❌ Error",
        description: str = "An error occurred",
        details: Optional[str] = None
    ) -> discord.Embed:
        """
        Create embed for error messages.
        
        Args:
            title: Error title
            description: Error description
            details: Optional detailed error info
        
        Returns:
            Discord embed with error info
        """
        embed = self._base_embed(
            title=title,
            description=description,
            color=discord.Color.red()
        )
        
        if details:
            embed.add_field(name="Details", value=details, inline=False)
        
        return embed
    
    def rate_limit(self, remaining_seconds: float) -> discord.Embed:
        """Create embed for rate limit warning."""
        embed = self._base_embed(
            title="⏳ Please Wait",
            description=f"You're sending commands too quickly.\nPlease wait {remaining_seconds:.1f} seconds.",
            color=discord.Color.orange()
        )
        return embed
    
    # ============================================================================
    # ADMIN EMBEDS
    # ============================================================================
    
    def admin_stats(self, stats: Dict[str, Any]) -> discord.Embed:
        """
        Create embed for bot statistics.
        
        Args:
            stats: Dictionary of statistics
        
        Returns:
            Discord embed with admin stats
        """
        embed = self._base_embed(
            title="📊 Bot Statistics",
            description="System health and usage",
            color=discord.Color.blue()
        )
        
        for key, value in stats.items():
            embed.add_field(
                name=key.replace('_', ' ').title(),
                value=str(value),
                inline=True
            )
        
        return embed
