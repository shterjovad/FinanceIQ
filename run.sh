#!/bin/bash
# FinanceIQ startup script

# Set PYTHONPATH to project root
export PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd):$PYTHONPATH"

# Run Streamlit app
uv run streamlit run src/ui/app.py
