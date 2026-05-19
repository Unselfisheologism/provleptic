# src/recommendation/__init__.py
from .generator import RecommendationGenerator, get_recommendation_generator
from .prompt_templates import PromptTemplates

__all__ = ['RecommendationGenerator', 'get_recommendation_generator', 'PromptTemplates']