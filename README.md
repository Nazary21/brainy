# Brainy - AI Bot Manager

A flexible Python-based system that manages AI-powered bots across multiple messaging platforms with customizable personalities and extensive memory capabilities.

## Overview

Brainy acts as an intermediate API manager that connects various AI providers (OpenAI, Grok, DeepSeek, etc.) with messaging platforms like Telegram. The system features customizable bot personalities, an advanced memory management system, and extensible functionality through modules.

## Key Features

- **Multiple AI Provider Support**: Connect to OpenAI, Grok, and more with a unified interface
- **Messaging Platform Integration**: Starting with Telegram, expandable to other platforms
- **Advanced Memory System**: Retrieval-augmented generation for coherent, context-aware conversations
- **Customizable Bot Personas**: Tailor bot personalities and behaviors to different use cases
- **Modular Architecture**: Extensible with custom modules for specialized functionality
- **Web Dashboard**: Configure and manage your bots through a clean interface

## Development Status

This project is in active development. See [dev-progress.md](dev-progress.md) for current status.

## Setup & Installation

### Prerequisites

- Python 3.9 or higher
- Rust toolchain (for chromadb and pydantic-core dependencies)
  ```bash
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
  ```
- Docker (for containerized deployment)
- Telegram Bot Token (from BotFather)
- OpenAI API Key
- Railway account (for deployment)

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/Nazary21/brainy.git
   cd brainy
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. Run the application:
   ```bash
   python run.py
   # or
   python -m brainy.main
   ```

### Testing the Telegram Integration

1. Create a Telegram bot using BotFather (https://t.me/botfather)
2. Copy the API token to your `.env` file under `TELEGRAM_BOT_TOKEN`
3. Start the application and open your bot in Telegram
4. Try the following commands:
   - `/start` - Begin a conversation
   - `/help` - See available commands
   - `/character <id>` - Change the bot's personality
   - `/characters` - List available personalities
   - `/remind <time> <unit> <message>` - Set a reminder (e.g. `/remind 5 minutes check oven`)
   - `/reminders` - List your active reminders
   - `/clear_reminders` - Clear all your reminders

You can also use natural language to interact with the module system:
- "Remind me to check the oven in 10 minutes"
- "Set a reminder for taking medication in 4 hours"
- "Remind me call mom in 1 day"

### Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t brainy .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 --env-file .env brainy
   ```

## Project Structure

```
brainy/
├── core/                      # Core system components
│   ├── conversation/          # Conversation handling
│   ├── character/             # Character system
│   ├── memory_manager/        # Memory and context management
│   └── modules/               # Module system
├── adapters/                  # Pluggable adapter interfaces
│   ├── ai/                    # AI provider adapters
│   └── messengers/            # Messaging platform adapters
├── config/                    # Configuration management
├── utils/                     # Shared utilities and helpers
└── tests/                     # Test files
```

See [specs.md](specs.md) for detailed system architecture and component descriptions.

## Module System

Brainy features an extensible module system that allows for adding new functionality through modules. Currently implemented modules include:

- **Reminder Module**: Set and manage reminders with commands or natural language
  - Commands: `/remind`, `/reminders`, `/clear_reminders`
  - Natural language: "remind me to do something in X minutes"

To implement a new module:
1. Create a class that inherits from `Module` base class
2. Register command handlers and trigger patterns
3. Implement the `process_message` method
4. Register the module in `brainy/core/modules/registry.py`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 