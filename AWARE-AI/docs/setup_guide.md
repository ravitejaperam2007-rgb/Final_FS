# Setup Guide

## Prerequisites

- Python 3.10+
- pip / pipenv / poetry

## Installation

```bash
git clone https://github.com/your-org/AWARE-AI.git
cd AWARE-AI
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in your API keys.

## Running

```bash
streamlit run app/streamlit_app.py
```

## Testing

```bash
pytest tests/ -v
```
