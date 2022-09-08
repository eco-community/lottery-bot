import asyncio
from random import SystemRandom

from discord import Embed
from discord.utils import find
from discord.ext import commands
from tortoise.query_utils import Q
from tortoise.transactions import in_transaction
from discord_slash import SlashContext

from config import ROLES_CAN_CONTROL_BOT, POINTS_EMOJI, PROJECT_THUMBNAIL
from app.models import Lottery, Ticket, User
from app.utils import (
    ensure_registered,
    pp_points,
    register_buy_ticket_command,
    register_buy_whitelisted_command,
    register_my_tickets_command,
)
from app.constants import LotteryStatus, GREEN, DELETE_AFTER


cryptogen = SystemRandom()


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(register_buy_ticket_command(self.bot, self.buy_ticket))
        self.bot.loop.create_task(register_my_tickets_command(self.bot, self.my_tickets))
        self.bot.loop.create_task(register_buy_whitelisted_command(self.bot, self.buy_whitelisted))

    async def buy_whitelisted(self, ctx: SlashContext, name: str):
        # batch ticket buying logic (admin only)
        await ensure_registered(ctx.author.id)
        can_control_bot = find(lambda _: _.name in ROLES_CAN_CONTROL_BOT, ctx.author.roles)
        # validate that user can control bot
        if not can_control_bot:
            return await ctx.send(
                f"{ctx.author.mention}, tickets can't be bought for `{name}` because you can't control bot",
                delete_after=DELETE_AFTER,
            )
        # validate that lottery exists
        lottery = await Lottery.get_or_none(name=name)
        if not lottery:
            return await ctx.send(
                f"{ctx.author.mention}, error, sweepstake `{name}` doesn't exist",
                delete_after=DELETE_AFTER,
            )
        # validate that lottery is of whitelisted type
        if not lottery.is_whitelisted:
            return await ctx.send(
                f"{ctx.author.mention}, this command works only for whitelisted sweepstakes",
                delete_after=DELETE_AFTER,
            )
        # validate that we allow selling tickets
        if lottery.status == LotteryStatus.STOP_SALES:
            return await ctx.send(
                f"{ctx.author.mention}, tickets can't be bought for `{name}` because there are no tickets left or it's close to strike date",  # noqa: E501
                delete_after=DELETE_AFTER,
            )
        elif lottery.status == LotteryStatus.STRIKED:
            return await ctx.send(
                f"{ctx.author.mention}, tickets can't be bought for `{name}` because winning tickets were already selected",  # noqa: E501
                delete_after=DELETE_AFTER,
            )
        elif lottery.status == LotteryStatus.ENDED:
            return await ctx.send(
                f"{ctx.author.mention}, tickets can't be bought for `{name}` because it has ended",
                delete_after=DELETE_AFTER,
            )
        async with in_transaction():
            try:
                await ctx.send(
                    f"Hello, {ctx.author.mention}, this sweepstake is of whitelisted type, please mention user(s) in the next message for whom you want to buy ticket(s)",  # noqa: E501
                    delete_after=DELETE_AFTER,
                )
                message = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.guild is not None and m.author == ctx.author,
                    timeout=300,
                )
                if len(message.raw_mentions) < 1:
                    return await ctx.send(
                        f"{ctx.author.mention}, you need to mention at least one person",
                        delete_after=DELETE_AFTER,
                    )  # noqa: E501
                owner_ids = message.raw_mentions
                # remove duplicates from list
                owner_ids = list(set(owner_ids))
                # ensure that all owners are registered
                for owner_id in owner_ids:
                    await ensure_registered(owner_id)
                # retrieve owners from db
                owners = await User.filter(id__in=owner_ids)
                # get existing ticket numbers from database to avoid collisions
                ticket_numbers = await Ticket.filter(lottery=lottery).values_list(
                    "ticket_number", flat=True
                )
                # ensure that there is enough available tickets left
                # make range to behave as inclusive range, this way ticket with max_number could be won
                all_possible_tickets = lottery.ticket_max_number + 1 - lottery.ticket_min_number
                already_existing_tickets = len(ticket_numbers)
                tickets_left = all_possible_tickets - already_existing_tickets
                need_to_create_tickets = len(owner_ids)
                # ensure that there is enough free to use tickets
                if tickets_left < need_to_create_tickets:
                    return await ctx.send(
                        f"{ctx.author.mention}, there is not enough tickets left (tickets left: {tickets_left})",
                        delete_after=DELETE_AFTER,
                    )  # noqa: E501
                # find out ticket numbers which are free to use
                free_ticket_numbers_set = set(
                    range(lottery.ticket_min_number, lottery.ticket_max_number + 1)
                ) - set(ticket_numbers)
                free_ticket_numbers = list(free_ticket_numbers_set)
                # shuffle free to use ticket numbers
                cryptogen.shuffle(free_ticket_numbers)
                # bulk create tickets
                tickets_raw = [
                    Ticket(
                        user=owner,
                        lottery=lottery,
                        ticket_number=free_ticket_numbers[i],
                    )
                    for i, owner in enumerate(owners)
                ]
                await Ticket.bulk_create(tickets_raw)
                if tickets_left == need_to_create_tickets:
                    lottery.status = LotteryStatus.STOP_SALES
                    await lottery.save(update_fields=["status", "modified_at"])
                string_message = ""
                for i, owner in enumerate(owners):
                    string_message += f" <@!{owner.id}>(`{free_ticket_numbers[i]}` :tickets:),"
                string_message = string_message[:-1]
                await ctx.send(
                    f"Congratulations {ctx.author.mention}, you just purchased tickets for `{lottery.name}` for:{string_message}"  # noqa: E501
                )
            except asyncio.TimeoutError:
                return

    async def buy_ticket(self, ctx: SlashContext, name: str):
        # ticket buying logic
        await ensure_registered(ctx.author.id)
        can_control_bot = find(lambda _: _.name in ROLES_CAN_CONTROL_BOT, ctx.author.roles)
        async with in_transaction():  # prevent race conditions via select_for_update + in_transaction
            # select user 2nd time to lock it's row
            user = await User.filter(id=ctx.author.id).select_for_update().get(id=ctx.author.id)
            # validate that lottery exists
            lottery = await Lottery.get_or_none(name=name)
            if not lottery:
                return await ctx.send(
                    f"{ctx.author.mention}, error, sweepstake `{name}` doesn't exist",
                    delete_after=DELETE_AFTER,
                )
            # validate that we allow selling tickets
            if lottery.status == LotteryStatus.STOP_SALES:
                return await ctx.send(
                    f"{ctx.author.mention}, tickets can't be bought for `{name}` because there are no tickets left or it's close to strike date",  # noqa: E501
                    delete_after=DELETE_AFTER,
                )
            elif lottery.status == LotteryStatus.STRIKED:
                return await ctx.send(
                    f"{ctx.author.mention}, tickets can't be bought for `{name}` because winning tickets were already selected",  # noqa: E501
                    delete_after=DELETE_AFTER,
                )
            elif lottery.status == LotteryStatus.ENDED:
                return await ctx.send(
                    f"{ctx.author.mention}, tickets can't be bought for `{name}` because it has ended",
                    delete_after=DELETE_AFTER,
                )
            # validate that lottery is of whitelisted type and user can control bot
            if lottery.is_whitelisted and not can_control_bot:
                return await ctx.send(
                    f"{ctx.author.mention}, tickets can't be bought for `{name}` because it is of `whitelisted` type",
                    delete_after=DELETE_AFTER,
                )
            # validate user balance
            if user.balance < lottery.ticket_price:
                return await ctx.send(
                    f"{ctx.author.mention}, not enough points, you only have `{pp_points(user.balance)}`{POINTS_EMOJI} in your sweepstake wallet and ticket price is `{int(lottery.ticket_price)}`{POINTS_EMOJI}. To add points to your sweepstake wallet, `!send @{ctx.bot.user.display_name}#{ctx.bot.user.discriminator} [number of points]`",  # noqa: E501
                    delete_after=DELETE_AFTER,
                )
            # handle whitelisted lotteries
            is_whitelisted_ticket = lottery.is_whitelisted and can_control_bot
            if is_whitelisted_ticket:
                try:
                    await ctx.send(
                        f"Hello, {ctx.author.mention}, this sweepstake is of whitelisted type, please mention user for whom you want to buy a ticket",  # noqa: E501
                        delete_after=DELETE_AFTER,
                    )
                    message = await self.bot.wait_for(
                        "message",
                        check=lambda m: m.guild is not None and m.author == ctx.author,
                        timeout=300,
                    )
                    if len(message.raw_mentions) != 1:
                        return await ctx.send(
                            f"{ctx.author.mention}, you need to mention only one person",
                            delete_after=DELETE_AFTER,
                        )  # noqa: E501
                    owner_id = message.raw_mentions[0]
                    await ensure_registered(owner_id)
                    owner = await User.get(id=owner_id)
                except asyncio.TimeoutError:
                    return
            else:
                owner = user
            # to generate random ticket number that doesn't have collisions we will need to grab all ticket numbers
            # from database and then check in python which numbers are available
            ticket_numbers = await Ticket.filter(lottery=lottery).values_list(
                "ticket_number", flat=True
            )
            # create ticket for user
            try:
                ticket = await Ticket.create(
                    user=owner,
                    lottery=lottery,
                    ticket_number=cryptogen.choice(
                        [
                            _
                            # make range to behave as inclusive range, this way ticket with max_number could be won
                            for _ in range(lottery.ticket_min_number, lottery.ticket_max_number + 1)
                            if _ not in ticket_numbers
                        ]
                    ),
                )
                user.balance = user.balance - lottery.ticket_price
                await user.save(update_fields=["balance", "modified_at"])
                if is_whitelisted_ticket:
                    await ctx.send(
                        f":tickets: Congratulations <@!{owner.id}>, you just had {lottery.name} purchased for you by {ctx.author.mention}.  Your ticket number is: {ticket.ticket_number}:tickets:"  # noqa: E501
                    )
                else:
                    await ctx.send(
                        f"{ctx.author.mention}, you bought {lottery.name} ticket with number: `{ticket.ticket_number}`, your balance is: `{pp_points(user.balance)}`{POINTS_EMOJI}"  # noqa: E501
                    )
            except IndexError:
                # it means that all tickets were sold, stop ticket sales for lottery
                lottery.status = LotteryStatus.STOP_SALES
                await lottery.save(update_fields=["status", "modified_at"])
                await ctx.send(
                    f"{ctx.author.mention}, ouch, the last ticket was sold a moment ago",
                    delete_after=DELETE_AFTER,
                )

    async def my_tickets(self, ctx: SlashContext, name: str):
        lottery = await Lottery.get_or_none(name=name)
        if not lottery:
            return await ctx.send(
                f"{ctx.author.mention}, error, sweepstake `{name}` doesn't exist",
                delete_after=DELETE_AFTER,
            )
        tickets = await Ticket.filter(Q(lottery__id=lottery.id) & Q(user__id=ctx.author.id))
        widget = Embed(
            description=f"You have `{len(tickets)}` tickets for `{name}`",
            color=GREEN,
            title=f"{name} tickets",
        )
        widget.set_thumbnail(url=PROJECT_THUMBNAIL)
        if len(tickets):
            widget.add_field(
                name="Ticket numbers:",
                value=f"`{', '.join([str(_.ticket_number) for _ in tickets])}`",
                inline=False,
            )
        await ctx.send(
            content=ctx.author.mention,
            embed=widget,
            delete_after=DELETE_AFTER,
        )


def setup(bot):
    bot.add_cog(TicketCog(bot))
