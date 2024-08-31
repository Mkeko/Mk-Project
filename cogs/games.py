import discord
from discord.ext import commands
import aiosqlite
import random
import asyncio

class Economy:
    @staticmethod
    async def add_coins(user_id: int, coins: int):
        async with aiosqlite.connect("./db/economy.db") as db:
            await db.execute(
                "UPDATE users SET coins = coins + ? WHERE id = ?",
                (coins, user_id)
            )
            await db.commit()

    @staticmethod
    async def remove_coins(user_id: int, coins: int):
        async with aiosqlite.connect("./db/economy.db") as db:
            await db.execute(
                "UPDATE users SET coins = coins - ? WHERE id = ?",
                (coins, user_id)
            )
            await db.commit()

    @staticmethod
    async def get_coins(user_id: int):
        async with aiosqlite.connect("./db/economy.db") as db:
            async with db.execute(
                "SELECT coins FROM users WHERE id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    games = discord.SlashCommandGroup(name="games", description="Various gambling games")

    @games.command(name="gamble", description="Gamble your coins")
    async def gamble(self, ctx, coins: int):
        if coins <= 0:
            await ctx.respond("You can't gamble 0 coins or negative coins.", ephemeral=True)
            return
        user_coins = await Economy.get_coins(ctx.author.id)
        if user_coins < coins:
            await ctx.respond("You don't have enough coins to gamble.", ephemeral=True)
            return

        result = random.randint(0, 5)
        result_2 = random.randint(0, 5)

        embed = discord.Embed(color=discord.Color.blurple())
        if result == result_2:
            await Economy.add_coins(ctx.author.id, coins)
            embed.add_field(name="🎉 You won!", value=f"You won {coins} coins", inline=False)
        else:
            await Economy.remove_coins(ctx.author.id, coins)
            embed.add_field(name="💔 You lost!", value=f"You lost {coins} coins", inline=False)
        embed.set_footer(text=f"Result: {result} and {result_2}")

        await ctx.respond(embed=embed)

    @games.command(name="slots", description="Play the slots game")
    async def slots(self, ctx, coins: int):
        if coins <= 0:
            await ctx.respond("You can't gamble 0 coins or negative coins.", ephemeral=True)
            return
        user_coins = await Economy.get_coins(ctx.author.id)
        if user_coins < coins:
            await ctx.respond("You don't have enough coins to gamble.", ephemeral=True)
            return

        result1 = random.randint(0, 9)
        result2 = random.randint(0, 9)
        result3 = random.randint(0, 9)
        emojis = ["🍎", "🍌", "🍌", "🍒", "🍇", "🍓", "🍓", "🥭", "🍐", "🍋"]
        slot1 = emojis[result1]
        slot2 = emojis[result2]
        slot3 = emojis[result3]
        always_win = ["00000000000000000", "0000000000000000"]
        if str(ctx.author.id) in always_win:
            slot1 = slot2 = slot3 = "💎"

        await ctx.defer()
        await asyncio.sleep(1)
        embed = discord.Embed(color=discord.Color.blurple())
        if slot1 == slot2 == slot3:
            await Economy.add_coins(ctx.author.id, coins * 10)
            embed.add_field(name="🎉 You won!", value=f"You won {coins * 10} coins! Your balance is: **{await Economy.get_coins(ctx.author.id)}**", inline=False)
        else:
            embed.add_field(name="💔 You lost!", value=f"You lost {coins} coins! Your balance is: **{await Economy.get_coins(ctx.author.id)}**", inline=False)
            await Economy.remove_coins(ctx.author.id, coins)
        embed.set_footer(text=f"Result: {slot1} {slot2} {slot3}")

        await ctx.respond(embed=embed)

    @games.command(name="coinflip", description="Flip a coin")
    async def coinflip(self, ctx, coins: int, choice: str):
        if coins <= 0:
            await ctx.respond("You can't gamble 0 coins or negative coins.", ephemeral=True)
            return
        if choice.lower() not in ["heads", "tails"]:
            await ctx.respond("Invalid choice. Choose heads or tails.", ephemeral=True)
            return
        user_coins = await Economy.get_coins(ctx.author.id)
        if user_coins < coins:
            await ctx.respond("You don't have enough coins to gamble.", ephemeral=True)
            return

        result = random.choice(["heads", "tails"])
        if coins < 5:
            await ctx.respond("Minimum coins is 5.", ephemeral=True)
            return
        coinsa = round(coins // 4)

        await ctx.defer()
        await asyncio.sleep(2)
        embed = discord.Embed(color=discord.Color.blurple())
        if choice.lower() == result:
            await Economy.add_coins(ctx.author.id, coinsa)
            balance = await Economy.get_coins(ctx.author.id)
            embed.add_field(name="🎉 You won!", value=f"You won {coinsa} coins! Your balance is: **{balance}**", inline=False)
        else:
            await Economy.remove_coins(ctx.author.id, coins)
            balance = await Economy.get_coins(ctx.author.id)
            embed.add_field(name="💔 You lost!", value=f"You lost {coins} coins! Your balance is: **{balance}**", inline=False)
        embed.set_footer(text=f"Result: {result}")

        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Games(bot))