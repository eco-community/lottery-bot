from discord import Embed
from discord.ext import commands
from tortoise import exceptions

from app.models import Lottery
from app.utils import get_eta_to_block
from constants import ROLES_CAN_CONTROL_BOT


@commands.has_any_role(*ROLES_CAN_CONTROL_BOT)
@commands.command()
async def new_lottery(ctx, name: str, strike_eth_block: int, ticket_price: int = None):
    # parse args
    if ticket_price:
        lottery = Lottery(name=name, strike_eth_block=strike_eth_block, ticket_price=ticket_price)
    else:
        lottery = Lottery(name=name, strike_eth_block=strike_eth_block)
    # get eta to block
    try:
        lottery.strike_date_eta = await get_eta_to_block(strike_eth_block)
    except TypeError:
        # block has already passed
        return await ctx.send(f"Error, block `{strike_eth_block}` already passed, choose a different block")
    # save lottery
    try:
        await lottery.save()
    except exceptions.IntegrityError:
        return await ctx.send(f"Error, lottery `{name}` already exists, choose a different name")
    await ctx.send(f"Success! Created lottery `{lottery}`, will strike at {lottery.strike_date_eta:%Y-%m-%d %H:%M} UTC")


@new_lottery.error
async def new_lottery_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send(
            "Wrong syntax, ```$lottery.new_lottery \"LOTTERY NAME\" STRIKE_ETH_BLOCK TICKET_PRICE(OPTIONAL)```"
        )  # noqa: E501


@commands.command()
async def view_lottery(ctx, name: str):
    lottery = await Lottery.get_or_none(name=name)
    if not lottery:
        return await ctx.send(f"Error, lottery `{name}` doesn't exist")
    widget = Embed(description=f"{lottery.name} information", color=0x03D692, title=f"{lottery.name}")
    widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
    widget.add_field(name="Ticket price:", value=f"{int(lottery.ticket_price)}", inline=False)
    widget.add_field(name="Strike ETH block:", value=f"[{lottery.strike_eth_block}](<https://etherscan.io/block/{lottery.strike_eth_block}>)", inline=False)  # noqa: E501
    widget.add_field(name="Strike Date (estimated):", value=f"[{lottery.strike_date_eta:%Y-%m-%d %H:%M} UTC](<https://etherscan.io/block/countdown/{lottery.strike_eth_block}>)", inline=False)  # noqa: E501
    await ctx.send(embed=widget)


@view_lottery.error
async def view_lottery_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("Wrong syntax, ```$lottery.view_lottery \"LOTTERY NAME\"```")


@commands.command()
async def lotteries(ctx):
    lotteries_list = await Lottery.all()
    if not lotteries_list:
        return await ctx.send("We don't have any lotteries, create one via `$lottery.new_lottery`")
    widget = Embed(description="List of all lotteries", color=0x03D692, title="All lotteries")
    widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
    for lottery in lotteries_list:
        widget.add_field(name=lottery.name, value=f"Ticket price {int(lottery.ticket_price)} :points:", inline=False)
    await ctx.send(embed=widget)


def setup(bot):
    bot.add_command(new_lottery)
    bot.add_command(view_lottery)
    bot.add_command(lotteries)
