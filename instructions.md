# Brainy Bot - User Instructions

This document provides instructions on how to use the Brainy bot, including all available commands and features.

## Getting Started

1. Start a conversation with the bot by sending the `/start` command.
2. The bot will respond with a greeting using the default character.
3. You can then interact with the bot by sending messages.

## Available Commands

### Basic Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Start a conversation with the bot | `/start` |
| `/help` | Display help information about all available commands | `/help` |
| `/clear` | Clear the current conversation history | `/clear` |

### Character Management Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/character <id>` | Switch to a specific character | `/character professor` |
| `/characters` | List all available characters | `/characters` |
| `/create_character` | Create a new character | See details below |
| `/edit_character` | Edit an existing character | See details below |
| `/delete_character <id>` | Delete a character | `/delete_character chef` |

#### Creating a Character

To create a new character, use the `/create_character` command with the following parameters:

```
/create_character id=<id> name=<name> prompt=<system_prompt> [description=<description>] [greeting=<greeting>] [farewell=<farewell>]
```

Required parameters:
- `id`: A unique identifier for the character (use only letters, numbers, and underscores)
- `name`: The display name of the character
- `prompt`: The system prompt that defines the character's personality and behavior

Optional parameters:
- `description`: A short description of the character
- `greeting`: A custom greeting message when switching to this character
- `farewell`: A custom farewell message when switching away from this character
- `avatar`: URL to an avatar image for the character

Example:
```
/create_character id=chef name="Chef Bot" prompt="You are a helpful chef assistant who provides cooking tips and recipes." description="A helpful cooking assistant" greeting="Hello! Ready to cook something delicious?" farewell="Goodbye! Happy cooking!"
```

**Note:** Keep character IDs simple and memorable. Character IDs are case-insensitive when using them (e.g., "Chef" and "chef" are treated as the same ID), but the original case is preserved for display purposes.

#### Editing a Character

To edit an existing character, use the `/edit_character` command with the following parameters:

```
/edit_character id=<id> [name=<name>] [prompt=<system_prompt>] [description=<description>] [greeting=<greeting>] [farewell=<farewell>]
```

Required parameters:
- `id`: The identifier of the character to edit

Optional parameters (at least one must be provided):
- `name`: New display name
- `prompt`: New system prompt
- `description`: New description
- `greeting`: New greeting message
- `farewell`: New farewell message
- `avatar`: New avatar URL

Example:
```
/edit_character id=chef name="Master Chef" prompt="You are a professional chef with expertise in international cuisine."
```

#### Deleting a Character

To delete a character, use the `/delete_character` command followed by the character ID:

```
/delete_character <character_id>
```

Example:
```
/delete_character chef
```

**Note:** You cannot delete the default character.

#### Switching Characters

To switch to a different character, use the `/character` command followed by the character ID:

```
/character <character_id>
```

Example:
```
/character professor
```

**Important Tips:**
- Character IDs are case-insensitive when referencing them in commands
- Do not include a slash before the character ID (use `/character chef`, not `/character /chef`)
- After creating a new character, you can immediately switch to it using the `/character` command
- Use `/characters` to see a list of all available characters and their IDs

### AI Provider Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/provider` | View or change the AI provider for the current conversation | `/provider` |
| `/provider <provider_id>` | Change to a specific AI provider | `/provider grok` |

Available provider IDs:
- `openai` - OpenAI (GPT-3.5/GPT-4)
- `grok` - Grok AI

### Reminder Module Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/remind <time> <unit> <task>` | Set a reminder | `/remind 30 minutes Check the oven` |
| `/reminders` | List all pending reminders | `/reminders` |
| `/clear_reminders` | Clear all reminders | `/clear_reminders` |

You can also set reminders conversationally by saying phrases like:
- "Remind me to check the oven in 30 minutes"
- "Set a reminder for my meeting in 2 hours"

## Natural Language Interactions

In addition to commands, Brainy understands natural language requests for various functions:

### Reminders
- "Remind me to call John in 2 hours"
- "Set a reminder for my meeting at 3 PM"
- "Can you remind me to take my medicine in 30 minutes?"

## Switching Characters and Providers

You can switch between different AI characters and providers at any time using the appropriate commands. This allows you to tailor the bot's personality and capabilities to your specific needs.

### Character Switching

1. To see available characters: `/characters`
2. To switch to a specific character: `/character <id>`
   - Example: `/character professor`

The bot will respond with a confirmation message and a greeting from the new character.

### Provider Switching

1. To see the current provider or available providers: `/provider`
2. To switch to a specific provider: `/provider <provider_id>`
   - Example: `/provider grok`

The bot will confirm the provider change and use the new provider for subsequent messages.

## Best Practices

1. **Clear context when needed**: If the conversation gets off track, use `/clear` to start fresh.
2. **Use specific characters for specific tasks**: Different characters have different strengths.
3. **Create custom characters**: Use `/create_character` to create personas tailored to your needs.
4. **Experiment with different providers**: Try both OpenAI and Grok to see which works best for your use case.
5. **Create characters with descriptive IDs**: Choose IDs that reflect the character's purpose (e.g., "chef", "teacher", "therapist").
6. **Use detailed system prompts**: The more specific your character's system prompt, the better it will perform its role.

## Troubleshooting

If you encounter issues with the bot:

1. Try the `/clear` command to reset the conversation context.
2. Check if you're using the correct command syntax.
3. If a command doesn't work, try sending `/help` to see a list of available commands.
4. When switching characters, make sure you're using the exact character ID as shown in the `/characters` list.
5. If you can't switch to a character you just created, try using `/characters` to verify it was created successfully.
6. For persistent issues, contact the bot administrator. 