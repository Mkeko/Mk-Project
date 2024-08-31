import discord
from discord.ext import commands
import aiosqlite

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    afk = discord.SlashCommandGroup(name="afk", description="Manage your AFK status")

    async def create_afk_table(self, guild_id):
        table_name = f"afk_{guild_id}"
        async with aiosqlite.connect("./db/configs.db") as db:
            await db.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} (user_id INTEGER PRIMARY KEY, reason TEXT)"
            )
            await db.commit()

    @afk.command(name="set", description="Set your AFK status")
    async def afk_set(self, ctx, *, reason: str):
        await self.create_afk_table(ctx.guild.id)
        table_name = f"afk_{ctx.guild.id}"
        
        async with aiosqlite.connect("./db/configs.db") as db:
            # Check if user is already AFK in guild
            async with db.execute(
                f"SELECT reason FROM {table_name} WHERE user_id = ?",
                (ctx.author.id,)
            ) as cursor:
                if await cursor.fetchone():
                    embed = discord.Embed(
                        description="You are already AFK in this server.",
                        color=discord.Color.red()
                    )
                    return await ctx.respond(embed=embed, delete_after=5)

            # Set user as AFK
            await db.execute(
                f"INSERT INTO {table_name} (user_id, reason) VALUES (?, ?)",
                (ctx.author.id, reason),
            )
            await db.commit()

            embed = discord.Embed(
                title="AFK Status Set",
                description=f"Your AFK status has been set to: {reason}",
                color=discord.Color.orange()
            )
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.avatar.url if ctx.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png"
            )

            try:
                await ctx.respond(embed=embed, delete_after=5)
            except discord.HTTPException as e:
                print(f"Failed to respond in AFK set command: {e}")

    @afk.command(name="clearall", description="Clear all AFK statuses (Admin only)")
    @commands.has_permissions(administrator=True)
    async def afk_clearall(self, ctx):
        table_name = f"afk_{ctx.guild.id}"
        async with aiosqlite.connect("./db/configs.db") as db:
            await db.execute(f"DROP TABLE IF EXISTS {table_name}")
            await db.commit()

        embed = discord.Embed(
            description="All AFK statuses have been cleared for this server.",
            color=discord.Color.green()
        )
        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png"
        )
        try:
            await ctx.respond(embed=embed, delete_after=5)
        except discord.HTTPException as e:
            print(f"Failed to respond in AFK clearall command: {e}")

    async def remove_afk_status(self, guild_id, user_id):
        table_name = f"afk_{guild_id}"
        async with aiosqlite.connect("./db/configs.db") as db:
            await db.execute(
                f"DELETE FROM {table_name} WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()

    async def check_afk_status(self, guild_id, user_id):
        table_name = f"afk_{guild_id}"
        async with aiosqlite.connect("./db/configs.db") as db:
            async with db.execute(
                f"SELECT reason FROM {table_name} WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_afk_status(self, guild_id, user_id, reason):
        table_name = f"afk_{guild_id}"
        async with aiosqlite.connect("./db/configs.db") as db:
            await db.execute(
                f"INSERT OR REPLACE INTO {table_name} (user_id, reason) VALUES (?, ?)",
                (user_id, reason)
            )
            await db.commit()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        await self.create_afk_table(message.guild.id)

        async with aiosqlite.connect("./db/configs.db") as db:
            table_name = f"afk_{message.guild.id}"

            # Remove AFK status if user sends a message
            async with db.execute(
                f"SELECT reason FROM {table_name} WHERE user_id = ?",
                (message.author.id,)
            ) as cursor:
                if await cursor.fetchone():
                    await self.remove_afk_status(message.guild.id, message.author.id)
                    embed = discord.Embed(
                        description=f"{message.author.mention}, you are no longer AFK.",
                        color=discord.Color.green()
                    )
                    embed.set_footer(
                        text=f"Requested by {message.author.display_name}",
                        icon_url=message.author.avatar.url if message.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png"
                    )
                    try:
                        await message.channel.send(embed=embed, delete_after=5)
                    except discord.HTTPException as e:
                        print(f"Failed to send message in on_message event: {e}")

            # Mention check for AFK users
            for user in message.mentions:
                if user.bot:
                    continue
                
                async with db.execute(
                    f"SELECT reason FROM {table_name} WHERE user_id = ?",
                    (user.id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        embed = discord.Embed(
                            description=f"{user.display_name} is AFK: {row[0]}",
                            color=discord.Color.orange()
                        )
                        embed.set_footer(
                            text=f"Requested by {message.author.display_name}",
                            icon_url=message.author.avatar.url if message.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png"
                        )
                        try:
                            await message.channel.send(embed=embed, delete_after=5)
                        except discord.HTTPException as e:
                            print(f"Failed to send message in on_message event: {e}")

def setup(bot):
    bot.add_cog(AFK(bot))
