from discord.ext import commands


class CommonCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(CommonCog(bot))
