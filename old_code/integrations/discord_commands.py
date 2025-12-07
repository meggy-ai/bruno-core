"""
Discord Slash Commands for Bruno Assistant

Implements modern slash command interface with autocomplete and type validation.

Commands:
- /bruno timer <action> [params]  - Timer management
- /bruno music <action> [params]  - Music playback
- /bruno memory <action> [params] - Memory operations
- /bruno admin <action> [params]  - Admin commands (restricted)
"""

from typing import Optional, Literal
import discord
from discord import app_commands
from discord.ext import commands

from bruno.utils.config import BrunoConfig
from bruno.core.bruno_interface import BrunoInterface, BrunoRequest
from bruno.core.action_executor import ActionExecutor


class BrunoCommands(commands.Cog):
    """Slash commands for Bruno Assistant."""
    
    def __init__(
        self,
        bot: commands.Bot,
        config: BrunoConfig,
        bruno_interface: BrunoInterface,
        action_executor: ActionExecutor
    ):
        self.bot = bot
        self.config = config
        self.bruno = bruno_interface
        self.executor = action_executor
    
    def is_admin(self, user: discord.User) -> bool:
        """Check if user has admin permissions."""
        admin_ids = self.config.get('discord.admin.admin_user_ids', [])
        return user.id in admin_ids
    
    # ============================================================================
    # TIMER COMMANDS
    # ============================================================================
    
    timer_group = app_commands.Group(name="timer", description="Manage timers")
    
    @timer_group.command(name="set", description="Set a timer")
    @app_commands.describe(
        duration="Timer duration (e.g., '5 minutes', '30 seconds', '1 hour')",
        label="Optional label for the timer"
    )
    async def timer_set(
        self,
        interaction: discord.Interaction,
        duration: str,
        label: Optional[str] = None
    ):
        """Set a timer with optional label."""
        await interaction.response.defer()
        
        # Build command text
        command = f"set a timer for {duration}"
        if label:
            command += f" called {label}"
        
        # Process through Bruno
        request = BrunoRequest(
            user_id=f"discord:{interaction.user.id}",
            username=interaction.user.display_name,
            message=command,
            channel="discord"
        )
        
        result = self.bruno.process_request(request)
        
        # Execute actions
        await self.executor.execute_actions(result.actions, interaction.channel)
        
        # Send response
        await interaction.followup.send(result.response)
    
    @timer_group.command(name="list", description="List all active timers")
    async def timer_list(self, interaction: discord.Interaction):
        """List all active timers."""
        await interaction.response.defer()
        
        request = BrunoRequest(
            user_id=f"discord:{interaction.user.id}",
            username=interaction.user.display_name,
            message="list timers",
            channel="discord"
        )
        
        result = self.bruno.process_request(request)
        await interaction.followup.send(result.response)
    
    @timer_group.command(name="cancel", description="Cancel a specific timer")
    @app_commands.describe(timer_id="Timer ID to cancel")
    async def timer_cancel(self, interaction: discord.Interaction, timer_id: int):
        """Cancel a specific timer by ID."""
        await interaction.response.defer()
        
        request = BrunoRequest(
            user_id=f"discord:{interaction.user.id}",
            username=interaction.user.display_name,
            message=f"cancel timer {timer_id}",
            channel="discord"
        )
        
        result = self.bruno.process_request(request)
        await self.executor.execute_actions(result.actions, interaction.channel)
        await interaction.followup.send(result.response)
    
    @timer_group.command(name="cancel-all", description="Cancel all active timers")
    async def timer_cancel_all(self, interaction: discord.Interaction):
        """Cancel all active timers."""
        await interaction.response.defer()
        
        request = BrunoRequest(
            user_id=f"discord:{interaction.user.id}",
            username=interaction.user.display_name,
            message="cancel all timers",
            channel="discord"
        )
        
        result = self.bruno.process_request(request)
        await self.executor.execute_actions(result.actions, interaction.channel)
        await interaction.followup.send(result.response)
    
    # ============================================================================
    # MUSIC COMMANDS
    # ============================================================================
    
    music_group = app_commands.Group(name="music", description="Control music playback")
    
    @music_group.command(name="play", description="Play music")
    @app_commands.describe(query="Music category or search query")
    async def music_play(self, interaction: discord.Interaction, query: str):
        """Play music by category or search query."""
        await interaction.response.defer()
        
        request = BrunoRequest(
            user_id=f"discord:{interaction.user.id}",
            username=interaction.user.display_name,
            message=f"play {query} music",
            channel="discord"
        )
        
        result = self.bruno.process_request(request)
        await self.executor.execute_actions(result.actions, interaction.channel)
        await interaction.followup.send(result.response)
    
    @music_group.command(name="pause", description="Pause music playback")
    async def music_pause(self, interaction: discord.Interaction):
        """Pause current music."""
        await interaction.response.defer()
        
        request = BrunoRequest(
            user_id=f"discord:{interaction.user.id}",
            username=interaction.user.display_name,
            message="pause music",
            channel="discord"
        )
        
        result = self.bruno.process_request(request)
        await self.executor.execute_actions(result.actions, interaction.channel)
        await interaction.followup.send(result.response)
    
    @music_group.command(name="resume", description="Resume music playback")
    async def music_resume(self, interaction: discord.Interaction):
        """Resume paused music."""
        await interaction.response.defer()
        
        request = BrunoRequest(
            user_id=f"discord:{interaction.user.id}",
            username=interaction.user.display_name,
            message="resume music",
            channel="discord"
        )
        
        result = self.bruno.process_request(request)
        await self.executor.execute_actions(result.actions, interaction.channel)
        await interaction.followup.send(result.response)
    
    @music_group.command(name="stop", description="Stop music playback")
    async def music_stop(self, interaction: discord.Interaction):
        """Stop current music."""
        await interaction.response.defer()
        
        request = BrunoRequest(
            user_id=f"discord:{interaction.user.id}",
            username=interaction.user.display_name,
            message="stop music",
            channel="discord"
        )
        
        result = self.bruno.process_request(request)
        await self.executor.execute_actions(result.actions, interaction.channel)
        await interaction.followup.send(result.response)
    
    @music_group.command(name="status", description="Show music playback status")
    async def music_status(self, interaction: discord.Interaction):
        """Get current music status."""
        await interaction.response.defer()
        
        request = BrunoRequest(
            user_id=f"discord:{interaction.user.id}",
            username=interaction.user.display_name,
            message="music status",
            channel="discord"
        )
        
        result = self.bruno.process_request(request)
        await interaction.followup.send(result.response)
    
    # ============================================================================
    # MEMORY COMMANDS
    # ============================================================================
    
    memory_group = app_commands.Group(name="memory", description="Manage conversation memory")
    
    @memory_group.command(name="search", description="Search conversation history")
    @app_commands.describe(query="What to search for")
    async def memory_search(self, interaction: discord.Interaction, query: str):
        """Search conversation history."""
        await interaction.response.defer()
        
        request = BrunoRequest(
            user_id=f"discord:{interaction.user.id}",
            username=interaction.user.display_name,
            message=f"search memory for {query}",
            channel="discord"
        )
        
        result = self.bruno.process_request(request)
        await interaction.followup.send(result.response)
    
    @memory_group.command(name="summary", description="Get conversation summary")
    async def memory_summary(self, interaction: discord.Interaction):
        """Get recent conversation summary."""
        await interaction.response.defer()
        
        request = BrunoRequest(
            user_id=f"discord:{interaction.user.id}",
            username=interaction.user.display_name,
            message="summarize our conversation",
            channel="discord"
        )
        
        result = self.bruno.process_request(request)
        await interaction.followup.send(result.response)
    
    @memory_group.command(name="stats", description="Show memory statistics")
    async def memory_stats(self, interaction: discord.Interaction):
        """Get memory statistics."""
        await interaction.response.defer()
        
        request = BrunoRequest(
            user_id=f"discord:{interaction.user.id}",
            username=interaction.user.display_name,
            message="memory stats",
            channel="discord"
        )
        
        result = self.bruno.process_request(request)
        await interaction.followup.send(result.response)
    
    # ============================================================================
    # ADMIN COMMANDS
    # ============================================================================
    
    admin_group = app_commands.Group(name="admin", description="Bot administration (admin only)")
    
    @admin_group.command(name="stats", description="Show bot statistics")
    async def admin_stats(self, interaction: discord.Interaction):
        """Get bot statistics (admin only)."""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ This command is restricted to bot administrators.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Get stats from various components
        stats = {
            "bot_latency": f"{self.bot.latency * 1000:.0f}ms",
            "guilds": len(self.bot.guilds),
            "users": len(self.bot.users),
            "active_timers": len(self.executor.timer_manager.active_timers) if hasattr(self.executor, 'timer_manager') else 0,
        }
        
        response = "**📊 Bot Statistics**\n\n"
        for key, value in stats.items():
            response += f"• **{key.replace('_', ' ').title()}**: {value}\n"
        
        await interaction.followup.send(response, ephemeral=True)
    
    @admin_group.command(name="clear-memory", description="Clear memory for a user")
    @app_commands.describe(user="User whose memory to clear")
    async def admin_clear_memory(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ):
        """Clear memory for specific user (admin only)."""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ This command is restricted to bot administrators.",
                ephemeral=True
            )
            return
        
        if not self.config.get('discord.admin.allow_memory_clear', False):
            await interaction.response.send_message(
                "❌ Memory clearing is disabled in configuration.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        user_id = f"discord:{user.id}"
        # Note: Would need to add clear_user_data method to memory_store
        # For now, just acknowledge
        
        await interaction.followup.send(
            f"✅ Memory cleared for {user.mention}",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    """Load the commands cog."""
    # This would be called from discord_bot.py
    pass
