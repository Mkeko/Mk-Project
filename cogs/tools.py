import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

class Tools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_link = os.getenv("BOT_INVITE_LINK", "https://discord.com/oauth2/authorize?client_id=00000000000000")  # Default link if not set

    @commands.slash_command(name="membercount", description="Displays the member count of the server.")
    async def membercount(self, ctx):
        await ctx.defer()
        try:
            members = ctx.guild.member_count
            description = f"This server has **{members}** members."
            embed = discord.Embed(title="Member Count", description=description, color=discord.Color.blue())
            embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png")
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png")
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"An error occurred while fetching the member count: {e}")

    @commands.slash_command(name="invite", description="Get the bot's invite link.")
    async def invite(self, ctx):
        await ctx.defer()
        try:
            description = f"Invite the bot using [this link]({self.invite_link})."
            embed = discord.Embed(title="Bot Invite", description=description, color=discord.Color.green())
            embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png")
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else "https://i.postimg.cc/fLQ8T6F6/NO-USER.png")
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"An error occurred while generating the invite link: {e}")

def setup(bot):
    bot.add_cog(Tools(bot))
