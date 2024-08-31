import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID"))

class ChannelManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="purge", description="Delete a specified number of messages in the channel.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, message_count: int):
        await ctx.defer()

        if message_count <= 0:
            return await ctx.respond("Please provide a positive number of messages to delete.", ephemeral=True)

        try:
            deleted = await ctx.channel.purge(limit=message_count + 1)  # Including the command message itself
            embed = discord.Embed(
                title="Purge Successful",
                description=f"Deleted {len(deleted) - 1} messages in {ctx.channel.mention}.",  # Exclude the command message
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
            await ctx.respond(embed=embed, delete_after=5)
        except discord.Forbidden:
            await ctx.respond("I don't have permission to delete messages.", ephemeral=True)
        except discord.HTTPException as e:
            await ctx.respond(f"Failed to delete messages: {str(e)}", ephemeral=True)

    @commands.slash_command(name="lock", description="Lock the channel.")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        await ctx.defer()

        try:
            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
            embed = discord.Embed(
                title="Channel Locked",
                description=f"{ctx.channel.mention} has been locked.",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
            await ctx.respond(embed=embed)
        except discord.Forbidden:
            await ctx.respond("I don't have permission to lock the channel.", ephemeral=True)
        except discord.HTTPException as e:
            await ctx.respond(f"Failed to lock the channel: {str(e)}", ephemeral=True)

    @commands.slash_command(name="unlock", description="Unlock the channel.")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        await ctx.defer()

        try:
            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
            embed = discord.Embed(
                title="Channel Unlocked",
                description=f"{ctx.channel.mention} has been unlocked.",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
            await ctx.respond(embed=embed)
        except discord.Forbidden:
            await ctx.respond("I don't have permission to unlock the channel.", ephemeral=True)
        except discord.HTTPException as e:
            await ctx.respond(f"Failed to unlock the channel: {str(e)}", ephemeral=True)

    @commands.slash_command(name="nuke", description="Nukes the channel and recreates it with the same settings.")
    async def nuke(self, ctx):
        # Check if the user is the guild owner or bot owner
        if ctx.author.id != ctx.guild.owner_id and ctx.author.id != DEVELOPER_ID:
            return await ctx.respond("You do not have permission to use this command.", ephemeral=True)

        channel = ctx.channel
        channel_name = channel.name
        channel_category = channel.category
        channel_permissions = channel.overwrites
        channel_position = channel.position

        try:
            await channel.delete()
            new_channel = await ctx.guild.create_text_channel(
                name=channel_name,
                category=channel_category,
                overwrites=channel_permissions,
                position=channel_position
            )
            await new_channel.send(f"{new_channel.mention} has been nuked by {ctx.author.mention}.", delete_after=10)
        except discord.Forbidden:
            await ctx.respond("I don't have permission to nuke the channel.", ephemeral=True)
        except discord.HTTPException as e:
            await ctx.respond(f"Failed to nuke the channel: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(ChannelManagement(bot))
