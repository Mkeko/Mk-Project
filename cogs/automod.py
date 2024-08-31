import discord
from discord.ext import commands
import aiosqlite

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "db/automod.db"
        self.bot.loop.create_task(self.create_tables())

    async def create_tables(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS automod_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    keyword TEXT NOT NULL
                )
            """)
            await db.commit()

    async def add_rule(self, guild_id, keyword):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO automod_rules (guild_id, keyword) VALUES (?, ?)",
                (guild_id, keyword)
            )
            await db.commit()

    async def remove_rule(self, guild_id, keyword):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM automod_rules WHERE guild_id = ? AND keyword = ?",
                (guild_id, keyword)
            )
            await db.commit()

    async def list_rules(self, guild_id):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT keyword FROM automod_rules WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    @discord.slash_command(name="automod", description="Manage auto-moderation rules.")
    @commands.has_permissions(administrator=True)
    async def automod(
        self,
        ctx,
        action: discord.Option(str, "Choose an action", choices=["add", "remove", "list", "help"]),
        keyword: discord.Option(str, "Keyword to add/remove", required=False)
    ):
        guild_id = str(ctx.guild.id)

        if action == "add" and keyword:
            await self.add_rule(guild_id, keyword)
            await ctx.respond(f"Rule added: {keyword}", ephemeral=True)
        
        elif action == "remove" and keyword:
            await self.remove_rule(guild_id, keyword)
            await ctx.respond(f"Rule removed: {keyword}", ephemeral=True)
        
        elif action == "list":
            rules = await self.list_rules(guild_id)
            if rules:
                response = "\n".join(rules)
                embed = discord.Embed(
                    title="Auto-Moderation Rules",
                    description=response,
                    color=discord.Color.blue()
                )
                await ctx.respond(embed=embed, ephemeral=True)
            else:
                await ctx.respond("No rules found.", ephemeral=True)
        
        elif action == "help":
            embed = discord.Embed(
                title="AutoMod Help",
                description="List of AutoMod commands:",
                color=discord.Color.green()
            )
            embed.add_field(name="/automod add <keyword>", value="Add a keyword to the auto-moderation list.", inline=False)
            embed.add_field(name="/automod remove <keyword>", value="Remove a keyword from the auto-moderation list.", inline=False)
            embed.add_field(name="/automod list", value="List all auto-moderation keywords.", inline=False)
            embed.add_field(name="/automod help", value="Display this help message.", inline=False)

            await ctx.respond(embed=embed, ephemeral=True)

        else:
            await ctx.respond("Invalid action. Use /automod help for more information.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guild_id = str(message.guild.id)
        rules = await self.list_rules(guild_id)
        for keyword in rules:
            if keyword.lower() in message.content.lower():
                await message.delete()
                await message.channel.send(f"Message from {message.author.mention} was removed due to prohibited content.")
                break

def setup(bot):
    bot.add_cog(AutoMod(bot))
