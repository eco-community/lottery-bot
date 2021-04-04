import re
import discord
from decimal import Decimal
from discord.ext import commands
from tortoise.expressions import F
from tortoise.transactions import in_transaction

import config
from app.models import User
from app.utils import ensure_registered, pp_points


@commands.command(aliases=["wallet", "balance"])
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
            await ctx.send(f"!send <@!{ctx.author.id}> {int(old_balance)}")
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
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Refill user's balance via listening for reactions to messages from The Accountant bot"""

        if payload.user_id != config.ACCOUNTANT_BOT_ID:
            # we need to only refill balance if it was The Accountant bot who reacted to message
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if (
            # if user tried to send points in message
            "!send" in message.content
            # and there were single mention in the message
            and len(message.raw_mentions) == 1
            # and lottery bot was mentioned
            and self.bot.user.id in message.raw_mentions
        ):
            await ensure_registered(message.author.id)
            # remove bot mention from content
            content_no_mentions = message.system_content.replace(str(self.bot.user.id), "")
            # remove comma from string (because of The Accountant Bot)
            content_no_mentions_no_comma = content_no_mentions.replace(",", "")
            # parse all numbers from message
            list_of_numbers = re.findall("\\d*[\\.]?\\d+", content_no_mentions_no_comma)
            # points should be the first number
            str_points = list_of_numbers[0]
            points = Decimal(str_points)
            await User.filter(id=message.author.id).update(balance=F("balance") + points)  # prevent race conditions
            await message.channel.send(
                f"<@{message.author.id}>, your balance was credited for {pp_points(points)}<:points:819648258112225316>"
            )


def setup(bot):
    bot.add_command(my_wallet)
    bot.add_command(withdraw)
    bot.add_command(deposit)
    bot.add_cog(WalletCog(bot))
