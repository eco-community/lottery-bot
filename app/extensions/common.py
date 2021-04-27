from discord import Embed, Activity, ActivityType
from discord.ext import commands
from discord_slash import cog_ext, SlashContext


import config
from constants import ROLES_CAN_CONTROL_BOT
from app.constants import GREEN


class CommonCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=Activity(type=ActivityType.playing, name="ECO lottery"))
        info = await self.bot.application_info()
        print(
            f"Add via link: https://discord.com/api/oauth2/authorize?client_id={info.id}&permissions=2147829824&scope=bot%20applications.commands"  # noqa: E501
        )

    @cog_ext.cog_subcommand(base="lottery", name="help", guild_ids=config.GUILD_IDS, description="List all commands")
    async def help(self, ctx: SlashContext):
        user_roles = [_.name for _ in ctx.author.roles]
        widget = Embed(description="Available commands for ECO Lottery Bot", color=GREEN, title="Help")
        widget.set_thumbnail(url="https://eco-bots.s3.eu-north-1.amazonaws.com/eco_large.png")
        # add admin help
        if any([role for role in user_roles if role in ROLES_CAN_CONTROL_BOT]):
            widget.add_field(name="!lottery.new", value="`Create a new lottery`", inline=False)
        # default help
        widget.add_field(name="/lottery list", value="`Display active lotteries`", inline=False)
        widget.add_field(name="/lottery history", value="`Display results for previous lotteries`", inline=False)
        widget.add_field(name="/lottery view", value="`Display lottery information`", inline=False)
        widget.add_field(name="/lottery tickets", value="`My tickets`", inline=False)
        widget.add_field(name="/lottery buy", value="`Buy ticket`", inline=False)
        widget.add_field(name="/lottery wallet", value="`View my lottery wallet`", inline=False)
        widget.add_field(name="/lottery withdraw", value="`Withdraw eco points from my lottery wallet`", inline=False)
        widget.add_field(name="/lottery deposit", value="`Deposit eco points to my lottery wallet`", inline=False)
        await ctx.send(content=ctx.author.mention, embed=widget)


def setup(bot):
    bot.add_cog(CommonCog(bot))
