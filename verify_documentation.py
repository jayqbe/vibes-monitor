#!/usr/bin/env python
"""
Verify that all documented APIs are accessible.
This script tests the imports and basic functionality documented in the API reference.
"""

import sys


def test_public_api_imports():
    """Test that all public API symbols can be imported."""
    print("Testing public API imports...")
    
    try:
        from token_telemetry import (
            __version__,
            Config,
            load_config,
            Database,
            CostCalculator,
            calculate_cost,
            ProxyServer,
            TelemetryHandler,
            Reporter,
            generate_summary,
            CallRecord,
            SummaryStats,
        )
        print("✅ All public API imports successful")
        return True
    except ImportError as e:
        print(f"❌ Public API import failed: {e}")
        return False


def test_module_imports():
    """Test that all modules can be imported directly."""
    print("\nTesting direct module imports...")
    
    try:
        import token_telemetry.config
        import token_telemetry.database
        import token_telemetry.cost_calculator
        import token_telemetry.models
        import token_telemetry.proxy
        import token_telemetry.reporter
        import token_telemetry.cli
        print("✅ All module imports successful")
        return True
    except ImportError as e:
        print(f"❌ Module import failed: {e}")
        return False


def test_configuration():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from token_telemetry.config import load_config, Config, ProxyConfig
        
        # Load default config
        config = load_config()
        assert isinstance(config, Config)
        assert hasattr(config, 'proxy')
        assert hasattr(config, 'mistral')
        assert hasattr(config, 'database')
        assert hasattr(config, 'logging')
        assert hasattr(config, 'pricing')
        
        # Check proxy config
        assert isinstance(config.proxy, ProxyConfig)
        assert config.proxy.host == "localhost"
        assert config.proxy.port == 8000
        
        print("✅ Configuration loading works")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_database():
    """Test database operations."""
    print("\nTesting database...")
    
    try:
        import tempfile
        import os
        from token_telemetry.database import Database
        from token_telemetry.models import CallRecord
        
        # Create temp database
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            
            # Insert a record
            record = CallRecord(
                timestamp="2026-05-19T14:30:45",
                model="mistral-medium",
                endpoint="/v1/chat/completions",
                origin="user",
                request_tokens=1000,
                response_tokens=500,
                processing_time=1.234,
                status_code=200,
                cost=0.001125,
            )
            record_id = db.insert_record(record)
            assert record_id > 0
            
            # Get record
            fetched = db.get_record(record_id)
            assert fetched is not None
            assert fetched.model == "mistral-medium"
            
            # Get summary
            stats = db.get_summary_stats()
            assert stats.total_calls == 1
            assert stats.total_request_tokens == 1000
            assert stats.total_response_tokens == 500
            
        print("✅ Database operations work")
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


def test_cost_calculator():
    """Test cost calculation."""
    print("\nTesting cost calculator...")
    
    try:
        from token_telemetry.cost_calculator import CostCalculator, calculate_cost
        
        # Test with default pricing
        calculator = CostCalculator()
        cost = calculator.calculate_cost("mistral-medium", 1000, 2000)
        expected = (1000 / 1_000_000) * 0.25 + (2000 / 1_000_000) * 0.75
        assert abs(cost - expected) < 0.000001
        
        # Test convenience function
        cost2 = calculate_cost("mistral-medium", 1000, 2000)
        assert abs(cost2 - expected) < 0.000001
        
        # Test add_model
        calculator.add_model("test-model", input_rate=0.50, output_rate=1.00)
        assert "test-model" in calculator.get_all_models()
        
        print("✅ Cost calculator works")
        return True
    except Exception as e:
        print(f"❌ Cost calculator test failed: {e}")
        return False


def test_models():
    """Test data models."""
    print("\nTesting models...")
    
    try:
        from token_telemetry.models import CallRecord, SummaryStats
        
        # Test CallRecord
        record = CallRecord(
            timestamp="2026-05-19T14:30:45",
            model="mistral-medium",
            endpoint="/v1/chat/completions",
            origin="user",
            request_tokens=1000,
            response_tokens=500,
            processing_time=1.234,
            status_code=200,
            cost=0.001125,
        )
        assert record.total_tokens() == 1500
        assert record.model == "mistral-medium"
        
        # Test to_dict and from_dict
        data = record.to_dict()
        assert data["model"] == "mistral-medium"
        record2 = CallRecord.from_dict(data)
        assert record2.model == record.model
        
        # Test SummaryStats
        stats = SummaryStats(
            total_calls=42,
            total_request_tokens=12000,
            total_response_tokens=20450,
            total_cost=0.0243,
        )
        assert stats.total_tokens == 32450
        
        print("✅ Models work")
        return True
    except Exception as e:
        print(f"❌ Models test failed: {e}")
        return False


def test_reporter():
    """Test reporter functionality."""
    print("\nTesting reporter...")
    
    try:
        import tempfile
        import os
        from token_telemetry.reporter import Reporter, generate_summary
        from token_telemetry.database import Database
        from token_telemetry.models import CallRecord
        
        # Create temp database with test data
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            
            # Insert test data
            for i in range(5):
                record = CallRecord(
                    timestamp="2026-05-19T14:30:45",
                    model="mistral-medium",
                    endpoint="/v1/chat/completions",
                    origin="user" if i % 2 == 0 else "agent",
                    request_tokens=1000,
                    response_tokens=500,
                    processing_time=1.234,
                    status_code=200,
                    cost=0.001125,
                )
                db.insert_record(record)
            
            # Test reporter
            reporter = Reporter(db_path)
            summary = reporter.generate_summary()
            assert "Token Telemetry Summary" in summary
            assert "Total API Calls: 5" in summary
            
            # Test convenience function
            summary2 = generate_summary(db_path=db_path)
            assert "Token Telemetry Summary" in summary2
            
            # Test export_to_dict
            data = reporter.export_to_dict()
            assert "summary" in data
            assert "records" in data
            
        print("✅ Reporter works")
        return True
    except Exception as e:
        print(f"❌ Reporter test failed: {e}")
        return False


def test_proxy_imports():
    """Test proxy imports (don't start server)."""
    print("\nTesting proxy imports...")
    
    try:
        from token_telemetry.proxy import ProxyServer, TelemetryHandler
        
        # Just test that we can create a ProxyServer (don't start it)
        server = ProxyServer(
            host="localhost",
            port=8000,
            mistral_base_url="https://api.mistral.ai",
            db_path=":memory:",
        )
        assert server.host == "localhost"
        assert server.port == 8000
        assert server.is_running() is False
        
        print("✅ Proxy imports work")
        return True
    except Exception as e:
        print(f"❌ Proxy test failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Documentation Verification")
    print("=" * 60)
    
    tests = [
        test_public_api_imports,
        test_module_imports,
        test_configuration,
        test_database,
        test_cost_calculator,
        test_models,
        test_reporter,
        test_proxy_imports,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("\n✅ All documentation examples are valid!")
        return 0
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
