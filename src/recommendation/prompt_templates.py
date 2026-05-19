# src/recommendation/prompt_templates.py
"""Prompt templates for recommendation generation with citation enforcement."""

from typing import Dict, List, Any, Optional
from string import Template


class PromptTemplates:
    """
    Template library for generating structured recommendations with citations.
    
    Implements citation-enforcing prompts following DPDP Act 2023 principles
    for data minimization and transparency.
    """

    # Base recommendation template
    BASE_TEMPLATE = Template("""
You are an expert policy analyst for the Government of India. Generate actionable recommendations based on the provided data.

CONTEXT:
$context

RULE TRIGGERED:
$rule_prompt

INSTRUCTIONS:
1. Provide exactly 3 actionable interventions
2. Each recommendation must include:
   - A clear action title
   - Specific implementation steps (2-3 sentences)
   - Expected outcome
   - Data source citation
3. Keep total response under 100 words
4. Use plain English, avoid jargon
5. Focus on practical, implementable solutions

OUTPUT FORMAT (JSON):
{
  "summary": "Brief overview of the situation",
  "recommendations": [
    {
      "title": "Action title",
      "steps": ["Step 1", "Step 2"],
      "outcome": "Expected result",
      "citation": "Source: [file/column] or 'Derived from analysis'",
      "confidence": 0.0-1.0
    }
  ],
  "overall_confidence": 0.0-1.0
}
""")

    # PMAY utilization improvement template
    PMAY_UTILIZATION_TEMPLATE = Template("""
You are a housing policy expert for the Government of India. Based on the data below, suggest interventions to improve PMAY (Pradhan Mantri Awas Yojana) fund utilization.

DISTRICT DATA:
$district_data

ANALYSIS:
- Current utilization: ${utilization}%
- Population: ${population:,}
- Target beneficiaries: ${target:,}
- Achieved: ${achieved:,}

RULE TRIGGERED: $rule_id
$rule_prompt

Generate exactly 3 recommendations that address:
1. Awareness and outreach
2. Documentation/process simplification
3. Monitoring and accountability

OUTPUT FORMAT (JSON) with citations:
{
  "summary": "Overview",
  "recommendations": [
    {
      "title": "...",
      "steps": ["...", "..."],
      "outcome": "...",
      "citation": "Source: [specific data reference]",
      "confidence": 0.0-1.0
    }
  ],
  "overall_confidence": 0.0-1.0
}
""")

    # Health scheme coverage template
    HEALTH_COVERAGE_TEMPLATE = Template("""
You are a public health policy expert for the Government of India. Suggest interventions to improve health scheme coverage in underserved areas.

DISTRICT DATA:
$district_data

ANALYSIS:
- Current coverage: ${coverage}%
- BPL population: ${bpl}% (high need indicator)
- Healthcare facilities: ${facilities}
- ASHA workers: ${asha_workers}

RULE TRIGGERED: $rule_id
$rule_prompt

Focus on:
1. Community health worker engagement
2. Mobile health units and outreach
3. Awareness and enrollment drives

OUTPUT FORMAT (JSON):
{
  "summary": "Overview",
  "recommendations": [...],
  "overall_confidence": 0.0-1.0
}
""")

    # Agricultural credit template
    AGRICULTURE_CREDIT_TEMPLATE = Template("""
You are an agricultural finance expert for the Government of India. Suggest ways to improve Kisan Credit Card (KCC) disbursement.

DISTRICT DATA:
$district_data

ANALYSIS:
- Current disbursement: ${disbursement}%
- Target: ${target}
- Agrarian population: ${agrarian}%
- Number of small farmers: ${small_farmers:,}

RULE TRIGGERED: $rule_id
$rule_prompt

Focus on:
1. Bank outreach to rural areas
2. Simplified documentation
3. Digital onboarding support

OUTPUT FORMAT (JSON):
{
  "summary": "Overview",
  "recommendations": [...],
  "overall_confidence": 0.0-1.0
}
""")

    # Generic intervention template
    GENERIC_INTERVENTION_TEMPLATE = Template("""
You are a policy analyst. Generate 3 actionable interventions based on the rule trigger.

RULE: $rule_id - $rule_name
$rule_prompt

DATA:
$context_data

OUTPUT JSON format:
{
  "summary": "Brief summary",
  "recommendations": [
    {
      "title": "Title",
      "steps": ["Step 1", "Step 2"],
      "outcome": "Expected outcome",
      "citation": "Data source reference",
      "confidence": 0.85
    }
  ],
  "overall_confidence": 0.85
}
""")

    @classmethod
    def get_template(cls, template_type: str) -> Template:
        """Get a template by type."""
        templates = {
            "base": cls.BASE_TEMPLATE,
            "pmay_utilization": cls.PMAY_UTILIZATION_TEMPLATE,
            "health_coverage": cls.HEALTH_COVERAGE_TEMPLATE,
            "agriculture_credit": cls.AGRICULTURE_CREDIT_TEMPLATE,
            "generic": cls.GENERIC_INTERVENTION_TEMPLATE,
        }
        return templates.get(template_type, cls.BASE_TEMPLATE)

    @classmethod
    def format_pmay_recommendation(
        cls,
        district_data: Dict,
        rule_id: str,
        rule_prompt: str,
        context: str
    ) -> str:
        """Format PMAY-specific recommendation prompt."""
        template = cls.get_template("pmay_utilization")
        return template.substitute(
            district_data=cls._format_district_data(district_data),
            utilization=district_data.get("pmay_utilization_percent", "N/A"),
            population=district_data.get("population", 0),
            target=district_data.get("pmay_target", 0),
            achieved=district_data.get("pmay_achieved", 0),
            rule_id=rule_id,
            rule_prompt=rule_prompt or "",
            context=context
        )

    @classmethod
    def format_health_recommendation(
        cls,
        district_data: Dict,
        rule_id: str,
        rule_prompt: str,
        context: str
    ) -> str:
        """Format health coverage recommendation prompt."""
        template = cls.get_template("health_coverage")
        return template.substitute(
            district_data=cls._format_district_data(district_data),
            coverage=district_data.get("health_scheme_coverage_percent", "N/A"),
            bpl=district_data.get("population_below_poverty_line", "N/A"),
            facilities=district_data.get("healthcare_facilities", "N/A"),
            asha_workers=district_data.get("asha_workers_deployed", "N/A"),
            rule_id=rule_id,
            rule_prompt=rule_prompt or "",
            context=context
        )

    @classmethod
    def format_agriculture_recommendation(
        cls,
        district_data: Dict,
        rule_id: str,
        rule_prompt: str,
        context: str
    ) -> str:
        """Format agriculture credit recommendation prompt."""
        template = cls.get_template("agriculture_credit")
        return template.substitute(
            district_data=cls._format_district_data(district_data),
            disbursement=district_data.get("kcc_disbursement_percent", "N/A"),
            target=district_data.get("kcc_target", "N/A"),
            agrarian=district_data.get("agrarian_percentage", "N/A"),
            small_farmers=district_data.get("small_marginal_farmers", 0),
            rule_id=rule_id,
            rule_prompt=rule_prompt or "",
            context=context
        )

    @classmethod
    def format_generic_recommendation(
        cls,
        rule_id: str,
        rule_name: str,
        rule_prompt: str,
        context_data: Dict,
        context_summary: str
    ) -> str:
        """Format generic recommendation prompt."""
        template = cls.get_template("generic")
        return template.substitute(
            rule_id=rule_id,
            rule_name=rule_name,
            rule_prompt=rule_prompt,
            context_data=cls._format_district_data(context_data),
            context=context_summary
        )

    @staticmethod
    def _format_district_data(data: Dict) -> str:
        """Format district data for prompt context."""
        lines = []
        for key, value in data.items():
            # Format key to be readable
            readable_key = key.replace("_", " ").title()
            lines.append(f"- {readable_key}: {value}")
        return "\n".join(lines)

    @classmethod
    def get_citation_instruction(cls) -> str:
        """Get citation enforcement instructions."""
        return """
CITATION REQUIREMENTS:
- Every recommendation MUST cite a data source
- Use format: "Source: [filename]/[column]" or "Derived from analysis"
- Do not make up statistics - only use data provided
- If data is insufficient, note it in the citation field
"""