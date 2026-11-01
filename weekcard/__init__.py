from redbot.core.bot import Red

from .weekcard import Weekcard


async def setup(bot: Red) -> None:
    await bot.add_cog(Weekcard(bot))
