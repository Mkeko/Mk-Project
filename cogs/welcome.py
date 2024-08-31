import discord
from discord.ext import commands
import aiosqlite
import datetime
import random

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}  # Store invites to track who invited new members
        bot.loop.create_task(self.initialize_db())
        bot.loop.create_task(self.cache_invites())

    async def initialize_db(self):
        try:
            async with aiosqlite.connect("db/configs.db") as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS welcome_config (
                        guild_id INTEGER PRIMARY KEY,
                        channel_id INTEGER,
                        message TEXT,
                        color TEXT,
                        title TEXT
                    )
                """)
                await db.commit()
        except Exception as e:
            print(f"Failed to initialize the database: {e}")

    async def cache_invites(self):
        """Cache all invites when the bot starts."""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            self.invites[guild.id] = await guild.invites()

    async def get_welcome_config(self, guild_id):
        async with aiosqlite.connect("db/configs.db") as db:
            async with db.execute("""
                SELECT channel_id, message, color, title FROM welcome_config WHERE guild_id = ?
            """, (guild_id,)) as cursor:
                return await cursor.fetchone()

    async def set_welcome_config(self, guild_id, channel_id=None, message=None, color=None, title=None):
        async with aiosqlite.connect("db/configs.db") as db:
            await db.execute("""
                INSERT OR REPLACE INTO welcome_config (guild_id, channel_id, message, color, title)
                VALUES (
                    ?, 
                    COALESCE(?, (SELECT channel_id FROM welcome_config WHERE guild_id = ?)), 
                    COALESCE(?, (SELECT message FROM welcome_config WHERE guild_id = ?)), 
                    COALESCE(?, (SELECT color FROM welcome_config WHERE guild_id = ?)), 
                    COALESCE(?, (SELECT title FROM welcome_config WHERE guild_id = ?))
                )
            """, (guild_id, channel_id, guild_id, message, guild_id, color, guild_id, title, guild_id))
            await db.commit()

    async def delete_welcome_config(self, guild_id):
        async with aiosqlite.connect("db/configs.db") as db:
            await db.execute("""
                DELETE FROM welcome_config WHERE guild_id = ?
            """, (guild_id,))
            await db.commit()

    def create_embed(self, title, description, color):
        return discord.Embed(
            title=title,
            description=description,
            color=discord.Color(int(color.lstrip("#"), 16))
        )

    def validate_color(self, color):
        try:
            int(color.lstrip("#"), 16)
            return True
        except ValueError:
            return False

    welcome = discord.SlashCommandGroup(name="welcome", description="Manage welcome settings")

    @welcome.command(name="set", description="Set the welcome channel for the server")
    @commands.has_permissions(administrator=True)
    async def welcome_set(self, ctx, channel: discord.TextChannel):
        await self.set_welcome_config(ctx.guild.id, channel_id=channel.id)
        embed = self.create_embed(
            title="Welcome Channel Set",
            description=f"Welcome channel has been set to {channel.mention}.",
            color="#00FF00"
        )
        await ctx.respond(embed=embed)

    @welcome.command(name="disable", description="Disable the welcome system")
    @commands.has_permissions(administrator=True)
    async def welcome_disable(self, ctx):
        await self.delete_welcome_config(ctx.guild.id)
        embed = self.create_embed(
            title="Welcome System Disabled",
            description="The welcome system has been disabled.",
            color="#FF0000"
        )
        await ctx.respond(embed=embed)

    @welcome.command(name="customize", description="Customize the welcome message")
    @commands.has_permissions(administrator=True)
    async def welcome_customize(self, ctx, message: str = None, color: str = None, title: str = None):
        if color and not self.validate_color(color):
            await ctx.respond("Invalid color code! Please provide a valid HEX color code.", ephemeral=True)
            return

        await self.set_welcome_config(ctx.guild.id, message=message, color=color, title=title)
        
        embed = self.create_embed(
            title="Welcome Message Customized",
            description=(
                f"**Message:** {message or 'None (default will be used)'}\n"
                f"**Color:** {color or 'None (default will be used)'}\n"
                f"**Title:** {title or 'None (default will be used)'}"
            ),
            color="#0000FF"
        )
        await ctx.respond(embed=embed)

    @welcome.command(name="clear", description="Clear the welcome message, color, or title")
    @commands.has_permissions(administrator=True)
    async def welcome_clear(self, ctx, field: str):
        valid_fields = ["message", "color", "title"]
        if field.lower() not in valid_fields:
            await ctx.respond(f"Invalid field! Please choose from {', '.join(valid_fields)}.", ephemeral=True)
            return

        clear_values = {field: None}
        await self.set_welcome_config(ctx.guild.id, **clear_values)
        
        embed = self.create_embed(
            title="Welcome Configuration Cleared",
            description=f"The **{field}** field has been cleared.",
            color="#FFA500"
        )
        await ctx.respond(embed=embed)

    @welcome.command(name="help", description="Show information about welcome message variables")
    async def welcome_help(self, ctx):
        variables = {
            "%member%": "Member's display name if applicable. Otherwise defaults to Username#Discriminator",
            "%member_name%": "Member's username",
            "%member_discriminator%": "Member's discriminator",
            "%member_mention%": "Mention the member",
            "%member_id%": "Member's Discord ID",
            "%member_avatar%": "Member's Discord profile picture",
            "%member_created%": "When the member made their account",
            "%member_created_ago%": "How long ago the member made their account",
            "%member_joined%": "When the member joined the server",
            "%member_joined_ago%": "How long ago the member joined the server",
            "%member_join_count%": "How many times the member joined the server",
            "%member_leave_count%": "How many times the member left the server",
            "%inviter%": "Inviter's display name if applicable. Otherwise defaults to Username#Discriminator",
            "%inviter_name%": "Inviter's username",
            "%inviter_discriminator%": "Inviter's discriminator",
            "%inviter_mention%": "Inviter's mention",
            "%inviter_id%": "Inviter's Discord ID",
            "%inviter_avatar%": "Inviter's Discord profile picture",
            "%inviter_invites%": "Inviter's number of total invites",
            "%inviter_reg_invites%": "Inviter's number of regular invites",
            "%inviter_leave_invites%": "Inviter's number of leave invites",
            "%inviter_fake_invites%": "Inviter's number of fake invites",
            "%inviter_bonus_invites%": "Inviter's number of bonus invites",
            "%guild_name%": "Server's name",
            "%guild_avatar%": "Server's icon",
            "%guild_count%": "Number of members in the server",
            "%invite_code%": "The invite code the user used",
            "%invite_uses%": "The number of uses the invite code has",
            "%invite_url%": "The invite URL",
            "%random_color%": "Random color for embeds"
        }

        description = "\n".join([f"**{var}** - {desc}" for var, desc in variables.items()])
        
        embed = self.create_embed(
            title="Welcome Variables",
            description=description,
            color="#0000FF"
        )
        await ctx.respond(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = await self.get_welcome_config(member.guild.id)
        if config:
            channel_id, welcome_message, color, title = config
            channel = member.guild.get_channel(channel_id)
            if channel:
                # Track the inviter by comparing invite counts
                invites_before = self.invites.get(member.guild.id, [])
                invites_after = await member.guild.invites()
                
                invite_used = None
                inviter = None
                
                for invite in invites_before:
                    for new_invite in invites_after:
                        if invite.code == new_invite.code and invite.uses < new_invite.uses:
                            invite_used = new_invite
                            inviter = invite.inviter
                            break
                    if invite_used:
                        break

                self.invites[member.guild.id] = invites_after  # Update cached invites

                # Format the welcome message
                inviter_info = {
                    "inviter": inviter.display_name if inviter else "Unknown",
                    "inviter_name": inviter.name if inviter else "Unknown",
                    "inviter_discriminator": inviter.discriminator if inviter else "0000",
                    "inviter_mention": inviter.mention if inviter else "Unknown",
                    "inviter_id": inviter.id if inviter else "Unknown",
                    "inviter_avatar": inviter.avatar.url if inviter and inviter.avatar else "https://i.postimg.cc/fLQJvHRb/blank-profile-picture.png",
                    "inviter_invites": "N/A",  # You need to implement logic to get inviter's invites
                    "inviter_reg_invites": "N/A",
                    "inviter_leave_invites": "N/A",
                    "inviter_fake_invites": "N/A",
                    "inviter_bonus_invites": "N/A",
                    "member": member.display_name,
                    "member_name": member.name,
                    "member_discriminator": member.discriminator,
                    "member_mention": member.mention,
                    "member_id": member.id,
                    "member_avatar": member.avatar.url if member.avatar else "https://i.postimg.cc/fLQJvHRb/blank-profile-picture.png",
                    "member_created": member.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "member_created_ago": (datetime.datetime.utcnow() - member.created_at).days,
                    "member_joined": member.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "member_joined_ago": (datetime.datetime.utcnow() - member.joined_at).days,
                    "member_join_count": "N/A",
                    "member_leave_count": "N/A",
                    "inviter_bonus_invites": "N/A",
                    "guild_name": member.guild.name,
                    "guild_avatar": member.guild.icon.url if member.guild.icon else "https://i.postimg.cc/fLQJvHRb/blank-profile-picture.png",
                    "guild_count": member.guild.member_count,
                    "invite_code": invite_used.code if invite_used else "N/A",
                    "invite_uses": invite_used.uses if invite_used else "N/A",
                    "invite_url": f"https://discord.gg/{invite_used.code}" if invite_used else "N/A",
                    "random_color": "#{:06x}".format(random.randint(0, 0xFFFFFF))
                }

                # Replace variables in welcome message
                if welcome_message:
                    for key, value in inviter_info.items():
                        welcome_message = welcome_message.replace(f"%{key}%", str(value))

                    embed = self.create_embed(
                        title=title or "Welcome!",
                        description=welcome_message,
                        color=color or "#00FF00"
                    )
                    await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        pass  # Add handling if needed

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        self.invites[invite.guild.id] = await invite.guild.invites()

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        self.invites[invite.guild.id] = await invite.guild.invites()

def setup(bot):
    bot.add_cog(Welcome(bot))
