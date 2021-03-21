from discord import Embed
from discord.ext import commands
from tortoise.query_utils import Q

from app.models import User, Lottery, Ticket


@commands.command()
async def buy_ticket(ctx, lottery_name: str):
    lottery = await Lottery.get_or_none(name=lottery_name)
    if not lottery:
        return await ctx.send(f"Error, lottery `{lottery_name}` doesn't exist")
    user, _ = await User.get_or_create(id=ctx.author.id, defaults={"id": ctx.author.id})
    if user.balance < lottery.ticket_price:
        return await ctx.send(
            f"Not enough points, You only have {user.balance} points on your deposit and ticket price is {lottery.ticket_price}"  # noqa: E501
        )
    await ctx.send("TODO")


@buy_ticket.error
async def buy_ticket_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("Wrong syntax, ```$lottery.buy_ticket 'LOTTERY NAME'```")


@commands.command()
async def view_tickets(ctx, lottery_name: str):
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
        widget.add_field(name="Ticket number:", value={ticket.ticket_number}, inline=False)
    await ctx.send(embed=widget)


@view_tickets.error
async def view_tickets_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("Wrong syntax, ```$lottery.view_tickets 'LOTTERY NAME'```")


def setup(bot):
    bot.add_command(buy_ticket)
    bot.add_command(view_tickets)
