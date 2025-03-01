import json
import datetime
import textwrap
import argparse
import os
import sys
from typing import Dict, List, Any, Optional, TextIO

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

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process and display Discord messages from a JSON file.')
    parser.add_argument('--file', '-f', default='messages.json', help='Path to the JSON file (default: messages.json)')
    parser.add_argument('--user', '-u', help='Filter messages by username or global name')
    parser.add_argument('--limit', '-l', type=int, help='Limit the number of messages displayed')
    parser.add_argument('--output', '-o', help='Save output to a file')
    parser.add_argument('--width', '-w', type=int, default=80, help='Terminal width for text wrapping (default: 80)')
    parser.add_argument('--reverse', '-r', action='store_true', help='Show newest messages first')
    parser.add_argument('--search', '-s', help='Search for messages containing specific text')
    args = parser.parse_args()
    
    # Set up output file if specified
    output_file = None
    if args.output:
        try:
            output_file = open(args.output, 'w', encoding='utf-8')
        except Exception as e:
            print(f"Error opening output file: {str(e)}")
            return
    
    try:
        # Load messages
        messages = load_messages(args.file)
        
        if not messages:
            print("No messages found or error loading messages.", file=output_file)
            if output_file:
                output_file.close()
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
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        if output_file:
            output_file.close()
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        if output_file:
            output_file.close()

# This ensures that when this file is imported, the main() function doesn't run
# But when executed directly, it does run
if __name__ == "__main__":
    main()
