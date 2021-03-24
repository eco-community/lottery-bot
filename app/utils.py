from datetime import datetime, timedelta, timezone

import aiohttp
import sentry_sdk
from discord.ext import commands

from app.models import User
import config


def use_sentry(client, **sentry_args):
    """
    Use this compatibility library as a bridge between Discord and Sentry.
    Arguments:
        client: The Discord client object (e.g. `discord.AutoShardedClient`).
        sentry_args: Keyword arguments to pass to the Sentry SDK.
    """

    sentry_sdk.init(**sentry_args)

    @client.event
    async def on_error(event, *args, **kwargs):
        """Don't ignore the error, causing Sentry to capture it."""
        raise

    @client.event
    async def on_command_error(msg, error):
        # don't report errors to sentry related to wrong permissions
        if not isinstance(
            error,
            (commands.MissingRole, commands.MissingAnyRole, commands.BadArgument, commands.MissingRequiredArgument),
        ):
            raise error


async def ensure_registered(user_id: int) -> User:
    """Ensure that user is registered in our database"""

    user, _ = await User.get_or_create(id=user_id)
    return user


async def get_eta_to_block(block: int) -> datetime:
    """Get ETA to block

    Raises: KeyError if block already passed
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.etherscan.io/api?module=block&action=getblockcountdown&blockno={block}&apikey={config.ETHERSCAN_API_KEY}"  # noqa: E501
        ) as response:

            response_json = await response.json()
            eta_in_seconds = int(float(response_json["result"]["EstimateTimeInSec"]))
            strike_date_eta = datetime.now(tz=timezone.utc) + timedelta(seconds=eta_in_seconds)
            return strike_date_eta
