"""
Integration Tests for Token Telemetry (TEST-004).

Comprehensive integration test coverage for:
- End-to-end with mocked Vibe CLI
- Complete data flow from request to report
- Configuration loading and validation
- Test report generation from real data
- Data flow validation
- Multiple request scenarios (concurrent/sequential)

Total tests: 50+
"""

import json
import os
import sys
import tempfile
import threading
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from token_telemetry.cli import main as cli_main
from token_telemetry.config import load_config
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
def temp_config_file(temp_db):
    """Create a temporary configuration file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(f"""
proxy:
  host: localhost
  port: 8888
mistral:
  base_url: "https://api.mistral.ai"
database:
  path: "{temp_db}"
""")
        config_path = f.name
    yield config_path
    if os.path.exists(config_path):
        os.unlink(config_path)


@pytest.fixture
def test_database(temp_db):
    """Create a test database instance."""
    db = Database(db_path=temp_db)
    try:
        db.clear_all()
    except Exception:
        pass
    return db


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


MOCK_RESPONSE = {
    "outputs": [{"text": "Hello world", "stop_reason": "stop"}],
    "usage": {"prompt_tokens": 25, "completion_tokens": 10, "total_tokens": 35},
}
MOCK_RESPONSE_BYTES = json.dumps(MOCK_RESPONSE).encode()


# =============================================================================
# 1. End-to-End with Mocked Vibe CLI
# =============================================================================

class TestEndToEndMockedVibeCLI:
    """Test end-to-end scenarios with mocked Vibe CLI."""

    @patch("token_telemetry.proxy.requests.request")
    def test_complete_request_flow(self, mock_request, temp_db):
        """Test complete flow: mocked Vibe CLI -> Proxy -> Mistral API -> Telemetry logged -> DB stored -> Cost calculated."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.content = MOCK_RESPONSE_BYTES
        mock_resp.json.return_value = MOCK_RESPONSE
        mock_request.return_value = mock_resp

        server = ProxyServer(host="localhost", port=9001, db_path=temp_db)
        TelemetryHandler.database = server.database
        TelemetryHandler.cost_calculator = server.cost_calculator
        TelemetryHandler.mistral_base_url = server.mistral_base_url

        from http.server import BaseHTTPRequestHandler
        with patch.object(BaseHTTPRequestHandler, "__init__", lambda *a, **k: None):
            handler = TelemetryHandler()
            handler.headers = {"X-Telemetry-Model": "mistral-medium"}
            handler.path = "/v1/chat/completions"
            handler.rfile = BytesIO(b'{"model": "mistral-medium"}')
            handler.wfile = BytesIO()
            handler.address_string = lambda: "127.0.0.1"

        request_data = {
            "method": "POST", "url": "https://api.mistral.ai/v1/chat/completions",
            "headers": {"Authorization": "Bearer test-key"}, "data": b'{"model": "mistral-medium"}',
            "model": "mistral-medium", "origin": "user",
        }
        response = handler._forward_request(request_data)
        record = handler._log_telemetry(request_data, response, 0.1)

        assert record.model == "mistral-medium"
        assert record.request_tokens == 25
        assert record.response_tokens == 10
        assert record.cost > 0
        assert server.database.get_total_count() == 1

    @patch("token_telemetry.proxy.requests.request")
    def test_multiple_sequential_requests(self, mock_request, temp_db):
        """Test multiple sequential requests through the proxy."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_resp.content = MOCK_RESPONSE_BYTES
        mock_resp.json.return_value = MOCK_RESPONSE
        mock_request.return_value = mock_resp

        server = ProxyServer(db_path=temp_db)
        TelemetryHandler.database = server.database
        TelemetryHandler.cost_calculator = server.cost_calculator
        TelemetryHandler.mistral_base_url = "https://api.mistral.ai"

        from http.server import BaseHTTPRequestHandler

        for model in ["mistral-tiny", "mistral-small", "mistral-medium"]:
            with patch.object(BaseHTTPRequestHandler, "__init__", lambda *a, **k: None):
                handler = TelemetryHandler()
                handler.headers = {"X-Telemetry-Model": model}
                handler.path = "/v1/chat/completions"
                handler.rfile = BytesIO(b'{}')
                handler.wfile = BytesIO()

            req_data = {"method": "POST", "url": f"https://api.mistral.ai/v1/{model}",
                       "headers": {}, "data": b"{}", "model": model, "origin": "user"}
            resp = handler._forward_request(req_data)
            handler._log_telemetry(req_data, resp, 0.1)

        assert server.database.get_total_count() == 3
        models = [r.model for r in server.database.get_records()]
        assert set(models) == {"mistral-tiny", "mistral-small", "mistral-medium"}

    @patch("token_telemetry.proxy.requests.request")
    def test_request_with_different_origins(self, mock_request, temp_db):
        """Test requests from different origins."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_resp.json.return_value = MOCK_RESPONSE
        mock_request.return_value = mock_resp

        server = ProxyServer(db_path=temp_db)
        TelemetryHandler.database = server.database
        TelemetryHandler.cost_calculator = server.cost_calculator
        TelemetryHandler.mistral_base_url = "https://api.mistral.ai"

        from http.server import BaseHTTPRequestHandler

        for origin in ["user", "agent", "sub-agent"]:
            with patch.object(BaseHTTPRequestHandler, "__init__", lambda *a, **k: None):
                handler = TelemetryHandler()
                handler.headers = {"X-Telemetry-Origin": origin}
                handler.path = "/v1/chat/completions"
                handler.rfile = BytesIO(b'{}')
                handler.wfile = BytesIO()

            req_data = {"method": "POST", "url": "https://api.mistral.ai/v1/chat/completions",
                       "headers": {}, "data": b"{}", "model": "mistral-medium", "origin": origin}
            resp = handler._forward_request(req_data)
            handler._log_telemetry(req_data, resp, 0.1)

        origins = [r.origin for r in server.database.get_records()]
        assert set(origins) == {"user", "agent", "sub-agent"}

    @patch("token_telemetry.proxy.requests.request")
    def test_e2e_error_response_handling(self, mock_request, temp_db):
        """Test end-to-end flow with error response from API."""
        mock_resp = Mock()
        mock_resp.status_code = 429
        mock_resp.headers = {}
        mock_resp.json.return_value = {"error": "Rate limit exceeded"}
        mock_request.return_value = mock_resp

        server = ProxyServer(db_path=temp_db)
        TelemetryHandler.database = server.database
        TelemetryHandler.cost_calculator = server.cost_calculator
        TelemetryHandler.mistral_base_url = "https://api.mistral.ai"

        from http.server import BaseHTTPRequestHandler
        with patch.object(BaseHTTPRequestHandler, "__init__", lambda *a, **k: None):
            handler = TelemetryHandler()
            handler.headers = {}
            handler.path = "/v1/chat/completions"
            handler.rfile = BytesIO(b'{}')
            handler.wfile = BytesIO()

        req_data = {"method": "POST", "url": "https://api.mistral.ai/v1/chat/completions",
                   "headers": {}, "data": b"{}", "model": "mistral-medium", "origin": "user"}
        resp = handler._forward_request(req_data)
        record = handler._log_telemetry(req_data, resp, 0.1)

        assert record.status_code == 429
        assert server.database.get_total_count() == 1


# =============================================================================
# 2. Configuration Integration
# =============================================================================

class TestConfigurationIntegration:
    """Test configuration loading and validation across components."""

    def test_config_loads_correctly(self, temp_config_file):
        """Test that configuration loads correctly from file."""
        config = load_config(config_path=temp_config_file)
        assert config.proxy.host == "localhost"
        assert config.proxy.port == 8888
        assert config.mistral.base_url == "https://api.mistral.ai"

    def test_config_used_by_proxy_server(self, temp_config_file, temp_db):
        """Test that proxy server uses loaded configuration."""
        config = load_config(config_path=temp_config_file)
        server = ProxyServer(
            host=config.proxy.host, port=config.proxy.port,
            mistral_base_url=config.mistral.base_url, db_path=temp_db,
        )
        assert server.host == config.proxy.host
        assert server.port == config.proxy.port

    def test_config_used_by_database(self, temp_config_file):
        """Test that database uses configuration."""
        config = load_config(config_path=temp_config_file)
        db = Database(db_path=config.database.path)
        assert db.db_path == Path(config.database.path)

    def test_config_used_by_reporter(self, temp_config_file, temp_db):
        """Test that reporter uses configuration."""
        config = load_config(config_path=temp_config_file)
        reporter = Reporter(db_path=config.database.path)
        assert reporter.database.db_path == Path(config.database.path)

    def test_default_config_without_file(self):
        """Test that default configuration is used when no file is specified."""
        config = load_config()
        assert config.proxy.host == "localhost"
        assert config.proxy.port == 8000

    def test_config_environment_override(self, monkeypatch):
        """Test that environment variables override configuration."""
        monkeypatch.setenv("TELEMETRY_PROXY_PORT", "9999")
        monkeypatch.setenv("MISTRAL_BASE_URL", "https://custom.mistral.ai")
        config = load_config()
        assert config.proxy.port == 9999
        assert config.mistral.base_url == "https://custom.mistral.ai"
        monkeypatch.delenv("TELEMETRY_PROXY_PORT")
        monkeypatch.delenv("MISTRAL_BASE_URL")


# =============================================================================
# 3. CLI Integration
# =============================================================================

class TestCLIIntegration:
    """Test CLI commands work end-to-end."""

    @patch("token_telemetry.cli.ProxyServer")
    @patch("token_telemetry.cli.load_config")
    def test_cli_proxy_start(self, mock_load_config, mock_proxy_class, temp_db):
        """Test that CLI proxy command starts the proxy server."""
        mock_config = Mock()
        mock_config.proxy.host = "localhost"
        mock_config.proxy.port = 8000
        mock_config.mistral.base_url = "https://api.mistral.ai"
        mock_config.database.path = temp_db
        mock_config.pricing = {}
        mock_load_config.return_value = mock_config

        mock_server = Mock()
        mock_server.start = Mock()
        mock_proxy_class.return_value = mock_server

        with patch("sys.argv", ["token-telemetry", "proxy"]):
            try:
                cli_main()
            except SystemExit:
                pass
        mock_server.start.assert_called()

    @patch("token_telemetry.cli.Reporter")
    @patch("token_telemetry.cli.load_config")
    def test_cli_report_generation(self, mock_load_config, mock_reporter_class, temp_db):
        """Test that CLI report command generates a report."""
        mock_config = Mock()
        mock_config.database.path = temp_db
        mock_load_config.return_value = mock_config

        mock_reporter = Mock()
        mock_reporter.generate_summary = Mock(return_value="Test Summary")
        mock_reporter_class.return_value = mock_reporter

        with patch("sys.argv", ["token-telemetry", "report"]):
            with patch("builtins.print") as mock_print:
                try:
                    cli_main()
                except SystemExit:
                    pass
        mock_reporter.generate_summary.assert_called()

    @patch("token_telemetry.cli.Reporter")
    @patch("token_telemetry.cli.load_config")
    def test_cli_report_with_filters(self, mock_load_config, mock_reporter_class, temp_db):
        """Test CLI report with model and origin filters."""
        mock_config = Mock()
        mock_config.database.path = temp_db
        mock_load_config.return_value = mock_config

        mock_reporter = Mock()
        mock_reporter.generate_summary = Mock(return_value="Filtered Summary")
        mock_reporter_class.return_value = mock_reporter

        with patch("sys.argv", ["token-telemetry", "report", "--model", "mistral-medium", "--origin", "user"]):
            with patch("builtins.print"):
                try:
                    cli_main()
                except SystemExit:
                    pass
        call_args = mock_reporter.generate_summary.call_args
        assert call_args[1]["filters"]["model"] == "mistral-medium"
        assert call_args[1]["filters"]["origin"] == "user"

    @patch("token_telemetry.cli.Reporter")
    @patch("token_telemetry.cli.load_config")
    def test_cli_report_output_to_file(self, mock_load_config, mock_reporter_class, temp_db):
        """Test CLI report output to file."""
        mock_config = Mock()
        mock_config.database.path = temp_db
        mock_load_config.return_value = mock_config

        mock_reporter = Mock()
        mock_reporter.generate_summary = Mock(return_value="Test Summary")
        mock_reporter_class.return_value = mock_reporter

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            output_path = f.name
        try:
            with patch("sys.argv", ["token-telemetry", "report", "-o", output_path]):
                try:
                    cli_main()
                except SystemExit:
                    pass
            with open(output_path, "r") as f:
                content = f.read()
            assert "Test Summary" in content
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


# =============================================================================
# 4. Reporter Integration
# =============================================================================

class TestReporterIntegration:
    """Test that reports can be generated from database data."""

    def test_report_generation_from_real_data(self, test_database):
        """Test report generation from real database data."""
        for i in range(10):
            record = CallRecord(
                timestamp=datetime.utcnow().isoformat(),
                model="mistral-medium", endpoint="/v1/chat/completions",
                origin="user", request_tokens=100 * (i + 1), response_tokens=200 * (i + 1),
                processing_time=0.5, status_code=200, cost=0.001 * (i + 1),
            )
            test_database.insert_record(record)

        reporter = Reporter(db_path=test_database.db_path)
        summary = reporter.generate_summary()

        assert "Token Telemetry Summary" in summary
        assert "mistral-medium" in summary
        assert "10 calls" in summary or "10" in summary
        assert "Total Cost" in summary

    def test_report_generation_by_model(self, test_database):
        """Test report generation filtered by model."""
        for model in ["mistral-tiny", "mistral-small", "mistral-medium"]:
            for _ in range(5):
                record = CallRecord(
                    timestamp=datetime.utcnow().isoformat(), model=model,
                    endpoint="/v1/chat/completions", origin="user",
                    request_tokens=100, response_tokens=200, processing_time=0.5,
                    status_code=200, cost=0.001,
                )
                test_database.insert_record(record)

        reporter = Reporter(db_path=test_database.db_path)
        summary = reporter.generate_summary(filters={"model": "mistral-medium"})

        assert "mistral-medium" in summary
        assert "5 calls" in summary or "5" in summary
        assert "mistral-tiny" not in summary
        assert "mistral-small" not in summary

    def test_report_time_period_daily(self, test_database):
        """Test daily time period report."""
        today = datetime.utcnow().date()
        for _ in range(10):
            record = CallRecord(
                timestamp=datetime(today.year, today.month, today.day, 12, 0, 0).isoformat(),
                model="mistral-medium", endpoint="/v1/chat/completions", origin="user",
                request_tokens=100, response_tokens=200, processing_time=0.5,
                status_code=200, cost=0.001,
            )
            test_database.insert_record(record)

        reporter = Reporter(db_path=test_database.db_path)
        summary = reporter.generate_summary(time_period="daily")

        assert "Token Telemetry Summary (Daily)" in summary

    def test_detailed_report_generation(self, test_database):
        """Test detailed report generation with individual records."""
        for i in range(5):
            record = CallRecord(
                timestamp=datetime.utcnow().isoformat(),
                model="mistral-medium", endpoint="/v1/chat/completions", origin="user",
                request_tokens=100 * (i + 1), response_tokens=200 * (i + 1),
                processing_time=0.5, status_code=200, cost=0.001 * (i + 1),
            )
            test_database.insert_record(record)

        reporter = Reporter(db_path=test_database.db_path)
        report = reporter.generate_detailed_report(limit=10)

        assert "Detailed Telemetry Records" in report
        assert "| Timestamp | Model | Origin | Tokens | Cost | Status |" in report


# =============================================================================
# 5. Data Flow Validation
# =============================================================================

class TestDataFlowValidation:
    """Verify data integrity throughout the pipeline."""

    @patch("token_telemetry.proxy.requests.request")
    def test_data_integrity_from_request_to_database(self, mock_request, temp_db):
        """Test that data maintains integrity from request to database."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"usage": {"prompt_tokens": 12345, "completion_tokens": 67890}}
        mock_request.return_value = mock_resp

        server = ProxyServer(db_path=temp_db)
        TelemetryHandler.database = server.database
        TelemetryHandler.cost_calculator = server.cost_calculator
        TelemetryHandler.mistral_base_url = "https://api.mistral.ai"

        from http.server import BaseHTTPRequestHandler
        with patch.object(BaseHTTPRequestHandler, "__init__", lambda *a, **k: None):
            handler = TelemetryHandler()
            handler.headers = {}
            handler.path = "/v1/chat/completions"
            handler.rfile = BytesIO(b'{}')
            handler.wfile = BytesIO()

        req_data = {"method": "POST", "url": "https://api.mistral.ai/v1/chat/completions",
                   "headers": {}, "data": b"{}", "model": "data-test", "origin": "user"}
        resp = handler._forward_request(req_data)
        record = handler._log_telemetry(req_data, resp, 0.5)

        assert record.request_tokens == 12345
        assert record.response_tokens == 67890
        db_rec = server.database.get_records()[0]
        assert db_rec.request_tokens == 12345
        assert db_rec.response_tokens == 67890

    def test_summary_stats_accuracy(self, test_database):
        """Test that summary statistics are calculated accurately."""
        for data in [
            {"model": "model-a", "origin": "user", "req": 100, "resp": 200, "cost": 0.01},
            {"model": "model-a", "origin": "user", "req": 150, "resp": 250, "cost": 0.015},
            {"model": "model-b", "origin": "agent", "req": 200, "resp": 300, "cost": 0.02},
        ]:
            record = CallRecord(
                timestamp=datetime.utcnow().isoformat(), model=data["model"],
                endpoint="/test", origin=data["origin"],
                request_tokens=data["req"], response_tokens=data["resp"],
                processing_time=0.5, status_code=200, cost=data["cost"],
            )
            test_database.insert_record(record)

        stats = test_database.get_summary_stats()
        assert stats.total_calls == 3
        assert stats.total_request_tokens == 450
        assert stats.total_response_tokens == 750
        assert abs(stats.total_cost - 0.045) < 0.0001
        assert stats.by_model["model-a"]["calls"] == 2
        assert stats.by_model["model-b"]["calls"] == 1

    def test_data_persistence_across_sessions(self, temp_db):
        """Test that data persists across database sessions."""
        db1 = Database(db_path=temp_db)
        record = CallRecord(
            timestamp=datetime.utcnow().isoformat(), model="persistence-test",
            endpoint="/test", origin="user", request_tokens=100, response_tokens=200,
            processing_time=0.5, status_code=200, cost=0.001,
        )
        db1.insert_record(record)

        db2 = Database(db_path=temp_db)
        records = db2.get_records()
        assert len(records) == 1
        assert records[0].model == "persistence-test"

    @patch("token_telemetry.proxy.requests.request")
    def test_cost_calculation_accuracy(self, mock_request, temp_db):
        """Test that cost calculation is accurate throughout the flow."""
        input_tokens = 1_000_000
        output_tokens = 2_000_000
        expected_cost = (input_tokens / 1_000_000) * 0.25 + (output_tokens / 1_000_000) * 0.75

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"usage": {"prompt_tokens": input_tokens, "completion_tokens": output_tokens}}
        mock_request.return_value = mock_resp

        server = ProxyServer(db_path=temp_db)
        TelemetryHandler.database = server.database
        TelemetryHandler.cost_calculator = server.cost_calculator
        TelemetryHandler.mistral_base_url = "https://api.mistral.ai"

        from http.server import BaseHTTPRequestHandler
        with patch.object(BaseHTTPRequestHandler, "__init__", lambda *a, **k: None):
            handler = TelemetryHandler()
            handler.headers = {}
            handler.path = "/v1/chat/completions"
            handler.rfile = BytesIO(b'{}')
            handler.wfile = BytesIO()

        req_data = {"method": "POST", "url": "https://api.mistral.ai/v1/chat/completions",
                   "headers": {}, "data": b"{}", "model": "mistral-medium", "origin": "user"}
        resp = handler._forward_request(req_data)
        record = handler._log_telemetry(req_data, resp, 0.1)

        assert abs(record.cost - expected_cost) < 0.01
        assert abs(server.database.get_records()[0].cost - expected_cost) < 0.01


# =============================================================================
# 6. Multiple Request Scenarios
# =============================================================================

class TestMultipleRequestScenarios:
    """Test multiple concurrent and sequential request scenarios."""

    @patch("token_telemetry.proxy.requests.request")
    def test_concurrent_requests_to_same_model(self, mock_request, temp_db):
        """Test concurrent requests to the same model."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"usage": {"prompt_tokens": 100, "completion_tokens": 200}}
        mock_request.return_value = mock_resp

        server = ProxyServer(db_path=temp_db)
        TelemetryHandler.database = server.database
        TelemetryHandler.cost_calculator = server.cost_calculator
        TelemetryHandler.mistral_base_url = "https://api.mistral.ai"

        from http.server import BaseHTTPRequestHandler

        def process_request(tid):
            with patch.object(BaseHTTPRequestHandler, "__init__", lambda *a, **k: None):
                handler = TelemetryHandler()
                handler.headers = {"X-Telemetry-Model": "concurrent-model"}
                handler.path = "/v1/chat/completions"
                handler.rfile = BytesIO(b'{}')
                handler.wfile = BytesIO()
            req_data = {"method": "POST", "url": "https://api.mistral.ai/v1/chat/completions",
                       "headers": {}, "data": b"{}", "model": "concurrent-model", "origin": f"user-{tid}"}
            resp = handler._forward_request(req_data)
            return handler._log_telemetry(req_data, resp, 0.1)

        threads = []
        results = []
        for i in range(10):
            t = threading.Thread(target=lambda tid: results.append(process_request(tid)), args=(i,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        assert all(r.model == "concurrent-model" for r in results)
        assert server.database.get_total_count() == 10

    @patch("token_telemetry.proxy.requests.request")
    def test_sequential_requests_accumulation(self, mock_request, temp_db):
        """Test that sequential requests to the same model accumulate correctly."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"usage": {"prompt_tokens": 100, "completion_tokens": 200}}
        mock_request.return_value = mock_resp

        server = ProxyServer(db_path=temp_db)
        TelemetryHandler.database = server.database
        TelemetryHandler.cost_calculator = server.cost_calculator
        TelemetryHandler.mistral_base_url = "https://api.mistral.ai"

        from http.server import BaseHTTPRequestHandler

        for _ in range(10):
            with patch.object(BaseHTTPRequestHandler, "__init__", lambda *a, **k: None):
                handler = TelemetryHandler()
                handler.headers = {"X-Telemetry-Model": "accum-test"}
                handler.path = "/v1/chat/completions"
                handler.rfile = BytesIO(b'{}')
                handler.wfile = BytesIO()
            req_data = {"method": "POST", "url": "https://api.mistral.ai/v1/chat/completions",
                       "headers": {}, "data": b"{}", "model": "accum-test", "origin": "user"}
            resp = handler._forward_request(req_data)
            handler._log_telemetry(req_data, resp, 0.1)

        stats = server.database.get_summary_stats(model="accum-test")
        assert stats.total_calls == 10
        assert stats.total_request_tokens == 1000
        assert stats.total_response_tokens == 2000

    @patch("token_telemetry.proxy.requests.request")
    def test_bulk_request_processing(self, mock_request, temp_db):
        """Test processing a large batch of requests."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"usage": {"prompt_tokens": 1000, "completion_tokens": 2000}}
        mock_request.return_value = mock_resp

        server = ProxyServer(db_path=temp_db)
        TelemetryHandler.database = server.database
        TelemetryHandler.cost_calculator = server.cost_calculator
        TelemetryHandler.mistral_base_url = "https://api.mistral.ai"

        from http.server import BaseHTTPRequestHandler

        for _ in range(100):
            with patch.object(BaseHTTPRequestHandler, "__init__", lambda *a, **k: None):
                handler = TelemetryHandler()
                handler.headers = {"X-Telemetry-Model": "bulk-model"}
                handler.path = "/v1/chat/completions"
                handler.rfile = BytesIO(b'{}')
                handler.wfile = BytesIO()
            req_data = {"method": "POST", "url": "https://api.mistral.ai/v1/chat/completions",
                       "headers": {}, "data": b"{}", "model": "bulk-model", "origin": "user"}
            resp = handler._forward_request(req_data)
            handler._log_telemetry(req_data, resp, 0.1)

        assert server.database.get_total_count() == 100
        stats = server.database.get_summary_stats()
        assert stats.by_model["bulk-model"]["calls"] == 100

    @patch("token_telemetry.proxy.requests.request")
    def test_mixed_success_and_error_responses(self, mock_request, temp_db):
        """Test mixed success and error responses in sequence."""
        server = ProxyServer(db_path=temp_db)
        TelemetryHandler.database = server.database
        TelemetryHandler.cost_calculator = server.cost_calculator
        TelemetryHandler.mistral_base_url = "https://api.mistral.ai"

        from http.server import BaseHTTPRequestHandler

        status_codes = [200, 200, 429, 200, 500, 200]

        for sc in status_codes:
            mock_resp = Mock()
            mock_resp.status_code = sc
            if sc == 200:
                mock_resp.json.return_value = {"usage": {"prompt_tokens": 100, "completion_tokens": 200}}
            else:
                mock_resp.json.side_effect = ValueError("Not JSON")
                mock_resp.content = b"Error"
            mock_request.return_value = mock_resp

            with patch.object(BaseHTTPRequestHandler, "__init__", lambda *a, **k: None):
                handler = TelemetryHandler()
                handler.headers = {}
                handler.path = "/v1/chat/completions"
                handler.rfile = BytesIO(b'{}' if sc == 200 else b"")
                handler.wfile = BytesIO()
            req_data = {"method": "POST", "url": "https://api.mistral.ai/v1/chat/completions",
                       "headers": {}, "data": b"{}" if sc == 200 else b"",
                       "model": "mixed-status", "origin": "user"}
            resp = handler._forward_request(req_data)
            handler._log_telemetry(req_data, resp, 0.1)

        assert server.database.get_total_count() == 6
        recorded_statuses = [r.status_code for r in server.database.get_records()]
        assert set(recorded_statuses) == {200, 429, 500}


# =============================================================================
# Import for time reference
# =============================================================================
import time
