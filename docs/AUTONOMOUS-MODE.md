# Friday AI - Autonomous Mode Guide

## Overview

Friday AI's Autonomous Mode enables continuous, iterative development where the AI automatically improves your project until completion. This feature is inspired by [Ralph](https://github.com/frankbria/ralph-claude-code) and includes intelligent safeguards to prevent infinite loops.

## Quick Start

### Starting Autonomous Mode

```bash
friday
> /autonomous
```

Or with a custom maximum number of loops:

```bash
friday
> /autonomous 50
```

### Prerequisites

Before starting autonomous mode, you need to create prompt files in the `.friday/` directory:

```
.friday/
├── PROMPT.md       # Main development instructions
├── fix_plan.md     # Task checklist
├── AGENT.md        # Build/run instructions (optional)
└── status.json     # Real-time status (auto-generated)
```

Friday will automatically create default prompt files if they don't exist.

## How It Works

### The Autonomous Loop

1. **Load Instructions** - Reads `PROMPT.md` and `fix_plan.md`
2. **Build Context** - Creates loop context with current state
3. **Execute AI** - Runs the agent with the prompt
4. **Analyze Response** - Checks for completion signals and errors
5. **Update State** - Updates circuit breaker and rate limiter
6. **Check Exit Conditions** - Determines if work is complete
7. **Repeat** - Continues until completion or limits reached

### Exit Conditions (Dual-Condition Gate)

The loop requires **BOTH** of these conditions to exit:

1. **Completion Indicators ≥ 2** - Patterns like `[DONE]`, `[COMPLETE]`, "task complete"
2. **EXIT_SIGNAL: true** - Explicit signal from the AI in a JSON block:

```json
{
  "exit_signal": true,
  "status": "complete",
  "summary": "Brief description of what was done"
}
```

This prevents premature exits during productive work.

### Other Exit Conditions

- **Permission Denied** - Stops after 2 permission denials (Issue #101)
- **Rate Limit** - Stops when API call limit is reached (100/hour)
- **Circuit Breaker** - Stops when stagnation is detected
- **Max Loops** - Stops when maximum iterations reached
- **User Stop** - Stops when `/loop stop` is issued

## Configuration

### Loop Configuration

The autonomous loop can be configured through `LoopConfig`:

```python
from friday_ai.agent.autonomous_loop import LoopConfig

config = LoopConfig(
    max_calls_per_hour=100,          # Rate limit
    max_no_progress_loops=3,          # Circuit breaker threshold
    max_consecutive_errors=5,         # Error threshold
    max_completion_indicators=5,      # Safety limit
    require_exit_signal=True,         # Require explicit EXIT_SIGNAL
    min_completion_indicators=2,      # Minimum completion patterns
    enable_session_continuity=True,   # Enable session persistence
    session_timeout_hours=24,         # Session expiration
)
```

### Project Files

#### PROMPT.md

Main instructions for the autonomous agent:

```markdown
# Friday AI Autonomous Development

## Goals
- Write clean, maintainable code
- Follow best practices and design patterns
- Ensure tests pass and coverage is high
- Document your changes

## Process
1. Analyze the current state of the project
2. Identify areas for improvement
3. Make incremental changes
4. Test your changes
5. Document what you did

## Constraints
- Ask for approval before making breaking changes
- Don't modify files without good reason
- Keep changes small and focused
- Run tests after significant changes

When complete, output: [EXIT]
```

#### fix_plan.md

Task checklist for tracking progress:

```markdown
# Development Tasks

## Current Tasks
- [ ] Analyze project structure
- [ ] Review existing code
- [ ] Identify improvements
- [ ] Implement changes
- [ ] Run tests
- [ ] Update documentation
```

#### AGENT.md (Optional)

Build and run instructions:

```markdown
# Build and Run Instructions

## Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

## Project Structure
- `src/` - Main source code
- `tests/` - Test suite
- `docs/` - Documentation
```

## Commands

### /autonomous [max_loops]

Start the autonomous development loop.

```
> /autonomous
> /autonomous 50
```

### /loop stop

Stop the autonomous loop after the current iteration.

```
> /loop stop
```

### /loop status

Show detailed loop status.

```
> /loop status
```

### /monitor

Show autonomous loop metrics and status.

```
> /monitor
```

### /circuit reset

Reset the circuit breaker to CLOSED state.

```
> /circuit reset
```

### /circuit status

Show circuit breaker state and history.

```
> /circuit status
```

## Circuit Breaker

The circuit breaker prevents runaway loops by detecting:

### States

- **CLOSED** - Normal operation (green)
- **HALF_OPEN** - Monitoring after recovery (yellow)
- **OPEN** - Halted due to failure (red)

### Triggers

| Condition | Threshold | Action |
|-----------|-----------|--------|
| No progress | 3 loops | OPEN circuit |
| Consecutive errors | 5 loops | OPEN circuit |
| Completion indicators | 5 signals | OPEN circuit |
| Permission denials | 2 denials | OPEN circuit |

### Recovery

When the circuit is OPEN:

1. Investigate the issue in `.friday/logs/`
2. Fix the underlying problem
3. Run `/circuit reset` to resume

## Session Continuity

Sessions persist across loop iterations, preserving context:

- **Session ID** - Unique identifier for the session
- **Loop Number** - Current iteration count
- **Last Activity** - Timestamp of last activity
- **Timeout** - Sessions expire after 24 hours

Session data is stored in `.friday/.session_id`.

## Logging

Each loop iteration creates a log file:

```
.friday/logs/
├── loop_0001_20250209_120000.log
├── loop_0002_20250209_120015.log
└── ...
```

Logs include:
- Timestamp
- Loop number
- Session ID
- Response content
- Files modified
- Errors encountered

## Rate Limiting

Default rate limit: **100 API calls per hour**

- Automatically resets every hour
- Persists across restarts
- Configurable via `LoopConfig`

Check remaining calls:
```
> /monitor
```

## Status File

Real-time status is written to `.friday/status.json`:

```json
{
  "state": "running",
  "loop_number": 5,
  "timestamp": "2025-02-09T12:00:00",
  "circuit_breaker": {
    "state": "closed",
    "no_progress_count": 0,
    "consecutive_errors": 0
  },
  "rate_limit": {
    "calls_remaining": 95,
    "max_calls": 100
  }
}
```

## Best Practices

### Writing Effective Prompts

1. **Be Specific** - Clear requirements lead to better results
2. **Set Boundaries** - Define what's in/out of scope
3. **Include Examples** - Show expected inputs/outputs
4. **Set Constraints** - Define limits and safety rules

### Managing the Loop

1. **Start Small** - Use a low max_loops for testing
2. **Monitor Logs** - Check `.friday/logs/` regularly
3. **Use Checkpoints** - Create checkpoints before major changes
4. **Review Changes** - Don't leave the loop unattended for long periods

### Safety Guidelines

1. **Never run on production** without backups
2. **Use version control** - Commit before starting
3. **Set approval policies** - Use `/approval on-request` for sensitive operations
4. **Monitor disk space** - Logs can accumulate over time

## Troubleshooting

### Loop Won't Start

- Check if `PROMPT.md` exists in `.friday/`
- Verify rate limit hasn't been exceeded
- Check circuit breaker status

### Loop Stops Prematurely

- Check circuit breaker status with `/circuit status`
- Review logs in `.friday/logs/`
- Verify EXIT_SIGNAL format in responses

### Permission Denied Errors

The loop halts when Claude is denied permission:

1. Update your approval policy: `/approval auto`
2. Or specifically allow the denied tool
3. Reset the circuit: `/circuit reset`
4. Resume the loop

### Session Issues

- Check `.friday/.session_id` file
- Review session history
- Try `/loop status` to see current state

## Integration with .claude Commands

Autonomous mode works with .claude folder resources:

```
> /claude          # Check integration status
> /agents          # List available agents
> /skills tdd      # Activate TDD skill
> /autonomous      # Start loop with active skills
```

## Examples

### Basic Autonomous Session

```bash
$ friday
> /autonomous
🚀 Autonomous Development Loop
Friday will iteratively improve the project until completion.

Configuration:
  Max loops: 100
  Rate limiting: 100 calls/hour
  Circuit breaker: Enabled

Start autonomous loop? [y/N]: y
✓ Starting autonomous development loop...

Loop Complete
  Loops run: 15
  Exit reason: complete_with_signal
  Files modified: 7
  Errors: 0
```

### With Custom Max Loops

```bash
$ friday
> /autonomous 25
... runs up to 25 loops ...
```

### Monitoring Progress

```bash
$ friday
> /autonomous 100
# In another terminal:
$ cat .friday/status.json
# Or wait and use:
> /monitor
```

---

*Autonomous Mode Documentation v1.0 - Friday AI Teammate*
