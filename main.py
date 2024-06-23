import os
import yaml
import logging
import hikari
import lightbulb
from lightbulb.ext import tasks
import json
import shutil

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
with open(config_path, 'r', encoding="UTF-8") as config_file:
    config = yaml.load(config_file, Loader=yaml.FullLoader)

meme_folder = os.path.normpath(os.path.join(script_dir, config['MOTDSettings']['messageFolder']))
if not os.path.exists(meme_folder):
    os.mkdir(meme_folder)

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
        logger.info("Restarting...")
    else:
        logger.info("Restarting... Reason: " + reason)

    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For Unix/Linux/Mac
        os.system('clear')
    os.system(f"python -OO {__file__}")
    exit()

async def check_memes():
    return


@bot.listen(hikari.GuildMessageCreateEvent)
async def on_message_sent(event):
    if (event.channel_id != config['channels']['memeChannel'] or event.author.id == config['botUserId']):
        return
    
    message_folder = os.path.normpath(os.path.join(meme_folder, str(event.message_id)))

    if not os.path.exists(message_folder):
        os.mkdir(message_folder)

    file_names = []
    for i in range(0, len(event.message.attachments)):
        file = event.message.attachments[i]
        filename = f"{i}.{file.extension}"
        file_names.append(filename)
        await file.save(os.path.join(message_folder, filename))

    message_info = {"id": event.message_id, "author": event.author.id, "content": event.content, "score": 0, "attachments": file_names}
    with open(os.path.join(message_folder, "info.json"), "w") as file:
        json.dump(message_info, file, indent=4)
        logger.info(f"Message {event.message_id} saved to {message_folder} (Info: {message_info})")
    
    for emoji in config['MOTDSettings']['reactionIcons']:
        await event.message.add_reaction(emoji[0])

    winningId = await check_memes()

@bot.listen(hikari.GuildMessageDeleteEvent)
async def on_message_deleted(event):
    if (event.channel_id != config['channels']['memeChannel']):
        return

    message_folder = os.path.normpath(os.path.join(meme_folder, str(event.message_id)))

    if not os.path.exists(message_folder):
        logger.warning(f"Message {event.message_id} was deleted but no folder was found.")
        return
    
    shutil.rmtree(message_folder, ignore_errors=False)
    logger.info(f"Message {event.message_id} deleted from {meme_folder}")

    winningId = await check_memes()

@bot.listen(hikari.GuildMessageUpdateEvent)
async def on_message_updated(event):
    if (event.channel_id != config['channels']['memeChannel'] or event.author.id == config['botUserId']):
        return
    
    message_folder = os.path.normpath(os.path.join(meme_folder, str(event.message_id)))

    if not os.path.exists(message_folder):
        logger.warning(f"Message {event.message_id} was updated but no folder was found. (Message: {event.message})")
        return
    
    message_info = {}

    with open(os.path.join(message_folder, "info.json"), "r") as file:
        message_info = json.load(file)
        message_info["content"] = event.message.content
    
    with open(os.path.join(message_folder, "info.json"), "w") as file:
        json.dump(message_info, file, indent=4)
        logger.info(f"Message {event.message_id} updated (Info: {message_info})")

    winningId = await check_memes()

@bot.listen(hikari.GuildReactionAddEvent)
async def on_reaction_added(event):
    if (event.channel_id != config['channels']['memeChannel'] or event.user_id == config['botUserId']):
        return

    message_folder = os.path.normpath(os.path.join(meme_folder, str(event.message_id)))

    if not os.path.exists(message_folder):
        logger.warning(f"Message {event.message_id} was reacted to but no folder was found. (Reaction: {event.emoji_name})")
        return
    
    for emoji in config['MOTDSettings']['reactionIcons'].keys():
        if event.is_for_emoji(emoji):
            logger.info(f"Message {event.message_id} reacted to with {emoji}")
            with open(os.path.join(message_folder, "info.json"), "r") as file:
                message_info = json.load(file)
                message_info["score"] += config['MOTDSettings']['reactionIcons'][emoji]
            with open(os.path.join(message_folder, "info.json"), "w") as file:
                json.dump(message_info, file, indent=4)
                logger.info(f"Message {event.message_id} updated (Info: {message_info})")
            return
        
@bot.listen(hikari.GuildReactionDeleteEvent)
async def on_reaction_deleted(event):
    if (event.channel_id != config['channels']['memeChannel'] or event.user_id == config['botUserId']):
        return

    message_folder = os.path.normpath(os.path.join(meme_folder, str(event.message_id)))

    if not os.path.exists(message_folder):
        logger.warning(f"Message {event.message_id} was reacted to but no folder was found. (Reaction: {event.emoji_name})")
        return
    
    for emoji in config['MOTDSettings']['reactionIcons'].keys():
        if event.is_for_emoji(emoji):
            logger.info(f"Message {event.message_id} reaction removed: {emoji}")
            with open(os.path.join(message_folder, "info.json"), "r") as file:
                message_info = json.load(file)
                message_info["score"] -= config['MOTDSettings']['reactionIcons'][emoji]
            with open(os.path.join(message_folder, "info.json"), "w") as file:
                json.dump(message_info, file, indent=4)
                logger.info(f"Message {event.message_id} updated (Info: {message_info})")
            return
    

@bot.command
@lightbulb.command("restart", "Restart the bot.")
@lightbulb.implements(lightbulb.SlashCommand)
async def restart_command(ctx: lightbulb.Context):
    guild = bot.cache.get_guild(ctx.guild_id)
    member = guild.get_member(ctx.author.id)
    if not config["adminRole"] in member.role_ids:
        await ctx.respond("You do not have permission to use this command.", flags=hikari.MessageFlag.EPHEMERAL)
        return
    
    await ctx.respond("Restarting...", flags=hikari.MessageFlag.EPHEMERAL)
    await restart()

@bot.command
@lightbulb.option("messageid", "The ID of the message to delete.", type=str, required=True)
@lightbulb.command("delete", "Delete a message.")
@lightbulb.implements(lightbulb.SlashCommand)
async def delete_command(ctx: lightbulb.Context):
    guild = bot.cache.get_guild(ctx.guild_id)
    member = guild.get_member(ctx.author.id)
    if not config["adminRole"] in member.role_ids:
        await ctx.respond("You do not have permission to use this command.", flags=hikari.MessageFlag.EPHEMERAL)
        return
    
    if not os.path.exists(os.path.normpath(os.path.join(meme_folder, str(ctx.options.messageId)))):
        await ctx.respond("Message not found.", flags=hikari.MessageFlag.EPHEMERAL)
        return
    
    os.remove(os.path.normpath(os.path.join(meme_folder, str(ctx.options.messageId))))
    await ctx.respond(f"Message {ctx.options.messageId} deleted.", flags=hikari.MessageFlag.EPHEMERAL)

@bot.command
@lightbulb.command("deleteall", "Delete all messages.")
@lightbulb.implements(lightbulb.SlashCommand)
async def delete_all_command(ctx: lightbulb.Context):
    guild = bot.cache.get_guild(ctx.guild_id)
    member = guild.get_member
    if not config["adminRole"] in member.role_ids:
        await ctx.respond("You do not have permission to use this command.", flags=hikari.MessageFlag.EPHEMERAL)
        return
    
    global confirm

    if confirm:
        shutil.rmtree(meme_folder)
        os.mkdir(meme_folder)
        await ctx.respond(f"Deleted all messages.", flags=hikari.MessageFlag.EPHEMERAL)
        confirm = False
        return
    
    confirm = True

    await ctx.respond(f"Resend this command to confirm.", flags=hikari.MessageFlag.EPHEMERAL)

if __name__ == "__main__":
    bot.run()