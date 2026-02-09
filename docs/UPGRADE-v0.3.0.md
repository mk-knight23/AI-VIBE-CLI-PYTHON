# Friday AI v0.3.0 - Major Upgrade

## Overview

This is a major upgrade from v0.2.0 to v0.3.0 that completes the integration of the `.claude` folder resources, enhances the autonomous development loop with Ralph patterns, and adds comprehensive session management.

## Version Information

- **Previous Version**: 0.2.0
- **New Version**: 0.3.0
- **Release Date**: February 2025
- **Status**: Feature Complete

## What's New

### 1. Enhanced Autonomous Loop (Ralph Integration Complete)

The autonomous loop has been significantly enhanced with features from Ralph:

#### Response Analysis
- **JSON Response Parsing** - Extracts structured data from Claude's JSON output
- **Two-Stage Error Filtering** - Eliminates false positives from JSON fields
- **Permission Denial Detection** - Handles permission issues (Issue #101)
- **Session ID Extraction** - Maintains continuity across iterations
- **Completion Indicators** - Smart pattern matching for completion signals

#### Circuit Breaker
- **Three States** - CLOSED, HALF_OPEN, OPEN with proper transitions
- **Permission Denial Threshold** - Opens after 2 permission denials
- **Output Decline Detection** - Monitors for significant output reduction
- **State History Tracking** - Logs all state changes for debugging

#### Session Continuity
- **Persistent Sessions** - Sessions survive across loop restarts
- **24-Hour Expiration** - Configurable session timeout
- **Loop Number Tracking** - Maintains iteration count
- **Session File** - Stored in `.friday/.session_id`

#### Status File Updates
- **Real-time Status** - `.friday/status.json` updated each iteration
- **Progress Tracking** - Loop number, circuit breaker state, rate limits
- **JSON Format** - Machine-readable for external monitoring

### 2. Complete .claude Integration

Full integration with the `.claude` folder structure:

#### Commands (`/command`)
All commands from `.claude/commands/` are now available:
- `/plan` - Use planner agent for implementation planning
- `/tdd` - Test-driven development workflow
- `/code-review` - Code review agent
- `/go-test` - Go testing with coverage
- `/go-build` - Fix Go build errors
- `/test-coverage` - Check test coverage
- `/refactor-clean` - Clean up dead code
- `/update-docs` - Update documentation
- `/update-codemaps` - Update codemaps
- And more...

#### Agents (`/agents`)
- List available agents: `/agents`
- Agents can be invoked via commands or workflows

#### Skills (`/skills`)
- List skills: `/skills`
- Activate skills: `/skills <name>`
- Active skills affect agent behavior

#### Workflows (`/workflow`)
- Run workflows: `/workflow <name>`
- Step-by-step execution with progress tracking
- Event-based updates

### 3. Enhanced CLI Commands

#### Loop Control
- `/autonomous [max_loops]` - Start autonomous loop
- `/loop stop` - Stop the loop gracefully
- `/loop status` - Show detailed status
- `/monitor` - Show metrics and status

#### Circuit Breaker Control
- `/circuit reset` - Reset to CLOSED state
- `/circuit open` - Manually open
- `/circuit close` - Close (same as reset)
- `/circuit status` - Show state and history

### 4. New Documentation

- `docs/AUTONOMOUS-MODE.md` - Complete autonomous mode guide
- `docs/SESSION-MANAGEMENT.md` - Session management guide
- `docs/UPGRADE-v0.3.0.md` - This document

## Technical Details

### Architecture Changes

#### ResponseAnalyzer
```python
class ResponseAnalyzer:
    def analyze(self, response: str) -> ResponseAnalysis
    def _try_parse_json(self, response: str) -> dict | None
    def _detect_errors(self, response: str) -> tuple[bool, int]
    def extract_session_id(self, response: str) -> str | None
```

#### CircuitBreaker
```python
class CircuitBreaker:
    def update(self, has_files_changed, has_errors, has_completion,
               has_permission_denials, output_length) -> CircuitBreakerState
    def reset(self) -> None
    def get_history(self) -> list[dict]
```

#### AutonomousLoop
```python
class AutonomousLoop:
    async def run(self, max_loops: int = 100) -> dict[str, Any]
    def _load_session(self) -> None
    def _save_session(self) -> None
    def _update_status_file(self, state: str, extra: dict | None) -> None
    def stop(self) -> None
```

### Exit Conditions (Dual-Condition Gate)

The loop requires BOTH:
1. `completion_indicators >= 2`
2. `EXIT_SIGNAL: true`

```json
{
  "exit_signal": true,
  "status": "complete",
  "summary": "Work completed successfully"
}
```

### Circuit Breaker Thresholds

| Condition | Threshold | Result |
|-----------|-----------|--------|
| No progress | 3 loops | OPEN |
| Consecutive errors | 5 loops | OPEN |
| Completion indicators | 5 signals | OPEN |
| Permission denials | 2 denials | OPEN |

## Migration Guide

### From v0.2.0 to v0.3.0

1. **Update package**:
   ```bash
   pip install --upgrade friday-ai-teammate
   ```

2. **No breaking changes** - All v0.2.0 features are preserved

3. **New features are opt-in**:
   - Autonomous mode requires explicit `/autonomous` command
   - .claude integration is automatic if `.claude/` folder exists

4. **Configuration changes**:
   - New `.friday/` directory for autonomous mode files
   - Session files now stored in `.friday/sessions/`

### Using New Features

#### Autonomous Mode

```bash
# Create project structure
mkdir -p .friday

# Create prompt files (or let Friday create defaults)
friday
> /autonomous

# Monitor progress
> /monitor

# Stop if needed
> /loop stop
```

#### .claude Commands

```bash
# Initialize .claude folder
mkdir -p .claude/{agents,skills,commands,workflows}

# Use commands
friday
> /plan "Implement user authentication"
> /tdd
> /code-review
```

## Configuration

### LoopConfig

```python
from friday_ai.agent.autonomous_loop import LoopConfig

config = LoopConfig(
    max_calls_per_hour=100,
    max_no_progress_loops=3,
    max_consecutive_errors=5,
    max_completion_indicators=5,
    require_exit_signal=True,
    min_completion_indicators=2,
    enable_session_continuity=True,
    session_timeout_hours=24,
)
```

### Project Structure

```
.friday/
├── PROMPT.md          # Development instructions
├── fix_plan.md       # Task list
├── AGENT.md          # Build instructions
├── status.json       # Current status
├── .session_id       # Session continuity
├── .call_count       # Rate limit state
└── logs/             # Execution logs
    ├── loop_0001_20250209_120000.log
    └── ...
```

## Performance Considerations

### Rate Limiting
- Default: 100 API calls per hour
- Automatic hourly reset
- Persistent across restarts

### Session Memory
- Sessions expire after 24 hours
- History limited to 100 entries
- Log rotation recommended for long runs

### Circuit Breaker
- Prevents infinite loops
- Configurable thresholds
- Manual control available

## Troubleshooting

### Loop Won't Start
- Check if PROMPT.md exists in `.friday/`
- Verify rate limit hasn't been exceeded
- Check circuit breaker status: `/circuit status`

### Loop Stops Prematurely
- Check circuit breaker status
- Review logs in `.friday/logs/`
- Verify EXIT_SIGNAL format

### Session Issues
- Check `.friday/.session_id` file
- Review session history
- Try `/resume` to see available sessions

### .claude Integration Not Working
- Verify `.claude/` folder exists
- Check folder structure: agents/, skills/, commands/, workflows/
- Use `/claude` to check integration status

## Known Issues

1. **Context Window** - Very long sessions may hit context limits
2. **Disk Space** - Logs accumulate over time in `.friday/logs/`
3. **Session Size** - Large sessions may take time to save/load

## Future Enhancements

### Planned for v0.4.0
- Web-based monitoring dashboard
- Multi-agent orchestration in autonomous mode
- Parallel execution of independent tasks
- Enhanced metrics and reporting
- Custom loop strategies

### Under Consideration
- Integration with CI/CD pipelines
- Advanced debugging tools
- Performance profiling
- Team session sharing

## Contributors

This release was built with:
- Ralph integration patterns from frankbria/ralph-claude-code
- .claude folder structure and best practices
- Community feedback and testing

## Support

- **Issues**: GitHub Issues
- **Documentation**: docs/
- **Examples**: .claude/ and ralph-claude-code/

---

**Friday AI Teammate v0.3.0** - Your intelligent coding companion, now with complete autonomous development capabilities!
