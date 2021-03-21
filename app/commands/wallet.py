from discord.ext import commands

from app.models import User


@commands.command()
async def my_wallet(ctx):
    user, _ = await User.get_or_create(id=ctx.author.id)
    await ctx.send(f"{ctx.message.author.mention}, your balance is: {int(user.balance)} :points")


def setup(bot):
    bot.add_command(my_wallet)
