import random
from typing import List
from decimal import Decimal
from datetime import datetime, timedelta, timezone

import aiohttp
import sentry_sdk
from tortoise.functions import Count
from tortoise.query_utils import Q
from discord.ext import commands
from discord_slash.utils.manage_commands import create_option, create_choice

import config
from app.models import User, Lottery
from app.constants import LotteryStatus
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
            (
                commands.MissingRole,
                commands.MissingAnyRole,
                commands.BadArgument,
                commands.MissingRequiredArgument,
                commands.errors.CommandNotFound,
            ),
        ):
            raise error


def pp_points(balance: Decimal) -> str:
    """Pretty print points"""
    str_balance = f"{balance:.1f}"
    suffix = ".0"
    # backport from Python 3.9 https://docs.python.org/3/library/stdtypes.html#str.removesuffix
    if suffix and str_balance.endswith(suffix):
        return str_balance[: -len(suffix)]
    else:
        return str_balance[:]


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
        block_hex = hex(block)
        async with session.get(
            f"https://api.etherscan.io/api?module=proxy&action=eth_getBlockByNumber&tag={block_hex}&boolean=true&apikey={config.ETHERSCAN_API_KEY}"  # noqa: E501
        ) as response:
            block_info = await response.json()
            return block_info["result"]["hash"]


async def get_old_winning_pool() -> int:
    """Return winning pool for past lotteries without winners (aka with 'ended' status and has_winners="False")"""
    qs = (
        await Lottery.filter(Q(status=LotteryStatus.ENDED) & Q(has_winners=False))
        .prefetch_related("tickets")
        .annotate(total_tickets=Count("tickets"))
    )
    # TODO: waiting for response to rewrite this into orm
    # https://github.com/tortoise/tortoise-orm/issues/683
    return sum([_.total_tickets * _.ticket_price for _ in qs])


async def register_view_lottery_command(bot, cmd) -> None:
    """Dirty hack to register options on fly for view_lottery command"""
    lotteries = await Lottery.all().order_by("-created_at").limit(10)
    try:
        # force sync_commands to detect new changes and sync slash commands with Discord
        del bot.slash.subcommands["sweepstake"]["view"]
    except KeyError:
        pass
    bot.slash.add_subcommand(
        cmd=cmd,
        base="sweepstake",
        name="view",
        description="Display sweepstake information",
        guild_ids=config.GUILD_IDS,
        options=[
            create_option(
                name="name",
                description="choose sweepstake",
                option_type=3,
                required=True,
                choices=[create_choice(name=_.name, value=_.name) for _ in lotteries],
            )
        ],
    )
    return None


async def register_buy_ticket_command(bot, cmd) -> None:
    """Dirty hack to register options on fly for buy_ticket command"""
    lotteries = await Lottery.filter(status=LotteryStatus.STARTED).order_by("-created_at").limit(10)
    try:
        # force sync_commands to detect new changes and sync slash commands with Discord
        del bot.slash.subcommands["sweepstake"]["buy"]
    except KeyError:
        pass
    bot.slash.add_subcommand(
        cmd=cmd,
        base="sweepstake",
        name="buy",
        description="Buy ticket",
        guild_ids=config.GUILD_IDS,
        options=[
            create_option(
                name="name",
                description="choose sweepstake",
                option_type=3,
                required=True,
                choices=[create_choice(name=_.name, value=_.name) for _ in lotteries],
            )
        ],
    )
    return None


async def register_my_tickets_command(bot, cmd) -> None:
    """Dirty hack to register options on fly for my_tickets command"""
    lotteries = await Lottery.all().order_by("-created_at").limit(10)
    try:
        # force sync_commands to detect new changes and sync slash commands with Discord
        del bot.slash.subcommands["sweepstake"]["tickets"]
    except KeyError:
        pass
    bot.slash.add_subcommand(
        cmd=cmd,
        base="sweepstake",
        name="tickets",
        description="My tickets",
        guild_ids=config.GUILD_IDS,
        options=[
            create_option(
                name="name",
                description="choose sweepstake",
                option_type=3,
                required=True,
                choices=[create_choice(name=_.name, value=_.name) for _ in lotteries],
            )
        ],
    )
    return None


async def reload_options_hack(bot) -> None:
    """dirty hack to fake dynamic loading of choices in slash commands"""
    await register_view_lottery_command(bot, bot.cogs["LotteryCog"].view_lottery)
    await register_buy_ticket_command(bot, bot.cogs["TicketCog"].buy_ticket)
    await register_my_tickets_command(bot, bot.cogs["TicketCog"].my_tickets)
    bot.reload_extension("app.extensions.lottery")


def select_winning_tickets(
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
    # make range to behave as inclusive range, this way ticket with max_number could be won
    return vrf_random.sample(range(min_number, max_number + 1), number_of_winning_tickets)


def select_winning_tickets_guaranteed(
    hash: str,
    ticket_numbers: list,
    number_of_winning_tickets: int = 1,
) -> List[int]:
    """Function will act as VRF (https://en.wikipedia.org/wiki/Verifiable_random_function)

    Args:
        hash (str): block hash, will be used as seed for verifiable randomness
        ticket_numbers (list): list of ticket numbers
        number_of_winning_tickets (int): number of winning tickets

    Example:
        select_winning_tickets_guaranteed("hash", [1, 2, 99], 10) will select winning ticket from three tickets

    Returns:
        list of winning ticket numbers
    """

    vrf_random = random.Random(hash)
    if len(ticket_numbers) >= number_of_winning_tickets:
        return vrf_random.sample(ticket_numbers, number_of_winning_tickets)
    else:
        return ticket_numbers
