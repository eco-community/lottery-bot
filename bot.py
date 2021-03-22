import logging

from discord import Intents
from tortoise import Tortoise
from discord.ext import commands
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

import config
from constants import SENTRY_ENV_NAME, TORTOISE_ORM
from app.utils import use_sentry


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


if __name__ == "__main__":
    bot.load_extension("app.commands.lottery")
    bot.load_extension("app.commands.tickets")
    bot.load_extension("app.commands.wallet")
    bot.load_extension("app.commands.common")
    bot.loop.run_until_complete(Tortoise.init(config=TORTOISE_ORM))
    bot.run(config.TOKEN)
