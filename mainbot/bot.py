import discord
from discord.ext import commands
from discord import app_commands
import json, os, asyncio, uuid, random
from datetime import datetime, timedelta

# ── Token ─────────────────────────────────────────────────────────────────────
TOKEN = None
try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DISCORD_TOKEN="):
                TOKEN = line.split("=", 1)[1].strip()
                break
except:
    pass
if not TOKEN:
    TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    print("❌ Kein Token gefunden!")
    exit(1)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE   = os.path.join(BASE, "config.json")
COMMANDS_FILE = os.path.join(BASE, "custom_commands.json")
CODES_FILE    = os.path.join(BASE, "codes.json")
TICKETS_FILE  = os.path.join(BASE, "tickets.json")
WARNS_FILE    = os.path.join(BASE, "warns.json")

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {} if path in (CONFIG_FILE, COMMANDS_FILE, WARNS_FILE) else []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def gcfg(guild_id):
    return load_json(CONFIG_FILE).get(str(guild_id), {})

def scfg(guild_id, key, value):
    cfg = load_json(CONFIG_FILE)
    cfg.setdefault(str(guild_id), {})[key] = value
    save_json(CONFIG_FILE, cfg)

def ts():
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")

def get_log_channel(guild):
    cid = gcfg(guild.id).get("log_channel")
    return guild.get_channel(int(cid)) if cid else None

def generate_id(typ):
    short = str(uuid.uuid4())[:8].upper()
    return {"kauf": "ORDER", "support": "SUPPORT", "bewerbung": "APPLY", "report": "REPORT", "partner": "PARTNER"}.get(typ, "TICKET") + f"-{short}"

# ════════════════════════════════════════════════════════════
# EMBED SYSTEM
# ════════════════════════════════════════════════════════════

class EmbedModal(discord.ui.Modal, title="Embed erstellen"):
    embed_title       = discord.ui.TextInput(label="Titel", max_length=256)
    embed_description = discord.ui.TextInput(label="Beschreibung", style=discord.TextStyle.paragraph, max_length=4000)
    embed_color       = discord.ui.TextInput(label="Farbe (Hex z.B. #ff0000)", placeholder="#5865F2", required=False, max_length=7)
    embed_footer      = discord.ui.TextInput(label="Footer (optional)", required=False, max_length=256)
    embed_image       = discord.ui.TextInput(label="Bild URL (optional)", required=False, max_length=500)

    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        try:
            color = discord.Color(0x1a3fdb)
        except:
            color = discord.Color(0x1a3fdb)
        embed = discord.Embed(title=self.embed_title.value, description=self.embed_description.value, color=color)
        if self.embed_footer.value:
            embed.set_footer(text=self.embed_footer.value)
        if self.embed_image.value:
            embed.set_image(url=self.embed_image.value)
        await self.channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Embed in {self.channel.mention} gesendet!", ephemeral=True)

class ChannelSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Channel auswählen...", channel_types=[discord.ChannelType.text])
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        # Echten Channel holen
        real_channel = interaction.guild.get_channel(channel.id)
        await interaction.response.send_modal(EmbedModal(channel=real_channel))

@bot.tree.command(name="embed", description="Embed erstellen und senden")
@app_commands.checks.has_permissions(manage_messages=True)
async def embed_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("📋 Channel auswählen:", view=ChannelSelectView(), ephemeral=True)

# ════════════════════════════════════════════════════════════
# CUSTOM COMMANDS
# ════════════════════════════════════════════════════════════

class AddCommandModal(discord.ui.Modal, title="Command erstellen"):
    cmd_name      = discord.ui.TextInput(label="Command Name (ohne /)", max_length=32)
    cmd_response  = discord.ui.TextInput(label="Antwort", style=discord.TextStyle.paragraph, max_length=2000)
    cmd_embed     = discord.ui.TextInput(label="Als Embed? (ja/nein)", placeholder="nein", required=False, max_length=4)
    cmd_color     = discord.ui.TextInput(label="Embed Farbe (optional)", placeholder="#5865F2", required=False, max_length=7)
    cmd_ephemeral = discord.ui.TextInput(label="Nur für dich sichtbar? (ja/nein)", placeholder="nein", required=False, max_length=4)

    async def on_submit(self, interaction: discord.Interaction):
        name = self.cmd_name.value.lower().strip().replace(" ", "_")
        as_embed = self.cmd_embed.value.lower().strip() in ("ja", "j", "yes", "y")
        ephemeral = self.cmd_ephemeral.value.lower().strip() in ("ja", "j", "yes", "y")
        try:
            color = int(self.cmd_color.value.strip().replace("#", ""), 16)
        except:
            color = 0x5865F2
        cmds = load_json(COMMANDS_FILE)
        cmds[name] = {"response": self.cmd_response.value, "embed": as_embed, "color": color, "ephemeral": ephemeral}
        save_json(COMMANDS_FILE, cmds)
        await interaction.response.send_message(f"✅ Command `/{name}` erstellt!", ephemeral=True)

@bot.tree.command(name="addcommand", description="Eigenen Command erstellen")
@app_commands.checks.has_permissions(manage_guild=True)
async def addcommand_cmd(interaction: discord.Interaction):
    await interaction.response.send_modal(AddCommandModal())

@bot.tree.command(name="deletecommand", description="Eigenen Command löschen")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(name="Command Name")
async def deletecommand_cmd(interaction: discord.Interaction, name: str):
    cmds = load_json(COMMANDS_FILE)
    if name in cmds:
        del cmds[name]
        save_json(COMMANDS_FILE, cmds)
        await interaction.response.send_message(f"🗑️ `/{name}` gelöscht!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ `/{name}` nicht gefunden.", ephemeral=True)

@bot.tree.command(name="listcommands", description="Alle eigenen Commands anzeigen")
async def listcommands_cmd(interaction: discord.Interaction):
    cmds = load_json(COMMANDS_FILE)
    if not cmds:
        await interaction.response.send_message("📭 Keine Commands vorhanden.", ephemeral=True)
        return
    embed = discord.Embed(title="📋 Eigene Commands", color=0x1a3fdb)
    for name, data in cmds.items():
        embed.add_field(name=f"/{name}", value=f"Embed: {'✅' if data['embed'] else '❌'}", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        name = interaction.data.get("name", "")
        cmds = load_json(COMMANDS_FILE)
        if name in cmds:
            cmd = cmds[name]
            if cmd["embed"]:
                embed = discord.Embed(description=cmd["response"], color=cmd["color"])
                await interaction.response.send_message(embed=embed, ephemeral=cmd["ephemeral"])
            else:
                await interaction.response.send_message(cmd["response"], ephemeral=cmd["ephemeral"])

# ════════════════════════════════════════════════════════════
# PSC CODE SYSTEM
# ════════════════════════════════════════════════════════════

@bot.tree.command(name="psc", description="Code einreichen")
@app_commands.describe(code="Dein Code")
async def psc_cmd(interaction: discord.Interaction, code: str):
    codes = load_json(CODES_FILE)
    codes.append({"code": code, "user": str(interaction.user), "user_id": interaction.user.id, "datum": ts()})
    save_json(CODES_FILE, codes)
    await interaction.response.send_message("✅ Code wurde eingereicht!", ephemeral=True)

# ════════════════════════════════════════════════════════════
# CLEAR
# ════════════════════════════════════════════════════════════

@bot.tree.command(name="clear", description="Chat leeren")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(menge="Anzahl Nachrichten (Standard: alle)")
async def clear_cmd(interaction: discord.Interaction, menge: int = 0):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=menge if menge > 0 else None)
    await interaction.followup.send(f"🗑️ {len(deleted)} Nachrichten gelöscht!", ephemeral=True)

# ════════════════════════════════════════════════════════════
# TICKET SYSTEM
# ════════════════════════════════════════════════════════════

TICKET_CATEGORIES = {
    "kauf": "Bestellungen", "support": "Support",
    "bewerbung": "Bewerbungen", "report": "Meldungen", "partner": "Partnerschaften"
}

async def get_or_create_category(guild, typ, support_role):
    name = TICKET_CATEGORIES.get(typ, "Tickets")
    for cat in guild.categories:
        if cat.name == name:
            return cat
    overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
    if support_role:
        overwrites[support_role] = discord.PermissionOverwrite(view_channel=True)
    return await guild.create_category(name=name, overwrites=overwrites)

async def save_transcript(channel, ticket_id, typ, user, details):
    messages = []
    async for msg in channel.history(limit=500, oldest_first=True):
        if msg.author.bot and not msg.embeds:
            continue
        messages.append({
            "author": str(msg.author), "content": msg.content,
            "time": msg.created_at.strftime("%d.%m.%Y %H:%M"),
            "embeds": [{"title": e.title or "", "fields": [{"name": f.name, "value": f.value} for f in e.fields]} for e in msg.embeds]
        })
    tickets = load_json(TICKETS_FILE)
    tickets.append({"id": ticket_id, "typ": typ, "user": str(user), "user_id": str(user.id),
                    "details": details, "erstellt": ts(), "verlauf": messages})
    save_json(TICKETS_FILE, tickets)

class KaufModal(discord.ui.Modal, title="Neue Bestellung"):
    produkt = discord.ui.TextInput(label="Produkt", placeholder="z.B. Premium — 1 Monat")
    betrag  = discord.ui.TextInput(label="Betrag", placeholder="z.B. €24.00")
    zahlung = discord.ui.TextInput(label="Zahlungsart", placeholder="z.B. PayPal F&F")
    note    = discord.ui.TextInput(label="Note (optional)", required=False)
    async def on_submit(self, interaction): await create_ticket(interaction, "kauf", self)

class SupportModal(discord.ui.Modal, title="Support Anfrage"):
    betreff      = discord.ui.TextInput(label="Betreff")
    beschreibung = discord.ui.TextInput(label="Beschreibung", style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction): await create_ticket(interaction, "support", self)

class BewerbungModal(discord.ui.Modal, title="Team Bewerbung"):
    alter      = discord.ui.TextInput(label="Alter")
    erfahrung  = discord.ui.TextInput(label="Erfahrung", style=discord.TextStyle.paragraph)
    warum      = discord.ui.TextInput(label="Warum willst du ins Team?", style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction): await create_ticket(interaction, "bewerbung", self)

class ReportModal(discord.ui.Modal, title="Meldung"):
    beschuldigter = discord.ui.TextInput(label="Beschuldigter (Name/ID)")
    grund         = discord.ui.TextInput(label="Grund", style=discord.TextStyle.paragraph)
    beweis        = discord.ui.TextInput(label="Beweis (Link optional)", required=False)
    async def on_submit(self, interaction): await create_ticket(interaction, "report", self)

class PartnerModal(discord.ui.Modal, title="Partnerschaft"):
    server_name  = discord.ui.TextInput(label="Server Name")
    member_count = discord.ui.TextInput(label="Mitglieder Anzahl")
    invite       = discord.ui.TextInput(label="Einladungslink")
    async def on_submit(self, interaction): await create_ticket(interaction, "partner", self)

async def create_ticket(interaction: discord.Interaction, typ: str, modal):
    cfg = gcfg(interaction.guild.id)
    support_role = interaction.guild.get_role(int(cfg["support_role"])) if cfg.get("support_role") else None
    category = await get_or_create_category(interaction.guild, typ, support_role)
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }
    if support_role:
        overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    channel = await interaction.guild.create_text_channel(
        name=f"{typ}-{interaction.user.name}".lower().replace(" ", "-")[:100],
        category=category, overwrites=overwrites
    )
    tid = generate_id(typ)
    details = {}

    if typ == "kauf":
        details = {"produkt": modal.produkt.value, "betrag": modal.betrag.value, "zahlung": modal.zahlung.value, "note": modal.note.value}
        embed = discord.Embed(title="Eingehende Bestellung", color=0x1a3fdb)
        embed.add_field(name="Artikel", value=f"> {modal.produkt.value}", inline=False)
        embed.add_field(name="Preis", value=f"> {modal.betrag.value}", inline=True)
        embed.add_field(name="Zahlung via", value=f"> {modal.zahlung.value}", inline=True)
        embed.add_field(name="Käufer", value=f"> {interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="Bestellnummer", value=f"```{tid}```", inline=False)
        if modal.note.value:
            embed.add_field(name="Anmerkung", value=f"> {modal.note.value}", inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Erstellt am {ts()}")
        view = KaufTicketView(tid, typ, interaction.user)
    elif typ == "support":
        details = {"betreff": modal.betreff.value, "beschreibung": modal.beschreibung.value}
        embed = discord.Embed(title="Support Anfrage", color=0x1a3fdb)
        embed.add_field(name="Thema", value=f"> {modal.betreff.value}", inline=False)
        embed.add_field(name="Beschreibung", value=f"> {modal.beschreibung.value}", inline=False)
        embed.add_field(name="Support-ID", value=f"```{tid}```", inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Erstellt am {ts()}")
        view = CloseTicketView(tid, typ, interaction.user)
    elif typ == "bewerbung":
        details = {"alter": modal.alter.value, "erfahrung": modal.erfahrung.value, "warum": modal.warum.value}
        embed = discord.Embed(title="Team Bewerbung", color=0x1a3fdb)
        embed.add_field(name="Alter", value=f"> {modal.alter.value}", inline=True)
        embed.add_field(name="Erfahrung", value=f"> {modal.erfahrung.value}", inline=False)
        embed.add_field(name="Motivation", value=f"> {modal.warum.value}", inline=False)
        embed.add_field(name="Bewerbungs-ID", value=f"```{tid}```", inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Erstellt am {ts()}")
        view = CloseTicketView(tid, typ, interaction.user)
    elif typ == "report":
        details = {"beschuldigter": modal.beschuldigter.value, "grund": modal.grund.value, "beweis": modal.beweis.value}
        embed = discord.Embed(title="Meldung eingegangen", color=0x1a3fdb)
        embed.add_field(name="Gemeldet", value=f"> {modal.beschuldigter.value}", inline=False)
        embed.add_field(name="Grund", value=f"> {modal.grund.value}", inline=False)
        if modal.beweis.value:
            embed.add_field(name="Beweis", value=f"> {modal.beweis.value}", inline=False)
        embed.add_field(name="Report-ID", value=f"```{tid}```", inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Erstellt am {ts()}")
        view = CloseTicketView(tid, typ, interaction.user)
    elif typ == "partner":
        details = {"server": modal.server_name.value, "mitglieder": modal.member_count.value, "invite": modal.invite.value}
        embed = discord.Embed(title="Partnerschaftsanfrage", color=0x1a3fdb)
        embed.add_field(name="Server", value=f"> {modal.server_name.value}", inline=True)
        embed.add_field(name="Mitglieder", value=f"> {modal.member_count.value}", inline=True)
        embed.add_field(name="Einladung", value=f"> {modal.invite.value}", inline=False)
        embed.add_field(name="Partner-ID", value=f"```{tid}```", inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Erstellt am {ts()}")
        view = CloseTicketView(tid, typ, interaction.user)

    mention = support_role.mention if support_role else ""
    await channel.send(content=f"{interaction.user.mention} {mention}", embed=embed, view=view)
    await interaction.response.send_message(f"✅ Ticket erstellt: {channel.mention}", ephemeral=True)

    # Log
    lch = get_log_channel(interaction.guild)
    if lch:
        lembed = discord.Embed(title="Ticket geöffnet", color=0x1a3fdb)
        lembed.add_field(name="Typ", value=typ.capitalize(), inline=True)
        lembed.add_field(name="Nutzer", value=interaction.user.mention, inline=True)
        lembed.add_field(name="Channel", value=channel.mention, inline=True)
        lembed.set_footer(text=ts())
        await lch.send(embed=lembed)

class KaufTicketView(discord.ui.View):
    def __init__(self, ticket_id=None, typ=None, user=None):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id; self.typ = typ; self.user = user

    @discord.ui.button(label="Bestätigen", style=discord.ButtonStyle.success, custom_id="confirm_purchase")
    async def confirm(self, interaction, button):
        await interaction.response.send_message("✅ Bestellung wurde bestätigt.")
        button.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="In Bearbeitung", style=discord.ButtonStyle.primary, custom_id="in_progress")
    async def in_progress(self, interaction, button):
        await interaction.response.send_message("🔄 Wird gerade bearbeitet...")

    @discord.ui.button(label="Ablehnen", style=discord.ButtonStyle.danger, custom_id="decline_purchase")
    async def decline(self, interaction, button):
        await interaction.response.send_message("❌ **Bestellung abgelehnt.** Channel wird in **10 Sekunden** geschlossen.")
        if self.ticket_id and self.user:
            await save_transcript(interaction.channel, self.ticket_id, self.typ or "kauf", self.user, {})
        await asyncio.sleep(10)
        await interaction.channel.delete()

class CloseTicketView(discord.ui.View):
    def __init__(self, ticket_id=None, typ=None, user=None):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id; self.typ = typ; self.user = user

    @discord.ui.button(label="Ticket schließen", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close(self, interaction, button):
        await interaction.response.send_message("🔒 Ticket wird in **10 Sekunden** geschlossen...")
        if self.ticket_id and self.user:
            await save_transcript(interaction.channel, self.ticket_id, self.typ or "support", self.user, {})
        await asyncio.sleep(10)
        await interaction.channel.delete()

class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Bestellung aufgeben",  description="Produkt kaufen",            emoji="🛍️", value="kauf"),
            discord.SelectOption(label="Hilfe benötigt",       description="Support kontaktieren",      emoji="🔧", value="support"),
            discord.SelectOption(label="Team beitreten",       description="Bewerbung einreichen",      emoji="📨", value="bewerbung"),
            discord.SelectOption(label="User melden",          description="Jemanden beim Team melden", emoji="⚠️", value="report"),
            discord.SelectOption(label="Kooperation anfragen", description="Partnerschaft vorschlagen", emoji="🤝", value="partner"),
        ]
        super().__init__(placeholder="Wähle eine Kategorie...", min_values=1, max_values=1, options=options, custom_id="ticket_dropdown")

    async def callback(self, interaction):
        modals = {"kauf": KaufModal, "support": SupportModal, "bewerbung": BewerbungModal, "report": ReportModal, "partner": PartnerModal}
        await interaction.response.send_modal(modals[self.values[0]]())

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

@bot.tree.command(name="ticketpanel", description="Ticket Panel senden")
@app_commands.checks.has_permissions(administrator=True)
async def ticketpanel_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="Ticket Support", description="Wähle unten die passende Kategorie für dein Anliegen.\n\n**Bitte sei so genau wie möglich** damit wir dir schnell helfen können.", color=0x1a3fdb)
    embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(text=f"Für weitere Optionen nach unten scrollen  •  {datetime.now().strftime('%d.%m.%Y')}")
    await interaction.channel.send(embed=embed, view=TicketPanelView())
    await interaction.response.send_message("✅ Panel gesendet!", ephemeral=True)

@bot.tree.command(name="setsupportrole", description="Support-Rolle einstellen")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(rolle="Die Rolle die alle Tickets sehen kann")
async def setsupportrole_cmd(interaction: discord.Interaction, rolle: discord.Role):
    scfg(interaction.guild.id, "support_role", str(rolle.id))
    await interaction.response.send_message(f"✅ Support-Rolle: {rolle.mention}", ephemeral=True)

# ════════════════════════════════════════════════════════════
# LOG SYSTEM
# ════════════════════════════════════════════════════════════

@bot.tree.command(name="setlogchannel", description="Log-Channel einstellen")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="Der Channel für Logs")
async def setlogchannel_cmd(interaction: discord.Interaction, channel: discord.TextChannel):
    scfg(interaction.guild.id, "log_channel", str(channel.id))
    await interaction.response.send_message(f"✅ Log-Channel: {channel.mention}", ephemeral=True)

@bot.event
async def on_member_join(member):
    ch = get_log_channel(member.guild)

    # Unverified Rolle geben
    cfg = gcfg(member.guild.id)
    unverified_role_id = cfg.get("unverified_role")
    if unverified_role_id:
        unverified_role = member.guild.get_role(int(unverified_role_id))
        if unverified_role:
            await member.add_roles(unverified_role)

    if not ch: return
    embed = discord.Embed(title="Mitglied beigetreten", color=0x1a3fdb)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Nutzer", value=f"{member.mention} (`{member.id}`)", inline=False)
    embed.add_field(name="Account erstellt", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
    embed.set_footer(text=ts())
    await ch.send(embed=embed)

@bot.event
async def on_member_remove(member):
    ch = get_log_channel(member.guild)
    if not ch: return
    embed = discord.Embed(title="Mitglied verlassen", color=0x1a3fdb)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Nutzer", value=f"{member} (`{member.id}`)", inline=False)
    embed.add_field(name="Rollen", value=" ".join([r.mention for r in member.roles[1:]]) or "Keine", inline=False)
    embed.set_footer(text=ts())
    await ch.send(embed=embed)

@bot.event
async def on_member_ban(guild, user):
    ch = get_log_channel(guild)
    if not ch: return
    grund = "Kein Grund angegeben"; mod = "Unbekannt"
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        if entry.target.id == user.id:
            grund = entry.reason or "Kein Grund angegeben"; mod = str(entry.user); break
    embed = discord.Embed(title="Mitglied gebannt", color=0x1a3fdb)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Nutzer", value=f"{user} (`{user.id}`)", inline=False)
    embed.add_field(name="Moderator", value=mod, inline=True)
    embed.add_field(name="Grund", value=grund, inline=True)
    embed.set_footer(text=ts())
    await ch.send(embed=embed)

@bot.event
async def on_member_unban(guild, user):
    ch = get_log_channel(guild)
    if not ch: return
    embed = discord.Embed(title="Mitglied entbannt", color=0x1a3fdb)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Nutzer", value=f"{user} (`{user.id}`)", inline=False)
    embed.set_footer(text=ts())
    await ch.send(embed=embed)

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    ch = get_log_channel(message.guild)
    if not ch: return
    embed = discord.Embed(title="Nachricht gelöscht", color=0x1a3fdb)
    embed.add_field(name="Nutzer", value=message.author.mention, inline=True)
    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    embed.add_field(name="Inhalt", value=message.content or "*kein Text*", inline=False)
    embed.set_footer(text=ts())
    await ch.send(embed=embed)

# ════════════════════════════════════════════════════════════
# WARN SYSTEM
# ════════════════════════════════════════════════════════════

@bot.tree.command(name="warn", description="Nutzer verwarnen")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(nutzer="Der Nutzer", grund="Grund der Verwarnung")
async def warn_cmd(interaction: discord.Interaction, nutzer: discord.Member, grund: str):
    warns = load_json(WARNS_FILE)
    uid = str(nutzer.id)
    if uid not in warns: warns[uid] = []
    warns[uid].append({"grund": grund, "mod": str(interaction.user), "datum": ts()})
    save_json(WARNS_FILE, warns)
    anzahl = len(warns[uid])
    ch = get_log_channel(interaction.guild)
    if ch:
        embed = discord.Embed(title="Nutzer verwarnt", color=0x1a3fdb)
        embed.set_thumbnail(url=nutzer.display_avatar.url)
        embed.add_field(name="Nutzer", value=f"{nutzer.mention} (`{nutzer.id}`)", inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Grund", value=grund, inline=True)
        embed.add_field(name="Verwarnungen gesamt", value=str(anzahl), inline=True)
        embed.set_footer(text=ts())
        await ch.send(embed=embed)
    await interaction.response.send_message(f"⚠️ {nutzer.mention} wurde verwarnt. ({anzahl}. Verwarnung)\nGrund: {grund}")

@bot.tree.command(name="warns", description="Verwarnungen eines Nutzers anzeigen")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(nutzer="Der Nutzer")
async def warns_cmd(interaction: discord.Interaction, nutzer: discord.Member):
    warns = load_json(WARNS_FILE)
    user_warns = warns.get(str(nutzer.id), [])
    if not user_warns:
        await interaction.response.send_message(f"✅ {nutzer.mention} hat keine Verwarnungen.", ephemeral=True); return
    embed = discord.Embed(title=f"Verwarnungen von {nutzer}", color=0x1a3fdb)
    for i, w in enumerate(user_warns, 1):
        embed.add_field(name=f"#{i} — {w['datum']}", value=f"**Grund:** {w['grund']}\n**Mod:** {w['mod']}", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clearwarns", description="Alle Verwarnungen eines Nutzers löschen")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(nutzer="Der Nutzer")
async def clearwarns_cmd(interaction: discord.Interaction, nutzer: discord.Member):
    warns = load_json(WARNS_FILE)
    warns[str(nutzer.id)] = []
    save_json(WARNS_FILE, warns)
    await interaction.response.send_message(f"✅ Alle Verwarnungen von {nutzer.mention} gelöscht.", ephemeral=True)

# ════════════════════════════════════════════════════════════
# VERIFICATION SYSTEM
# ════════════════════════════════════════════════════════════

pending_captcha = {}  # user_id -> richtige antwort

class CaptchaModal(discord.ui.Modal):
    def __init__(self, answer: int):
        super().__init__(title="Verifizierung — Bist du ein Mensch?")
        self.answer = answer
        self.eingabe = discord.ui.TextInput(
            label=f"Löse die Aufgabe um fortzufahren",
            placeholder="Deine Antwort...",
            max_length=5
        )
        self.add_item(self.eingabe)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_answer = int(self.eingabe.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ Bitte nur eine Zahl eingeben.", ephemeral=True)
            return

        if user_answer != self.answer:
            await interaction.response.send_message("❌ Falsche Antwort! Versuch es nochmal.", ephemeral=True)
            return

        cfg = gcfg(interaction.guild.id)
        verified_role_id = cfg.get("verified_role")
        unverified_role_id = cfg.get("unverified_role")

        if not verified_role_id:
            await interaction.response.send_message("❌ Verified-Rolle nicht eingestellt.", ephemeral=True)
            return

        verified_role = interaction.guild.get_role(int(verified_role_id))
        if not verified_role:
            await interaction.response.send_message("❌ Rolle nicht gefunden.", ephemeral=True)
            return

        await interaction.user.add_roles(verified_role)

        if unverified_role_id:
            unverified_role = interaction.guild.get_role(int(unverified_role_id))
            if unverified_role and unverified_role in interaction.user.roles:
                await interaction.user.remove_roles(unverified_role)

        embed = discord.Embed(title="Willkommen!", description="Du hast dich erfolgreich verifiziert und hast jetzt Zugang zum Server.", color=0x1a3fdb)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        ch = get_log_channel(interaction.guild)
        if ch:
            lembed = discord.Embed(title="Nutzer verifiziert", color=0x1a3fdb)
            lembed.add_field(name="Nutzer", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
            lembed.set_thumbnail(url=interaction.user.display_avatar.url)
            lembed.set_footer(text=ts())
            await ch.send(embed=lembed)

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verifizieren", style=discord.ButtonStyle.success, custom_id="verify_btn", emoji="✅")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.bot:
            await interaction.response.send_message("❌ Bots können sich nicht verifizieren.", ephemeral=True)
            return

        cfg = gcfg(interaction.guild.id)
        verified_role_id = cfg.get("verified_role")
        if not verified_role_id:
            await interaction.response.send_message("❌ Verified-Rolle nicht eingestellt.", ephemeral=True)
            return

        verified_role = interaction.guild.get_role(int(verified_role_id))
        if verified_role and verified_role in interaction.user.roles:
            await interaction.response.send_message("✅ Du bist bereits verifiziert!", ephemeral=True)
            return

        # Rechenaufgabe generieren
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        op = random.choice(["+", "-", "*"])
        if op == "+": answer = a + b
        elif op == "-": answer = a - b
        else:
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            answer = a * b

        modal = CaptchaModal(answer=answer)
        modal.title = f"Bist du ein Mensch? — {a} {op} {b} = ?"
        await interaction.response.send_modal(modal)

@bot.tree.command(name="verifypanel", description="Verification Panel senden")
@app_commands.checks.has_permissions(administrator=True)
async def verifypanel_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Verifizierung",
        description=(
            "Willkommen auf dem Server!\n\n"
            "Drücke den Button unten um dich zu verifizieren "
            "und Zugang zum Server zu erhalten.\n\n"
            "> Durch die Verifizierung stimmst du unseren Regeln zu."
        ),
        color=0x1a3fdb
    )
    embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(text="Nur einmal nötig  •  Dauert weniger als eine Sekunde")
    await interaction.channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message("✅ Verification Panel gesendet!", ephemeral=True)

@bot.tree.command(name="setverifiedrole", description="Rolle die Nutzer nach Verifizierung bekommen")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(rolle="Die Verified-Rolle")
async def setverifiedrole_cmd(interaction: discord.Interaction, rolle: discord.Role):
    scfg(interaction.guild.id, "verified_role", str(rolle.id))
    await interaction.response.send_message(f"✅ Verified-Rolle: {rolle.mention}", ephemeral=True)

@bot.tree.command(name="setunverifiedrole", description="Rolle die neue Nutzer beim Joinen bekommen")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(rolle="Die Unverified-Rolle")
async def setunverifiedrole_cmd(interaction: discord.Interaction, rolle: discord.Role):
    scfg(interaction.guild.id, "unverified_role", str(rolle.id))
    await interaction.response.send_message(f"✅ Unverified-Rolle: {rolle.mention}", ephemeral=True)



# ════════════════════════════════════════════════════════════
# GIVEAWAY SYSTEM
# ════════════════════════════════════════════════════════════

GIVEAWAYS_FILE = os.path.join(BASE, "giveaways.json")
VOUCHES_FILE   = os.path.join(BASE, "vouches.json")

def load_vouches():
    if os.path.exists(VOUCHES_FILE):
        with open(VOUCHES_FILE) as f:
            return json.load(f)
    return []

def save_vouches(data):
    with open(VOUCHES_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_giveaways():
    if os.path.exists(GIVEAWAYS_FILE):
        with open(GIVEAWAYS_FILE) as f:
            return json.load(f)
    return []

def save_giveaways(data):
    with open(GIVEAWAYS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

class GiveawayModal(discord.ui.Modal, title="🎁 Giveaway erstellen"):
    preis        = discord.ui.TextInput(label="Preis / Was wird verlost?", placeholder="z.B. Discord Nitro", max_length=100)
    gewinner     = discord.ui.TextInput(label="Anzahl Gewinner", placeholder="1", max_length=2)
    dauer        = discord.ui.TextInput(label="Dauer (z.B. 1h, 30m, 1d)", placeholder="1h", max_length=10)
    beschreibung = discord.ui.TextInput(label="Beschreibung (optional)", required=False, style=discord.TextStyle.paragraph, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        dauer_str = self.dauer.value.strip().lower()
        seconds = 0
        try:
            if dauer_str.endswith("d"):   seconds = int(dauer_str[:-1]) * 86400
            elif dauer_str.endswith("h"): seconds = int(dauer_str[:-1]) * 3600
            elif dauer_str.endswith("m"): seconds = int(dauer_str[:-1]) * 60
            else: raise ValueError
        except:
            await interaction.response.send_message("❌ Ungültige Dauer. Nutze z.B. `1h`, `30m`, `2d`", ephemeral=True)
            return

        try:
            winner_count = max(1, int(self.gewinner.value.strip()))
        except:
            winner_count = 1

        end_ts = int((datetime.now() + timedelta(seconds=seconds)).timestamp())

        embed = discord.Embed(title=f"🎁 {self.preis.value}", color=0x1a3fdb)
        if self.beschreibung.value:
            embed.description = self.beschreibung.value
        embed.add_field(name="Gewinner", value=str(winner_count), inline=True)
        embed.add_field(name="Endet", value=f"<t:{end_ts}:R>", inline=True)
        embed.add_field(name="Veranstalter", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Reagiere mit 🎉 um teilzunehmen!")

        await interaction.response.send_message("✅ Giveaway wird gestartet!", ephemeral=True)
        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction("🎉")

        giveaways = load_giveaways()
        giveaways.append({"message_id": str(msg.id), "channel_id": str(interaction.channel.id),
                          "guild_id": str(interaction.guild.id), "preis": self.preis.value,
                          "winner_count": winner_count, "end_ts": end_ts, "active": True})
        save_giveaways(giveaways)
        bot.loop.create_task(giveaway_timer(msg.id, interaction.channel.id, seconds))

async def giveaway_timer(message_id, channel_id, seconds):
    await asyncio.sleep(seconds)
    await end_giveaway(message_id, channel_id)

async def end_giveaway(message_id, channel_id):
    giveaways = load_giveaways()
    gw = next((g for g in giveaways if g["message_id"] == str(message_id) and g["active"]), None)
    if not gw: return
    channel = bot.get_channel(channel_id)
    if not channel: return
    try:
        msg = await channel.fetch_message(message_id)
    except:
        return

    teilnehmer = []
    for reaction in msg.reactions:
        if str(reaction.emoji) == "🎉":
            async for user in reaction.users():
                if not user.bot:
                    teilnehmer.append(user)

    embed = msg.embeds[0] if msg.embeds else discord.Embed(title=f"🎁 {gw['preis']}")
    embed.color = 0xed4245

    if not teilnehmer:
        embed.set_footer(text="Niemand hat teilgenommen.")
        await msg.edit(embed=embed)
        await channel.send("❌ Niemand hat am Giveaway teilgenommen.")
    else:
        winners = random.sample(teilnehmer, min(gw["winner_count"], len(teilnehmer)))
        embed.set_footer(text=f"Gewinner: {', '.join([str(w) for w in winners])}")
        await msg.edit(embed=embed)
        await channel.send(f"🎉 Glückwunsch {' '.join([w.mention for w in winners])}! Du hast **{gw['preis']}** gewonnen!\n> Du hast **1 Stunde** Zeit ein Ticket zu eröffnen!")

    for g in giveaways:
        if g["message_id"] == str(message_id):
            g["active"] = False
    save_giveaways(giveaways)

@bot.tree.command(name="giveaway", description="Neues Giveaway starten")
@app_commands.checks.has_permissions(manage_guild=True)
async def giveaway_cmd(interaction: discord.Interaction):
    await interaction.response.send_modal(GiveawayModal())

# ════════════════════════════════════════════════════════════
# VOUCH SYSTEM
# ════════════════════════════════════════════════════════════

STARS = {"1": "⭐", "2": "⭐⭐", "3": "⭐⭐⭐", "4": "⭐⭐⭐⭐", "5": "⭐⭐⭐⭐⭐"}

class VouchModal(discord.ui.Modal, title="Bewertung abgeben"):
    verkäufer = discord.ui.TextInput(label="Verkäufer (Name oder @)", placeholder="z.B. Kyron")
    produkt   = discord.ui.TextInput(label="Gekauftes Produkt", placeholder="z.B. Premium — 1 Monat")
    bewertung = discord.ui.TextInput(label="Bewertung (1-5 Sterne)", placeholder="5", max_length=1)
    kommentar = discord.ui.TextInput(label="Kommentar", style=discord.TextStyle.paragraph, placeholder="Wie war deine Erfahrung?", max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        if self.bewertung.value not in ("1","2","3","4","5"):
            await interaction.response.send_message("❌ Bewertung muss zwischen 1 und 5 sein.", ephemeral=True)
            return

        vouches = load_vouches()
        # Zählen wie oft dieser User schon gevoucht hat
        user_vouches = [v for v in vouches if v["user_id"] == str(interaction.user.id)]
        vouch_count = len(user_vouches) + 1

        entry = {
            "user": str(interaction.user),
            "user_id": str(interaction.user.id),
            "verkäufer": self.verkäufer.value,
            "produkt": self.produkt.value,
            "bewertung": self.bewertung.value,
            "kommentar": self.kommentar.value,
            "datum": ts()
        }
        vouches.append(entry)
        save_vouches(vouches)

        # Vouch Channel holen
        cfg = gcfg(interaction.guild.id)
        vouch_channel_id = cfg.get("vouch_channel")
        ch = interaction.guild.get_channel(int(vouch_channel_id)) if vouch_channel_id else interaction.channel

        embed = discord.Embed(color=0x1a3fdb)
        embed.add_field(name="Verkäufer", value=self.verkäufer.value, inline=True)
        embed.add_field(name="Käufer", value=interaction.user.mention, inline=True)
        embed.add_field(name="Bewertung", value=STARS.get(self.bewertung.value, "⭐"), inline=True)
        embed.add_field(name="Produkt", value=self.produkt.value, inline=False)
        embed.add_field(name="Kommentar", value=self.kommentar.value, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"{interaction.user} • {vouch_count}. Vouch  •  {ts()}")

        await ch.send(embed=embed)
        await interaction.response.send_message("✅ Vouch wurde abgegeben!", ephemeral=True)

@bot.tree.command(name="vouch", description="Bewertung abgeben")
async def vouch_cmd(interaction: discord.Interaction):
    await interaction.response.send_modal(VouchModal())

@bot.tree.command(name="setvouchchannel", description="Channel für Vouches einstellen")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="Der Channel für Vouches")
async def setvouchchannel_cmd(interaction: discord.Interaction, channel: discord.TextChannel):
    scfg(interaction.guild.id, "vouch_channel", str(channel.id))
    await interaction.response.send_message(f"✅ Vouch-Channel: {channel.mention}", ephemeral=True)

@bot.tree.command(name="greroll", description="Giveaway neu auslosen")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(message_id="Message ID des Giveaways")
async def greroll_cmd(interaction: discord.Interaction, message_id: str):
    await interaction.response.defer(ephemeral=True)
    try:
        msg = await interaction.channel.fetch_message(int(message_id))
    except:
        await interaction.followup.send("❌ Nachricht nicht gefunden.", ephemeral=True)
        return
    teilnehmer = []
    for reaction in msg.reactions:
        if str(reaction.emoji) == "🎉":
            async for user in reaction.users():
                if not user.bot: teilnehmer.append(user)
    if not teilnehmer:
        await interaction.followup.send("❌ Keine Teilnehmer.", ephemeral=True)
        return
    winner = random.choice(teilnehmer)
    await interaction.channel.send(f"🎉 Neuer Gewinner: {winner.mention} — Glückwunsch!")
    await interaction.followup.send("✅ Neu ausgelost!", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(TicketPanelView())
    bot.add_view(KaufTicketView())
    bot.add_view(CloseTicketView())
    bot.add_view(VerifyView())
    print(f"✅ Bot eingeloggt als {bot.user}")
    # Globale Commands leeren
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    # Alle Commands guild-spezifisch registrieren
    for guild in bot.guilds:
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ {len(synced)} Commands in {guild.name}")

bot.run(TOKEN)
