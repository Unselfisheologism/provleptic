.PHONY: dev test run deploy-streamlit

setup:
    pip install -r requirements.txt --break-system-packages
    python -m spacy download en_core_web_sm --break-system-packages

test:
    pytest tests/ -v --cov=src

run:
    streamlit run src/api/main.py

deploy-streamlit:
    @echo "Push to GitHub, then deploy at https://streamlit.io/cloud"
