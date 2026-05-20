"""
Reporter for Token Telemetry.

Generates text-based summaries from telemetry data with category breakdowns.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from token_telemetry.database import Database, get_database
from token_telemetry.models import CallRecord, SummaryStats

logger = logging.getLogger(__name__)


class Reporter:
    """
    Generates text-based summaries from telemetry data.
    
    Supports filtering by model, origin, and time period.
    """
    
    def __init__(self, db_path: str = "telemetry.db") -> None:
        """
        Initialize the reporter.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.database = Database(db_path)
    
    def generate_summary(
        self,
        filters: Optional[Dict[str, Any]] = None,
        time_period: str = "all",
    ) -> str:
        """
        Generate a text-based summary report.
        
        Args:
            filters: Optional filters to apply
                     - model: Filter by model name
                     - origin: Filter by origin
                     - start_date: Start date (ISO format)
                     - end_date: End date (ISO format)
            time_period: Time period for summary
                        - 'all': All data
                        - 'daily': Today's data
                        - 'weekly': This week's data
                        - 'monthly': This month's data
        
        Returns:
            Formatted text summary
        """
        # Apply time period filters
        date_filters = self._get_date_filters(time_period)
        
        # Merge filters
        if filters:
            date_filters.update(filters)
        
        # Get summary statistics
        stats = self.database.get_summary_stats(
            model=date_filters.get("model"),
            origin=date_filters.get("origin"),
            start_date=date_filters.get("start_date"),
            end_date=date_filters.get("end_date"),
        )
        
        # Generate summary text
        return self._format_summary(stats, time_period, date_filters)
    
    def _get_date_filters(self, time_period: str) -> Dict[str, Any]:
        """
        Get date filters based on time period.
        
        Args:
            time_period: Time period string
        
        Returns:
            Dictionary with start_date and/or end_date
        """
        now = datetime.utcnow()
        filters = {}
        
        if time_period == "daily":
            # Today
            today = now.strftime("%Y-%m-%d")
            filters["start_date"] = f"{today}T00:00:00"
            filters["end_date"] = f"{today}T23:59:59"
        elif time_period == "weekly":
            # This week (Monday to Sunday)
            start_of_week = now - timedelta(days=now.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            filters["start_date"] = start_of_week.strftime("%Y-%m-%dT00:00:00")
            filters["end_date"] = end_of_week.strftime("%Y-%m-%dT23:59:59")
        elif time_period == "monthly":
            # This month
            start_of_month = datetime(now.year, now.month, 1)
            # Last day of month
            if now.month == 12:
                end_of_month = datetime(now.year + 1, 1, 1)
            else:
                end_of_month = datetime(now.year, now.month + 1, 1)
            end_of_month = end_of_month - timedelta(days=1)
            
            filters["start_date"] = start_of_month.strftime("%Y-%m-%dT00:00:00")
            filters["end_date"] = end_of_month.strftime("%Y-%m-%dT23:59:59")
        
        return filters
    
    def _format_summary(
        self,
        stats: SummaryStats,
        time_period: str = "all",
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Format summary statistics into text.
        
        Args:
            stats: Summary statistics
            time_period: Time period for the summary
            filters: Applied filters (for display)
        
        Returns:
            Formatted text summary
        """
        lines = []
        
        # Header
        if time_period == "all":
            lines.append("## Token Telemetry Summary")
        else:
            lines.append(f"## Token Telemetry Summary ({time_period.capitalize()})")
        lines.append("")
        
        # Overall statistics
        lines.append(f"- **Total API Calls**: {stats.total_calls:,}")
        lines.append(
            f"- **Total Tokens**: {stats.total_tokens:,} "
            f"(Input: {stats.total_request_tokens:,}, Output: {stats.total_response_tokens:,})"
        )
        lines.append(f"- **Total Cost**: ${stats.total_cost:.6f}")
        lines.append("")
        
        # Breakdown by Model
        if stats.by_model:
            lines.append("### Breakdown by Model")
            for model, model_stats in sorted(stats.by_model.items()):
                total_tokens = model_stats['request_tokens'] + model_stats['response_tokens']
                lines.append(
                    f"- **{model}**: {model_stats['calls']:,} calls, "
                    f"{total_tokens:,} tokens "
                    f"(Input: {model_stats['request_tokens']:,}, "
                    f"Output: {model_stats['response_tokens']:,}), "
                    f"${model_stats['cost']:.6f}"
                )
            lines.append("")
        
        # Breakdown by Origin
        if stats.by_origin:
            lines.append("### Breakdown by Origin")
            for origin, origin_stats in sorted(stats.by_origin.items()):
                total_tokens = origin_stats['request_tokens'] + origin_stats['response_tokens']
                lines.append(
                    f"- **{origin}**: {origin_stats['calls']:,} calls, "
                    f"{total_tokens:,} tokens "
                    f"(Input: {origin_stats['request_tokens']:,}, "
                    f"Output: {origin_stats['response_tokens']:,}), "
                    f"${origin_stats['cost']:.6f}"
                )
            lines.append("")
        
        # Filter information
        if filters:
            filter_parts = []
            if filters.get("model"):
                filter_parts.append(f"Model: {filters['model']}")
            if filters.get("origin"):
                filter_parts.append(f"Origin: {filters['origin']}")
            if filters.get("start_date") and filters.get("end_date"):
                filter_parts.append(f"Date Range: {filters['start_date']} to {filters['end_date']}")
            
            if filter_parts:
                lines.append(f"*Filtered by: {', '.join(filter_parts)}*")
                lines.append("")
        
        # Database info
        total_records = self.database.get_total_count()
        lines.append(f"*Database contains {total_records:,} total records*")
        
        return "\n".join(lines)
    
    def generate_detailed_report(
        self,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a detailed report with individual records.
        
        Args:
            limit: Maximum number of records to include
            filters: Optional filters to apply
        
        Returns:
            Formatted detailed report
        """
        # Get records
        records = self.database.get_records(
            limit=limit,
            model=filters.get("model") if filters else None,
            origin=filters.get("origin") if filters else None,
            start_date=filters.get("start_date") if filters else None,
            end_date=filters.get("end_date") if filters else None,
        )
        
        lines = []
        lines.append("## Detailed Telemetry Records")
        lines.append("")
        
        if not records:
            lines.append("*No records found*")
            return "\n".join(lines)
        
        # Header
        lines.append("| Timestamp | Model | Origin | Tokens | Cost | Status |")
        lines.append("|----------|-------|--------|--------|------|--------|")
        
        # Records
        for record in records:
            total_tokens = record.total_tokens()
            lines.append(
                f"| {record.timestamp[:19]} | {record.model} | {record.origin} | "
                f"{total_tokens:,} | ${record.cost:.6f} | {record.status_code} |"
            )
        
        lines.append("")
        lines.append(f"*Showing {len(records)} of {self.database.get_total_count()} records*")
        
        return "\n".join(lines)
    
    def export_to_dict(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Export summary data as a dictionary (for JSON export).
        
        Args:
            filters: Optional filters to apply
        
        Returns:
            Dictionary containing summary data
        """
        # Get summary statistics
        stats = self.database.get_summary_stats(
            model=filters.get("model") if filters else None,
            origin=filters.get("origin") if filters else None,
            start_date=filters.get("start_date") if filters else None,
            end_date=filters.get("end_date") if filters else None,
        )
        
        # Get individual records
        records = self.database.get_records(
            limit=None,  # All records
            model=filters.get("model") if filters else None,
            origin=filters.get("origin") if filters else None,
            start_date=filters.get("start_date") if filters else None,
            end_date=filters.get("end_date") if filters else None,
        )
        
        return {
            "summary": {
                "total_calls": stats.total_calls,
                "total_request_tokens": stats.total_request_tokens,
                "total_response_tokens": stats.total_response_tokens,
                "total_tokens": stats.total_tokens,
                "total_cost": stats.total_cost,
            },
            "by_model": stats.by_model,
            "by_origin": stats.by_origin,
            "records": [record.to_dict() for record in records],
        }


def generate_summary(
    db_path: str = "telemetry.db",
    filters: Optional[Dict[str, Any]] = None,
    time_period: str = "all",
) -> str:
    """
    Convenience function to generate a summary.
    
    Args:
        db_path: Path to the SQLite database
        filters: Optional filters to apply
        time_period: Time period for summary
    
    Returns:
        Formatted text summary
    """
    reporter = Reporter(db_path)
    return reporter.generate_summary(filters=filters, time_period=time_period)


def main() -> None:
    """Main entry point for running the reporter from command line."""
    import argparse
    import sys
    
    from token_telemetry.config import load_config
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Generate token telemetry summary reports"
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Filter by model name",
    )
    parser.add_argument(
        "--origin",
        type=str,
        default=None,
        help="Filter by origin (user, agent, sub-agent)",
    )
    parser.add_argument(
        "--period",
        type=str,
        choices=["daily", "weekly", "monthly", "all"],
        default="all",
        help="Time period for summary (default: all)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Start date for custom period (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End date for custom period (YYYY-MM-DD)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    # Load configuration
    config = load_config(config_path=args.config)
    
    # Build filters
    filters = {}
    if args.model:
        filters["model"] = args.model
    if args.origin:
        filters["origin"] = args.origin
    if args.start_date:
        filters["start_date"] = f"{args.start_date}T00:00:00"
    if args.end_date:
        filters["end_date"] = f"{args.end_date}T23:59:59"
    
    # Generate summary
    summary = generate_summary(
        db_path=config.database.path,
        filters=filters,
        time_period=args.period,
    )
    
    # Output
    if args.output:
        with open(args.output, "w") as f:
            f.write(summary)
        print(f"Report written to {args.output}")
    else:
        print(summary)


if __name__ == "__main__":
    main()
