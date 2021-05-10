import logging
import asyncio

from discord import Embed
from discord.utils import find
from discord.ext import commands, tasks
from tortoise.expressions import F
from tortoise.query_utils import Q
from tortoise.functions import Count
from tortoise import exceptions, timezone
from tortoise.transactions import in_transaction
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option
from discord_slash.model import SlashCommandOptionType

import config
from constants import ROLES_CAN_CONTROL_BOT
from app.models import Lottery, User
from app.exceptions import BlockAlreadyMinedException
from app.utils import (
    get_eta_to_block,
    select_winning_tickets,
    get_hash_for_block,
    pp_points,
    get_old_winning_pool,
    register_view_lottery_command,
    reload_options_hack,
)
from app.constants import LotteryStatus, STOP_SALES_BEFORE_START_IN_SEC, BLOCK_CONFIRMATIONS, GREEN, GOLD


class LotteryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lock = asyncio.Lock()
        self.lottery_status_cron_job.start()
        self.bot.loop.create_task(register_view_lottery_command(self.bot, self.view_lottery))

    def cog_unload(self):
        self.lottery_status_cron_job.cancel()

    @cog_ext.cog_slash(
        name="new_lottery",
        guild_ids=config.GUILD_IDS,
        description="Create a new lottery",
        options=[
            create_option(
                name="name",
                description="Lottery name",
                option_type=SlashCommandOptionType.STRING,
                required=True,
            ),
            create_option(
                name="eth_block",
                description="Lottery strike block",
                option_type=SlashCommandOptionType.INTEGER,
                required=True,
            ),
            create_option(
                name="price",
                description="Ticket price (default 10)",
                option_type=SlashCommandOptionType.INTEGER,
                required=False,
            ),
            create_option(
                name="min_num",
                description="Ticket min number (default 10000)",
                option_type=SlashCommandOptionType.INTEGER,
                required=False,
            ),
            create_option(
                name="max_num",
                description="Ticket max number (default 99000)",
                option_type=SlashCommandOptionType.INTEGER,
                required=False,
            ),
            create_option(
                name="number_of_winning_tickets",
                description="Number of winning tickets (default 1)",
                option_type=SlashCommandOptionType.INTEGER,
                required=False,
            ),
        ],
    )
    async def new_lottery(
        self,
        ctx: SlashContext,
        name: str,
        eth_block: int,
        price: int = None,
        min_num: int = None,
        max_num: int = None,
        number_of_winning_tickets: int = None,
    ):
        can_control_bot = find(lambda _: _.name in ROLES_CAN_CONTROL_BOT, ctx.author.roles)
        if not can_control_bot:
            return await ctx.send(f"{ctx.author.mention}, I’m sorry but I can’t do that for you.")
        # parse args
        lottery = Lottery(name=name, strike_eth_block=eth_block)
        if price is not None:
            lottery.ticket_price = price
        if min_num is not None:
            lottery.ticket_min_number = min_num
        if max_num is not None:
            lottery.ticket_max_number = max_num
        if number_of_winning_tickets is not None:
            lottery.number_of_winning_tickets = number_of_winning_tickets
        # get eta to block
        try:
            lottery.strike_date_eta = await get_eta_to_block(eth_block)
        except BlockAlreadyMinedException:
            # block has already passed
            return await ctx.send(
                f"{ctx.author.mention}, error, block `{eth_block}` already passed, choose a different block"
            )
        # save lottery
        try:
            await lottery.save()
        except exceptions.IntegrityError:
            return await ctx.send(
                f"{ctx.author.mention}, error, lottery `{name}` already exists, choose a different name"
            )
        await ctx.send(
            f"{ctx.author.mention}, success! Created lottery `{lottery}`, will strike at {lottery.strike_date_eta:%Y-%m-%d %H:%M} UTC"  # noqa: E501
        )
        await reload_options_hack(ctx.bot)

    async def view_lottery(self, ctx: SlashContext, name: str):
        lottery = (
            await Lottery.all().prefetch_related("tickets").annotate(total_tickets=Count("tickets")).get(name=name)
        )
        widget = Embed(description=f"{lottery.name} information", color=GREEN, title=f"{lottery.name}")
        widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
        widget.add_field(
            name="Ticket price:",
            value=f"{pp_points(lottery.ticket_price)}<:points:819648258112225316>",
            inline=False,
        )
        widget.add_field(
            name="Strike Date (estimated):",
            value=f"[{lottery.strike_date_eta:%Y-%m-%d %H:%M} UTC](<https://etherscan.io/block/countdown/{lottery.strike_eth_block}>)",  # noqa: E501
            inline=False,
        )
        widget.add_field(
            name="Tickets left:", value=f"{lottery.possible_tickets_count - lottery.total_tickets}", inline=False
        )
        if lottery.status in [LotteryStatus.STARTED, LotteryStatus.STOP_SALES]:
            # get winning pool for the current lottery
            lottery_pool = lottery.total_tickets * lottery.ticket_price
            # get old winning pool
            old_winning_pool = await get_old_winning_pool()
            total_winning_pool = old_winning_pool + lottery_pool
            widget.add_field(
                name="Expected reward to win:",
                value=f"{pp_points(total_winning_pool)}<:points:819648258112225316>",
                inline=False,
            )
        widget.add_field(name="Status:", value=f"{lottery.status}", inline=False)
        widget.add_field(name="Min ticket number:", value=f"{lottery.ticket_min_number}", inline=False)
        widget.add_field(name="Max ticket number:", value=f"{lottery.ticket_max_number}", inline=False)
        widget.add_field(
            name="Winning tickets:",
            value=f"{', '.join(map(str, lottery.winning_tickets)) if lottery.winning_tickets else '-'}",
            inline=False,
        )
        widget.add_field(
            name="How many ticket numbers will be drawn:", value=lottery.number_of_winning_tickets, inline=False
        )
        widget.add_field(
            name="Strike ETH block:",
            value=f"[{lottery.strike_eth_block}](<https://etherscan.io/block/{lottery.strike_eth_block}>)",
            inline=False,
        )  # noqa: E501
        await ctx.send(content=ctx.author.mention, embed=widget)

    @cog_ext.cog_subcommand(
        base="lottery",
        name="history",
        guild_ids=config.GUILD_IDS,
        description="Display results for previous lotteries",
    )
    async def history(self, ctx: SlashContext):
        lotteries_ended = (
            await Lottery.filter(status=LotteryStatus.ENDED)
            .prefetch_related("tickets")
            .order_by("-created_at")
            .limit(10)
        )
        if not lotteries_ended:
            return await ctx.send(f"{ctx.author.mention}, we don't have any past lotteries")
        widget = Embed(description="Results for last 10 lotteries", color=GREEN, title="History of lotteries")
        widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
        for lottery in lotteries_ended:
            if lottery.has_winners:
                winners_ids = {_.user_id for _ in lottery.tickets if _.ticket_number in lottery.winning_tickets}
                winners_mentions = [f"<@!{_}>" for _ in winners_ids]
                winners_mentions_str = ", ".join(winners_mentions)
                widget.add_field(name=lottery.name, value=f"Winners: {winners_mentions_str}", inline=False)
            else:
                widget.add_field(name=lottery.name, value="Winners: `no winners`", inline=False)
        await ctx.send(content=ctx.author.mention, embed=widget)

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
                lottery.winning_tickets = select_winning_tickets(
                    hash=block_hash,
                    min_number=lottery.ticket_min_number,
                    max_number=lottery.ticket_max_number,
                    number_of_winning_tickets=lottery.number_of_winning_tickets,
                )
                lottery.status = LotteryStatus.STRIKED
                await lottery.save(update_fields=["winning_tickets", "status", "modified_at"])
                logging.debug(f":::lottery_cron: Selected winning tickets for: {lottery.id}")
        return None

    async def _handle_payments_to_winners(self) -> bool:
        """Handle payments for winning tickets

        We will check if users have tickets with winning numbers, if they don't lottery points will
        be added to the total winning pool for the next lottery
        """
        striked_lotteries = (
            await Lottery.filter(status=LotteryStatus.STRIKED)
            .prefetch_related("tickets")
            .annotate(total_tickets=Count("tickets"))
        )
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
                lottery_pool = lottery.total_tickets * lottery.ticket_price
                # get old winning pool
                old_winning_pool = await get_old_winning_pool()
                total_winning_pool = old_winning_pool + lottery_pool
                # share winning pool equally between winners
                winner_share = total_winning_pool / len(winners_ids)
                await User.filter(id__in=winners_ids).update(balance=F("balance") + int(winner_share))
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
        should_reload_options = False
        if bulk_save_has_winners:
            await Lottery.filter(id__in=bulk_save_has_winners).update(status=LotteryStatus.ENDED, has_winners=True)
            should_reload_options = True
        if bulk_save_no_winners:
            await Lottery.filter(id__in=bulk_save_no_winners).update(status=LotteryStatus.ENDED)
            should_reload_options = True
        return should_reload_options

    @tasks.loop(seconds=config.CHECK_LOTTERY_STATUS_SECONDS)
    async def lottery_status_cron_job(self):
        # ensure that only one instance of job is running, other instances will be discarded
        if not self.lock.locked():
            await self.lock.acquire()
            try:
                should_reload_options = False
                async with in_transaction():
                    await self._handle_stopping_sales()
                    await self._handle_selecting_winning_tickets()
                    should_reload_options = await self._handle_payments_to_winners()
                if should_reload_options:
                    await reload_options_hack(self.bot)
            finally:
                self.lock.release()

    @lottery_status_cron_job.before_loop
    async def before_check_lottery_status(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(LotteryCog(bot))
