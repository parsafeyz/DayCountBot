# DayCountBot

```
daycount/
├── bot.py              # Main entry point, bot initialization, handler registration
├── config.py           # Configuration (admin ID, bot token, defaults)
├── database.py         # SQLite async database layer (aiosqlite)
├── models.py           # Dataclasses for Task, Schedule, etc.
├── handlers/
│   ├── __init__.py     # Exports all handlers
│   ├── start.py        # /start command handler
│   ├── create.py       # /create wizard (ConversationHandler)
│   ├── list_tasks.py   # /list command
│   ├── edit.py         # /edit command (ConversationHandler)
│   ├── delete.py       # /delete command
│   ├── pause_resume.py # /pause, /resume commands
│   └── status.py       # /status command
├── scheduler.py        # APScheduler integration, job management
├── renderer.py         # Message template rendering (fill placeholders)
├── requirements.txt    # Dependencies
└── README.md           # Usage instructions
```
