import os
import yaml
import logging
import hikari
import lightbulb
from lightbulb.ext import tasks

# ANSI color codes
class AnsiColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[0;37m",    # White
        logging.INFO: "\033[0;36m",     # Cyan
        logging.WARNING: "\033[0;33m",  # Yellow
        logging.ERROR: "\033[0;31m",    # Red
        logging.CRITICAL: "\033[1;31m", # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{log_color}{message}{self.RESET}"

class DiscordHandler(logging.Handler):
    def __init__(self, bot, channel_id):
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id

    async def send_log(self, record):
        channel = await self.bot.rest.fetch_channel(self.channel_id)
        if isinstance(channel, hikari.TextableChannel):
            await self.bot.rest.create_message(channel, f"```ansi\n{self.format(record)}```")

    def emit(self, record):
        self.bot.create_task(self.send_log(record))

# Load configuration
script_dir = os.path.dirname(__file__)
config_path = os.path.join(script_dir, "config.yml")
with open(config_path, 'r') as config_file:
    config = yaml.load(config_file, Loader=yaml.FullLoader)

# Initialize the bot
bot = lightbulb.BotApp(
    token=config['token'],
    ignore_bots=True,
    intents=hikari.Intents.ALL
)
tasks.load(bot)

# Set up logging
logger = logging.getLogger('hikari')
logger.setLevel(logging.INFO)
formatter = AnsiColorFormatter('[%(levelname)s] %(name)s: %(message)s')
discord_handler = DiscordHandler(bot, config['channels']['logsChannel'])
discord_handler.setFormatter(formatter)
logger.addHandler(discord_handler)


async def restart(reason=None):
    if reason == None:
        await logger.info("Restarting...")
    else:
        await logger.info("Restarting... Reason: " + reason)

    os.system("clear")
    os.system(f"python -OO {__file__}")
    exit()


# Run the bot
bot.run()