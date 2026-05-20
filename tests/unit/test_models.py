"""
Unit tests for the data models module.

Tests CallRecord and SummaryStats dataclasses.
"""

from datetime import datetime

from token_telemetry.models import CallRecord, SummaryStats


class TestCallRecord:
    """Test CallRecord dataclass."""
    
    def test_call_record_creation(self):
        """Test creating a CallRecord with all fields."""
        record = CallRecord(
            timestamp="2026-05-19T12:34:56",
            model="mistral-medium",
            endpoint="https://api.mistral.ai/v1/chat/completions",
            origin="user",
            request_tokens=256,
            response_tokens=512,
            processing_time=0.125,
            status_code=200,
            cost=0.000576,
        )
        
        assert record.timestamp == "2026-05-19T12:34:56"
        assert record.model == "mistral-medium"
        assert record.endpoint == "https://api.mistral.ai/v1/chat/completions"
        assert record.origin == "user"
        assert record.request_tokens == 256
        assert record.response_tokens == 512
        assert record.processing_time == 0.125
        assert record.status_code == 200
        assert record.cost == 0.000576
    
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
    
    def test_total_tokens_with_zero(self):
        """Test total_tokens with zero values."""
        record = CallRecord(
            timestamp="2026-05-19T12:00:00",
            model="test",
            endpoint="/test",
            origin="user",
            request_tokens=0,
            response_tokens=0,
            processing_time=0.0,
            status_code=200,
            cost=0.0,
        )
        
        assert record.total_tokens() == 0
    
    def test_to_dict(self):
        """Test to_dict method."""
        record = CallRecord(
            timestamp="2026-05-19T12:00:00",
            model="mistral-medium",
            endpoint="/v1/chat/completions",
            origin="agent",
            request_tokens=1000,
            response_tokens=2000,
            processing_time=1.5,
            status_code=200,
            cost=0.005,
        )
        
        data = record.to_dict()
        
        assert isinstance(data, dict)
        assert data["timestamp"] == "2026-05-19T12:00:00"
        assert data["model"] == "mistral-medium"
        assert data["endpoint"] == "/v1/chat/completions"
        assert data["origin"] == "agent"
        assert data["request_tokens"] == 1000
        assert data["response_tokens"] == 2000
        assert data["processing_time"] == 1.5
        assert data["status_code"] == 200
        assert data["cost"] == 0.005
    
    def test_from_dict(self):
        """Test from_dict method."""
        data = {
            "timestamp": "2026-05-19T12:00:00",
            "model": "mistral-large",
            "endpoint": "/v1/chat/completions",
            "origin": "sub-agent",
            "request_tokens": 500,
            "response_tokens": 1000,
            "processing_time": 2.0,
            "status_code": 200,
            "cost": 0.0075,
        }
        
        record = CallRecord.from_dict(data)
        
        assert record.timestamp == "2026-05-19T12:00:00"
        assert record.model == "mistral-large"
        assert record.origin == "sub-agent"
        assert record.request_tokens == 500
        assert record.response_tokens == 1000
        assert record.processing_time == 2.0
        assert record.status_code == 200
        assert record.cost == 0.0075
    
    def test_from_dict_with_missing_fields(self):
        """Test from_dict with missing fields uses defaults."""
        data = {
            "model": "test-model",
            "endpoint": "/test",
        }
        
        record = CallRecord.from_dict(data)
        
        assert record.model == "test-model"
        assert record.endpoint == "/test"
        assert record.timestamp is not None  # Should be current time
        assert record.origin == "unknown"
        assert record.request_tokens == 0
        assert record.response_tokens == 0
        assert record.processing_time == 0.0
        assert record.status_code == 0
        assert record.cost == 0.0
    
    def test_from_dict_with_partial_fields(self):
        """Test from_dict with some fields missing."""
        data = {
            "timestamp": "2026-05-19T12:00:00",
            "model": "test",
            "request_tokens": 100,
        }
        
        record = CallRecord.from_dict(data)
        
        assert record.timestamp == "2026-05-19T12:00:00"
        assert record.model == "test"
        assert record.request_tokens == 100
        assert record.response_tokens == 0
        assert record.origin == "unknown"


class TestSummaryStats:
    """Test SummaryStats dataclass."""
    
    def test_summary_stats_creation(self):
        """Test creating SummaryStats with all fields."""
        stats = SummaryStats(
            total_calls=100,
            total_request_tokens=50000,
            total_response_tokens=75000,
            total_cost=25.50,
            by_model={
                "mistral-medium": {
                    "calls": 60,
                    "request_tokens": 30000,
                    "response_tokens": 45000,
                    "cost": 15.30,
                },
                "mistral-large": {
                    "calls": 40,
                    "request_tokens": 20000,
                    "response_tokens": 30000,
                    "cost": 10.20,
                },
            },
            by_origin={
                "user": {
                    "calls": 80,
                    "request_tokens": 40000,
                    "response_tokens": 60000,
                    "cost": 20.40,
                },
                "agent": {
                    "calls": 20,
                    "request_tokens": 10000,
                    "response_tokens": 15000,
                    "cost": 5.10,
                },
            },
        )
        
        assert stats.total_calls == 100
        assert stats.total_request_tokens == 50000
        assert stats.total_response_tokens == 75000
        assert stats.total_cost == 25.50
        assert "mistral-medium" in stats.by_model
        assert "mistral-large" in stats.by_model
        assert "user" in stats.by_origin
        assert "agent" in stats.by_origin
    
    def test_summary_stats_defaults(self):
        """Test SummaryStats with default values."""
        stats = SummaryStats()
        
        assert stats.total_calls == 0
        assert stats.total_request_tokens == 0
        assert stats.total_response_tokens == 0
        assert stats.total_cost == 0.0
        assert stats.by_model == {}
        assert stats.by_origin == {}
    
    def test_total_tokens_property(self):
        """Test total_tokens property."""
        stats = SummaryStats(
            total_request_tokens=10000,
            total_response_tokens=20000,
        )
        
        assert stats.total_tokens == 30000
    
    def test_total_tokens_with_zero(self):
        """Test total_tokens property with zero values."""
        stats = SummaryStats()
        
        assert stats.total_tokens == 0
    
    def test_total_tokens_calculation(self):
        """Test total_tokens calculation."""
        stats = SummaryStats(
            total_request_tokens=12345,
            total_response_tokens=67890,
        )
        
        assert stats.total_tokens == 12345 + 67890


class TestModelSerialization:
    """Test serialization and deserialization of models."""
    
    def test_roundtrip_serialization(self):
        """Test that serialization and deserialization works correctly."""
        original = CallRecord(
            timestamp="2026-05-19T12:34:56",
            model="mistral-medium",
            endpoint="/v1/chat/completions",
            origin="user",
            request_tokens=256,
            response_tokens=512,
            processing_time=0.125,
            status_code=200,
            cost=0.000576,
        )
        
        data = original.to_dict()
        restored = CallRecord.from_dict(data)
        
        assert restored.timestamp == original.timestamp
        assert restored.model == original.model
        assert restored.endpoint == original.endpoint
        assert restored.origin == original.origin
        assert restored.request_tokens == original.request_tokens
        assert restored.response_tokens == original.response_tokens
        assert restored.processing_time == original.processing_time
        assert restored.status_code == original.status_code
        assert restored.cost == original.cost
    
    def test_multiple_roundtrips(self):
        """Test multiple serialization/deserialization cycles."""
        record = CallRecord(
            timestamp="2026-05-19T12:00:00",
            model="test-model",
            endpoint="/test",
            origin="user",
            request_tokens=100,
            response_tokens=200,
            processing_time=0.5,
            status_code=200,
            cost=0.001,
        )
        
        # Serialize and deserialize 5 times
        for _ in range(5):
            data = record.to_dict()
            record = CallRecord.from_dict(data)
        
        assert record.model == "test-model"
        assert record.request_tokens == 100
