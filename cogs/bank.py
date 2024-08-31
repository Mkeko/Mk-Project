import discord
from discord.ext import commands
import aiosqlite

class Bank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "./db/economy.db"
        bot.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        async with aiosqlite.connect(self.db_path) as db:
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
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT coins, weekly_timestamp, daily_timestamp, bank FROM users WHERE id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
                if user is None:
                    # Initialize user data if not found
                    await db.execute(
                        "INSERT INTO users (id, coins, weekly_timestamp, daily_timestamp, bank) VALUES (?, 0, 0, 0, 0)",
                        (user_id,)
                    )
                    await db.commit()
                    return {"coins": 0, "weekly_timestamp": 0, "daily_timestamp": 0, "bank": 0}
                else:
                    return {
                        "coins": user[0],
                        "weekly_timestamp": user[1],
                        "daily_timestamp": user[2],
                        "bank": user[3],
                    }

    @discord.slash_command(name="bank", description="Bank-related commands.")
    async def bank(self, ctx: discord.ApplicationContext, action: discord.Option(str, "Choose an action", choices=["deposit", "balance", "withdraw", "help"]), amount: discord.Option(int, "Amount to deposit/withdraw", required=False)):

        if action == "deposit":
            if amount is None or amount <= 0:
                await ctx.respond("The deposit amount must be a positive number.", ephemeral=True)
                return

            user_data = await self.get_user(ctx.author.id)
            if user_data["coins"] < amount:
                await ctx.respond("Insufficient coins in your wallet to deposit.", ephemeral=True)
                return

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE users SET coins = coins - ?, bank = bank + ? WHERE id = ?", (amount, amount, ctx.author.id))
                await db.commit()

            embed = discord.Embed(
                title="Deposit Successful",
                description=f"You have successfully deposited {amount} coins into your bank.",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png")
            await ctx.respond(embed=embed)

        elif action == "withdraw":
            if amount is None or amount <= 0:
                await ctx.respond("The withdraw amount must be a positive number.", ephemeral=True)
                return

            user_data = await self.get_user(ctx.author.id)
            if user_data["bank"] < amount:
                await ctx.respond("Insufficient coins in your bank to withdraw.", ephemeral=True)
                return

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE users SET bank = bank - ?, coins = coins + ? WHERE id = ?", (amount, amount, ctx.author.id))
                await db.commit()

            embed = discord.Embed(
                title="Withdrawal Successful",
                description=f"You have successfully withdrawn {amount} coins from your bank.",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png")
            await ctx.respond(embed=embed)

        elif action == "balance":
            user_data = await self.get_user(ctx.author.id)
            embed = discord.Embed(
                title=f"{ctx.author.name}'s Bank Balance",
                description=(
                    f"**Bank Balance:** {user_data['bank']} coins\n"
                    f"**Wallet Balance:** {user_data['coins']} coins"
                ),
                color=discord.Color.blue(),
            )
            embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png")
            await ctx.respond(embed=embed)

        elif action == "help":
            embed = discord.Embed(
                title="Bank Command Help",
                description="List of Bank commands:",
                color=discord.Color.green()
            )
            embed.add_field(name="/bank deposit <amount>", value="Deposit coins into your bank.", inline=False)
            embed.add_field(name="/bank withdraw <amount>", value="Withdraw coins from your bank.", inline=False)
            embed.add_field(name="/bank balance", value="Check your bank and wallet balance.", inline=False)
            embed.add_field(name="/bank help", value="Display this help message.", inline=False)

            await ctx.respond(embed=embed)

        else:
            await ctx.respond("Invalid action. Use /bank help for more information.", ephemeral=True)

def setup(bot):
    bot.add_cog(Bank(bot))
