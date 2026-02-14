#!/usr/bin/env python3
"""Run Friday AI autonomous upgrade for 20 iterations."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from friday_ai.config.config import ApprovalPolicy, Config
from friday_ai.agent.agent import Agent
from friday_ai.agent.autonomous_loop import AutonomousLoop, LoopConfig


async def run_autonomous_upgrade():
    """Run autonomous upgrade loop for 20 iterations."""
    print("🚀 Friday AI v2.1.0 Autonomous Upgrade")
    print("=" * 60)
    print("Target: v1.0.0 → v2.1.0")
    print("Iterations: 20")
    print("Phase 1: Foundation (1-5)")
    print("Phase 2: Multi-Provider (6-9)")
    print("Phase 3: Intelligence (10-14)")
    print("Phase 4: Advanced (15-20)")
    print("=" * 60)
    print()

    # Create configuration
    config = Config(
        model_name="GLM-4.7",
        approval=ApprovalPolicy.ON_REQUEST,
    )

    # Create agent
    agent = Agent(config)

    # Initialize session
    if agent.session:
        await agent.session.initialize()

    # Create loop config
    loop_config = LoopConfig(
        max_calls_per_hour=100,
        max_no_progress_loops=3,
        max_consecutive_errors=5,
        max_completion_indicators=5,
        require_exit_signal=True,
        min_completion_indicators=2,
        enable_session_continuity=True,
        session_timeout_hours=24,
        enable_tmux=False,
        log_dir=".friday/logs",
        prompt_file=".friday/PROMPT.md",
        fix_plan_file=".friday/fix_plan.md",
        agent_file=".friday/AGENT.md",
        status_file=".friday/status.json",
    )

    # Create autonomous loop
    autonomous = AutonomousLoop(agent, loop_config)

    # Run autonomous loop
    max_loops = 20
    print(f"🔄 Starting autonomous development loop ({max_loops} iterations)")
    print()

    try:
        result = await autonomous.run(max_loops=max_loops)

        print("\n" + "=" * 60)
        print("🎉 Autonomous upgrade complete!")
        print(f"Final state: {result.get('state', 'unknown')}")
        print(f"Total loops: {result.get('loop_number', 0)}")
        print(f"Circuit breaker: {result.get('circuit_breaker', {}).get('state', 'unknown')}")
        print("=" * 60)

        # Show summary
        print("\n📊 Upgrade Summary:")
        print(f"  - Iterations: {result.get('loop_number', 0)}/{max_loops}")
        print(f"  - Errors: {result.get('circuit_breaker', {}).get('consecutive_errors', 0)}")
        print(f"  - Status: {result.get('state', 'unknown').upper()}")
        print()

        return result

    except KeyboardInterrupt:
        print("\n⚠️  Upgrade interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_autonomous_upgrade())
