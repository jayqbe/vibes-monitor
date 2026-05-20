"""
Cost Calculator for Token Telemetry.

Computes costs based on token usage and model-specific pricing.
Supports dynamic pricing configuration from files and environment variables.
"""

import copy
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# Default pricing (Mistral AI - as of May 2026)
# Pricing is per 1M tokens
DEFAULT_PRICING = {
    "default": {
        "input": 0.25,   # $0.25 per 1M input tokens
        "output": 0.75,  # $0.75 per 1M output tokens
    },
    "mistral-tiny": {
        "input": 0.25,
        "output": 0.75,
    },
    "mistral-small": {
        "input": 0.25,
        "output": 0.75,
    },
    "mistral-medium": {
        "input": 0.25,
        "output": 0.75,
    },
    "mistral-large": {
        "input": 0.25,
        "output": 0.75,
    },
    "codestral-latest": {
        "input": 0.25,
        "output": 0.75,
    },
}


class CostCalculator:
    """
    Cost calculator that computes API call costs based on token usage.
    
    Supports configurable pricing per model with fallback to default pricing.
    """
    
    def __init__(self, pricing_config: Optional[Dict[str, Dict[str, float]]] = None) -> None:
        """
        Initialize the cost calculator.
        
        Args:
            pricing_config: Optional pricing configuration dictionary.
                           Format: {model: {input: rate, output: rate}}
                           If None, uses default pricing.
        """
        if pricing_config:
            self.pricing = copy.deepcopy(pricing_config)
        else:
            self.pricing = copy.deepcopy(DEFAULT_PRICING)
        
        # Ensure default pricing is present
        if "default" not in self.pricing:
            self.pricing["default"] = copy.deepcopy(DEFAULT_PRICING["default"])
        
        # Fill in missing keys for all models
        default_pricing = self.pricing["default"]
        for model, rates in self.pricing.items():
            if "input" not in rates:
                rates["input"] = default_pricing["input"]
            if "output" not in rates:
                rates["output"] = default_pricing["output"]
    
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
        """
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("Token counts cannot be negative")
        
        # Get pricing for this model
        model_pricing = self.pricing.get(model.lower())
        
        # Fall back to default pricing if model not found
        if model_pricing is None:
            logger.warning(f"Model '{model}' not found in pricing config, using default")
            model_pricing = self.pricing.get("default", DEFAULT_PRICING["default"])
        
        # Calculate cost (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * model_pricing.get("input", 0.25)
        output_cost = (output_tokens / 1_000_000) * model_pricing.get("output", 0.75)
        
        total_cost = input_cost + output_cost
        
        logger.debug(
            f"Cost calculation: model={model}, input_tokens={input_tokens}, "
            f"output_tokens={output_tokens}, cost=${total_cost:.6f}"
        )
        
        return total_cost
    
    def get_pricing_for_model(self, model: str) -> Dict[str, float]:
        """
        Get the pricing configuration for a specific model.
        
        Args:
            model: The model name
            
        Returns:
            Dictionary with 'input' and 'output' rates
        """
        model_pricing = self.pricing.get(model.lower())
        
        if model_pricing is None:
            logger.warning(f"Model '{model}' not found in pricing config, using default")
            return self.pricing.get("default", DEFAULT_PRICING["default"])
        
        return model_pricing
    
    def get_all_models(self) -> list:
        """
        Get a list of all configured models.
        
        Returns:
            List of model names
        """
        return list(self.pricing.keys())
    
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
        """
        self.pricing[model.lower()] = {
            "input": input_rate,
            "output": output_rate,
        }
        logger.info(f"Added pricing for model: {model}")
    
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
        """
        model_key = model.lower()
        
        if model_key not in self.pricing:
            logger.warning(f"Model '{model}' not found, adding it")
            self.add_model(model, input_rate or 0.25, output_rate or 0.75)
            return
        
        if input_rate is not None:
            self.pricing[model_key]["input"] = input_rate
        if output_rate is not None:
            self.pricing[model_key]["output"] = output_rate
        
        logger.info(f"Updated pricing for model: {model}")
    
    def remove_model(self, model: str) -> None:
        """
        Remove a model from the pricing configuration.
        
        Args:
            model: Model name to remove
        """
        model_key = model.lower()
        
        if model_key in self.pricing and model_key != "default":
            del self.pricing[model_key]
            logger.info(f"Removed pricing for model: {model}")


# Global cost calculator instance
_calculator: Optional[CostCalculator] = None


def get_cost_calculator(pricing_config: Optional[Dict[str, Dict[str, float]]] = None) -> CostCalculator:
    """
    Get or create a global cost calculator instance.
    
    Args:
        pricing_config: Optional pricing configuration
        
    Returns:
        CostCalculator instance
    """
    global _calculator
    
    if _calculator is None:
        _calculator = CostCalculator(pricing_config)
    
    return _calculator


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
    """
    calculator = get_cost_calculator(pricing_config)
    return calculator.calculate_cost(model, input_tokens, output_tokens)


def reset_cost_calculator() -> None:
    """Reset the global cost calculator instance."""
    global _calculator
    _calculator = None
