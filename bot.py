import logging

from discord import Intents
from tortoise import Tortoise
from discord.ext import commands
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

import config
from constants import SENTRY_ENV_NAME, ROLES_CAN_CONTROL_BOT, GUILD_INDEX
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
@bot.command("ping")
async def help(ctx):
    lottery = Lottery(name="New Tournament", ticket_price=19, strike_eth_block=424242)
    await lottery.save()
    await ctx.send("pong from lottery")


if __name__ == "__main__":
    bot.loop.run_until_complete(Tortoise.init(db_url="sqlite://db.sqlite3", modules={"models": ["models"]}))
    bot.loop.run_until_complete(Tortoise.generate_schemas())
    bot.run(config.TOKEN)
