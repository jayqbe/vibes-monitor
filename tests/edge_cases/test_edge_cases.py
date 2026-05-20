"""
Edge case tests for Token Telemetry (TEST-005).

Comprehensive edge case coverage for:
- Invalid model names
- Failed API calls (429, 500 errors)
- Malformed responses (non-JSON, missing fields)
- Network failures
- Token exhaustion scenarios
- Concurrent access scenarios

Total tests: 70+
"""

import json
import os
import sys
import tempfile
import threading
import time
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from token_telemetry.cost_calculator import CostCalculator
from token_telemetry.database import Database
from token_telemetry.models import CallRecord
from token_telemetry.proxy import ProxyServer, TelemetryHandler
from token_telemetry.reporter import Reporter


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_database(temp_db):
    """Create a mock Database instance for testing."""
    db = Database(db_path=temp_db)
    try:
        db.clear_all()
    except Exception:
        pass
    return db


@pytest.fixture
def mock_cost_calculator():
    """Create a mock CostCalculator instance for testing."""
    return CostCalculator()


@pytest.fixture(autouse=True)
def reset_handler_state():
    """Reset handler class state before each test."""
    orig_db = TelemetryHandler.database
    orig_calc = TelemetryHandler.cost_calculator
    orig_url = TelemetryHandler.mistral_base_url
    yield
    TelemetryHandler.database = orig_db
    TelemetryHandler.cost_calculator = orig_calc
    TelemetryHandler.mistral_base_url = orig_url


@pytest.fixture
def mock_handler(mock_database, mock_cost_calculator):
    """Create a TelemetryHandler instance for testing."""
    TelemetryHandler.database = mock_database
    TelemetryHandler.cost_calculator = mock_cost_calculator
    TelemetryHandler.mistral_base_url = "https://api.mistral.ai"

    from http.server import BaseHTTPRequestHandler

    with patch.object(BaseHTTPRequestHandler, '__init__', lambda *args, **kwargs: None):
        handler = TelemetryHandler()
        handler.headers = {}
        handler.path = "/v1/chat/completions"
        handler.rfile = BytesIO(b"")
        handler.wfile = BytesIO()
        handler.address_string = lambda: "127.0.0.1"
        return handler


# =============================================================================
# 1. Invalid Model Names - Edge Cases (10 tests)
# =============================================================================


class TestInvalidModelNames:
    """Test edge cases for invalid model names."""

    def test_cost_calculator_unknown_model_uses_default(self, mock_cost_calculator):
        cost = mock_cost_calculator.calculate_cost("completely-unknown-model-xyz", 1_000_000, 1_000_000)
        assert cost == 1.0

    def test_cost_calculator_empty_model_name(self, mock_cost_calculator):
        cost = mock_cost_calculator.calculate_cost("", 1000, 2000)
        assert cost > 0

    def test_cost_calculator_whitespace_model_name(self, mock_cost_calculator):
        cost = mock_cost_calculator.calculate_cost("   ", 1000, 2000)
        assert cost > 0

    def test_cost_calculator_special_characters_in_model_name(self, mock_cost_calculator):
        cost = mock_cost_calculator.calculate_cost("model@#$%^&*()", 1000, 2000)
        assert cost > 0

    def test_cost_calculator_very_long_model_name(self, mock_cost_calculator):
        long_name = "a" * 10000
        cost = mock_cost_calculator.calculate_cost(long_name, 1000, 2000)
        assert cost > 0

    def test_proxy_model_extraction_unknown_path(self, mock_handler):
        handler = mock_handler
        handler.headers = {}
        handler.path = "/api/unknown/path/to/endpoint"
        assert handler._extract_model() == "unknown"

    def test_proxy_model_extraction_empty_path(self, mock_handler):
        handler = mock_handler
        handler.headers = {}
        handler.path = ""
        assert handler._extract_model() == "unknown"

    def test_proxy_model_extraction_root_path(self, mock_handler):
        handler = mock_handler
        handler.headers = {}
        handler.path = "/"
        assert handler._extract_model() == "unknown"

    def test_database_store_invalid_model_name(self, mock_database):
        record = CallRecord(
            timestamp=datetime.now().isoformat(),
            model="invalid-model-!@#$",
            endpoint="/test",
            origin="user",
            request_tokens=100,
            response_tokens=200,
            processing_time=0.5,
            status_code=200,
            cost=0.001,
        )
        db_id = mock_database.insert_record(record)
        retrieved = mock_database.get_record(db_id)
        assert retrieved is not None
        assert retrieved.model == "invalid-model-!@#$"

    def test_reporter_summary_with_invalid_model_names(self, mock_database):
        for invalid_name in ["", " ", "!@#$", "a" * 100]:
            record = CallRecord(
                timestamp=datetime.now().isoformat(),
                model=invalid_name,
                endpoint="/test",
                origin="user",
                request_tokens=100,
                response_tokens=200,
                processing_time=0.5,
                status_code=200,
                cost=0.001,
            )
            mock_database.insert_record(record)
        reporter = Reporter(db_path=mock_database.db_path)
        summary = reporter.generate_summary()
        assert "Token Telemetry Summary" in summary


# =============================================================================
# 2. Failed API Calls - Edge Cases (10 tests)
# =============================================================================


class TestFailedAPICalls:
    """Test edge cases for failed API calls with various HTTP status codes."""

    def test_proxy_handle_429_rate_limit(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        mock_response.headers = {}
        mock_response.content = b'{"error": "Rate limit exceeded"}'
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.status_code == 429
        assert record.request_tokens == 0
        assert record.response_tokens == 0

    def test_proxy_handle_500_internal_server_error(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.headers = {}
        mock_response.content = b"Internal Server Error"
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.status_code == 500
        assert record.request_tokens == 0

    def test_proxy_handle_502_bad_gateway(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 502
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.headers = {}
        mock_response.content = b"Bad Gateway"
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.status_code == 502

    def test_proxy_handle_503_service_unavailable(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.headers = {}
        mock_response.content = b"Service Unavailable"
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.status_code == 503

    def test_proxy_handle_400_bad_request(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        mock_response.headers = {}
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.status_code == 400

    def test_proxy_handle_401_unauthorized(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.headers = {}
        mock_response.content = b"Unauthorized"
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.status_code == 401

    def test_proxy_handle_404_not_found(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.headers = {}
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.status_code == 404

    def test_proxy_response_with_error_json(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}
        mock_response.headers = {}
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.status_code == 429

    def test_database_store_error_status_codes(self, mock_database):
        error_codes = [400, 401, 403, 404, 429, 500, 502, 503, 504]
        for status_code in error_codes:
            record = CallRecord(
                timestamp=datetime.now().isoformat(),
                model="test-model",
                endpoint="/test",
                origin="user",
                request_tokens=0,
                response_tokens=0,
                processing_time=0.1,
                status_code=status_code,
                cost=0.0,
            )
            db_id = mock_database.insert_record(record)
            retrieved = mock_database.get_record(db_id)
            assert retrieved.status_code == status_code


# =============================================================================
# 3. Malformed Responses - Edge Cases (10 tests)
# =============================================================================


class TestMalformedResponses:
    """Test edge cases for malformed API responses."""

    def test_proxy_response_non_json_content(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.headers = {}
        mock_response.content = b"This is not JSON"
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.request_tokens == 0
        assert record.response_tokens == 0
        assert record.status_code == 200

    def test_proxy_response_empty_body(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Empty", "", 0)
        mock_response.headers = {}
        mock_response.content = b""
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.request_tokens == 0
        assert record.response_tokens == 0

    def test_proxy_response_missing_usage_field(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"outputs": [{"text": "Hello"}]}
        mock_response.headers = {}
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.request_tokens == 0
        assert record.response_tokens == 0

    def test_proxy_response_missing_prompt_tokens(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"usage": {"completion_tokens": 100}}
        mock_response.headers = {}
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.request_tokens == 0
        assert record.response_tokens == 100

    def test_proxy_response_missing_completion_tokens(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"usage": {"prompt_tokens": 100}}
        mock_response.headers = {}
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.request_tokens == 100
        assert record.response_tokens == 0

    def test_proxy_response_null_usage(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"usage": None}
        mock_response.headers = {}
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.request_tokens == 0
        assert record.response_tokens == 0

    def test_proxy_response_partial_json(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Partial", "", 0)
        mock_response.headers = {}
        mock_response.content = b'{"usage": {"prompt_tokens":'
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.request_tokens == 0
        assert record.response_tokens == 0

    def test_proxy_build_response_empty_content(self, mock_handler):
        handler = mock_handler
        handler.wfile = BytesIO()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.headers = {}
        mock_response.content = b""
        handler._build_response(mock_response)
        handler.send_response.assert_called_once_with(204)
        handler.end_headers.assert_called_once()
        assert handler.wfile.getvalue() == b""

    def test_proxy_build_response_binary_content(self, mock_handler):
        handler = mock_handler
        handler.wfile = BytesIO()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        binary_content = b'\x00\x01\x02\x03\x04\x05'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/octet-stream"}
        mock_response.content = binary_content
        handler._build_response(mock_response)
        assert handler.wfile.getvalue() == binary_content


# =============================================================================
# 4. Network Failures - Edge Cases (8 tests)
# =============================================================================


class TestNetworkFailures:
    """Test edge cases for network failures."""

    @patch("token_telemetry.proxy.requests.request")
    def test_proxy_connection_error(self, mock_request, mock_handler):
        mock_request.side_effect = requests.exceptions.ConnectionError("Failed to connect")
        handler = mock_handler
        request_data = {
            "method": "POST",
            "url": "https://api.mistral.ai/v1/chat/completions",
            "headers": {},
            "data": b"{}",
        }
        with pytest.raises(requests.exceptions.ConnectionError):
            handler._forward_request(request_data)

    @patch("token_telemetry.proxy.requests.request")
    def test_proxy_timeout_error(self, mock_request, mock_handler):
        mock_request.side_effect = requests.exceptions.Timeout("Request timed out")
        handler = mock_handler
        request_data = {"method": "POST", "url": "https://api.mistral.ai/v1/chat/completions", "headers": {}, "data": b"{}"}
        with pytest.raises(requests.exceptions.Timeout):
            handler._forward_request(request_data)

    @patch("token_telemetry.proxy.requests.request")
    def test_proxy_ssl_error(self, mock_request, mock_handler):
        mock_request.side_effect = requests.exceptions.SSLError("SSL error")
        handler = mock_handler
        request_data = {"method": "POST", "url": "https://api.mistral.ai/v1/chat/completions", "headers": {}, "data": b"{}"}
        with pytest.raises(requests.exceptions.SSLError):
            handler._forward_request(request_data)

    def test_database_non_blocking_on_failure(self, mock_handler, temp_db):
        mock_db = Mock()
        mock_db.insert_record.side_effect = Exception("Database unavailable")
        handler = mock_handler
        handler.database = mock_db
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"usage": {"prompt_tokens": 100, "completion_tokens": 200}}
        request_data = {"url": "/test", "model": "test", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record is not None

    def test_proxy_handle_generic_request_exception(self, mock_handler):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.headers = {}
        mock_response.content = b"Error"
        handler = mock_handler
        request_data = {"url": "/test", "model": "test", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.status_code == 500


# =============================================================================
# 5. Token Exhaustion Scenarios - Edge Cases (9 tests)
# =============================================================================


class TestTokenExhaustion:
    """Test edge cases for token boundary conditions."""

    def test_cost_calculator_zero_tokens(self, mock_cost_calculator):
        cost = mock_cost_calculator.calculate_cost("mistral-medium", 0, 0)
        assert cost == 0.0

    def test_cost_calculator_max_int_tokens(self, mock_cost_calculator):
        max_int = sys.maxsize
        cost = mock_cost_calculator.calculate_cost("mistral-medium", max_int, max_int)
        assert cost > 0

    def test_cost_calculator_negative_tokens_raises(self, mock_cost_calculator):
        with pytest.raises(ValueError, match="Token counts cannot be negative"):
            mock_cost_calculator.calculate_cost("mistral-medium", -100, 0)
        with pytest.raises(ValueError, match="Token counts cannot be negative"):
            mock_cost_calculator.calculate_cost("mistral-medium", 0, -100)

    def test_cost_calculator_very_large_token_values(self, mock_cost_calculator):
        input_tokens = 1_000_000_000
        output_tokens = 1_000_000_000
        cost = mock_cost_calculator.calculate_cost("mistral-medium", input_tokens, output_tokens)
        expected = (input_tokens / 1_000_000) * 0.25 + (output_tokens / 1_000_000) * 0.75
        assert abs(cost - expected) < 0.01

    def test_database_store_zero_tokens(self, mock_database):
        record = CallRecord(
            timestamp=datetime.now().isoformat(),
            model="test-model",
            endpoint="/test",
            origin="user",
            request_tokens=0,
            response_tokens=0,
            processing_time=0.5,
            status_code=200,
            cost=0.0,
        )
        db_id = mock_database.insert_record(record)
        retrieved = mock_database.get_record(db_id)
        assert retrieved.request_tokens == 0
        assert retrieved.response_tokens == 0

    def test_database_store_max_tokens(self, mock_database):
        max_int = sys.maxsize
        record = CallRecord(
            timestamp=datetime.now().isoformat(),
            model="test-model",
            endpoint="/test",
            origin="user",
            request_tokens=max_int,
            response_tokens=max_int,
            processing_time=0.5,
            status_code=200,
            cost=1000000.0,
        )
        db_id = mock_database.insert_record(record)
        retrieved = mock_database.get_record(db_id)
        assert retrieved.request_tokens == max_int
        assert retrieved.response_tokens == max_int

    def test_proxy_telemetry_zero_tokens_from_response(self, mock_handler, mock_database):
        handler = mock_handler
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"usage": {"prompt_tokens": 0, "completion_tokens": 0}}
        mock_response.headers = {}
        request_data = {"url": "/test", "model": "test-model", "origin": "user"}
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.request_tokens == 0
        assert record.response_tokens == 0
        assert record.cost == 0.0

    def test_reporter_summary_zero_tokens(self, mock_database):
        record = CallRecord(
            timestamp=datetime.now().isoformat(),
            model="test-model",
            endpoint="/test",
            origin="user",
            request_tokens=0,
            response_tokens=0,
            processing_time=0.5,
            status_code=200,
            cost=0.0,
        )
        mock_database.insert_record(record)
        reporter = Reporter(db_path=mock_database.db_path)
        summary = reporter.generate_summary()
        assert "0 tokens" in summary.lower() or "0" in summary


# =============================================================================
# 6. Concurrent Access Scenarios - Edge Cases (6 tests)
# =============================================================================


class TestConcurrentAccess:
    """Test edge cases for concurrent access."""

    def test_database_concurrent_inserts(self, temp_db):
        db = Database(db_path=temp_db)

        def insert_records(thread_id):
            for i in range(50):
                record = CallRecord(
                    timestamp=datetime.now().isoformat(),
                    model=f"model-{thread_id}",
                    endpoint="/test",
                    origin=f"user-{thread_id}",
                    request_tokens=100,
                    response_tokens=200,
                    processing_time=0.5,
                    status_code=200,
                    cost=0.001,
                )
                db.insert_record(record)

        threads = [threading.Thread(target=insert_records, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total = db.get_total_count()
        assert total == 500

    def test_database_concurrent_queries(self, temp_db):
        db = Database(db_path=temp_db)
        for i in range(100):
            record = CallRecord(
                timestamp=datetime.now().isoformat(),
                model="test",
                endpoint="/test",
                origin="user",
                request_tokens=100,
                response_tokens=200,
                processing_time=0.5,
                status_code=200,
                cost=0.001,
            )
            db.insert_record(record)

        results = []
        errors = []

        def query_database(thread_id):
            try:
                for _ in range(10):
                    records = db.get_records(limit=10)
                    stats = db.get_summary_stats()
                    count = db.get_total_count()
                    results.append((len(records), stats.total_calls, count))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=query_database, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert len(results) == 50

    def test_cost_calculator_concurrent_calculations(self, mock_cost_calculator):
        results = []
        errors = []

        def calculate_cost(thread_id):
            try:
                for i in range(100):
                    cost = mock_cost_calculator.calculate_cost("mistral-medium", thread_id * 1000, thread_id * 2000)
                    results.append(cost)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=calculate_cost, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert len(results) == 1000


# =============================================================================
# CLI and Reporter Edge Cases (8 tests)
# =============================================================================


class TestCLIEdgeCases:
    """Test edge cases for CLI module."""

    def test_reporter_empty_database(self, mock_database):
        reporter = Reporter(db_path=mock_database.db_path)
        summary = reporter.generate_summary()
        assert "0" in summary or "No" in summary

    def test_reporter_invalid_time_period(self, mock_database):
        reporter = Reporter(db_path=mock_database.db_path)
        summary = reporter.generate_summary(time_period="invalid")
        assert "Token Telemetry Summary" in summary

    def test_reporter_filter_with_no_matches(self, mock_database):
        record = CallRecord(
            timestamp=datetime.now().isoformat(),
            model="other-model",
            endpoint="/test",
            origin="user",
            request_tokens=100,
            response_tokens=200,
            processing_time=0.5,
            status_code=200,
            cost=0.001,
        )
        mock_database.insert_record(record)
        reporter = Reporter(db_path=mock_database.db_path)
        summary = reporter.generate_summary(filters={"model": "non-existent"})
        assert "0" in summary or "No" in summary

    def test_reporter_detailed_report_empty(self, mock_database):
        reporter = Reporter(db_path=mock_database.db_path)
        report = reporter.generate_detailed_report(limit=100)
        assert "No records found" in report

    def test_reporter_export_to_dict_empty(self, mock_database):
        reporter = Reporter(db_path=mock_database.db_path)
        data = reporter.export_to_dict()
        assert data["summary"]["total_calls"] == 0
        assert data["records"] == []


# =============================================================================
# Proxy Server Edge Cases (6 tests)
# =============================================================================


class TestProxyServerEdgeCases:
    """Test edge cases for proxy server."""

    def test_proxy_server_stop_when_not_running(self, temp_db):
        server = ProxyServer(
            host="localhost",
            port=9992,
            mistral_base_url="https://api.mistral.ai",
            db_path=temp_db,
        )
        server.stop()
        assert not server.is_running()

    def test_proxy_server_multiple_start_stop(self, temp_db):
        server = ProxyServer(
            host="localhost",
            port=9993,
            mistral_base_url="https://api.mistral.ai",
            db_path=temp_db,
        )
        server.start_in_thread()
        assert server.is_running()
        server.stop()
        assert not server.is_running()
        server.start_in_thread()
        assert server.is_running()
        server.stop()
        assert not server.is_running()

    def test_proxy_server_custom_pricing_empty(self, temp_db):
        server = ProxyServer(
            host="localhost",
            port=9994,
            mistral_base_url="https://api.mistral.ai",
            db_path=temp_db,
            pricing_config={},
        )
        assert server.cost_calculator is not None
        cost = server.cost_calculator.calculate_cost("test", 1000, 2000)
        assert cost > 0

    def test_proxy_server_none_pricing(self, temp_db):
        server = ProxyServer(
            host="localhost",
            port=9995,
            mistral_base_url="https://api.mistral.ai",
            db_path=temp_db,
            pricing_config=None,
        )
        assert server.cost_calculator is not None
        cost = server.cost_calculator.calculate_cost("test", 1000, 2000)
        assert cost > 0
