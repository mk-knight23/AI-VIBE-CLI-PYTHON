"""Async task scheduler for Friday AI.

Provides scheduled execution of tasks and utilities.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from friday_ai.config.config import Config

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine
else:
    from collections.abc import Awaitable, Callable

TaskCallback = Callable[..., Awaitable[Any]]
Coroutine = TaskCallback


class ScheduledTask:
    """Represents a scheduled task."""

    def __init__(
        self,
        name: str,
        coro: Callable[..., Awaitable[Any]],
        schedule_time: datetime,
        args: tuple[Any, ...] = (),
        periodic: bool = False,
        period: timedelta | None = None,
    ):
        """Initialize scheduled task.

        Args:
            name: Task name
            coro: Coroutine function to execute
            schedule_time: When to execute
            args: Arguments for coroutine
            periodic: Whether this is a periodic task
            period: Period for periodic tasks
        """
        self.name = name
        self.coro = coro
        self.schedule_time = schedule_time
        self.args = args
        self.periodic = periodic
        self.period = period
        self.task: asyncio.Task | None = None

        if periodic and not period:
            raise ValueError("Period required for periodic tasks")

    async def run(self) -> Any:
        """Run the scheduled task."""
        return await self.coro(*self.args)


class Scheduler:
    """Async task scheduler."""

    def __init__(self, config: Config):
        """Initialize scheduler.

        Args:
            config: Configuration
        """
        self.config = config
        self.tasks = []
        self.running = False

    async def schedule(
        self,
        task: ScheduledTask,
    ) -> None:
        """Schedule a task.

        Args:
            task: Task to schedule
        """
        if task.periodic and not task.period:
            raise ValueError("Period required for periodic tasks")

        self.tasks.append(task)
        logger.info(f"Scheduled task '{task.name}' for {task.schedule_time}")

    async def start(self) -> None:
        """Start the scheduler."""
        if self.running:
            return

        self.running = True
        logger.info("Scheduler started")

        try:
            while self.running:
                now = datetime.now(timezone.utc)

                # Find due tasks
                due_tasks = [t for t in self.tasks if t.schedule_time <= now]

                for task in due_tasks:
                    # Run task as background task
                    asyncio.create_task(self._run_task(task))

                    if task.periodic and task.period:
                        # Reschedule
                        task.schedule_time = now + task.period
                        logger.debug(
                            f"Rescheduled periodic task '{task.name}' for {task.schedule_time}"
                        )
                    else:
                        # Remove one-off task
                        self.tasks.remove(task)

                await asyncio.sleep(1)
        finally:
            self.running = False
            logger.info("Scheduler stopped")

    async def _run_task(self, task: ScheduledTask) -> None:
        """Run a single task with error handling."""
        try:
            logger.debug(f"Executing task '{task.name}'")
            await task.run()
        except Exception as e:
            logger.error(f"Error executing task '{task.name}': {e}")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self.running = False
