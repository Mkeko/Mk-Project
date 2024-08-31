import discord
from discord.ext import commands
import aiosqlite

class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def create_table(self):
        """Create the main table if it doesn't exist."""
        async with aiosqlite.connect("./db/configs.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS autorole_config (
                    guild_id INTEGER PRIMARY KEY,
                    role_id INTEGER
                )
            """)
            await db.commit()

    async def set_autorole(self, guild_id, role_id):
        """Set the auto role for a guild."""
        await self.create_table()
        async with aiosqlite.connect("./db/configs.db") as db:
            await db.execute("""
                INSERT OR REPLACE INTO autorole_config (guild_id, role_id)
                VALUES (?, ?)
            """, (guild_id, role_id))
            await db.commit()

    async def get_autorole(self, guild_id):
        """Retrieve the auto role for a guild."""
        await self.create_table()
        async with aiosqlite.connect("./db/configs.db") as db:
            async with db.execute("""
                SELECT role_id FROM autorole_config WHERE guild_id = ?
            """, (guild_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def delete_autorole(self, guild_id):
        """Delete the auto role configuration for a guild."""
        await self.create_table()
        async with aiosqlite.connect("./db/configs.db") as db:
            await db.execute("""
                DELETE FROM autorole_config WHERE guild_id = ?
            """, (guild_id,))
            await db.commit()

    autorole = discord.SlashCommandGroup(name="autorole", description="Auto role commands")

    @autorole.command(name="set", description="Set the auto role for the server")
    @commands.has_permissions(manage_roles=True)
    async def autorole_set(self, ctx, role: discord.Role):
        if ctx.guild.me.guild_permissions.manage_roles:
            await self.set_autorole(ctx.guild.id, role.id)
            embed = discord.Embed(
                title="Auto Role Set",
                description=f"Auto role has been set to {role.mention}.",
                color=discord.Color.blue()
            )
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have the required permissions to manage roles.",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed)

    @autorole.command(name="disable", description="Disable the auto role")
    @commands.has_permissions(manage_roles=True)
    async def autorole_disable(self, ctx):
        if ctx.guild.me.guild_permissions.manage_roles:
            await self.delete_autorole(ctx.guild.id)
            embed = discord.Embed(
                title="Auto Role Disabled",
                description="Auto role has been disabled.",
                color=discord.Color.blue()
            )
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have the required permissions to manage roles.",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        role_id = await self.get_autorole(member.guild.id)
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    pass

def setup(bot):
    bot.add_cog(AutoRole(bot))
