import discord
from discord.ext import commands
import os
import json
import datetime
import asyncio
import argparse
import textwrap
from typing import Dict, List, Any, Optional, TextIO

# Configuration
TOKEN_FILE = "config.json"  # Where the bot token is stored
DEFAULT_JSON_FILE = "messages.json"  # Default file containing Discord messages
BATCH_SIZE = 5  # Reduced batch size to avoid rate limits
DELAY_BETWEEN_MESSAGES = 0.25  # Add delay between individual messages
MAX_RATE = 5  # Much more conservative rate limit
DEFAULT_PREFIX = "!"  # Command prefix for bot commands

def format_timestamp(timestamp: str) -> str:
    """Format the Discord timestamp to a readable format."""
    try:
        # Discord timestamps look like: "2023-01-01T12:34:56.789+00:00"
        dt = datetime.datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp

def wrap_text(text: str, width: int = 80) -> str:
    """Wrap text to a specified width."""
    if not text:
        return ""
    
    lines = []
    for line in text.split('\n'):
        if len(line) <= width:
            lines.append(line)
        else:
            wrapped = textwrap.wrap(line, width=width)
            lines.extend(wrapped)
    
    return '\n'.join(lines)

def load_messages(file_path: str) -> List[Dict[str, Any]]:
    """
    Load messages from the JSON file.
    Handles different Discord export formats.
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Handle different JSON structures
            if isinstance(data, list):
                # Direct list of messages
                return data
            elif isinstance(data, dict):
                # Check for known export formats
                if 'messages' in data:
                    # Standard Discord export format
                    return data['messages']
                elif 'channel' in data and 'messages' in data:
                    # Another common format
                    return data['messages']
                elif 'guild' in data and 'channels' in data:
                    # Guild export with multiple channels
                    print("Guild export detected with multiple channels. Please specify a channel export file.")
                    return []
                else:
                    # Try to find a list of messages in any field
                    for key, value in data.items():
                        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                            if all(isinstance(item, dict) and 'author' in item and 'content' in item and 'timestamp' in item for item in value[:5]):
                                print(f"Found messages in field '{key}'")
                                return value
                    
                    print("Unknown JSON structure. Please check the file format.")
                    return []
            else:
                print("Invalid JSON format. Expected a list or dictionary.")
                return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {str(e)}")
        return []
    except Exception as e:
        print(f"Error loading messages: {str(e)}")
        return []

def print_message(message: Dict[str, Any], width: int = 80, file: Optional[TextIO] = None) -> None:
    """Print a single message in a readable format."""
    # Get author name (prefer global_name if available, otherwise username)
    author = message.get('author', {})
    author_name = author.get('global_name') or author.get('username') or 'Unknown User'
    
    # Get message content
    content = message.get('content', '')
    wrapped_content = wrap_text(content, width=width)
    
    # Get timestamp
    timestamp = format_timestamp(message.get('timestamp', ''))
    
    # Print the message
    print(f"[{timestamp}] {author_name}:", file=file)
    if wrapped_content:
        print(wrapped_content, file=file)
    
    # Check for attachments
    attachments = message.get('attachments', [])
    if attachments:
        print(f"  Attachments ({len(attachments)}):", file=file)
        for i, attachment in enumerate(attachments, 1):
            url = attachment.get('url', 'No URL')
            filename = attachment.get('filename', 'Unknown file')
            print(f"  {i}. {filename}", file=file)
            print(f"     {url}", file=file)
    
    # Check for embeds
    embeds = message.get('embeds', [])
    if embeds:
        print(f"  Embeds ({len(embeds)}):", file=file)
        for i, embed in enumerate(embeds, 1):
            title = embed.get('title', 'No Title')
            url = embed.get('url', '')
            description = embed.get('description', '')
            
            print(f"  {i}. {title}", file=file)
            if url:
                print(f"     URL: {url}", file=file)
            if description:
                wrapped_desc = wrap_text(description, width=width-5)
                indented_desc = '\n'.join(f"     {line}" for line in wrapped_desc.split('\n'))
                print(indented_desc, file=file)
    
    # Check for reactions
    reactions = message.get('reactions', [])
    if reactions:
        reaction_str = "  Reactions: "
        for reaction in reactions:
            emoji = reaction.get('emoji', {})
            emoji_name = emoji.get('name', '')
            count = reaction.get('count', 0)
            reaction_str += f"{emoji_name} ({count}) "
        print(reaction_str, file=file)
    
    # Print a separator for readability
    print("-" * width, file=file)

def load_config():
    """Load bot configuration from config.json file."""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    else:
        return {}

def save_config(config):
    """Save bot configuration to config.json file."""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# Initialize the bot with intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
bot = commands.Bot(command_prefix=DEFAULT_PREFIX, intents=intents, help_command=None)

@bot.event
async def on_ready():
    """Event triggered when the bot is ready and connected to Discord."""
    print(f'Bot is connected as {bot.user.name} (ID: {bot.user.id})')
    print(f'Bot is in {len(bot.guilds)} servers')
    for guild in bot.guilds:
        print(f'- {guild.name} (ID: {guild.id})')
        for channel in guild.text_channels:
            print(f'  - #{channel.name} (ID: {channel.id})')
    print('------')
    print('Bot is ready!')
    print('Use "!post" to post messages from messages.json to the current channel')
    print('Or run the auto-post mode by providing channel ID as command line argument')
    
    # Check if we should auto-post based on command line arguments
    if hasattr(bot, 'auto_post_channel_id') and bot.auto_post_channel_id:
        channel = bot.get_channel(bot.auto_post_channel_id)
        if channel:
            print(f"\nAuto-posting messages to #{channel.name}...")
            
            # Ask about deleting all messages in channel
            if hasattr(bot, 'delete_all_messages') and bot.delete_all_messages:
                await delete_all_channel_messages(channel)
                
            await auto_post_messages(channel, 
                                   clean=bot.auto_post_clean, 
                                   limit=bot.auto_post_limit, 
                                   reverse=bot.auto_post_reverse)
        else:
            print(f"\nError: Could not find channel with ID {bot.auto_post_channel_id}")

@bot.command(name="help")
async def help_command(ctx):
    """Display help information about the bot."""
    help_text = """
**Discord ExportBot Commands**

`!help` - Shows this help message
`!post [limit]` - Posts messages from messages.json to this channel (limit is optional)
`!reverse` - Posts messages in reverse order (newest first)
`!filter <username>` - Only post messages from a specific user
`!search <term>` - Only post messages containing a specific term
`!clean` - Clean up previous messages sent by this bot in the channel
`!deleteall` - Delete ALL messages in the channel (use with caution!)
    """
    await ctx.send(help_text)

@bot.command(name="post")
async def post_command(ctx, limit: int = None, *, options: str = ""):
    """Post messages from messages.json to the current channel."""
    # Send a temporary message that will be deleted after 5 seconds
    await ctx.send("📥 Loading messages from messages.json... Please wait.", delete_after=5)
    
    # Parse options
    reverse = False
    filter_user = None
    search_term = None
    
    if "reverse" in options.lower():
        reverse = True
    
    if "filter:" in options.lower():
        parts = options.lower().split("filter:")
        if len(parts) > 1:
            filter_user = parts[1].split()[0].strip()
    
    if "search:" in options.lower():
        parts = options.lower().split("search:")
        if len(parts) > 1:
            search_term = parts[1].split()[0].strip()
    
    # Load messages from messages.json
    messages = load_messages("messages.json")
    
    if not messages:
        await ctx.send("❌ No messages found in messages.json or error loading file.")
        return
    
    # Sort messages by timestamp
    sorted_messages = sorted(messages, key=lambda m: m.get('timestamp', ''))
    if reverse:
        sorted_messages.reverse()
    
    # Filter messages by user if specified
    if filter_user:
        filtered_messages = []
        for message in sorted_messages:
            author = message.get('author', {})
            global_name = (author.get('global_name') or '').lower()
            username = (author.get('username') or '').lower()
            
            if filter_user.lower() in global_name or filter_user.lower() in username:
                filtered_messages.append(message)
        sorted_messages = filtered_messages
    
    # Filter messages by search term if specified
    if search_term:
        search_messages = []
        for message in sorted_messages:
            content = (message.get('content') or '').lower()
            if search_term.lower() in content:
                search_messages.append(message)
        sorted_messages = search_messages
    
    # Limit the number of messages if specified
    if limit and limit > 0:
        sorted_messages = sorted_messages[:limit]
    
    total_messages = len(sorted_messages)
    
    # Calculate and display estimated completion time - ONLY IN CONSOLE
    expected_rate = 4.0  # Expected messages per second
    estimated_seconds = total_messages / expected_rate
    estimated_time = datetime.timedelta(seconds=estimated_seconds)
    estimated_completion = datetime.datetime.now() + estimated_time
    
    # Only print to console, don't send to Discord
    print(f"Found {total_messages} messages. Posting them now...")
    print(f"Estimated time to completion: {str(estimated_time).split('.')[0]}")
    print(f"Expected to finish at: {estimated_completion.strftime('%H:%M:%S')}")
    
    # Post messages individually with delay to avoid rate limits
    start_time = datetime.datetime.now()
    last_update_time = start_time
    
    for i, msg in enumerate(sorted_messages):
        # Format the message
        author = msg.get('author', {})
        author_name = author.get('global_name') or author.get('username') or 'Unknown User'
        content = msg.get('content', '')
        timestamp = format_timestamp(msg.get('timestamp', ''))
        
        # Create message text in the specified format
        msg_text = f"[{timestamp}] {author_name}: {content}"
        
        # Send message
        try:
            await ctx.send(msg_text[:2000])  # Discord has a 2000 character limit
            
            # Update time estimates more frequently - every message multiple of 20 or every 30 seconds
            current_time = datetime.datetime.now()
            time_since_update = (current_time - last_update_time).total_seconds()
            
            if (i + 1) % 20 == 0 or i == total_messages - 1 or time_since_update >= 30:
                progress = i + 1
                elapsed = (current_time - start_time).total_seconds()
                rate = progress / elapsed if elapsed > 0 else 0
                percentage = (progress / total_messages) * 100
                
                # Update time estimates
                remaining_messages = total_messages - progress
                remaining_time = remaining_messages / rate if rate > 0 else 0
                new_eta = datetime.datetime.now() + datetime.timedelta(seconds=remaining_time)
                
                # Only print to console, don't send to Discord
                print(f"Posted {progress}/{total_messages} messages ({percentage:.1f}%, {rate:.1f} msgs/sec)")
                print(f"Estimated time remaining: {str(datetime.timedelta(seconds=int(remaining_time))).split('.')[0]}")
                print(f"New ETA: {new_eta.strftime('%H:%M:%S')}")
                
                # Update the last update time
                last_update_time = current_time
            
            # Add delay to avoid rate limits
            await asyncio.sleep(DELAY_BETWEEN_MESSAGES)
            
        except Exception as e:
            print(f"❌ Error posting message: {str(e)}")
            await asyncio.sleep(1)  # Longer delay if there's an error
    
    # All messages have been sent
    end_time = datetime.datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    print(f"✅ Finished posting {len(sorted_messages)} messages in {elapsed:.2f} seconds.")
    
    # Only send a simple completion message
    await ctx.send(f"✅ Finished posting {len(sorted_messages)} messages from messages.json", delete_after=30)

@bot.command(name="filter")
async def filter_command(ctx, username: str, limit: int = None):
    """Filter and post messages from a specific user."""
    await post_command(ctx, limit, options=f"filter:{username}")

@bot.command(name="search")
async def search_command(ctx, term: str, limit: int = None):
    """Search and post messages containing a specific term."""
    await post_command(ctx, limit, options=f"search:{term}")

@bot.command(name="reverse")
async def reverse_command(ctx, limit: int = None):
    """Post messages in reverse order (newest first)."""
    await post_command(ctx, limit, options="reverse")

@bot.command(name="clean")
async def clean_command(ctx):
    """Clean up previous messages sent by this bot in the channel."""
    await ctx.send("🧹 Cleaning up previous messages from this bot...")
    
    deleted_count = 0
    start_time = datetime.datetime.now()
    
    try:
        async for message in ctx.channel.history(limit=500):
            # Only delete messages from this bot
            if message.author.id == bot.user.id:
                await message.delete()
                deleted_count += 1
                
                # Add a small delay to prevent rate limiting
                if deleted_count % 5 == 0:
                    await asyncio.sleep(1)
                    await ctx.send(f"Deleted {deleted_count} messages...", delete_after=2)
        
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        await ctx.send(f"✅ Cleanup complete! Deleted {deleted_count} messages in {elapsed:.2f} seconds.")
    
    except discord.errors.Forbidden:
        await ctx.send("❌ Error: Bot doesn't have permission to delete messages.")
    except Exception as e:
        await ctx.send(f"❌ Error during cleanup: {e}")

@bot.command(name="deleteall")
async def deleteall_command(ctx):
    """Delete ALL messages in the channel."""
    confirmation = await ctx.send("⚠️ **WARNING**: This will delete ALL messages in this channel. Type `!confirm` within 10 seconds to proceed.")
    
    def check(message):
        return message.content.lower() == "!confirm" and message.author == ctx.author
    
    try:
        await bot.wait_for('message', check=check, timeout=10.0)
        await delete_all_channel_messages(ctx.channel)
    except asyncio.TimeoutError:
        await confirmation.edit(content="Operation cancelled. No messages were deleted.")
        
async def delete_all_channel_messages(channel):
    """Delete all messages in a channel."""
    try:
        await channel.send("🧹 Deleting ALL messages in this channel...")
        deleted_count = 0
        start_time = datetime.datetime.now()
        
        # Delete messages in chunks to avoid rate limits
        while True:
            messages = []
            async for message in channel.history(limit=100):
                messages.append(message)
                
            if not messages:
                break
                
            # If more than one message, use bulk delete
            if len(messages) > 1 and (datetime.datetime.now() - messages[-1].created_at).days < 14:
                try:
                    await channel.delete_messages(messages)
                    deleted_count += len(messages)
                    await asyncio.sleep(1)  # Avoid rate limits
                except discord.errors.HTTPException:
                    # If bulk delete fails, delete one by one
                    for message in messages:
                        try:
                            await message.delete()
                            deleted_count += 1
                            await asyncio.sleep(0.5)  # Avoid rate limits
                        except:
                            pass
            else:
                # Delete one by one for older messages
                for message in messages:
                    try:
                        await message.delete()
                        deleted_count += 1
                        await asyncio.sleep(0.5)  # Avoid rate limits
                    except:
                        pass
            
            # Provide status update
            elapsed = (datetime.datetime.now() - start_time).total_seconds()
            print(f"Deleted {deleted_count} messages... ({deleted_count/elapsed:.1f} msgs/sec)")
        
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        await channel.send(f"✅ Finished deleting {deleted_count} messages in {elapsed:.2f} seconds.")
        
    except discord.errors.Forbidden:
        await channel.send("❌ Error: Bot doesn't have permission to manage messages.")
    except Exception as e:
        await channel.send(f"❌ Error during deletion: {e}")

async def auto_post_messages(channel, clean=False, limit=None, reverse=False):
    """Post messages from messages.json to the specified channel automatically."""
    # First, clean up old messages if requested
    if clean:
        print("Cleaning up previous messages from this bot...")
        
        deleted_count = 0
        start_time = datetime.datetime.now()
        
        try:
            async for message in channel.history(limit=500):
                # Only delete messages from this bot
                if message.author.id == bot.user.id:
                    await message.delete()
                    deleted_count += 1
                    
                    # Add a small delay to prevent rate limiting
                    if deleted_count % 5 == 0:
                        await asyncio.sleep(1)
                        elapsed = (datetime.datetime.now() - start_time).total_seconds()
                        rate = deleted_count / elapsed if elapsed > 0 else 0
                        print(f"Deleted {deleted_count} messages... ({rate:.1f} msgs/sec)")
            
            elapsed = (datetime.datetime.now() - start_time).total_seconds()
            print(f"Cleanup complete! Deleted {deleted_count} messages in {elapsed:.2f} seconds.")
            
            # Add a small delay after cleanup to ensure Discord's cache updates
            await asyncio.sleep(1)
        
        except discord.errors.Forbidden:
            print("Error: Bot doesn't have permission to delete messages.")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    # Load messages from the JSON file
    print("Loading messages from messages.json...")
    messages = load_messages("messages.json")
    
    if not messages:
        print("No messages found in messages.json or error loading file.")
        return
    
    # Sort messages by timestamp
    sorted_messages = sorted(messages, key=lambda m: m.get('timestamp', ''))
    if reverse:
        sorted_messages.reverse()
    
    # Apply limit if specified
    if limit and limit > 0:
        sorted_messages = sorted_messages[:limit]
    
    total_messages = len(sorted_messages)
    
    # Calculate and display estimated completion time
    expected_rate = 4.0  # Expected messages per second based on our delay settings
    estimated_seconds = total_messages / expected_rate
    estimated_time = datetime.timedelta(seconds=estimated_seconds)
    estimated_completion = datetime.datetime.now() + estimated_time
    
    print(f"Found {total_messages} messages. Posting them now...")
    print(f"Estimated time to completion: {str(estimated_time).split('.')[0]}")
    print(f"Expected to finish at: {estimated_completion.strftime('%H:%M:%S')}")
    
    # Send initial message to verify permissions
    try:
        # Only send a notice message that will disappear after 5 seconds
        await channel.send("Starting to post messages from messages.json...", delete_after=5)
    except Exception as e:
        print(f"Error: Could not send messages to this channel. {e}")
        return
    
    # Process messages individually with controlled delays
    start_time = datetime.datetime.now()
    last_update_time = start_time
    
    for i, msg in enumerate(sorted_messages):
        # Format the message
        author = msg.get('author', {})
        author_name = author.get('global_name') or author.get('username') or 'Unknown User'
        content = msg.get('content', '')
        timestamp = format_timestamp(msg.get('timestamp', ''))
        
        # Create message text exactly as requested
        msg_text = f"[{timestamp}] {author_name}: {content}"
        
        # Send message with error handling
        try:
            await channel.send(msg_text[:2000])  # Discord has a 2000 character limit
            
            # Update time estimates more frequently - every message multiple of 20 or every 30 seconds
            current_time = datetime.datetime.now()
            time_since_update = (current_time - last_update_time).total_seconds()
            
            if (i + 1) % 20 == 0 or i == total_messages - 1 or time_since_update >= 30:
                progress = i + 1
                elapsed = (current_time - start_time).total_seconds()
                rate = progress / elapsed if elapsed > 0 else 0
                percentage = (progress / total_messages) * 100
                
                # Update time estimates
                remaining_messages = total_messages - progress
                remaining_time = remaining_messages / rate if rate > 0 else 0
                new_eta = datetime.datetime.now() + datetime.timedelta(seconds=remaining_time)
                
                # Only print to console, don't send to Discord
                print(f"Posted {progress}/{total_messages} messages ({percentage:.1f}%, {rate:.1f} msgs/sec)")
                print(f"Estimated time remaining: {str(datetime.timedelta(seconds=int(remaining_time))).split('.')[0]}")
                print(f"New ETA: {new_eta.strftime('%H:%M:%S')}")
                
                # Update the last update time
                last_update_time = current_time
            
            # Add small delay between messages to avoid rate limits
            await asyncio.sleep(DELAY_BETWEEN_MESSAGES)
            
        except discord.errors.HTTPException as e:
            # If we hit a rate limit, wait longer
            if e.status == 429:
                print(f"Rate limited. Waiting 2 seconds...")
                await asyncio.sleep(2)
                # Try again
                try:
                    await channel.send(msg_text[:2000])
                except:
                    print(f"Failed to send message after retry: {msg_text[:50]}...")
            else:
                print(f"HTTP error: {e}")
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"Error posting message: {e}")
            await asyncio.sleep(1)
    
    # All messages have been sent
    end_time = datetime.datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    print(f"✅ Finished posting all {total_messages} messages in {elapsed:.2f} seconds.")
    print(f"Average rate: {total_messages/elapsed:.2f} messages per second")
    
    # Send completion message that will disappear after 30 seconds
    await channel.send(f"✅ Finished posting {total_messages} messages from messages.json", delete_after=30)

def setup_bot():
    """Set up the bot configuration."""
    config = load_config()
    
    if 'token' not in config or config['token'] == "YOUR_BOT_TOKEN_HERE":
        print("\n========== DISCORD BOT TOKEN SETUP ==========")
        print("Bot token not found in config.json or needs to be updated.")
        print("You can get a token from https://discord.com/developers/applications")
        print("Be sure to enable all Privileged Gateway Intents in the Bot settings!")
        token = input("Please enter your Discord bot token: ").strip()
        config['token'] = token
        save_config(config)
        print("Token saved to config.json")
        print("=============================================\n")
    
    return config

async def process_json_file(args):
    """Process a JSON file directly without Discord."""
    # Load messages
    messages = load_messages(args.file)
    
    if not messages:
        print("No messages found or error loading messages.")
        return
    
    # Sort messages by timestamp
    sorted_messages = sorted(messages, key=lambda m: m.get('timestamp', ''))
    if args.reverse:
        sorted_messages.reverse()
    
    # Filter messages by user if specified
    if args.user:
        user_lower = args.user.lower()
        filtered_messages = []
        for message in sorted_messages:
            author = message.get('author', {})
            global_name = (author.get('global_name') or '').lower()
            username = (author.get('username') or '').lower()
            
            if user_lower in global_name or user_lower in username:
                filtered_messages.append(message)
        sorted_messages = filtered_messages
    
    # Filter messages by search term if specified
    if args.search:
        search_lower = args.search.lower()
        search_messages = []
        for message in sorted_messages:
            content = (message.get('content') or '').lower()
            if search_lower in content:
                search_messages.append(message)
        sorted_messages = search_messages
    
    # Limit the number of messages if specified
    if args.limit and args.limit > 0:
        sorted_messages = sorted_messages[:args.limit]
    
    # Set up output file if specified
    output_file = None
    if args.output:
        try:
            output_file = open(args.output, 'w', encoding='utf-8')
        except Exception as e:
            print(f"Error opening output file: {str(e)}")
            return
    
    # Print header
    print(f"Displaying {len(sorted_messages)} messages from {args.file}", file=output_file)
    if args.user:
        print(f"Filtered by user: {args.user}", file=output_file)
    if args.search:
        print(f"Searched for: {args.search}", file=output_file)
    if args.limit:
        print(f"Limited to {args.limit} messages", file=output_file)
    print("-" * args.width, file=output_file)
    
    # Print all messages
    for message in sorted_messages:
        print_message(message, width=args.width, file=output_file)
    
    # Close output file if opened
    if output_file:
        print(f"Output saved to {args.output}")
        output_file.close()

def main():
    """Main function to handle command line arguments and run the appropriate function."""
    parser = argparse.ArgumentParser(description='Discord ExportBot: Process and transfer Discord messages.')
    
    # Add shared arguments
    parser.add_argument('--file', '-f', default=DEFAULT_JSON_FILE, help=f'Path to the JSON file (default: {DEFAULT_JSON_FILE})')
    parser.add_argument('--limit', '-l', type=int, help='Limit the number of messages processed')
    parser.add_argument('--reverse', '-r', action='store_true', help='Process messages in reverse order (newest first)')
    parser.add_argument('--channel', '-c', type=int, help='Discord channel ID to post messages to')
    parser.add_argument('--clean', '-C', action='store_true', help='Clean up previous bot messages in the channel')
    parser.add_argument('--token', '-t', help='Discord bot token (will be saved to config.json)')
    parser.add_argument('--deleteall', '-D', action='store_true', help='Delete ALL messages in the channel before posting')
    
    # Create subparsers for different modes
    subparsers = parser.add_subparsers(dest='mode', help='Operating mode')
    
    # Local processing mode
    local_parser = subparsers.add_parser('local', help='Process messages locally (no Discord)')
    local_parser.add_argument('--user', '-u', help='Filter messages by username or global name')
    local_parser.add_argument('--output', '-o', help='Save output to a file')
    local_parser.add_argument('--width', '-w', type=int, default=80, help='Terminal width for text wrapping (default: 80)')
    local_parser.add_argument('--search', '-s', help='Search for messages containing specific text')
    
    # Interactive mode
    interactive_parser = subparsers.add_parser('interactive', help='Run the interactive bot with commands')
    
    args = parser.parse_args()
    
    # If no mode is specified, use discord mode by default
    if not args.mode:
        args.mode = 'discord'
        
    if args.mode == 'local':
        # Process JSON file locally
        asyncio.run(process_json_file(args))
    elif args.mode == 'interactive':
        # Run the interactive bot
        config = setup_bot()
        
        if 'token' not in config:
            print("Error: Bot token not found and not provided.")
            return
        
        print("\n============== STARTING INTERACTIVE BOT ==============")
        print("Connecting to Discord...")
        print("If this is your first run, please ensure you have:")
        print("1. Enabled the Message Content Intent in the Discord Developer Portal")
        print("2. Invited the bot to your server")
        print("3. Given the bot proper permissions in your server")
        print("===================================================\n")
        
        try:
            bot.run(config['token'])
        except discord.errors.PrivilegedIntentsRequired:
            print("\n❌ ERROR: Privileged Intents Required")
            print("You need to enable the Message Content Intent in the Discord Developer Portal:")
            print("1. Go to https://discord.com/developers/applications")
            print("2. Select your bot application")
            print("3. Go to 'Bot' settings in the left sidebar")
            print("4. Scroll down to 'Privileged Gateway Intents'")
            print("5. Enable 'Message Content Intent'")
            print("6. Click 'Save Changes'")
            print("7. Restart this bot\n")
        except discord.errors.LoginFailure:
            print("\n❌ ERROR: Invalid Token")
            print("The token in your config.json file is invalid.")
            print("Please delete the config.json file and run the bot again to enter a new token.\n")
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}\n")
    else:  # discord mode
        # Setup bot configuration
        config = setup_bot()
        
        # Check for token in args or config
        if hasattr(args, 'token') and args.token:
            config['token'] = args.token
            save_config(config)
        
        if 'token' not in config:
            print("Error: Bot token not found and not provided.")
            return
        
        # Setup auto-post parameters
        bot.auto_post_channel_id = args.channel if hasattr(args, 'channel') and args.channel else None
        bot.auto_post_clean = args.clean if hasattr(args, 'clean') and args.clean else False
        bot.auto_post_limit = args.limit if hasattr(args, 'limit') and args.limit else None
        bot.auto_post_reverse = args.reverse if hasattr(args, 'reverse') and args.reverse else False
        bot.delete_all_messages = args.deleteall if hasattr(args, 'deleteall') and args.deleteall else False
        
        # Get channel ID from command line or ask user
        if not bot.auto_post_channel_id:
            print("IMPORTANT: You need to enter a CHANNEL ID, not a server/guild ID.")
            channel_id_input = input("Enter the ID of the channel to post messages to: ").strip()
            try:
                bot.auto_post_channel_id = int(channel_id_input)
            except ValueError:
                print("Invalid channel ID. Please enter a numeric ID.")
                return
        
        # Ask about cleaning up messages
        if not hasattr(args, 'clean') or (not args.clean and not args.clean == False):
            clean_input = input("Do you want to delete previous messages sent by this bot? (y/n): ").strip().lower()
            bot.auto_post_clean = clean_input.startswith('y')
            
        # Ask about deleting ALL messages
        if not bot.delete_all_messages:
            delete_all_input = input("Do you want to delete ALL messages in the channel before posting? (y/n): ").strip().lower()
            bot.delete_all_messages = delete_all_input.startswith('y')
            if bot.delete_all_messages:
                confirm = input("⚠️ WARNING: This will delete ALL messages in the channel. Type 'yes' to confirm: ").strip().lower()
                if confirm != 'yes':
                    print("Operation cancelled.")
                    bot.delete_all_messages = False
        
        print("\n============== STARTING DISCORD EXPORT BOT ==============")
        print(f"Reading messages from: {args.file}")
        if hasattr(args, 'limit') and args.limit:
            print(f"Limited to {args.limit} messages")
        if hasattr(args, 'reverse') and args.reverse:
            print("Processing messages in reverse order (newest first)")
        if bot.auto_post_clean:
            print("The bot will delete its previous messages in the channel")
        if bot.delete_all_messages:
            print("⚠️ The bot will delete ALL messages in the channel before posting")
        print("===================================================\n")
        
        try:
            bot.run(config['token'])
        except discord.errors.PrivilegedIntentsRequired:
            print("\n❌ ERROR: Privileged Intents Required")
            print("You need to enable the Message Content Intent in the Discord Developer Portal:")
            print("1. Go to https://discord.com/developers/applications")
            print("2. Select your bot application")
            print("3. Go to 'Bot' settings in the left sidebar")
            print("4. Scroll down to 'Privileged Gateway Intents'")
            print("5. Enable 'Message Content Intent'")
            print("6. Click 'Save Changes'")
            print("7. Restart this bot\n")
        except discord.errors.LoginFailure:
            print("\n❌ ERROR: Invalid Token")
            print("The token in your config.json file is invalid.")
            print("Please delete the config.json file and run the bot again to enter a new token.\n")
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}\n")

if __name__ == "__main__":
    main() 
