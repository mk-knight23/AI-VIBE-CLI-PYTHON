"""CLI entry point for Friday AI API server.

Usage:
    python -m friday_ai.api --host 0.0.0.0 --port 8000
"""

import argparse
import asyncio
import logging
import sys

import uvicorn

from friday_ai.api.server import create_app


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging for the API server."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> int:
    """Main entry point for API server."""
    parser = argparse.ArgumentParser(
        description="Friday AI API Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development only)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (production only)",
    )

    args = parser.parse_args()

    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    logger.info(f"Starting Friday AI API server on {args.host}:{args.port}")

    # Create app
    app = create_app()

    # Run server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level=args.log_level.lower(),
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
