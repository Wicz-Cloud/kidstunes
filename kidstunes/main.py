import asyncio
import logging

from .bot import KidsTunesBot
from .config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("kidstunes.log")],
)


async def main() -> None:
    try:
        config = Config()
        bot = KidsTunesBot(config)
        await bot.start(config.discord_token)
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
