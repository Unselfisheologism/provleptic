# src/rules/engine.py
"""Rule engine for evaluating policy rules against context data."""

import yaml
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from loguru import logger

from .dsl import ConditionParser, ActionExecutor, RuleResult


@dataclass
class EvaluatedRule:
    """A rule that has been evaluated against context."""
    rule_id: str
    rule_name: str
    description: str
    triggered: bool
    condition_met: bool
    action_result: Dict[str, Any]
    priority: str
    notify_roles: List[str]
    recommendation_prompt: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RuleEngine:
    """
    YAML-based rule engine for policy decision support.
    
    Loads rules from YAML files and evaluates them against context data.
    Supports complex conditions with AND/OR logic and various operators.
    """

    def __init__(self, rules_dir: str = "rules/"):
        self.rules_dir = Path(rules_dir)
        self.rules: List[Dict] = []
        self.condition_parser = ConditionParser()
        self.action_executor = ActionExecutor()
        self._load_rules()

    def _load_rules(self):
        """Load all YAML rule files from the rules directory."""
        if not self.rules_dir.exists():
            logger.warning(f"Rules directory not found: {self.rules_dir}")
            return

        for rule_file in self.rules_dir.glob("*.yaml"):
            try:
                with open(rule_file, 'r') as f:
                    rule = yaml.safe_load(f)
                    self.rules.append(rule)
                    logger.info(f"Loaded rule: {rule.get('rule_id', rule_file.stem)}")
            except Exception as e:
                logger.error(f"Error loading rule file {rule_file}: {e}")

    def reload_rules(self):
        """Reload all rules from disk."""
        self.rules = []
        self._load_rules()

    def add_rule(self, rule: Dict):
        """Add a rule programmatically."""
        self.rules.append(rule)

    def evaluate(self, context: Dict) -> List[EvaluatedRule]:
        """
        Evaluate all rules against the given context.
        
        Args:
            context: Dictionary containing entity data, e.g.,
                {
                    "District": {"name": "Nashik", "pmay_utilization_percent": 45, "population": 6000000},
                    "entity_type": "District",
                    "identifier": "Nashik"
                }
        
        Returns:
            List of EvaluatedRule objects, both triggered and non-triggered
        """
        results = []
        
        for rule in self.rules:
            evaluated = self._evaluate_single_rule(rule, context)
            results.append(evaluated)
        
        return results

    def evaluate_and_get_triggered(self, context: Dict) -> List[EvaluatedRule]:
        """Evaluate rules and return only triggered ones."""
        return [r for r in self.evaluate(context) if r.triggered]

    def _evaluate_single_rule(self, rule: Dict, context: Dict) -> EvaluatedRule:
        """Evaluate a single rule against context."""
        rule_id = rule.get("rule_id", "unknown")
        rule_name = rule.get("name", rule_id)
        description = rule.get("description", "")
        
        try:
            # Check condition
            condition = rule.get("condition", {})
            condition_met = self.condition_parser.evaluate(condition, context)
            
            # Execute action if triggered
            if condition_met:
                action = rule.get("action", {})
                action_result = self.action_executor.execute(action, context)
            else:
                action_result = {"triggered": False, "action": "none"}
            
            return EvaluatedRule(
                rule_id=rule_id,
                rule_name=rule_name,
                description=description,
                triggered=condition_met,
                condition_met=condition_met,
                action_result=action_result,
                priority=rule.get("action", {}).get("priority", "medium"),
                notify_roles=rule.get("action", {}).get("notify_roles", []),
                recommendation_prompt=rule.get("action", {}).get("recommendation_prompt"),
                metadata={
                    "rule_hash": self._compute_rule_hash(rule),
                    "condition": condition,
                    "action": rule.get("action", {}),
                }
            )
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule_id}: {e}")
            return EvaluatedRule(
                rule_id=rule_id,
                rule_name=rule_name,
                description=description,
                triggered=False,
                condition_met=False,
                action_result={"error": str(e)},
                priority="medium",
                notify_roles=[],
            )

    def _compute_rule_hash(self, rule: Dict) -> str:
        """Compute SHA-256 hash of a rule for integrity verification."""
        rule_str = yaml.dump(rule, sort_keys=True)
        return hashlib.sha256(rule_str.encode()).hexdigest()

    def get_rule_by_id(self, rule_id: str) -> Optional[Dict]:
        """Get a rule by its ID."""
        for rule in self.rules:
            if rule.get("rule_id") == rule_id:
                return rule
        return None

    def list_rules(self) -> List[Dict]:
        """List all loaded rules with their IDs and descriptions."""
        return [
            {
                "rule_id": r.get("rule_id"),
                "name": r.get("name"),
                "description": r.get("description"),
                "priority": r.get("action", {}).get("priority"),
            }
            for r in self.rules
        ]