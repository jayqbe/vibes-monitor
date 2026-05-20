"""
Database Access Layer for Token Telemetry.

Implements SQLite database operations for storing and retrieving telemetry data.
Provides thread-safe connection handling and CRUD operations for telemetry records.
"""

import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from token_telemetry.models import CallRecord, SummaryStats

logger = logging.getLogger(__name__)

# SQL schema for the calls table
SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    model TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    origin TEXT NOT NULL,
    request_tokens INTEGER NOT NULL DEFAULT 0,
    response_tokens INTEGER NOT NULL DEFAULT 0,
    processing_time REAL NOT NULL DEFAULT 0.0,
    status_code INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_calls_timestamp ON calls(timestamp);
CREATE INDEX IF NOT EXISTS idx_calls_model ON calls(model);
CREATE INDEX IF NOT EXISTS idx_calls_origin ON calls(origin);
"""

# Thread-local storage for database connections
# Key: db_path, Value: connection
_thread_local = threading.local()


class Database:
    """
    SQLite Database manager for telemetry data.
    
    Provides thread-safe connection handling and CRUD operations.
    Uses WAL mode for better concurrency.
    """
    
    def __init__(self, db_path: str = "telemetry.db") -> None:
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._initialized = False
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a thread-local database connection for this database path.
        
        Returns:
            SQLite connection object
        """
        # Initialize thread-local storage if needed
        if not hasattr(_thread_local, 'connections'):
            _thread_local.connections = {}
        
        db_path_str = str(self.db_path)
        
        if db_path_str not in _thread_local.connections:
            conn = sqlite3.connect(
                db_path_str,
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode
            )
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            # Allow shared cache mode
            conn.execute("PRAGMA read_uncommitted=True")
            _thread_local.connections[db_path_str] = conn
        
        return _thread_local.connections[db_path_str]
    
    def _ensure_initialized(self) -> None:
        """Ensure the database schema is initialized."""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._initialize_schema()
                    self._initialized = True
    
    def _initialize_schema(self) -> None:
        """Initialize the database schema."""
        try:
            conn = self._get_connection()
            conn.executescript(SCHEMA)
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise
    
    @contextmanager
    def get_cursor(self):
        """
        Context manager for getting a database cursor.
        
        Yields:
            SQLite cursor object
        """
        self._ensure_initialized()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()
    
    def insert_record(self, record: CallRecord) -> int:
        """
        Insert a telemetry record into the database.
        
        Args:
            record: CallRecord object to insert
            
        Returns:
            The ID of the inserted record
        """
        self._ensure_initialized()
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO calls (
                        timestamp, model, endpoint, origin,
                        request_tokens, response_tokens,
                        processing_time, status_code, cost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.timestamp,
                        record.model,
                        record.endpoint,
                        record.origin,
                        record.request_tokens,
                        record.response_tokens,
                        record.processing_time,
                        record.status_code,
                        record.cost,
                    ),
                )
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Failed to insert record: {e}")
            raise
    
    def get_record(self, record_id: int) -> Optional[CallRecord]:
        """
        Get a single telemetry record by ID.
        
        Args:
            record_id: ID of the record to retrieve
            
        Returns:
            CallRecord object or None if not found
        """
        self._ensure_initialized()
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM calls WHERE id = ?",
                    (record_id,),
                )
                row = cursor.fetchone()
                if row:
                    return CallRecord(
                        timestamp=row[1],
                        model=row[2],
                        endpoint=row[3],
                        origin=row[4],
                        request_tokens=row[5],
                        response_tokens=row[6],
                        processing_time=row[7],
                        status_code=row[8],
                        cost=row[9],
                    )
                return None
        except sqlite3.Error as e:
            logger.error(f"Failed to get record {record_id}: {e}")
            raise
    
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
        """
        self._ensure_initialized()
        
        query = "SELECT * FROM calls"
        params: List[Any] = []
        conditions: List[str] = []
        
        if model:
            conditions.append("model = ?")
            params.append(model)
        
        if origin:
            conditions.append("origin = ?")
            params.append(origin)
        
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC"
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset > 0:
                query += " OFFSET ?"
                params.append(offset)
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                return [
                    CallRecord(
                        timestamp=row[1],
                        model=row[2],
                        endpoint=row[3],
                        origin=row[4],
                        request_tokens=row[5],
                        response_tokens=row[6],
                        processing_time=row[7],
                        status_code=row[8],
                        cost=row[9],
                    )
                    for row in rows
                ]
        except sqlite3.Error as e:
            logger.error(f"Failed to get records: {e}")
            raise
    
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
        """
        self._ensure_initialized()
        
        # Build WHERE clause
        conditions: List[str] = []
        params: List[Any] = []
        
        if model:
            conditions.append("model = ?")
            params.append(model)
        
        if origin:
            conditions.append("origin = ?")
            params.append(origin)
        
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        stats = SummaryStats()
        
        try:
            with self.get_cursor() as cursor:
                # Get overall stats
                query = f"""
                    SELECT 
                        COUNT(*) as total_calls,
                        SUM(request_tokens) as total_request_tokens,
                        SUM(response_tokens) as total_response_tokens,
                        SUM(cost) as total_cost
                    FROM calls{where_clause}
                """
                cursor.execute(query, tuple(params))
                row = cursor.fetchone()
                if row:
                    stats.total_calls = row[0] or 0
                    stats.total_request_tokens = row[1] or 0
                    stats.total_response_tokens = row[2] or 0
                    stats.total_cost = row[3] or 0.0
                
                # Get stats by model
                query = f"""
                    SELECT 
                        model,
                        COUNT(*) as calls,
                        SUM(request_tokens) as request_tokens,
                        SUM(response_tokens) as response_tokens,
                        SUM(cost) as cost
                    FROM calls{where_clause}
                    GROUP BY model
                """
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                for row in rows:
                    stats.by_model[row[0]] = {
                        'calls': row[1] or 0,
                        'request_tokens': row[2] or 0,
                        'response_tokens': row[3] or 0,
                        'cost': row[4] or 0.0,
                    }
                
                # Get stats by origin
                query = f"""
                    SELECT 
                        origin,
                        COUNT(*) as calls,
                        SUM(request_tokens) as request_tokens,
                        SUM(response_tokens) as response_tokens,
                        SUM(cost) as cost
                    FROM calls{where_clause}
                    GROUP BY origin
                """
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                for row in rows:
                    stats.by_origin[row[0]] = {
                        'calls': row[1] or 0,
                        'request_tokens': row[2] or 0,
                        'response_tokens': row[3] or 0,
                        'cost': row[4] or 0.0,
                    }
        except sqlite3.Error as e:
            logger.error(f"Failed to get summary stats: {e}")
            raise
        
        return stats
    
    def get_records_by_date(self, date: str) -> List[CallRecord]:
        """
        Get all records for a specific date.
        
        Args:
            date: Date in ISO format (YYYY-MM-DD)
            
        Returns:
            List of CallRecord objects for the specified date
        """
        # Convert date to range (start of day to end of day)
        start_date = f"{date}T00:00:00"
        end_date = f"{date}T23:59:59"
        return self.get_records(start_date=start_date, end_date=end_date)
    
    def get_records_by_week(self, year: int, week: int) -> List[CallRecord]:
        """
        Get all records for a specific week.
        
        Args:
            year: Year number
            week: Week number (1-53)
            
        Returns:
            List of CallRecord objects for the specified week
        """
        # Calculate date range for the week
        start_date = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
        end_date = start_date + timedelta(days=6)
        
        start_str = start_date.strftime("%Y-%m-%dT00:00:00")
        end_str = end_date.strftime("%Y-%m-%dT23:59:59")
        
        return self.get_records(start_date=start_str, end_date=end_str)
    
    def get_records_by_month(self, year: int, month: int) -> List[CallRecord]:
        """
        Get all records for a specific month.
        
        Args:
            year: Year number
            month: Month number (1-12)
            
        Returns:
            List of CallRecord objects for the specified month
        """
        start_date = datetime(year, month, 1)
        # Last day of month
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        end_date = end_date - timedelta(days=1)
        
        start_str = start_date.strftime("%Y-%m-%dT00:00:00")
        end_str = end_date.strftime("%Y-%m-%dT23:59:59")
        
        return self.get_records(start_date=start_str, end_date=end_str)
    
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
        self._ensure_initialized()
        
        conditions: List[str] = []
        params: List[Any] = []
        
        if model:
            conditions.append("model = ?")
            params.append(model)
        
        if origin:
            conditions.append("origin = ?")
            params.append(origin)
        
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        try:
            with self.get_cursor() as cursor:
                query = f"DELETE FROM calls{where_clause}"
                cursor.execute(query, tuple(params))
                return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"Failed to delete records: {e}")
            raise
    
    def clear_all(self) -> int:
        """
        Clear all records from the database.
        
        Returns:
            Number of records deleted
        """
        return self.delete_records()
    
    def get_total_count(self) -> int:
        """
        Get the total number of records in the database.
        
        Returns:
            Total count of records
        """
        self._ensure_initialized()
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM calls")
                row = cursor.fetchone()
                return row[0] or 0
        except sqlite3.Error as e:
            logger.error(f"Failed to get total count: {e}")
            raise
    
    def vacuum(self) -> None:
        """Run VACUUM to optimize the database."""
        self._ensure_initialized()
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute("VACUUM")
        except sqlite3.Error as e:
            logger.error(f"Failed to run VACUUM: {e}")
            raise


# Import timedelta for week/month calculations
from datetime import timedelta


# Create a global database instance (can be overridden)
_database: Optional[Database] = None


def get_database(db_path: Optional[str] = None) -> Database:
    """
    Get or create a global database instance.
    
    Args:
        db_path: Optional path to the database file.
                 If None, uses the default path or creates an in-memory database.
    
    Returns:
        Database instance
    """
    global _database
    
    if _database is None:
        _database = Database(db_path or ":memory:")
    
    return _database


def reset_database() -> None:
    """Reset the global database instance."""
    global _database
    if _database is not None:
        _database = None
