# API Reference

Complete API reference for all public interfaces in Token Telemetry.

## Overview

This document provides detailed API documentation for all public classes, functions, and methods in the Token Telemetry system. All examples are tested and verified to work with the current implementation.

## Public API Summary

The following symbols are exported via `token_telemetry.__all__` and are part of the public API:

| Symbol | Type | Module | Description |
|--------|------|--------|-------------|
| `__version__` | str | `__init__.py` | Package version |
| `Config` | class | `config.py` | Configuration dataclass |
| `load_config` | function | `config.py` | Load configuration |
| `Database` | class | `database.py` | Database manager |
| `CostCalculator` | class | `cost_calculator.py` | Cost calculator |
| `calculate_cost` | function | `cost_calculator.py` | Calculate cost convenience function |
| `ProxyServer` | class | `proxy.py` | Proxy server |
| `TelemetryHandler` | class | `proxy.py` | Request handler |
| `Reporter` | class | `reporter.py` | Reporter |
| `generate_summary` | function | `reporter.py` | Generate summary convenience function |
| `CallRecord` | class | `models.py` | Call record dataclass |
| `SummaryStats` | class | `models.py` | Summary statistics dataclass |

---

## Configuration API

### `load_config`

```python
from token_telemetry import load_config

def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from files and environment variables.
    
    Configuration is loaded in the following order (later overrides earlier):
    1. Default configuration from package
    2. User configuration file (config/local.yaml or specified path)
    3. Environment variables
    
    Args:
        config_path: Optional path to a specific configuration file.
                     If None, will check for config/local.yaml
    
    Returns:
        Config object with all configuration values
    
    Example:
        >>> config = load_config()
        >>> print(config.proxy.port)
        8000
        >>> config = load_config("config/production.yaml")
    """
```

### `Config`

```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class Config:
    """
    Main configuration class for Token Telemetry.
    
    Attributes:
        proxy: Proxy server configuration
        mistral: Mistral API configuration
        database: Database configuration
        logging: Logging configuration
        pricing: Pricing configuration per model
    """
    proxy: ProxyConfig
    mistral: MistralConfig
    database: DatabaseConfig
    logging: LoggingConfig
    pricing: Dict[str, Dict[str, float]]
```

### Configuration Sub-classes

```python
@dataclass
class ProxyConfig:
    """Proxy server configuration."""
    host: str = "localhost"
    port: int = 8000


@dataclass
class MistralConfig:
    """Mistral API configuration."""
    base_url: str = "https://api.mistral.ai"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "telemetry.db"


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "telemetry.log"
```

---

## Database API

### `Database`

```python
from token_telemetry import Database
from token_telemetry.models import CallRecord, SummaryStats
from typing import List, Optional, Dict, Any

class Database:
    """
    SQLite Database manager for telemetry data.
    
    Provides thread-safe connection handling and CRUD operations.
    Uses WAL mode for better concurrency.
    
    Args:
        db_path: Path to the SQLite database file
    
    Example:
        >>> db = Database("telemetry.db")
        >>> record = CallRecord(
        ...     timestamp="2026-05-19T14:30:45",
        ...     model="mistral-medium",
        ...     endpoint="/v1/chat/completions",
        ...     origin="user",
        ...     request_tokens=1000,
        ...     response_tokens=500,
        ...     processing_time=1.234,
        ...     status_code=200,
        ...     cost=0.001125,
        ... )
        >>> record_id = db.insert_record(record)
        >>> print(f"Inserted record with ID: {record_id}")
    """
    
    def __init__(self, db_path: str = "telemetry.db") -> None:
        """Initialize the database manager."""
        
    def insert_record(self, record: CallRecord) -> int:
        """
        Insert a telemetry record into the database.
        
        Args:
            record: CallRecord object to insert
            
        Returns:
            The ID of the inserted record
            
        Example:
            >>> record = CallRecord(...)
            >>> record_id = db.insert_record(record)
        """
        
    def get_record(self, record_id: int) -> Optional[CallRecord]:
        """
        Get a single telemetry record by ID.
        
        Args:
            record_id: ID of the record to retrieve
            
        Returns:
            CallRecord object or None if not found
            
        Example:
            >>> record = db.get_record(1)
            >>> if record:
            ...     print(record.model)
        """
        
    def get_records(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        model: Optional[str] = None,
        origin: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[CallRecord]:
        """
        Get multiple telemetry records with optional filtering.
        
        Args:
            limit: Maximum number of records to return
            offset: Offset for pagination
            model: Filter by model name
            origin: Filter by origin
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            
        Returns:
            List of CallRecord objects
            
        Example:
            >>> # Get all records for mistral-medium
            >>> records = db.get_records(model="mistral-medium")
            >>> 
            >>> # Get last 10 records
            >>> records = db.get_records(limit=10)
            >>> 
            >>> # Get records from today
            >>> from datetime import datetime
            >>> today = datetime.now().strftime("%Y-%m-%d")
            >>> records = db.get_records(
            ...     start_date=f"{today}T00:00:00",
            ...     end_date=f"{today}T23:59:59"
            ... )
        """
        
    def get_summary_stats(
        self,
        model: Optional[str] = None,
        origin: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> SummaryStats:
        """
        Get aggregated summary statistics.
        
        Args:
            model: Filter by model name
            origin: Filter by origin
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            
        Returns:
            SummaryStats object with aggregated data
            
        Example:
            >>> stats = db.get_summary_stats()
            >>> print(f"Total calls: {stats.total_calls}")
            >>> print(f"Total cost: ${stats.total_cost:.6f}")
        """
        
    def get_records_by_date(self, date: str) -> List[CallRecord]:
        """
        Get all records for a specific date.
        
        Args:
            date: Date in ISO format (YYYY-MM-DD)
            
        Returns:
            List of CallRecord objects for the specified date
        """
        
    def get_records_by_week(self, year: int, week: int) -> List[CallRecord]:
        """
        Get all records for a specific week.
        
        Args:
            year: Year number
            week: Week number (1-53)
            
        Returns:
            List of CallRecord objects for the specified week
        """
        
    def get_records_by_month(self, year: int, month: int) -> List[CallRecord]:
        """
        Get all records for a specific month.
        
        Args:
            year: Year number
            month: Month number (1-12)
            
        Returns:
            List of CallRecord objects for the specified month
        """
        
    def delete_records(
        self,
        model: Optional[str] = None,
        origin: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        """
        Delete records matching the specified criteria.
        
        Args:
            model: Filter by model name
            origin: Filter by origin
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            
        Returns:
            Number of records deleted
        """
        
    def clear_all(self) -> int:
        """
        Clear all records from the database.
        
        Returns:
            Number of records deleted
        """
        
    def get_total_count(self) -> int:
        """
        Get the total number of records in the database.
        
        Returns:
            Total count of records
        """
        
    def vacuum(self) -> None:
        """Run VACUUM to optimize the database."""
```

### `get_database`

```python
from token_telemetry import get_database

def get_database(db_path: Optional[str] = None) -> Database:
    """
    Get or create a global database instance.
    
    Args:
        db_path: Optional path to the database file.
                 If None, uses the default path or creates an in-memory database.
    
    Returns:
        Database instance
    
    Example:
        >>> db = get_database()  # Uses default path
        >>> db = get_database("/custom/path/telemetry.db")
    """
```

---

## Cost Calculator API

### `CostCalculator`

```python
from token_telemetry import CostCalculator
from typing import Dict, Optional, List

class CostCalculator:
    """
    Cost calculator that computes API call costs based on token usage.
    
    Supports configurable pricing per model with fallback to default pricing.
    
    Args:
        pricing_config: Optional pricing configuration dictionary.
                       Format: {model: {input: rate, output: rate}}
                       If None, uses default pricing.
    
    Example:
        >>> calculator = CostCalculator()
        >>> cost = calculator.calculate_cost("mistral-medium", 1000, 2000)
        >>> print(f"Cost: ${cost:.6f}")
        Cost: $0.001750
        >>> 
        >>> # Custom pricing
        >>> custom_pricing = {
        ...     "my-model": {"input": 0.50, "output": 1.00},
        ...     "default": {"input": 0.25, "output": 0.75},
        ... }
        >>> calculator = CostCalculator(custom_pricing)
    """
    
    def __init__(self, pricing_config: Optional[Dict[str, Dict[str, float]]] = None) -> None:
        """Initialize the cost calculator."""
        
    def calculate_cost(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> float:
        """
        Calculate the cost for an API call.
        
        Args:
            model: The model name
            input_tokens: Number of input (prompt) tokens
            output_tokens: Number of output (completion) tokens
            
        Returns:
            Cost in USD
            
        Raises:
            ValueError: If token counts are negative
            
        Example:
            >>> cost = calculator.calculate_cost("mistral-medium", 1000, 2000)
            >>> # cost = (1000/1M)*0.25 + (2000/1M)*0.75 = 0.000250 + 0.001500
        """
        
    def get_pricing_for_model(self, model: str) -> Dict[str, float]:
        """
        Get the pricing configuration for a specific model.
        
        Args:
            model: The model name
            
        Returns:
            Dictionary with 'input' and 'output' rates
            
        Example:
            >>> pricing = calculator.get_pricing_for_model("mistral-medium")
            >>> print(pricing)
            {'input': 0.25, 'output': 0.75}
        """
        
    def get_all_models(self) -> List[str]:
        """
        Get a list of all configured models.
        
        Returns:
            List of model names
            
        Example:
            >>> models = calculator.get_all_models()
            >>> print(models)
            ['default', 'mistral-tiny', 'mistral-small', ...]
        """
        
    def add_model(
        self,
        model: str,
        input_rate: float = 0.25,
        output_rate: float = 0.75,
    ) -> None:
        """
        Add a new model with custom pricing.
        
        Args:
            model: Model name
            input_rate: Input token rate per 1M tokens
            output_rate: Output token rate per 1M tokens
            
        Example:
            >>> calculator.add_model("my-model", input_rate=0.50, output_rate=1.00)
        """
        
    def update_model(
        self,
        model: str,
        input_rate: Optional[float] = None,
        output_rate: Optional[float] = None,
    ) -> None:
        """
        Update pricing for an existing model.
        
        Args:
            model: Model name
            input_rate: New input token rate (optional)
            output_rate: New output token rate (optional)
            
        Example:
            >>> calculator.update_model("my-model", input_rate=0.60)
        """
        
    def remove_model(self, model: str) -> None:
        """
        Remove a model from the pricing configuration.
        
        Args:
            model: Model name to remove
            
        Note:
            Cannot remove 'default' model
        """
```

### `calculate_cost`

```python
from token_telemetry import calculate_cost

def calculate_cost(
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    pricing_config: Optional[Dict[str, Dict[str, float]]] = None,
) -> float:
    """
    Convenience function to calculate cost for an API call.
    
    Args:
        model: The model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        pricing_config: Optional pricing configuration
        
    Returns:
        Cost in USD
    
    Example:
        >>> cost = calculate_cost("mistral-medium", 1000, 2000)
        >>> print(f"Cost: ${cost:.6f}")
        Cost: $0.001750
    """
```

---

## Models API

### `CallRecord`

```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class CallRecord:
    """
    Represents a single API call telemetry record.
    
    Attributes:
        timestamp: ISO 8601 formatted timestamp
        model: Name of the model used
        endpoint: API endpoint URL
        origin: Call initiator (user, agent, sub-agent)
        request_tokens: Number of tokens in the request
        response_tokens: Number of tokens in the response
        processing_time: Time taken to process the request (seconds)
        status_code: HTTP status code
        cost: Calculated cost for the call (USD)
    
    Example:
        >>> record = CallRecord(
        ...     timestamp="2026-05-19T14:30:45.123456",
        ...     model="mistral-medium",
        ...     endpoint="/v1/chat/completions",
        ...     origin="user",
        ...     request_tokens=1000,
        ...     response_tokens=500,
        ...     processing_time=1.234,
        ...     status_code=200,
        ...     cost=0.001125,
        ... )
        >>> print(record.total_tokens())
        1500
    """
    timestamp: str
    model: str
    endpoint: str
    origin: str
    request_tokens: int
    response_tokens: int
    processing_time: float
    status_code: int
    cost: float
    
    def total_tokens(self) -> int:
        """
        Calculate total tokens (request + response).
        
        Returns:
            Sum of request_tokens and response_tokens
            
        Example:
            >>> record = CallRecord(..., request_tokens=1000, response_tokens=500, ...)
            >>> print(record.total_tokens())
            1500
        """
        
    def to_dict(self) -> Dict:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary with all attributes
            
        Example:
            >>> record = CallRecord(...)
            >>> data = record.to_dict()
            >>> print(data["model"])
            mistral-medium
        """
        
    @classmethod
    def from_dict(cls, data: Dict) -> "CallRecord":
        """
        Create CallRecord from dictionary.
        
        Args:
            data: Dictionary with attribute values
            
        Returns:
            CallRecord instance
            
        Example:
            >>> data = {
            ...     "timestamp": "2026-05-19T14:30:45",
            ...     "model": "mistral-medium",
            ...     "endpoint": "/v1/chat/completions",
            ...     "origin": "user",
            ...     "request_tokens": 1000,
            ...     "response_tokens": 500,
            ...     "processing_time": 1.234,
            ...     "status_code": 200,
            ...     "cost": 0.001125,
            ... }
            >>> record = CallRecord.from_dict(data)
        """
```

### `SummaryStats`

```python
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class SummaryStats:
    """
    Aggregated statistics for reporting.
    
    Attributes:
        total_calls: Total number of API calls
        total_request_tokens: Sum of all request tokens
        total_response_tokens: Sum of all response tokens
        total_cost: Sum of all costs
        by_model: Statistics grouped by model
        by_origin: Statistics grouped by origin
    
    Example:
        >>> stats = SummaryStats(
        ...     total_calls=42,
        ...     total_request_tokens=12000,
        ...     total_response_tokens=20450,
        ...     total_cost=0.0243,
        ...     by_model={"mistral-medium": {...}},
        ...     by_origin={"user": {...}},
        ... )
        >>> print(f"Total tokens: {stats.total_tokens}")
        Total tokens: 32450
    """
    total_calls: int = 0
    total_request_tokens: int = 0
    total_response_tokens: int = 0
    total_cost: float = 0.0
    by_model: Dict = field(default_factory=dict)
    by_origin: Dict = field(default_factory=dict)
    
    @property
    def total_tokens(self) -> int:
        """
        Calculate total tokens across all calls.
        
        Returns:
            Sum of total_request_tokens and total_response_tokens
            
        Example:
            >>> stats = SummaryStats(
            ...     total_request_tokens=12000,
            ...     total_response_tokens=20450,
            ... )
            >>> print(stats.total_tokens)
            32450
        """
```

---

## Proxy API

### `ProxyServer`

```python
from token_telemetry import ProxyServer
from typing import Dict, Optional

class ProxyServer:
    """
    HTTP Proxy Server for Token Telemetry.
    
    Wraps the standard HTTPServer and manages the proxy lifecycle.
    
    Args:
        host: Host to bind to (default: localhost)
        port: Port to listen on (default: 8000)
        mistral_base_url: Base URL for Mistral API (default: https://api.mistral.ai)
        db_path: Path to SQLite database (default: telemetry.db)
        pricing_config: Pricing configuration for cost calculator (default: None)
    
    Example:
        >>> # Simple usage
        >>> server = ProxyServer()
        >>> server.start()
        >>> 
        >>> # Custom configuration
        >>> server = ProxyServer(
        ...     host="0.0.0.0",
        ...     port=8080,
        ...     db_path="/var/lib/telemetry/telemetry.db",
        ... )
        >>> server.start_in_thread()
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        mistral_base_url: str = "https://api.mistral.ai",
        db_path: str = "telemetry.db",
        pricing_config: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> None:
        """Initialize the proxy server."""
        
    def start(self) -> None:
        """
        Start the proxy server.
        
        Runs forever until interrupted with Ctrl+C.
        
        Example:
            >>> server = ProxyServer()
            >>> server.start()
        """
        
    def start_in_thread(self) -> None:
        """
        Start the proxy server in a background thread.
        
        The server runs as a daemon thread, so the main thread can continue.
        
        Example:
            >>> server = ProxyServer()
            >>> server.start_in_thread()
            >>> # Do other work...
            >>> server.stop()
        """
        
    def stop(self) -> None:
        """
        Stop the proxy server.
        
        Example:
            >>> server = ProxyServer()
            >>> server.start_in_thread()
            >>> server.stop()
        """
        
    def is_running(self) -> bool:
        """
        Check if the server is running.
        
        Returns:
            True if server is running, False otherwise
            
        Example:
            >>> server = ProxyServer()
            >>> server.start_in_thread()
            >>> print(server.is_running())
            True
        """
```

### `TelemetryHandler`

```python
from http.server import BaseHTTPRequestHandler
from token_telemetry import TelemetryHandler

class TelemetryHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler that intercepts API calls and logs telemetry.
    
    This class handles incoming HTTP requests, forwards them to Mistral API,
    and logs telemetry data.
    
    Class Attributes:
        database: Shared Database instance
        cost_calculator: Shared CostCalculator instance
        mistral_base_url: Shared Mistral API base URL
    
    Note:
        This class is typically used internally by ProxyServer.
        For custom usage, set the class attributes before creating instances.
    
    Example:
        >>> from token_telemetry.database import Database
        >>> from token_telemetry.cost_calculator import CostCalculator
        >>> TelemetryHandler.database = Database()
        >>> TelemetryHandler.cost_calculator = CostCalculator()
        >>> TelemetryHandler.mistral_base_url = "https://api.mistral.ai"
    """
```

---

## Reporter API

### `Reporter`

```python
from token_telemetry import Reporter
from typing import Dict, Optional, List, Any

class Reporter:
    """
    Generates text-based summaries from telemetry data.
    
    Supports filtering by model, origin, and time period.
    
    Args:
        db_path: Path to the SQLite database (default: telemetry.db)
    
    Example:
        >>> reporter = Reporter()
        >>> summary = reporter.generate_summary(time_period="daily")
        >>> print(summary)
    """
    
    def __init__(self, db_path: str = "telemetry.db") -> None:
        """Initialize the reporter."""
        
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
                        - 'weekly': This week's data (Monday-Sunday)
                        - 'monthly': This month's data
        
        Returns:
            Formatted text summary
        
        Example:
            >>> # All data
            >>> summary = reporter.generate_summary()
            >>> 
            >>> # Today's data
            >>> summary = reporter.generate_summary(time_period="daily")
            >>> 
            >>> # Filtered by model
            >>> summary = reporter.generate_summary(
            ...     filters={"model": "mistral-medium"},
            ...     time_period="weekly"
            ... )
        """
        
    def generate_detailed_report(
        self,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a detailed report with individual records.
        
        Args:
            limit: Maximum number of records to include (default: 100)
            filters: Optional filters to apply
        
        Returns:
            Formatted detailed report in markdown table format
        
        Example:
            >>> report = reporter.generate_detailed_report(limit=50)
        """
        
    def export_to_dict(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Export summary data as a dictionary (for JSON export).
        
        Args:
            filters: Optional filters to apply
        
        Returns:
            Dictionary containing:
                - summary: Aggregated statistics
                - by_model: Statistics by model
                - by_origin: Statistics by origin
                - records: List of individual records as dictionaries
        
        Example:
            >>> import json
            >>> data = reporter.export_to_dict()
            >>> print(json.dumps(data, indent=2))
        """
```

### `generate_summary`

```python
from token_telemetry import generate_summary

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
    
    Example:
        >>> summary = generate_summary(
        ...     db_path="telemetry.db",
        ...     filters={"model": "mistral-medium"},
        ...     time_period="daily"
        ... )
        >>> print(summary)
    """
```

---

## Usage Examples

### Complete Workflow Example

```python
"""
Complete example of using Token Telemetry programmatically.
"""

from token_telemetry import (
    load_config,
    Database,
    CostCalculator,
    CallRecord,
    SummaryStats,
    Reporter,
)
from datetime import datetime

# 1. Load configuration
config = load_config()

# 2. Create database
 database = Database(config.database.path)

# 3. Create cost calculator
calculator = CostCalculator(config.pricing)

# 4. Insert a record
record = CallRecord(
    timestamp=datetime.utcnow().isoformat(),
    model="mistral-medium",
    endpoint="/v1/chat/completions",
    origin="user",
    request_tokens=1000,
    response_tokens=500,
    processing_time=1.234,
    status_code=200,
    cost=calculator.calculate_cost("mistral-medium", 1000, 500),
)
record_id = database.insert_record(record)

# 5. Get summary statistics
stats = database.get_summary_stats()
print(f"Total calls: {stats.total_calls}")
print(f"Total tokens: {stats.total_tokens}")
print(f"Total cost: ${stats.total_cost:.6f}")

# 6. Generate report
reporter = Reporter(config.database.path)
summary = reporter.generate_summary(time_period="all")
print(summary)

# 7. Export to JSON
import json
data = reporter.export_to_dict()
print(json.dumps(data, indent=2))
```

### Filtering Example

```python
from token_telemetry import Reporter
from datetime import datetime, timedelta

reporter = Reporter()

# Filter by model
summary = reporter.generate_summary(filters={"model": "mistral-medium"})

# Filter by origin
summary = reporter.generate_summary(filters={"origin": "agent"})

# Filter by date range
today = datetime.now().strftime("%Y-%m-%d")
summary = reporter.generate_summary(
    filters={
        "start_date": f"{today}T00:00:00",
        "end_date": f"{today}T23:59:59",
    }
)

# Combined filters
summary = reporter.generate_summary(
    filters={
        "model": "mistral-large",
        "origin": "user",
        "start_date": "2026-05-19T00:00:00",
        "end_date": "2026-05-20T00:00:00",
    },
    time_period="all",
)
```

---

## Error Handling

### Database Errors

```python
from token_telemetry import Database, CallRecord

db = Database()

try:
    record = CallRecord(...)
    record_id = db.insert_record(record)
except Exception as e:
    print(f"Database error: {e}")
```

### Cost Calculation Errors

```python
from token_telemetry import calculate_cost

try:
    # Negative tokens will raise ValueError
    cost = calculate_cost("mistral-medium", -100, 200)
except ValueError as e:
    print(f"Invalid token count: {e}")
```

---

## See Also

- [Architecture Overview](architecture.md) - System architecture
- [Module Documentation](modules.md) - Detailed module documentation
- [Contribution Guidelines](contributing.md) - How to contribute
