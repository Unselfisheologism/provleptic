# src/recommendation/generator.py
"""LLM-powered recommendation generator with structured output and citation enforcement."""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from loguru import logger

from src.core.opencode_client import opencode_client
from .prompt_templates import PromptTemplates


@dataclass
class Recommendation:
    """Single recommendation with traceable reasoning."""
    title: str
    steps: List[str]
    outcome: str
    citation: str
    confidence: float = 0.8
    reasoning_chain: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Recommendation':
        return cls(
            title=data.get("title", ""),
            steps=data.get("steps", []),
            outcome=data.get("outcome", ""),
            citation=data.get("citation", "Source: Derived from analysis"),
            confidence=data.get("confidence", 0.8),
            reasoning_chain=data.get("reasoning_chain", [])
        )


@dataclass
class RecommendationResponse:
    """Complete recommendation response with metadata."""
    summary: str
    recommendations: List[Recommendation]
    overall_confidence: float
    rule_id: Optional[str] = None
    rule_prompt: Optional[str] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    raw_llm_response: Optional[str] = None
    generation_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "overall_confidence": self.overall_confidence,
            "rule_id": self.rule_id,
            "rule_prompt": self.rule_prompt,
            "context_data": self.context_data,
            "generation_timestamp": self.generation_timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'RecommendationResponse':
        return cls(
            summary=data.get("summary", ""),
            recommendations=[
                Recommendation.from_dict(r) for r in data.get("recommendations", [])
            ],
            overall_confidence=data.get("overall_confidence", 0.8),
            rule_id=data.get("rule_id"),
            rule_prompt=data.get("rule_prompt"),
            context_data=data.get("context_data", {}),
            raw_llm_response=data.get("raw_llm_response"),
            generation_timestamp=data.get("generation_timestamp", "")
        )


class RecommendationGenerator:
    """
    LLM-powered recommendation generator with structured output.
    
    Features:
    - Citation-enforcing prompts
    - Structured JSON output parsing
    - Confidence scoring
    - Traceable reasoning chain
    - DPDP-compliant data minimization
    """

    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.model = model
        self.prompt_templates = PromptTemplates()

    def generate(
        self,
        rule_id: str,
        rule_prompt: str,
        context_data: Dict[str, Any],
        district_name: Optional[str] = None,
        template_type: str = "generic"
    ) -> RecommendationResponse:
        """
        Generate recommendations based on rule trigger and context.
        
        Args:
            rule_id: ID of the triggered rule
            rule_prompt: Rule's recommendation prompt template
            context_data: Data context for the recommendation
            district_name: Name of the district (for template formatting)
            template_type: Type of template to use
        
        Returns:
            RecommendationResponse with structured recommendations
        """
        from datetime import datetime
        
        # Format the prompt based on template type and rule
        if "pmay" in rule_id.lower():
            prompt = self.prompt_templates.format_pmay_recommendation(
                context_data, rule_id, rule_prompt, ""
            )
        elif "health" in rule_id.lower():
            prompt = self.prompt_templates.format_health_recommendation(
                context_data, rule_id, rule_prompt, ""
            )
        elif "agriculture" in rule_id.lower() or "credit" in rule_id.lower():
            prompt = self.prompt_templates.format_agriculture_recommendation(
                context_data, rule_id, rule_prompt, ""
            )
        else:
            context_summary = self._summarize_context(context_data, district_name)
            prompt = self.prompt_templates.format_generic_recommendation(
                rule_id,
                rule_id.replace("_", " ").title(),
                rule_prompt,
                context_data,
                context_summary
            )
        
        # Add citation requirements
        prompt += self.prompt_templates.get_citation_instruction()

        logger.info(f"Generating recommendations for rule: {rule_id}")
        
        try:
            response = opencode_client.request_with_retry(
                "chat",
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a policy analyst assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            raw_response = response.choices[0].message.content
            
            # Parse JSON response
            parsed = self._parse_json_response(raw_response)
            
            # Build response object
            recommendations = [
                Recommendation.from_dict(r) for r in parsed.get("recommendations", [])
            ]
            
            return RecommendationResponse(
                summary=parsed.get("summary", "No summary provided"),
                recommendations=recommendations,
                overall_confidence=parsed.get("overall_confidence", 0.8),
                rule_id=rule_id,
                rule_prompt=rule_prompt,
                context_data=self._minimize_data(context_data),
                raw_llm_response=raw_response,
                generation_timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return self._generate_fallback_response(rule_id, context_data)

    def _parse_json_response(self, raw_response: str) -> Dict[str, Any]:
        """Parse and validate JSON response from LLM."""
        try:
            # Try direct JSON parsing
            return json.loads(raw_response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Return default structure
            return {
                "summary": "Unable to parse LLM response",
                "recommendations": [],
                "overall_confidence": 0.0
            }

    def _summarize_context(self, context: Dict, district_name: Optional[str]) -> str:
        """Summarize context data for prompt."""
        parts = []
        if district_name:
            parts.append(f"District: {district_name}")
        
        for key, value in list(context.items())[:5]:
            readable_key = key.replace("_", " ")
            parts.append(f"- {readable_key}: {value}")
        
        return "\n".join(parts)

    def _minimize_data(self, context: Dict) -> Dict[str, Any]:
        """
        Minimize data according to DPDP principles.
        
        Only include fields relevant to the recommendation.
        """
        # List of relevant fields for policy recommendations
        relevant_fields = [
            "name", "district", "state", "population",
            "pmay_utilization_percent", "health_scheme_coverage_percent",
            "kcc_disbursement_percent", "target", "achieved",
            "utilization", "coverage", "disbursement"
        ]
        
        minimized = {}
        for key, value in context.items():
            if any(field in key.lower() for field in relevant_fields):
                minimized[key] = value
        
        return minimized

    def _generate_fallback_response(
        self,
        rule_id: str,
        context_data: Dict
    ) -> RecommendationResponse:
        """Generate a fallback response when LLM fails."""
        return RecommendationResponse(
            summary=f"Rule {rule_id} was triggered. Manual review recommended.",
            recommendations=[
                Recommendation(
                    title="Manual Review Required",
                    steps=[
                        "Review the triggered rule criteria",
                        "Examine district-level data",
                        "Consult with field officers"
                    ],
                    outcome="Improved understanding for decision-making",
                    citation="Source: System-generated due to LLM unavailable",
                    confidence=0.5
                )
            ],
            overall_confidence=0.5,
            rule_id=rule_id,
            context_data=self._minimize_data(context_data)
        )

    def generate_batch(
        self,
        triggers: List[Dict[str, Any]]
    ) -> List[RecommendationResponse]:
        """
        Generate recommendations for multiple rule triggers.
        
        Args:
            triggers: List of dicts with rule_id, rule_prompt, context_data
        
        Returns:
            List of RecommendationResponse objects
        """
        results = []
        for trigger in triggers:
            result = self.generate(
                rule_id=trigger.get("rule_id", "unknown"),
                rule_prompt=trigger.get("rule_prompt", ""),
                context_data=trigger.get("context_data", {}),
                district_name=trigger.get("district_name")
            )
            results.append(result)
        
        return results


# Global generator instance
_recommendation_generator: Optional[RecommendationGenerator] = None


def get_recommendation_generator() -> RecommendationGenerator:
    """Get the global recommendation generator instance."""
    global _recommendation_generator
    if _recommendation_generator is None:
        _recommendation_generator = RecommendationGenerator()
    return _recommendation_generator