"""Friday AI API Server - Phase 1 Foundation.

This module provides the REST API and WebSocket server for Friday AI,
enabling multi-user access and remote integration.
"""

from friday_ai.api.server import create_app

__all__ = ["create_app"]
