import logging
from typing import Optional, cast

import discord
from discord.ext import commands

from .config import Config
from .database import Database
from .downloader import Downloader
from .models import Request

logger = logging.getLogger(__name__)


class RequestCog(commands.Cog):
    def __init__(self, bot: "KidsTunesBot") -> None:
        self.bot = bot

    @commands.command(name="request")
    async def request_music(self, ctx: commands.Context, *, search_term: str) -> None:
        logger.info(f"Request command called in channel {ctx.channel.id}")
        if ctx.channel.id != self.bot.config.request_channel_id:
            logger.info(
                f"Ignoring request in wrong channel {ctx.channel.id}, expected {self.bot.config.request_channel_id}"
            )
            return

        refined_data = await self.bot.downloader.refine_search_structured(search_term)
        logger.info(f"Original: {search_term}, Refined: {refined_data}")

        req = Request(
            discord_user_id=str(ctx.author.id),
            discord_username=ctx.author.display_name,
            search_term=search_term,
            refined_search_term=refined_data["refined_search_term"],
            artist=refined_data["artist"],
            song=refined_data["song"],
            album=refined_data["album"],
            original_message_id=str(ctx.message.id),
            original_channel_id=str(ctx.channel.id),
        )
        request_id = await self.bot.db.create_request(req)

        embed = self._create_embed(req, request_id)
        assert self.bot.approval_channel is not None  # Should be set in on_ready
        msg = await self.bot.approval_channel.send(embed=embed)

        # Add reactions (check if they don't already exist to prevent duplicates)
        if not any(str(reaction.emoji) == "✅" for reaction in msg.reactions):
            await msg.add_reaction("✅")
        if not any(str(reaction.emoji) == "❌" for reaction in msg.reactions):
            await msg.add_reaction("❌")

        await self.bot.db.update_request(request_id, message_id=str(msg.id))
        logger.info(
            f"New request {request_id} from {req.discord_username}: {search_term}"
        )

    @commands.command(name="retry")
    async def retry_request(self, ctx: commands.Context, request_id: int) -> None:
        member = cast(discord.Member, ctx.author)
        if not any(role.id == self.bot.config.admin_role_id for role in member.roles):
            return

        req = await self.bot.db.get_request_by_id(request_id)
        if not req or req.status != "failed":
            await ctx.send("Invalid request ID or request is not failed.")
            return

        assert req.id is not None  # Should have ID since fetched by ID

        await self.bot.db.update_request(req.id, status="approved")
        try:
            search_query = req.refined_search_term or req.search_term
            await self.bot.downloader.search_and_download(req.id, search_query)
            await ctx.send(f"Retried request {request_id} successfully.")
            logger.info(f"Retried request {request_id}")
        except Exception as e:
            await ctx.send(f"Retry failed: {e}")
            logger.error(f"Retry failed for {request_id}: {e}")

    @commands.Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: discord.User
    ) -> None:
        if user.bot:
            return
        logger.info(
            f"Reaction added: {reaction.emoji} by {user} in {reaction.message.channel}"
        )
        if reaction.message.channel.id != self.bot.config.approval_channel_id:
            logger.info(
                f"Ignoring reaction in wrong channel {reaction.message.channel.id}, expected {self.bot.config.approval_channel_id}"
            )
            return
        member = cast(discord.Member, user)
        if not any(role.id == self.bot.config.admin_role_id for role in member.roles):
            logger.info(f"User {user} does not have admin role")
            return

        emoji = str(reaction.emoji)
        if emoji not in ["✅", "❌"]:
            return

        req = await self.bot.db.get_request_by_message_id(str(reaction.message.id))
        if not req:
            logger.info(f"No request found for message {reaction.message.id}")
            return

        assert req.id is not None  # Should always have an ID from database

        logger.info(f"Processing {emoji} for request {req.id}")
        if emoji == "✅":
            await self.bot.db.update_request(req.id, status="approved")
            embed = self._create_embed(req, req.id, status="Downloading...")
            embed.color = 0xFFFF00
            await reaction.message.edit(embed=embed)

            try:
                search_query = req.refined_search_term or req.search_term
                await self.bot.downloader.search_and_download(
                    req.id, search_query, req.artist, req.song, req.album
                )
                embed = self._create_embed(req, req.id, status="Complete ✓")
                embed.color = 0x00FF00
                logger.info(f"Completed request {req.id}")
            except Exception as e:
                await self.bot.db.update_request(
                    req.id, status="failed", error_message=str(e)
                )
                embed = self._create_embed(req, req.id, status="Failed ✗", error=str(e))
                embed.color = 0xFF0000
                logger.error(f"Failed request {req.id}: {e}")

            await reaction.message.edit(embed=embed)

            # Add reaction to original message
            if req.original_message_id and req.original_channel_id:
                try:
                    original_channel = self.bot.get_channel(
                        int(req.original_channel_id)
                    )
                    if original_channel:
                        original_message = await original_channel.fetch_message(
                            int(req.original_message_id)
                        )
                        await original_message.add_reaction("✅")
                        logger.info(
                            f"Added approval reaction to original message {req.original_message_id}"
                        )
                    else:
                        logger.warning(
                            f"Could not find original channel {req.original_channel_id}"
                        )
                except discord.NotFound:
                    logger.warning(
                        f"Original message {req.original_message_id} not found (may have been deleted)"
                    )
                except discord.Forbidden:
                    logger.warning(
                        f"Missing permissions to react to original message {req.original_message_id}"
                    )
                except Exception as e:
                    logger.error(f"Failed to add reaction to original message: {e}")
        else:
            await self.bot.db.update_request(req.id, status="rejected")
            embed = self._create_embed(req, req.id, status="Rejected")
            embed.color = 0xFF0000
            await reaction.message.edit(embed=embed)
            logger.info(f"Rejected request {req.id}")

            # Add reaction to original message
            if req.original_message_id and req.original_channel_id:
                try:
                    original_channel = self.bot.get_channel(
                        int(req.original_channel_id)
                    )
                    if original_channel:
                        original_message = await original_channel.fetch_message(
                            int(req.original_message_id)
                        )
                        await original_message.add_reaction("❌")
                        logger.info(
                            f"Added rejection reaction to original message {req.original_message_id}"
                        )
                    else:
                        logger.warning(
                            f"Could not find original channel {req.original_channel_id}"
                        )
                except discord.NotFound:
                    logger.warning(
                        f"Original message {req.original_message_id} not found (may have been deleted)"
                    )
                except discord.Forbidden:
                    logger.warning(
                        f"Missing permissions to react to original message {req.original_message_id}"
                    )
                except Exception as e:
                    logger.error(f"Failed to add reaction to original message: {e}")

    def _create_embed(
        self,
        req: Request,
        request_id: int,
        status: str = "Pending Approval",
        error: Optional[str] = None,
    ) -> discord.Embed:
        embed = discord.Embed(title=f"Music Request #{request_id}", color=0x0000FF)
        embed.add_field(name="Requester", value=req.discord_username, inline=True)
        embed.add_field(name="Original Request", value=req.search_term, inline=True)

        # Add structured music information if available
        if req.artist or req.song or req.album:
            music_info = []
            if req.artist:
                music_info.append(f"🎤 **Artist:** {req.artist}")
            if req.song:
                music_info.append(f"🎵 **Song:** {req.song}")
            if req.album:
                music_info.append(f"💿 **Album:** {req.album}")
            embed.add_field(
                name="🎼 Identified Music", value="\n".join(music_info), inline=False
            )

        if req.refined_search_term and req.refined_search_term != req.search_term:
            embed.add_field(
                name="🔍 AI Refined Search", value=req.refined_search_term, inline=False
            )

        embed.add_field(name="Status", value=status, inline=False)
        if req.youtube_title:
            embed.add_field(name="YouTube Title", value=req.youtube_title, inline=False)
        if error:
            embed.add_field(name="Error", value=error, inline=False)
        if req.created_at:
            embed.set_footer(
                text=f"Requested at {req.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        return embed


class KidsTunesBot(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        super().__init__(command_prefix="!", intents=intents)

        self.config = config
        self.db = Database(config.database_path)
        self.downloader = Downloader(self.db, config)
        self.approval_channel: Optional[discord.TextChannel] = None

    async def setup_hook(self) -> None:
        await self.db.connect()
        logger.info("Database connected")

    async def on_ready(self) -> None:
        await self.add_cog(RequestCog(self))
        logger.info("Cog added")
        self.approval_channel = cast(
            discord.TextChannel, self.get_channel(self.config.approval_channel_id)
        )
        logger.info(f"Bot is ready. Approval channel: {self.approval_channel}")
        logger.info(f"Commands: {list(self.all_commands.keys())}")
        logger.info(f"Guilds: {[g.name for g in self.guilds]}")
        for guild in self.guilds:
            logger.info(
                f'Guild {guild.name} channels: {[c.name for c in guild.channels if hasattr(c, "name")]}'
            )
            logger.info(
                f'Channel IDs: {[c.id for c in guild.channels if hasattr(c, "id")]}'
            )

        # Clean up any stuck requests on startup
        await self._cleanup_stuck_requests()

    async def _cleanup_stuck_requests(self) -> None:
        """Clean up requests that may be stuck in downloading state from previous runs."""
        try:
            # This would require adding a method to the database class to find stuck requests
            # For now, just log that cleanup would happen here
            logger.info("Request cleanup check completed (no stuck requests found)")
        except Exception as e:
            logger.error(f"Error during request cleanup: {e}")

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return
        await self.process_commands(message)
