# Friday AI - Session Management Guide

## Overview

Friday AI provides comprehensive session management that allows you to save, resume, and track your conversations with the AI. Sessions persist across restarts and can be resumed at any time within the expiration window.

## Quick Start

### Saving a Session

```bash
friday
> /save
```

### Listing Saved Sessions

```bash
friday
> /sessions
```

### Resuming a Session

```bash
friday
> /resume <session_id>
```

Or use the interactive selector:

```bash
friday
> /resume
# Select from the list
```

## Session Concepts

### What is a Session?

A session represents a complete conversation context including:

- **Messages** - Full conversation history
- **Turn Count** - Number of exchanges
- **Usage Statistics** - Token usage information
- **Metadata** - Timestamps and custom data

### Session Types

1. **Active Session** - Currently loaded in memory
2. **Saved Session** - Persisted to disk
3. **Expired Session** - Beyond the timeout period (24 hours)

## Session Lifecycle

### 1. Creation

Sessions are automatically created when you start Friday:

```bash
friday
# New session created automatically
```

Or when resuming a previous session:

```bash
friday --resume
```

### 2. Activity

During the session, all interactions are tracked:

- User messages
- Assistant responses
- Tool calls and results
- Token usage

### 3. Persistence

Save the session explicitly:

```bash
> /save
```

Or create a named checkpoint:

```bash
> /checkpoint
```

### 4. Expiration

Sessions expire after 24 hours of inactivity. Expired sessions are still listed but marked as expired.

### 5. Resumption

Resume a previous session:

```bash
friday --resume                    # Interactive selection
friday --resume <session_id>       # Specific session
```

Or from within Friday:

```bash
> /resume <session_id>
```

## Commands

### /save

Save the current session.

```
> /save
✓ Session saved: session_20250209_120000_1234
```

### /sessions

List all saved sessions.

```
> /sessions

Saved Sessions
  • session_20250209_120000_1234 (turns: 15, updated: 2025-02-09T12:30:00)
  • session_20250208_100000_5678 (turns: 42, updated: 2025-02-08T11:00:00) [expired]
```

### /resume [session_id]

Resume a saved session.

```
> /resume session_20250209_120000_1234
✓ Resumed session: session_20250209_120000_1234

> /resume
Saved Sessions
  1. session_20250209_120000_1234 (turns: 15)
  2. session_20250208_100000_5678 (turns: 42)

Select session number: 1
✓ Resumed session: session_20250209_120000_1234
```

### /checkpoint

Create a checkpoint (named save point).

```
> /checkpoint
✓ Checkpoint created: checkpoint_20250209_123000_1
```

### /restore [checkpoint_id]

Restore from a checkpoint.

```
> /restore checkpoint_20250209_123000_1
✓ Restored session: session_20250209_120000_1234, checkpoint: checkpoint_20250209_123000_1
```

### CLI --resume Flag

Resume from the command line:

```bash
# Interactive selection
friday --resume

# Resume specific session
friday --resume session_20250209_120000_1234

# With a prompt
friday --resume "Continue where we left off"
```

## Session Storage

### File Locations

Sessions are stored in:

```
~/.config/friday/sessions/
├── session_20250209_120000_1234.json
├── session_20250208_100000_5678.json
└── ...
```

Checkpoints are stored in:

```
~/.config/friday/checkpoints/
├── checkpoint_20250209_123000_1.json
└── ...
```

### Session File Format

```json
{
  "session_id": "session_20250209_120000_1234",
  "created_at": "2025-02-09T12:00:00",
  "updated_at": "2025-02-09T12:30:00",
  "turn_count": 15,
  "total_usage": 15000,
  "messages": [
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hi there!"}
  ]
}
```

## Session Manager API

For programmatic access:

```python
from friday_ai.agent.session_manager import SessionManager, Session, SessionEventType

# Create manager
manager = SessionManager()

# Create a new session
session = manager.create_session(metadata={"project": "my-app"})

# Add events
session.add_event(SessionEventType.STARTED, "User initiated session")

# Get current session
current = manager.get_current_session()

# List all sessions
sessions = manager.list_sessions()

# Resume a session
resumed = manager.resume_session("session_20250209_120000_1234")

# Pause session
manager.pause_session()

# Stop session
manager.stop_session("User completed task")
```

## Session Events

Sessions track events for audit purposes:

```python
class SessionEventType(Enum):
    STARTED = "started"
    PAUSED = "paused"
    RESUMED = "resumed"
    STOPPED = "stopped"
    ERROR = "error"
    COMPLETED = "completed"
```

Event history is stored with each session and includes:
- Event type
- Timestamp
- Reason (optional)
- Metadata (optional)

## Autonomous Mode Sessions

In autonomous mode, sessions have additional tracking:

### Session Continuity

The autonomous loop maintains session continuity across iterations:

- **Session ID** persists across loop iterations
- **Loop Number** tracks progress
- **Last Activity** timestamp updated each iteration

### Configuration

```python
from friday_ai.agent.autonomous_loop import LoopConfig

config = LoopConfig(
    enable_session_continuity=True,
    session_timeout_hours=24,
    session_file=".friday/.session_id",
)
```

### Session File

Autonomous sessions store additional data:

```json
{
  "session_id": "abc12345",
  "loop_number": 15,
  "last_activity": "2025-02-09T12:30:00"
}
```

## Best Practices

### When to Save

- **Before major changes** - Create a checkpoint
- **After completing tasks** - Save the session
- **Before exiting** - Automatic, but explicit saves are safer
- **During long conversations** - Periodic saves prevent data loss

### Session Naming

Sessions are automatically named with timestamps:

```
session_YYYYMMDD_HHMMSS_XXXX
```

For better organization, use metadata:

```python
session = manager.create_session(metadata={
    "project": "api-refactor",
    "task": "migrate-to-fastapi"
})
```

### Cleaning Up

Sessions are not automatically deleted. To clean up:

1. List all sessions: `/sessions`
2. Manually delete old session files from `~/.config/friday/sessions/`
3. Or use the API: `manager.delete_session(session_id)`

## Troubleshooting

### Session Not Found

```
> /resume invalid_session
✗ Session not found
```

Check:
- Session ID spelling
- Session hasn't been deleted
- Session file exists in storage

### Session Expired

```
> /resume session_old
⚠ Session expired
```

Expired sessions are still listed but cannot be resumed. The data is preserved but the conversation context is stale.

### Resume Failed

```
> /resume session_20250209_120000_1234
✗ Error resuming session
```

Possible causes:
- Corrupted session file
- Version mismatch
- Missing dependencies

Workaround: Start a new session and manually reference previous work.

### Storage Issues

If sessions aren't persisting:

1. Check disk space
2. Verify write permissions to `~/.config/friday/`
3. Check for disk errors

## Integration with Workflows

Sessions work seamlessly with workflows:

```bash
# Start a workflow
> /workflow code-review

# Save progress
> /checkpoint

# Continue later
friday --resume
```

## Security Considerations

### Session Data

Session files contain conversation history. Be aware that:

- Sessions may contain sensitive information
- Files are stored as plain JSON
- Access controls depend on file system permissions

### Best Practices

1. **Don't commit sessions** - Add to `.gitignore`:
   ```
   .friday/sessions/
   ~/.config/friday/sessions/
   ```

2. **Clean up regularly** - Delete old sessions

3. **Use environment isolation** - Separate sessions per project

---

*Session Management Documentation v1.0 - Friday AI Teammate*
