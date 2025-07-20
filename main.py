import discord
from discord.ext import commands
from discord import app_commands
import os
from keep_alive import keep_alive

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ID del canale staff log (sostituisci con quello vero del tuo server)
LOG_CHANNEL_ID = 1271405128016072826

# Categorie ticket personalizzabili
TICKET_CATEGORIES = {
    "support": "🎫 Supporto",
    "purchase": "🛒 Acquisti"
}

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot online come {bot.user}")

@tree.command(name="setup", description="Crea il menu per i ticket")
async def setup(interaction: discord.Interaction):
    view = TicketButtons()
    embed = discord.Embed(
        title="📩 Apri un Ticket",
        description="Seleziona una categoria:",
        color=discord.Color.green()
    )
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Menu ticket creato!", ephemeral=True)

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for key, label in TICKET_CATEGORIES.items():
            self.add_item(TicketButton(label=label, custom_id=key))

class TicketButton(discord.ui.Button):
    def __init__(self, label, custom_id):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        category_name = self.custom_id
        channel_name = f"{category_name}-{interaction.user.name}".replace(" ", "-").lower()

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        category = discord.utils.get(guild.categories, name="TICKETS")
        if category is None:
            category = await guild.create_category("TICKETS")

        existing = discord.utils.get(category.text_channels, name=channel_name)
        if existing:
            await interaction.response.send_message("❌ Hai già un ticket aperto.", ephemeral=True)
            return

        channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)

        close_view = CloseTicketButton()
        await channel.send(f"{interaction.user.mention} ticket aperto!", view=close_view)

        # Log nel canale staff
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"📩 Ticket aperto: {channel.mention} da {interaction.user.mention}")

        await interaction.response.send_message(f"✅ Ticket creato: {channel.mention}", ephemeral=True)

class CloseTicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="🔒 Chiudi Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket"))

    @discord.ui.button(label="🔒 Chiudi Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"🔒 Ticket chiuso: {interaction.channel.name}")

# /close manuale
@tree.command(name="close", description="Chiude il ticket attuale")
async def close(interaction: discord.Interaction):
    if interaction.channel.category and interaction.channel.category.name == "TICKETS":
        await interaction.channel.delete()
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"🔒 Ticket chiuso manualmente: {interaction.channel.name}")
    else:
        await interaction.response.send_message("❌ Questo non è un canale ticket.", ephemeral=True)

# /transcript: invia DM all'utente con lo storico del ticket
@tree.command(name="transcript", description="Invia il contenuto del ticket all'utente")
async def transcript(interaction: discord.Interaction):
    if interaction.channel.category and interaction.channel.category.name == "TICKETS":
        messages = []
        async for msg in interaction.channel.history(limit=100, oldest_first=True):
            messages.append(f"[{msg.created_at.strftime('%H:%M')}] {msg.author.name}: {msg.content}")

        transcript_text = "\n".join(messages)
        if len(transcript_text) > 1900:
            transcript_text = transcript_text[:1900] + "\n...(troncato)"

        try:
            await interaction.user.send(f"📄 Transcript di `{interaction.channel.name}`:\n```{transcript_text}```")
            await interaction.response.send_message("✅ Transcript inviato in DM.", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Impossibile inviare DM.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Questo non è un ticket.", ephemeral=True)

# /message
@tree.command(name="message", description="Invia un messaggio in un canale tramite ID")
@app_commands.describe(
    canale="ID del canale",
    messaggio="Testo da inviare"
)
async def message(interaction: discord.Interaction, canale: str, messaggio: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Solo gli admin possono usare questo comando.", ephemeral=True)
        return

    try:
        channel = await bot.fetch_channel(int(canale))
        await channel.send(messaggio)
        await interaction.response.send_message(f"✅ Messaggio inviato in {channel.mention}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Errore: {str(e)}", ephemeral=True)

# Keep alive + avvio
keep_alive()
bot.run(os.getenv("TOKEN"))
