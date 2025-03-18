# Brainy Chatbot UX Patterns

This document outlines the standardized UX patterns that all modules should follow to provide a consistent user experience.

## Command Response Patterns

### 1. Command Help (No Arguments)

When a user invokes a command without required arguments, always provide:

- Emoji-prefixed title indicating the command purpose
- Clear usage instructions with proper formatting (using backticks)
- Multiple concrete examples
- Related commands the user might need

Example:
```
⏰ **Reminder Help**

To set a reminder, use the format:
`/remind <time> <unit> <message>`

📝 **Examples:**
• `/remind 5 minutes check oven`
• `/remind 1 hour call mom`
• `/remind 2 days review document`

⚙️ **Available Commands:**
• `/reminders` - List your active reminders
• `/clear_reminders` - Delete all reminders
```

### 2. Success States

Always provide clear success feedback when a user's action is completed successfully:

- Use ✅ emoji to indicate success
- Bold the success message
- Include a summary of what was created/changed
- Show relevant details about the created item
- Indicate any follow-up actions available

Example:
```
✅ **Reminder Set!**

I'll remind you about: "check email"

⏰ Due in: 30 minutes
📅 Date: Monday, Mar 18
🕒 Time: 06:30 PM

You now have 3 active reminders. Use /reminders to see all.
```

### 3. Error States

For error scenarios, provide clear guidance on what went wrong and how to fix it:

- Use ⚠️ emoji for warnings and errors
- Clearly state what went wrong
- Provide suggestions on how to correct the error
- Include examples where appropriate

Example:
```
⚠️ Please provide a positive number for the time.

Try: `/remind 5 minutes check email`
```

### 4. Empty State Listings

When a user requests to see a list of items (reminders, notes, etc.) but none exist:

- Be friendly and informative
- Explain how to create the first item
- Include a complete example command

Example:
```
You don't have any active reminders. Use `/remind <time> <unit> <message>` to set one.

Example: `/remind 30 minutes check email`
```

### 5. List Views

When displaying lists of items:

- Use consistent emoji prefixes for categories
- Number items clearly
- Format dates and times in a human-readable way
- Include clear instructions for related actions

Example:
```
📋 Your active reminders:

⏰ 1. "Check email"
   Due: Monday, Mar 18 at 06:30 PM
   Time remaining: 30 minutes

⏰ 2. "Call John"
   Due: Tuesday, Mar 19 at 10:00 AM
   Time remaining: 1 day, 15 hours

To clear all reminders, use /clear_reminders
```

## Text Formatting Guidelines

- Use **bold** for titles and important information
- Use `code formatting` for commands and inputs
- Use bullet points (•) for lists of examples or options
- Use emojis consistently for visual categorization:
  - ✅ Success states
  - ⚠️ Warnings and errors
  - ⏰ Time-related items
  - 📋 Lists
  - 📝 Examples/instructions

## Date and Time Formatting

- Format dates as: "Day of week, Month Day" (e.g., "Monday, Mar 18")
- Format times as: "HH:MM AM/PM" (e.g., "06:30 PM")
- Format durations in a human-readable way (e.g., "30 minutes" or "1 day, 15 hours")

## Message Length Guidelines

- Keep success messages concise but informative
- For help text, provide comprehensive information
- Limit list responses to a reasonable number of items (5-10)
- For longer lists, consider pagination or summarization

## Future Patterns to Consider

- Confirmation for destructive actions
- Interactive buttons (when platform supports them)
- Inline help with command suggestions
- Progressive disclosure of complex information 