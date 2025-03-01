# Discord ExportBot

A powerful utility for transferring Discord message exports to live Discord channels. This tool allows you to read message JSON exports and either:

1. Display them in the terminal/console (local mode)
2. Post them to a Discord channel through a bot (discord mode)

## ✨ Features

- **Ultra-Fast:** Transfers messages at speeds up to 45/second (Discord API rate limit is 50/second)
- **Easy Setup:** Simple command-line interface and guided setup process
- **Flexible:** Works with different Discord export JSON formats
- **Clean:** Option to automatically delete previous bot messages
- **Complete:** Includes timestamps, usernames, attachments, embeds, and reactions

## 📋 Requirements

- Python 3.6 or higher
- discord.py library
- A Discord bot token (instructions below)
- Discrub Chrome extension (for exporting Discord messages)

## 🔧 Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/discord-exportbot.git
   cd discord-exportbot
   ```

2. Install the required Python package:
   ```
   pip install discord.py
   ```

3. Place your Discord message export file in the same directory (default name: `messages.json`)

## 📤 Exporting Discord Messages with Discrub

1. Install [Discrub from Chrome Web Store](https://chromewebstore.google.com/detail/discrub/plhdclenpaecffbcefjmpkkbdpkmhhbj?hl=en-US)
2. Open Discord in your browser
3. Click on the Discrub extension menu
4. Click on "Direct Messages" 
5. Select the conversation you want to export
6. Configure export settings:
   - Set "Messages Per Page" to 1,000,000 (or maximum)
   - Sort by "Ascending" (oldest first)
   - Enable "Include Preview"
   - Enable "Download Media"
   - Enable "Include Reactions"
7. Click "Export" and select JSON format
8. Save the file as `messages.json` in the same directory as exportbot.py

## 🤖 Creating a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under "TOKEN", click "Copy" to copy your bot token
5. **Important:** Enable the "Message Content Intent" under "Privileged Gateway Intents"
6. Go to "OAuth2" → "URL Generator"
7. Select scopes: "bot"
8. Select bot permissions: "Read Messages/View Channels", "Send Messages", "Read Message History", "Manage Messages" (for cleanup feature)
9. Use the generated URL to invite the bot to your server

## 💬 Usage

### Basic Discord Mode (Default)

```bash
python exportbot.py
```

This will:
1. Ask for your bot token on first run (stored in config.json)
2. Ask which channel to post messages to
3. Transfer all messages from messages.json to the Discord channel

### Advanced Discord Mode

```bash
python exportbot.py discord --file custom.json --limit 100 --reverse --clean --channel 123456789012345678
```

Options:
- `--file, -f`: Specify a different JSON file (default: messages.json)
- `--limit, -l`: Limit the number of messages to transfer
- `--reverse, -r`: Transfer newest messages first (default is oldest first)
- `--clean, -C`: Delete previous messages sent by this bot in the channel
- `--channel, -c`: Specify the Discord channel ID
- `--token, -t`: Provide Discord bot token (will be saved to config.json)

### Local Mode (No Discord)

```bash
python exportbot.py local --file export.json --user "johndoe" --search "hello" --output results.txt
```

Options:
- `--file, -f`: Specify input JSON file (default: messages.json)
- `--user, -u`: Filter messages by username
- `--search, -s`: Search for messages containing specific text
- `--output, -o`: Save output to a text file
- `--width, -w`: Set terminal width for text wrapping (default: 80)
- `--limit, -l`: Limit number of messages displayed
- `--reverse, -r`: Show newest messages first

## 🚀 Examples

**Transfer 50 most recent messages:**
```bash
python exportbot.py --limit 50 --reverse
```

**Clean up previous bot messages and post new ones:**
```bash
python exportbot.py --clean
```

**Filter messages locally from a specific user:**
```bash
python exportbot.py local --user "username" --output user_messages.txt
```

**Search for messages containing specific text:**
```bash
python exportbot.py local --search "keyword" --output search_results.txt
```

## 💾 JSON Format

This script is designed to work with Discord message exports, which contain an array of message objects with fields like:
- `id`: Message ID
- `author`: Object containing username and global_name
- `content`: The message text
- `timestamp`: When the message was sent
- `attachments`: Array of attachments (if any)
- `embeds`: Array of embeds (if any)

## 🔑 Configuration

The bot stores its configuration in `config.json`:
- `token`: Your Discord bot token
- `channel_id`: Last used Discord channel ID

You can modify this file directly or use command-line arguments to override settings.

## 🛠 Troubleshooting

**Bot token invalid:**
- Ensure you've copied the token correctly from the Discord Developer Portal
- Delete config.json to force the bot to ask for the token again

**"Privileged Intents Required" error:**
- Go to the Discord Developer Portal
- Select your application → Bot tab
- Enable "Message Content Intent" under "Privileged Gateway Intents"

**Messages not appearing:**
- Verify the bot has permission to read and send messages in the channel
- Check the JSON file format matches the expected format

## 📞 Need Help?

If you need help with this tool, please contact me through my Discord profile.

## 📄 License

MIT 