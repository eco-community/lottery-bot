from discord.ext import commands

from app.models import User
from app.utils import ensure_registered


@commands.command()
async def my_wallet(ctx):
    user = await ensure_registered(ctx.author.id)
    await ctx.send(f"{ctx.author.mention}, your balance is: {int(user.balance)} :points:")


@commands.command()
async def withdraw(ctx):
    await ensure_registered(ctx.author.id)
    user = await User.all().select_for_update().get(id=ctx.author.id)
    if user.balance >= 1:
        await ctx.send(f"!send {ctx.author.mention} {int(user.balance)}")
        user.balance = 0
        await user.save(update_fields=["balance", "modified_at"])
    else:
        await ctx.send(
            f"{ctx.author.mention} minimum withdrawal amount is 1 :points: (you have {int(user.balance)} :points:)"  # noqa: E501
        )


@commands.command()
async def deposit(ctx):
    await ensure_registered(ctx.author.id)
    await ctx.send(f"To deposit 10 :points: to your account send command\n `!send {ctx.bot.user.mention} 10`")


def setup(bot):
    bot.add_command(my_wallet)
    bot.add_command(withdraw)
    bot.add_command(deposit)
