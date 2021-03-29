import re
import discord
from decimal import Decimal
from discord.ext import commands
from tortoise.expressions import F
from tortoise.transactions import in_transaction

import config
from app.models import User
from app.utils import ensure_registered, pp_points


@commands.command()
async def my_wallet(ctx):
    user = await ensure_registered(ctx.author.id)
    await ctx.send(f"{ctx.author.mention}, your balance is: {pp_points(user.balance)}<:points:819648258112225316>")


@commands.command()
async def withdraw(ctx):
    await ensure_registered(ctx.author.id)
    async with in_transaction():  # prevent race conditions via select_for_update + in_transaction
        user = await User.all().select_for_update().get(id=ctx.author.id)
        old_balance = user.balance
        if old_balance >= 1:
            user.balance = 0
            await user.save(update_fields=["balance", "modified_at"])
            await ctx.send(f"!send {ctx.author.mention} {int(old_balance)}")
        else:
            await ctx.send(
                f"{ctx.author.mention} minimum withdrawal amount is 1<:points:819648258112225316> (you have {pp_points(user.balance)}<:points:819648258112225316>)"  # noqa: E501
            )


@commands.command()
async def deposit(ctx):
    await ensure_registered(ctx.author.id)
    await ctx.send(
        f"To deposit 10<:points:819648258112225316> to your account send command\n `!send {ctx.bot.user.mention} 10`"
    )


class WalletCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Refill user's balance via listening for messages from The Accountant bot"""

        # if message is from The Accountant bot and money were send to Lottery Bot
        if (
            message.author.id == config.ACCOUNTANT_BOT_ID
            and self.bot.user.mentioned_in(message)
            and "I’ve recorded that you transferred" in message.content
        ):
            regex = re.compile("points:(\\d*\\.?\\d+)")
            points = Decimal(regex.findall(message.system_content)[0])
            mentioned_user = [_ for _ in message.mentions if _.id != self.bot.user.id][0]
            await User.filter(id=mentioned_user.id).update(balance=F("balance") + points)  # prevent race conditions
            await message.channel.send(
                f"{mentioned_user.mention}, your balance was credited for {pp_points(points)}<:points:819648258112225316>"
            )


def setup(bot):
    bot.add_command(my_wallet)
    bot.add_command(withdraw)
    bot.add_command(deposit)
    bot.add_cog(WalletCog(bot))
