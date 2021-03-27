import random
from typing import List
from datetime import datetime, timedelta, timezone

import aiohttp
import sentry_sdk
from discord.ext import commands

import config
from app.models import User
from app.exceptions import BlockAlreadyMinedException


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

    Raises: BlockAlreadyMinedException if block already passed
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.etherscan.io/api?module=block&action=getblockcountdown&blockno={block}&apikey={config.ETHERSCAN_API_KEY}"  # noqa: E501
        ) as response:
            try:
                response_json = await response.json()
                eta_in_seconds = int(float(response_json["result"]["EstimateTimeInSec"]))
                strike_date_eta = datetime.now(tz=timezone.utc) + timedelta(seconds=eta_in_seconds)
                return strike_date_eta
            except TypeError:
                raise BlockAlreadyMinedException()


async def get_hash_for_block(block: int) -> str:
    """Function which will get block hash for block

    Returns:
        block hash
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.blockcypher.com/v1/eth/main/blocks/{block}") as response:
            block_info = await response.json()
            return block_info["hash"]


async def select_winning_tickets(
    hash: str,
    min_number: int,
    max_number: int,
    number_of_winning_tickets: int = 1,
) -> List[int]:
    """Function will act as VRF (https://en.wikipedia.org/wiki/Verifiable_random_function)

    Args:
        hash (str): block hash, will be used as seed for verifiable randomness
        min_number (int): start of the range
        max_number (int): end of the range for generating winning numbers for tickets
        number_of_winning_tickets (int): number of winning tickets

    Example:
        select_winning_tickets("hash", 1, 10) will generate numbers between 1 and 10

    Returns:
        list of winning ticket numbers
    """

    vrf_random = random.Random(hash)
    return vrf_random.sample(range(min_number, max_number), number_of_winning_tickets)
