import discord
from discord.ext import commands
import aiosqlite
import aiohttp
import random
import time
import json
import os

class Exp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown = {}
        self.xp_cooldown = 120  # Cooldown time in seconds
        self.username_cache = {}
        self.username_cache_file = "./temp/username_cache.json"
        self.level_roles = {}  # Dictionary to store level-based roles
        self.load_username_cache()

    def load_username_cache(self):
        if os.path.exists(self.username_cache_file):
            with open(self.username_cache_file, 'r') as f:
                self.username_cache = json.load(f)
        else:
            self.username_cache = {}

    def save_username_cache(self):
        with open(self.username_cache_file, 'w') as f:
            json.dump(self.username_cache, f)

    async def create_user_table(self, guild_id):
        table_name = f"users_{guild_id}"
        async with aiosqlite.connect("./db/levelsys.db") as db:
            await db.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER, guild_id INTEGER, xp INTEGER, level INTEGER, PRIMARY KEY (id, guild_id))"
            )
            await db.commit()

    async def get_user_data(self, guild_id, user_id):
        await self.create_user_table(guild_id)
        table_name = f"users_{guild_id}"
        async with aiosqlite.connect("./db/levelsys.db") as db:
            async with db.execute(
                f"SELECT xp, level FROM {table_name} WHERE id = ? AND guild_id = ?",
                (user_id, guild_id)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    xp, level = row
                else:
                    xp, level = 0, 1
                    await db.execute(
                        f"INSERT INTO {table_name} (id, guild_id, xp, level) VALUES (?, ?, ?, ?)",
                        (user_id, guild_id, xp, level)
                    )
                    await db.commit()
                return xp, level

    async def update_user_data(self, guild_id, user_id, xp_gain):
        await self.create_user_table(guild_id)
        table_name = f"users_{guild_id}"
        async with aiosqlite.connect("./db/levelsys.db") as db:
            async with db.execute(
                f"SELECT xp, level FROM {table_name} WHERE id = ? AND guild_id = ?",
                (user_id, guild_id)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    current_xp, current_level = row
                    new_xp = current_xp + xp_gain
                    required_xp = 100 * current_level
                    leveled_up = False
                    while new_xp >= required_xp:
                        new_xp -= required_xp
                        current_level += 1
                        required_xp = 100 * current_level
                        leveled_up = True
                    await db.execute(
                        f"UPDATE {table_name} SET xp = ?, level = ? WHERE id = ? AND guild_id = ?",
                        (new_xp, current_level, user_id, guild_id)
                    )
                    await db.commit()
                    return leveled_up, current_level
                else:
                    await db.execute(
                        f"INSERT INTO {table_name} (id, guild_id, xp, level) VALUES (?, ?, ?, ?)",
                        (user_id, guild_id, xp_gain, 1)
                    )
                    await db.commit()
                    return False, 1

    async def fetch_username(self, user_id):
        if user_id in self.username_cache:
            return self.username_cache[user_id]

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://discordlookup.mesalytic.moe/v1/user/{user_id}") as resp:
                if resp.status == 200:
                    user_data = await resp.json()
                    username = user_data.get("username", f"User: {user_id}")
                else:
                    username = f"User: {user_id}"

        self.username_cache[user_id] = username
        self.save_username_cache()
        return username

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        current_time = time.time()
        guild_id = message.guild.id
        user_id = message.author.id

        if user_id in self.cooldown and current_time - self.cooldown[user_id] < self.xp_cooldown:
            return

        xp_gain = random.randint(1, 10)
        leveled_up, new_level = await self.update_user_data(guild_id, user_id, xp_gain)
        self.cooldown[user_id] = current_time

        if leveled_up:
            await self.assign_roles_based_on_level(message.guild, message.author, new_level)
            embed = discord.Embed(
                title="Level Up!",
                description=f"Congratulations {message.author.mention}, you have reached level {new_level}!",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png")
            level_up_message = await message.channel.send(embed=embed)
            await level_up_message.delete(delay=10)

    async def assign_roles_based_on_level(self, guild, member, new_level):
        if guild.id in self.level_roles:
            for level, role_id in self.level_roles[guild.id].items():
                role = guild.get_role(role_id)
                if role and new_level >= level:
                    await member.add_roles(role, reason=f"Leveled up to {new_level}")

    exp = discord.SlashCommandGroup(name="exp", description="Experience points commands")

    @exp.command(name="level", description="Get the level of a user")
    async def get_level(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        xp, level = await self.get_user_data(ctx.guild.id, member.id)
        
        embed = discord.Embed(
            title=f"Level Information for {member.display_name}",
            description=f"{member.display_name} is level {level} with {xp} XP",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.avatar.url)
        embed.set_footer(text="Requested by " + ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png")
        
        await ctx.respond(embed=embed)

    @exp.command(name="stats", description="Show your stats")
    async def stats(self, ctx):
        xp, level = await self.get_user_data(ctx.guild.id, ctx.author.id)
        
        embed = discord.Embed(
            title=f"Your Stats, {ctx.author.display_name}",
            color=discord.Color.orange()
        )
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="XP", value=xp, inline=True)
        embed.set_thumbnail(url=ctx.author.avatar.url)
        embed.set_footer(text="Requested by " + ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png")
        await ctx.respond(embed=embed)

    @exp.command(name="leaderboard", description="Show the leaderboard for XP and levels")
    async def leaderboard(self, ctx):
        table_name = f"users_{ctx.guild.id}"
        async with aiosqlite.connect("./db/levelsys.db") as db:
            async with db.execute(
                f"SELECT id, xp, level FROM {table_name} ORDER BY level DESC, xp DESC LIMIT 10"
            ) as cursor:
                leaderboard_data = await cursor.fetchall()
        
        embed = discord.Embed(
            title="Leaderboard: XP and Levels",
            color=discord.Color.gold()
        )

        if not leaderboard_data:
            embed.description = "No data available."
        else:
            async with aiohttp.ClientSession() as session:
                for idx, (user_id, xp, level) in enumerate(leaderboard_data, start=1):
                    username = await self.fetch_username(user_id)
                    embed.add_field(
                        name=f"#{idx}: {username}",
                        value=f"Level **{level}** with **{xp}** XP",
                        inline=False
                    )

        embed.set_footer(text="Requested by " + ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png")
        await ctx.respond(embed=embed)

    @exp.command(name="roles", description="Manage roles for levels")
    @commands.has_permissions(manage_roles=True)
    async def level_roles(self, ctx, action: str, level: int = None, role: discord.Role = None):
        if action == "give" and level is not None and role is not None:
            if ctx.guild.id not in self.level_roles:
                self.level_roles[ctx.guild.id] = {}
            self.level_roles[ctx.guild.id][level] = role.id
            await ctx.respond(f"Assigned role {role.name} for level {level}.")
        elif action == "remove" and level is not None:
            if ctx.guild.id in self.level_roles and level in self.level_roles[ctx.guild.id]:
                del self.level_roles[ctx.guild.id][level]
                await ctx.respond(f"Removed role assignment for level {level}.")
            else:
                await ctx.respond("No role assignment found for that level.")
        elif action == "list":
            embed = discord.Embed(
                title="Level Role Assignments",
                color=discord.Color.purple()
            )
            if ctx.guild.id in self.level_roles and self.level_roles[ctx.guild.id]:
                for level, role_id in self.level_roles[ctx.guild.id].items():
                    role = ctx.guild.get_role(role_id)
                    embed.add_field(name=f"Level {level}", value=role.name if role else "Role not found", inline=False)
            else:
                embed.description = "No role assignments found."
            await ctx.respond(embed=embed)
        else:
            await ctx.respond("Invalid action. Use `give`, `remove`, or `list`.")

def setup(bot):
    bot.add_cog(Exp(bot))
