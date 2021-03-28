from discord import Embed
from discord.ext import commands
from random import SystemRandom

from tortoise import exceptions
from tortoise.query_utils import Q
from tortoise.expressions import F
from tortoise.transactions import in_transaction

from app.models import Lottery, Ticket, User
from app.utils import ensure_registered, pp_points
from app.constants import LotteryStatus


cryptogen = SystemRandom()


@commands.command()
async def buy_ticket(ctx, lottery_name: str):
    await ensure_registered(ctx.author.id)
    # ticket buying logic
    try:
        async with in_transaction():  # prevent race conditions via select_for_update + in_transaction
            user = await User.all().select_for_update().get(id=ctx.author.id)  # select user 2nd time to lock it's row
            # validate that lottery exists
            lottery = await Lottery.get_or_none(name=lottery_name)
            if not lottery:
                return await ctx.send(f"Error, lottery `{lottery_name}` doesn't exist")
            # validate that we allow selling tickets
            if lottery.status == LotteryStatus.STOP_SALES:
                return await ctx.send(f"Tickets can't be bought for `{lottery_name}` because it's close to strike date")
            elif lottery.status == LotteryStatus.STRIKED:
                return await ctx.send(
                    f"Tickets can't be bought for `{lottery_name}` because winning tickets were already selected"
                )
            elif lottery.status == LotteryStatus.ENDED:
                return await ctx.send(f"Tickets can't be bought for `{lottery_name}` because it has ended")
            # validate user balance
            if user.balance < lottery.ticket_price:
                return await ctx.send(
                    f"Not enough points, You only have `{pp_points(user.balance)}`:points: on your deposit and ticket price is `{int(lottery.ticket_price)}`:points:"  # noqa: E501
                )
            user.balance = F("balance") - lottery.ticket_price  # to prevent race conditions
            await user.save(update_fields=["balance", "modified_at"])
            # create ticket for user
            ticket = await Ticket.create(
                user=user,
                lottery=lottery,
                ticket_number=cryptogen.randint(lottery.ticket_min_number, lottery.ticket_max_number - 1),
            )
            await user.refresh_from_db(fields=["balance"])
            await ctx.send(
                f"You bought ticket with number: `{ticket.ticket_number}`, your balance is: `{pp_points(user.balance)}`:points:"  # noqa: E501
            )
    except exceptions.IntegrityError:
        # could be caused by duplicate tickets because we have a higher probability of collisions
        # it's safe to have a collision in tickets because balance will be rolled back in transaction
        await ctx.send(f"Error, {ctx.author.mention}, please try again")


@buy_ticket.error
async def buy_ticket_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send('Wrong syntax, ```$lottery.buy_ticket "LOTTERY NAME"```')


@commands.command()
async def my_tickets(ctx, lottery_name: str):
    lottery = await Lottery.get_or_none(name=lottery_name)
    if not lottery:
        return await ctx.send(f"Error, lottery `{lottery_name}` doesn't exist")
    tickets = await Ticket.filter(Q(lottery__id=lottery.id) & Q(user__id=ctx.author.id))
    widget = Embed(
        description=f"You have {len(tickets)} tickets for the {lottery_name}",
        color=0x03D692,
        title="Your tickets",
    )
    widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
    for ticket in tickets:
        widget.add_field(name="Ticket number:", value=f"{ticket.ticket_number}", inline=False)
    await ctx.send(embed=widget)


@my_tickets.error
async def my_tickets_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send('Wrong syntax, ```$lottery.my_tickets "LOTTERY NAME"```')


def setup(bot):
    bot.add_command(buy_ticket)
    bot.add_command(my_tickets)
