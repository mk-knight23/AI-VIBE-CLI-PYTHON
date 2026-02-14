"""LLM Router - Integration layer for multi-provider routing.

This module provides the integration between the ProviderRouter and the main
Agent/Session flow, adding:
- Task complexity estimation
- Provider usage tracking
- Cost tracking and summaries
"""

import logging
from collections import defaultdict
from typing import Optional

from friday_ai.client.multi_provider import (
    ProviderRouter,
    TaskComplexity,
    ProviderType,
)

logger = logging.getLogger(__name__)


class LLMRouter:
    """Router for intelligent LLM provider selection and tracking.

    Wraps ProviderRouter with additional functionality:
    - Task complexity estimation from user prompts
    - Usage tracking per provider
    - Cost tracking and summaries
    """

    def __init__(self):
        """Initialize LLM router."""
        self._router = ProviderRouter()
        self._usage_counts: dict[ProviderType, int] = defaultdict(int)
        self._costs: dict[ProviderType, float] = defaultdict(float)
        self._total_requests: int = 0

    def estimate_complexity(self, prompt: str) -> TaskComplexity:
        """Estimate task complexity from prompt.

        Args:
            prompt: User prompt or task description.

        Returns:
            Estimated task complexity level.
        """
        prompt_lower = prompt.lower()
        prompt_length = len(prompt)

        # Check for EXPERT keywords first (highest priority)
        expert_keywords = ["debug", "research", "investigate", "critical"]
        if any(keyword in prompt_lower for keyword in expert_keywords):
            return TaskComplexity.EXPERT

        # Check for COMPLEX keywords (high complexity tasks)
        complex_keywords = [
            "architecture", "design", "implement", "system",
            "microservices", "distributed", "oauth", "jwt",
            "websocket", "real-time", "authentication system",
            "collaboration platform",
        ]
        if any(keyword in prompt_lower for keyword in complex_keywords):
            return TaskComplexity.COMPLEX

        # Check for MODERATE keywords (multi-step tasks)
        moderate_keywords = [
            "review", "explain", "suggest", "improvements",
            "how", "works", "function",
        ]
        if any(keyword in prompt_lower for keyword in moderate_keywords):
            return TaskComplexity.MODERATE

        # Check length and complexity indicators
        # Simple tasks: short prompts
        if prompt_length < 100:
            return TaskComplexity.SIMPLE

        # Moderate tasks: medium length, multi-step
        if prompt_length < 500:
            return TaskComplexity.MODERATE

        # Default to COMPLEX for long prompts
        return TaskComplexity.COMPLEX

    def track_usage(
        self,
        provider_type: ProviderType,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Track usage and cost for a provider.

        Args:
            provider_type: Provider used.
            input_tokens: Input tokens consumed.
            output_tokens: Output tokens consumed.
        """
        self._usage_counts[provider_type] += 1
        self._total_requests += 1

        cost = self._router.estimate_cost(
            provider_type, input_tokens, output_tokens
        )
        self._costs[provider_type] += cost

        logger.debug(
            f"Tracked usage: {provider_type.value} "
            f"+${cost:.4f} ({input_tokens} in, {output_tokens} out)"
        )

    def get_usage_count(self, provider_type: ProviderType) -> int:
        """Get usage count for a provider.

        Args:
            provider_type: Provider type.

        Returns:
            Number of requests made to this provider.
        """
        return self._usage_counts.get(provider_type, 0)

    def get_total_cost(self, provider_type: ProviderType) -> float:
        """Get total cost for a provider.

        Args:
            provider_type: Provider type.

        Returns:
            Total cost in USD.
        """
        return self._costs.get(provider_type, 0.0)

    def get_cost_summary(self) -> dict:
        """Get cost summary across all providers.

        Returns:
            Dictionary with cost statistics.
        """
        total_cost = sum(self._costs.values())

        by_provider = {}
        for provider_type, cost in self._costs.items():
            by_provider[provider_type.value] = {
                "requests": self._usage_counts[provider_type],
                "cost": round(cost, 4),
            }

        return {
            "total_requests": self._total_requests,
            "total_cost": round(total_cost, 4),
            "by_provider": by_provider,
        }

    @property
    def router(self) -> ProviderRouter:
        """Get the underlying provider router."""
        return self._router
