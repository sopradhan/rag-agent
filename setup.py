"""
Setup script for RAG Agent System
Enables installation as a Python package
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="rag-agent-system",
    version="1.0.0",
    author="RAG Agent Team",
    description="LangChain-based RAG system with hierarchical RBAC, chain-of-thought reasoning, and multi-source ingestion",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/rag-agent-system",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.10",
    install_requires=[
        "langchain>=0.3.0",
        "langchain-core>=0.3.0",
        "langchain-community>=0.3.0",
        "langgraph>=0.2.0",
        "ollama>=0.1.15",
        "chromadb>=0.4.0",
        "sentence-transformers>=2.2.2",
        "PyPDF2>=3.0.0",
        "pdfplumber>=0.10.0",
        "python-docx>=1.0.0",
        "pandas>=2.0.0",
        "pyyaml>=6.0.1",
        "python-dotenv>=1.0.0",
        "click>=8.1.7",
        "streamlit>=1.29.0",
        "tiktoken>=0.5.0",
    ],
    entry_points={
        "console_scripts": [
            "rag-agent-init=scripts.initialize:main",
            "rag-agent-ingest=scripts.ingest:main",
            "rag-agent-query=scripts.query:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
