# tests/test_recommendation.py
"""Tests for the recommendation generator."""

import pytest
from unittest.mock import patch, MagicMock

from src.recommendation.generator import (
    RecommendationGenerator,
    Recommendation,
    RecommendationResponse
)
from src.recommendation.prompt_templates import PromptTemplates


class TestRecommendation:
    """Tests for Recommendation dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        rec = Recommendation(
            title="Test Title",
            steps=["Step 1", "Step 2"],
            outcome="Improved coverage",
            citation="Source: Derived from analysis",
            confidence=0.85
        )
        
        result = rec.to_dict()
        
        assert result["title"] == "Test Title"
        assert len(result["steps"]) == 2
        assert result["confidence"] == 0.85

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "title": "Test",
            "steps": ["A", "B"],
            "outcome": "Result",
            "citation": "Source: Test",
            "confidence": 0.9
        }
        
        rec = Recommendation.from_dict(data)
        
        assert rec.title == "Test"
        assert rec.confidence == 0.9


class TestRecommendationResponse:
    """Tests for RecommendationResponse dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        rec = Recommendation(
            title="Test",
            steps=["Step"],
            outcome="Result",
            citation="Source: Test",
            confidence=0.8
        )
        
        response = RecommendationResponse(
            summary="Summary",
            recommendations=[rec],
            overall_confidence=0.8,
            rule_id="test_rule"
        )
        
        result = response.to_dict()
        
        assert result["summary"] == "Summary"
        assert len(result["recommendations"]) == 1
        assert result["rule_id"] == "test_rule"


class TestPromptTemplates:
    """Tests for prompt templates."""

    def test_get_template(self):
        """Test getting templates by type."""
        template = PromptTemplates.get_template("base")
        assert template is not None
        
        template = PromptTemplates.get_template("pmay_utilization")
        assert template is not None

    def test_format_generic_recommendation(self):
        """Test generic recommendation formatting."""
        result = PromptTemplates.format_generic_recommendation(
            rule_id="test_rule",
            rule_name="Test Rule",
            rule_prompt="Test prompt",
            context_data={"population": 5000000},
            context_summary="Test context"
        )
        
        assert "test_rule" in result
        assert "Test prompt" in result
        assert "population" in result

    def test_get_citation_instruction(self):
        """Test citation instruction."""
        instruction = PromptTemplates.get_citation_instruction()
        
        assert "CITATION" in instruction
        assert "Source:" in instruction


class TestRecommendationGenerator:
    """Tests for RecommendationGenerator."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance."""
        return RecommendationGenerator()

    def test_summarize_context(self, generator):
        """Test context summarization."""
        context = {
            "name": "Nashik",
            "population": 6000000,
            "pmay_utilization_percent": 45
        }
        
        result = generator._summarize_context(context, "Nashik")
        
        assert "Nashik" in result
        assert "population" in result

    def test_minimize_data(self, generator):
        """Test data minimization."""
        context = {
            "name": "Nashik",
            "population": 6000000,
            "aadhaar_number": "123456789012",
            "phone": "9876543210",
            "pmay_utilization_percent": 45
        }
        
        result = generator._minimize_data(context)
        
        assert "name" in result or "pmay_utilization_percent" in result
        assert "aadhaar_number" not in result
        assert "phone" not in result

    def test_generate_fallback_response(self, generator):
        """Test fallback response generation."""
        result = generator._generate_fallback_response(
            rule_id="test_rule",
            context_data={"population": 5000000}
        )
        
        assert result.summary is not None
        assert len(result.recommendations) >= 1
        assert result.overall_confidence == 0.5

    def test_parse_json_response(self, generator):
        """Test JSON response parsing."""
        valid_json = '{"summary": "Test", "recommendations": [], "overall_confidence": 0.8}'
        
        result = generator._parse_json_response(valid_json)
        
        assert result["summary"] == "Test"
        assert result["overall_confidence"] == 0.8

    def test_parse_json_response_with_extraction(self, generator):
        """Test JSON extraction from text."""
        text_with_json = 'Here is the result: {"summary": "Test", "recommendations": [], "overall_confidence": 0.8}'
        
        result = generator._parse_json_response(text_with_json)
        
        assert result["summary"] == "Test"