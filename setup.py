"""
Stock Market Sentiment Analyzer — setup.py
Provides `pip install -e .` support and package metadata.
"""
from setuptools import setup, find_packages

setup(
    name="stock-sentiment-analyzer",
    version="1.0.0",
    description="Real-time stock market sentiment analysis with FinBERT and GPT-4o-mini",
    author="Vamsi Kishore",
    packages=find_packages(where="backend"),
    package_dir={"": "backend"},
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.30.6",
        "sqlalchemy>=2.0.35",
        "asyncpg>=0.29.0",
        "pydantic>=2.9.2",
        "pydantic-settings>=2.5.2",
        "httpx>=0.27.2",
        "yfinance>=0.2.44",
        "transformers>=4.44.2",
        "torch>=2.4.1",
        "openai>=1.47.0",
        "apscheduler>=3.10.4",
        "python-dotenv>=1.0.1",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0",
            "pytest-asyncio>=0.23",
            "httpx>=0.27.2",
        ]
    },
)
