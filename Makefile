.PHONY: dev test run deploy-streamlit lint

setup:
	pip install -r requirements.txt --break-system-packages
	python -m spacy download en_core_web_sm --break-system-packages

test:
	pytest tests/ -v --cov=src --cov-report=html

test-rules:
	pytest tests/test_rules.py -v

test-audit:
	pytest tests/test_audit.py -v

test-recommendation:
	pytest tests/test_recommendation.py -v

test-compliance:
	pytest tests/test_compliance.py -v

test-auth:
	pytest tests/test_auth.py -v

run:
	streamlit run src/api/main.py

run-headless:
	python -c "
from src.rules.engine import RuleEngine
from src.audit.logger import AuditLogger
from src.recommendation.generator import RecommendationGenerator

# Quick smoke test
engine = RuleEngine('src/rules/sample_rules')
logger = AuditLogger()
gen = RecommendationGenerator()

print('Rule Engine:', 'OK' if len(engine.rules) >= 3 else 'WARNING: No rules loaded')
print('Audit Logger:', 'OK' if logger.count_entries() >= 0 else 'ERROR')
print('Recommendation Generator:', 'OK' if gen else 'ERROR')
"

lint:
	@echo "Running lint checks..."
	@python -m py_compile src/rules/*.py src/auth/*.py src/audit/*.py src/recommendation/*.py src/compliance/*.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage

deploy-streamlit:
	@echo "Push to GitHub, then deploy at https://streamlit.io/cloud"
	@echo "For HF Spaces with GPU: https://huggingface.co/new-space"