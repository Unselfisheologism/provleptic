.PHONY: dev test run deploy-streamlit

dev:
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

test:
	. venv/bin/activate && pytest tests/ -v --cov=src

run:
	. venv/bin/activate && streamlit run src/api/main.py

deploy-streamlit:
	@echo "Push to GitHub, then deploy at https://streamlit.io/cloud"
