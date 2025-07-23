# arXiv Researcher Agent

A simple LangGraph agent that downloads and analyzes arXiv research papers and generates a comprehensive summary report

## Overview

This agent extracts arXiv paper URLs from user input, downloads the full text content, and generates a report with three types of analysis:
- High-level summary
- Detailed technical summary  
- Real-world applications of the papers content

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

## Usage

The agent accepts arXiv URLs or paper IDs and returns a comprehensive research summary.

## Architecture

- `agent.py` - Main workflow orchestration
- `agents/` - Specialized summary agents
- `utils.py` - PDF download and text extraction
- `shared.py` - State definitions and shared model
- `prompts/` - Agent prompts and templates

## Requirements

- Python 3.8+
- OpenAI API key
- LangGraph and LangChain dependencies