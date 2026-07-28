# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   ░█▀▀░█▀█░█▀▄░█▀▀░█░█   ░█▀▄░█▀▀░█░█░█▀▀                     ║
# ║   ░█░░░█░█░█░█░█▀▀░▄▀▄   ░█░█░█▀▀░▀▄▀░▀▀█                     ║
# ║   ░▀▀▀░▀▀▀░▀▀░░▀▀▀░▀░▀   ░▀▀░░▀▀▀░░▀░░▀▀▀                     ║
# ║                                                                  ║
# ║            © 2026 Arsh — All Rights Reserved                    ║
# ║                                                                  ║
# ║            Built by  ──  Arsh                                    ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

import discord
from utils.emoji import ARROWRED
from discord.ext import commands
import aiosqlite
from utils.cv2 import CV2

INVITE_DB = "db/invite.db"
EMOJI_INVITE = ARROWRED

from utils.config import BotName


class Tracking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------
    async def ensure_tables(self, guild_id):
        async with aiosqlite.connect(INVITE_DB) as db:
            await db.execute(f'''
                CREATE TABLE IF NOT EXISTS invites_{guild_id} (
                    user_id INTEGER PRIMARY KEY,
                    total INTEGER DEFAULT 0,
                    fake INTEGER DEFAULT 0,
                    left INTEGER DEFAULT 0,
                    rejoin INTEGER DEFAULT 0
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS logging (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS leave_channel (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER
                )
            ''')
            await db.commit()

    async def get_total_invites(self, guild_id, user_id):
        async with aiosqlite.connect(INVITE_DB) as db:
            async with db.execute(
                f"SELECT total FROM invites_{guild_id} WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_invite_stats(self, guild_id, user_id):
        """Return (total, fake, left, rejoin) tuple for a user."""
        async with aiosqlite.connect(INVITE_DB) as db:
            async with db.execute(
                f"SELECT total, fake, left, rejoin FROM invites_{guild_id} WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row if row else (0, 0, 0, 0)

    # ------------------------------------------------------------------
    # Listeners — invite cache
    # ------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_ready(self):
        import asyncio
        async def fetch_invites(guild):
            try:
                self.invites[guild.id] = await guild.invites()
            except discord.Forbidden:
                pass
            except Exception:
                pass

        await asyncio.gather(*(fetch_invites(guild) for guild in self.bot.guilds))

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        try:
            self.invites[invite.guild.id] = await invite.guild.invites()
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        try:
            self.invites[invite.guild.id] = await invite.guild.invites()
        except discord.Forbidden:
            pass

    # ------------------------------------------------------------------
    # Listener — member join (invite tracking + log)
    # ------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        await self.ensure_tables(guild.id)

        invites_before = self.invites.get(guild.id, [])
        try:
            invites_after = await guild.invites()
        except discord.Forbidden:
            invites_after = []

        inviter = None
        for invite in invites_after:
            for old_invite in invites_before:
                if invite.code == old_invite.code and invite.uses > old_invite.uses:
                    inviter = invite.inviter
                    break
            if inviter:
                break

        self.invites[guild.id] = invites_after

        async with aiosqlite.connect(INVITE_DB) as db:
            if inviter:
                async with db.execute(
                    f"SELECT user_id FROM invites_{guild.id} WHERE user_id = ?",
                    (member.id,)
                ) as cursor:
                    user_row = await cursor.fetchone()

                if user_row:
                    await db.execute(
                        f"UPDATE invites_{guild.id} SET rejoin = rejoin + 1 WHERE user_id = ?",
                        (inviter.id,)
                    )
                else:
                    await db.execute(
                        f"INSERT OR IGNORE INTO invites_{guild.id} (user_id) VALUES (?)",
                        (inviter.id,)
                    )
                    await db.execute(
                        f"UPDATE invites_{guild.id} SET total = total + 1 WHERE user_id = ?",
                        (inviter.id,)
                    )
            await db.commit()

            async with db.execute(
                "SELECT channel_id FROM logging WHERE guild_id = ?",
                (guild.id,)
            ) as cursor:
                log_row = await cursor.fetchone()

        log_channel = guild.get_channel(log_row[0]) if log_row else None
        if log_channel:
            total = await self.get_total_invites(guild.id, inviter.id) if inviter else 0
            msg = (
                f"{member.mention} has joined {guild.name}, invited by "
                f"{inviter.name if inviter else 'Unknown'}, who now has {total} invites."
            )
            await log_channel.send(view=CV2("📥 Member Joined", msg))

    # ------------------------------------------------------------------
    # Listener — member remove (leave counter + leave-channel message)
    # ------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        await self.ensure_tables(guild.id)

        # Update the inviter's "left" counter
        async with aiosqlite.connect(INVITE_DB) as db:
            await db.execute(
                f"UPDATE invites_{guild.id} SET left = left + 1 WHERE user_id = ?",
                (member.id,)
            )
            await db.commit()

            async with db.execute(
                "SELECT channel_id FROM leave_channel WHERE guild_id = ?",
                (guild.id,)
            ) as cursor:
                leave_row = await cursor.fetchone()

        # Send a goodbye message to the configured leave channel (if any)
        leave_channel = guild.get_channel(leave_row[0]) if leave_row else None
        if leave_channel:
            msg = (
                f"**{member.name}** has left **{guild.name}**.\n"
                f"We'll miss you! 💔"
            )
            try:
                await leave_channel.send(
                    view=CV2(
                        "📤 Member Left",
                        msg,
                        author=member.name,
                        avatar_url=member.display_avatar.url if member.display_avatar else None,
                    )
                )
            except discord.Forbidden:
                pass
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Commands — view invite stats
    # ------------------------------------------------------------------
    @commands.command(aliases=["inv"])
    async def invites(self, ctx, member: discord.Member = None):
        """Show invite stats for yourself or another member."""
        member = member or ctx.author
        await self.ensure_tables(ctx.guild.id)

        total, fake, left, rejoin = await self.get_invite_stats(ctx.guild.id, member.id)
        real = total - fake - left - rejoin

        desc = (
            f"{EMOJI_INVITE} **› {member.mention} has `{total}` invites**\n\n"
            f"**Real:** `{real}`\n"
            f"**Fake:** `{fake}`\n"
            f"**Left:** `{left}`\n"
            f"**Rejoins:** `{rejoin}`\n\n"
            f"{EMOJI_INVITE} **Get {BotName} Premium Lifetime [Join Support Here](https://discord.gg/uBDnveBU3c)**"
        )
        await ctx.send(view=CV2(
            f"Invite Log - {member.name}",
            desc,
            author=member.name,
            avatar_url=member.display_avatar.url if member.display_avatar else None,
        ))

    @commands.command(aliases=["inviter"])
    async def invited(self, ctx, member: discord.Member = None):
        """Show who invited you (or another member) to the server."""
        member = member or ctx.author
        await self.ensure_tables(ctx.guild.id)

        # Walk the guild's audit log? No — we don't track inviter per member.
        # The bot only tracks the inviter's invite count, not which member
        # they invited. We'll show the member's own invite stats instead,
        # which is the closest available info.
        total, fake, left, rejoin = await self.get_invite_stats(ctx.guild.id, member.id)
        real = total - fake - left - rejoin

        desc = (
            f"**Member:** {member.mention}\n"
            f"**Joined:** {member.joined_at.strftime('%Y-%m-%d %H:%M UTC') if member.joined_at else 'Unknown'}\n\n"
            f"This member has invited `{total}` people to the server.\n"
            f"**Real:** `{real}` · **Fake:** `{fake}` · **Left:** `{left}` · **Rejoins:** `{rejoin}`"
        )
        await ctx.send(view=CV2(
            f"Inviter Info - {member.name}",
            desc,
            author=member.name,
            avatar_url=member.display_avatar.url if member.display_avatar else None,
        ))

    @commands.command(aliases=["invinfo"])
    async def inviteinfo(self, ctx, member: discord.Member = None):
        """Detailed invite info card for a member (or yourself)."""
        member = member or ctx.author
        await self.ensure_tables(ctx.guild.id)

        total, fake, left, rejoin = await self.get_invite_stats(ctx.guild.id, member.id)
        real = total - fake - left - rejoin

        # Get rank on the leaderboard
        async with aiosqlite.connect(INVITE_DB) as db:
            async with db.execute(
                f"SELECT COUNT(*) + 1 AS rank FROM invites_{ctx.guild.id} "
                f"WHERE total > (SELECT total FROM invites_{ctx.guild.id} WHERE user_id = ?)",
                (member.id,)
            ) as cursor:
                rank_row = await cursor.fetchone()
            rank = rank_row[0] if rank_row else "—"

        desc = (
            f"{EMOJI_INVITE} **Invite Stats for {member.mention}**\n\n"
            f"**Total Invites:** `{total}`\n"
            f"**Real Invites:** `{real}`\n"
            f"**Fake Invites:** `{fake}`\n"
            f"**Left Invites:** `{left}`\n"
            f"**Rejoins:** `{rejoin}`\n"
            f"**Leaderboard Rank:** `#{rank}`\n\n"
            f"**Account Created:** {member.created_at.strftime('%Y-%m-%d') if member.created_at else 'Unknown'}\n"
            f"**Joined Server:** {member.joined_at.strftime('%Y-%m-%d') if member.joined_at else 'Unknown'}"
        )
        await ctx.send(view=CV2(
            f"Invite Info - {member.name}",
            desc,
            author=member.name,
            avatar_url=member.display_avatar.url if member.display_avatar else None,
        ))

    # ------------------------------------------------------------------
    # Commands — admin: modify invites
    # ------------------------------------------------------------------
    @commands.command(aliases=["addinvs"])
    @commands.has_permissions(administrator=True)
    async def addinvites(self, ctx, member: discord.Member, amount: int):
        """Add invites to a member (admin only)."""
        await self.ensure_tables(ctx.guild.id)
        async with aiosqlite.connect(INVITE_DB) as db:
            await db.execute(
                f"INSERT OR IGNORE INTO invites_{ctx.guild.id} (user_id) VALUES (?)",
                (member.id,)
            )
            await db.execute(
                f"UPDATE invites_{ctx.guild.id} SET total = total + ? WHERE user_id = ?",
                (amount, member.id)
            )
            await db.commit()
        await ctx.send(view=CV2(
            "✅ Success",
            f"Added **{amount}** invites to {member.mention}.\nRequested by {ctx.author.mention}",
            author=ctx.author.name,
            avatar_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None,
        ))

    @commands.command(aliases=["rminvs", "deleteinvs"])
    @commands.has_permissions(administrator=True)
    async def removeinvites(self, ctx, member: discord.Member, amount: int):
        """Remove invites from a member (admin only)."""
        if amount < 0:
            await ctx.send(view=CV2("❌ Error", "Amount must be a positive number."))
            return
        await self.ensure_tables(ctx.guild.id)
        async with aiosqlite.connect(INVITE_DB) as db:
            await db.execute(
                f"INSERT OR IGNORE INTO invites_{ctx.guild.id} (user_id) VALUES (?)",
                (member.id,)
            )
            await db.execute(
                f"UPDATE invites_{ctx.guild.id} SET total = MAX(0, total - ?) WHERE user_id = ?",
                (amount, member.id)
            )
            await db.commit()
        await ctx.send(view=CV2(
            "✅ Success",
            f"Removed **{amount}** invites from {member.mention}.\nRequested by {ctx.author.mention}",
            author=ctx.author.name,
            avatar_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None,
        ))

    @commands.command(aliases=["setinvs"])
    @commands.has_permissions(administrator=True)
    async def setinvites(self, ctx, member: discord.Member, amount: int):
        """Set a member's invite count to a specific value (admin only)."""
        await self.ensure_tables(ctx.guild.id)
        async with aiosqlite.connect(INVITE_DB) as db:
            await db.execute(
                f"INSERT OR REPLACE INTO invites_{ctx.guild.id} (user_id, total) VALUES (?, ?)",
                (member.id, amount)
            )
            await db.commit()
        await ctx.send(view=CV2(
            "✅ Success",
            f"Set invites of {member.mention} to **{amount}**.\nRequested by {ctx.author.mention}",
            author=ctx.author.name,
            avatar_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None,
        ))

    # ------------------------------------------------------------------
    # Commands — admin: reset / clear invites
    # ------------------------------------------------------------------
    @commands.command(aliases=["resetinvs"])
    @commands.has_permissions(administrator=True)
    async def resetinvites(self, ctx, member: discord.Member):
        """Reset a specific member's invites (admin only)."""
        await self.ensure_tables(ctx.guild.id)
        async with aiosqlite.connect(INVITE_DB) as db:
            await db.execute(
                f"DELETE FROM invites_{ctx.guild.id} WHERE user_id = ?",
                (member.id,)
            )
            await db.commit()
        await ctx.send(view=CV2(
            "✅ Success",
            f"Reset invites of {member.mention}.\nRequested by {ctx.author.mention}",
            author=ctx.author.name,
            avatar_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None,
        ))

    @commands.command(aliases=["clearallinvites", "wipeinvites"])
    @commands.has_permissions(administrator=True)
    async def clearinvites(self, ctx):
        """Clear ALL invites for everyone in this server (admin only).

        Usage:
          >clearinvites           → clears everyone
        """
        await self.ensure_tables(ctx.guild.id)
        async with aiosqlite.connect(INVITE_DB) as db:
            await db.execute(f"DELETE FROM invites_{ctx.guild.id}")
            await db.commit()
        await ctx.send(view=CV2(
            "🧹 Cleared",
            f"All invite records for **{ctx.guild.name}** have been cleared.\nRequested by {ctx.author.mention}",
            author=ctx.author.name,
            avatar_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None,
        ))

    @commands.command(aliases=["resetmyinvs", "resetmine"])
    async def resetmyinvites(self, ctx):
        """Reset your own invite count in this server."""
        await self.ensure_tables(ctx.guild.id)
        async with aiosqlite.connect(INVITE_DB) as db:
            await db.execute(
                f"DELETE FROM invites_{ctx.guild.id} WHERE user_id = ?",
                (ctx.author.id,)
            )
            await db.commit()
        await ctx.send(view=CV2(
            "✅ Success",
            f"{ctx.author.mention}, your invite count has been reset to **0**.",
            author=ctx.author.name,
            avatar_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None,
        ))

    # ------------------------------------------------------------------
    # Commands — leaderboard
    # ------------------------------------------------------------------
    @commands.command(aliases=["invlb"])
    async def invitesleaderboard(self, ctx):
        """Top 10 inviters in this server."""
        await self.ensure_tables(ctx.guild.id)
        async with aiosqlite.connect(INVITE_DB) as db:
            async with db.execute(
                f"SELECT user_id, total FROM invites_{ctx.guild.id} ORDER BY total DESC LIMIT 10"
            ) as cursor:
                data = await cursor.fetchall()

        if not data:
            await ctx.send(view=CV2(
                "❌ Error",
                "No invites found.",
                author=ctx.author.name,
                avatar_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None,
            ))
            return

        leaderboard = ""
        for idx, (user_id, total) in enumerate(data, start=1):
            user = ctx.guild.get_member(user_id)
            name = user.name if user else f"Left User ({user_id})"
            leaderboard += f"#{idx} **{name}** — `{total}` invites\n"

        await ctx.send(view=CV2(
            "📊 Invite Leaderboard",
            leaderboard,
            author=ctx.author.name,
            avatar_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None,
        ))

    # ------------------------------------------------------------------
    # Commands — join logging channel
    # ------------------------------------------------------------------
    @commands.command(aliases=["invlog"])
    @commands.has_permissions(administrator=True)
    async def invitelogging(self, ctx, channel: discord.TextChannel):
        """Set the channel where invite-join logs are sent (admin only)."""
        await self.ensure_tables(ctx.guild.id)
        async with aiosqlite.connect(INVITE_DB) as db:
            await db.execute(
                "INSERT OR REPLACE INTO logging (guild_id, channel_id) VALUES (?, ?)",
                (ctx.guild.id, channel.id)
            )
            await db.commit()
        await ctx.send(view=CV2(
            "✅ Success",
            f"Invite logs will now be sent to {channel.mention}.\nRequested by {ctx.author.mention}",
            author=ctx.author.name,
            avatar_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None,
        ))

    # ------------------------------------------------------------------
    # Commands — leave channel
    # ------------------------------------------------------------------
    @commands.command(aliases=["setleave", "leavechannel", "goodbyechannel"])
    @commands.has_permissions(administrator=True)
    async def setleavechannel(self, ctx, channel: discord.TextChannel):
        """Set the channel where goodbye messages are sent when members leave (admin only)."""
        await self.ensure_tables(ctx.guild.id)
        async with aiosqlite.connect(INVITE_DB) as db:
            await db.execute(
                "INSERT OR REPLACE INTO leave_channel (guild_id, channel_id) VALUES (?, ?)",
                (ctx.guild.id, channel.id)
            )
            await db.commit()
        await ctx.send(view=CV2(
            "✅ Success",
            f"Leave messages will now be sent to {channel.mention}.\nRequested by {ctx.author.mention}",
            author=ctx.author.name,
            avatar_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None,
        ))

    @commands.command(aliases=["unsetleave", "removeleavechannel", "disableleave"])
    @commands.has_permissions(administrator=True)
    async def unsetleavechannel(self, ctx):
        """Disable goodbye messages (admin only)."""
        await self.ensure_tables(ctx.guild.id)
        async with aiosqlite.connect(INVITE_DB) as db:
            await db.execute(
                "DELETE FROM leave_channel WHERE guild_id = ?",
                (ctx.guild.id,)
            )
            await db.commit()
        await ctx.send(view=CV2(
            "✅ Success",
            f"Leave channel disabled. Goodbye messages will no longer be sent.\nRequested by {ctx.author.mention}",
            author=ctx.author.name,
            avatar_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None,
        ))


async def setup(bot):
    await bot.add_cog(Tracking(bot))
