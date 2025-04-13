# Discord MOTD Bot Docker Setup

This repository contains Dockerized version of the Discord MOTD (Message of the Day) bot.

## Setup Instructions

### Prerequisites
- Docker and Docker Compose installed on your machine
- A Discord bot token and other required configuration values

### Configuration
1. Copy the `config.yml.example` file to `config.yml`:
   ```bash
   cp config.yml.example config.yml
   ```

2. Edit the `config.yml` file with your Discord bot configuration:
   - Add your bot token
   - Set the bot user ID
   - Configure admin role ID
   - Set up channel IDs for meme channel, logs channel, and MOTD channel

### Running the Bot
To start the bot, run:
```bash
docker-compose up -d
```

To stop the bot:
```bash
docker-compose down
```

### Viewing Logs
To view the logs from the bot:
```bash
docker-compose logs -f
```

### Persistent Data
The bot's meme data is stored in a Docker volume named `meme-data`. This ensures that data persists even if the container is restarted or rebuilt.

### Updating the Bot
To update the bot with new code:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Commands
The bot provides several commands:
- `/restart` - Restart the bot (admin only)
- `/delete messageid` - Delete a specific message (admin only)
- `/deleteall` - Delete all messages (admin only)
- `/runmotd` - Manually run the MOTD (admin only)