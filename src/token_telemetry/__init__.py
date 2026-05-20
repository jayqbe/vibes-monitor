"""
Token Telemetry for Vibe CLI

A standalone token telemetry system that runs as a proxy wrapper around Vibe CLI
to measure model API traffic, compute costs, and output text-based summaries.

Components:
- Proxy Wrapper: Intercepts API calls from Vibe CLI
- Telemetry Logger: Records metrics to SQLite database
- Cost Calculator: Computes cost based on Mistral AI pricing
- Reporter: Generates text-based summaries with category breakdowns
"""

__version__ = "1.0.0"
__author__ = "Mistral Vibe"
__description__ = "Token Telemetry Proxy for Vibe CLI"


# Lazy imports to avoid circular dependencies
def __getattr__(name: str):
    """Lazy import of submodules to avoid circular dependencies."""
    _modules = {
        "Config": "token_telemetry.config",
        "load_config": "token_telemetry.config",
        "Database": "token_telemetry.database",
        "CostCalculator": "token_telemetry.cost_calculator",
        "calculate_cost": "token_telemetry.cost_calculator",
        "ProxyServer": "token_telemetry.proxy",
        "TelemetryHandler": "token_telemetry.proxy",
        "Reporter": "token_telemetry.reporter",
        "generate_summary": "token_telemetry.reporter",
        "CallRecord": "token_telemetry.models",
        "SummaryStats": "token_telemetry.models",
    }
    
    if name in _modules:
        module = __import__(_modules[name], fromlist=[name])
        return getattr(module, name)
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    "Config",
    "load_config",
    "Database",
    "CostCalculator",
    "calculate_cost",
    "ProxyServer",
    "TelemetryHandler",
    "Reporter",
    "generate_summary",
    "CallRecord",
    "SummaryStats",
]
