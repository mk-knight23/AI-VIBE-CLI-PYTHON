"""Async task scheduler for Friday AI.

Provides scheduled execution of tasks and utilities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TYPE_CHECKING

from friday_ai.config.config import Config

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from typing import Coroutine, Callable
else:
    from collections.abc import Callable

TaskCallback = Callable[..., Awaitable[Any]]
Coroutine = TaskCallback


class ScheduledTask:
    """Represents a scheduled task."""

    def __init__(
        self,
        name: str,
        coro: Coroutine,
        schedule_time: datetime,
        args: tuple[Any, ...] = (),
        periodic: bool = False,
        period: Optional[timedelta] = None,
    ):
        """Initialize scheduled task.

        Args:
            name: Task name
            coro: Coroutine to execute
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

        if periodic and period:
            if not period:
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
        task.task = asyncio.create_task(task.coro, *task.args)

    async def start(self) -> None:
        """Start the scheduler."""
        self.running = True

        while self.tasks:
            now = datetime.now()

            due_tasks = [t for t in self.tasks if t.schedule_time <= now]

            if not due_tasks:
                await asyncio.sleep(1)  # No tasks due yet

            for task in due_tasks:
                if task.periodic and task.periodic:
                    # Schedule next execution
                    next_run = task.schedule_time + task.period
                    while next_run <= now:
                        await asyncio.sleep(1)

                # Run task
                await asyncio.create_task(task.coro, *task.args)

                # Calculate next run time
                if task.periodic:
                    task.schedule_time = task.schedule_time + task.period

        self.running = False
