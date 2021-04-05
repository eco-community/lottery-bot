from random import SystemRandom

from discord import Embed
from discord.ext import commands
from tortoise.query_utils import Q
from tortoise.transactions import in_transaction

from app.models import Lottery, Ticket, User
from app.utils import ensure_registered, pp_points
from app.constants import LotteryStatus


cryptogen = SystemRandom()


@commands.command(aliases=["buy"])
async def buy_ticket(ctx, *, lottery_name):
    lottery_name = lottery_name.replace('"', "")
    # ticket buying logic
    await ensure_registered(ctx.author.id)
    async with in_transaction():  # prevent race conditions via select_for_update + in_transaction
        # select user 2nd time to lock it's row
        user = await User.filter(id=ctx.author.id).select_for_update().get(id=ctx.author.id)
        # validate that lottery exists
        lottery = await Lottery.get_or_none(name=lottery_name)
        if not lottery:
            return await ctx.send(f"{ctx.author.mention}, error, lottery `{lottery_name}` doesn't exist")
        # validate that we allow selling tickets
        if lottery.status == LotteryStatus.STOP_SALES:
            return await ctx.send(
                f"{ctx.author.mention}, tickets can't be bought for `{lottery_name}` because there are no tickets left or it's close to strike date"  # noqa: E501
            )
        elif lottery.status == LotteryStatus.STRIKED:
            return await ctx.send(
                f"{ctx.author.mention}, tickets can't be bought for `{lottery_name}` because winning tickets were already selected"  # noqa: E501
            )
        elif lottery.status == LotteryStatus.ENDED:
            return await ctx.send(
                f"{ctx.author.mention}, tickets can't be bought for `{lottery_name}` because it has ended"
            )
        # validate user balance
        if user.balance < lottery.ticket_price:
            return await ctx.send(
                f"{ctx.author.mention}, not enough points, you only have `{pp_points(user.balance)}`<:points:819648258112225316> in your lottery wallet and ticket price is `{int(lottery.ticket_price)}`<:points:819648258112225316>. To add points to your lottery wallet, `!send @{ctx.bot.user.display_name}#{ctx.bot.user.discriminator} [number of points]`"  # noqa: E501
            )
        user.balance = user.balance - lottery.ticket_price
        await user.save(update_fields=["balance", "modified_at"])
        # to generate random ticket number that doesn't have collisions we will need to grab all ticket numbers
        # from database and then check in python which numbers are available
        ticket_numbers = await Ticket.filter(lottery=lottery).values_list("ticket_number", flat=True)
        # create ticket for user
        try:
            ticket = await Ticket.create(
                user=user,
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
            await user.refresh_from_db(fields=["balance"])
            await ctx.send(
                f"{ctx.author.mention}, you bought ticket with number: `{ticket.ticket_number}`, your balance is: `{pp_points(user.balance)}`<:points:819648258112225316>"  # noqa: E501
            )
        except IndexError:
            # it means that all tickets were sold, stop ticket sales for lottery
            lottery.status = LotteryStatus.STOP_SALES
            await lottery.save(update_fields=["status", "modified_at"])
            await ctx.send(f"{ctx.author.mention}, ouch, the last ticket was sold a moment ago")


@buy_ticket.error
async def buy_ticket_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send(f"{ctx.author.mention}, wrong syntax, ```!lottery.buy [lottery name]```")


@commands.command(aliases=["tickets"])
async def my_tickets(ctx, *, lottery_name):
    lottery_name = lottery_name.replace('"', "")
    lottery = await Lottery.get_or_none(name=lottery_name)
    if not lottery:
        return await ctx.send(f"{ctx.author.mention}, error, lottery `{lottery_name}` doesn't exist")
    tickets = await Ticket.filter(Q(lottery__id=lottery.id) & Q(user__id=ctx.author.id))
    widget = Embed(
        description=f"{ctx.author.mention}, you have `{len(tickets)}` tickets for `{lottery_name}`",
        color=0x03D692,
        title="Your tickets",
    )
    widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
    if len(tickets):
        widget.add_field(
            name="Ticket numbers:",
            value=f"`{', '.join([str(_.ticket_number) for _ in tickets])}`",
            inline=False,
        )
    await ctx.send(embed=widget)


@my_tickets.error
async def my_tickets_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send(f"{ctx.author.mention}, wrong syntax, ```!lottery.tickets [lottery name]```")


def setup(bot):
    bot.add_command(buy_ticket)
    bot.add_command(my_tickets)
