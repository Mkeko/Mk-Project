import discord
from discord.ext import commands, tasks
import aiosqlite
import datetime
import random

class GiveawayModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.add_item(discord.ui.InputText(label="Duration (e.g., 1s, 1m, 1h, 1d, 1w)", placeholder="1h"))
        self.add_item(discord.ui.InputText(label="Prize", placeholder="The prize of the giveaway"))
        self.add_item(discord.ui.InputText(label="Number of Winners", placeholder="1"))

    async def callback(self, interaction: discord.Interaction):
        try:
            duration_str = self.children[0].value
            prize = self.children[1].value
            num_winners = int(self.children[2].value)

            duration = self.parse_duration(duration_str)
            if not duration:
                await interaction.response.send_message(
                    "Invalid duration format. Use formats like 1s, 1m, 1h, 1d, 1w.", ephemeral=True
                )
                return

            end_time = int((datetime.datetime.utcnow() + duration).timestamp())
            embed = discord.Embed(
                title="Giveaway",
                description=f"Prize: **{prize}**\nReact with 🎉 to enter!\nEnds: <t:{end_time}:R>\nHosted by: {interaction.user.mention}",
                color=discord.Color.blue()
            )
            message = await interaction.channel.send(embed=embed)
            await message.add_reaction("🎉")

            await self.add_giveaway(interaction.guild_id, interaction.channel_id, message.id, prize, end_time, num_winners, interaction.user.id)
            await interaction.response.send_message("Giveaway started!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Invalid input. Ensure all fields are filled correctly.", ephemeral=True)

    async def add_giveaway(self, guild_id, channel_id, message_id, prize, end_time, num_winners, host_id):
        async with aiosqlite.connect("./db/giveaways.db") as db:
            await db.execute(f"""
                INSERT INTO giveaways_{guild_id} (channel_id, message_id, prize, end_time, num_winners, host_id, participants)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (channel_id, message_id, prize, end_time, num_winners, host_id, ""))
            await db.commit()

    def parse_duration(self, duration_str):
        unit = duration_str[-1]
        if unit not in "smhdw":
            return None

        try:
            value = int(duration_str[:-1])
        except ValueError:
            return None

        time_deltas = {
            "s": datetime.timedelta(seconds=value),
            "m": datetime.timedelta(minutes=value),
            "h": datetime.timedelta(hours=value),
            "d": datetime.timedelta(days=value),
            "w": datetime.timedelta(weeks=value)
        }

        return time_deltas.get(unit)

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_giveaways.start()
        self.bot.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        async with aiosqlite.connect("./db/giveaways.db") as db:
            for guild in self.bot.guilds:
                await db.execute(f"""
                    CREATE TABLE IF NOT EXISTS giveaways_{guild.id} (
                        channel_id INTEGER,
                        message_id INTEGER,
                        prize TEXT,
                        end_time INTEGER,
                        num_winners INTEGER,
                        host_id INTEGER,
                        participants TEXT
                    )
                """)
            await db.commit()

    async def ensure_guild_table(self, guild_id):
        async with aiosqlite.connect("./db/giveaways.db") as db:
            await db.execute(f"""
                CREATE TABLE IF NOT EXISTS giveaways_{guild_id} (
                    channel_id INTEGER,
                    message_id INTEGER,
                    prize TEXT,
                    end_time INTEGER,
                    num_winners INTEGER,
                    host_id INTEGER,
                    participants TEXT
                )
            """)
            await db.commit()

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        now = int(datetime.datetime.utcnow().timestamp())
        async with aiosqlite.connect("./db/giveaways.db") as db:
            for guild in self.bot.guilds:
                await self.ensure_guild_table(guild.id)
                async with db.execute(
                    f"SELECT channel_id, message_id, prize, num_winners, participants FROM giveaways_{guild.id} WHERE end_time <= ?", 
                    (now,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        channel_id, message_id, prize, num_winners, participants = row
                        channel = self.bot.get_channel(channel_id)
                        if not channel:
                            continue

                        try:
                            message = await channel.fetch_message(message_id)
                            participants = participants.split(',') if participants else []
                            participants = [p for p in participants if int(p) != self.bot.user.id]
                            if participants:
                                winners = random.sample(participants, min(num_winners, len(participants)))
                                winner_mentions = [self.bot.get_guild(guild.id).get_member(int(winner)).mention for winner in winners]
                                await channel.send(f"Congratulations {', '.join(winner_mentions)}! You won the giveaway for **{prize}**! 🎉")
                            else:
                                await channel.send("No participants for the giveaway. 😔")
                            await message.delete()
                        except discord.NotFound:
                            pass
                        await db.execute(f"DELETE FROM giveaways_{guild.id} WHERE message_id = ?", (message_id,))
                await db.commit()

    async def add_participant(self, guild_id, message_id, user_id):
        if user_id == self.bot.user.id:
            return

        async with aiosqlite.connect("./db/giveaways.db") as db:
            await self.ensure_guild_table(guild_id)
            async with db.execute(f"SELECT participants FROM giveaways_{guild_id} WHERE message_id = ?", (message_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    participants = row[0].split(',') if row[0] else []
                    if str(user_id) not in participants:
                        participants.append(str(user_id))
                        await db.execute(f"UPDATE giveaways_{guild_id} SET participants = ? WHERE message_id = ?", (','.join(participants), message_id))
                        await db.commit()

    giveaway = discord.SlashCommandGroup(name="giveaway", description="Manage giveaways")

    @giveaway.command(name="setup", description="Setup a new giveaway")
    @commands.has_permissions(administrator=True)
    async def giveaway_setup(self, ctx):
        await self.ensure_guild_table(ctx.guild.id)
        modal = GiveawayModal(self.bot, title="Giveaway Setup")
        await ctx.send_modal(modal)

    @giveaway.command(name="end", description="End an active giveaway")
    @commands.has_permissions(administrator=True)
    async def giveaway_end(self, ctx, message_id: discord.Option(str, description="The ID of the giveaway message")):
        try:
            message_id = int(message_id)
            async with aiosqlite.connect("./db/giveaways.db") as db:
                await self.ensure_guild_table(ctx.guild.id)
                await db.execute(f"UPDATE giveaways_{ctx.guild.id} SET end_time = ? WHERE message_id = ?", (int(datetime.datetime.utcnow().timestamp()), message_id))
                await db.commit()
            await ctx.respond("The giveaway will end shortly.", ephemeral=True)
        except ValueError:
            await ctx.respond("Invalid message ID. Provide a valid integer.", ephemeral=True)

    @giveaway.command(name="list", description="List all active giveaways")
    async def giveaway_list(self, ctx):
        async with aiosqlite.connect("./db/giveaways.db") as db:
            await self.ensure_guild_table(ctx.guild.id)
            async with db.execute(f"SELECT channel_id, message_id, prize, end_time FROM giveaways_{ctx.guild.id}") as cursor:
                rows = await cursor.fetchall()
                if not rows:
                    return await ctx.respond("No active giveaways at the moment.", ephemeral=True)

                embed = discord.Embed(title="Active Giveaways", color=discord.Color.blue())
                for row in rows:
                    channel_id, message_id, prize, end_time = row
                    end_time_str = datetime.datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S UTC')
                    embed.add_field(name=f"Giveaway in <#{channel_id}>", value=f"Prize: **{prize}**\nEnds: {end_time_str}\n[Message Link](https://discord.com/channels/{ctx.guild.id}/{channel_id}/{message_id})", inline=False)
                await ctx.respond(embed=embed, ephemeral=True)

    @giveaway.command(name="reroll", description="Reroll the winners of a giveaway")
    @commands.has_permissions(administrator=True)
    async def giveaway_reroll(self, ctx, message_id: discord.Option(str, description="The ID of the giveaway message")):
        try:
            message_id = int(message_id)
            async with aiosqlite.connect("./db/giveaways.db") as db:
                await self.ensure_guild_table(ctx.guild.id)
                async with db.execute(f"SELECT participants, prize, num_winners FROM giveaways_{ctx.guild.id} WHERE message_id = ?", (message_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        participants, prize, num_winners = row
                        participants = participants.split(',') if participants else []
                        participants = [p for p in participants if int(p) != self.bot.user.id]
                        if participants:
                            winners = random.sample(participants, min(num_winners, len(participants)))
                            winner_mentions = [ctx.guild.get_member(int(winner)).mention for winner in winners]
                            await ctx.respond(f"Congratulations {', '.join(winner_mentions)}! You won the giveaway for **{prize}**! 🎉", ephemeral=True)
                        else:
                            await ctx.respond("No participants for the giveaway. 😔", ephemeral=True)
                    else:
                        await ctx.respond("No giveaway found with that message ID.", ephemeral=True)
        except ValueError:
            await ctx.respond("Invalid message ID. Provide a valid integer.", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.emoji.name == "🎉" and not payload.user_id == self.bot.user.id:
            await self.add_participant(payload.guild_id, payload.message_id, payload.user_id)

def setup(bot):
    bot.add_cog(Giveaway(bot))
