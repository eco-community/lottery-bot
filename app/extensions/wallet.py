import re
from decimal import Decimal

import discord
from discord.ext import commands
from tortoise.expressions import F
from tortoise.transactions import in_transaction
from discord_slash import cog_ext, SlashContext

import config
from app.models import User
from app.utils import ensure_registered, pp_points
from app.constants import DELETE_AFTER


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
                f"<@{message.author.id}>, your balance was credited for {pp_points(points)}<:points:819648258112225316>.\nTo participate, `/sweepstake buy [sweepstake name]`",  # noqa: E501
                delete_after=DELETE_AFTER,
            )

    @cog_ext.cog_subcommand(
        base="sweepstake",
        name="wallet",
        guild_ids=config.GUILD_IDS,
        description="View my sweepstake wallet",
    )
    async def my_wallet(self, ctx: SlashContext):
        user = await ensure_registered(ctx.author.id)
        await ctx.send(
            f"{ctx.author.mention}, your balance is: {pp_points(user.balance)}<:points:819648258112225316>",
            delete_after=DELETE_AFTER,
        )

    @cog_ext.cog_subcommand(
        base="sweepstake",
        name="withdraw",
        guild_ids=config.GUILD_IDS,
        description="Withdraw eco points from my sweepstake wallet",
    )
    async def withdraw(self, ctx: SlashContext):
        await ensure_registered(ctx.author.id)
        async with in_transaction():  # prevent race conditions via select_for_update + in_transaction
            user = await User.filter(id=ctx.author.id).select_for_update().get(id=ctx.author.id)
            old_balance = user.balance
            if old_balance >= 1:
                user.balance = 0
                await user.save(update_fields=["balance", "modified_at"])
                await ctx.send(f"!send <@!{ctx.author.id}> {int(old_balance)}", delete_after=DELETE_AFTER)
            else:
                await ctx.send(
                    f"{ctx.author.mention} minimum withdrawal amount is 1<:points:819648258112225316> (you have {pp_points(user.balance)}<:points:819648258112225316>)",  # noqa: E501
                    delete_after=DELETE_AFTER,
                )

    @cog_ext.cog_subcommand(
        base="sweepstake",
        name="deposit",
        guild_ids=config.GUILD_IDS,
        description="Deposit eco points to my sweepstake wallet",
    )
    async def deposit(self, ctx: SlashContext):
        await ensure_registered(ctx.author.id)
        await ctx.send(
            f"{ctx.author.mention}, to deposit <:points:819648258112225316> to your sweepstake wallet send command\n `!send @{ctx.bot.user.display_name}#{ctx.bot.user.discriminator} [number of points]`",  # noqa: E501
            delete_after=DELETE_AFTER,
        )


def setup(bot):
    bot.add_cog(WalletCog(bot))
