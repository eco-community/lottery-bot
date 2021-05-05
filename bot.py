import logging

from discord import Intents, Activity, ActivityType
from tortoise import Tortoise
from discord.ext import commands
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from discord_slash import SlashCommand

import config
from constants import SENTRY_ENV_NAME, TORTOISE_ORM
from app.utils import use_sentry


if __name__ == "__main__":
    # initialize bot params
    intents = Intents.default()
    intents.members = True
    activity = Activity(type=ActivityType.playing, name="ECO lottery")
    bot = commands.Bot(command_prefix="!lottery.", help_command=None, intents=intents, activity=activity)
    SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True, override_type=True)

    # init sentry SDK
    use_sentry(
        bot,
        dsn=config.SENTRY_API_KEY,
        environment=SENTRY_ENV_NAME,
        integrations=[AioHttpIntegration()],
    )

    # setup logger
    logging.basicConfig(
        filename="eco-lottery.log",
        level=logging.getLevelName(config.LOG_LEVEL),
        format="%(asctime)s %(levelname)s:%(message)s",
    )
    bot.load_extension("app.extensions.lottery")
    bot.load_extension("app.extensions.tickets")
    bot.load_extension("app.extensions.wallet")
    bot.load_extension("app.extensions.common")
    bot.loop.run_until_complete(Tortoise.init(config=TORTOISE_ORM))
    bot.run(config.TOKEN)
