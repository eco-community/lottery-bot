from discord import Embed
from discord.ext import commands

from constants import ROLES_CAN_CONTROL_BOT


@commands.command()
async def help(ctx):
    user_roles = [_.name for _ in ctx.author.roles]
    widget = Embed(description="Available commands for ECO Lottery Bot", color=0x03D692, title="Help")
    widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
    # add admin help
    if any([role for role in user_roles if role in ROLES_CAN_CONTROL_BOT]):
        widget.add_field(name="$lottery.new_lottery", value="`Create a new lottery`", inline=False)
    # default help
    widget.add_field(name="$lottery.view_lottery", value="`Display lottery information`", inline=False)
    widget.add_field(name="$lottery.lotteries", value="`Display all lotteries`", inline=False)
    widget.add_field(name="$lottery.my_tickets", value="`My tickets`", inline=False)
    widget.add_field(name="$lottery.buy_ticket", value="`Buy ticket`", inline=False)
    widget.add_field(name="$lottery.my_wallet", value="`View my balance`", inline=False)
    widget.add_field(name="$lottery.withdraw", value="`Withdraw eco :points: to my balance`", inline=False)
    widget.add_field(name="$lottery.deposit", value="`Deposit eco :points: to my balance`", inline=False)
    await ctx.send(embed=widget)


def setup(bot):
    bot.add_command(help)
