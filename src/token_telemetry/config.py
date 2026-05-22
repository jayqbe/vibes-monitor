"""
Configuration Management for Token Telemetry.

Handles loading configuration from files and environment variables.
Supports YAML and JSON configuration formats.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class ProxyConfig:
    """Proxy server configuration."""
    host: str = "localhost"
    port: int = 8000
    track_endpoints: Optional[list] = None  # List of endpoint patterns to track (None = all)
    ignore_endpoints: Optional[list] = None  # List of endpoint patterns to ignore


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


@dataclass
class Config:
    """
    Main configuration class for Token Telemetry.
    
    Holds all configuration values loaded from files and environment variables.
    """
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    mistral: MistralConfig = field(default_factory=MistralConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    pricing: Dict[str, Dict[str, float]] = field(default_factory=dict)


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    """
    Load a YAML file.
    
    Args:
        path: Path to the YAML file
        
    Returns:
        Dictionary containing the YAML data
        
    Raises:
        ValueError: If YAML is not available or file cannot be loaded
    """
    if not HAS_YAML:
        raise ValueError("PyYAML is required to load YAML files. Install with: pip install pyyaml")
    
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}


def _load_json_file(path: Path) -> Dict[str, Any]:
    """
    Load a JSON file.
    
    Args:
        path: Path to the JSON file
        
    Returns:
        Dictionary containing the JSON data
    """
    with open(path, 'r') as f:
        return json.load(f)


def _load_config_file(path: Path) -> Dict[str, Any]:
    """
    Load a configuration file (YAML or JSON).
    
    Args:
        path: Path to the configuration file
        
    Returns:
        Dictionary containing the configuration data
        
    Raises:
        ValueError: If file format is not supported
    """
    suffix = path.suffix.lower()
    
    if suffix in ('.yaml', '.yml'):
        return _load_yaml_file(path)
    elif suffix == '.json':
        return _load_json_file(path)
    else:
        raise ValueError(f"Unsupported configuration file format: {suffix}")


def _merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two configuration dictionaries.
    
    Args:
        base: Base configuration
        override: Override configuration
        
    Returns:
        Merged configuration
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


def _get_env_value(key: str, default: Any = None) -> Any:
    """
    Get a value from environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Value from environment or default
    """
    value = os.environ.get(key)
    if value is None:
        return default
    
    # Try to convert to appropriate type
    if value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    
    try:
        return int(value)
    except ValueError:
        pass
    
    try:
        return float(value)
    except ValueError:
        pass
    
    return value


def _load_env_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    
    Environment variables are mapped as follows:
    - TELEMETRY_PROXY_HOST -> proxy.host
    - TELEMETRY_PROXY_PORT -> proxy.port
    - MISTRAL_BASE_URL -> mistral.base_url
    - TELEMETRY_DB_PATH -> database.path
    
    Returns:
        Dictionary containing configuration from environment
    """
    config = {}
    
    # Proxy configuration
    proxy = {}
    if 'TELEMETRY_PROXY_HOST' in os.environ:
        proxy['host'] = _get_env_value('TELEMETRY_PROXY_HOST')
    if 'TELEMETRY_PROXY_PORT' in os.environ:
        proxy['port'] = _get_env_value('TELEMETRY_PROXY_PORT', 8000)
    if proxy:
        config['proxy'] = proxy
    
    # Mistral configuration
    mistral = {}
    if 'MISTRAL_BASE_URL' in os.environ:
        mistral['base_url'] = _get_env_value('MISTRAL_BASE_URL')
    if mistral:
        config['mistral'] = mistral
    
    # Database configuration
    database = {}
    if 'TELEMETRY_DB_PATH' in os.environ:
        database['path'] = _get_env_value('TELEMETRY_DB_PATH')
    if database:
        config['database'] = database
    
    return config


def _parse_pricing_config(pricing_data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """
    Parse pricing configuration into a standardized format.
    
    Args:
        pricing_data: Raw pricing configuration data
        
    Returns:
        Parsed pricing configuration with model -> {input, output} structure
    """
    parsed = {}
    
    for model, rates in pricing_data.items():
        if isinstance(rates, dict):
            parsed[model] = {
                'input': float(rates.get('input', 0.25)),
                'output': float(rates.get('output', 0.75)),
            }
        elif isinstance(rates, (int, float)):
            # Legacy format: single rate for both input and output
            parsed[model] = {
                'input': float(rates),
                'output': float(rates),
            }
    
    return parsed


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
    """
    # Start with empty config
    merged_config: Dict[str, Any] = {}
    
    # Load default configuration from package
    defaults_dir = Path(__file__).parent.parent.parent / "config"
    
    # Load default config
    default_config_path = defaults_dir / "default_config.yaml"
    if default_config_path.exists():
        merged_config = _merge_configs(merged_config, _load_config_file(default_config_path))
    
    # Load default pricing
    default_pricing_path = defaults_dir / "default_pricing.yaml"
    if default_pricing_path.exists():
        pricing_data = _load_config_file(default_pricing_path)
        merged_config['pricing'] = _parse_pricing_config(pricing_data.get('pricing', {}))
    
    # Load user configuration file
    if config_path:
        user_config_path = Path(config_path)
        if user_config_path.exists():
            merged_config = _merge_configs(merged_config, _load_config_file(user_config_path))
    else:
        # Check for config/local.yaml
        local_config_path = Path("config") / "local.yaml"
        if local_config_path.exists():
            merged_config = _merge_configs(merged_config, _load_config_file(local_config_path))
    
    # Load environment variables (highest priority)
    env_config = _load_env_config()
    merged_config = _merge_configs(merged_config, env_config)
    
    # Build Config object
    config = Config()
    
    # Parse proxy config
    proxy_data = merged_config.get('proxy', {})
    config.proxy = ProxyConfig(
        host=proxy_data.get('host', 'localhost'),
        port=proxy_data.get('port', 8000),
        track_endpoints=proxy_data.get('track_endpoints'),
        ignore_endpoints=proxy_data.get('ignore_endpoints'),
    )
    
    # Parse mistral config
    mistral_data = merged_config.get('mistral', {})
    config.mistral = MistralConfig(
        base_url=mistral_data.get('base_url', 'https://api.mistral.ai'),
    )
    
    # Parse database config
    database_data = merged_config.get('database', {})
    config.database = DatabaseConfig(
        path=database_data.get('path', 'telemetry.db'),
    )
    
    # Parse logging config
    logging_data = merged_config.get('logging', {})
    config.logging = LoggingConfig(
        level=logging_data.get('level', 'INFO'),
        format=logging_data.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        file=logging_data.get('file', 'telemetry.log'),
    )
    
    # Parse pricing config
    pricing_data = merged_config.get('pricing', {})
    config.pricing = _parse_pricing_config(pricing_data)
    
    return config


def get_config_path() -> Optional[Path]:
    """
    Get the path to the user's configuration file.
    
    Returns:
        Path to the configuration file, or None if not found
    """
    # Check for config/local.yaml
    local_path = Path("config") / "local.yaml"
    if local_path.exists():
        return local_path
    
    # Check for config.yaml in current directory
    current_path = Path("config.yaml")
    if current_path.exists():
        return current_path
    
    return None
