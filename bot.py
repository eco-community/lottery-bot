import logging

from discord import Intents, Embed
from tortoise import Tortoise, exceptions
from discord.ext import commands
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

import config
from constants import SENTRY_ENV_NAME, ROLES_CAN_CONTROL_BOT
from utils import use_sentry
from models import Lottery


# initialize bot params
intents = Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="$lottery.", help_command=None, intents=intents)


# init sentry SDK
use_sentry(
    bot,
    dsn=config.SENTRY_API_KEY,
    environment=SENTRY_ENV_NAME,
    integrations=[AioHttpIntegration()],
)

# setup logger
logging.basicConfig(filename="eco-lottery.log", level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")
bot.remove_command(help)


@commands.has_any_role(*ROLES_CAN_CONTROL_BOT)
@bot.command("help")
async def help(ctx):
    widget = Embed(description="Available commands for ECO Lottery Bot", color=0x03D692, title="Help")
    widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
    widget.add_field(name="$lottery.new_lottery", value="`Create a new lottery`", inline=False)
    widget.add_field(name="$lottery.view_lottery", value="`Display lottery information`", inline=False)
    await ctx.send(embed=widget)


@commands.has_any_role(*ROLES_CAN_CONTROL_BOT)
@bot.command("new_lottery")
async def new_lottery(ctx, name: str, strike_eth_block: int, ticket_price: int):
    if ticket_price:
        lottery = Lottery(name=name, strike_eth_block=strike_eth_block, ticket_price=ticket_price)
    else:
        lottery = Lottery(name=name, strike_eth_block=strike_eth_block)
    try:
        await lottery.save()
    except exceptions.IntegrityError:
        return await ctx.send(f"Error, lottery `{name}` already exists, choose a different name")
    await ctx.send(f"Success! Created lottery: `{lottery}`")


@new_lottery.error
async def new_lottery_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("Wrong syntax, ```$lottery.new_lottery 'LOTTERY NAME' STRIKE_ETH_BLOCK TICKET_PRICE(OPTIONAL)```")  # noqa: E501


@commands.has_any_role(*ROLES_CAN_CONTROL_BOT)
@bot.command("view_lottery")
async def view_lottery(ctx, name: str):
    lottery = await Lottery.get_or_none(name=name)
    if not lottery:
        return await ctx.send(f"Error, lottery `{name}` doesn't exist")
    widget = Embed(description=f"{lottery.name} information", color=0x03D692, title=f"{lottery.name}")
    widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
    widget.add_field(name="Ticket price:", value=f"{int(lottery.ticket_price)}", inline=False)
    widget.add_field(name="Strike ETH block:", value=f"{lottery.strike_eth_block}", inline=False)
    await ctx.send(embed=widget)


@view_lottery.error
async def view_lottery_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("Wrong syntax, ```$lottery.view_lottery 'LOTTERY NAME'```")


if __name__ == "__main__":
    bot.loop.run_until_complete(Tortoise.init(db_url="sqlite://db.sqlite3", modules={"models": ["models"]}))
    bot.loop.run_until_complete(Tortoise.generate_schemas())
    bot.run(config.TOKEN)
