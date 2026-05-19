# tests/test_rules.py
"""Tests for the rule engine and DSL."""

import pytest
import os
import tempfile
import yaml
from pathlib import Path

from src.rules.engine import RuleEngine, EvaluatedRule
from src.rules.dsl import ConditionParser, ActionExecutor


class TestConditionParser:
    """Tests for the condition parser."""

    def test_simple_less_than(self):
        parser = ConditionParser()
        context = {"District": {"population": 5000000}}
        
        condition = {
            "entity": "District",
            "field": "population",
            "operator": ">",
            "value": 1000000
        }
        
        assert parser.evaluate(condition, context) is True
        
        condition2 = {
            "entity": "District",
            "field": "population",
            "operator": ">",
            "value": 10000000
        }
        assert parser.evaluate(condition2, context) is False

    def test_all_condition(self):
        parser = ConditionParser()
        context = {
            "District": {
                "pmay_utilization_percent": 45,
                "population": 6000000
            }
        }
        
        condition = {
            "all": [
                {"entity": "District", "field": "pmay_utilization_percent", "operator": "<", "value": 50},
                {"entity": "District", "field": "population", "operator": ">", "value": 1000000}
            ]
        }
        
        assert parser.evaluate(condition, context) is True

    def test_any_condition(self):
        parser = ConditionParser()
        context = {"District": {"pmay_utilization_percent": 45}}
        
        condition = {
            "any": [
                {"entity": "District", "field": "pmay_utilization_percent", "operator": "<", "value": 50},
                {"entity": "District", "field": "pmay_utilization_percent", "operator": ">", "value": 90}
            ]
        }
        
        assert parser.evaluate(condition, context) is True

    def test_none_condition(self):
        parser = ConditionParser()
        context = {"District": {"pmay_utilization_percent": 45}}
        
        condition = {
            "none": [
                {"entity": "District", "field": "pmay_utilization_percent", "operator": ">", "value": 90}
            ]
        }
        
        assert parser.evaluate(condition, context) is True


class TestActionExecutor:
    """Tests for the action executor."""

    def test_flag_for_review(self):
        executor = ActionExecutor()
        action = {
            "type": "flag_for_review",
            "priority": "high",
            "notify_roles": ["policymaker", "field_officer"]
        }
        context = {"entity_type": "District", "identifier": "Nashik"}
        
        result = executor.execute(action, context)
        
        assert result["action"] == "flag_for_review"
        assert result["flagged"] is True
        assert result["priority"] == "high"
        assert "policymaker" in result["notify_roles"]


class TestRuleEngine:
    """Tests for the rule engine."""

    def test_load_yaml_rules(self):
        """Test loading rules from YAML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rule = {
                "rule_id": "test_rule",
                "name": "Test Rule",
                "description": "A test rule",
                "condition": {
                    "entity": "District",
                    "field": "pmay_utilization_percent",
                    "operator": "<",
                    "value": 50
                },
                "action": {
                    "type": "flag_for_review",
                    "priority": "high"
                }
            }
            
            rule_file = Path(tmpdir) / "test_rule.yaml"
            with open(rule_file, 'w') as f:
                yaml.dump(rule, f)
            
            engine = RuleEngine(tmpdir)
            
            assert len(engine.rules) == 1
            assert engine.rules[0]["rule_id"] == "test_rule"

    def test_evaluate_triggered(self):
        """Test rule evaluation when condition is met."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rule = {
                "rule_id": "pmay_review",
                "name": "PMAY Review",
                "description": "Flag low utilization",
                "condition": {
                    "all": [
                        {"entity": "District", "field": "pmay_utilization_percent", "operator": "<", "value": 50},
                        {"entity": "District", "field": "population", "operator": ">", "value": 1000000}
                    ]
                },
                "action": {
                    "type": "flag_for_review",
                    "priority": "high"
                }
            }
            
            rule_file = Path(tmpdir) / "pmay.yaml"
            with open(rule_file, 'w') as f:
                yaml.dump(rule, f)
            
            engine = RuleEngine(tmpdir)
            
            context = {
                "District": {
                    "pmay_utilization_percent": 45,
                    "population": 6000000
                }
            }
            
            results = engine.evaluate(context)
            
            assert len(results) == 1
            assert results[0].triggered is True
            assert results[0].rule_id == "pmay_review"

    def test_evaluate_not_triggered(self):
        """Test rule evaluation when condition is not met."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rule = {
                "rule_id": "pmay_review",
                "name": "PMAY Review",
                "condition": {
                    "entity": "District",
                    "field": "pmay_utilization_percent",
                    "operator": "<",
                    "value": 50
                },
                "action": {
                    "type": "flag_for_review"
                }
            }
            
            rule_file = Path(tmpdir) / "pmay.yaml"
            with open(rule_file, 'w') as f:
                yaml.dump(rule, f)
            
            engine = RuleEngine(tmpdir)
            
            context = {
                "District": {
                    "pmay_utilization_percent": 75
                }
            }
            
            results = engine.evaluate(context)
            
            assert len(results) == 1
            assert results[0].triggered is False

    def test_add_rule_programmatically(self):
        """Test adding rules programmatically."""
        engine = RuleEngine()
        
        rule = {
            "rule_id": "custom_rule",
            "name": "Custom Rule",
            "condition": {
                "entity": "District",
                "field": "population",
                "operator": ">",
                "value": 1000000
            },
            "action": {
                "type": "notify"
            }
        }
        
        engine.add_rule(rule)
        
        assert len(engine.rules) == 1
        assert engine.rules[0]["rule_id"] == "custom_rule"