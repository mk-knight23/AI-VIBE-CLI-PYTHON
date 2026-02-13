from __future__ import annotations
import json
from typing import AsyncGenerator, Awaitable, Callable
from friday_ai.agent.events import AgentEvent, AgentEventType
from friday_ai.agent.session import Session
from friday_ai.client.response import StreamEventType, TokenUsage, ToolCall, ToolResultMessage
from friday_ai.config.config import Config
from friday_ai.prompts.system import create_loop_breaker_prompt
from friday_ai.tools.base import ToolConfirmation


class Agent:
    def __init__(
        self,
        config: Config,
        confirmation_callback: Callable[[ToolConfirmation], bool] | None = None,
    ):
        self.config = config
        self.session: Session | None = Session(self.config)
        if self.session:
            self.session.safety_manager.approval_manager.confirmation_callback = (
                confirmation_callback
            )

    async def run(self, message: str):
        if not self.session:
            yield AgentEvent.agent_error("Session not initialized.")
            return

        await self.session.hook_system.trigger_before_agent(message)
        yield AgentEvent.agent_start(message)
        if self.session.context_manager:
            self.session.context_manager.add_user_message(message)

        final_response: str | None = None

        async for event in self._agentic_loop():
            yield event

            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")

        if self.session:
            await self.session.hook_system.trigger_after_agent(message, final_response or "")
        yield AgentEvent.agent_end(final_response)

    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
        if not self.session:
            yield AgentEvent.agent_error("Session not initialized.")
            return

        max_turns = self.config.max_turns

        for turn_num in range(max_turns):
            if not self.session:
                break

            self.session.increment_turn()
            response_text = ""

            # check for context overflow
            if self.session.context_manager and self.session.context_manager.needs_compression():
                summary, usage_result = await self.session.chat_compactor.compress(
                    self.session.context_manager
                )

                if summary and usage_result:
                    self.session.context_manager.replace_with_summary(summary)
                    self.session.context_manager.set_latest_usage(usage_result)
                    self.session.context_manager.add_usage(usage_result)

            tool_schemas = self.session.tool_orchestrator.tool_registry.get_schemas()

            tool_calls: list[ToolCall] = []
            usage: TokenUsage | None = None

            if self.session.context_manager:
                async for event in self.session.client.chat_completion(
                    self.session.context_manager.get_messages(),
                    tools=tool_schemas if tool_schemas else None,
                ):
                    if event.type == StreamEventType.TEXT_DELTA:
                        if event.text_delta:
                            content = event.text_delta.content
                            response_text += content
                            yield AgentEvent.text_delta(content)
                    elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                        if event.tool_call:
                            tool_calls.append(event.tool_call)
                    elif event.type == StreamEventType.ERROR:
                        yield AgentEvent.agent_error(
                            event.error or "Unknown error occurred.",
                        )
                    elif event.type == StreamEventType.MESSAGE_COMPLETE:
                        if event.usage:
                            usage = event.usage

            if not self.session:
                break

            if self.session.context_manager:
                self.session.context_manager.add_assistant_message(
                    response_text or "",
                    (
                        [
                            {
                                "id": tc.call_id,
                                "type": "function",
                                "function": {
                                    "name": tc.name or "unknown",
                                    "arguments": tc.arguments,
                                },
                            }
                            for tc in tool_calls
                        ]
                        if tool_calls
                        else None
                    ),
                )
            if response_text:
                yield AgentEvent.text_complete(response_text)
                self.session.loop_detector.record_action(
                    "response",
                    text=response_text,
                )

            if not tool_calls:
                if usage and self.session.context_manager:
                    self.session.context_manager.set_latest_usage(usage)
                    self.session.context_manager.add_usage(usage)

                if self.session.context_manager:
                    self.session.context_manager.prune_tool_outputs()
                return

            tool_call_results: list[ToolResultMessage] = []

            for tool_call in tool_calls:
                from friday_ai.client.response import parse_tool_call_arguments

                arguments = tool_call.arguments
                if isinstance(arguments, dict):
                    args = arguments
                else:
                    args = parse_tool_call_arguments(arguments)
                tool_name = tool_call.name or "unknown"

                yield AgentEvent.tool_call_start(
                    tool_call.call_id,
                    tool_name,
                    args,
                )

                self.session.loop_detector.record_action(
                    "tool_call",
                    tool_name=tool_name,
                    args=args,
                )

                result = await self.session.tool_orchestrator.tool_registry.invoke(
                    tool_name,
                    args,
                    self.config.cwd,
                    self.session.hook_system,
                    self.session.safety_manager.approval_manager,
                )

                yield AgentEvent.tool_call_complete(
                    tool_call.call_id,
                    tool_name,
                    result,
                )

                tool_call_results.append(
                    ToolResultMessage(
                        tool_call_id=tool_call.call_id,
                        content=result.to_model_output(),
                        is_error=not result.success,
                    )
                )

            if not self.session:
                break

            for tool_result in tool_call_results:
                if self.session.context_manager:
                    self.session.context_manager.add_tool_result(
                        tool_result.tool_call_id,
                        tool_result.content,
                    )

            loop_detection_error = self.session.loop_detector.check_for_loop()
            if loop_detection_error:
                loop_prompt = create_loop_breaker_prompt(loop_detection_error)
                if self.session.context_manager:
                    self.session.context_manager.add_user_message(loop_prompt)

            if usage and self.session.context_manager:
                self.session.context_manager.set_latest_usage(usage)
                self.session.context_manager.add_usage(usage)

            if self.session.context_manager:
                self.session.context_manager.prune_tool_outputs()
        yield AgentEvent.agent_error(f"Maximum turns ({max_turns}) reached")

    async def __aenter__(self) -> Agent:
        if self.session:
            await self.session.initialize()
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_val,
        exc_tb,
    ) -> None:
        if self.session:
            await self.session.cleanup()
            self.session = None
