"""
Unit tests for the database module.

Tests CRUD operations, connection handling, and error scenarios.
"""

import os
import tempfile
from datetime import datetime

import pytest

from token_telemetry.database import Database, get_database, reset_database
from token_telemetry.models import CallRecord, SummaryStats


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    os.unlink(db_path)
    reset_database()


@pytest.fixture
def database(temp_db):
    """Create a Database instance for testing."""
    return Database(db_path=temp_db)


class TestDatabaseInitialization:
    """Test database initialization and schema creation."""
    
    def test_database_creation(self, temp_db):
        """Test that database file is created."""
        db = Database(db_path=temp_db)
        assert os.path.exists(temp_db)
    
    def test_schema_initialization(self, database):
        """Test that schema is initialized correctly."""
        # Insert a test record
        record = CallRecord(
            timestamp=datetime.utcnow().isoformat(),
            model="test-model",
            endpoint="/test",
            origin="user",
            request_tokens=100,
            response_tokens=200,
            processing_time=0.5,
            status_code=200,
            cost=0.001,
        )
        db_id = database.insert_record(record)
        assert db_id == 1
        
        # Verify record was inserted
        retrieved = database.get_record(db_id)
        assert retrieved is not None
        assert retrieved.model == "test-model"
    
    def test_thread_safety(self, temp_db):
        """Test that database is thread-safe."""
        db = Database(db_path=temp_db)
        
        # Insert records from multiple threads
        import threading
        
        def insert_records():
            for i in range(10):
                record = CallRecord(
                    timestamp=datetime.utcnow().isoformat(),
                    model=f"model-{i}",
                    endpoint="/test",
                    origin="user",
                    request_tokens=100,
                    response_tokens=200,
                    processing_time=0.5,
                    status_code=200,
                    cost=0.001,
                )
                db.insert_record(record)
        
        threads = [threading.Thread(target=insert_records) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify all records were inserted
        total = db.get_total_count()
        assert total == 50


class TestDatabaseCRUD:
    """Test CRUD operations on the database."""
    
    def test_insert_record(self, database):
        """Test inserting a single record."""
        record = CallRecord(
            timestamp="2026-05-19T12:00:00",
            model="mistral-medium",
            endpoint="/v1/chat/completions",
            origin="user",
            request_tokens=100,
            response_tokens=200,
            processing_time=0.5,
            status_code=200,
            cost=0.001,
        )
        
        db_id = database.insert_record(record)
        assert db_id == 1
        
        retrieved = database.get_record(db_id)
        assert retrieved is not None
        assert retrieved.model == "mistral-medium"
        assert retrieved.request_tokens == 100
        assert retrieved.response_tokens == 200
        assert retrieved.cost == 0.001
    
    def test_get_record_not_found(self, database):
        """Test getting a non-existent record."""
        result = database.get_record(999)
        assert result is None
    
    def test_get_records_with_filters(self, database):
        """Test getting records with filters."""
        # Insert test records
        records = [
            CallRecord(
                timestamp="2026-05-19T12:00:00",
                model="mistral-medium",
                endpoint="/v1/chat/completions",
                origin="user",
                request_tokens=100,
                response_tokens=200,
                processing_time=0.5,
                status_code=200,
                cost=0.001,
            ),
            CallRecord(
                timestamp="2026-05-19T13:00:00",
                model="mistral-large",
                endpoint="/v1/chat/completions",
                origin="agent",
                request_tokens=200,
                response_tokens=300,
                processing_time=0.7,
                status_code=200,
                cost=0.002,
            ),
            CallRecord(
                timestamp="2026-05-19T14:00:00",
                model="mistral-medium",
                endpoint="/v1/chat/completions",
                origin="user",
                request_tokens=150,
                response_tokens=250,
                processing_time=0.6,
                status_code=200,
                cost=0.0015,
            ),
        ]
        
        for record in records:
            database.insert_record(record)
        
        # Test model filter
        medium_records = database.get_records(model="mistral-medium")
        assert len(medium_records) == 2
        
        # Test origin filter
        user_records = database.get_records(origin="user")
        assert len(user_records) == 2
        
        # Test combined filters
        user_medium = database.get_records(model="mistral-medium", origin="user")
        assert len(user_medium) == 2
    
    def test_get_records_with_limit(self, database):
        """Test getting records with limit."""
        # Insert test records
        for i in range(10):
            record = CallRecord(
                timestamp=f"2026-05-19T12:{i:02d}:00",
                model="test-model",
                endpoint="/test",
                origin="user",
                request_tokens=100,
                response_tokens=200,
                processing_time=0.5,
                status_code=200,
                cost=0.001,
            )
            database.insert_record(record)
        
        # Get limited records
        limited = database.get_records(limit=5)
        assert len(limited) == 5
    
    def test_delete_records(self, database):
        """Test deleting records."""
        # Insert test records
        for i in range(5):
            record = CallRecord(
                timestamp=f"2026-05-19T12:{i:02d}:00",
                model="test-model",
                endpoint="/test",
                origin="user",
                request_tokens=100,
                response_tokens=200,
                processing_time=0.5,
                status_code=200,
                cost=0.001,
            )
            database.insert_record(record)
        
        assert database.get_total_count() == 5
        
        # Delete some records
        deleted = database.delete_records(model="test-model")
        assert deleted == 5
        assert database.get_total_count() == 0
    
    def test_clear_all(self, database):
        """Test clearing all records."""
        # Insert test records
        for i in range(5):
            record = CallRecord(
                timestamp=f"2026-05-19T12:{i:02d}:00",
                model="test-model",
                endpoint="/test",
                origin="user",
                request_tokens=100,
                response_tokens=200,
                processing_time=0.5,
                status_code=200,
                cost=0.001,
            )
            database.insert_record(record)
        
        assert database.get_total_count() == 5
        
        # Clear all
        deleted = database.clear_all()
        assert deleted == 5
        assert database.get_total_count() == 0


class TestSummaryStats:
    """Test summary statistics generation."""
    
    def test_summary_stats_basic(self, database):
        """Test basic summary statistics."""
        # Insert test records
        records = [
            CallRecord(
                timestamp="2026-05-19T12:00:00",
                model="mistral-medium",
                endpoint="/v1/chat/completions",
                origin="user",
                request_tokens=100,
                response_tokens=200,
                processing_time=0.5,
                status_code=200,
                cost=0.001,
            ),
            CallRecord(
                timestamp="2026-05-19T13:00:00",
                model="mistral-medium",
                endpoint="/v1/chat/completions",
                origin="user",
                request_tokens=200,
                response_tokens=300,
                processing_time=0.7,
                status_code=200,
                cost=0.002,
            ),
            CallRecord(
                timestamp="2026-05-19T14:00:00",
                model="mistral-large",
                endpoint="/v1/chat/completions",
                origin="agent",
                request_tokens=150,
                response_tokens=250,
                processing_time=0.6,
                status_code=200,
                cost=0.0015,
            ),
        ]
        
        for record in records:
            database.insert_record(record)
        
        # Get summary stats
        stats = database.get_summary_stats()
        
        assert stats.total_calls == 3
        assert stats.total_request_tokens == 450
        assert stats.total_response_tokens == 750
        assert stats.total_tokens == 1200
        assert abs(stats.total_cost - 0.0045) < 0.0001
        
        # Check by model
        assert "mistral-medium" in stats.by_model
        assert stats.by_model["mistral-medium"]["calls"] == 2
        assert stats.by_model["mistral-medium"]["request_tokens"] == 300
        
        assert "mistral-large" in stats.by_model
        assert stats.by_model["mistral-large"]["calls"] == 1
        
        # Check by origin
        assert "user" in stats.by_origin
        assert stats.by_origin["user"]["calls"] == 2
        
        assert "agent" in stats.by_origin
        assert stats.by_origin["agent"]["calls"] == 1
    
    def test_summary_stats_with_filters(self, database):
        """Test summary statistics with filters."""
        # Insert test records
        for i in range(5):
            record = CallRecord(
                timestamp=f"2026-05-19T12:{i:02d}:00",
                model="mistral-medium" if i % 2 == 0 else "mistral-large",
                endpoint="/v1/chat/completions",
                origin="user" if i % 2 == 0 else "agent",
                request_tokens=100,
                response_tokens=200,
                processing_time=0.5,
                status_code=200,
                cost=0.001,
            )
            database.insert_record(record)
        
        # Get stats for mistral-medium only
        stats = database.get_summary_stats(model="mistral-medium")
        assert stats.total_calls == 3
        
        # Get stats for agent only
        stats = database.get_summary_stats(origin="agent")
        assert stats.total_calls == 2
    
    def test_summary_stats_empty_database(self, database):
        """Test summary statistics on empty database."""
        stats = database.get_summary_stats()
        
        assert stats.total_calls == 0
        assert stats.total_request_tokens == 0
        assert stats.total_response_tokens == 0
        assert stats.total_cost == 0.0
        assert stats.by_model == {}
        assert stats.by_origin == {}


class TestCallRecord:
    """Test CallRecord model."""
    
    def test_total_tokens(self):
        """Test total_tokens method."""
        record = CallRecord(
            timestamp="2026-05-19T12:00:00",
            model="test",
            endpoint="/test",
            origin="user",
            request_tokens=100,
            response_tokens=200,
            processing_time=0.5,
            status_code=200,
            cost=0.001,
        )
        
        assert record.total_tokens() == 300
    
    def test_to_dict(self):
        """Test to_dict method."""
        record = CallRecord(
            timestamp="2026-05-19T12:00:00",
            model="test",
            endpoint="/test",
            origin="user",
            request_tokens=100,
            response_tokens=200,
            processing_time=0.5,
            status_code=200,
            cost=0.001,
        )
        
        data = record.to_dict()
        
        assert data["timestamp"] == "2026-05-19T12:00:00"
        assert data["model"] == "test"
        assert data["origin"] == "user"
        assert data["request_tokens"] == 100
        assert data["response_tokens"] == 200
    
    def test_from_dict(self):
        """Test from_dict method."""
        data = {
            "timestamp": "2026-05-19T12:00:00",
            "model": "test",
            "endpoint": "/test",
            "origin": "user",
            "request_tokens": 100,
            "response_tokens": 200,
            "processing_time": 0.5,
            "status_code": 200,
            "cost": 0.001,
        }
        
        record = CallRecord.from_dict(data)
        
        assert record.timestamp == "2026-05-19T12:00:00"
        assert record.model == "test"
        assert record.request_tokens == 100
    
    def test_from_dict_with_defaults(self):
        """Test from_dict with missing fields."""
        data = {"model": "test"}
        
        record = CallRecord.from_dict(data)
        
        assert record.model == "test"
        assert record.request_tokens == 0
        assert record.response_tokens == 0
        assert record.origin == "unknown"


class TestSummaryStatsModel:
    """Test SummaryStats model."""
    
    def test_total_tokens_property(self):
        """Test total_tokens property."""
        stats = SummaryStats(
            total_calls=10,
            total_request_tokens=1000,
            total_response_tokens=2000,
            total_cost=0.01,
        )
        
        assert stats.total_tokens == 3000
