import discord
from discord.ext import commands
import time

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="ping", description="Check the bot's latency.")
    async def ping(self, ctx: discord.ApplicationContext):
        start_time = time.monotonic()
        message = await ctx.respond("Pong! Calculating latency...")
        end_time = time.monotonic()
        
        round_trip_latency = (end_time - start_time) * 1000  # Convert to milliseconds
        api_latency = self.bot.latency * 1000  # Convert to milliseconds

        await message.edit_original_message(
            content=f"Pong! 🏓\n"
                    f"Round-trip latency: `{round_trip_latency:.2f} ms`\n"
                    f"API heartbeat latency: `{api_latency:.2f} ms`"
        )

def setup(bot):
    bot.add_cog(Ping(bot))
