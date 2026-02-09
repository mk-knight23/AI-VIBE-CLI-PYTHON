import asyncio
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any
import click
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from friday_ai.agent.agent import Agent

logger = logging.getLogger(__name__)
from friday_ai.agent.events import AgentEventType
from friday_ai.agent.persistence import PersistenceManager, SessionSnapshot
from friday_ai.agent.session import Session
from friday_ai.config.config import ApprovalPolicy, Config
from friday_ai.config.loader import load_config, get_data_dir
from friday_ai.ui.tui import TUI, get_console

console = get_console()

# Version information
__version__ = "1.0.0"


class CLI:
    def __init__(self, config: Config):
        self.agent: Agent | None = None
        self.config = config
        self.tui = TUI(config, console)
        self._claude_context: Any | None = None
        self._command_mapper: Any | None = None
        self._workflow_engine: Any | None = None

    def _init_claude_integration(self) -> None:
        """Initialize .claude folder integration if enabled."""
        if not self.config.claude_dir and not self.config.get_claude_dir():
            return

        try:
            from friday_ai.claude_integration import (
                ClaudeAgentLoader,
                CommandMapper,
                RulesEngine,
                SkillsManager,
                WorkflowEngine,
            )
            from friday_ai.claude_integration.context import ClaudeContext

            claude_dir = self.config.get_claude_dir()
            if not claude_dir:
                return

            # Initialize context
            self._claude_context = ClaudeContext(claude_dir=claude_dir)

            # Load agents
            if self.config.claude_agents_enabled:
                agent_loader = ClaudeAgentLoader(claude_dir)
                agents = agent_loader.load_all_agents()
                for agent_def in agents:
                    self._claude_context.agents[agent_def.name] = agent_def

            # Load skills
            if self.config.claude_skills_enabled:
                skills_manager = SkillsManager(claude_dir)
                skills = skills_manager.load_all_skills()
                for skill in skills:
                    self._claude_context.skills[skill.name] = skill

            # Load rules
            if self.config.claude_rules_enabled:
                rules_engine = RulesEngine(claude_dir)
                rules = rules_engine.load_all_rules()
                self._claude_context.rules = rules

            # Load workflows
            if self.config.claude_workflows_enabled:
                self._workflow_engine = WorkflowEngine(claude_dir)
                self._workflow_engine.load_all_workflows()
                for workflow in self._workflow_engine.list_workflows():
                    self._claude_context.workflows[workflow.name] = workflow

            # Load commands
            if self.config.claude_commands_enabled:
                self._command_mapper = CommandMapper(claude_dir)
                self._command_mapper.load_all_commands()
                for cmd in self._command_mapper.list_commands():
                    self._claude_context.commands[cmd.name] = cmd

        except Exception as e:
            logger.debug(f"Failed to initialize .claude integration: {e}")

    async def run_single(self, message: str) -> str | None:
        async with Agent(self.config) as agent:
            self.agent = agent
            return await self._process_message(message)

    async def run_interactive(self) -> str | None:
        self.tui.print_welcome(
            "Friday",
            lines=[
                f"model: {self.config.model_name}",
                f"cwd: {self.config.cwd}",
                "commands: /help /config /approval /model /exit",
            ],
        )

        async with Agent(
            self.config,
            confirmation_callback=self.tui.handle_confirmation,
        ) as agent:
            self.agent = agent

            while True:
                try:
                    user_input = console.input("\n[user]>[/user] ").strip()
                    if not user_input:
                        continue

                    if user_input.startswith("/"):
                        should_continue = await self._handle_command(user_input)
                        if not should_continue:
                            break
                        continue

                    await self._process_message(user_input)
                except KeyboardInterrupt:
                    console.print("\n[dim]Use /exit to quit[/dim]")
                except EOFError:
                    break

        console.print("\n[dim]Goodbye![/dim]")

    def _get_tool_kind(self, tool_name: str) -> str | None:
        tool = self.agent.session.tool_registry.get(tool_name)
        if not tool:
            return None

        return tool.kind.value

    async def _process_message(self, message: str) -> str | None:
        if not self.agent:
            return None

        assistant_streaming = False
        final_response: str | None = None

        async for event in self.agent.run(message):
            if event.type == AgentEventType.TEXT_DELTA:
                content = event.data.get("content", "")
                if not assistant_streaming:
                    self.tui.begin_assistant()
                    assistant_streaming = True
                self.tui.stream_assistant_delta(content)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")
                if assistant_streaming:
                    self.tui.end_assistant()
                    assistant_streaming = False
            elif event.type == AgentEventType.AGENT_ERROR:
                error = event.data.get("error", "Unknown error")
                console.print(f"\n[error]Error: {error}[/error]")
            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_start(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("arguments", {}),
                )
            elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_complete(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("success", False),
                    event.data.get("output", ""),
                    event.data.get("error"),
                    event.data.get("metadata"),
                    event.data.get("diff"),
                    event.data.get("truncated", False),
                    event.data.get("exit_code"),
                )

        return final_response

    async def _handle_command(self, command: str) -> bool:
        cmd = command.lower().strip()
        parts = cmd.split(maxsplit=1)
        cmd_name = parts[0]
        cmd_args = parts[1] if len(parts) > 1 else ""

        if cmd_name == "/exit" or cmd_name == "/quit":
            return False
        elif command == "/help":
            self.tui.show_help()
        elif command == "/clear":
            self.agent.session.context_manager.clear()
            self.agent.session.loop_detector.clear()
            console.print("[success]Conversation cleared [/success]")
        elif command == "/config":
            console.print("\n[bold]Current Configuration[/bold]")
            console.print(f"  Model: {self.config.model_name}")
            console.print(f"  Temperature: {self.config.temperature}")
            console.print(f"  Approval: {self.config.approval.value}")
            console.print(f"  Working Dir: {self.config.cwd}")
            console.print(f"  Max Turns: {self.config.max_turns}")
            console.print(f"  Hooks Enabled: {self.config.hooks_enabled}")
        elif cmd_name == "/model":
            if cmd_args:
                self.config.model_name = cmd_args
                console.print(f"[success]Model changed to: {cmd_args} [/success]")
            else:
                console.print(f"Current model: {self.config.model_name}")
        elif cmd_name == "/approval":
            if cmd_args:
                try:
                    approval = ApprovalPolicy(cmd_args)
                    self.config.approval = approval
                    console.print(
                        f"[success]Approval policy changed to: {cmd_args} [/success]"
                    )
                except:
                    console.print(
                        f"[error]Incorrect approval policy: {cmd_args} [/error]"
                    )
                    console.print(
                        f"Valid options: {', '.join(p for p in ApprovalPolicy)}"
                    )
            else:
                console.print(f"Current approval policy: {self.config.approval.value}")
        elif cmd_name == "/stats":
            stats = self.agent.session.get_stats()
            console.print("\n[bold]Session Statistics [/bold]")
            for key, value in stats.items():
                console.print(f"   {key}: {value}")
        elif cmd_name == "/tools":
            tools = self.agent.session.tool_registry.get_tools()
            console.print(f"\n[bold]Available tools ({len(tools)}) [/bold]")
            for tool in tools:
                console.print(f"  • {tool.name}")
        elif cmd_name == "/mcp":
            mcp_servers = self.agent.session.mcp_manager.get_all_servers()
            console.print(f"\n[bold]MCP Servers ({len(mcp_servers)}) [/bold]")
            for server in mcp_servers:
                status = server["status"]
                status_color = "green" if status == "connected" else "red"
                console.print(
                    f"  • {server['name']}: [{status_color}]{status}[/{status_color}] ({server['tools']} tools)"
                )
        elif cmd_name == "/save":
            persistence_manager = PersistenceManager()
            session_snapshot = SessionSnapshot(
                session_id=self.agent.session.session_id,
                created_at=self.agent.session.created_at,
                updated_at=self.agent.session.updated_at,
                turn_count=self.agent.session.turn_count,
                messages=self.agent.session.context_manager.get_messages(),
                total_usage=self.agent.session.context_manager.total_usage,
            )
            persistence_manager.save_session(session_snapshot)
            console.print(
                f"[success]Session saved: {self.agent.session.session_id}[/success]"
            )
        elif cmd_name == "/sessions":
            persistence_manager = PersistenceManager()
            sessions = persistence_manager.list_sessions()
            console.print("\n[bold]Saved Sessions[/bold]")
            for s in sessions:
                console.print(
                    f"  • {s['session_id']} (turns: {s['turn_count']}, updated: {s['updated_at']})"
                )
        elif cmd_name == "/resume":
            if not cmd_args:
                console.print(f"[error]Usage: /resume <session_id> [/error]")
            else:
                persistence_manager = PersistenceManager()
                snapshot = persistence_manager.load_session(cmd_args)
                if not snapshot:
                    console.print(f"[error]Session does not exist [/error]")
                else:
                    session = Session(
                        config=self.config,
                    )
                    await session.initialize()
                    session.session_id = snapshot.session_id
                    session.created_at = snapshot.created_at
                    session.updated_at = snapshot.updated_at
                    session.turn_count = snapshot.turn_count
                    session.context_manager.total_usage = snapshot.total_usage

                    for msg in snapshot.messages:
                        if msg.get("role") == "system":
                            continue
                        elif msg["role"] == "user":
                            session.context_manager.add_user_message(
                                msg.get("content", "")
                            )
                        elif msg["role"] == "assistant":
                            session.context_manager.add_assistant_message(
                                msg.get("content", ""), msg.get("tool_calls")
                            )
                        elif msg["role"] == "tool":
                            session.context_manager.add_tool_result(
                                msg.get("tool_call_id", ""), msg.get("content", "")
                            )

                    await self.agent.session.client.close()
                    await self.agent.session.mcp_manager.shutdown()

                    self.agent.session = session
                    console.print(
                        f"[success]Resumed session: {session.session_id}[/success]"
                    )
        elif cmd_name == "/checkpoint":
            persistence_manager = PersistenceManager()
            session_snapshot = SessionSnapshot(
                session_id=self.agent.session.session_id,
                created_at=self.agent.session.created_at,
                updated_at=self.agent.session.updated_at,
                turn_count=self.agent.session.turn_count,
                messages=self.agent.session.context_manager.get_messages(),
                total_usage=self.agent.session.context_manager.total_usage,
            )
            checkpoint_id = persistence_manager.save_checkpoint(session_snapshot)
            console.print(f"[success]Checkpoint created: {checkpoint_id}[/success]")
        elif cmd_name == "/restore":
            if not cmd_args:
                console.print(f"[error]Usage: /restore <checkpoint_id> [/error]")
            else:
                persistence_manager = PersistenceManager()
                snapshot = persistence_manager.load_checkpoint(cmd_args)
                if not snapshot:
                    console.print(f"[error]Checkpoint does not exist [/error]")
                else:
                    session = Session(
                        config=self.config,
                    )
                    await session.initialize()
                    session.session_id = snapshot.session_id
                    session.created_at = snapshot.created_at
                    session.updated_at = snapshot.updated_at
                    session.turn_count = snapshot.turn_count
                    session.context_manager.total_usage = snapshot.total_usage

                    for msg in snapshot.messages:
                        if msg.get("role") == "system":
                            continue
                        elif msg["role"] == "user":
                            session.context_manager.add_user_message(
                                msg.get("content", "")
                            )
                        elif msg["role"] == "assistant":
                            session.context_manager.add_assistant_message(
                                msg.get("content", ""), msg.get("tool_calls")
                            )
                        elif msg["role"] == "tool":
                            session.context_manager.add_tool_result(
                                msg.get("tool_call_id", ""), msg.get("content", "")
                            )

                    await self.agent.session.client.close()
                    await self.agent.session.mcp_manager.shutdown()

                    self.agent.session = session
                    console.print(
                        f"[success]Restored session: {session.session_id}, checkpoint: {cmd_args}[/success]"
                    )
        elif cmd_name == "/workflow":
            if not cmd_args:
                console.print("[error]Usage: /workflow <name> [/error]")
                console.print("Available workflows: code-review, refactor, debug, learn")
            else:
                await self._run_workflow(cmd_args)
        elif cmd_name == "/claude":
            # Show .claude integration status
            if not self._claude_context:
                self._init_claude_integration()
            if self._claude_context:
                console.print("\n[bold].claude Integration Status[/bold]")
                console.print(f"  Agents: {len(self._claude_context.agents)}")
                console.print(f"  Skills: {len(self._claude_context.skills)}")
                console.print(f"  Rules: {len(self._claude_context.rules)}")
                console.print(f"  Workflows: {len(self._claude_context.workflows)}")
                console.print(f"  Commands: {len(self._claude_context.commands)}")
            else:
                console.print("[warning].claude directory not found[/warning]")
        elif cmd_name == "/autonomous":
            # Start autonomous development loop
            await self._start_autonomous_loop(cmd_args)
        elif cmd_name == "/loop":
            # Control autonomous loop
            await self._control_loop(cmd_args)
        elif cmd_name == "/monitor":
            # Show loop status
            self._show_loop_status()
        elif cmd_name == "/circuit":
            # Circuit breaker control
            self._control_circuit_breaker(cmd_args)
        elif cmd_name == "/agents":
            # List available .claude agents
            if not self._claude_context:
                self._init_claude_integration()
            if self._claude_context and self._claude_context.agents:
                console.print("\n[bold]Available Agents[/bold]")
                for name, agent_def in self._claude_context.agents.items():
                    console.print(f"  • {name}: {agent_def.description[:60]}...")
            else:
                console.print("[dim]No .claude agents found[/dim]")
        elif cmd_name == "/skills":
            # List and activate skills
            if not cmd_args:
                if not self._claude_context:
                    self._init_claude_integration()
                if self._claude_context and self._claude_context.skills:
                    console.print("\n[bold]Available Skills[/bold]")
                    for name, skill in self._claude_context.skills.items():
                        active = "[green]●[/green]" if name in self._claude_context.active_skills else "○"
                        console.print(f"  {active} {name}: {skill.description[:50]}...")
                    console.print("\nUse /skills <name> to activate")
                else:
                    console.print("[dim]No .claude skills found[/dim]")
            else:
                # Activate a skill
                if not self._claude_context:
                    self._init_claude_integration()
                if self._claude_context:
                    if self._claude_context.activate_skill(cmd_args):
                        console.print(f"[success]Activated skill: {cmd_args}[/success]")
                    else:
                        console.print(f"[error]Skill not found: {cmd_args}[/error]")
        else:
            # Check for .claude commands
            if not self._command_mapper:
                self._init_claude_integration()

            if self._command_mapper:
                claude_cmd = self._command_mapper.get_command(cmd_name.lstrip("/"))
                if claude_cmd:
                    await self._execute_claude_command(claude_cmd, cmd_args)
                else:
                    console.print(f"[error]Unknown command: {cmd_name}[/error]")
            else:
                console.print(f"[error]Unknown command: {cmd_name}[/error]")

        return True

    async def _execute_claude_command(self, command: Any, args: str) -> None:
        """Execute a .claude command."""
        from friday_ai.claude_integration.command_mapper import SlashCommand

        if not isinstance(command, SlashCommand):
            return

        try:
            # Build the prompt
            prompt = command.build_prompt(args)

            if command.workflow:
                # Execute workflow
                console.print(f"\n[bold]Running workflow: {command.workflow}[/bold]")
                await self._run_workflow(command.workflow)
            elif command.agent:
                # Invoke agent
                console.print(f"\n[bold]Invoking agent: {command.agent}[/bold]")
                await self._process_message(prompt)
            elif command.skill:
                # Activate skill and process
                if self._claude_context and self._claude_context.activate_skill(command.skill):
                    console.print(f"[success]Activated skill: {command.skill}[/success]")
                await self._process_message(prompt)
            else:
                # Just process the prompt
                await self._process_message(prompt)
        except Exception as e:
            console.print(f"[error]Error executing command: {e}[/error]")

    async def _run_workflow(self, workflow_name: str):
        """Run a predefined workflow or .claude workflow."""
        # Check for built-in workflows first
        workflows = {
            "code-review": self._workflow_code_review,
            "refactor": self._workflow_refactor,
            "debug": self._workflow_debug,
            "learn": self._workflow_learn,
        }

        if workflow_name in workflows:
            await workflows[workflow_name]()
            return

        # Check for .claude workflows
        if self._workflow_engine:
            workflow = self._workflow_engine.get_workflow(workflow_name)
            if workflow:
                console.print(f"\n[bold]Running workflow: {workflow.name}[/bold]")
                console.print(workflow.description)
                # For now, just process a message with the workflow context
                # Full workflow execution would require more complex orchestration
                prompt = f"Follow this workflow: {workflow.name}\n\n{workflow.description}"
                if workflow.steps:
                    prompt += "\n\nSteps:\n"
                    for i, step in enumerate(workflow.steps, 1):
                        prompt += f"{i}. {step.name}: {step.description}\n"
                await self._process_message(prompt)
                return

        console.print(f"[error]Unknown workflow: {workflow_name}[/error]")

    async def _workflow_code_review(self):
        """Code review workflow."""
        console.print("\n[bold]Code Review Workflow[/bold]")
        file_path = console.input("Enter file path to review: ").strip()
        if file_path:
            await self._process_message(f"Review the code in {file_path} for bugs, security issues, and best practices")

    async def _workflow_refactor(self):
        """Refactoring workflow."""
        console.print("\n[bold]Refactoring Workflow[/bold]")
        file_path = console.input("Enter file path to refactor: ").strip()
        if file_path:
            await self._process_message(f"Suggest refactoring improvements for {file_path}. Focus on readability, performance, and maintainability.")

    async def _workflow_debug(self):
        """Debugging workflow."""
        console.print("\n[bold]Debugging Workflow[/bold]")
        error_msg = console.input("Describe the error or issue: ").strip()
        if error_msg:
            await self._process_message(f"Help me debug this issue: {error_msg}")

    async def _workflow_learn(self):
        """Learning workflow."""
        console.print("\n[bold]Learning Workflow[/bold]")
        topic = console.input("What topic do you want to learn about? ").strip()
        if topic:
            await self._process_message(f"Explain {topic} with examples from this codebase")

        self._autonomous_loop: AutonomousLoop | None = None

    async def _start_autonomous_loop(self, args: str) -> None:
        """Start autonomous development loop.

        Args:
            args: Optional arguments for the loop (max_loops, etc).
        """
        from friday_ai.agent.autonomous_loop import AutonomousLoop, LoopConfig

        console.print("\n[bold]🚀 Autonomous Development Loop[/bold]")
        console.print("[dim]Friday will iteratively improve the project until completion.[/dim]")

        # Parse arguments
        max_loops = 100
        if args:
            parts = args.split()
            for part in parts:
                if part.startswith("--max-loops="):
                    max_loops = int(part.split("=")[1])
                elif part.isdigit():
                    max_loops = int(part)

        console.print(f"\n[yellow]Configuration:[/yellow]")
        console.print(f"  Max loops: {max_loops}")
        console.print(f"  Rate limiting: 100 calls/hour")
        console.print(f"  Circuit breaker: Enabled")

        # Create loop config
        loop_config = LoopConfig(
            max_calls_per_hour=100,
            max_no_progress_loops=3,
            max_consecutive_errors=5,
            require_exit_signal=True,
            min_completion_indicators=2,
        )

        # Check if prompt file exists
        prompt_file = Path(loop_config.prompt_file)
        if not prompt_file.exists():
            console.print(f"\n[warning]Prompt file not found: {prompt_file}[/warning]")
            create = click.confirm("Create default prompt file?")
            if create:
                self._create_default_prompt_files()
            else:
                console.print("[error]Cannot start autonomous loop without prompt file[/error]")
                return

        # Confirm start (auto-accept in yolo mode)
        if self.config.approval != ApprovalPolicy.YOLO:
            if not click.confirm("\n[yellow]Start autonomous loop?[/yellow]"):
                console.print("Cancelled.")
                return

        # Start the loop
        console.print("\n[success]Starting autonomous development loop...[/success]\n")

        # Create autonomous loop
        try:
            # Ensure agent is initialized
            agent_initialized_here = False
            if not self.agent:
                from friday_ai.agent.agent import Agent
                self.agent = Agent(self.config)
                await self.agent.__aenter__()
                agent_initialized_here = True

            self._autonomous_loop = AutonomousLoop(self.agent, loop_config)
            results = await self._autonomous_loop.run(max_loops=max_loops)

            # Display results
            console.print(f"\n[bold]Loop Complete[/bold]")
            console.print(f"  Loops run: {results['loops_run']}")
            console.print(f"  Exit reason: {results['exit_reason']}")
            console.print(f"  Files modified: {len(results['files_modified'])}")
            console.print(f"  Errors: {len(results['errors_encountered'])}")

            # Cleanup if we initialized the agent
            if agent_initialized_here:
                await self.agent.__aexit__(None, None, None)
                self.agent = None
                self._autonomous_loop = None

        except Exception as e:
            console.print(f"\n[error]Loop error: {e}[/error]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")

    async def _control_loop(self, args: str) -> None:
        """Control autonomous loop.

        Args:
            args: Control command (stop, pause, resume, status).
        """
        console.print("\n[bold]Loop Control[/bold]")

        if not args or args in ["status", "info"]:
            self._show_loop_status()
        elif args == "stop":
            if self._autonomous_loop and self._autonomous_loop.is_running:
                self._autonomous_loop.stop()
                console.print("[success]Loop will stop after current iteration[/success]")
            else:
                console.print("[warning]No active loop to stop[/warning]")
        elif args == "pause":
            console.print("[warning]Pause not yet implemented. Use /loop stop to stop the loop.[/warning]")
        elif args == "resume":
            console.print("[warning]Resume not yet implemented. Use /autonomous to start a new loop.[/warning]")
        else:
            console.print(f"[error]Unknown loop command: {args}[/error]")
            console.print("Available: stop, pause, resume, status")

    def _show_loop_status(self) -> None:
        """Show autonomous loop status."""
        from friday_ai.agent.autonomous_loop import LoopConfig

        console.print("\n[bold]📊 Autonomous Loop Status[/bold]\n")

        loop_config = LoopConfig()

        # Load status file if exists
        status_file = Path(loop_config.status_file)
        if status_file.exists():
            try:
                import json
                status = json.loads(status_file.read_text())
                console.print(f"  State: {status.get('state', 'unknown')}")
                console.print(f"  Loop number: {status.get('loop_number', 0)}")
                console.print(f"  Last activity: {status.get('last_activity', 'never')}")
            except Exception:
                console.print("  [dim]No status available[/dim]")
        else:
            console.print("  [dim]No active loop[/dim]")

        # Rate limiting
        call_count_file = Path(loop_config.call_count_file)
        if call_count_file.exists():
            try:
                import json
                data = json.loads(call_count_file.read_text())
                calls = data.get("count", 0)
                console.print(f"\n[yellow]Rate Limiting:[/yellow]")
                console.print(f"  Calls made: {calls}/100")
                console.print(f"  Calls remaining: {100 - calls}")
            except Exception:
                pass

    def _control_circuit_breaker(self, args: str) -> None:
        """Control circuit breaker.

        Args:
            args: Control command (reset, status, open, close).
        """
        console.print("\n[bold]⚡ Circuit Breaker[/bold]\n")

        from friday_ai.agent.autonomous_loop import LoopConfig, CircuitBreakerState

        # Get circuit breaker from active loop if available
        circuit_breaker = None
        if self._autonomous_loop:
            circuit_breaker = self._autonomous_loop.circuit_breaker

        if not args or args == "status":
            if circuit_breaker:
                state_color = "green" if circuit_breaker.state == CircuitBreakerState.CLOSED else "red" if circuit_breaker.state == CircuitBreakerState.OPEN else "yellow"
                console.print(f"  Status: [{state_color}]{circuit_breaker.state.value.upper()}[/{state_color}]")
                console.print(f"  No progress loops: {circuit_breaker.no_progress_count}/{self._autonomous_loop.config.max_no_progress_loops if self._autonomous_loop else 3}")
                console.print(f"  Consecutive errors: {circuit_breaker.consecutive_error_count}/{self._autonomous_loop.config.max_consecutive_errors if self._autonomous_loop else 5}")
                console.print(f"  Completion indicators: {circuit_breaker.completion_count}/{self._autonomous_loop.config.max_completion_indicators if self._autonomous_loop else 5}")
            else:
                console.print("  Status: [green]CLOSED[/green] (normal operation)")
                console.print("  No active loop - no circuit breaker data available")
        elif args == "reset":
            if circuit_breaker:
                circuit_breaker.reset()
                console.print("[success]Circuit breaker reset to CLOSED[/success]")
            else:
                console.print("[warning]No active loop to reset circuit breaker[/warning]")
        elif args == "open":
            if circuit_breaker:
                from friday_ai.agent.autonomous_loop import CircuitBreakerState
                circuit_breaker.state = CircuitBreakerState.OPEN
                console.print("[warning]Circuit breaker manually opened[/warning]")
            else:
                console.print("[warning]No active loop to open circuit breaker[/warning]")
        elif args == "close":
            if circuit_breaker:
                circuit_breaker.reset()  # Reset closes the circuit
                console.print("[success]Circuit breaker closed[/success]")
            else:
                console.print("[warning]No active loop to close circuit breaker[/warning]")
        else:
            console.print(f"[error]Unknown command: {args}[/error]")
            console.print("Available: reset, status, open, close")

    def _create_default_prompt_files(self) -> None:
        """Create default prompt files for autonomous loop."""
        from friday_ai.agent.autonomous_loop import LoopConfig

        loop_config = LoopConfig()

        # Create directories
        Path(".friday").mkdir(exist_ok=True)
        Path(loop_config.log_dir).mkdir(parents=True, exist_ok=True)

        # Create PROMPT.md
        prompt_file = Path(loop_config.prompt_file)
        if not prompt_file.exists():
            prompt_content = """# Friday AI Autonomous Development

You are an autonomous AI developer working to improve this project.

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
"""
            prompt_file.write_text(prompt_content)
            console.print(f"[success]Created: {prompt_file}[/success]")

        # Create fix_plan.md
        fix_plan_file = Path(loop_config.fix_plan_file)
        if not fix_plan_file.exists():
            fix_plan_content = """# Development Tasks

Tasks will be tracked here as you work through the project.

## Current Tasks
- [ ] Analyze project structure
- [ ] Review existing code
- [ ] Identify improvements
- [ ] Implement changes
- [ ] Run tests
- [ ] Update documentation
"""
            fix_plan_file.write_text(fix_plan_content)
            console.print(f"[success]Created: {fix_plan_file}[/success]")

        # Create AGENT.md
        agent_file = Path(loop_config.agent_file)
        if not agent_file.exists():
            agent_content = """# Build and Run Instructions

## Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

## Project Structure
- `friday_ai/` - Main source code
- `tests/` - Test suite
- `docs/` - Documentation
"""
            agent_file.write_text(agent_content)
            console.print(f"[success]Created: {agent_file}[/success]")


# CLI Group for subcommands
@click.group(invoke_without_command=True)
@click.argument("prompt", required=False)
@click.option(
    "--cwd",
    "-c",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Current working directory",
)
@click.option(
    "--version",
    "-v",
    is_flag=True,
    help="Show version information",
)
@click.option(
    "--config",
    "show_config",
    is_flag=True,
    help="Show current configuration",
)
@click.option(
    "--approval",
    "-a",
    type=click.Choice([p.value for p in ApprovalPolicy]),
    help="Set approval policy",
)
@click.option(
    "--model",
    "-m",
    help="Set AI model",
)
@click.pass_context
def cli(
    ctx,
    prompt: str | None,
    cwd: Path | None,
    version: bool,
    show_config: bool,
    approval: str | None,
    model: str | None,
):
    """Friday AI - Your intelligent coding assistant.

    Examples:
        friday                    # Start interactive mode
        friday "Hello!"          # Single prompt
        friday -c /path/to/code  # Set working directory
        friday --version         # Show version
    """
    if version:
        console.print(f"Friday AI Teammate v{__version__}")
        ctx.exit()

    if show_config:
        try:
            config = load_config(cwd=cwd)
            console.print("\n[bold]Configuration[/bold]")
            console.print(f"  Model: {config.model_name}")
            console.print(f"  Temperature: {config.temperature}")
            console.print(f"  Approval: {config.approval.value}")
            console.print(f"  Working Dir: {config.cwd}")
            console.print(f"  Config Files:")
            user_config = Path.home() / ".config" / "ai-agent" / "config.toml"
            project_config = (cwd or Path.cwd()) / ".ai-agent" / "config.toml"
            console.print(f"    - User: {user_config} ({'exists' if user_config.exists() else 'not found'})")
            console.print(f"    - Project: {project_config} ({'exists' if project_config.exists() else 'not found'})")
        except Exception as e:
            console.print(f"[error]Error loading config: {e}[/error]")
        ctx.exit()

    # Handle subcommands
    if ctx.invoked_subcommand is None:
        # No subcommand, run main logic
        try:
            config = load_config(cwd=cwd)
        except Exception as e:
            console.print(f"[error]Configuration Error: {e}[/error]")
            ctx.exit(1)

        # Override config with CLI options
        if approval:
            config.approval = ApprovalPolicy(approval)
        if model:
            config.model_name = model

        errors = config.validate()
        if errors:
            for error in errors:
                console.print(f"[error]{error}[/error]")
            ctx.exit(1)

        friday_cli = CLI(config)

        if prompt:
            result = asyncio.run(friday_cli.run_single(prompt))
            if result is None:
                ctx.exit(1)
        else:
            asyncio.run(friday_cli.run_interactive())


@cli.command()
@click.option(
    "--cwd",
    "-c",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Project directory to initialize",
)
def init(cwd: Path | None):
    """Initialize a new Friday AI project configuration."""
    target_dir = cwd or Path.cwd()
    config_dir = target_dir / ".ai-agent"
    config_file = config_dir / "config.toml"

    if config_file.exists():
        console.print(f"[warning]Configuration already exists at {config_file}[/warning]")
        overwrite = click.confirm("Overwrite?")
        if not overwrite:
            console.print("Cancelled.")
            return

    config_dir.mkdir(parents=True, exist_ok=True)

    config_content = '''# Friday AI Project Configuration
[model]
name = "GLM-4.7"
temperature = 1.0

# Project settings
cwd = "."
approval = "auto"
max_turns = 100

# Shell environment
[shell_environment]
ignore_default_excludes = false
exclude_patterns = ["*KEY*", "*TOKEN*", "*SECRET*"]

# MCP servers (optional)
# [mcp_servers.filesystem]
# command = "npx"
# args = ["-y", "@modelcontextprotocol/server-filesystem", "."]
# enabled = true
'''

    config_file.write_text(config_content)
    console.print(f"[success]Created configuration at {config_file}[/success]")

    # Create tools directory
    tools_dir = config_dir / "tools"
    tools_dir.mkdir(exist_ok=True)

    # Create example custom tool
    example_tool = tools_dir / "example.py"
    if not example_tool.exists():
        example_tool.write_text('''from friday_ai.tools.base import Tool, ToolInvocation, ToolKind, ToolResult

class ExampleTool(Tool):
    name = "example"
    kind = ToolKind.READ
    description = "An example custom tool"

    schema = {
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "Input to process"}
        },
        "required": ["input"]
    }

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = invocation.params
        input_val = params.get("input", "")
        return ToolResult.success_result(f"Processed: {input_val}")
''')
        console.print(f"[success]Created example tool at {example_tool}[/success]")


@cli.command()
@click.option(
    "--global",
    "global_",
    is_flag=True,
    help="Edit global configuration",
)
def config(global_: bool):
    """Show or edit configuration."""
    if global_:
        config_path = Path.home() / ".config" / "ai-agent" / "config.toml"
    else:
        config_path = Path.cwd() / ".ai-agent" / "config.toml"

    if not config_path.exists():
        console.print(f"[error]Configuration not found at {config_path}[/error]")
        console.print("Run 'friday init' to create a configuration.")
        return

    console.print(f"\n[bold]Configuration at {config_path}:[/bold]\n")
    content = config_path.read_text()
    console.print(content)


@cli.command()
@click.option(
    "--all",
    "list_all",
    is_flag=True,
    help="List all available workflows",
)
def workflow(list_all: bool):
    """List available workflows."""
    if list_all:
        console.print("\n[bold]Available Workflows[/bold]\n")

        workflows = {
            "code-review": {
                "description": "Review code for bugs, security issues, and best practices",
                "usage": "/workflow code-review",
            },
            "refactor": {
                "description": "Get refactoring suggestions for better code quality",
                "usage": "/workflow refactor",
            },
            "debug": {
                "description": "Help debug errors and issues",
                "usage": "/workflow debug",
            },
            "learn": {
                "description": "Learn about a topic with codebase examples",
                "usage": "/workflow learn",
            },
        }

        for name, info in workflows.items():
            console.print(f"[bold]{name}[/bold]")
            console.print(f"  Description: {info['description']}")
            console.print(f"  Usage: {info['usage']}")
            console.print()


@cli.command()
@click.argument("session_id", required=False)
def resume(session_id: str | None):
    """Resume a saved session."""
    if not session_id:
        # List available sessions
        persistence_manager = PersistenceManager()
        sessions = persistence_manager.list_sessions()

        if not sessions:
            console.print("No saved sessions found.")
            return

        console.print("\n[bold]Saved Sessions[/bold]")
        for i, s in enumerate(sessions, 1):
            console.print(f"  {i}. {s['session_id']} (turns: {s['turn_count']})")

        # Ask user to select
        choice = click.prompt("\nSelect session number", type=int, default=1)
        if 1 <= choice <= len(sessions):
            session_id = sessions[choice - 1]["session_id"]
        else:
            console.print("[error]Invalid selection[/error]")
            return

    # Resume the session
    try:
        config = load_config()
        friday_cli = CLI(config)

        async def do_resume():
            persistence_manager = PersistenceManager()
            snapshot = persistence_manager.load_session(session_id)

            if not snapshot:
                console.print(f"[error]Session not found: {session_id}[/error]")
                return

            async with Agent(config) as agent:
                friday_cli.agent = agent

                # Restore session state
                session = Session(config=config)
                await session.initialize()
                session.session_id = snapshot.session_id
                session.created_at = snapshot.created_at
                session.updated_at = snapshot.updated_at
                session.turn_count = snapshot.turn_count
                session.context_manager.total_usage = snapshot.total_usage

                for msg in snapshot.messages:
                    if msg.get("role") == "system":
                        continue
                    elif msg["role"] == "user":
                        session.context_manager.add_user_message(msg.get("content", ""))
                    elif msg["role"] == "assistant":
                        session.context_manager.add_assistant_message(
                            msg.get("content", ""), msg.get("tool_calls")
                        )
                    elif msg["role"] == "tool":
                        session.context_manager.add_tool_result(
                            msg.get("tool_call_id", ""), msg.get("content", "")
                        )

                agent.session = session
                console.print(f"[success]Resumed session: {session_id}[/success]")

                # Continue interactive mode
                await friday_cli.run_interactive()

        asyncio.run(do_resume())

    except Exception as e:
        console.print(f"[error]Error resuming session: {e}[/error]")


# Entry point
@click.command()
@click.argument("prompt", required=False)
@click.option(
    "--cwd",
    "-c",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Current working directory",
)
@click.option(
    "--version",
    "-v",
    is_flag=True,
    help="Show version information",
)
def main(prompt: str | None, cwd: Path | None, version: bool):
    """Friday AI - Your intelligent coding assistant."""
    if version:
        console.print(f"Friday AI Teammate v{__version__}")
        return

    try:
        config = load_config(cwd=cwd)
    except Exception as e:
        console.print(f"[error]Configuration Error: {e}[/error]")
        sys.exit(1)

    errors = config.validate()
    if errors:
        for error in errors:
            console.print(f"[error]{error}[/error]")
        sys.exit(1)

    cli_instance = CLI(config)

    if prompt:
        result = asyncio.run(cli_instance.run_single(prompt))
        if result is None:
            sys.exit(1)
    else:
        asyncio.run(cli_instance.run_interactive())


if __name__ == "__main__":
    main()
