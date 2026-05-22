"""
Unit tests for the proxy server module.

Tests request interception and forwarding, telemetry logging integration,
error handling scenarios. Uses pytest-mock for mocking external API calls.
"""

import json
import os
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
from token_telemetry.proxy import (
    FORWARD_HEADERS,
    TELEMETRY_HEADERS,
    ProxyServer,
    TelemetryHandler,
    main,
)


# Mock response data for Mistral API
MOCK_RESPONSE_JSON = {
    "outputs": [{"text": "Hello world", "stop_reason": "stop"}],
    "usage": {
        "prompt_tokens": 25,
        "completion_tokens": 10,
        "total_tokens": 35,
    },
}

MOCK_RESPONSE_BODY = json.dumps(MOCK_RESPONSE_JSON).encode()


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_database(temp_db):
    """Create a mock Database instance for testing."""
    db = Database(db_path=temp_db)
    # Clear any existing data
    try:
        db.clear_all()
    except:
        pass
    return db


@pytest.fixture
def mock_cost_calculator():
    """Create a mock CostCalculator instance for testing."""
    return CostCalculator()


@pytest.fixture(autouse=True)
def reset_handler_state():
    """Reset handler class state before each test."""
    # Save original state
    orig_db = TelemetryHandler.database
    orig_calc = TelemetryHandler.cost_calculator
    orig_url = TelemetryHandler.mistral_base_url
    
    yield
    
    # Restore original state
    TelemetryHandler.database = orig_db
    TelemetryHandler.cost_calculator = orig_calc
    TelemetryHandler.mistral_base_url = orig_url


@pytest.fixture
def mock_handler(mock_database, mock_cost_calculator):
    """Create a TelemetryHandler instance for testing."""
    # Set up class-level state
    TelemetryHandler.database = mock_database
    TelemetryHandler.cost_calculator = mock_cost_calculator
    TelemetryHandler.mistral_base_url = "https://api.mistral.ai"

    # Create a mock handler that doesn't call parent __init__
    # We'll set the necessary attributes manually
    with patch.object(BaseHTTPRequestHandler, '__init__', lambda *args, **kwargs: None):
        handler = TelemetryHandler()
        handler.headers = {}
        handler.path = "/v1/chat/completions"
        handler.rfile = BytesIO(b"")
        handler.wfile = BytesIO()
        handler.address_string = lambda: "127.0.0.1"
        return handler


# Import BaseHTTPRequestHandler for patching
from http.server import BaseHTTPRequestHandler


class TestModelExtraction:
    """Test model extraction from requests."""

    def test_extract_model_from_header(self, mock_handler):
        """Test extracting model from X-Telemetry-Model header."""
        handler = mock_handler
        handler.headers = {"X-Telemetry-Model": "mistral-medium"}
        
        model = handler._extract_model()
        assert model == "mistral-medium"

    def test_extract_model_from_x_model_header(self, mock_handler):
        """Test extracting model from X-Model header."""
        handler = mock_handler
        handler.headers = {"X-Model": "mistral-large"}
        
        model = handler._extract_model()
        assert model == "mistral-large"

    def test_extract_model_from_x_origin_header(self, mock_handler):
        """Test extracting model from path."""
        handler = mock_handler
        handler.headers = {}
        handler.path = "/api/mistral-large/chat"
        
        model = handler._extract_model()
        assert model == "mistral-large"

    def test_extract_model_from_path_tiny(self, mock_handler):
        """Test extracting mistral-tiny from path."""
        handler = mock_handler
        handler.headers = {}
        handler.path = "/v1/models/mistral-tiny"
        
        model = handler._extract_model()
        assert model == "mistral-tiny"

    def test_extract_model_from_path_small(self, mock_handler):
        """Test extracting mistral-small from path."""
        handler = mock_handler
        handler.headers = {}
        handler.path = "/chat/mistral-small"
        
        model = handler._extract_model()
        assert model == "mistral-small"

    def test_extract_model_from_path_medium(self, mock_handler):
        """Test extracting mistral-medium from path."""
        handler = mock_handler
        handler.headers = {}
        handler.path = "/api/mistral-medium"
        
        model = handler._extract_model()
        assert model == "mistral-medium"

    def test_extract_model_from_path_codestral(self, mock_handler):
        """Test extracting codestral from path."""
        handler = mock_handler
        handler.headers = {}
        handler.path = "/codestral/latest"
        
        model = handler._extract_model()
        assert model == "codestral"

    def test_extract_model_unknown(self, mock_handler):
        """Test extracting model returns 'unknown' when not found."""
        handler = mock_handler
        handler.headers = {}
        handler.path = "/api/unknown-model/endpoint"
        
        model = handler._extract_model()
        assert model == "unknown"

    def test_extract_model_priority_headers_over_path(self, mock_handler):
        """Test that headers take priority over path for model extraction."""
        handler = mock_handler
        handler.headers = {"X-Telemetry-Model": "mistral-medium"}
        handler.path = "/api/mistral-large/chat"
        
        model = handler._extract_model()
        assert model == "mistral-medium"

    def test_extract_model_from_request_body(self, mock_handler):
        """Test extracting model from JSON request body."""
        import json
        handler = mock_handler
        handler.path = "/v1/chat/completions"
        handler.headers = {}
        
        # Model in JSON body
        post_data = json.dumps({"model": "mistral-large", "messages": []}).encode('utf-8')
        model = handler._extract_model(post_data=post_data)
        assert model == "mistral-large"

    def test_extract_model_priority_body_over_path(self, mock_handler):
        """Test that body model takes precedence over path model."""
        import json
        handler = mock_handler
        handler.path = "/v1/chat/completions/mistral-tiny"
        handler.headers = {}
        
        # Body has different model
        post_data = json.dumps({"model": "mistral-large", "messages": []}).encode('utf-8')
        model = handler._extract_model(post_data=post_data)
        assert model == "mistral-large"  # Body wins over path

    def test_extract_model_priority_headers_over_body(self, mock_handler):
        """Test that header model takes precedence over body model."""
        import json
        handler = mock_handler
        handler.path = "/v1/chat/completions"
        handler.headers = {"X-Telemetry-Model": "mistral-small"}
        
        # Body has different model
        post_data = json.dumps({"model": "mistral-large", "messages": []}).encode('utf-8')
        model = handler._extract_model(post_data=post_data)
        assert model == "mistral-small"  # Header wins over body

    def test_extract_model_from_body_with_path_fallback(self, mock_handler):
        """Test that path is used as fallback when body has no model."""
        import json
        handler = mock_handler
        handler.path = "/v1/chat/completions/mistral-medium"
        handler.headers = {}
        
        # Body without model field
        post_data = json.dumps({"messages": []}).encode('utf-8')
        model = handler._extract_model(post_data=post_data)
        assert model == "mistral-medium"  # Falls back to path


class TestOriginExtraction:
    """Test origin extraction from requests."""

    def test_extract_origin_from_telemetry_header(self, mock_handler):
        """Test extracting origin from X-Telemetry-Origin header."""
        handler = mock_handler
        handler.headers = {"X-Telemetry-Origin": "agent-1"}
        
        origin = handler._extract_origin()
        assert origin == "agent-1"

    def test_extract_origin_from_x_origin_header(self, mock_handler):
        """Test extracting origin from X-Origin header."""
        handler = mock_handler
        handler.headers = {"X-Origin": "sub-agent"}
        
        origin = handler._extract_origin()
        assert origin == "sub-agent"

    def test_extract_origin_default_to_user(self, mock_handler):
        """Test that origin defaults to 'user' when not specified."""
        handler = mock_handler
        handler.headers = {}
        
        origin = handler._extract_origin()
        assert origin == "user"

    def test_extract_origin_case_insensitive(self, mock_handler):
        """Test that origin header values are normalized to lowercase."""
        handler = mock_handler
        handler.headers = {"X-Telemetry-Origin": "AGENT"}
        
        origin = handler._extract_origin()
        assert origin == "agent"


class TestEndpointFiltering:
    """Test endpoint tracking/ignoring functionality."""

    def test_should_track_endpoint_default(self, mock_handler):
        """Test that all endpoints are tracked by default."""
        handler = mock_handler
        handler.track_endpoints = None
        handler.ignore_endpoints = None
        
        assert handler._should_track_endpoint("/v1/chat/completions") == True
        assert handler._should_track_endpoint("/v1/datalake/events") == True
        assert handler._should_track_endpoint("/v1/connectors/bootstrap") == True

    def test_should_track_endpoint_ignore_patterns(self, mock_handler):
        """Test ignoring specific endpoint patterns."""
        handler = mock_handler
        handler.ignore_endpoints = ["/datalake/", "/connectors/"]
        handler.track_endpoints = None
        
        # Should track model endpoints
        assert handler._should_track_endpoint("/v1/chat/completions") == True
        assert handler._should_track_endpoint("/v1/models") == True
        
        # Should NOT track ignored endpoints
        assert handler._should_track_endpoint("/v1/datalake/events") == False
        assert handler._should_track_endpoint("/v1/datalake/other") == False
        assert handler._should_track_endpoint("/v1/connectors/bootstrap") == False

    def test_should_track_endpoint_whitelist(self, mock_handler):
        """Test whitelist mode (only track specified endpoints)."""
        handler = mock_handler
        handler.track_endpoints = ["/chat/", "/models/"]
        handler.ignore_endpoints = None
        
        # Should track whitelisted endpoints
        assert handler._should_track_endpoint("/v1/chat/completions") == True
        assert handler._should_track_endpoint("/v1/models/list") == True
        
        # Should NOT track non-whitelisted endpoints
        assert handler._should_track_endpoint("/v1/datalake/events") == False
        assert handler._should_track_endpoint("/v1/other/endpoint") == False

    def test_should_track_endpoint_whitelist_takes_precedence(self, mock_handler):
        """Test that whitelist takes precedence over blacklist if both are set."""
        handler = mock_handler
        handler.track_endpoints = ["/chat/"]
        handler.ignore_endpoints = ["/datalake/"]
        
        # Only whitelist matters when both are set
        assert handler._should_track_endpoint("/v1/chat/completions") == True
        assert handler._should_track_endpoint("/v1/datalake/events") == False
        assert handler._should_track_endpoint("/v1/models") == False


class TestRequestTokenExtraction:
    """Test request token extraction from headers."""

    def test_extract_request_tokens_from_header(self, mock_handler):
        """Test extracting request tokens from X-Telemetry-Request-Tokens header."""
        handler = mock_handler
        handler.headers = {"X-Telemetry-Request-Tokens": "100"}
        
        tokens = handler._extract_request_tokens()
        assert tokens == 100

    def test_extract_request_tokens_no_header(self, mock_handler):
        """Test that request tokens returns 0 when header not present."""
        handler = mock_handler
        handler.headers = {}
        
        tokens = handler._extract_request_tokens()
        assert tokens == 0

    def test_extract_request_tokens_invalid_header(self, mock_handler):
        """Test that invalid token header returns 0."""
        handler = mock_handler
        handler.headers = {"X-Telemetry-Request-Tokens": "invalid"}
        
        tokens = handler._extract_request_tokens()
        assert tokens == 0


class TestForwardRequest:
    """Test request forwarding logic."""

    @patch("token_telemetry.proxy.requests.request")
    def test_forward_request_post(self, mock_request, mock_handler):
        """Test forwarding a POST request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = MOCK_RESPONSE_BODY
        mock_response.json.return_value = MOCK_RESPONSE_JSON
        mock_request.return_value = mock_response

        handler = mock_handler
        request_data = {
            "method": "POST",
            "url": "https://api.mistral.ai/v1/chat/completions",
            "headers": {"Authorization": "Bearer test-key"},
            "data": b'{"model": "mistral-medium"}',
        }

        response = handler._forward_request(request_data)

        assert response == mock_response
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "POST"
        assert call_args[1]["url"] == "https://api.mistral.ai/v1/chat/completions"
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-key"

    @patch("token_telemetry.proxy.requests.request")
    def test_forward_request_get(self, mock_request, mock_handler):
        """Test forwarding a GET request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        handler = mock_handler
        request_data = {
            "method": "GET",
            "url": "https://api.mistral.ai/v1/models",
            "headers": {},
            "data": None,
        }

        response = handler._forward_request(request_data)

        assert response == mock_response
        mock_request.assert_called_once_with(
            method="GET",
            url="https://api.mistral.ai/v1/models",
            headers={},
            data=None,
            timeout=30,
        )

    @patch("token_telemetry.proxy.requests.request")
    def test_forward_request_exception(self, mock_request, mock_handler):
        """Test that request exceptions are propagated."""
        mock_request.side_effect = requests.exceptions.RequestException("Connection failed")

        handler = mock_handler
        request_data = {
            "method": "POST",
            "url": "https://api.mistral.ai/v1/chat/completions",
            "headers": {},
            "data": b"{}",
        }

        with pytest.raises(requests.exceptions.RequestException):
            handler._forward_request(request_data)

    @patch("token_telemetry.proxy.requests.request")
    def test_forward_request_timeout(self, mock_request, mock_handler):
        """Test that timeout is set correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        handler = mock_handler
        request_data = {
            "method": "POST",
            "url": "https://api.mistral.ai/v1/chat/completions",
            "headers": {},
            "data": b"{}",
        }

        handler._forward_request(request_data)

        mock_request.assert_called_once()
        assert mock_request.call_args[1]["timeout"] == 30


class TestTelemetryLogging:
    """Test telemetry logging functionality."""

    def test_log_telemetry_success(self, mock_handler, mock_database):
        """Test successful telemetry logging."""
        handler = mock_handler

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
            }
        }

        request_data = {
            "url": "https://api.mistral.ai/v1/chat/completions",
            "model": "mistral-medium",
            "origin": "user",
        }

        record = handler._log_telemetry(request_data, mock_response, 0.5)

        assert isinstance(record, CallRecord)
        assert record.model == "mistral-medium"
        assert record.origin == "user"
        assert record.request_tokens == 100
        assert record.response_tokens == 200
        assert record.processing_time == 0.5
        assert record.status_code == 200
        assert record.cost > 0

        # Verify record was stored in database
        all_records = mock_database.get_records()
        assert len(all_records) >= 1
        assert all_records[0].model == "mistral-medium"

    def test_log_telemetry_with_input_tokens_field(self, mock_handler, mock_database):
        """Test telemetry logging with input_tokens instead of prompt_tokens."""
        handler = mock_handler

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "usage": {
                "input_tokens": 50,
                "output_tokens": 75,
            }
        }

        request_data = {
            "url": "/test",
            "model": "test",
            "origin": "user",
        }

        record = handler._log_telemetry(request_data, mock_response, 0.1)

        assert record.request_tokens == 50
        assert record.response_tokens == 75

    def test_log_telemetry_malformed_json(self, mock_handler, mock_database):
        """Test telemetry logging with malformed JSON response."""
        handler = mock_handler

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.content = b"not json"

        request_data = {
            "url": "/test",
            "model": "test",
            "origin": "user",
        }

        record = handler._log_telemetry(request_data, mock_response, 0.1)

        # Should still create a record with 0 tokens
        assert record.request_tokens == 0
        assert record.response_tokens == 0
        assert record.status_code == 200

    def test_log_telemetry_missing_usage(self, mock_handler, mock_database):
        """Test telemetry logging when usage field is missing."""
        handler = mock_handler

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"outputs": [{"text": "hello"}]}

        request_data = {
            "url": "/test",
            "model": "test",
            "origin": "user",
        }

        record = handler._log_telemetry(request_data, mock_response, 0.1)

        assert record.request_tokens == 0
        assert record.response_tokens == 0

    def test_log_telemetry_error_status(self, mock_handler, mock_database):
        """Test telemetry logging with error status code."""
        handler = mock_handler

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limit exceeded"}

        request_data = {
            "url": "/test",
            "model": "test",
            "origin": "user",
        }

        record = handler._log_telemetry(request_data, mock_response, 0.1)

        assert record.status_code == 429

    def test_log_telemetry_without_database(self, mock_handler):
        """Test that logging works without a database (non-blocking)."""
        handler = mock_handler
        # Remove database
        handler.database = None

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"usage": {"prompt_tokens": 10, "completion_tokens": 20}}

        request_data = {
            "url": "/test",
            "model": "test",
            "origin": "user",
        }

        # Should not raise an exception
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record is not None

    def test_log_telemetry_without_cost_calculator(self, mock_handler, mock_database):
        """Test that logging works without a cost calculator."""
        handler = mock_handler
        handler.cost_calculator = None

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"usage": {"prompt_tokens": 10, "completion_tokens": 20}}

        request_data = {
            "url": "/test",
            "model": "test",
            "origin": "user",
        }

        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record.cost == 0.0

    def test_log_telemetry_cost_calculation(self, mock_handler, mock_database, mock_cost_calculator):
        """Test that cost is calculated correctly."""
        handler = mock_handler

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "usage": {
                "prompt_tokens": 1_000_000,
                "completion_tokens": 1_000_000,
            }
        }

        request_data = {
            "url": "/test",
            "model": "mistral-medium",
            "origin": "user",
        }

        record = handler._log_telemetry(request_data, mock_response, 0.1)

        # Default pricing: input $0.25 per 1M, output $0.75 per 1M
        # 1M input + 1M output = $1.00
        assert record.cost == 1.0


class TestBuildResponse:
    """Test response building."""

    def test_build_response_success(self, mock_handler):
        """Test building a successful response."""
        # Create a handler with mock wfile
        handler = mock_handler
        handler.wfile = BytesIO()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/json",
            "X-Request-ID": "test-123",
        }
        mock_response.content = MOCK_RESPONSE_BODY

        handler._build_response(mock_response)

        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_called()
        handler.end_headers.assert_called_once()
        # Body should be written
        assert handler.wfile.getvalue() == MOCK_RESPONSE_BODY

    def test_build_response_filters_headers(self, mock_handler):
        """Test that certain headers are filtered out."""
        handler = mock_handler
        handler.wfile = BytesIO()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/json",
            "Content-Length": "100",
            "Transfer-Encoding": "chunked",
            "Connection": "keep-alive",
            "X-Custom": "value",
        }
        mock_response.content = b"{}"

        handler._build_response(mock_response)

        # Content-Length, Transfer-Encoding, and Connection should be filtered
        for header in ["Content-Length", "Transfer-Encoding", "Connection"]:
            assert not any(
                header in str(call) for call in handler.send_header.call_args_list
            )


class TestRequestHeaders:
    """Test request header constants."""

    def test_forward_headers(self):
        """Test that forward headers are defined correctly."""
        expected = [
            "Authorization",
            "Content-Type",
            "Accept",
            "User-Agent",
            "X-Request-ID",
        ]
        assert set(FORWARD_HEADERS) == set(expected)

    def test_telemetry_headers(self):
        """Test that telemetry headers are defined correctly."""
        expected = [
            "X-Telemetry-Model",
            "X-Telemetry-Origin",
            "X-Model",
            "X-Origin",
        ]
        assert set(TELEMETRY_HEADERS) == set(expected)


class TestProxyServer:
    """Test ProxyServer class."""

    def test_proxy_server_initialization(self, temp_db):
        """Test ProxyServer initialization."""
        server = ProxyServer(
            host="localhost",
            port=9000,
            mistral_base_url="https://api.mistral.ai",
            db_path=temp_db,
        )

        assert server.host == "localhost"
        assert server.port == 9000
        assert server.mistral_base_url == "https://api.mistral.ai"
        assert server.db_path == temp_db
        assert server.database is not None
        assert server.cost_calculator is not None
        assert server.server is None

    def test_proxy_server_start_in_thread(self, temp_db):
        """Test starting proxy server in a background thread."""
        server = ProxyServer(
            host="localhost",
            port=9999,
            mistral_base_url="https://api.mistral.ai",
            db_path=temp_db,
        )

        server.start_in_thread()

        assert server.is_running()
        assert server._server_thread is not None
        assert server._server_thread.is_alive()

        # Clean up
        server.stop()

    def test_proxy_server_stop(self, temp_db):
        """Test stopping the proxy server."""
        server = ProxyServer(
            host="localhost",
            port=9998,
            mistral_base_url="https://api.mistral.ai",
            db_path=temp_db,
        )

        server.start_in_thread()
        assert server.is_running()

        server.stop()
        assert not server.is_running()

    def test_proxy_server_is_running(self, temp_db):
        """Test is_running method."""
        server = ProxyServer(
            host="localhost",
            port=9997,
            mistral_base_url="https://api.mistral.ai",
            db_path=temp_db,
        )

        assert not server.is_running()

        server.start_in_thread()
        assert server.is_running()

        server.stop()
        assert not server.is_running()

    def test_proxy_server_custom_mistral_url(self, temp_db):
        """Test proxy server with custom Mistral base URL."""
        custom_url = "https://custom.mistral.ai"
        server = ProxyServer(
            host="localhost",
            port=9996,
            mistral_base_url=custom_url,
            db_path=temp_db,
        )

        assert server.mistral_base_url == custom_url

    def test_proxy_server_custom_pricing(self, temp_db):
        """Test proxy server with custom pricing configuration."""
        custom_pricing = {
            "custom-model": {
                "input": 0.50,
                "output": 1.00,
            }
        }
        server = ProxyServer(
            host="localhost",
            port=9995,
            mistral_base_url="https://api.mistral.ai",
            db_path=temp_db,
            pricing_config=custom_pricing,
        )

        assert server.pricing_config == custom_pricing
        assert server.cost_calculator is not None

    @patch("token_telemetry.proxy.HTTPServer")
    @patch("token_telemetry.proxy.TelemetryHandler")
    def test_proxy_server_start_blocking(self, mock_handler, mock_http_server, temp_db):
        """Test starting proxy server in blocking mode (simulated)."""
        mock_server_instance = Mock()
        mock_server_instance.serve_forever.side_effect = KeyboardInterrupt()
        mock_http_server.return_value = mock_server_instance

        server = ProxyServer(
            host="localhost",
            port=9994,
            mistral_base_url="https://api.mistral.ai",
            db_path=temp_db,
        )

        # Patch serve_forever to avoid infinite loop
        with patch.object(mock_server_instance, "serve_forever", side_effect=KeyboardInterrupt()):
            with patch.object(mock_server_instance, "shutdown"):
                with patch.object(mock_server_instance, "server_close"):
                    server.start()

        # Verify server was created
        mock_http_server.assert_called_once()


class TestHandlerInitialization:
    """Test TelemetryHandler initialization."""

    def test_handler_uses_class_defaults(self, temp_db):
        """Test that handler uses class-level defaults when not provided."""
        TelemetryHandler.database = None
        TelemetryHandler.cost_calculator = None
        TelemetryHandler.mistral_base_url = "https://api.mistral.ai"

        # Create handler with mock args
        with patch.object(BaseHTTPRequestHandler, '__init__', lambda *args, **kwargs: None):
            handler = TelemetryHandler(b"", b"", b"")

        assert handler.database is None
        assert handler.cost_calculator is None
        assert handler.mistral_base_url == "https://api.mistral.ai"

    def test_handler_uses_instance_overrides(self, mock_database, mock_cost_calculator):
        """Test that handler uses instance-level overrides."""
        TelemetryHandler.database = None
        TelemetryHandler.cost_calculator = None

        with patch.object(BaseHTTPRequestHandler, '__init__', lambda *args, **kwargs: None):
            handler = TelemetryHandler(
                b"", b"", b"",
                database=mock_database,
                cost_calculator=mock_cost_calculator,
                mistral_base_url="https://custom.mistral.ai",
            )

        assert handler.database == mock_database
        assert handler.cost_calculator == mock_cost_calculator
        assert handler.mistral_base_url == "https://custom.mistral.ai"


class TestHandlerLogging:
    """Test TelemetryHandler logging."""

    @patch("token_telemetry.proxy.logger")
    def test_log_message(self, mock_logger, mock_handler):
        """Test that log_message uses the module logger."""
        handler = mock_handler
        handler.address_string = lambda: "127.0.0.1"

        handler.log_message("%s request", "POST")

        mock_logger.info.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error handling."""

    @patch("token_telemetry.proxy.requests.request")
    def test_network_error_handling(self, mock_request, mock_handler, mock_database):
        """Test handling of network errors during forwarding."""
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

    def test_response_without_json_content(self, mock_handler, mock_database):
        """Test handling response without valid JSON."""
        handler = mock_handler

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.content = b"plain text"

        request_data = {
            "url": "/test",
            "model": "test",
            "origin": "user",
        }

        record = handler._log_telemetry(request_data, mock_response, 0.1)

        assert record.request_tokens == 0
        assert record.response_tokens == 0
        assert record.status_code == 200

    def test_500_error_response(self, mock_handler, mock_database):
        """Test handling 500 error response."""
        handler = mock_handler

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.content = b"Internal Server Error"

        request_data = {
            "url": "/test",
            "model": "test",
            "origin": "user",
        }

        record = handler._log_telemetry(request_data, mock_response, 0.1)

        assert record.status_code == 500
        assert record.request_tokens == 0
        assert record.response_tokens == 0

    def test_429_rate_limit_response(self, mock_handler, mock_database):
        """Test handling 429 rate limit response."""
        handler = mock_handler

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limit exceeded"}

        request_data = {
            "url": "/test",
            "model": "test",
            "origin": "user",
        }

        record = handler._log_telemetry(request_data, mock_response, 0.1)

        assert record.status_code == 429


class TestHTTPMethods:
    """Test all HTTP method handlers."""

    def test_do_put_calls_do_post(self, mock_handler):
        """Test that PUT method delegates to POST."""
        handler = mock_handler
        handler.do_POST = Mock()

        handler.do_PUT()

        handler.do_POST.assert_called_once()

    def test_do_delete_calls_do_get(self, mock_handler):
        """Test that DELETE method delegates to GET."""
        handler = mock_handler
        handler.do_GET = Mock()

        handler.do_DELETE()

        handler.do_GET.assert_called_once()

    def test_do_patch_calls_do_post(self, mock_handler):
        """Test that PATCH method delegates to POST."""
        handler = mock_handler
        handler.do_POST = Mock()

        handler.do_PATCH()

        handler.do_POST.assert_called_once()


class TestMainFunction:
    """Test the main entry point."""

    @patch("token_telemetry.config.load_config")
    @patch("token_telemetry.proxy.ProxyServer")
    def test_main(self, mock_server_class, mock_load_config, temp_db):
        """Test main function."""
        from unittest.mock import patch
        
        # Patch sys.argv to avoid argument parsing errors
        with patch("sys.argv", ["telemetry-proxy"]):
            mock_config = Mock()
            mock_config.proxy.host = "localhost"
            mock_config.proxy.port = 8000
            mock_config.proxy.track_endpoints = None
            mock_config.proxy.ignore_endpoints = None
            mock_config.mistral.base_url = "https://api.mistral.ai"
            mock_config.database.path = temp_db
            mock_config.pricing = {}
            mock_load_config.return_value = mock_config

            mock_server = Mock()
            mock_server.start = Mock()
            mock_server_class.return_value = mock_server

            main()

            mock_load_config.assert_called_once()
            mock_server_class.assert_called_once()
            mock_server.start.assert_called_once()


class TestConcurrentAccess:
    """Test concurrent access scenarios."""

    @patch("token_telemetry.proxy.requests.request")
    def test_concurrent_requests(self, mock_request, mock_database, mock_cost_calculator):
        """Test handling concurrent requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"usage": {"prompt_tokens": 10, "completion_tokens": 20}}
        mock_response.headers = {}
        mock_response.content = b"{}"
        mock_request.return_value = mock_response

        TelemetryHandler.database = mock_database
        TelemetryHandler.cost_calculator = mock_cost_calculator

        results = []
        errors = []

        def process_request(thread_id):
            try:
                with patch.object(BaseHTTPRequestHandler, '__init__', lambda *args, **kwargs: None):
                    handler = TelemetryHandler()
                handler.headers = {}
                handler.path = "/test"
                handler.rfile = BytesIO(b"")
                handler.wfile = BytesIO()
                
                request_data = {
                    "method": "POST",
                    "url": f"https://api.mistral.ai/v1/chat/completions/{thread_id}",
                    "headers": {},
                    "data": b"{}",
                    "model": "mistral-medium",
                    "origin": "user",
                }
                processing_time = 0.1
                record = handler._log_telemetry(request_data, mock_response, processing_time)
                results.append(record)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=process_request, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10

        # Verify all records were stored
        all_records = mock_database.get_records()
        assert len(all_records) >= 10


class TestForwardHeadersFiltering:
    """Test filtering of headers for forwarding."""

    @patch("token_telemetry.proxy.requests.request")
    def test_forward_headers_only(self, mock_request, mock_handler):
        """Test that only FORWARD_HEADERS are forwarded."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        handler = mock_handler

        # Set up headers with some that should be forwarded and some that shouldn't
        all_headers = {
            "Authorization": "Bearer token",
            "Content-Type": "application/json",
            "X-Custom-Header": "custom-value",
            "User-Agent": "test-agent",
            "Accept": "application/json",
        }

        # Simulate header extraction
        forward_headers = {}
        for header in FORWARD_HEADERS:
            if header in all_headers:
                forward_headers[header] = all_headers[header]

        # Add telemetry headers
        forward_headers["X-Telemetry-Model"] = "mistral-medium"
        forward_headers["X-Telemetry-Origin"] = "user"

        request_data = {
            "method": "POST",
            "url": "https://api.mistral.ai/v1/chat/completions",
            "headers": forward_headers,
            "data": b"{}",
        }

        handler._forward_request(request_data)

        # Verify only forward headers + telemetry headers were used
        call_args = mock_request.call_args
        sent_headers = call_args[1]["headers"]

        assert "Authorization" in sent_headers
        assert "Content-Type" in sent_headers
        assert "User-Agent" in sent_headers
        assert "Accept" in sent_headers
        assert "X-Telemetry-Model" in sent_headers
        assert "X-Telemetry-Origin" in sent_headers
        assert "X-Custom-Header" not in sent_headers


class TestResponseBuildingEdgeCases:
    """Test edge cases in response building."""

    def test_build_response_empty_content(self, mock_handler):
        """Test building response with empty content."""
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

    def test_build_response_special_characters(self, mock_handler):
        """Test building response with special characters."""
        handler = mock_handler
        handler.wfile = BytesIO()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        special_content = b'{"test": "value"}'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json; charset=utf-8"}
        mock_response.content = special_content

        handler._build_response(mock_response)

        assert handler.wfile.getvalue() == special_content


class TestCostCalculatorIntegration:
    """Test integration with cost calculator."""

    def test_cost_calculator_custom_pricing(self, mock_handler, mock_database):
        """Test cost calculation with custom pricing."""
        custom_pricing = {
            "test-model": {
                "input": 0.50,
                "output": 1.00,
            }
        }
        cost_calculator = CostCalculator(pricing_config=custom_pricing)

        handler = mock_handler
        handler.cost_calculator = cost_calculator

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "usage": {
                "prompt_tokens": 1_000_000,
                "completion_tokens": 1_000_000,
            }
        }

        request_data = {
            "url": "/test",
            "model": "test-model",
            "origin": "user",
        }

        record = handler._log_telemetry(request_data, mock_response, 0.1)

        # With custom pricing: input $0.50 per 1M, output $1.00 per 1M
        # 1M + 1M = $1.50
        assert record.cost == 1.50


class TestDatabaseIntegration:
    """Test integration with database."""

    def test_database_insert_on_telemetry_log(self, mock_handler, mock_database):
        """Test that telemetry records are inserted into database."""
        initial_count = mock_database.get_total_count()

        handler = mock_handler

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"usage": {"prompt_tokens": 100, "completion_tokens": 200}}

        request_data = {
            "url": "/test",
            "model": "test-model",
            "origin": "test-origin",
        }

        handler._log_telemetry(request_data, mock_response, 0.5)

        new_count = mock_database.get_total_count()
        assert new_count == initial_count + 1

        # Verify the record
        records = mock_database.get_records()
        assert records[0].model == "test-model"
        assert records[0].origin == "test-origin"
        assert records[0].request_tokens == 100
        assert records[0].response_tokens == 200

    def test_database_error_non_blocking(self, mock_handler, temp_db):
        """Test that database errors don't block request processing."""
        # Create a database that will fail
        mock_db = Mock()
        mock_db.insert_record.side_effect = Exception("Database error")

        handler = mock_handler
        handler.database = mock_db

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"usage": {"prompt_tokens": 10, "completion_tokens": 20}}

        request_data = {
            "url": "/test",
            "model": "test",
            "origin": "user",
        }

        # Should not raise an exception
        record = handler._log_telemetry(request_data, mock_response, 0.1)
        assert record is not None
        
        # Database error should have been logged but not raised
        mock_db.insert_record.assert_called_once()
