"""Tests for premium models module."""
import pytest
from tessera.premium_models import is_premium_model, get_model_multiplier

@pytest.mark.unit
class TestPremiumModels:
    def test_is_premium_gpt5(self):
        assert is_premium_model("gpt-5") is True
    
    def test_is_premium_claude_sonnet(self):
        assert is_premium_model("claude-sonnet-4") is True
    
    def test_not_premium_gpt4o(self):
        assert is_premium_model("gpt-4o") is False
    
    def test_get_multiplier_opus(self):
        mult = get_model_multiplier("claude-opus-4.1")
        assert mult == 10.0
    
    def test_get_multiplier_free(self):
        mult = get_model_multiplier("gpt-4o")
        assert mult == 0.0
