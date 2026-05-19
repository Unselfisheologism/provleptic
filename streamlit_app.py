"""
Streamlit app entry point for cloud deployment.

This file serves as the entry point for Streamlit Cloud deployment.
Streamlit Cloud looks for a file named 'streamlit_app.py' in the repository root.

The actual application logic is in src/api/main.py.
"""
from src.api.main import *

if __name__ == "__main__":
    # This block is typically not needed for Streamlit Cloud
    # as Streamlit handles execution automatically.
    # Included for local testing with: streamlit run streamlit_app.py
    pass