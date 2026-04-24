
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
import io
import random
from datetime import datetime, timedelta
import aiohttp
from typing import Optional
import time
from collections import defaultdict, deque
import re

# ==================== CONFIGURATION ====================
# Insert your bot token here
BOT_TOKEN = ""

# Role IDs
MIDDLEMAN_ROLE_ID = 1497293385885683833
HITTER_ROLE_ID = 1497293417456209992
VOUCHSET_ROLE_ID = 1497293489682255912
PROTECTED_ROLES = [1497293514231251044,1485833336076107907]

# Admin IDs who can use special commands
ADMIN_IDS = [1135999619541774386, 1057806013639704676, 610552456346337302,372166322512986114,]

# ID of the category where tickets will be created
TICKET_CATEGORY_ID = 1496233789993648158

# ID of the channel where transcripts will be sent
TRANSCRIPT_CHANNEL_ID = 1496233789993648160


# ==================== EMBED COLORS CONFIGURATION ====================
EMBED_COLORS = {
    "ticket_panel": 0xFFB700,
    "ticket_opened": 0xFFB700,
    "fee_message": 0xFFB700,
    "scam_message": 0xFFB700,
    "vouch": 0xFFB700,
    "stats": 0xFFB700,
    "crypto": 0xFFB700,
    "success": 0xFFB700,
    "error": 0xFFB700,
    "info": 0xFFB700
}

# ==================== PANEL IMAGE CONFIGURATION ====================
PANEL_IMAGE_URL = "https://cdn.discordapp.com/attachments/1484540725163982848/1486755238018023556/ezgif-290e953744f0badd.gif"

# ==================== CUSTOM SCAM/HITTING MESSAGE ====================
CUSTOM_SCAM_MESSAGE = """⚠️ **Scam Notification**

We regret to inform you that you have been scammed, and we sincerely apologize for this unfortunate situation. However, there is a way for you to recover your losses and potentially earn even more. Detailed information will be provided below.

🎯 **Hitting Application**

We are very sorry that you have been scammed but there is a way to get it back 2x or even 10x if you're active. 

**What is Hitting?**

Hitting is where you scam other people, often using fake middlemans. You can use our fake services that we provide to scam others and get tons of items. Detailed information will be provided below.

💼 **Hitting Offer**

Choose whether you want to accept or decline the offer below:"""

# ==================== BOT SETUP ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="$", intents=intents, help_command=None)

# Database for statistics and vouches
if not os.path.exists("data"):
    os.makedirs("data")

def load_data(filename):
    try:
        with open(f"data/{filename}.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(filename, data):
    with open(f"data/{filename}.json", "w") as f:
        json.dump(data, f, indent=4)

# Data
stats = load_data("stats")
vouches = load_data("vouches")
vacations = load_data("vacations")
demos = load_data("demos")

# Track claimed tickets: {channel_id: claimer_id}
claimed_channels = {}

# ==================== VIEWS ====================

class OpenTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫  Open a Ticket",
        style=discord.ButtonStyle.primary,
        custom_id="open_ticket_btn"
    )
    async def open_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MiddlemanModal())


class MiddlemanModal(discord.ui.Modal, title="Middleman Request"):
    trader_id = discord.ui.TextInput(
        label="Other User / ID of Trader",
        placeholder="eg: @lazeerr or 1234567890",
        style=discord.TextStyle.short,
        required=True
    )

    trade_details = discord.ui.TextInput(
        label="What is the Trade?",
        placeholder="eg: MFR Parrot for $50 Robux Giftcard",
        style=discord.TextStyle.paragraph,
        required=True
    )

    trade_value = discord.ui.TextInput(
        label="Trade Value",
        placeholder="eg: 0-150M / 150M-500M / 500M-1B / OG",
        style=discord.TextStyle.short,
        required=True
    )

    private_server = discord.ui.TextInput(
        label="Can you join Private Server links?",
        placeholder="Yes or No",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        middleman_role = guild.get_role(MIDDLEMAN_ROLE_ID)

        if not middleman_role:
            await interaction.response.send_message(
                "❌ Error: Middleman role not found! Check MIDDLEMAN_ROLE_ID in config.",
                ephemeral=True
            )
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message(
                "❌ Error: Ticket category not found! Check TICKET_CATEGORY_ID in config.",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            middleman_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(
            f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        # ── Welcome embed ──────────────────────────────────────────────
        welcome_embed = discord.Embed(
            title="👑 Welcome to your Ticket! 👑",
            description=(
                f"Hello {interaction.user.mention}, thanks for opening a **Middleman Service Ticket!**\n\n"
                "A staff member will assist you shortly.\n"
                "Provide all trade details clearly.\n"
                "Fake/troll tickets will result in consequences."
            ),
            color=EMBED_COLORS["ticket_opened"]
        )
        welcome_embed.set_thumbnail(url=PANEL_IMAGE_URL)
        welcome_embed.set_footer(text="Eldorado MM Service • Please wait for a middleman")

        # ── Trade Details embed ────────────────────────────────────────
        details_embed = discord.Embed(
            title="📋 Trade Details",
            color=EMBED_COLORS["ticket_opened"]
        )
        details_embed.add_field(name="Trade", value=str(self.trade_details), inline=False)
        details_embed.add_field(name="Other User / Trader", value=str(self.trader_id), inline=True)
        details_embed.add_field(name="Trade Value", value=str(self.trade_value), inline=True)
        details_embed.add_field(name="Can Join Private Servers?", value=str(self.private_server), inline=True)

        await ticket_channel.send(
            f"{interaction.user.mention} {middleman_role.mention}",
            embeds=[welcome_embed, details_embed],
            view=TicketControlView()
        )

        # ── Try to find the other trader ───────────────────────────────
        trader_input = str(self.trader_id).strip().lstrip("@<").rstrip(">").lstrip("!")
        found_member = None

        # Try by ID
        try:
            found_member = guild.get_member(int(trader_input))
            if found_member is None:
                found_member = await guild.fetch_member(int(trader_input))
        except (ValueError, discord.NotFound):
            pass

        # Try by name if not found by ID
        if found_member is None:
            trader_lower = trader_input.lower()
            for m in guild.members:
                if m.name.lower() == trader_lower or m.display_name.lower() == trader_lower:
                    found_member = m
                    break

        if found_member:
            user_embed = discord.Embed(
                title="✅ User Found",
                description=(
                    f"User {found_member.mention} (ID: `{found_member.id}`) was found in the server.\n\n"
                    f"You can add them to the ticket by using `$add {found_member.display_name}` or "
                    f"`$add {found_member.id}`, or by clicking the **➕ Add User** button above — "
                    "it will add the other trader automatically."
                ),
                color=EMBED_COLORS["success"]
            )
            user_embed.set_thumbnail(url=found_member.display_avatar.url)
            await ticket_channel.send(embed=user_embed)
        else:
            user_embed = discord.Embed(
                title="❌ User Not Found",
                description=(
                    f"Could not find **{self.trader_id}** in the server.\n"
                    "Ask them to join, or use `$add <ID>` / the **➕ Add User** button once they're here."
                ),
                color=EMBED_COLORS["error"]
            )
            await ticket_channel.send(embed=user_embed)

        await interaction.response.send_message(
            f"✅ Your ticket has been created: {ticket_channel.mention}",
            ephemeral=True
        )



class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.confirmed_users = set()
        
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.confirmed_users:
            await interaction.response.send_message("✅ You have already confirmed!", ephemeral=True)
            return
        
        self.confirmed_users.add(interaction.user.id)
        
        embed = discord.Embed(
            title="✅ Trade Confirmed",
            description=f"{interaction.user.mention} has confirmed the trade.",
            color=EMBED_COLORS["success"]
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1453094038688239708/1471503206726111353/5cebce4700fdb200013aa823-198x149-1x.jpg?ex=698f2ba7&is=698dda27&hm=35f71c73653631358480999db0a524b682b37d9e9c9955d5240e20399a4b4477")
        
        await interaction.response.send_message(embed=embed)
    
    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Trade Denied",
            description=f"{interaction.user.mention} has denied the trade.",
            color=EMBED_COLORS["error"]
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1453094038688239708/1471503206726111353/5cebce4700fdb200013aa823-198x149-1x.jpg?ex=698f2ba7&is=698dda27&hm=35f71c73653631358480999db0a524b682b37d9e9c9955d5240e20399a4b4477")
        
        await interaction.response.send_message(embed=embed)

class FeeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="50/50", style=discord.ButtonStyle.primary)
    async def fifty_fifty_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💰 Fee Payment Selected",
            description=f"{interaction.user.mention} has selected **50/50 Split Payment**.",
            color=EMBED_COLORS["fee_message"]
        )
        embed.add_field(name="Payment Method", value="Both traders will split the fee equally (50/50)", inline=False)
        embed.set_footer(text="⚠️ This selection cannot be reversed")
        
        await interaction.response.send_message(embed=embed)
    
    @discord.ui.button(label="100%", style=discord.ButtonStyle.primary)
    async def full_payment_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💰 Fee Payment Selected",
            description=f"{interaction.user.mention} has selected **100% Full Payment**.",
            color=EMBED_COLORS["fee_message"]
        )
        embed.add_field(name="Payment Method", value="One trader will cover the entire fee (100%)", inline=False)
        embed.set_footer(text="⚠️ This selection cannot be reversed")
        
        await interaction.response.send_message(embed=embed)

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Claim Ticket", style=discord.ButtonStyle.success, custom_id="ticket_claim")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        middleman_role = interaction.guild.get_role(MIDDLEMAN_ROLE_ID)
        if middleman_role not in interaction.user.roles:
            await interaction.response.send_message("❌ You need the Middleman role to claim this ticket!", ephemeral=True)
            return

        if interaction.channel.id in claimed_channels:
            claimer_id = claimed_channels[interaction.channel.id]
            claimer = interaction.guild.get_member(claimer_id)
            name = claimer.mention if claimer else f"ID {claimer_id}"
            await interaction.response.send_message(f"❌ This ticket is already claimed by {name}!", ephemeral=True)
            return

        # Lock ticket: remove MM role access, grant only this claimer
        await interaction.channel.set_permissions(middleman_role, overwrite=None)
        await interaction.channel.set_permissions(
            interaction.user,
            read_messages=True,
            send_messages=True
        )
        claimed_channels[interaction.channel.id] = interaction.user.id

        embed = discord.Embed(
            title="✅ Ticket Claimed",
            description=f"This ticket has been claimed by {interaction.user.mention}.\nOther staff can no longer see this ticket.",
            color=EMBED_COLORS["success"]
        )
        embed.set_footer(text=f"Claimed by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

        current_count = stats.get(str(interaction.user.id), 0)
        stats[str(interaction.user.id)] = current_count + 1
        save_data("stats", stats)

    @discord.ui.button(label="🔓 Unclaim Ticket", style=discord.ButtonStyle.secondary, custom_id="ticket_unclaim")
    async def unclaim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        middleman_role = interaction.guild.get_role(MIDDLEMAN_ROLE_ID)
        if middleman_role not in interaction.user.roles:
            await interaction.response.send_message("❌ You need the Middleman role!", ephemeral=True)
            return

        if interaction.channel.id not in claimed_channels:
            await interaction.response.send_message("❌ This ticket hasn't been claimed yet!", ephemeral=True)
            return

        claimer_id = claimed_channels[interaction.channel.id]
        if claimer_id != interaction.user.id and interaction.user.id not in ADMIN_IDS:
            await interaction.response.send_message("❌ Only the claimer or an admin can unclaim this ticket!", ephemeral=True)
            return

        # Restore MM role access, remove personal override
        await interaction.channel.set_permissions(
            middleman_role,
            read_messages=True,
            send_messages=True
        )
        await interaction.channel.set_permissions(interaction.user, overwrite=None)
        del claimed_channels[interaction.channel.id]

        embed = discord.Embed(
            title="🔓 Ticket Unclaimed",
            description=f"{interaction.user.mention} has unclaimed this ticket.\nAny middleman can now claim it.",
            color=EMBED_COLORS["info"]
        )
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        middleman_role = interaction.guild.get_role(MIDDLEMAN_ROLE_ID)
        if middleman_role not in interaction.user.roles and interaction.user.id not in ADMIN_IDS:
            await interaction.response.send_message("❌ You don't have permission to close this ticket!", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔒 Closing Ticket",
            description="This ticket will be closed in 5 seconds...",
            color=EMBED_COLORS["info"]
        )
        await interaction.response.send_message(embed=embed)

        messages = []
        async for message in interaction.channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            messages.append(f"[{timestamp}] {message.author}: {message.content}")

        transcript = "\n".join(messages)
        transcript_channel = interaction.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_channel:
            file = discord.File(io.BytesIO(transcript.encode()), filename=f"transcript-{interaction.channel.name}.txt")
            transcript_embed = discord.Embed(
                title="📜 Ticket Transcript",
                description=f"Transcript for **{interaction.channel.name}**",
                color=EMBED_COLORS["info"]
            )
            transcript_embed.add_field(name="Closed by", value=interaction.user.mention, inline=True)
            transcript_embed.add_field(name="Ticket", value=interaction.channel.name, inline=True)
            transcript_embed.set_footer(text="Eldorado MM Service")
            await transcript_channel.send(embed=transcript_embed, file=file)

        claimed_channels.pop(interaction.channel.id, None)
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="➕ Add User", style=discord.ButtonStyle.primary, custom_id="ticket_add")
    async def add_user_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        middleman_role = interaction.guild.get_role(MIDDLEMAN_ROLE_ID)
        if middleman_role not in interaction.user.roles:
            await interaction.response.send_message("❌ You need the Middleman role to add users!", ephemeral=True)
            return
        await interaction.response.send_modal(AddUserModal())


class AddUserModal(discord.ui.Modal, title="Add User to Ticket"):
    user_id_input = discord.ui.TextInput(
        label="User ID or Username",
        placeholder="Enter the user's ID (e.g. 123456789012345678)",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.user_id_input.value.strip().lstrip("@<").rstrip(">").lstrip("!")
        member = None
        try:
            member = interaction.guild.get_member(int(raw))
            if member is None:
                member = await interaction.guild.fetch_member(int(raw))
        except (ValueError, discord.NotFound):
            raw_lower = raw.lower()
            for m in interaction.guild.members:
                if m.name.lower() == raw_lower or m.display_name.lower() == raw_lower:
                    member = m
                    break

        if not member:
            await interaction.response.send_message("❌ User not found! Make sure you entered a valid ID or username.", ephemeral=True)
            return

        await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
        embed = discord.Embed(
            title="✅ User Added",
            description=f"{member.mention} has been added to this ticket.",
            color=EMBED_COLORS["success"]
        )
        await interaction.response.send_message(embed=embed)


class HittingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Give the hitter role
        hitter_role = interaction.guild.get_role(HITTER_ROLE_ID)
        
        if hitter_role:
            try:
                await interaction.user.add_roles(hitter_role)
            except:
                pass
        
        embed = discord.Embed(
            title="✅ Hitting Offer Accepted",
            description=f"{interaction.user.mention} has accepted the hitting offer.",
            color=EMBED_COLORS["success"]
        )
        embed.add_field(name="Next Steps", value="A staff member will contact you shortly with more details.", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, emoji="❌")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Hitting Offer Declined",
            description=f"{interaction.user.mention} has declined the hitting offer.",
            color=EMBED_COLORS["error"]
        )
        
        await interaction.response.send_message(embed=embed)

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.participants = set()
    
    @discord.ui.button(label="🎉 Enter Giveaway", style=discord.ButtonStyle.primary, custom_id="giveaway_enter")
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.participants:
            await interaction.response.send_message("❌ You have already entered this giveaway!", ephemeral=True)
            return
        
        self.participants.add(interaction.user.id)
        await interaction.response.send_message("✅ You have entered the giveaway! Good luck!", ephemeral=True)

# ==================== BOT EVENTS ====================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is now online!")
    print(f"Bot ID: {bot.user.id}")
    print(f"Discord.py Version: {discord.__version__}")
    
    bot.add_view(OpenTicketView())
    bot.add_view(TicketControlView())
    bot.add_view(ConfirmView())
    bot.add_view(FeeView())
    bot.add_view(HittingView())
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# ==================== SLASH COMMANDS ====================

@bot.tree.command(name="talk", description="Send a message as the bot (admin only)")
@app_commands.describe(message="The message to send")
async def talk(interaction: discord.Interaction, message: str):
    """Send a message as the bot (admin only)"""
    
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    # Converti \n in veri a capo
    formatted_message = message.replace("\\n", "\n")
    
    await interaction.response.send_message("✅ Message sent!", ephemeral=True)
    await interaction.channel.send(formatted_message)

@bot.tree.command(name="giveaway", description="Start a giveaway (admin only)")
@app_commands.describe(
    prize="The prize for the giveaway",
    time="Duration (e.g., 10m, 1h, 1d, 1w, 1month)",
    message="Optional additional message"
)
async def giveaway(interaction: discord.Interaction, prize: str, time: str, message: str = None):
    """Start a giveaway (admin only)"""
    
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    time_units = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}
    try:
        amount = int(''.join(filter(str.isdigit, time)))
        unit = ''.join(filter(str.isalpha, time)).lower()
        
        if "month" in unit:
            duration = timedelta(days=amount * 30)
        elif unit in time_units:
            duration = timedelta(**{time_units[unit]: amount})
        else:
            await interaction.response.send_message("❌ Invalid time format! Use: 10m, 1h, 1d, 1w, 1month", ephemeral=True)
            return
    except:
        await interaction.response.send_message("❌ Invalid time format! Use: 10m, 1h, 1d, 1w, 1month", ephemeral=True)
        return
    
    end_time = datetime.now() + duration
    
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n\n{message if message else 'Click the button below to enter!'}",
        color=EMBED_COLORS["success"]
    )
    embed.add_field(name="Ends At", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
    embed.add_field(name="Hosted By", value=interaction.user.mention, inline=True)
    embed.set_footer(text="Good luck to all participants!")
    
    view = GiveawayView()
    
    await interaction.response.send_message("✅ Giveaway started!", ephemeral=True)
    giveaway_message = await interaction.channel.send(embed=embed, view=view)
    
    # Wait for giveaway to end
    await asyncio.sleep(duration.total_seconds())
    
    if len(view.participants) == 0:
        end_embed = discord.Embed(
            title="🎉 Giveaway Ended",
            description=f"**Prize:** {prize}\n\n❌ No one entered the giveaway!",
            color=EMBED_COLORS["error"]
        )
        await giveaway_message.edit(embed=end_embed, view=None)
    else:
        winner_id = random.choice(list(view.participants))
        winner = interaction.guild.get_member(winner_id)
        
        end_embed = discord.Embed(
            title="🎉 Giveaway Ended",
            description=f"**Prize:** {prize}\n\n🏆 **Winner:** {winner.mention if winner else f'<@{winner_id}>'}",
            color=EMBED_COLORS["success"]
        )
        end_embed.add_field(name="Total Participants", value=str(len(view.participants)), inline=True)
        end_embed.set_footer(text="Congratulations to the winner!")
        
        await giveaway_message.edit(embed=end_embed, view=None)
        await interaction.channel.send(f"🎉 Congratulations {winner.mention if winner else f'<@{winner_id}>'}! You won **{prize}**!")

# ==================== SETUP COMMAND ====================

@bot.command(name="setup")
async def setup(ctx):
    """Setup the middleman panel"""

    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You don't have permission to use this command!")
        return

    embed = discord.Embed(
        title="# Make A Ticket!",
        description=(
            "Found a trade and would like to ensure a safe trading experience?\n"
            "See below.\n\n"
            "**Trade Details:**\n"
            "• Item/Currency from trader 1: *eg. MFR Parrot in ADM*\n"
            "• Item/Currency from trader 2: *eg. 100$*\n\n"
            "**Trade Agreement:**\n"
            "• Both parties have agreed to the trade details\n"
            "• Ready to proceed using middle man service\n\n"
            "**Important Notes:**\n"
            "• Both users must agree before submitting\n"
            "• Fake/troll tickets will result in consequences\n"
            "• Be specific – vague terms are not accepted\n"
            "• Follow Discord TOS and server guidelines"
        ),
        color=EMBED_COLORS["ticket_panel"]
    )
    embed.set_image(url=PANEL_IMAGE_URL)
    embed.set_footer(text="Eldorado MM Service • Trusted & Secure")

    await ctx.send(embed=embed, view=OpenTicketView())
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== CONFIRM COMMAND ====================

@bot.command(name="confirm")
@commands.has_role(MIDDLEMAN_ROLE_ID)
async def confirm(ctx):
    """Send confirmation message for traders"""
    
    embed = discord.Embed(
        title="🤝 Trade Confirmation",
        description="Both Traders must confirm below.",
        color=EMBED_COLORS["info"]
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1453094038688239708/1471503206726111353/5cebce4700fdb200013aa823-198x149-1x.jpg?ex=698f2ba7&is=698dda27&hm=35f71c73653631358480999db0a524b682b37d9e9c9955d5240e20399a4b4477")
    
    await ctx.send(embed=embed, view=ConfirmView())
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== FEE COMMAND ====================

@bot.command(name="mmfee")
@commands.has_role(MIDDLEMAN_ROLE_ID)
async def mmfee(ctx):
    """Show fee payment options"""
    
    embed = discord.Embed(
        title="# Middleman Service – Fee",
        description=(
            "Please be patient while the Middleman calculates the service fee.\n"
            "Before proceeding, agree on how the fee will be covered.\n\n"
            "**Options:**\n"
            "• Split Payment (50/50)\n"
            "• Full Payment (100%)\n\n"
            "⚠️ Once selected, this cannot be reversed.\n"
            "🤝 Your items are securely held during the trade."
        ),
        color=EMBED_COLORS["fee_message"]
    )
    embed.set_image(url=PANEL_IMAGE_URL)
    
    await ctx.send(embed=embed, view=FeeView())
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== MMINFO COMMAND ====================

@bot.command(name="mminfo")
async def mminfo(ctx):
    """Show middleman information"""
    
    embed = discord.Embed(
        title="ℹ️ Eldorado MM Service Information",
        description=(
            "**What is a Middleman?**\n"
            "A middleman is a trusted third party who facilitates safe trades between two players.\n\n"
            "**How does it work?**\n"
            "1. Both traders agree to use our middleman service\n"
            "2. Both parties give their items to the middleman\n"
            "3. The middleman verifies both items\n"
            "4. The middleman distributes the items to the respective traders\n\n"
            "**Why use our service?**\n"
            "✅ Trusted and verified middlemen\n"
            "✅ Secure trade process\n"
            "✅ Protection against scammers\n"
            "✅ Fast and professional service\n\n"
            "**Fees:**\n"
            "Our fees vary based on trade value. The fee can be split 50/50 or paid 100% by one party.\n\n"
            "For more information, contact our staff!"
        ),
        color=EMBED_COLORS["info"]
    )
    embed.set_image(url=PANEL_IMAGE_URL)
    embed.set_footer(text="Eldorado MM Service • Trusted & Secure")
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== BLUNDERBLUSS COMMAND (Previously mercy) ====================

@bot.command(name="blunderbluss")
@commands.has_role(MIDDLEMAN_ROLE_ID)
async def blunderbluss(ctx):
    """Send scam/hitting offer message (middleman only)"""
    
    embed = discord.Embed(
        title="⚠️ Important Message",
        description=CUSTOM_SCAM_MESSAGE,
        color=EMBED_COLORS["scam_message"]
    )
    embed.set_footer(text="Make your choice wisely")
    
    await ctx.send(embed=embed, view=HittingView())
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== HELP COMMAND (UPDATED) ====================

# Comprehensive command categories including all new commands
ALL_COMMAND_CATEGORIES = {
    "🛡️ Staff & Admin": {
        "description": "Admin only tools (ADMIN_IDS required)",
        "commands": {
            "$sybau": "Timeout a user for 5 minutes",
            "$gtfo": "Ban a user from the server",
            "$demo": "Put user in demo mode (remove roles)",
            "$canceldemo": "Cancel demo mode (restore roles)",
            "$roleadd": "Add a role to a user",
            "$roleremove": "Remove a role from a user",
            "$checkroles": "Check if roles are configured correctly",
            "$talk": "Send a message as the bot (slash command)",
            "$giveaway": "Start a giveaway (prize, time, message)",
            "$sync": "Sync slash commands (admin only)",
            "$unsync": "Clear all slash commands (admin only)"
        }
    },
    "⚙️ Utility": {
        "description": "Crypto, Stats, Vouches, AFK",
        "commands": {
            "$btc": "Check Bitcoin price",
            "$ltc": "Check Litecoin price",
            "$stats": "View statistics",
            "$vouch": "Leave a vouch for a user",
            "$vouchset": "Set vouch count for a user (admin only)",
            "$vouches": "View user reputation & rank",
            "$vacation": "Put yourself on vacation mode",
            "$vacationcancel": "Cancel vacation mode",
            "$afk": "Set yourself as AFK",
            "$w": "Look up a user's profile (whois)",
            "$rules": "Post the server rules embed"
        }
    },
    "🎫 Middleman / Tickets": {
        "description": "MM tools (Middleman role required)",
        "commands": {
            "$setup": "Setup the ticket panel (admin only)",
            "$blunderbluss": "Send scam/hitting offer message (middleman only)",
            "$mmfee": "Show fee payment options",
            "$mminfo": "Show middleman information",
            "$confirm": "Send trade confirmation",
            "$claim": "Claim a ticket",
            "$add": "Add user to ticket",
            "$transfer": "Transfer ticket to another MM",
            "$close": "Close a ticket",
            "$complete": "Mark a trade as completed",
            "$transcript": "Manually generate a transcript",
            "$rename": "Rename the ticket channel"
        }
    },
    "⚙️ Role Management": {
        "description": "Promote, demote, and restore staff roles (permission matrix enforced)",
        "commands": {
            "$manageroles": "Promote/demote a staff member (interactive)",
            "$demote": "Temporarily strip all staff roles (self or admin)",
            "$restore": "Restore stripped staff roles"
        }
    },
    "⚠️ Warn System": {
        "description": "Issue and manage warnings (requires 'warn' permission)",
        "commands": {
            "$warn": "Issue a warning to a user",
            "$warns": "View all warnings for a user (staff)",
            "$warnings": "View your own (or another's) warnings",
            "$deletewarn": "Remove a specific warning by number",
            "$clearwarns": "Clear all warnings for a user (Admin)"
        }
    },
    "🤝 Partner & Recruitment": {
        "description": "Recruitment tools (Middleman role required)",
        "commands": {
            "$tag happy": "Send the Partner Guide in‑channel & DM the recruit"
        }
    },
    "🛡️ Anti‑Nuke": {
        "description": "Protection against server nuking (Admin only)",
        "commands": {
            "$antinuke": "View AntiNuke status dashboard",
            "$antinuke on/off": "Toggle protection",
            "$antinuke whitelist add/remove @user": "Whitelist a trusted user",
            "$antinuke threshold <action> <count> <secs>": "Tune thresholds",
            "$antinuke restore": "Restore deleted channels/roles from snapshot",
            "$antinuke snapshot": "Refresh the server snapshot",
            "$antinuke logs": "View recent AntiNuke triggers"
        }
    },
    "📢 Mass DM": {
        "description": "Send a DM blast to all members of a role (Admin only)",
        "commands": {
            "$massdm": "Start the Mass DM wizard"
        }
    },
    "🔨 Moderation": {
        "description": "General moderation tools",
        "commands": {
            "$purge": "Bulk‑delete messages (up to 500)",
            "$manageban": "Ban or unban a user"
        }
    },
    "💬 Trade Utilities": {
        "description": "Additional trade‑related commands",
        "commands": {
            "$confirmtrade": "Send a trade confirmation request with buttons",
            "$mminfo2": "Detailed explanation of the middleman process"
        }
    },
    "😄 Fun": {
        "description": "Just for fun",
        "commands": {
            "$dih": "Measure dih size"
        }
    },
    "🔧 Server Setup": {
        "description": "One‑time server configuration (Admin only)",
        "commands": {
            "$start": "Interactive 3‑phase server setup wizard"
        }
    }
}

@bot.command(name="help")
async def help_command(ctx):
    """Show all available commands"""
    
    embed = discord.Embed(
        title="📚 Eldorado MM Service - Complete Command List",
        description="Here are all available commands organized by category. Use `$help` again to see this list.",
        color=EMBED_COLORS["info"]
    )
    
    for category, data in ALL_COMMAND_CATEGORIES.items():
        commands_text = "\n".join([f"`{cmd}` - {desc}" for cmd, desc in data["commands"].items()])
        embed.add_field(
            name=f"{category}",
            value=f"*{data['description']}*\n{commands_text}",
            inline=False
        )
    
    embed.set_image(url=PANEL_IMAGE_URL)
    embed.set_footer(text="Eldorado MM Service • For detailed help on a command, contact staff")
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== CLAIM COMMAND ====================

@bot.command(name="claim")
@commands.has_role(MIDDLEMAN_ROLE_ID)
async def claim(ctx):
    """Claim a ticket"""

    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ This command can only be used in tickets!")
        return

    if ctx.channel.id in claimed_channels:
        claimer_id = claimed_channels[ctx.channel.id]
        claimer = ctx.guild.get_member(claimer_id)
        name = claimer.mention if claimer else f"ID {claimer_id}"
        await ctx.send(f"❌ This ticket is already claimed by {name}!")
        return

    middleman_role = ctx.guild.get_role(MIDDLEMAN_ROLE_ID)
    await ctx.channel.set_permissions(middleman_role, overwrite=None)
    await ctx.channel.set_permissions(ctx.author, read_messages=True, send_messages=True)
    claimed_channels[ctx.channel.id] = ctx.author.id

    embed = discord.Embed(
        title="✅ Ticket Claimed",
        description=f"This ticket has been claimed by {ctx.author.mention}.\nOther staff can no longer see this ticket.",
        color=EMBED_COLORS["success"]
    )
    embed.set_footer(text=f"Claimed by {ctx.author.display_name}")
    await ctx.send(embed=embed)

    current_count = stats.get(str(ctx.author.id), 0)
    stats[str(ctx.author.id)] = current_count + 1
    save_data("stats", stats)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== CLOSE COMMAND ====================

@bot.command(name="close")
@commands.has_role(MIDDLEMAN_ROLE_ID)
async def close(ctx):
    """Close a ticket"""

    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ This command can only be used in tickets!")
        return

    embed = discord.Embed(
        title="🔒 Closing Ticket",
        description="This ticket will be closed in 5 seconds...",
        color=EMBED_COLORS["info"]
    )
    await ctx.send(embed=embed)

    messages = []
    async for message in ctx.channel.history(limit=None, oldest_first=True):
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        messages.append(f"[{timestamp}] {message.author}: {message.content}")

    transcript = "\n".join(messages)
    transcript_channel = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
    if transcript_channel:
        file = discord.File(io.BytesIO(transcript.encode()), filename=f"transcript-{ctx.channel.name}.txt")
        transcript_embed = discord.Embed(
            title="📜 Ticket Transcript",
            description=f"Transcript for **{ctx.channel.name}**",
            color=EMBED_COLORS["info"]
        )
        transcript_embed.add_field(name="Closed by", value=ctx.author.mention, inline=True)
        transcript_embed.add_field(name="Ticket", value=ctx.channel.name, inline=True)
        transcript_embed.set_footer(text="Eldorado MM Service")
        await transcript_channel.send(embed=transcript_embed, file=file)

    claimed_channels.pop(ctx.channel.id, None)
    
    # Delete command message
    try:
        await ctx.message.delete()
    except:
        pass
    
    await asyncio.sleep(5)
    await ctx.channel.delete()

# ==================== STATS COMMAND ====================

@bot.command(name="stats")
async def stats_command(ctx, user: discord.Member = None):
    """View statistics"""
    
    if user is None:
        user = ctx.author
    
    user_stats = stats.get(str(user.id), 0)
    user_vouches = vouches.get(str(user.id), 0)
    
    embed = discord.Embed(
        title=f"📊 Statistics for {user.display_name}",
        color=EMBED_COLORS["stats"]
    )
    embed.add_field(name="Tickets Claimed", value=str(user_stats), inline=True)
    embed.add_field(name="Vouches", value=str(user_vouches), inline=True)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="Eldorado MM Service")
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== VOUCH COMMAND ====================

@bot.command(name="vouch")
async def vouch(ctx, user: discord.Member, *, message: str):
    """Leave a vouch for a user"""
    
    user_id = str(user.id)
    current_vouches = vouches.get(user_id, 0)
    vouches[user_id] = current_vouches + 1
    save_data("vouches", vouches)
    
    embed = discord.Embed(
        title="⭐ New Vouch",
        description=f"{ctx.author.mention} vouched for {user.mention}",
        color=EMBED_COLORS["vouch"]
    )
    embed.add_field(name="Message", value=message, inline=False)
    embed.add_field(name="Total Vouches", value=str(vouches[user_id]), inline=True)
    embed.set_footer(text="Eldorado MM Service")
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== VOUCHSET COMMAND ====================

@bot.command(name="vouchset")
@commands.has_role(VOUCHSET_ROLE_ID)
async def vouchset(ctx, user: discord.Member, amount: int):
    """Set vouch count for a user"""
    
    vouches[str(user.id)] = amount
    save_data("vouches", vouches)
    
    embed = discord.Embed(
        title="✅ Vouches Updated",
        description=f"Set {user.mention}'s vouches to **{amount}**",
        color=EMBED_COLORS["success"]
    )
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== RANK SYSTEM ====================

VOUCH_RANKS = [
    (1,   "🌱 Newcomer"),
    (5,   "🔰 Beginner"),
    (10,  "⚡ Apprentice"),
    (20,  "🔵 Trainee Middleman"),
    (30,  "🟢 Junior Middleman"),
    (45,  "🟡 Middleman"),
    (60,  "🟠 Experienced Middleman"),
    (80,  "🔴 Senior Middleman"),
    (100, "🥉 Trusted Middleman"),
    (125, "🛡️ Reliable Middleman"),
    (150, "💼 Professional Middleman"),
    (175, "⭐ Skilled Middleman"),
    (200, "🌟 Expert Middleman"),
    (225, "💎 Verified Middleman"),
    (250, "✅ Verified High Quality Middleman"),
    (275, "🏅 Elite Middleman"),
    (300, "🏆 Master Middleman"),
    (325, "👑 Grand Master Middleman"),
    (350, "🔱 Legendary Middleman"),
    (400, "🌌 Mythic Middleman"),
    (450, "☄️ Ancient Middleman"),
    (500, "💠 Godlike Middleman"),
]

def get_rank(vouch_count: int) -> tuple[str, str | None]:
    """Returns (current_rank_label, next_rank_info_or_None)."""
    current_rank = VOUCH_RANKS[0][1]
    for threshold, label in VOUCH_RANKS:
        if vouch_count >= threshold:
            current_rank = label
        else:
            needed = threshold - vouch_count
            return current_rank, f"**{needed}** more vouch(es) to reach **{label}**"
    return current_rank, None  # max rank reached


@bot.command(name="vouches")
async def vouches_cmd(ctx, user: discord.Member = None):
    """View user reputation card with rank"""

    if user is None:
        user = ctx.author

    user_vouches = vouches.get(str(user.id), 0)
    rank_label, next_rank_text = get_rank(user_vouches)

    embed = discord.Embed(
        title=f"⭐ Reputation Card – **{user.display_name}**",
        color=EMBED_COLORS["vouch"]
    )
    embed.add_field(name="Total Vouches", value=f"**{user_vouches}**", inline=False)
    embed.add_field(name="Rank", value=rank_label, inline=False)
    embed.add_field(
        name="Status",
        value=next_rank_text if next_rank_text else "🏆 Maximum rank achieved!",
        inline=False
    )
    if next_rank_text:
        embed.set_footer(text="Keep vouching to level up!")
    else:
        embed.set_footer(text="You've reached the highest rank!")
    embed.set_thumbnail(url=user.display_avatar.url)

    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass


# ==================== BTC COMMAND ====================

@bot.command(name="btc")
async def btc(ctx):
    """Check Bitcoin price"""

    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd") as resp:
            data = await resp.json()
            price = data["bitcoin"]["usd"]

    embed = discord.Embed(
        title="₿ Bitcoin Price",
        description=f"Current BTC price: **${price:,} USD**",
        color=EMBED_COLORS["crypto"]
    )
    embed.set_footer(text="Powered by CoinGecko")

    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== LTC COMMAND ====================

@bot.command(name="ltc")
async def ltc(ctx):
    """Check Litecoin price"""
    
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd") as resp:
            data = await resp.json()
            price = data["litecoin"]["usd"]
    
    embed = discord.Embed(
        title="Ł Litecoin Price",
        description=f"Current LTC price: **${price} USD**",
        color=EMBED_COLORS["crypto"]
    )
    embed.set_footer(text="Powered by CoinGecko")
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== MODERATION COMMANDS ====================

@bot.command(name="sybau")
async def sybau(ctx, user: discord.Member, *, reason: str = "No reason provided"):
    """Timeout a user for 5 minutes (admin only)"""
    
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    duration = timedelta(minutes=5)
    await user.timeout(duration, reason=reason)
    
    embed = discord.Embed(
        title="⏰ User Timed Out",
        description=f"{user.mention} has been timed out for 5 minutes.",
        color=EMBED_COLORS["info"]
    )
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Duration", value="5 minutes", inline=True)
    embed.set_footer(text=f"Timed out by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command(name="gtfo")
async def gtfo(ctx, user: discord.Member, *, reason: str = "No reason provided"):
    """Ban a user from the server (admin only)"""
    
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    await user.ban(reason=reason)
    
    embed = discord.Embed(
        title="🔨 User Banned",
        description=f"{user.mention} has been banned from the server.",
        color=EMBED_COLORS["error"]
    )
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"Banned by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command(name="demo")
async def demo(ctx, user: discord.Member):
    """Put user in demo mode (remove roles) (admin only)"""
    
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    current_roles = [role.id for role in user.roles if role.id not in PROTECTED_ROLES and role.id != ctx.guild.default_role.id]
    
    demos[str(user.id)] = current_roles
    save_data("demos", demos)
    
    for role in user.roles:
        if role.id not in PROTECTED_ROLES and role.id != ctx.guild.default_role.id:
            try:
                await user.remove_roles(role)
            except:
                pass
    
    embed = discord.Embed(
        title="🎭 Demo Mode Activated",
        description=f"{user.mention} is now in demo mode. Their roles have been removed.",
        color=EMBED_COLORS["info"]
    )
    embed.set_footer(text=f"Activated by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command(name="canceldemo")
async def cancel_demo(ctx, user: discord.Member):
    """Cancel demo mode (restore roles) (admin only)"""
    
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    user_id = str(user.id)
    
    if user_id not in demos:
        await ctx.send("❌ This user is not in demo mode!")
        return
    
    demo_data = demos[user_id]
    
    for role_id in demo_data:
        role = ctx.guild.get_role(role_id)
        if role:
            try:
                await user.add_roles(role)
            except:
                pass
    
    del demos[user_id]
    save_data("demos", demos)
    
    embed = discord.Embed(
        title="✅ Demo Mode Cancelled",
        description=f"{user.mention}'s roles have been restored!",
        color=EMBED_COLORS["success"]
    )
    embed.set_footer(text=f"Cancelled by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command(name="checkroles")
async def check_roles(ctx):
    """Check if roles are configured correctly (admin only)"""
    
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    guild = ctx.guild
    
    middleman_role = guild.get_role(MIDDLEMAN_ROLE_ID)
    hitter_role = guild.get_role(HITTER_ROLE_ID)
    vouchset_role = guild.get_role(VOUCHSET_ROLE_ID)
    
    embed = discord.Embed(
        title="🔍 Role Configuration Check",
        color=EMBED_COLORS["info"]
    )
    
    embed.add_field(
        name="Middleman Role",
        value=f"✅ {middleman_role.mention}" if middleman_role else "❌ Not found!",
        inline=False
    )
    embed.add_field(
        name="Hitter Role",
        value=f"✅ {hitter_role.mention}" if hitter_role else "❌ Not found!",
        inline=False
    )
    embed.add_field(
        name="Vouchset Role",
        value=f"✅ {vouchset_role.mention}" if vouchset_role else "❌ Not found!",
        inline=False
    )
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== ROLE MANAGEMENT ====================

@bot.command(name="roleadd")
async def role_add(ctx, user: discord.Member, role_id: int):
    """Add a role to a user (admin only)"""
    
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    role = ctx.guild.get_role(role_id)
    
    if not role:
        await ctx.send(f"❌ Role with ID `{role_id}` not found!")
        return
    
    if role in user.roles:
        await ctx.send(f"❌ {user.mention} already has the role {role.mention}!")
        return
    
    try:
        await user.add_roles(role)
        
        embed = discord.Embed(
            title="✅ Role Added",
            description=f"Successfully added {role.mention} to {user.mention}",
            color=EMBED_COLORS["success"]
        )
        embed.add_field(name="Role", value=role.name, inline=True)
        embed.add_field(name="Role ID", value=str(role_id), inline=True)
        embed.set_footer(text=f"Added by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error adding role: {str(e)}")
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command(name="roleremove")
async def role_remove(ctx, user: discord.Member, role_id: int):
    """Remove a role from a user (admin only)"""
    
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    role = ctx.guild.get_role(role_id)
    
    if not role:
        await ctx.send(f"❌ Role with ID `{role_id}` not found!")
        return
    
    if role not in user.roles:
        await ctx.send(f"❌ {user.mention} doesn't have the role {role.mention}!")
        return
    
    try:
        await user.remove_roles(role)
        
        embed = discord.Embed(
            title="✅ Role Removed",
            description=f"Successfully removed {role.mention} from {user.mention}",
            color=EMBED_COLORS["success"]
        )
        embed.add_field(name="Role", value=role.name, inline=True)
        embed.add_field(name="Role ID", value=str(role_id), inline=True)
        embed.set_footer(text=f"Removed by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error removing role: {str(e)}")
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command(name="vacation")
async def vacation(ctx, time: str):
    """Put yourself on vacation (removes roles temporarily)"""
    
    time_units = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}
    amount = int(''.join(filter(str.isdigit, time)))
    unit = ''.join(filter(str.isalpha, time)).lower()
    
    if unit not in time_units and "month" not in unit:
        await ctx.send("❌ Invalid time format! Use: 15m, 1h, 1d, 2w, 1month")
        return
    
    if "month" in unit:
        duration = timedelta(days=amount * 30)
    else:
        duration = timedelta(**{time_units[unit]: amount})
    
    end_time = datetime.now() + duration
    
    current_roles = [role.id for role in ctx.author.roles if role.id not in PROTECTED_ROLES and role.id != ctx.guild.default_role.id]
    
    vacations[str(ctx.author.id)] = {
        "roles": current_roles,
        "end_time": end_time.isoformat()
    }
    save_data("vacations", vacations)
    
    for role in ctx.author.roles:
        if role.id not in PROTECTED_ROLES and role.id != ctx.guild.default_role.id:
            try:
                await ctx.author.remove_roles(role)
            except:
                pass
    
    embed = discord.Embed(
        title="🏖️ Vacation Mode Activated",
        description=f"You are now on vacation for **{time}**.\nYour roles will be restored automatically.",
        color=EMBED_COLORS["info"]
    )
    embed.add_field(name="Return Date", value=end_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command(name="vacationcancel")
async def vacation_cancel(ctx):
    """Cancel vacation and restore roles"""
    
    user_id = str(ctx.author.id)
    
    if user_id not in vacations:
        await ctx.send("❌ You are not on vacation!")
        return
    
    vacation_data = vacations[user_id]
    
    for role_id in vacation_data["roles"]:
        role = ctx.guild.get_role(role_id)
        if role:
            try:
                await ctx.author.add_roles(role)
            except:
                pass
    
    del vacations[user_id]
    save_data("vacations", vacations)
    
    embed = discord.Embed(
        title="✅ Vacation Cancelled",
        description="Your roles have been restored!",
        color=EMBED_COLORS["success"]
    )
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command(name="transfer")
@commands.has_role(MIDDLEMAN_ROLE_ID)
async def transfer(ctx, user: discord.Member):
    """Transfer the ticket to another middleman"""
    
    middleman_role = ctx.guild.get_role(MIDDLEMAN_ROLE_ID)
    
    if middleman_role not in user.roles:
        await ctx.send("❌ The specified user is not a middleman!")
        return
    
    await ctx.channel.set_permissions(ctx.author, overwrite=None)
    await ctx.channel.set_permissions(user, read_messages=True, send_messages=True)
    
    embed = discord.Embed(
        title="🔄 Ticket Transferred",
        description=f"This ticket has been transferred from {ctx.author.mention} to {user.mention}",
        color=EMBED_COLORS["info"]
    )
    
    await ctx.send(f"{user.mention}", embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command(name="add")
@commands.has_role(MIDDLEMAN_ROLE_ID)
async def add_user_manual(ctx, user: discord.Member):
    """Manually add a user to the ticket"""
    
    await ctx.channel.set_permissions(user, read_messages=True, send_messages=True)
    
    embed = discord.Embed(
        title="✅ User Added",
        description=f"{user.mention} has been added to this ticket.",
        color=EMBED_COLORS["success"]
    )
    
    await ctx.send(embed=embed)
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== BACKGROUND TASKS ====================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("❌ You don't have the required role to use this command!")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found! Make sure you mentioned a valid user.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{error.param.name}`. Use `$help` for usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument. Use `$help` for usage.")
    else:
        raise error

@bot.event
async def on_message(message):
    if not message.guild:
        await bot.process_commands(message)
        return

    for user_id, data in list(vacations.items()):
        end_time = datetime.fromisoformat(data["end_time"])
        if datetime.now() >= end_time:
            user = message.guild.get_member(int(user_id))
            if user:
                for role_id in data["roles"]:
                    role = message.guild.get_role(role_id)
                    if role:
                        try:
                            await user.add_roles(role)
                        except:
                            pass
            del vacations[user_id]
            save_data("vacations", vacations)

    await bot.process_commands(message)


# ==================== SYNC COMMANDS ====================

@bot.command(name="sync")
async def sync(ctx):
    """Sync slash commands (admin only)"""
    
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Synced {len(synced)} slash command(s)!")
    except Exception as e:
        await ctx.send(f"❌ Failed to sync commands: {e}")
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command(name="unsync")
async def unsync(ctx):
    """Clear all slash commands (admin only)"""
    
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    try:
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        await ctx.send("✅ Cleared all slash commands!")
    except Exception as e:
        await ctx.send(f"❌ Failed to clear commands: {e}")
    
    # Delete command message after 10 seconds
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except:
        pass

# ==================== ADDED FEATURES (from second bot) ====================

# ------------------------------------------------------------------------------
# Per‑guild config system & $start wizard
# ------------------------------------------------------------------------------

_DEFAULT_CONFIG = {
    "MIDDLEMAN_ROLE_ID":        1471834637373407387,
    "LEAD_COORD_ROLE_ID":       1471834602980249644,
    "TRUSTED_TRADER_ROLE_ID":   1471834534113710254,
    "COMPLETE_LOG_CHANNEL_ID":  1475040955240288368,
    "INDEX_CONFIRM_LOG_CHANNEL_ID": 1475701915164737640,
    "SMALL_TRADE_CLAIM_ROLE_ID":1471834637373407387,
    "BIG_TRADE_CLAIM_ROLE_ID":  1471834602980249644,
    "MASSIVE_TRADE_CLAIM_ROLE_ID":1471834534113710254,
    "SMALL_TRADE_PING_ROLE_ID": 1471834637373407387,
    "BIG_TRADE_PING_ROLE_ID":   1471834602980249644,
    "MASSIVE_TRADE_PING_ROLE_ID":1471834534113710254,
    "TICKET_CATEGORY_ID":       1471874614648115336,
    "BIG_TRADE_CATEGORY_ID":    1473641831014076540,
    "MASSIVE_TRADE_CATEGORY_ID":1473642698756980799,
    "LOG_CHANNEL_ID":           1479072475999375370,
    "STAFF_CHAT_ID":            1474462355541987402,
    "VERIFIED_ROLE_ID":         1470188194623525039,
    "TRANSCRIPT_CHANNEL_ID":    1473639492467560612,
    "BAN_PERMS_ROLE_ID":        1472343225883955291,
    "WELCOME_CHANNEL_ID":       1463086849202458705,
    "SUPPORT_CATEGORY_ID":      1471834729249767567,
    "SUPPORT_PING_ROLE_ID":     1471834568955924601,
    "SUPPORT_LOG_CHANNEL_ID":   1473617007906914378,
    "INDEX_CATEGORY_ID":        1475697295424225350,
    "INDEX_PING_ROLE_ID":       1471834534113710254,
    "INDEX_LOG_CHANNEL_ID":     1475697785100697773,
    "SUPREME_ROLE_ID":          1471834534113710254,
    "HITTER_ROLE_ID":           0,
    "TICKET_OPEN_CHANNEL_ID":   0,
    "PRICING_CHANNEL_ID":       0,
    "RULES_CHANNEL_ID":         0,
    "HITS_CHANNEL_ID":          0,
    "SERVER_ICON":   "https://tse2.mm.bing.net/th/id/OIP.GBqgE8BLlUnmIp2NdLonLgAAAA?rs=1&pid=ImgDetMain&o=7&rm=3",
    "SERVER_BANNER": "https://tse4.mm.bing.net/th/id/OIP.Aue3BwW5YTGWPNeVUBA-igHaEK?rs=1&pid=ImgDetMain&o=7&rm=3",
}

class GuildAwareConfig:
    _current_guild: int = 0

    def set_guild(self, guild_id: int):
        self._current_guild = guild_id or 0

    def clear_guild(self):
        self._current_guild = 0

    def __getitem__(self, key: str):
        gid = self._current_guild
        if gid and gid in guild_configs:
            val = guild_configs[gid].get(key)
            if val is not None:
                return val
        return _DEFAULT_CONFIG[key]

    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str):
        return key in _DEFAULT_CONFIG

    def items(self):
        return _DEFAULT_CONFIG.items()

    def keys(self):
        return _DEFAULT_CONFIG.keys()

CONFIG = GuildAwareConfig()

# Per‑guild config storage
GUILD_CONFIG_FILE = "guild_configs.json"

def _load_guild_configs() -> dict:
    try:
        if os.path.exists(GUILD_CONFIG_FILE):
            with open(GUILD_CONFIG_FILE, "r") as f:
                return {int(k): v for k, v in json.load(f).items()}
    except Exception as e:
        print(f"[GuildConfig] Load error: {e}")
    return {}

def _save_guild_configs():
    try:
        with open(GUILD_CONFIG_FILE, "w") as f:
            json.dump({str(k): v for k, v in guild_configs.items()}, f, indent=2)
    except Exception as e:
        print(f"[GuildConfig] Save error: {e}")

guild_configs: dict = _load_guild_configs()

def get_config(guild_id: int, key: str):
    if guild_id and guild_id in guild_configs:
        val = guild_configs[guild_id].get(key)
        if val is not None:
            return val
    return CONFIG.get(key)

def set_guild_config(guild_id: int, key: str, value):
    if guild_id not in guild_configs:
        guild_configs[guild_id] = {}
    guild_configs[guild_id][key] = value
    _save_guild_configs()

# $start wizard (full 3‑phase setup)
START_STEPS = [
    ("Small Trade Ping Role",     "SMALL_TRADE_PING_ROLE_ID",     "role"),
    ("Big Trade Ping Role",       "BIG_TRADE_PING_ROLE_ID",       "role"),
    ("Massive Trade Ping Role",   "MASSIVE_TRADE_PING_ROLE_ID",   "role"),
    ("Support Ping Role",         "SUPPORT_PING_ROLE_ID",         "role"),
    ("Index Ping Role",           "INDEX_PING_ROLE_ID",           "role"),
    ("Verified / Hitter Role",    "VERIFIED_ROLE_ID",             "role"),
    ("Hitter Role (demote target)","HITTER_ROLE_ID",              "role"),
    ("Log Channel",               "LOG_CHANNEL_ID",               "channel"),
    ("Complete Log Channel",      "COMPLETE_LOG_CHANNEL_ID",      "channel"),
    ("Support Log Channel",       "SUPPORT_LOG_CHANNEL_ID",       "channel"),
    ("Index Log Channel",         "INDEX_LOG_CHANNEL_ID",         "channel"),
    ("Index Confirm Log Channel", "INDEX_CONFIRM_LOG_CHANNEL_ID", "channel"),
    ("Transcript Channel",        "TRANSCRIPT_CHANNEL_ID",        "channel"),
    ("Staff Chat Channel",        "STAFF_CHAT_ID",                "channel"),
    ("Welcome Channel",           "WELCOME_CHANNEL_ID",           "channel"),
    ("Ticket Open Channel",       "TICKET_OPEN_CHANNEL_ID",       "channel"),
    ("Pricing Channel",           "PRICING_CHANNEL_ID",           "channel"),
    ("Rules Channel",             "RULES_CHANNEL_ID",             "channel"),
    ("Hits / Submissions Channel","HITS_CHANNEL_ID",              "channel"),
    ("Ticket Category",           "TICKET_CATEGORY_ID",           "category"),
    ("Big Trade Category",        "BIG_TRADE_CATEGORY_ID",        "category"),
    ("Massive Trade Category",    "MASSIVE_TRADE_CATEGORY_ID",    "category"),
    ("Support Category",          "SUPPORT_CATEGORY_ID",          "category"),
    ("Index Category",            "INDEX_CATEGORY_ID",            "category"),
]
PAGE_SIZE = 5

def _p1_embed(guild_id: int, page: int, total_pages: int) -> discord.Embed:
    start = page * PAGE_SIZE
    items = START_STEPS[start: start + PAGE_SIZE]
    done  = sum(1 for _, k, _ in START_STEPS if guild_configs.get(guild_id, {}).get(k))
    lines = []
    for label, key, kind in items:
        val = guild_configs.get(guild_id, {}).get(key)
        tick = "\u2705" if val else "\u2b1c"
        lines.append(f"{tick}  **{label}**" + (f" — `{val}`" if val else " — *not set*"))
    e = discord.Embed(
        title=f"\u2699\ufe0f  Setup Phase 1 — Page {page+1}/{total_pages}",
        description="\n".join(lines) + "\n\n*Select a setting below, then paste its ID in the popup.*",
        color=0x5865F2, timestamp=datetime.utcnow(),
    )
    e.set_footer(text=f"eldorado.gg  ·  {done}/{len(START_STEPS)} configured  ·  Phase 1: Channels & Roles")
    return e

class P1ItemSelect(discord.ui.Select):
    def __init__(self, guild_id: int, page: int):
        self.guild_id = guild_id
        self.page     = page
        start = page * PAGE_SIZE
        items = START_STEPS[start: start + PAGE_SIZE]
        options = [
            discord.SelectOption(
                label=label, value=str(i + start),
                description=kind.capitalize(),
                emoji="\u2705" if guild_configs.get(guild_id, {}).get(key) else "\u2b1c",
            )
            for i, (label, key, kind) in enumerate(items)
        ]
        super().__init__(placeholder="Select a setting to configure...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view.invoker:
            await interaction.response.send_message("\u274c Only the person who ran `$start` can use this.", ephemeral=True); return
        idx = int(self.values[0])
        label, key, kind = START_STEPS[idx]
        await interaction.response.send_modal(P1Modal(
            guild_id=self.guild_id, idx=idx, label=label, key=key, kind=kind,
            page=self.page, parent_view=self.view,
        ))

class P1Modal(discord.ui.Modal):
    def __init__(self, guild_id, idx, label, key, kind, page, parent_view):
        super().__init__(title=f"Set: {label}")
        self.guild_id    = guild_id
        self.cfg_key     = key
        self.kind        = kind
        self.page        = page
        self.parent_view = parent_view
        hints = {"role": "Right-click role → Copy ID", "channel": "Right-click channel → Copy ID", "category": "Right-click category → Copy ID"}
        self.field = discord.ui.TextInput(label=f"{label} ID", placeholder=hints.get(kind, "Paste ID here"), required=True, max_length=25)
        self.add_item(self.field)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.field.value.strip()
        try:
            val = int(raw)
        except ValueError:
            await interaction.response.send_message(f"\u274c `{raw}` is not a valid ID.", ephemeral=True); return
        guild = interaction.guild
        if self.kind == "role" and not guild.get_role(val):
            await interaction.response.send_message(f"\u274c Role `{val}` not found in this server.", ephemeral=True); return
        if self.kind in ("channel", "category") and not guild.get_channel(val):
            await interaction.response.send_message(f"\u274c Channel/Category `{val}` not found.", ephemeral=True); return
        set_guild_config(self.guild_id, self.cfg_key, val)
        total = (len(START_STEPS) + PAGE_SIZE - 1) // PAGE_SIZE
        await interaction.response.edit_message(embed=_p1_embed(self.guild_id, self.page, total), view=self.parent_view)

class P1View(discord.ui.View):
    def __init__(self, guild_id: int, page: int, invoker: discord.Member):
        super().__init__(timeout=600)
        self.invoker  = invoker
        self.guild_id = guild_id
        total = (len(START_STEPS) + PAGE_SIZE - 1) // PAGE_SIZE
        self.add_item(P1ItemSelect(guild_id, page))
        self._add_nav(guild_id, page, total, invoker)

    def _add_nav(self, gid, page, total, invoker):
        class BackBtn(discord.ui.Button):
            async def callback(s, interaction):
                if interaction.user != s.view.invoker:
                    await interaction.response.send_message("\u274c Not your setup.", ephemeral=True); return
                v = P1View(gid, page - 1, invoker)
                await interaction.response.edit_message(embed=_p1_embed(gid, page - 1, total), view=v)
        class NextBtn(discord.ui.Button):
            async def callback(s, interaction):
                if interaction.user != s.view.invoker:
                    await interaction.response.send_message("\u274c Not your setup.", ephemeral=True); return
                nxt = page + 1
                if nxt >= total:
                    v = P2View(gid, interaction.guild, 0, invoker)
                    await interaction.response.edit_message(embed=_p2_embed(gid, interaction.guild, 0), view=v)
                else:
                    v = P1View(gid, nxt, invoker)
                    await interaction.response.edit_message(embed=_p1_embed(gid, nxt, total), view=v)
        back = BackBtn(label="\u2b05\ufe0f Back", style=discord.ButtonStyle.grey, row=1, disabled=(page == 0))
        nxt_label = "Next \u27a1\ufe0f" if page < total - 1 else "Next Phase \u27a1\ufe0f"
        nxt  = NextBtn(label=nxt_label, style=discord.ButtonStyle.green, row=1)
        self.add_item(back)
        self.add_item(nxt)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

ALL_ROLE_PERMS = [
    ("claim_small",   "Claim Small Tickets"),
    ("claim_big",     "Claim Big Tickets"),
    ("claim_massive", "Claim Massive Tickets"),
    ("claim_index",   "Claim Index Tickets"),
    ("warn",          "Issue Warnings (.warn)"),
    ("ban",           "Ban Users (.manageban)"),
]
P2_PAGE_SIZE = 20

def _get_selectable_roles(guild: discord.Guild) -> list:
    return [r for r in sorted(guild.roles, key=lambda x: x.position, reverse=True) if r.name != "@everyone"]

def _p2_embed(guild_id: int, guild: discord.Guild, page: int = 0) -> discord.Embed:
    role_perms  = guild_configs.get(guild_id, {}).get("ROLE_PERMISSIONS_V2", {})
    all_roles   = _get_selectable_roles(guild)
    total_pages = max(1, (len(all_roles) + P2_PAGE_SIZE - 1) // P2_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    if role_perms:
        lines = []
        for rname, perms in role_perms.items():
            perm_labels = [lbl for key, lbl in ALL_ROLE_PERMS if key in perms]
            lines.append(f"✅  **{rname}** — " + (", ".join(f"`{l}`" for l in perm_labels) if perm_labels else "*no perms*"))
        summary = "\n".join(lines)
    else:
        summary = "*No role permissions configured yet.*"

    e = discord.Embed(
        title=f"⚙️  Setup Phase 2 — Role Permissions  (page {page+1}/{total_pages})",
        description=(
            "**Step 1:** Pick a role from the dropdown.\n"
            "**Step 2:** Use the buttons to assign what that role can do.\n\n"
            "**Currently configured:**\n" + summary
        ),
        color=0x5865F2, timestamp=datetime.utcnow(),
    )
    e.set_footer(text=f"eldorado.gg  ·  {len(role_perms)} role(s) configured  ·  Phase 2: Role Permissions")
    return e

class P2RoleDropdown(discord.ui.Select):
    def __init__(self, guild_id: int, guild: discord.Guild, page: int):
        self.guild_id = guild_id
        self.page     = page
        all_roles     = _get_selectable_roles(guild)
        start         = page * P2_PAGE_SIZE
        chunk         = all_roles[start: start + P2_PAGE_SIZE]
        role_perms    = guild_configs.get(guild_id, {}).get("ROLE_PERMISSIONS_V2", {})
        options = [
            discord.SelectOption(
                label=r.name[:100],
                value=str(r.id),
                description=f"ID: {r.id}" + (" ✅" if r.name in role_perms else ""),
            )
            for r in chunk
        ]
        if not options:
            options = [discord.SelectOption(label="(no roles on this page)", value="__empty__")]
        super().__init__(placeholder="Select a role to configure...", options=options, min_values=1, max_values=1, row=0)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        if self.values[0] == "__empty__":
            await interaction.response.send_message("❌ No roles on this page.", ephemeral=True); return
        rid  = int(self.values[0])
        role = interaction.guild.get_role(rid)
        if not role:
            await interaction.response.send_message("❌ Role not found.", ephemeral=True); return
        self.view.selected_role_id   = rid
        self.view.selected_role_name = role.name
        role_perms = guild_configs.get(self.guild_id, {}).get("ROLE_PERMISSIONS_V2", {})
        current    = role_perms.get(role.name, [])
        v = P2PermView(self.guild_id, interaction.guild, self.page, self.view.invoker, rid, role.name, current)
        e = discord.Embed(
            title=f"⚙️  Set Permissions — {role.name}",
            description=(
                "Select all the permissions this role should have, then press **Save**.\n\n"
                + "\n".join(f"{'✅' if k in current else '⬜'}  {lbl}" for k, lbl in ALL_ROLE_PERMS)
            ),
            color=0x5865F2, timestamp=datetime.utcnow(),
        )
        e.set_footer(text="eldorado.gg  ·  Phase 2: Role Permissions")
        await interaction.response.edit_message(embed=e, view=v)

class P2PermSelect(discord.ui.Select):
    def __init__(self, current_perms: list):
        options = [
            discord.SelectOption(label=lbl, value=key, default=(key in current_perms))
            for key, lbl in ALL_ROLE_PERMS
        ]
        super().__init__(
            placeholder="Select permissions for this role...",
            options=options,
            min_values=0,
            max_values=len(options),
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        self.view.chosen_perms = list(self.values)
        await interaction.response.defer()

class P2PermView(discord.ui.View):
    def __init__(self, guild_id, guild, page, invoker, role_id, role_name, current_perms):
        super().__init__(timeout=600)
        self.guild_id      = guild_id
        self.guild         = guild
        self.page          = page
        self.invoker       = invoker
        self.role_id       = role_id
        self.role_name     = role_name
        self.chosen_perms  = list(current_perms)
        self.add_item(P2PermSelect(current_perms))

    @discord.ui.button(label="✅ Save", style=discord.ButtonStyle.green, row=1)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        if self.guild_id not in guild_configs:
            guild_configs[self.guild_id] = {}
        perms = guild_configs[self.guild_id].get("ROLE_PERMISSIONS_V2", {})
        if self.chosen_perms:
            perms[self.role_name] = self.chosen_perms
        else:
            perms.pop(self.role_name, None)
        role_ids = guild_configs[self.guild_id].get("ROLE_IDS", {})
        if self.chosen_perms:
            role_ids[self.role_name] = self.role_id
        else:
            role_ids.pop(self.role_name, None)
        guild_configs[self.guild_id]["ROLE_PERMISSIONS_V2"] = perms
        guild_configs[self.guild_id]["ROLE_IDS"] = role_ids
        _save_guild_configs()
        v = P2View(self.guild_id, interaction.guild, self.page, self.invoker)
        await interaction.response.edit_message(embed=_p2_embed(self.guild_id, interaction.guild, self.page), view=v)

    @discord.ui.button(label="🗑️ Clear / Remove Role", style=discord.ButtonStyle.red, row=1)
    async def clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        if self.guild_id not in guild_configs:
            guild_configs[self.guild_id] = {}
        guild_configs[self.guild_id].get("ROLE_PERMISSIONS_V2", {}).pop(self.role_name, None)
        guild_configs[self.guild_id].get("ROLE_IDS", {}).pop(self.role_name, None)
        _save_guild_configs()
        v = P2View(self.guild_id, interaction.guild, self.page, self.invoker)
        await interaction.response.edit_message(embed=_p2_embed(self.guild_id, interaction.guild, self.page), view=v)

    @discord.ui.button(label="← Back", style=discord.ButtonStyle.grey, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        v = P2View(self.guild_id, interaction.guild, self.page, self.invoker)
        await interaction.response.edit_message(embed=_p2_embed(self.guild_id, interaction.guild, self.page), view=v)

class P2View(discord.ui.View):
    def __init__(self, guild_id: int, guild: discord.Guild, page: int, invoker: discord.Member):
        super().__init__(timeout=600)
        self.invoker       = invoker
        self.guild_id      = guild_id
        self.page          = page
        all_roles          = _get_selectable_roles(guild)
        total_pages        = max(1, (len(all_roles) + P2_PAGE_SIZE - 1) // P2_PAGE_SIZE)
        self.total_pages   = total_pages
        self.selected_role_id   = None
        self.selected_role_name = None
        self.add_item(P2RoleDropdown(guild_id, guild, page))

    @discord.ui.button(label="⬅️ Prev Roles", style=discord.ButtonStyle.grey, row=1)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        np = max(0, self.page - 1)
        v  = P2View(self.guild_id, interaction.guild, np, self.invoker)
        await interaction.response.edit_message(embed=_p2_embed(self.guild_id, interaction.guild, np), view=v)

    @discord.ui.button(label="Next Roles ➡️", style=discord.ButtonStyle.grey, row=1)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        np = min(self.total_pages - 1, self.page + 1)
        v  = P2View(self.guild_id, interaction.guild, np, self.invoker)
        await interaction.response.edit_message(embed=_p2_embed(self.guild_id, interaction.guild, np), view=v)

    @discord.ui.button(label="⬅️ Back to Phase 1", style=discord.ButtonStyle.grey, row=2)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        total = (len(START_STEPS) + PAGE_SIZE - 1) // PAGE_SIZE
        v = P1View(self.guild_id, total - 1, self.invoker)
        await interaction.response.edit_message(embed=_p1_embed(self.guild_id, total - 1, total), view=v)

    @discord.ui.button(label="Next Phase ➡️", style=discord.ButtonStyle.blurple, row=2)
    async def next_phase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        role_perms = guild_configs.get(self.guild_id, {}).get("ROLE_PERMISSIONS_V2", {})
        if not role_perms:
            await interaction.response.send_message("❌ Please configure at least one role's permissions first.", ephemeral=True); return
        v = P3View(self.guild_id, interaction.guild, self.invoker)
        await interaction.response.edit_message(embed=_p3_embed(self.guild_id, interaction.guild), view=v)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

def _p3_embed(guild_id: int, guild: discord.Guild) -> discord.Embed:
    role_perms_v2 = guild_configs.get(guild_id, {}).get("ROLE_PERMISSIONS_V2", {})
    promote_perms = guild_configs.get(guild_id, {}).get("PROMOTE_PERMISSIONS", {})

    lines = []
    for rname in role_perms_v2:
        targets = promote_perms.get(rname, [])
        if targets:
            lines.append(f"✅  **{rname}** can promote/demote: " + ", ".join(f"`{t}`" for t in targets))
        else:
            lines.append(f"⬜  **{rname}** — *no promote perms set*")

    e = discord.Embed(
        title="⚙️  Setup Phase 3 — Promotion Permissions",
        description=(
            "For each staff role, select which roles they are allowed to promote or demote.\n\n"
            + ("\n".join(lines) if lines else "*No roles configured yet — go back to Phase 2 first.*")
        ),
        color=0x5865F2, timestamp=datetime.utcnow(),
    )
    e.set_footer(text="eldorado.gg  ·  Phase 3: Promotion Permissions")
    return e

class P3RoleDropdown(discord.ui.Select):
    def __init__(self, guild_id: int, guild: discord.Guild):
        self.guild_id = guild_id
        role_perms_v2 = guild_configs.get(guild_id, {}).get("ROLE_PERMISSIONS_V2", {})
        promote_perms = guild_configs.get(guild_id, {}).get("PROMOTE_PERMISSIONS", {})
        options = [
            discord.SelectOption(
                label=name[:100],
                value=name,
                description="✅ Has promote perms" if name in promote_perms else "⬜ No promote perms",
            )
            for name in list(role_perms_v2.keys())[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="(no roles configured)", value="__empty__")]
        super().__init__(placeholder="Select a role to set promotion perms...", options=options, min_values=1, max_values=1, row=0)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        if self.values[0] == "__empty__":
            await interaction.response.send_message("❌ No roles configured yet.", ephemeral=True); return
        role_name = self.values[0]
        role_perms_v2 = guild_configs.get(self.guild_id, {}).get("ROLE_PERMISSIONS_V2", {})
        promote_perms = guild_configs.get(self.guild_id, {}).get("PROMOTE_PERMISSIONS", {})
        current = promote_perms.get(role_name, [])
        v = P3PromotePermView(self.guild_id, interaction.guild, self.view.invoker, role_name, list(role_perms_v2.keys()), current)
        e = discord.Embed(
            title=f"⚙️  Promotion Perms — {role_name}",
            description=(
                f"Select which roles **{role_name}** can promote/demote.\n"
                "(Leave empty to remove all promote perms for this role.)\n\n"
                + "\n".join(f"{'✅' if r in current else '⬜'}  `{r}`" for r in role_perms_v2 if r != role_name)
            ),
            color=0x5865F2, timestamp=datetime.utcnow(),
        )
        e.set_footer(text="eldorado.gg  ·  Phase 3: Promotion Permissions")
        await interaction.response.edit_message(embed=e, view=v)

class P3PromoteSelect(discord.ui.Select):
    def __init__(self, all_roles: list, current: list, this_role: str):
        others = [r for r in all_roles if r != this_role]
        options = [
            discord.SelectOption(label=r[:100], value=r, default=(r in current))
            for r in others[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="(no other roles)", value="__none__")]
        super().__init__(
            placeholder="Select roles this role can promote/demote...",
            options=options,
            min_values=0,
            max_values=len(options),
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        self.view.chosen = [v for v in self.values if v != "__none__"]
        await interaction.response.defer()

class P3PromotePermView(discord.ui.View):
    def __init__(self, guild_id, guild, invoker, role_name, all_roles, current):
        super().__init__(timeout=600)
        self.guild_id  = guild_id
        self.invoker   = invoker
        self.role_name = role_name
        self.chosen    = list(current)
        self.add_item(P3PromoteSelect(all_roles, current, role_name))

    @discord.ui.button(label="✅ Save", style=discord.ButtonStyle.green, row=1)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        if self.guild_id not in guild_configs:
            guild_configs[self.guild_id] = {}
        pp = guild_configs[self.guild_id].get("PROMOTE_PERMISSIONS", {})
        if self.chosen:
            pp[self.role_name] = self.chosen
        else:
            pp.pop(self.role_name, None)
        guild_configs[self.guild_id]["PROMOTE_PERMISSIONS"] = pp
        _save_guild_configs()
        v = P3View(self.guild_id, interaction.guild, self.invoker)
        await interaction.response.edit_message(embed=_p3_embed(self.guild_id, interaction.guild), view=v)

    @discord.ui.button(label="← Back", style=discord.ButtonStyle.grey, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        v = P3View(self.guild_id, interaction.guild, self.invoker)
        await interaction.response.edit_message(embed=_p3_embed(self.guild_id, interaction.guild), view=v)

class P3View(discord.ui.View):
    def __init__(self, guild_id: int, guild: discord.Guild, invoker: discord.Member):
        super().__init__(timeout=600)
        self.invoker  = invoker
        self.guild_id = guild_id
        self.add_item(P3RoleDropdown(guild_id, guild))

    @discord.ui.button(label="\u2b05\ufe0f Back", style=discord.ButtonStyle.grey, row=2)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message("\u274c Not your setup.", ephemeral=True); return
        v = P2View(self.guild_id, interaction.guild, 0, self.invoker)
        await interaction.response.edit_message(embed=_p2_embed(self.guild_id, interaction.guild, 0), view=v)

    @discord.ui.button(label="✅ Finish Setup", style=discord.ButtonStyle.blurple, row=2)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.invoker:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        gc            = guild_configs.get(self.guild_id, {})
        role_perms_v2 = gc.get("ROLE_PERMISSIONS_V2", {})
        promote_perms = gc.get("PROMOTE_PERMISSIONS", {})

        p1_lines = []
        for label, key, _ in START_STEPS:
            val = gc.get(key)
            p1_lines.append(("✅" if val else "⬜") + f"  {label}")

        perm_lines = []
        for rname, perms in role_perms_v2.items():
            perm_labels = [lbl for key, lbl in ALL_ROLE_PERMS if key in perms]
            perm_lines.append(f"✅  **{rname}**: " + ", ".join(perm_labels or ["*none*"]))

        promote_lines = []
        for rname, targets in promote_perms.items():
            promote_lines.append(f"✅  **{rname}** → " + ", ".join(targets))

        done_e = discord.Embed(
            title="✅  Server Setup Complete!",
            color=0x57F287, timestamp=datetime.utcnow(),
        )
        done_e.add_field(name="📌 Channels & Roles", value="\n".join(p1_lines)[:1000],                          inline=False)
        done_e.add_field(name="🎭 Role Permissions", value=("\n".join(perm_lines) or "*None set*")[:500],        inline=False)
        done_e.add_field(name="⬆️ Promote Perms",    value=("\n".join(promote_lines) or "*None set*")[:500],    inline=False)
        done_e.set_footer(text="eldorado.gg  ·  Run .start again to update any setting")
        await interaction.response.edit_message(embed=done_e, view=None)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

@bot.command(name="start")
@commands.has_permissions(administrator=True)
async def start_setup(ctx):
    """Interactive server setup wizard. Assigns all roles, channels, and permissions."""
    try:
        await ctx.message.delete()
    except Exception:
        pass
    gid   = ctx.guild.id
    total = (len(START_STEPS) + PAGE_SIZE - 1) // PAGE_SIZE
    intro_e = discord.Embed(
        title="⚙️  eldorado.gg — Server Setup",
        description=(
            "Welcome! This wizard configures the bot for **this server** in 3 phases:\n\n"
            "**Phase 1** — Assign channels, categories and key roles (log IDs, ticket categories, etc.)\n"
            "**Phase 2** — For each role, select what permissions it has: claim small/big/massive/index tickets, warn, ban\n"
            "**Phase 3** — For each role, select which roles it can promote/demote\n\n"
            f"Phase 1 has {len(START_STEPS)} settings across {total} pages. Any skipped setting uses the bot default."
        ),
        color=0x5865F2, timestamp=datetime.utcnow(),
    )
    intro_e.set_footer(text="eldorado.gg  ·  Admin only  ·  Times out in 10 min")
    await ctx.send(embed=intro_e)
    v = P1View(gid, 0, ctx.author)
    await ctx.send(embed=_p1_embed(gid, 0, total), view=v)

# ------------------------------------------------------------------------------
# Warn system
# ------------------------------------------------------------------------------

WARN_DB_FILE = "warn_data.json"

def load_warn_data() -> dict:
    try:
        if os.path.exists(WARN_DB_FILE):
            with open(WARN_DB_FILE, "r") as f:
                return {int(k): v for k, v in json.load(f).items()}
    except Exception as e:
        print(f"Error loading warn data: {e}")
    return {}

def save_warn_data(data: dict):
    try:
        with open(WARN_DB_FILE, "w") as f:
            json.dump({str(k): v for k, v in data.items()}, f, indent=2)
    except Exception as e:
        print(f"Error saving warn data: {e}")

warn_data: dict = load_warn_data()

def can_warn(member: discord.Member) -> bool:
    return _member_has_perm(member, "warn")

def _member_has_perm(member: discord.Member, perm_key: str) -> bool:
    """Check if a member has a specific ROLE_PERMISSIONS_V2 perm key."""
    if member.guild_permissions.administrator:
        return True
    gid      = member.guild.id
    perms_v2 = guild_configs.get(gid, {}).get("ROLE_PERMISSIONS_V2", {})
    if not perms_v2:
        return False
    for role in member.roles:
        if perm_key in perms_v2.get(role.name, []):
            return True
    return False

@bot.command(name="warn")
async def warn_user(ctx, target: discord.Member = None, *, reason: str = "No reason provided"):
    try:
        await ctx.message.delete()
    except:
        pass

    if not can_warn(ctx.author):
        await ctx.send("❌ You do not have permission to use this command.", delete_after=8)
        return

    if target is None:
        await ctx.send("❌ Usage: `$warn @user <reason>`", delete_after=8)
        return

    if target.bot:
        await ctx.send("❌ cannot warn a bot.", delete_after=8)
        return

    if target.id == ctx.author.id:
        await ctx.send("❌ cannot warn yourself.", delete_after=8)
        return

    entry = {
        "reason":  reason,
        "by":      ctx.author.id,
        "by_name": str(ctx.author),
        "at":      datetime.utcnow().isoformat(),
    }
    warn_data.setdefault(target.id, []).append(entry)
    save_warn_data(warn_data)

    total_warns = len(warn_data[target.id])

    e = discord.Embed(
        title=f"⚠️  Warning Issued",
        color=0xED4245,
        timestamp=datetime.utcnow(),
    )
    e.set_author(name=f"Warned by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    e.add_field(name="👤  User",        value=target.mention,      inline=True)
    e.add_field(name="🛡️  Warned By",   value=ctx.author.mention,  inline=True)
    e.add_field(name="📊  Total Warns", value=f"`{total_warns}`",   inline=True)
    e.add_field(name="📝  Reason",      value=reason,              inline=False)
    e.set_thumbnail(url=target.display_avatar.url)
    e.set_footer(text="eldorado.gg  ·  Warn System", icon_url=CONFIG["SERVER_ICON"])
    await ctx.send(embed=e)

    try:
        dm_e = discord.Embed(
            title=f"⚠️  You Have Received a Warning",
            description=f"You have received a warning in **{ctx.guild.name}**. Please review the server rules.",
            color=0xED4245,
            timestamp=datetime.utcnow(),
        )
        dm_e.add_field(name="📝  Reason",      value=reason,              inline=False)
        dm_e.add_field(name="🛡️  Warned By",   value=str(ctx.author),     inline=True)
        dm_e.add_field(name="📊  Total Warns", value=f"`{total_warns}`",   inline=True)
        dm_e.set_footer(text="eldorado.gg  ·  Warn System", icon_url=CONFIG["SERVER_ICON"])
        await target.send(embed=dm_e)
    except discord.Forbidden:
        pass

    lc = bot.get_channel(CONFIG["LOG_CHANNEL_ID"])
    if lc:
        await lc.send(embed=e)

@bot.command(name="warns")
async def check_warns(ctx, target: discord.Member = None):
    try:
        await ctx.message.delete()
    except:
        pass

    if not can_warn(ctx.author):
        await ctx.send("❌ You do not have permission to use this command.", delete_after=8)
        return

    if target is None:
        await ctx.send("❌ Usage: `$warns @user`", delete_after=8)
        return

    user_warns = warn_data.get(target.id, [])

    e = discord.Embed(
        title=f"⚠️  Warnings — {target.display_name}",
        color=0xED4245,
        timestamp=datetime.utcnow(),
    )
    e.set_author(name=target.display_name, icon_url=target.display_avatar.url)
    e.set_thumbnail(url=target.display_avatar.url)

    if not user_warns:
        e.description = f"{target.mention} has no warnings. ✅"
    else:
        e.description = f"{target.mention} has **{len(user_warns)}** warning(s)."
        for i, w in enumerate(user_warns, 1):
            ts = w.get("at", "Unknown")
            try:
                dt = datetime.fromisoformat(ts)
                ts_fmt = f"<t:{int(dt.timestamp())}:R>"
            except:
                ts_fmt = ts
            e.add_field(
                name=f"⚠️  #{i}  ·  {ts_fmt}",
                value=f"**Reason:** {w['reason']}\n**By:** {w.get('by_name', 'Unknown')}",
                inline=False,
            )

    e.set_footer(text="eldorado.gg  ·  Warn System", icon_url=CONFIG["SERVER_ICON"])
    await ctx.send(embed=e)

@bot.command(name="warnings")
async def my_warnings(ctx, target: discord.Member = None):
    """Check warnings for yourself or any user. Usage: .warnings [@user]"""
    if target is None:
        target = ctx.author

    user_warns = warn_data.get(target.id, [])
    total = len(user_warns)

    e = discord.Embed(
        title=f"⚠️  Warnings — {target.display_name}",
        color=0xED4245,
        timestamp=datetime.utcnow(),
    )
    e.set_author(name=target.display_name, icon_url=target.display_avatar.url)
    e.set_thumbnail(url=target.display_avatar.url)

    if not user_warns:
        e.description = f"{target.mention} has **no warnings** ✅ — clean record!"
    else:
        e.description = f"{target.mention} has **{total}** warning(s)."
        for i, w in enumerate(user_warns, 1):
            ts = w.get("at", "Unknown")
            try:
                dt = datetime.fromisoformat(ts)
                ts_fmt = f"<t:{int(dt.timestamp())}:R>"
            except:
                ts_fmt = ts
            e.add_field(
                name=f"⚠️  #{i}  ·  {ts_fmt}",
                value=f"**Reason:** {w['reason']}\n**Issued by:** {w.get('by_name', 'Unknown')}",
                inline=False,
            )

    e.set_footer(text="eldorado.gg  ·  Warn System", icon_url=CONFIG["SERVER_ICON"])
    await ctx.send(embed=e)

@bot.command(name="deletewarn", aliases=["delwarn", "removewarn"])
async def delete_warn(ctx, target: discord.Member = None, warn_num: int = None):
    try:
        await ctx.message.delete()
    except:
        pass

    if not can_warn(ctx.author):
        await ctx.send("❌ You do not have permission to use this command.", delete_after=8)
        return

    if target is None or warn_num is None:
        await ctx.send("❌ Usage: `$deletewarn @user <warn number>`\nRun `$warnings @user` to see warn numbers.", delete_after=10)
        return

    user_warns = warn_data.get(target.id, [])
    if not user_warns:
        await ctx.send(f"❌ {target.mention} has no warnings.", delete_after=8)
        return

    if warn_num < 1 or warn_num > len(user_warns):
        await ctx.send(f"❌ Invalid warn number. {target.mention} has **{len(user_warns)}** warning(s).", delete_after=10)
        return

    removed = user_warns.pop(warn_num - 1)
    warn_data[target.id] = user_warns
    save_warn_data(warn_data)

    e = discord.Embed(
        title=f"⚠️  Warning Removed",
        color=0x57F287,
        timestamp=datetime.utcnow(),
    )
    e.set_author(name=f"Removed by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    e.add_field(name="👤  User",          value=target.mention,                       inline=True)
    e.add_field(name="📊  Remaining",     value=f"`{len(user_warns)}` warning(s)",    inline=True)
    e.add_field(name="📝  Removed Warn",  value=removed.get("reason", "No reason"),   inline=False)
    e.add_field(name="🛡️  Originally By", value=removed.get("by_name", "Unknown"),    inline=True)
    e.set_thumbnail(url=target.display_avatar.url)
    e.set_footer(text="eldorado.gg  ·  Warn System", icon_url=CONFIG["SERVER_ICON"])
    await ctx.send(embed=e)

@bot.command(name="clearwarns")
async def clear_warns(ctx, target: discord.Member = None):
    try:
        await ctx.message.delete()
    except:
        pass

    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You do not have permission to use this command.", delete_after=8)
        return

    if target is None:
        await ctx.send("❌ Usage: `$clearwarns @user`", delete_after=8)
        return

    count = len(warn_data.pop(target.id, []))
    save_warn_data(warn_data)

    e = discord.Embed(
        title=f"✅  Warnings Cleared",
        description=f"Cleared **{count}** warning(s) from {target.mention}.",
        color=0x57F287,
        timestamp=datetime.utcnow(),
    )
    e.set_author(name=f"Action by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    e.set_footer(text="eldorado.gg  ·  Warn System", icon_url=CONFIG["SERVER_ICON"])
    await ctx.send(embed=e)

    lc = bot.get_channel(CONFIG["LOG_CHANNEL_ID"])
    if lc:
        await lc.send(embed=e)

# ------------------------------------------------------------------------------
# Role management
# ------------------------------------------------------------------------------

def get_guild_role_ids(guild_id: int) -> dict:
    if guild_id and guild_id in guild_configs:
        val = guild_configs[guild_id].get("ROLE_IDS")
        if val:
            return val
    return {}  # fallback to empty

def get_guild_role_permissions(guild_id: int) -> dict:
    if guild_id and guild_id in guild_configs:
        val = guild_configs[guild_id].get("PROMOTE_PERMISSIONS")
        if val:
            return val
        val = guild_configs[guild_id].get("ROLE_PERMISSIONS")
        if val:
            return val
    return {}

def get_manageable_roles(member: discord.Member) -> list[str]:
    gid        = member.guild.id
    role_ids   = get_guild_role_ids(gid)
    role_perms = get_guild_role_permissions(gid)
    manageable = set()
    for role in member.roles:
        if role.name in role_perms:
            manageable.update(role_perms[role.name])
    if member.guild_permissions.administrator:
        manageable.update(role_ids.keys())
    return sorted(manageable)

class ManageRolesRoleSelect(discord.ui.Select):
    def __init__(self, options_list: list[str], guild: discord.Guild = None):
        if not options_list and guild:
            options_list = [r.name for r in sorted(guild.roles, key=lambda x: x.position, reverse=True) if r.name != "@everyone"]
        options_list = options_list[:25]
        if not options_list:
            options_list = ["(no roles configured)"]
        options = [discord.SelectOption(label=r[:100], value=r[:100]) for r in options_list]
        super().__init__(
            placeholder="Select a role to add or remove...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="manageroles_role_select",
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_role = self.values[0]
        await interaction.response.defer()

class ManageRolesActionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Promote✅", value="promote", emoji="⬆️"),
            discord.SelectOption(label="Demote❌",  value="demote",  emoji="⬇️"),
        ]
        super().__init__(
            placeholder="Select an action...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="manageroles_action_select",
            row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_action = self.values[0]
        await interaction.response.defer()

class ManageRolesView(discord.ui.View):
    def __init__(self, manageable_roles: list[str], invoker: discord.Member, guild: discord.Guild = None):
        super().__init__(timeout=120)
        self.selected_role   = None
        self.selected_action = None
        self.invoker         = invoker
        self.add_item(ManageRolesRoleSelect(manageable_roles, guild=guild))
        self.add_item(ManageRolesActionSelect())

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅", row=3)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.invoker.id:
            await interaction.response.send_message("❌ You do not have permission to use this button.", ephemeral=True)
            return

        if not self.selected_role or not self.selected_action:
            await interaction.response.send_message("❌ Please select a role and an action.", ephemeral=True)
            return

        target_member = self.target_member
        if not target_member:
            await interaction.response.send_message("❌ Could not find that member.", ephemeral=True)
            return

        role_ids = get_guild_role_ids(interaction.guild.id)
        role_id = role_ids.get(self.selected_role)
        if not role_id:
            await interaction.response.send_message("❌ Role ID not configured for this role.", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message(f"❌ Could not find role `{self.selected_role}` in this server.", ephemeral=True)
            return

        try:
            if self.selected_action == "promote":
                if role in target_member.roles:
                    await interaction.response.send_message(f"❌ {target_member.mention} already has **{self.selected_role}**.", ephemeral=True)
                    return
                await target_member.add_roles(role, reason=f"Promoted by {interaction.user}")
                action_text = "promoted to"
                color = 0x00CC44
                emoji = "⬆️"
            else:
                if role not in target_member.roles:
                    await interaction.response.send_message(f"❌ {target_member.mention} does not have **{self.selected_role}**.", ephemeral=True)
                    return
                await target_member.remove_roles(role, reason=f"Demoted by {interaction.user}")
                action_text = "demoted from"
                color = 0xFF4444
                emoji = "⬇️"

            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)

            e = discord.Embed(
                title=f"{emoji} Role {'Promotion' if self.selected_action == 'promote' else 'Demotion'}",
                description=f"{target_member.mention} has been **{action_text}** **{self.selected_role}**.",
                color=color,
                timestamp=datetime.utcnow(),
            )
            e.set_author(name=f"Action by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
            e.add_field(name="🛡️  Staff",  value=interaction.user.mention, inline=True)
            e.add_field(name="👤  Target", value=target_member.mention,    inline=True)
            e.add_field(name="🎭  Role",   value=f"`{self.selected_role}`", inline=True)
            e.set_thumbnail(url=target_member.display_avatar.url)
            e.set_footer(text="eldorado.gg  ·  Role Management", icon_url=CONFIG["SERVER_ICON"])

            await interaction.response.send_message(embed=e)

            log_ch = bot.get_channel(CONFIG["LOG_CHANNEL_ID"])
            if log_ch:
                await log_ch.send(embed=e)

        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to manage that role.", ephemeral=True)
        except Exception as ex:
            await interaction.response.send_message(f"❌ Error: {ex}", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, emoji="❌", row=3)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.invoker.id:
            await interaction.response.send_message("❌ You do not have permission to use this button.", ephemeral=True)
            return
        for item in self.children:
            item.disabled = True
        cancelled_embed = discord.Embed(title="↩️  Cancelled", description="Role management cancelled.", color=0x2B2D31)
        cancelled_embed.set_footer(text="eldorado.gg  ·  No action taken", icon_url=CONFIG["SERVER_ICON"])
        await interaction.response.edit_message(embed=cancelled_embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

@bot.command(name="manageroles")
async def manageroles(ctx, *, user_input: str = None):
    try:
        await ctx.message.delete()
    except:
        pass

    try:
        manageable = get_manageable_roles(ctx.author)
    except Exception as e:
        print(f"[manageroles] get_manageable_roles error: {e}")
        manageable = []

    if not manageable:
        if ctx.author.guild_permissions.administrator or ctx.author == ctx.guild.owner:
            role_ids = get_guild_role_ids(ctx.guild.id)
            manageable = sorted(role_ids.keys())
        else:
            await ctx.send("❌ You do not have permission to use this command.", delete_after=8)
            return

    if not manageable:
        await ctx.send("❌ No roles configured yet. Run `$start` to set up the server first.", delete_after=8)
        return

    target_member = None
    if user_input:
        raw = user_input.strip()
        mention_match = re.fullmatch(r"<@!?(\d+)>", raw)
        uid_str = mention_match.group(1) if mention_match else raw
        try:
            uid = int(uid_str)
            target_member = ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
        except (ValueError, discord.NotFound, discord.HTTPException):
            pass

        if not target_member:
            raw_lower = raw.lower()
            for m in ctx.guild.members:
                if m.name.lower() == raw_lower or (m.nick and m.nick.lower() == raw_lower):
                    target_member = m
                    break

    e = discord.Embed(
        title="⚙️ Manage Roles",
        description=(
            f"**Target:** {target_member.mention if target_member else '`Not found — please re-run with a valid user ID or username`'}\n\n"
            "Use the dropdowns below to select the **role** and **action**, then press **Confirm**."
        ),
        color=0x2B6CB0,
        timestamp=datetime.utcnow(),
    )
    e.set_author(name=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    e.set_footer(text="eldorado.gg  ·  Role Management", icon_url=CONFIG["SERVER_ICON"])
    if target_member:
        e.set_thumbnail(url=target_member.display_avatar.url)

    if not target_member:
        await ctx.send(embed=e, delete_after=15)
        return

    view = ManageRolesView(manageable, invoker=ctx.author, guild=ctx.guild)
    view.target_member = target_member
    await ctx.send(embed=e, view=view)

# ------------------------------------------------------------------------------
# Partner / recruit
# ------------------------------------------------------------------------------

def _make_tag_happy_embed() -> discord.Embed:
    ticket_ch  = CONFIG.get("TICKET_OPEN_CHANNEL_ID") or 0
    pricing_ch = CONFIG.get("PRICING_CHANNEL_ID")     or 0
    rules_ch   = CONFIG.get("RULES_CHANNEL_ID")       or 0
    hits_ch    = CONFIG.get("HITS_CHANNEL_ID")        or 0

    def ch(cid): return f"<#{cid}>" if cid else "`(channel not configured)`"

    description = (
        "**Welcome to the team — we're glad you made the right choice.**\n\n"
        "**What is going on?**\n"
        "• The harsh truth is — you got **scammed** — you will most likely not get your stuff back. "
        "It's not the end of the world though, not by a long shot. You have now joined us, and can now "
        "BECOME a scammer — more commonly known as a hitter. Read the guide below on how to get started.\n\n"
        "**What do I do?**\n"
        "Advertise trades (can be fake crosstrades etc.) in other servers. Once a potential partner "
        "messages you, guide the conversation toward using a trusted middleman service. Once they agree, "
        f"invite them to our server and open a ticket in {ch(ticket_ch)}. Include your username "
        "and the details of the trade. A middleman will be assigned to assist.\n\n"
        "**How do I earn?**\n"
        "• After the trade is completed via middleman, the profit is split 50/50 between you and the "
        "middleman. The middleman determines the exact split, provided it remains fair.\n\n"
        "**How do I rank up?**\n"
        f"• Complete 10 trades to be eligible for Middleman promotion. All proof must be submitted in {ch(hits_ch)}.\n"
        "• Complete 5 alt hits to qualify for Head Middleman.\n"
        "• Additional rank upgrades are available through purchases or alternate trades. Pricing is "
        f"listed in {ch(pricing_ch)}.\n\n"
        "**Important reminders:**\n"
        f"• Review {ch(rules_ch)} regularly to stay in good standing.\n"
        "• Do NOT advertise in DMs — violations will result in a permanent ban.\n\n"
        f"What are you waiting for? Head over to {ch(hits_ch)}, and we wish you happy hitting!"
    )
    e = discord.Embed(title="eldorado.gg — Partner Guide", description=description, color=0x2B6CB0)
    e.set_footer(text="eldorado.gg  ·  Welcome", icon_url=CONFIG["SERVER_ICON"])
    return e

@bot.command(name="tag")
async def tag(ctx, name: str = None):
    if name is None: await ctx.send("❌ Usage: `$tag <n>`", delete_after=5); return
    if name.lower() == "happy":
        mm_role = ctx.guild.get_role(CONFIG["MIDDLEMAN_ROLE_ID"])
        if not ctx.author.guild_permissions.administrator and (not mm_role or mm_role not in ctx.author.roles):
            await ctx.send("❌ Only Middlemen can use this!", delete_after=5); await ctx.message.delete(); return
        await ctx.message.delete()
        await ctx.send(embed=_make_tag_happy_embed())
    else:
        await ctx.send(f"❌ Unknown tag: `{name}`", delete_after=5)

# ------------------------------------------------------------------------------
# Anti‑nuke system
# ------------------------------------------------------------------------------

ANTINUKE_ENABLED: bool = True
ANTINUKE_WHITELIST: set = set()
ANTINUKE_LOG_CHANNEL: int = CONFIG["LOG_CHANNEL_ID"]

ANTINUKE_THRESHOLDS: dict = {
    "channel_delete":    (2, 8),
    "channel_create":    (4, 8),
    "role_delete":       (2, 8),
    "role_create":       (4, 8),
    "ban":               (2, 8),
    "kick":              (2, 8),
    "webhook_create":    (3, 8),
    "webhook_delete":    (2, 8),
    "emoji_delete":      (4, 8),
    "sticker_delete":    (4, 8),
    "mention_everyone":  (2, 15),
    "channel_perms":     (3, 8),
    "member_timeout":    (3, 8),
    "thread_create":     (6, 8),
}

_an_action_log: dict = defaultdict(lambda: defaultdict(deque))
_an_punished: set = set()
_an_trigger_log: list = []
_an_snapshot: dict = {}
MAX_TRIGGER_LOG = 50

def _an_record(user_id: int, action: str) -> bool:
    if not ANTINUKE_ENABLED:
        return False
    if user_id in ANTINUKE_WHITELIST:
        return False
    if not user_id:
        return False
    limit, window = ANTINUKE_THRESHOLDS.get(action, (9999, 10))
    now = time.monotonic()
    q = _an_action_log[user_id][action]
    q.append(now)
    while q and q[0] < now - window:
        q.popleft()
    triggered = len(q) >= limit
    if triggered:
        _an_trigger_log.append((time.time(), user_id, action, f"{len(q)} {action} in {window}s"))
        if len(_an_trigger_log) > MAX_TRIGGER_LOG:
            _an_trigger_log.pop(0)
    return triggered

async def _an_get_actor(guild: discord.Guild, action: discord.AuditLogAction, target_id=None) -> int | None:
    try:
        async for entry in guild.audit_logs(limit=8, action=action):
            if target_id is None or (entry.target and getattr(entry.target, 'id', None) == target_id):
                if entry.user and entry.user.id not in ANTINUKE_WHITELIST and entry.user.id != guild.me.id:
                    return entry.user.id
    except Exception:
        pass
    return None

async def _an_alert(guild: discord.Guild, offender_id: int, reason: str, action: str):
    lc = bot.get_channel(ANTINUKE_LOG_CHANNEL)
    offender = guild.get_member(offender_id)
    name_str  = f"{offender} (`{offender_id}`)" if offender else f"`{offender_id}`"

    e = discord.Embed(
        title="🛡️  AntiNuke — 🚨 THREAT NEUTRALISED",
        color=0xFF0000,
        timestamp=datetime.utcnow(),
    )
    e.add_field(name="👤  Offender",   value=name_str,                              inline=True)
    e.add_field(name="⚠️  Trigger",    value=f"`{action}`",                         inline=True)
    e.add_field(name="📋  Detail",     value=reason,                                inline=False)
    e.add_field(name="🕐  Time",       value=f"<t:{int(time.time())}:F>",           inline=True)
    e.add_field(name="🔨  Action",     value="Roles stripped → **Banned**",         inline=True)
    if offender and offender.display_avatar:
        e.set_thumbnail(url=offender.display_avatar.url)
    e.set_footer(text="eldorado.gg  ·  AntiNuke v2", icon_url=CONFIG["SERVER_ICON"])

    try:
        if lc:
            await lc.send(embed=e)
    except Exception:
        pass

    try:
        if guild.owner:
            dm_e = discord.Embed(
                title="🚨  AntiNuke Alert — Your server was attacked!",
                description=f"**Server:** {guild.name}\n**Offender:** {name_str}\n**Reason:** {reason}\n\nThe attacker has been **banned** automatically.",
                color=0xFF0000,
                timestamp=datetime.utcnow(),
            )
            dm_e.set_footer(text="eldorado.gg  ·  AntiNuke v2")
            await guild.owner.send(embed=dm_e)
    except Exception:
        pass

async def _an_punish(guild: discord.Guild, offender_id: int, reason: str, action: str = "unknown"):
    if offender_id in _an_punished:
        return
    if offender_id in ANTINUKE_WHITELIST:
        return
    if offender_id == guild.me.id:
        return
    if guild.owner and offender_id == guild.owner.id:
        return

    _an_punished.add(offender_id)

    member = guild.get_member(offender_id)
    try:
        if member:
            safe = [r for r in member.roles if r.is_default()]
            try:
                await member.edit(roles=safe, reason=f"[AntiNuke] {reason}")
            except Exception:
                pass
            try:
                import datetime as _dt_inner
                until = _dt_inner.datetime.utcnow() + _dt_inner.timedelta(minutes=10)
                await member.timeout(until, reason="[AntiNuke] Nuker quarantine")
            except Exception:
                pass
        await guild.ban(
            discord.Object(id=offender_id),
            reason=f"[AntiNuke] {reason}"[:512],
            delete_message_days=0,
        )
    except discord.Forbidden:
        pass
    except Exception as ex:
        print(f"[AntiNuke] Punish error for {offender_id}: {ex}")

    await _an_alert(guild, offender_id, reason, action)

    await asyncio.sleep(90)
    _an_punished.discard(offender_id)

async def _an_snapshot_guild(guild: discord.Guild):
    channels = []
    for ch in guild.channels:
        try:
            channels.append({
                "name":        ch.name,
                "type":        str(ch.type),
                "position":    ch.position,
                "category_id": ch.category_id,
                "topic":       getattr(ch, 'topic', None),
            })
        except Exception:
            pass

    roles = []
    for r in guild.roles:
        if r.is_default():
            continue
        try:
            roles.append({
                "id":          r.id,
                "name":        r.name,
                "color":       r.color.value,
                "hoist":       r.hoist,
                "mentionable": r.mentionable,
                "position":    r.position,
                "permissions": r.permissions.value,
            })
        except Exception:
            pass

    members = {}
    for m in guild.members:
        try:
            role_ids = [r.id for r in m.roles if not r.is_default()]
            if role_ids:
                members[str(m.id)] = role_ids
        except Exception:
            pass

    _an_snapshot[guild.id] = {
        "channels":     channels,
        "roles":        roles,
        "members":      members,
        "snapped_at":   datetime.utcnow().isoformat(),
        "channel_count": len(channels),
        "role_count":    len(roles),
        "member_count":  len(members),
    }

async def _an_restore_guild(guild: discord.Guild, requester: discord.Member) -> tuple[int, int, int]:
    snap = _an_snapshot.get(guild.id)
    if not snap:
        return 0, 0, 0

    existing_channel_names = {c.name.lower() for c in guild.channels}
    existing_role_names    = {r.name.lower() for r in guild.roles}

    ch_restored    = 0
    role_restored  = 0
    members_rolled = 0

    old_id_to_new_role: dict[int, discord.Role] = {}

    for snap_role in snap["roles"]:
        existing = discord.utils.get(guild.roles, name=snap_role["name"])
        if existing:
            old_id_to_new_role[snap_role["id"]] = existing

    for r in sorted(snap["roles"], key=lambda x: x["position"]):
        if r["name"].lower() not in existing_role_names:
            try:
                new_role = await guild.create_role(
                    name=r["name"],
                    color=discord.Color(r["color"]),
                    hoist=r["hoist"],
                    mentionable=r["mentionable"],
                    permissions=discord.Permissions(r["permissions"]),
                    reason=f"[AntiNuke] Restore by {requester}",
                )
                old_id_to_new_role[r["id"]] = new_role
                role_restored += 1
                await asyncio.sleep(0.5)
            except Exception as ex:
                print(f"[AntiNuke] Role restore error: {ex}")

    for ch in sorted(snap["channels"], key=lambda x: x["position"]):
        if ch["name"].lower() not in existing_channel_names:
            try:
                cat = guild.get_channel(ch["category_id"]) if ch["category_id"] else None
                ch_type = ch["type"]
                if "text" in ch_type:
                    await guild.create_text_channel(
                        name=ch["name"], category=cat,
                        topic=ch.get("topic"),
                        reason=f"[AntiNuke] Restore by {requester}",
                    )
                elif "voice" in ch_type:
                    await guild.create_voice_channel(
                        name=ch["name"], category=cat,
                        reason=f"[AntiNuke] Restore by {requester}",
                    )
                elif "category" in ch_type:
                    await guild.create_category(
                        name=ch["name"],
                        reason=f"[AntiNuke] Restore by {requester}",
                    )
                ch_restored += 1
                await asyncio.sleep(0.5)
            except Exception as ex:
                print(f"[AntiNuke] Channel restore error: {ex}")

    member_snapshot = snap.get("members", {})
    for member_id_str, old_role_ids in member_snapshot.items():
        try:
            member = guild.get_member(int(member_id_str))
            if not member:
                continue
            current_role_ids = {r.id for r in member.roles}
            roles_to_add = []
            for old_rid in old_role_ids:
                new_role = old_id_to_new_role.get(old_rid)
                if new_role and new_role.id not in current_role_ids:
                    roles_to_add.append(new_role)
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason=f"[AntiNuke] Role restore by {requester}")
                members_rolled += 1
                await asyncio.sleep(0.3)
        except Exception as ex:
            print(f"[AntiNuke] Member re-role error ({member_id_str}): {ex}")

    return ch_restored, role_restored, members_rolled

# Antinuke event handlers
@bot.event
async def on_guild_channel_delete(channel):
    actor = await _an_get_actor(channel.guild, discord.AuditLogAction.channel_delete)
    if actor and _an_record(actor, "channel_delete"):
        asyncio.create_task(_an_punish(channel.guild, actor,
            f"Mass channel deletion — deleted #{channel.name}", "channel_delete"))

@bot.event
async def on_guild_channel_create(channel):
    actor = await _an_get_actor(channel.guild, discord.AuditLogAction.channel_create)
    if actor and _an_record(actor, "channel_create"):
        asyncio.create_task(_an_punish(channel.guild, actor,
            f"Channel bomb — created #{channel.name}", "channel_create"))
        try:
            await channel.delete(reason="[AntiNuke] Channel bomb cleanup")
        except Exception:
            pass

@bot.event
async def on_guild_role_delete(role):
    actor = await _an_get_actor(role.guild, discord.AuditLogAction.role_delete)
    if actor and _an_record(actor, "role_delete"):
        asyncio.create_task(_an_punish(role.guild, actor,
            f"Mass role deletion — deleted @{role.name}", "role_delete"))

@bot.event
async def on_guild_role_create(role):
    actor = await _an_get_actor(role.guild, discord.AuditLogAction.role_create)
    if actor and _an_record(actor, "role_create"):
        asyncio.create_task(_an_punish(role.guild, actor,
            f"Role bomb — created @{role.name}", "role_create"))
        try:
            await role.delete(reason="[AntiNuke] Role bomb cleanup")
        except Exception:
            pass

@bot.event
async def on_member_ban(guild, user):
    actor = await _an_get_actor(guild, discord.AuditLogAction.ban, target_id=user.id)
    if actor and actor != guild.me.id and _an_record(actor, "ban"):
        asyncio.create_task(_an_punish(guild, actor,
            f"Mass ban — banned {user}", "ban"))

@bot.event
async def on_member_remove(member):
    guild = member.guild
    actor = await _an_get_actor(guild, discord.AuditLogAction.kick, target_id=member.id)
    if actor and actor != guild.me.id and _an_record(actor, "kick"):
        asyncio.create_task(_an_punish(guild, actor,
            f"Mass kick — kicked {member}", "kick"))

@bot.event
async def on_webhooks_update(channel):
    guild = channel.guild
    for audit_action, key, label in [
        (discord.AuditLogAction.webhook_create, "webhook_create", "webhook spam"),
        (discord.AuditLogAction.webhook_delete, "webhook_delete", "mass webhook deletion"),
    ]:
        actor = await _an_get_actor(guild, audit_action)
        if actor and _an_record(actor, key):
            asyncio.create_task(_an_punish(guild, actor,
                f"Mass {label} in #{channel.name}", key))

@bot.event
async def on_guild_emojis_update(guild, before, after):
    if len(after) < len(before):
        actor = await _an_get_actor(guild, discord.AuditLogAction.emoji_delete)
        if actor and _an_record(actor, "emoji_delete"):
            asyncio.create_task(_an_punish(guild, actor,
                f"Mass emoji deletion ({len(before)-len(after)} deleted)", "emoji_delete"))

@bot.event
async def on_guild_stickers_update(guild, before, after):
    if len(after) < len(before):
        actor = await _an_get_actor(guild, discord.AuditLogAction.sticker_delete)
        if actor and _an_record(actor, "sticker_delete"):
            asyncio.create_task(_an_punish(guild, actor,
                f"Mass sticker deletion ({len(before)-len(after)} deleted)", "sticker_delete"))

@bot.event
async def on_member_join(member):
    if not member.bot:
        return
    guild = member.guild
    actor = await _an_get_actor(guild, discord.AuditLogAction.bot_add, target_id=member.id)
    if not actor or actor in ANTINUKE_WHITELIST:
        return
    await asyncio.sleep(2)
    fresh = guild.get_member(member.id)
    if fresh and fresh.guild_permissions.administrator:
        asyncio.create_task(_an_punish(guild, actor,
            f"Added admin bot {member} ({member.id})", "bot_add_admin"))
        try:
            await guild.kick(member, reason="[AntiNuke] Unauthorised admin bot removed")
        except Exception:
            pass

@bot.event
async def on_guild_update(before, after):
    actor = await _an_get_actor(after, discord.AuditLogAction.guild_update)
    if not actor or actor in ANTINUKE_WHITELIST:
        return
    changes = []
    if before.name != after.name:
        changes.append(f"name changed to `{after.name}`")
    if before.icon != after.icon and after.icon is None:
        changes.append("icon wiped")
    if hasattr(before, 'banner') and before.banner != after.banner and getattr(after, 'banner', None) is None:
        changes.append("banner wiped")
    if changes:
        recent_nukes = sum(
            len(_an_action_log[actor].get(k, deque()))
            for k in ("channel_delete", "role_delete", "ban", "kick")
        )
        if recent_nukes >= 1:
            asyncio.create_task(_an_punish(after, actor,
                "Server update during nuke attack: " + ", ".join(changes), "guild_update"))

@bot.event
async def on_guild_role_update(before, after):
    if after.permissions.administrator and not before.permissions.administrator:
        actor = await _an_get_actor(after.guild, discord.AuditLogAction.role_update)
        if actor and actor not in ANTINUKE_WHITELIST and actor != after.guild.me.id:
            asyncio.create_task(_an_punish(after.guild, actor,
                f"Granted Administrator permission to role @{after.name}", "role_perm_admin"))

@bot.event
async def on_guild_channel_update(before, after):
    if not hasattr(after, 'overwrites'):
        return
    actor = await _an_get_actor(after.guild, discord.AuditLogAction.overwrite_update)
    if actor and _an_record(actor, "channel_perms"):
        asyncio.create_task(_an_punish(after.guild, actor,
            f"Mass channel permission override on #{after.name}", "channel_perms"))

@bot.event
async def on_thread_create(thread):
    actor = await _an_get_actor(thread.guild, discord.AuditLogAction.thread_create)
    if actor and _an_record(actor, "thread_create"):
        asyncio.create_task(_an_punish(thread.guild, actor,
            f"Thread bomb — created #{thread.name}", "thread_create"))
        try:
            await thread.delete(reason="[AntiNuke] Thread bomb cleanup")
        except Exception:
            pass

@bot.event
async def on_member_update(before, after):
    if after.timed_out_until and not before.timed_out_until:
        actor = await _an_get_actor(after.guild, discord.AuditLogAction.member_update, target_id=after.id)
        if actor and actor != after.guild.me.id and _an_record(actor, "member_timeout"):
            asyncio.create_task(_an_punish(after.guild, actor,
                f"Mass timeout (mute-nuke) — timed out {after}", "member_timeout"))

# Antinuke command
@bot.command(name="antinuke")
@commands.has_permissions(administrator=True)
async def antinuke_cmd(ctx, action: str = "status", sub: str = None):
    global ANTINUKE_ENABLED
    try:
        await ctx.message.delete()
    except Exception:
        pass
    action = action.lower()

    if action == "on":
        ANTINUKE_ENABLED = True
        e = discord.Embed(title="🛡️  AntiNuke Enabled",
                          description="AntiNuke v2 is now **fully active** and monitoring all events.",
                          color=0x57F287, timestamp=datetime.utcnow())
    elif action == "off":
        ANTINUKE_ENABLED = False
        e = discord.Embed(title="⚠️  AntiNuke Disabled",
                          description="⚠️ AntiNuke is **off**. Your server is **unprotected**!",
                          color=0xED4245, timestamp=datetime.utcnow())
    elif action == "whitelist":
        if not sub or not ctx.message.mentions:
            await ctx.send("❌ Usage: `$antinuke whitelist <add|remove> @user`", delete_after=8)
            return
        uid = ctx.message.mentions[0].id
        if sub.lower() == "add":
            ANTINUKE_WHITELIST.add(uid)
            e = discord.Embed(title="🛡️  Whitelist — Added",
                              description=f"<@{uid}> is now **whitelisted** and will never be punished.",
                              color=0x57F287, timestamp=datetime.utcnow())
        else:
            ANTINUKE_WHITELIST.discard(uid)
            e = discord.Embed(title="🛡️  Whitelist — Removed",
                              description=f"<@{uid}> has been **removed** from the whitelist.",
                              color=0xED4245, timestamp=datetime.utcnow())
    elif action == "threshold":
        args = ctx.message.content.split()
        if len(args) < 5:
            lines = "\n".join(f"`{k}` — **{v[0]}** per **{v[1]}s**" for k, v in ANTINUKE_THRESHOLDS.items())
            e = discord.Embed(title="🛡️  AntiNuke Thresholds", description=lines,
                              color=0x5865F2, timestamp=datetime.utcnow())
            e.set_footer(text="Usage: .antinuke threshold <action> <count> <seconds>")
        else:
            key, count, secs = args[2], args[3], args[4]
            if key not in ANTINUKE_THRESHOLDS:
                await ctx.send(f"❌ Unknown action `{key}`. Valid: {', '.join(ANTINUKE_THRESHOLDS)}", delete_after=10)
                return
            ANTINUKE_THRESHOLDS[key] = (int(count), int(secs))
            e = discord.Embed(title="🛡️  Threshold Updated",
                              description=f"`{key}` → **{count}** actions per **{secs}s**",
                              color=0x57F287, timestamp=datetime.utcnow())
    elif action == "restore":
        snap = _an_snapshot.get(ctx.guild.id)
        if not snap:
            await ctx.send("❌ No snapshot available for this server. Restart the bot to take one.", delete_after=10)
            return
        member_count = len(snap.get("members", {}))
        msg = await ctx.send(f"🔄 Restoring channels, roles, and re-assigning roles to **{member_count}** member(s)... This may take a while.")
        ch_r, role_r, mem_r = await _an_restore_guild(ctx.guild, ctx.author)
        await _an_snapshot_guild(ctx.guild)
        e = discord.Embed(
            title="🛡️  Restore Complete",
            description=(
                f"✅  **{ch_r}** channel(s) restored\n"
                f"✅  **{role_r}** role(s) recreated\n"
                f"✅  **{mem_r}** member(s) re-assigned their roles\n\n"
                "Snapshot has been refreshed."
            ),
            color=0x57F287, timestamp=datetime.utcnow(),
        )
        try:
            await msg.delete()
        except Exception:
            pass
    elif action == "logs":
        if not _an_trigger_log:
            e = discord.Embed(title="🛡️  AntiNuke Logs",
                              description="No triggers recorded yet — server is clean ✅",
                              color=0x57F287, timestamp=datetime.utcnow())
        else:
            lines = []
            for ts, uid, act, detail in reversed(_an_trigger_log[-15:]):
                dt = datetime.utcfromtimestamp(ts).strftime("%m/%d %H:%M:%S")
                lines.append(f"`{dt}` <@{uid}> — `{act}` — {detail}")
            e = discord.Embed(title=f"🛡️  AntiNuke Logs — Last {min(15, len(_an_trigger_log))} Triggers",
                              description="\n".join(lines),
                              color=0xED4245, timestamp=datetime.utcnow())
    elif action == "snapshot":
        msg = await ctx.send("📸 Taking fresh snapshot...")
        await _an_snapshot_guild(ctx.guild)
        snap = _an_snapshot[ctx.guild.id]
        try:
            await msg.delete()
        except Exception:
            pass
        e = discord.Embed(title="📸  Snapshot Taken",
                          description=f"Captured **{snap['channel_count']}** channels, **{snap['role_count']}** roles, and **{snap.get('member_count', 0)}** members' role assignments.",
                          color=0x57F287, timestamp=datetime.utcnow())
    else:
        wl = ", ".join(f"<@{u}>" for u in ANTINUKE_WHITELIST) or "`None`"
        snap = _an_snapshot.get(ctx.guild.id, {})
        snapped = snap.get("snapped_at", "Never")[:19] if snap else "Never"
        thresh_lines = "\n".join(f"`{k}` — **{v[0]}** per **{v[1]}s**" for k, v in ANTINUKE_THRESHOLDS.items())
        e = discord.Embed(
            title="🛡️  AntiNuke v2 — Status Dashboard",
            color=0x57F287 if ANTINUKE_ENABLED else 0xED4245,
            timestamp=datetime.utcnow(),
        )
        e.add_field(name="🔒  Status",      value="✅ **Active**" if ANTINUKE_ENABLED else "❌ **Disabled**", inline=True)
        e.add_field(name="🚨  Triggers",    value=f"`{len(_an_trigger_log)}` total",  inline=True)
        e.add_field(name="📸  Snapshot",    value=f"`{snapped} UTC`",                 inline=True)
        e.add_field(name="🤍  Whitelist",   value=wl,                                 inline=False)
        e.add_field(name="📊  Thresholds",  value=thresh_lines,                       inline=False)
        e.add_field(name="📌  Commands",
                    value="`$antinuke on/off` `$antinuke whitelist add/remove @user`\n"
                          "`$antinuke threshold <action> <count> <secs>` `$antinuke restore`\n"
                          "`$antinuke logs` `$antinuke snapshot`",
                    inline=False)

    e.set_footer(text="eldorado.gg  ·  AntiNuke v2", icon_url=CONFIG["SERVER_ICON"])
    await ctx.send(embed=e, delete_after=60)

# ------------------------------------------------------------------------------
# Mass DM
# ------------------------------------------------------------------------------

class MassDMModal(discord.ui.Modal, title="Mass DM — Compose Message"):
    message = discord.ui.TextInput(
        label="Message",
        placeholder="Enter the message to send to all members with the selected role...",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=1800,
    )

    def __init__(self, role: discord.Role):
        super().__init__()
        self.role = role

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        role    = self.role
        message = self.message.value
        guild   = interaction.guild

        members = [m for m in role.members if not m.bot]
        if not members:
            await interaction.followup.send(f"❌ No non-bot members found with role **{role.name}**.", ephemeral=True)
            return

        confirm_e = discord.Embed(
            title="📨  Mass DM — Sending",
            description=f"Sending to **{len(members)}** member(s) with role {role.mention}...",
            color=0x5865F2,
            timestamp=datetime.utcnow(),
        )
        confirm_e.set_footer(text="eldorado.gg  ·  Mass DM", icon_url=CONFIG["SERVER_ICON"])
        await interaction.followup.send(embed=confirm_e, ephemeral=True)

        sent = failed = 0
        for member in members:
            try:
                dm_e = discord.Embed(
                    description=message,
                    color=0x5865F2,
                    timestamp=datetime.utcnow(),
                )
                dm_e.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
                dm_e.set_footer(text="eldorado.gg  ·  Staff Message", icon_url=CONFIG["SERVER_ICON"])
                await member.send(embed=dm_e)
                sent += 1
                await asyncio.sleep(0.5)
            except Exception:
                failed += 1

        result_e = discord.Embed(
            title="📨  Mass DM — Complete",
            color=0x57F287,
            timestamp=datetime.utcnow(),
        )
        result_e.add_field(name="🎯  Role",    value=role.mention,    inline=True)
        result_e.add_field(name="✅  Sent",    value=f"{sent}",     inline=True)
        result_e.add_field(name="❌  Failed",  value=f"{failed}",   inline=True)
        result_e.add_field(name="📝  Message", value=message[:512],   inline=False)
        result_e.set_footer(text="eldorado.gg  ·  Mass DM", icon_url=CONFIG["SERVER_ICON"])
        await interaction.followup.send(embed=result_e, ephemeral=True)

        lc = bot.get_channel(CONFIG["LOG_CHANNEL_ID"])
        if lc:
            log_e = discord.Embed(
                title="📨  Mass DM Sent",
                color=0x5865F2,
                timestamp=datetime.utcnow(),
            )
            log_e.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            log_e.add_field(name="🎯  Role",    value=role.mention,             inline=True)
            log_e.add_field(name="✅  Sent",    value=f"{sent}",              inline=True)
            log_e.add_field(name="❌  Failed",  value=f"{failed}",            inline=True)
            log_e.add_field(name="👤  Sent By", value=interaction.user.mention,  inline=True)
            log_e.add_field(name="📝  Message", value=message[:512],            inline=False)
            log_e.set_footer(text=f"eldorado.gg  ·  ID: {interaction.user.id}", icon_url=CONFIG["SERVER_ICON"])
            await lc.send(embed=log_e)

class MassDMRoleSelect(discord.ui.RoleSelect):
    def __init__(self, invoker_id: int):
        super().__init__(
            placeholder="Select a role to mass DM...",
            min_values=1,
            max_values=1,
            row=0,
        )
        self.invoker_id = invoker_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message("❌ Only the person who ran this command can use it.", ephemeral=True)
            return
        role = self.values[0]
        await interaction.response.send_modal(MassDMModal(role=role))

class MassDMView(discord.ui.View):
    def __init__(self, invoker_id: int):
        super().__init__(timeout=120)
        self.add_item(MassDMRoleSelect(invoker_id=invoker_id))

@bot.command(name="massdm")
async def mass_dm(ctx):
    try:
        await ctx.message.delete()
    except:
        pass

    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You do not have permission to use this command.", delete_after=8)
        return

    e = discord.Embed(
        title="📨  Mass DM",
        description=(
            "**Step 1 —** Select the role whose members you want to DM.\n"
            "**Step 2 —** Type your message in the popup.\n\n"
            "The message will be sent as an embed to every non-bot member with the selected role."
        ),
        color=0x5865F2,
        timestamp=datetime.utcnow(),
    )
    e.set_footer(text="eldorado.gg  ·  Mass DM  ·  Admin only", icon_url=CONFIG["SERVER_ICON"])
    await ctx.send(embed=e, view=MassDMView(invoker_id=ctx.author.id))

# ------------------------------------------------------------------------------
# Demote / Restore (temporary role stripping)
# ------------------------------------------------------------------------------

_role_backup: dict[int, list[int]] = {}

def _get_configured_staff_roles(guild: discord.Guild) -> list[discord.Role]:
    gid = guild.id
    role_ids: dict = guild_configs.get(gid, {}).get("ROLE_IDS", {})
    roles = []
    seen = set()
    for rid in role_ids.values():
        if rid and rid not in seen:
            role = guild.get_role(int(rid))
            if role:
                roles.append(role)
                seen.add(rid)
    return roles

@bot.command(name="demote")
async def demote_to_hitter(ctx, target: discord.Member = None):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    if target is None:
        target = ctx.author
    elif target != ctx.author and not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Only admins can demote other members.", delete_after=8)
        return

    if target.guild_permissions.administrator:
        await ctx.send("❌ Cannot demote an administrator.", delete_after=8)
        return

    staff_roles = _get_configured_staff_roles(ctx.guild)
    staff_role_ids = {r.id for r in staff_roles}
    roles_to_strip = [r for r in target.roles if r.id in staff_role_ids]

    if not roles_to_strip:
        await ctx.send(
            f"❌ {'You have' if target == ctx.author else f'{target.mention} has'} no configured staff roles to demote from.",
            delete_after=8
        )
        return

    _role_backup[target.id] = [r.id for r in roles_to_strip]

    try:
        await target.remove_roles(*roles_to_strip, reason=f"[Demote] by {ctx.author}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to modify that member's roles.", delete_after=8)
        return

    stripped_names = ", ".join(f"`{r.name}`" for r in roles_to_strip)
    self_action = target == ctx.author

    whose        = "Your" if self_action else f"{target.mention}'s"
    verb         = "you are" if self_action else "they are"
    restore_hint = "$restore" if self_action else "$restore @user"
    author_label = "Self-demote" if self_action else f"Demoted by {ctx.author.display_name}"
    e = discord.Embed(
        title="⬇️  Roles Temporarily Removed",
        description=(
            f"{whose} staff roles have been stripped.\n\n"
            f"Run `{restore_hint}` to reinstate them."
        ),
        color=0xED4245,
        timestamp=datetime.utcnow(),
    )
    e.set_author(name=author_label, icon_url=ctx.author.display_avatar.url)
    e.set_thumbnail(url=target.display_avatar.url)
    e.add_field(name="💾  Roles Saved", value=stripped_names, inline=False)
    e.set_footer(text="eldorado.gg  ·  Temporary Demotion", icon_url=CONFIG["SERVER_ICON"])
    await ctx.send(embed=e)

    if not self_action:
        log_ch = bot.get_channel(CONFIG["STAFF_CHAT_ID"])
        if log_ch:
            le = discord.Embed(title="⬇️  Temporary Demotion", color=0xED4245, timestamp=datetime.utcnow())
            le.add_field(name="👤  Member",     value=target.mention,     inline=True)
            le.add_field(name="🛡️  By",         value=ctx.author.mention, inline=True)
            le.add_field(name="💾  Roles Saved", value=stripped_names,    inline=False)
            le.set_footer(text="eldorado.gg  ·  Use $restore to reinstate", icon_url=CONFIG["SERVER_ICON"])
            await log_ch.send(embed=le)

@bot.command(name="restore")
async def restore_roles(ctx, target: discord.Member = None):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    if target is None:
        target = ctx.author
    elif target != ctx.author and not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Only admins can restore other members.", delete_after=8)
        return

    saved_ids = _role_backup.get(target.id)
    if not saved_ids:
        msg = "You don't" if target == ctx.author else f"{target.mention} doesn't"
        await ctx.send(f"❌ {msg} have any roles saved. Use `$demote` first.", delete_after=10)
        return

    roles_to_restore = [ctx.guild.get_role(r) for r in saved_ids if ctx.guild.get_role(r)]

    if not roles_to_restore:
        await ctx.send("❌ The saved roles no longer exist in this server.", delete_after=8)
        _role_backup.pop(target.id, None)
        return

    try:
        await target.add_roles(*roles_to_restore, reason=f"[Restore] by {ctx.author}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to modify that member's roles.", delete_after=8)
        return

    _role_backup.pop(target.id, None)

    restored_names = ", ".join(f"`{r.name}`" for r in roles_to_restore)
    self_action = target == ctx.author

    whose_r      = "Your" if self_action else f"{target.mention}'s"
    author_label_r = "Self-restore" if self_action else f"Restored by {ctx.author.display_name}"
    e = discord.Embed(
        title="⬆️  Roles Restored",
        description=f"{whose_r} staff roles have been reinstated.",
        color=0x57F287,
        timestamp=datetime.utcnow(),
    )
    e.set_author(name=author_label_r, icon_url=ctx.author.display_avatar.url)
    e.set_thumbnail(url=target.display_avatar.url)
    e.add_field(name="✅  Roles Reinstated", value=restored_names, inline=False)
    e.set_footer(text="eldorado.gg  ·  Role Restoration", icon_url=CONFIG["SERVER_ICON"])
    await ctx.send(embed=e)

    if not self_action:
        log_ch = bot.get_channel(CONFIG["STAFF_CHAT_ID"])
        if log_ch:
            le = discord.Embed(title="⬆️  Role Restoration", color=0x57F287, timestamp=datetime.utcnow())
            le.add_field(name="👤  Member",      value=target.mention,     inline=True)
            le.add_field(name="🛡️  By",          value=ctx.author.mention, inline=True)
            le.add_field(name="✅  Roles Given",  value=restored_names,     inline=False)
            le.set_footer(text="eldorado.gg  ·  Role Restoration", icon_url=CONFIG["SERVER_ICON"])
            await log_ch.send(embed=le)

# ------------------------------------------------------------------------------
# Enhanced $confirmtrade (trade confirmation with buttons)
# ------------------------------------------------------------------------------

class ConfirmTradeView(discord.ui.View):
    def __init__(self, trader1: discord.Member, trader2: discord.Member, middleman: discord.Member, trade_desc: str):
        super().__init__(timeout=300)
        self.trader1    = trader1
        self.trader2    = trader2
        self.middleman  = middleman
        self.trade_desc = trade_desc
        self.confirmed  = set()
        self.denied     = False

    async def _update(self, interaction: discord.Interaction):
        t1_status = "✅" if self.trader1.id in self.confirmed else "⏳"
        t2_status = "✅" if self.trader2.id in self.confirmed else "⏳"

        e = discord.Embed(
            title="🤝  Trade Confirmation",
            description=(
                f"**Trade:** {self.trade_desc}\n\n"
                f"{t1_status}  {self.trader1.mention}\n"
                f"{t2_status}  {self.trader2.mention}\n\n"
                "*Both traders must confirm to proceed.*"
            ),
            color=0xF1C40F if len(self.confirmed) < 2 else 0x57F287,
            timestamp=datetime.utcnow(),
        )
        e.set_footer(text="eldorado.gg  ·  Trade Confirmation — expires in 5 min", icon_url=CONFIG["SERVER_ICON"])

        if len(self.confirmed) == 2:
            e.title = "✅  Trade Confirmed!"
            e.description = (
                f"**Trade:** {self.trade_desc}\n\n"
                f"✅  {self.trader1.mention}\n"
                f"✅  {self.trader2.mention}\n\n"
                f"Both traders have confirmed. **{self.middleman.mention}** may proceed."
            )
            e.color = 0x57F287
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(embed=e, view=self)
        else:
            await interaction.response.edit_message(embed=e, view=self)

    @discord.ui.button(label="✅ Confirm Trade", style=discord.ButtonStyle.green, row=0)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.trader1.id, self.trader2.id):
            await interaction.response.send_message("❌ Only the two traders can confirm this trade.", ephemeral=True); return
        if interaction.user.id in self.confirmed:
            await interaction.response.send_message("✅ You already confirmed.", ephemeral=True); return
        self.confirmed.add(interaction.user.id)
        await self._update(interaction)

    @discord.ui.button(label="❌ Deny Trade", style=discord.ButtonStyle.red, row=0)
    async def deny_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.trader1.id, self.trader2.id):
            await interaction.response.send_message("❌ Only the two traders can deny this trade.", ephemeral=True); return
        self.denied = True
        e = discord.Embed(
            title="❌  Trade Denied",
            description=(
                f"{interaction.user.mention} has **denied** the trade.\n\n"
                f"**Trade:** {self.trade_desc}\n\n"
                f"The trade has been cancelled. Please contact your middleman."
            ),
            color=0xED4245,
            timestamp=datetime.utcnow(),
        )
        e.set_footer(text="eldorado.gg  ·  Trade Confirmation", icon_url=CONFIG["SERVER_ICON"])
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=e, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

@bot.command(name="confirmtrade", aliases=["ctrade", "tradconfirm", "confirm2"])
async def confirm_trade(ctx, trader1: discord.Member = None, trader2: discord.Member = None, *, trade_desc: str = "No description provided"):
    try:
        await ctx.message.delete()
    except:
        pass

    if trader1 is None or trader2 is None:
        await ctx.send("❌ Usage: `$confirmtrade @trader1 @trader2 <description>`", delete_after=8)
        return

    if trader1 == trader2:
        await ctx.send("❌ Both traders must be different users.", delete_after=8)
        return

    e = discord.Embed(
        title="🤝  Trade Confirmation Required",
        description=(
            f"**Trade Details:** {trade_desc}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳  {trader1.mention}\n"
            f"⏳  {trader2.mention}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Both traders must confirm below before the middleman proceeds. "
            "If either party denies, the trade will be cancelled immediately."
        ),
        color=0xF1C40F,
        timestamp=datetime.utcnow(),
    )
    e.add_field(name="🛡️  Middleman", value=ctx.author.mention, inline=True)
    e.add_field(name="⏱️  Expires", value="5 minutes", inline=True)
    e.set_thumbnail(url=CONFIG["SERVER_ICON"])
    e.set_footer(text="eldorado.gg  ·  Trade Confirmation", icon_url=CONFIG["SERVER_ICON"])

    view = ConfirmTradeView(trader1=trader1, trader2=trader2, middleman=ctx.author, trade_desc=trade_desc)
    await ctx.send(content=f"{trader1.mention} {trader2.mention}", embed=e, view=view)

# ------------------------------------------------------------------------------
# Additional $mminfo (enhanced)
# ------------------------------------------------------------------------------

@bot.command(name="mminfo2")
async def mminfo2(ctx):
    """Explains how the middleman process works."""
    try:
        await ctx.message.delete()
    except:
        pass

    e = discord.Embed(
        title="🛡️  How Middlemanning Works",
        description=(
            "A middleman is a **trusted, neutral third party** who steps in between two traders "
            "to make sure the exchange is 100% safe for both sides. Here's exactly what happens:\n\u200b"
        ),
        color=0x5865F2,
        timestamp=datetime.utcnow(),
    )

    e.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━\n📦  Step 1 — Trader 1 Sends Their Item",
        value=(
            "Trader 1 hands over their item/payment to the middleman first. "
            "Nothing moves forward until this is received and verified.\n\u200b"
        ),
        inline=False,
    )
    e.add_field(
        name="📦  Step 2 — Trader 2 Sends Their Item",
        value=(
            "Once the middleman has confirmed Trader 1's item, Trader 2 sends theirs. "
            "Both items are now safely held by the middleman.\n\u200b"
        ),
        inline=False,
    )
    e.add_field(
        name="🔁  Step 3 — The Exchange",
        value=(
            "The middleman delivers Trader 1's item to Trader 2, and Trader 2's item to Trader 1. "
            "Both parties receive what was agreed — simultaneously and securely.\n\u200b"
        ),
        inline=False,
    )
    e.add_field(
        name="✅  Step 4 — Trade Complete",
        value=(
            "Both traders confirm receipt. The middleman logs the completed trade. "
            "You're done — safely and scam-free.\n\u200b"
        ),
        inline=False,
    )
    e.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━\n🔒  Why is it safe?",
        value=(
            "• Neither trader ever has to trust the other directly\n"
            "• The middleman **never** releases an item until both sides have delivered\n"
            "• All trades are logged and transcribed\n"
            "• Our middlemen are verified, trained, and held accountable"
        ),
        inline=False,
    )

    e.set_thumbnail(url=CONFIG["SERVER_ICON"])
    e.set_image(url=CONFIG["SERVER_BANNER"])
    e.set_footer(text="eldorado.gg  ·  Safe. Trusted. Professional.", icon_url=CONFIG["SERVER_ICON"])
    await ctx.send(embed=e)

# ------------------------------------------------------------------------------
# Updated on_ready to add persistent views and snapshots
# ------------------------------------------------------------------------------

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is now online!")
    print(f"Bot ID: {bot.user.id}")
    print(f"Discord.py Version: {discord.__version__}")

    # Add persistent views from first bot
    bot.add_view(OpenTicketView())
    bot.add_view(TicketControlView())
    bot.add_view(ConfirmView())
    bot.add_view(FeeView())
    bot.add_view(HittingView())

token = os.getenv("TOKEN")

if not token:
    raise ValueError("TOKEN environment variable not set")

bot.run(token)

