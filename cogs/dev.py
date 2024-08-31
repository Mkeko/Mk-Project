import discord
from discord.ext import commands
import aiosqlite
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID"))

class Dev(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.authorized_user_ids = [DEVELOPER_ID]  # Replace with actual user IDs if needed

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
                    return {"coins": 0, "weekly_timestamp": 0, "daily_timestamp": 0, "bank": 0}
                return {"coins": user[1], "weekly_timestamp": user[2], "daily_timestamp": user[3], "bank": user[4]}

    async def check_permissions(self, ctx):
        if ctx.author.id not in self.authorized_user_ids:
            embed = discord.Embed(title="Permission Denied", description="You do not have permission to use this command.", color=discord.Color.red())
            await ctx.respond(embed=embed, delete_after=5)
            return False
        if ctx.guild is None:
            embed = discord.Embed(title="Invalid Context", description="This command can only be used in a server.", color=discord.Color.red())
            await ctx.respond(embed=embed, delete_after=5)
            return False
        return True

    @discord.slash_command(name="dev", description="Developer commands.")
    async def dev(
        self,
        ctx: discord.ApplicationContext,
        action: discord.Option(str, "Choose an action", choices=["addcoins", "removecoins", "addcoupon", "removecoupon", "listcoupons", "help"]),
        user: discord.Option(discord.Member, "User to modify", required=False),
        amount: discord.Option(int, "Amount of coins", required=False),
        code: discord.Option(str, "Coupon code", required=False),
        max_uses: discord.Option(int, "Maximum uses for the coupon", required=False)
    ):
        if not await self.check_permissions(ctx):
            return
        
        if action == "addcoins":
            if user is None or amount is None or amount <= 0:
                embed = discord.Embed(title="Invalid Parameters", description="You must specify a user and a positive amount.", color=discord.Color.red())
                return await ctx.respond(embed=embed, delete_after=5)
            async with aiosqlite.connect("./db/economy.db") as db:
                await db.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, user.id))
                await db.commit()
                embed = discord.Embed(title="Coins Added", description=f"Added {amount} coins to {user.mention}.", color=discord.Color.green())
                await ctx.respond(embed=embed, delete_after=5)

        elif action == "removecoins":
            if user is None or amount is None or amount <= 0:
                embed = discord.Embed(title="Invalid Parameters", description="You must specify a user and a positive amount.", color=discord.Color.red())
                return await ctx.respond(embed=embed, delete_after=5)
            user_data = await self.get_user(user.id)
            if user_data["coins"] < amount:
                embed = discord.Embed(title="Insufficient Funds", description=f"{user.mention} does not have enough coins.", color=discord.Color.red())
                return await ctx.respond(embed=embed, delete_after=5)
            async with aiosqlite.connect("./db/economy.db") as db:
                await db.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (amount, user.id))
                await db.commit()
                embed = discord.Embed(title="Coins Removed", description=f"Removed {amount} coins from {user.mention}.", color=discord.Color.green())
                await ctx.respond(embed=embed, delete_after=5)

        elif action == "addcoupon":
            if code is None or amount is None or max_uses is None or amount <= 0 or max_uses <= 0:
                embed = discord.Embed(title="Invalid Parameters", description="You must specify a code, coins, and max uses, all of which must be positive.", color=discord.Color.red())
                return await ctx.respond(embed=embed, delete_after=5)
            async with aiosqlite.connect("./db/configs.db") as db:
                await db.execute("INSERT INTO coupons (code, coins, max_uses, usedby) VALUES (?, ?, ?, ?)", (code, amount, max_uses, ""))
                await db.commit()
                embed = discord.Embed(title="Coupon Added", description=f"Added coupon {code} with {amount} coins and {max_uses} max uses.", color=discord.Color.green())
                await ctx.respond(embed=embed, delete_after=5)

        elif action == "removecoupon":
            if code is None:
                embed = discord.Embed(title="Invalid Parameters", description="You must specify a coupon code.", color=discord.Color.red())
                return await ctx.respond(embed=embed, delete_after=5)
            async with aiosqlite.connect("./db/configs.db") as db:
                async with db.execute("SELECT * FROM coupons WHERE code = ?", (code,)) as cursor:
                    coupon = await cursor.fetchone()
                    if coupon is None:
                        embed = discord.Embed(title="Coupon Not Found", description=f"No coupon with code {code} exists.", color=discord.Color.red())
                        return await ctx.respond(embed=embed, delete_after=5)
                    await db.execute("DELETE FROM coupons WHERE code = ?", (code,))
                    await db.commit()
                    embed = discord.Embed(title="Coupon Removed", description=f"Removed coupon with code {code}.", color=discord.Color.green())
                    await ctx.respond(embed=embed, delete_after=5)

        elif action == "listcoupons":
            async with aiosqlite.connect("./db/configs.db") as db:
                async with db.execute("SELECT * FROM coupons") as cursor:
                    coupons = await cursor.fetchall()
                    if not coupons:
                        return await ctx.respond("No coupons found.")
                    response = "\n".join(
                        f"Code: **{coupon[1]}**, Coins: **{coupon[2]}**, Uses: **{coupon[3]}**" for coupon in coupons
                    )
                    embed = discord.Embed(title="Coupons", description=response, color=discord.Color.orange())
                    await ctx.respond(embed=embed, ephemeral=True)

        elif action == "help":
            embed = discord.Embed(
                title="Dev Commands Help",
                description="List of developer commands:",
                color=discord.Color.green()
            )
            embed.add_field(name="/dev addcoins <user> <amount>", value="Add coins to a user.", inline=False)
            embed.add_field(name="/dev removecoins <user> <amount>", value="Remove coins from a user.", inline=False)
            embed.add_field(name="/dev addcoupon <code> <coins> <max_uses>", value="Add a coupon.", inline=False)
            embed.add_field(name="/dev removecoupon <code>", value="Remove a coupon.", inline=False)
            embed.add_field(name="/dev listcoupons", value="List all coupons.", inline=False)
            embed.add_field(name="/dev help", value="Display this help message.", inline=False)
            await ctx.respond(embed=embed)

        else:
            await ctx.respond("Invalid action. Use /dev help for more information.", ephemeral=True)

def setup(bot):
    bot.add_cog(Dev(bot))
