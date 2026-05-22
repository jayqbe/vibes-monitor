"""
Command-line interface for Token Telemetry.

Provides the main entry point for running the proxy server and generating reports.
"""

import argparse
import logging
import sys
from typing import Optional

from token_telemetry.config import load_config
from token_telemetry.proxy import ProxyServer
from token_telemetry.reporter import Reporter, generate_summary

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for the CLI.
    
    Args:
        verbose: If True, set logging level to DEBUG
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def start_proxy(args: argparse.Namespace) -> None:
    """
    Start the telemetry proxy server.
    
    Args:
        args: Parsed command-line arguments
    """
    config = load_config(config_path=args.config)
    
    # Override config with command-line arguments
    if args.port:
        config.proxy.port = args.port
    if args.host:
        config.proxy.host = args.host
    
    logger.info(f"Starting telemetry proxy on {args.host}:{args.port}")
    logger.info(f"Forwarding to: {config.mistral.base_url}")
    logger.info(f"Database: {config.database.path}")
    
    try:
        server = ProxyServer(
            host=config.proxy.host,
            port=config.proxy.port,
            mistral_base_url=config.mistral.base_url,
            db_path=config.database.path,
            pricing_config=config.pricing,
            track_endpoints=config.proxy.track_endpoints,
            ignore_endpoints=config.proxy.ignore_endpoints,
        )
        server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down proxy server...")
    except Exception as e:
        logger.error(f"Error starting proxy server: {e}")
        sys.exit(1)


def generate_report(args: argparse.Namespace) -> None:
    """
    Generate and display a telemetry summary report.
    
    Args:
        args: Parsed command-line arguments
    """
    config = load_config(config_path=args.config)
    
    reporter = Reporter(db_path=config.database.path)
    
    # Apply filters if specified
    filters = {}
    if args.model:
        filters["model"] = args.model
    if args.origin:
        filters["origin"] = args.origin
    if args.start_date:
        filters["start_date"] = args.start_date
    if args.end_date:
        filters["end_date"] = args.end_date
    
    summary = reporter.generate_summary(filters=filters, time_period=args.period)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(summary)
        logger.info(f"Report written to {args.output}")
    else:
        print(summary)


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="token-telemetry",
        description="Token Telemetry for Vibe CLI - Track API calls and compute costs",
    )
    
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Proxy command
    proxy_parser = subparsers.add_parser(
        "proxy",
        help="Start the telemetry proxy server",
    )
    proxy_parser.add_argument(
        "-p", "--port",
        type=int,
        default=8000,
        help="Port to run the proxy server on (default: 8000)",
    )
    proxy_parser.add_argument(
        "-H", "--host",
        type=str,
        default="localhost",
        help="Host to run the proxy server on (default: localhost)",
    )
    proxy_parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to configuration file",
    )
    proxy_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    # Report command
    report_parser = subparsers.add_parser(
        "report",
        help="Generate a telemetry summary report",
    )
    report_parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to configuration file",
    )
    report_parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Filter by model name",
    )
    report_parser.add_argument(
        "--origin",
        type=str,
        default=None,
        help="Filter by origin (user, agent, sub-agent)",
    )
    report_parser.add_argument(
        "--period",
        type=str,
        choices=["daily", "weekly", "monthly", "all"],
        default="all",
        help="Time period for summary (default: all)",
    )
    report_parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Start date for custom period (YYYY-MM-DD)",
    )
    report_parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End date for custom period (YYYY-MM-DD)",
    )
    report_parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    report_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    # Default command (proxy) if no subcommand specified
    parser.set_defaults(command="proxy")
    
    return parser.parse_args()


def main() -> None:
    """
    Main entry point for the token-telemetry CLI.
    """
    args = parse_args()
    
    # Handle version option
    if args.version:
        from token_telemetry import __version__
        print(f"Token Telemetry v{__version__}")
        return
    
    setup_logging(args.verbose)
    
    if args.command == "proxy":
        start_proxy(args)
    elif args.command == "report":
        generate_report(args)
    else:
        # Default to proxy if no command specified
        start_proxy(args)


if __name__ == "__main__":
    main()
