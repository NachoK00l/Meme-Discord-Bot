import os
import hikari.embeds
import yaml
import logging
import hikari
import lightbulb
from lightbulb.ext import tasks
import json
import shutil
from glob import glob
import random

confirm = False

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

favorites = {}

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

async def sendAsUser(userId, message, channelId, attachments=None):
    user = await bot.rest.fetch_user(user=userId)

    webhook = await bot.rest.create_webhook(
        channelId,
        name=user.username,
        avatar=user.avatar_url
    )

    await bot.rest.execute_webhook(
        webhook=webhook,
        token=webhook.token,
        content=message,
        username=user.username,
        avatar_url=user.avatar_url,
        attachments=attachments if attachments else None
    )

    await bot.rest.delete_webhook(webhook)

    logger.info(f"Sent message as user: {user.username}")

async def getWinner():
    memeInfos = []

    if not os.path.exists(meme_folder):
        logger.warning("Memes folder does not exist!")
        return
    
    messageIds = [ item for item in os.listdir(meme_folder) if os.path.isdir(os.path.join(meme_folder, item)) ]

    for messageId in messageIds:
        with open(os.path.join(meme_folder, messageId, "info.json"), 'r') as f:
            memeInfo = json.load(f)
            memeInfo["tiebreaker"] = random.random()
            memeInfos.append(memeInfo)

    memeInfos.sort(key=lambda x: x["score"] + x["tiebreaker"], reverse=True)

    logger.info(json.dumps(memeInfos, indent=4))

    return memeInfos[0]

async def sendMOTD():
    winnerData = await getWinner()

    winnerFolder = os.path.normpath(os.path.join(meme_folder, str(winnerData["id"])))

    if not os.path.exists(winnerFolder):
        logger.warning(f"Winner folder does not exist! (messageInfo: {json.dumps(winnerData, indent=4)})")
        return
    
    attachmentFiles = []

    for attachment in winnerData["attachments"]:
        attachmentFiles.append(hikari.File(os.path.join(winnerFolder, attachment), attachment))

    score = winnerData["score"]

    content = winnerData["content"] if winnerData["content"] else ""

    await sendAsUser(winnerData["author"], content + f"\n> Score: {score}", config['MOTDSettings']['channelId'], attachmentFiles)

    shutil.rmtree(meme_folder)

    os.mkdir(meme_folder)


@bot.listen(hikari.GuildMessageCreateEvent)
async def on_message_sent(event):
    if (config['MOTDSettings']['enabled']):
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

        message_info = {"id": event.message_id, "author": event.author.id, "content": event.content if event.content != None else "", "score": 0, "attachments": file_names}
        with open(os.path.join(message_folder, "info.json"), "w") as file:
            json.dump(message_info, file, indent=4)
            logger.info(f"Message {event.message_id} saved to {message_folder} (Info: {message_info})")
        
        for emoji in config['MOTDSettings']['reactionIcons']:
            await event.message.add_reaction(emoji[0])

        await event.message.add_reaction(config['MOTDSettings']['favoriteIcon'])



@bot.listen(hikari.GuildMessageDeleteEvent)
async def on_message_deleted(event):
    if (config['MOTDSettings']['enabled']):
        if (event.channel_id != config['channels']['memeChannel']):
            return

        message_folder = os.path.normpath(os.path.join(meme_folder, str(event.message_id)))

        if not os.path.exists(message_folder):
            logger.warning(f"Message {event.message_id} was deleted but no folder was found.")
            return
        
        shutil.rmtree(message_folder, ignore_errors=False)
        logger.info(f"Message {event.message_id} deleted from {meme_folder}")
    


@bot.listen(hikari.GuildMessageUpdateEvent)
async def on_message_updated(event):
    if (config['MOTDSettings']['enabled']):
        if (event.channel_id != config['channels']['memeChannel'] or event.author_id == config['botUserId']):
            return
        
        if (event.message.content == hikari.UNDEFINED):
            logger.info(f"Message embed was added and ignored.")
            return
        
        message_folder = os.path.normpath(os.path.join(meme_folder, str(event.message_id)))

        if not os.path.exists(message_folder):
            logger.warning(f"Message {event.message_id} was updated but no folder was found. (Message: {event.message})")
            return
        
        message_info = {}

        with open(os.path.join(message_folder, "info.json"), "r") as file:
            message_info = json.load(file)
            message_info["content"] = event.message.content if event.message.content != None else ""
        
        with open(os.path.join(message_folder, "info.json"), "w") as file:
            json.dump(message_info, file, indent=4)
            logger.info(f"Message {event.message_id} updated (Info: {message_info})")
        


@bot.listen(hikari.GuildReactionAddEvent)
async def on_reaction_added(event: hikari.GuildReactionAddEvent):
    if (config['MOTDSettings']['enabled']):
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
            
        if event.is_for_emoji(config['MOTDSettings']['favoriteIcon']):
            if event.user_id in favorites:
                await bot.rest.delete_reaction(channel=event.channel_id, message=event.message_id, emoji=config['MOTDSettings']['favoriteIcon'], user=event.user_id)
                return
            
            favorites[event.user_id] = event.message_id

            with open(os.path.join(message_folder, "info.json"), "r") as file:
                message_info = json.load(file)
                message_info["score"] += 1

            with open(os.path.join(message_folder, "info.json"), "w") as file:
                    json.dump(message_info, file, indent=4)
                    logger.info(f"Message {event.message_id} updated (Info: {message_info})")

            logger.info(f"Message {event.message_id} favorited by {event.user_id}")


            
@bot.listen(hikari.GuildReactionDeleteEvent)
async def on_reaction_deleted(event):
    if (config['MOTDSettings']['enabled']):
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
            
        if event.is_for_emoji(config['MOTDSettings']['favoriteIcon']):
            if event.user_id in favorites:
                del favorites[event.user_id]

                with open(os.path.join(message_folder, "info.json"), "r") as file:
                    message_info = json.load(file)
                    message_info["score"] -= 1

                with open(os.path.join(message_folder, "info.json"), "w") as file:
                    json.dump(message_info, file, indent=4)
                    logger.info(f"Message {event.message_id} updated (Info: {message_info})")

                logger.info(f"Message {event.message_id} unfavorited by {event.user_id}")
        

    

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
    
    if not os.path.exists(os.path.normpath(os.path.join(meme_folder, str(ctx.options.messageid)))):
        await ctx.respond("Message not found.", flags=hikari.MessageFlag.EPHEMERAL)
        return
    
    shutil.rmtree(os.path.normpath(os.path.join(meme_folder, str(ctx.options.messageid))))
    await ctx.respond(f"Message {ctx.options.messageid} deleted.", flags=hikari.MessageFlag.EPHEMERAL)

@bot.command
@lightbulb.command("deleteall", "Delete all messages.")
@lightbulb.implements(lightbulb.SlashCommand)
async def delete_all_command(ctx: lightbulb.Context):
    guild = bot.cache.get_guild(ctx.guild_id)
    member = guild.get_member(ctx.author.id)
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

@bot.command
@lightbulb.command("runmotd", "Manualy run the MOTD.")
@lightbulb.implements(lightbulb.SlashCommand)
async def run_motd_command(ctx: lightbulb.Context):
    guild = bot.cache.get_guild(ctx.guild_id)
    member = guild.get_member(ctx.author.id)
    if not config["adminRole"] in member.role_ids:
        await ctx.respond("You do not have permission to use this command.", flags=hikari.MessageFlag.EPHEMERAL)
        return

    await sendMOTD()

    await ctx.respond(f"MOTD sent.", flags=hikari.MessageFlag.EPHEMERAL)


@tasks.task(tasks.CronTrigger(hour=config['MOTDSettings']['time']['hour'], minute=config['MOTDSettings']['time']['minute'], second=config['MOTDSettings']['time']['second']))
async def MOTDTrigger():
    await sendMOTD()

if __name__ == "__main__":
    if (config['MOTDSettings']['enabled']):
        MOTDTrigger.start()

    bot.run()