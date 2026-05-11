import discord
from discord.ext import commands
import random
import os

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

balances = {}

def get_balance(user):
    if user not in balances:
        balances[user] = 1000
    return balances[user]

def casino_embed(title, description):
    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.red()
    )

@bot.event
async def on_ready():
    print(f"Casino Bot is online as {bot.user}")

# 💰 BALANCE
@bot.command()
async def balance(ctx):
    bal = get_balance(ctx.author.id)
    embed = casino_embed(
        "💰 Balance",
        f"{ctx.author.mention}, you have **{bal} coins**"
    )
    await ctx.send(embed=embed)

# 🎲 COINFLIP
@bot.command()
async def coinflip(ctx, amount: int, choice: str):
    bal = get_balance(ctx.author.id)

    if amount <= 0:
        await ctx.send(embed=casino_embed("❌ Error", "Bet must be greater than 0"))
        return

    if amount > bal:
        await ctx.send(embed=casino_embed("❌ Error", "Not enough coins"))
        return

    result = random.choice(["heads", "tails"])

    if choice.lower() == result:
        balances[ctx.author.id] += amount
        embed = casino_embed(
            "🎲 Coinflip - Win",
            f"Result: **{result}**\nYou won **+{amount} coins** 💰"
        )
    else:
        balances[ctx.author.id] -= amount
        embed = casino_embed(
            "🎲 Coinflip - Lose",
            f"Result: **{result}**\nYou lost **-{amount} coins** ❌"
        )

    await ctx.send(embed=embed)

# 🎰 SLOTS
@bot.command()
async def slots(ctx, amount: int):
    bal = get_balance(ctx.author.id)

    if amount <= 0:
        await ctx.send(embed=casino_embed("❌ Error", "Bet must be greater than 0"))
        return

    if amount > bal:
        await ctx.send(embed=casino_embed("❌ Error", "Not enough coins"))
        return

    symbols = ["🍒", "🍋", "🍉", "⭐"]
    result = [random.choice(symbols) for _ in range(3)]

    if result[0] == result[1] == result[2]:
        win = amount * 3
        balances[ctx.author.id] += win
        embed = casino_embed(
            "🎰 Slots - JACKPOT",
            f"{' '.join(result)}\nYou won **+{win} coins** 💰"
        )
    else:
        balances[ctx.author.id] -= amount
        embed = casino_embed(
            "🎰 Slots - Lose",
            f"{' '.join(result)}\nYou lost **-{amount} coins** ❌"
        )

    await ctx.send(embed=embed)

bot.run(os.getenv("TOKEN"))