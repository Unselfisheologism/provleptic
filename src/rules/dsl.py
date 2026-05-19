# src/rules/dsl.py
"""Domain Specific Language parsers for rule conditions and actions."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import operator

# Operator mapping
OPERATORS = {
    "<": operator.lt,
    ">": operator.gt,
    "<=": operator.le,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
    "in": lambda a, b: a in b,
    "not in": lambda a, b: a not in b,
    "contains": lambda a, b: b in a,
    "startswith": lambda a, b: str(a).startswith(str(b)),
    "endswith": lambda a, b: str(a).endswith(str(b)),
}


@dataclass
class RuleResult:
    """Result of rule evaluation."""
    rule_id: str
    triggered: bool
    action_type: str
    metadata: Dict[str, Any]
    priority: str
    notify_roles: List[str]
    recommendation_prompt: Optional[str] = None


class ConditionParser:
    """Parses and evaluates YAML condition expressions."""

    def __init__(self):
        self.operators = OPERATORS

    def evaluate(self, condition: Dict, context: Dict) -> bool:
        """
        Evaluate a condition against the context.
        
        Supports:
        - {"all": [conditions]} - all must be true
        - {"any": [conditions]} - at least one must be true
        - {"none": [conditions]} - none must be true
        - {"entity": "X", "field": "Y", "operator": "op", "value": Z} - field comparison
        """
        if "all" in condition:
            return all(self.evaluate(c, context) for c in condition["all"])
        
        if "any" in condition:
            return any(self.evaluate(c, context) for c in condition["any"])
        
        if "none" in condition:
            return not any(self.evaluate(c, context) for c in condition["none"])
        
        if "entity" in condition:
            return self._evaluate_field_comparison(condition, context)
        
        return False

    def _evaluate_field_comparison(self, cond: Dict, context: Dict) -> bool:
        """Evaluate a single field comparison condition."""
        entity_type = cond.get("entity")
        field = cond.get("field")
        op_str = cond.get("operator")
        expected_value = cond.get("value")

        # Get the actual value from context
        # Handle nested paths like "district.pmay_utilization_percent"
        actual_value = self._get_nested_value(context, entity_type, field)

        if actual_value is None:
            return False

        if op_str not in self.operators:
            raise ValueError(f"Unsupported operator: {op_str}")

        op_func = self.operators[op_str]
        return op_func(actual_value, expected_value)

    def _get_nested_value(self, context: Dict, entity_type: str, field: str) -> Any:
        """Get a nested value from context using entity type and field path."""
        # Try to find the entity in context
        # Context might have entities as {"District": {...}} or direct fields
        entity_data = context.get(entity_type, context)
        
        if isinstance(entity_data, dict):
            # Handle dot notation for nested fields
            if "." in field:
                parts = field.split(".")
                value = entity_data
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        return None
                return value
            return entity_data.get(field)
        
        return None


class ActionExecutor:
    """Executes actions triggered by rules."""

    def __init__(self):
        self.handlers = {
            "flag_for_review": self._flag_for_review,
            "notify": self._notify,
            "generate_recommendation": self._generate_recommendation,
            "export_report": self._export_report,
            "escalate": self._escalate,
        }

    def execute(self, action: Dict, context: Dict, rule_result: Optional[RuleResult] = None) -> Dict:
        """Execute an action and return the result."""
        action_type = action.get("type", "flag_for_review")
        handler = self.handlers.get(action_type, self._default_handler)
        return handler(action, context, rule_result)

    def _flag_for_review(self, action: Dict, context: Dict, rule_result: Optional[RuleResult] = None) -> Dict:
        """Flag an entity for review."""
        return {
            "action": "flag_for_review",
            "flagged": True,
            "priority": action.get("priority", "medium"),
            "reason": f"Rule triggered: {rule_result.rule_id if rule_result else 'unknown'}",
            "context_summary": {
                "entity": context.get("entity_type", "unknown"),
                "identifier": context.get("identifier", "unknown"),
            },
            "notify_roles": action.get("notify_roles", []),
        }

    def _notify(self, action: Dict, context: Dict, rule_result: Optional[RuleResult] = None) -> Dict:
        """Send a notification."""
        return {
            "action": "notify",
            "notification_sent": True,
            "channels": action.get("channels", ["in_app"]),
            "message": action.get("message", "Rule triggered"),
            "roles": action.get("notify_roles", []),
        }

    def _generate_recommendation(self, action: Dict, context: Dict, rule_result: Optional[RuleResult] = None) -> Dict:
        """Mark for recommendation generation."""
        return {
            "action": "generate_recommendation",
            "requires_llm": True,
            "prompt_template": action.get("recommendation_prompt"),
            "context": context,
        }

    def _export_report(self, action: Dict, context: Dict, rule_result: Optional[RuleResult] = None) -> Dict:
        """Generate an export report."""
        return {
            "action": "export_report",
            "format": action.get("format", "csv"),
            "includes": action.get("includes", ["summary", "details"]),
        }

    def _escalate(self, action: Dict, context: Dict, rule_result: Optional[RuleResult] = None) -> Dict:
        """Escalate to higher authority."""
        return {
            "action": "escalate",
            "escalation_level": action.get("escalation_level", 1),
            "reason": action.get("reason", "Rule escalation"),
        }

    def _default_handler(self, action: Dict, context: Dict, rule_result: Optional[RuleResult] = None) -> Dict:
        """Default handler for unknown actions."""
        return {
            "action": action.get("type", "unknown"),
            "success": True,
            "message": f"Executed action: {action.get('type')}",
        }