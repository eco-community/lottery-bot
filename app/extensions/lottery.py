import logging
import asyncio

from discord import Embed
from discord.ext import commands, tasks
from tortoise.expressions import F
from tortoise.query_utils import Q
from tortoise.functions import Count
from tortoise import exceptions, timezone
from tortoise.transactions import in_transaction

import config
from constants import ROLES_CAN_CONTROL_BOT
from app.models import Lottery, User
from app.exceptions import BlockAlreadyMinedException
from app.utils import get_eta_to_block, select_winning_tickets, get_hash_for_block, pp_points
from app.constants import LotteryStatus, STOP_SALES_BEFORE_START_IN_SEC, BLOCK_CONFIRMATIONS, GREEN, GOLD


@commands.has_any_role(*ROLES_CAN_CONTROL_BOT)
@commands.command(aliases=["new", "create"])
async def new_lottery(
    ctx,
    name: str,
    strike_eth_block: int,
    ticket_price: int = None,
    ticket_min_number: int = None,
    ticket_max_number: int = None,
):
    # parse args
    lottery = Lottery(name=name, strike_eth_block=strike_eth_block)
    if ticket_price is not None:
        lottery.ticket_price = ticket_price
    if ticket_min_number is not None:
        lottery.ticket_min_number = ticket_min_number
    if ticket_max_number is not None:
        lottery.ticket_max_number = ticket_max_number
    # get eta to block
    try:
        lottery.strike_date_eta = await get_eta_to_block(strike_eth_block)
    except BlockAlreadyMinedException:
        # block has already passed
        return await ctx.send(
            f"{ctx.author.mention}, error, block `{strike_eth_block}` already passed, choose a different block"
        )
    # save lottery
    try:
        await lottery.save()
    except exceptions.IntegrityError:
        return await ctx.send(f"{ctx.author.mention}, error, lottery `{name}` already exists, choose a different name")
    await ctx.send(
        f"{ctx.author.mention}, success! Created lottery `{lottery}`, will strike at {lottery.strike_date_eta:%Y-%m-%d %H:%M} UTC"  # noqa: E501
    )


@new_lottery.error
async def new_lottery_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send(
            f'{ctx.author.mention}, wrong syntax, ```!lottery.new "[lottery name]" [ethereum block] [ticket price](optional) [ticket min number](optional) [ticket max number](optional)```'  # noqa: E501
        )


@commands.command(aliases=["view"])
async def view_lottery(ctx, *, name):
    name = name.replace('"', "")
    lottery = (
        await Lottery.filter(name=name)
        .prefetch_related("tickets")
        .annotate(total_tickets=Count("tickets"))
        .get_or_none(name=name)
    )
    if not lottery:
        return await ctx.send(f"{ctx.author.mention}, error, lottery `{name}` doesn't exist")
    widget = Embed(description=f"{lottery.name} information", color=GREEN, title=f"{lottery.name}")
    widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
    widget.add_field(name="Ticket price:", value=f"{int(lottery.ticket_price)}", inline=False)
    widget.add_field(
        name="Strike ETH block:",
        value=f"[{lottery.strike_eth_block}](<https://etherscan.io/block/{lottery.strike_eth_block}>)",
        inline=False,
    )  # noqa: E501
    widget.add_field(name="Status:", value=f"{lottery.status}", inline=False)
    widget.add_field(name="Min ticket number:", value=f"{lottery.ticket_min_number}", inline=False)
    widget.add_field(name="Max ticket number:", value=f"{lottery.ticket_max_number}", inline=False)
    widget.add_field(
        name="Tickets left:", value=f"{lottery.possible_tickets_count - lottery.total_tickets}", inline=False
    )
    widget.add_field(
        name="Winning tickets:",
        value=f"{', '.join(map(str, lottery.winning_tickets)) if lottery.winning_tickets else '-'}",
        inline=False,
    )
    widget.add_field(
        name="Strike Date (estimated):",
        value=f"[{lottery.strike_date_eta:%Y-%m-%d %H:%M} UTC](<https://etherscan.io/block/countdown/{lottery.strike_eth_block}>)",  # noqa: E501
        inline=False,
    )
    await ctx.send(content=ctx.author.mention, embed=widget)


@view_lottery.error
async def view_lottery_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send(f"{ctx.author.mention}, wrong syntax, ```!lottery.view [lottery name]```")


@commands.command(aliases=["list", "active"])
async def lotteries(ctx):
    lotteries_list = await Lottery.exclude(status=LotteryStatus.ENDED)
    if not lotteries_list:
        return await ctx.send(f"{ctx.author.mention}, we don't have any active lotteries")
    widget = Embed(description="List of all lotteries", color=GREEN, title="All lotteries")
    widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
    for lottery in lotteries_list:
        widget.add_field(
            name=lottery.name,
            value=f"Ticket price {pp_points(lottery.ticket_price)}<:points:819648258112225316>",
            inline=False,
        )
    await ctx.send(content=ctx.author.mention, embed=widget)


class LotteryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lock = asyncio.Lock()
        self.lottery_status_cron_job.start()

    async def _handle_stopping_sales(self) -> None:
        """Handle stopping sales for started lotteries if strike date is close enough"""
        started_lotteries = await Lottery.filter(status=LotteryStatus.STARTED)
        stop_sales_for_lotteries_ids = []
        for lottery in started_lotteries:
            total_seconds_to_lottery = (lottery.strike_date_eta - timezone.now()).total_seconds()
            if total_seconds_to_lottery < STOP_SALES_BEFORE_START_IN_SEC:
                # change lottery status to LotteryStatus.STOP_SALES
                stop_sales_for_lotteries_ids.append(lottery.id)
        if stop_sales_for_lotteries_ids:
            # bulk change lotteries to LotteryStatus.STOP_SALES
            await Lottery.filter(id__in=stop_sales_for_lotteries_ids).update(status=LotteryStatus.STOP_SALES)
            logging.debug(f":::lottery_cron: Stopped selling tickets for: {stop_sales_for_lotteries_ids}")
        return None

    async def _handle_selecting_winning_tickets(self) -> None:
        """Handle selecting winning tickets for lottery

        Note: we will also ensure that lottery.strike_eth_block has required number of confirmations (aka block depth)
        """
        stop_sales_lotteries = await Lottery.filter(status=LotteryStatus.STOP_SALES)
        for lottery in stop_sales_lotteries:
            # check if block was mined with required number of confirmations
            try:
                await get_eta_to_block(lottery.strike_eth_block + BLOCK_CONFIRMATIONS)
                # block hasn't been mined yet
            except BlockAlreadyMinedException:
                # block has been mined, we could select winning ticket numbers
                block_hash = await get_hash_for_block(lottery.strike_eth_block)
                lottery.winning_tickets = await select_winning_tickets(
                    hash=block_hash,
                    min_number=lottery.ticket_min_number,
                    max_number=lottery.ticket_max_number,
                )
                lottery.status = LotteryStatus.STRIKED
                await lottery.save(update_fields=["winning_tickets", "status", "modified_at"])
                logging.debug(f":::lottery_cron: Selected winning tickets for: {lottery.id}")
        return None

    async def _handle_payments_to_winners(self) -> None:
        """Handle payments for winning tickets

        We will check if users have tickets with winning numbers, if they don't lottery points will
        be added to the total winning pool for the next lottery
        """
        striked_lotteries = await Lottery.filter(status=LotteryStatus.STRIKED).prefetch_related("tickets")
        notification_channel = self.bot.get_channel(config.LOTTERY_CHANNEL_ID)
        bulk_save_has_winners = []
        bulk_save_no_winners = []
        for lottery in striked_lotteries:
            # check if lottery has winning tickets
            winners_ids = set()
            for ticket in lottery.tickets:
                if ticket.ticket_number in lottery.winning_tickets:
                    winners_ids.add(ticket.user_id)
                    logging.debug(f":::lottery_cron: Winner for lottery: {lottery.name} is: {ticket.user_id}")
            # process winners
            if winners_ids:
                bulk_save_has_winners.append(lottery.id)
                # get winning pool for the current lottery
                lottery_pool = len(lottery.tickets) * lottery.ticket_price
                # get winning pool for past lotteries without winners (aka with 'ended' status and has_winners="False")
                qs = (
                    await Lottery.filter(Q(status=LotteryStatus.ENDED) & Q(has_winners=False))
                    .prefetch_related("tickets")
                    .annotate(total_tickets=Count("tickets"))
                )
                # TODO: waiting for response to rewrite this into orm
                # https://github.com/tortoise/tortoise-orm/issues/683
                old_winning_pool = sum([_.total_tickets * _.ticket_price for _ in qs])
                total_winning_pool = old_winning_pool + lottery_pool
                # share winning pool equally between winners
                winner_share = total_winning_pool / len(winners_ids)
                await User.filter(id__in=winners_ids).update(balance=F("balance") + winner_share)
                # remove old winning pool (because it was paid to the winners)
                if old_winning_pool:
                    await Lottery.filter(Q(status=LotteryStatus.ENDED) & Q(has_winners=False)).update(has_winners=True)
                winners_mentions = [f"<@!{_}>" for _ in winners_ids]
                winners_mentions_str = ", ".join(winners_mentions)
            else:
                bulk_save_no_winners.append(lottery.id)
            widget = Embed(
                description=f"`{lottery.name}` striked",
                color=GOLD,
                title=lottery.name,
            )
            widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
            widget.add_field(
                name="Winning tickets:",
                value=f"`{', '.join(map(str, lottery.winning_tickets))}`",
                inline=False,
            )
            if winners_ids:
                widget.add_field(name="Winners:", value=winners_mentions_str, inline=False)
                # send notification to the channel
                await notification_channel.send(content=winners_mentions_str, embed=widget)
            else:
                widget.add_field(
                    name="Winners:",
                    value="Nobody won the lottery, winning pool will be added to the next lottery",
                    inline=False,
                )
                # send notification to the channel
                await notification_channel.send(embed=widget)
        # bulk change lotteries to LotteryStatus.ENDED
        if bulk_save_has_winners:
            await Lottery.filter(id__in=bulk_save_has_winners).update(status=LotteryStatus.ENDED, has_winners=True)
        if bulk_save_no_winners:
            await Lottery.filter(id__in=bulk_save_no_winners).update(status=LotteryStatus.ENDED)
        return None

    @tasks.loop(seconds=config.CHECK_LOTTERY_STATUS_SECONDS)
    async def lottery_status_cron_job(self):
        # ensure that only one instance of job is running, other instances will be discarded
        if not self.lock.locked():
            await self.lock.acquire()
            try:
                async with in_transaction():
                    await self._handle_stopping_sales()
                    await self._handle_selecting_winning_tickets()
                    await self._handle_payments_to_winners()
            finally:
                self.lock.release()

    @lottery_status_cron_job.before_loop
    async def before_check_lottery_status(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_command(new_lottery)
    bot.add_command(view_lottery)
    bot.add_command(lotteries)
    bot.add_cog(LotteryCog(bot))
