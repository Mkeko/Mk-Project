import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import datetime
import aiosqlite

load_dotenv("../.env")

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_embed(self, ctx, title, description, color):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png"
        )
        await ctx.respond(embed=embed)

    # Command for banning a member
    @discord.slash_command(name="ban", description="Ban a member from the server.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, reason: str = None):
        await ctx.defer()
        try:
            await member.ban(reason=reason)
            await self.send_embed(ctx, "Member Banned", f"{member.mention} has been banned.", discord.Color.red())
        except discord.Forbidden:
            await self.send_embed(ctx, "Error", "Insufficient permissions to ban this member.", discord.Color.red())

    # Command for kicking a member
    @discord.slash_command(name="kick", description="Kick a member from the server.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, reason: str = None):
        await ctx.defer()
        try:
            await member.kick(reason=reason)
            await self.send_embed(ctx, "Member Kicked", f"{member.mention} has been kicked.", discord.Color.orange())
        except discord.Forbidden:
            await self.send_embed(ctx, "Error", "Insufficient permissions to kick this member.", discord.Color.red())

    # Command for timing out a member
    @discord.slash_command(name="timeout", description="Timeout a member from the server.")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: int, reason: str = None):
        await ctx.defer()
        try:
            timeout_duration = discord.utils.utcnow() + datetime.timedelta(seconds=duration)
            await member.timeout(timeout_duration, reason=reason)

            duration_str = f"{duration // 60} minutes and {duration % 60} seconds" if duration >= 60 else f"{duration} seconds"
            await self.send_embed(ctx, "Member Timed Out", f"{member.mention} has been timed out for {duration_str}.", discord.Color.blue())
        except discord.Forbidden:
            await self.send_embed(ctx, "Error", "Insufficient permissions to timeout this member.", discord.Color.red())
        except Exception as e:
            await self.send_embed(ctx, "Error", f"An error occurred: {str(e)}", discord.Color.red())

    # Command for unbanning a member
    @discord.slash_command(name="unban", description="Unban a member from the server.")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, member: discord.User, reason: str = None):
        await ctx.defer()
        try:
            await ctx.guild.unban(member, reason=reason)
            await self.send_embed(ctx, "Member Unbanned", f"{member.mention} has been unbanned.", discord.Color.green())
        except discord.Forbidden:
            await self.send_embed(ctx, "Error", "Insufficient permissions to unban this member.", discord.Color.red())
        except discord.NotFound:
            await self.send_embed(ctx, "Error", "Member not found or not banned.", discord.Color.red())

    # Command for removing timeout from a member
    @discord.slash_command(name="untimeout", description="Remove timeout from a member.")
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member, reason: str = None):
        await ctx.defer()
        try:
            await member.remove_timeout(reason=reason)
            await self.send_embed(ctx, "Member Untimed Out", f"{member.mention} has been untimed out.", discord.Color.green())
        except discord.Forbidden:
            await self.send_embed(ctx, "Error", "Insufficient permissions to untimeout this member.", discord.Color.red())
        except Exception as e:
            await self.send_embed(ctx, "Error", f"An error occurred: {str(e)}", discord.Color.red())

    ## WARNING SYSTEM

    async def create_warn_table(self, guild_id):
        table_name = f"warns_{guild_id}"
        async with aiosqlite.connect("./db/configs.db") as db:
            await db.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} (user_id INTEGER, reason TEXT)"
            )
            await db.commit()

    async def add_warn(self, guild_id, user_id, reason):
        table_name = f"warns_{guild_id}"
        async with aiosqlite.connect("./db/configs.db") as db:
            await db.execute(
                f"INSERT INTO {table_name} (user_id, reason) VALUES (?, ?)",
                (user_id, reason)
            )
            await db.commit()

    async def get_warns(self, guild_id, user_id):
        table_name = f"warns_{guild_id}"
        async with aiosqlite.connect("./db/configs.db") as db:
            async with db.execute(
                f"SELECT rowid, reason FROM {table_name} WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return rows

    async def remove_warn(self, guild_id, user_id, warn_id):
        table_name = f"warns_{guild_id}"
        async with aiosqlite.connect("./db/configs.db") as db:
            await db.execute(
                f"DELETE FROM {table_name} WHERE rowid = ? AND user_id = ?",
                (warn_id, user_id)
            )
            await db.commit()

    warn = discord.SlashCommandGroup(name="warn", description="Warning commands")

    @warn.command(name="user", description="Warn a user")
    async def warn_user(self, ctx, user: discord.User, *, reason: str):
        await self.create_warn_table(ctx.guild.id)
        await self.add_warn(ctx.guild.id, user.id, reason)

        embed = discord.Embed(
            title="User Warned",
            description=f"{user.mention} has been warned for:\n{reason}",
            color=discord.Color.orange()
        )
        await ctx.respond(embed=embed)

    @warn.command(name="list", description="List warnings for a user")
    async def warn_list(self, ctx, user: discord.User):
        await self.create_warn_table(ctx.guild.id)
        warns = await self.get_warns(ctx.guild.id, user.id)

        if warns:
            embed = discord.Embed(
                title=f"Warnings for {user.display_name}",
                color=discord.Color.orange()
            )
            for idx, warn in enumerate(warns, 1):
                embed.add_field(name=f"Warning {idx}", value=warn[1], inline=False)
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="No Warnings",
                description=f"{user.display_name} has no warnings.",
                color=discord.Color.green()
            )
            await ctx.respond(embed=embed)

    @warn.command(name="remove", description="Remove a specific warning from a user")
    async def warn_remove(self, ctx, user: discord.User, warn_id: int):
        await self.create_warn_table(ctx.guild.id)
        warns = await self.get_warns(ctx.guild.id, user.id)

        if any(warn[0] == warn_id for warn in warns):
            await self.remove_warn(ctx.guild.id, user.id, warn_id)
            embed = discord.Embed(
                title="Warning Removed",
                description=f"Removed warning ID {warn_id} from {user.display_name}.",
                color=discord.Color.green()
            )
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="Warning Not Found",
                description=f"No warning with ID {warn_id} found for {user.display_name}.",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed)

    ## INVITE-BASED AUTO-BANNING SYSTEM

    async def create_invite_table(self, guild_id):
        table_name = f"invite_config_{guild_id}"
        async with aiosqlite.connect("./db/configs.db") as db:
            await db.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} (invite_count INTEGER)"
            )
            await db.commit()

    async def get_invite_threshold(self, guild_id):
        table_name = f"invite_config_{guild_id}"
        async with aiosqlite.connect("./db/configs.db") as db:
            async with db.execute(
                f"SELECT invite_count FROM {table_name}"
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_invite_threshold(self, guild_id, count):
        table_name = f"invite_config_{guild_id}"
        async with aiosqlite.connect("./db/configs.db") as db:
            await db.execute(
                f"DELETE FROM {table_name}"
            )
            await db.execute(
                f"INSERT INTO {table_name} (invite_count) VALUES (?)",
                (count,)
            )
            await db.commit()

    @discord.slash_command(name="set_invite_threshold", description="Set the invite threshold for auto-banning.")
    @commands.has_permissions(administrator=True)
    async def set_invite_threshold_command(self, ctx, count: int):
        await self.create_invite_table(ctx.guild.id)
        await self.set_invite_threshold(ctx.guild.id, count)
        await self.send_embed(ctx, "Invite Threshold Set", f"Invite threshold has been set to {count}.", discord.Color.green())

    @discord.slash_command(name="view_invite_threshold", description="View the current invite threshold.")
    async def view_invite_threshold(self, ctx):
        await self.create_invite_table(ctx.guild.id)
        threshold = await self.get_invite_threshold(ctx.guild.id)

        if threshold is not None:
            await self.send_embed(ctx, "Current Invite Threshold", f"The current invite threshold is {threshold}.", discord.Color.blue())
        else:
            await self.send_embed(ctx, "No Threshold Set", "No invite threshold is currently set.", discord.Color.red())

    async def check_invites(self, member):
        async with aiosqlite.connect("./db/configs.db") as db:
            table_name = f"invite_config_{member.guild.id}"
            threshold = await db.execute(f"SELECT invite_count FROM {table_name}")
            threshold = await threshold.fetchone()
            if threshold:
                threshold = threshold[0]
                # Get invite counts for the member
                invites = await member.guild.invites()
                invite_count = sum(invite.uses for invite in invites if invite.inviter == member)
                if invite_count >= threshold:
                    await member.ban(reason="Exceeded invite threshold")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.check_invites(member)

def setup(bot):
    bot.add_cog(Mod(bot))
