import discord
from discord.ext import commands
import aiosqlite
import datetime
import aiohttp
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.initialize_db())
        self.username_cache_file = "./temp/username_cache.json"
        self.username_cache = self.load_username_cache()
        self.guild_id = int(os.getenv("GUILD_ID", "0000000000000000000"))
        self.channel_id = int(os.getenv("CHANNEL_ID", "000000000000000000"))

    def load_username_cache(self):
        if os.path.exists(self.username_cache_file):
            with open(self.username_cache_file, 'r') as f:
                return json.load(f)
        return {}

    def save_username_cache(self):
        with open(self.username_cache_file, 'w') as f:
            json.dump(self.username_cache, f, indent=4)

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

    async def initialize_db(self):
        async with aiosqlite.connect("./db/economy.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    coins INTEGER NOT NULL,
                    weekly_timestamp INTEGER NOT NULL,
                    daily_timestamp INTEGER NOT NULL,
                    bank INTEGER NOT NULL
                )
            """)
            await db.commit()

    async def get_user(self, user_id):
        async with aiosqlite.connect("./db/economy.db") as db:
            async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
                if user is None:
                    await db.execute(
                        "INSERT INTO users (id, coins, weekly_timestamp, daily_timestamp, bank) VALUES (?, ?, ?, ?, ?)",
                        (user_id, 0, 0, 0, 0),
                    )
                    await db.commit()
                    return {
                        "coins": 0,
                        "weekly_timestamp": 0,
                        "daily_timestamp": 0,
                        "bank": 0
                    }
                else:
                    return {
                        "coins": user[1],
                        "weekly_timestamp": user[2],
                        "daily_timestamp": user[3],
                        "bank": user[4],
                    }

    @discord.slash_command(name="economy", description="Economy commands.")
    async def economy(
        self,
        ctx: discord.ApplicationContext,
        action: discord.Option(str, "Choose an action", choices=["daily", "weekly", "balance", "leaderboard", "transfer", "help"]),
        recipient: discord.Option(discord.Member, "Recipient for transfer", required=False),
        amount: discord.Option(int, "Amount of coins", required=False),
        code: discord.Option(str, "Coupon code", required=False),
        max_uses: discord.Option(int, "Maximum uses for the coupon", required=False)
    ):
        try:
            if action == "daily":
                user = await self.get_user(ctx.author.id)
                now = round(datetime.datetime.now().timestamp())

                if user["daily_timestamp"] == 0 or user["daily_timestamp"] + 86400 <= now:
                    async with aiosqlite.connect("./db/economy.db") as db:
                        await db.execute(
                            "UPDATE users SET coins = coins + 50, daily_timestamp = ? WHERE id = ?",
                            (now, ctx.author.id),
                        )
                        await db.commit()
                    embed = discord.Embed(
                        title="Daily Reward Claimed",
                        description="You have successfully claimed your daily reward of 50 coins!",
                        color=discord.Color.green()
                    )
                else:
                    wait_time = user["daily_timestamp"] + 86400 - now
                    embed = discord.Embed(
                        title="Daily Reward",
                        description=f"You have already claimed your daily reward! Please wait <t:{user['daily_timestamp'] + 86400}:R> to claim again.",
                        color=discord.Color.red()
                    )
                embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
                await ctx.respond(embed=embed)

            elif action == "weekly":
                user = await self.get_user(ctx.author.id)
                now = round(datetime.datetime.now().timestamp())

                if user["weekly_timestamp"] == 0 or user["weekly_timestamp"] + 604800 <= now:
                    async with aiosqlite.connect("./db/economy.db") as db:
                        await db.execute(
                            "UPDATE users SET coins = coins + 300, weekly_timestamp = ? WHERE id = ?",
                            (now, ctx.author.id),
                        )
                        await db.commit()
                    embed = discord.Embed(
                        title="Weekly Reward Claimed",
                        description="You have successfully claimed your weekly reward of 300 coins!",
                        color=discord.Color.green()
                    )
                else:
                    wait_time = user["weekly_timestamp"] + 604800 - now
                    embed = discord.Embed(
                        title="Weekly Reward",
                        description=f"You have already claimed your weekly reward! Please wait <t:{user['weekly_timestamp'] + 604800}:R> to claim again.",
                        color=discord.Color.red()
                    )
                embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
                await ctx.respond(embed=embed)

            elif action == "balance":
                target_user = recipient or ctx.author
                user_data = await self.get_user(target_user.id)
                embed = discord.Embed(
                    title=f"{target_user.display_name}'s Balance",
                    description=f"You have **{user_data['coins']}** coins.",
                    color=discord.Color.blue(),
                )
                embed.set_thumbnail(url=target_user.avatar.url)
                embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
                await ctx.respond(embed=embed)

            elif action == "leaderboard":
                async with aiosqlite.connect("./db/economy.db") as db:
                    async with db.execute("SELECT * FROM users ORDER BY coins DESC LIMIT 10") as cursor:
                        users = await cursor.fetchall()
                        embed = discord.Embed(
                            title="Economy Leaderboard",
                            description="",
                            color=discord.Color.blue()
                        )

                        if not users:
                            embed.description = "No leaderboard data available."
                        else:
                            async with aiohttp.ClientSession() as session:
                                for idx, user in enumerate(users, start=1):
                                    user_id = user[0]
                                    username = await self.fetch_username(user_id)
                                    
                                    embed.add_field(
                                        name=f"#{idx}: {username}",
                                        value=f"**{user[1]}** Coins",
                                        inline=False
                                    )

                        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
                        await ctx.respond(embed=embed)

            elif action == "transfer":
                if recipient is None or amount is None or amount <= 0:
                    await ctx.respond("You must specify a recipient and a positive amount.", ephemeral=True)
                    return

                if recipient.id == ctx.author.id:
                    await ctx.respond("You cannot transfer coins to yourself.", ephemeral=True)
                    return

                sender_data = await self.get_user(ctx.author.id)
                recipient_data = await self.get_user(recipient.id)

                if sender_data['coins'] < amount:
                    await ctx.respond("You do not have enough coins to complete this transfer.", ephemeral=True)
                    return

                async with aiosqlite.connect("./db/economy.db") as db:
                    await db.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (amount, ctx.author.id))
                    await db.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, recipient.id))
                    await db.commit()

                embed = discord.Embed(
                    title="Transfer Successful",
                    description=f"You have successfully transferred {amount} coins to {recipient.display_name}.",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
                await ctx.respond(embed=embed)

                try:
                    dm_embed = discord.Embed(
                        title="Coins Received",
                        description=f"You have received {amount} coins from {ctx.author.display_name}.",
                        color=discord.Color.green()
                    )
                    await recipient.send(embed=dm_embed)
                except discord.Forbidden:
                    pass  # If the recipient has DMs disabled, we just skip sending the DM

                guild = self.bot.get_guild(self.guild_id)
                channel = guild.get_channel(self.channel_id) if guild else None

                if channel:
                    log_embed = discord.Embed(
                        title="Coins Transferred",
                        description=f"{ctx.author.display_name} has transferred {amount} coins to {recipient.display_name}.",
                        color=discord.Color.orange()
                    )
                    await channel.send(embed=log_embed)

            elif action == "help":
                embed = discord.Embed(
                    title="Economy Commands Help",
                    description=(
                        "**/economy daily** - Claim your daily reward\n"
                        "**/economy weekly** - Claim your weekly reward\n"
                        "**/economy balance** - Check your balance\n"
                        "**/economy leaderboard** - View the top users\n"
                        "**/economy transfer** - Transfer coins to another user"
                    ),
                    color=discord.Color.blue(),
                )
                embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
                await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"An error occurred: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(Economy(bot))
