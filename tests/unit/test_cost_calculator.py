"""
Unit tests for the cost calculator module.

Tests cost calculation logic, pricing configuration, and edge cases.
"""

import pytest

from token_telemetry.cost_calculator import (
    CostCalculator,
    calculate_cost,
    get_cost_calculator,
    reset_cost_calculator,
)


@pytest.fixture(autouse=True)
def reset_calculator():
    """Reset the global calculator before and after each test."""
    reset_cost_calculator()
    yield
    reset_cost_calculator()


class TestCostCalculator:
    """Test CostCalculator class."""
    
    def test_default_pricing(self):
        """Test cost calculation with default pricing."""
        calculator = CostCalculator()
        
        # Test with known values
        # Default: input $0.25 per 1M, output $0.75 per 1M
        # For 1M input + 1M output: 0.25 + 0.75 = $1.00
        cost = calculator.calculate_cost("mistral-medium", 1_000_000, 1_000_000)
        assert cost == 1.0
    
    def test_mistral_tiny_pricing(self):
        """Test cost calculation for mistral-tiny."""
        calculator = CostCalculator()
        
        # 1000 input tokens + 2000 output tokens
        # Input: 1000/1M * 0.25 = 0.00025
        # Output: 2000/1M * 0.75 = 0.0015
        # Total: 0.00175
        cost = calculator.calculate_cost("mistral-tiny", 1000, 2000)
        assert abs(cost - 0.00175) < 0.00001
    
    def test_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        calculator = CostCalculator()
        
        cost = calculator.calculate_cost("mistral-medium", 0, 0)
        assert cost == 0.0
    
    def test_unknown_model_uses_default(self):
        """Test that unknown models use default pricing."""
        calculator = CostCalculator()
        
        cost = calculator.calculate_cost("unknown-model", 1_000_000, 1_000_000)
        assert cost == 1.0  # Default is same as mistral models
    
    def test_negative_tokens_raises_error(self):
        """Test that negative token counts raise ValueError."""
        calculator = CostCalculator()
        
        with pytest.raises(ValueError, match="Token counts cannot be negative"):
            calculator.calculate_cost("mistral-medium", -100, 0)
        
        with pytest.raises(ValueError, match="Token counts cannot be negative"):
            calculator.calculate_cost("mistral-medium", 0, -100)
    
    def test_custom_pricing(self):
        """Test cost calculation with custom pricing."""
        custom_pricing = {
            "custom-model": {
                "input": 0.50,
                "output": 1.00,
            }
        }
        calculator = CostCalculator(pricing_config=custom_pricing)
        
        # With custom pricing: input $0.50 per 1M, output $1.00 per 1M
        cost = calculator.calculate_cost("custom-model", 1_000_000, 1_000_000)
        assert cost == 1.50
    
    def test_custom_pricing_fallback(self):
        """Test that custom pricing falls back to default for unknown models."""
        custom_pricing = {
            "custom-model": {
                "input": 0.50,
                "output": 1.00,
            }
        }
        calculator = CostCalculator(pricing_config=custom_pricing)
        
        # Unknown model should use default pricing
        cost = calculator.calculate_cost("mistral-medium", 1_000_000, 1_000_000)
        # Default pricing should be used (from the calculator's default)
        assert abs(cost - 1.0) < 0.0001


class TestPricingConfiguration:
    """Test pricing configuration management."""
    
    def test_get_pricing_for_model(self):
        """Test getting pricing for a specific model."""
        calculator = CostCalculator()
        
        pricing = calculator.get_pricing_for_model("mistral-medium")
        assert pricing["input"] == 0.25
        assert pricing["output"] == 0.75
    
    def test_get_pricing_for_unknown_model(self):
        """Test getting pricing for unknown model uses default."""
        calculator = CostCalculator()
        
        pricing = calculator.get_pricing_for_model("unknown-model")
        assert pricing["input"] == 0.25  # Default input rate
        assert pricing["output"] == 0.75  # Default output rate
    
    def test_get_all_models(self):
        """Test getting all configured models."""
        calculator = CostCalculator()
        
        models = calculator.get_all_models()
        assert "mistral-tiny" in models
        assert "mistral-medium" in models
        assert "mistral-large" in models
        assert "default" in models
    
    def test_add_model(self):
        """Test adding a new model."""
        calculator = CostCalculator()
        
        calculator.add_model("new-model", input_rate=0.10, output_rate=0.20)
        
        pricing = calculator.get_pricing_for_model("new-model")
        assert pricing["input"] == 0.10
        assert pricing["output"] == 0.20
    
    def test_update_model(self):
        """Test updating an existing model."""
        calculator = CostCalculator()
        
        # Update mistral-medium pricing
        calculator.update_model("mistral-medium", input_rate=0.30)
        
        pricing = calculator.get_pricing_for_model("mistral-medium")
        assert pricing["input"] == 0.30
        assert pricing["output"] == 0.75  # Unchanged
    
    def test_update_nonexistent_model(self):
        """Test updating a non-existent model adds it."""
        calculator = CostCalculator()
        
        calculator.update_model("new-model", input_rate=0.10, output_rate=0.20)
        
        pricing = calculator.get_pricing_for_model("new-model")
        assert pricing["input"] == 0.10
        assert pricing["output"] == 0.20
    
    def test_remove_model(self):
        """Test removing a model."""
        calculator = CostCalculator()
        
        # Add a custom model first
        calculator.add_model("temp-model", input_rate=0.10, output_rate=0.20)
        
        assert "temp-model" in calculator.get_all_models()
        
        calculator.remove_model("temp-model")
        
        assert "temp-model" not in calculator.get_all_models()
    
    def test_cannot_remove_default_model(self):
        """Test that default model cannot be removed."""
        calculator = CostCalculator()
        
        # Try to remove default model
        calculator.remove_model("default")
        
        # Default should still be there
        assert "default" in calculator.get_all_models()


class TestGlobalCalculator:
    """Test global calculator functions."""
    
    def test_get_cost_calculator(self):
        """Test getting the global calculator."""
        calculator = get_cost_calculator()
        assert isinstance(calculator, CostCalculator)
    
    def test_get_cost_calculator_singleton(self):
        """Test that get_cost_calculator returns the same instance."""
        calc1 = get_cost_calculator()
        calc2 = get_cost_calculator()
        assert calc1 is calc2
    
    def test_get_cost_calculator_with_config(self):
        """Test getting calculator with custom config."""
        custom_pricing = {"test": {"input": 0.1, "output": 0.2}}
        calculator = get_cost_calculator(pricing_config=custom_pricing)
        
        pricing = calculator.get_pricing_for_model("test")
        assert pricing["input"] == 0.1


class TestConvenienceFunction:
    """Test the convenience calculate_cost function."""
    
    def test_calculate_cost_function(self):
        """Test the calculate_cost convenience function."""
        cost = calculate_cost("mistral-medium", 1_000_000, 1_000_000)
        assert cost == 1.0
    
    def test_calculate_cost_with_config(self):
        """Test calculate_cost with custom pricing config."""
        custom_pricing = {"test": {"input": 0.1, "output": 0.2}}
        cost = calculate_cost("test", 1_000_000, 1_000_000, pricing_config=custom_pricing)
        assert abs(cost - 0.3) < 0.0001


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_large_token_counts(self):
        """Test with very large token counts."""
        calculator = CostCalculator()
        
        # 100M tokens
        cost = calculator.calculate_cost("mistral-medium", 100_000_000, 100_000_000)
        # 100 * 0.25 + 100 * 0.75 = 25 + 75 = 100
        assert cost == 100.0
    
    def test_very_small_token_counts(self):
        """Test with very small token counts."""
        calculator = CostCalculator()
        
        cost = calculator.calculate_cost("mistral-medium", 1, 1)
        # 1/1M * 0.25 + 1/1M * 0.75 = 0.000001
        assert abs(cost - 0.000001) < 0.0000001
    
    def test_model_case_insensitive(self):
        """Test that model names are case-insensitive."""
        calculator = CostCalculator()
        
        cost1 = calculator.calculate_cost("mistral-medium", 1_000_000, 1_000_000)
        cost2 = calculator.calculate_cost("MISTRAL-MEDIUM", 1_000_000, 1_000_000)
        cost3 = calculator.calculate_cost("Mistral-Medium", 1_000_000, 1_000_000)
        
        assert cost1 == cost2 == cost3
    
    def test_partial_pricing_config(self):
        """Test with partial pricing configuration."""
        # Only specify input rate
        custom_pricing = {"test": {"input": 0.1}}
        calculator = CostCalculator(pricing_config=custom_pricing)
        
        # Should use default for output
        pricing = calculator.get_pricing_for_model("test")
        assert pricing["input"] == 0.1
        assert pricing["output"] == 0.75  # Default


class TestAllMistralModels:
    """Test cost calculation for all Mistral models."""
    
    def test_all_mistral_models(self):
        """Test that all Mistral models have the same pricing."""
        calculator = CostCalculator()
        
        models = ["mistral-tiny", "mistral-small", "mistral-medium", "mistral-large", "codestral-latest"]
        
        for model in models:
            cost = calculator.calculate_cost(model, 1_000_000, 1_000_000)
            assert cost == 1.0, f"Model {model} has incorrect cost"
