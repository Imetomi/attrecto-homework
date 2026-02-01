# Portfolio Health Dashboard

AI-powered email analysis system that extracts project issues and risks from engineering communications.

## Dashboard Preview

![Dashboard Overview](docs/images/dashboard.png)
*Director-level view with issue prioritization and analytics*

![Open Issues](docs/images/open-problems.png)
*Prioritized list of open issues requiring attention*

![Issue Details](docs/images/issue.png)
*Detailed issue view with evidence and context*

## Quick Start

### 1. Setup

```bash
# Install dependencies
uv sync

# Configure Azure OpenAI credentials
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
```

### 2. Run Analysis

```bash
# Analyze emails and generate report
uv run python main.py
```

This creates:
- `data/portfolio_data.json` - Database of issues
- `data/output/portfolio_health_report.json` - JSON report

### 3. Launch Dashboard

```bash
# Start the web dashboard
./run_dashboard.sh
```

Open http://localhost:8000 in your browser.

---

## AI Usage in This Project

This project demonstrates extensive use of AI for both **development** and **data analysis**:

### 1. Development with Claude & Cursor

**Claude (Sonnet 4.5)** and **Cursor IDE** were used throughout the entire development lifecycle:

- **System Design & Architecture:** The core innovation of sequential email processing with thread summarization was designed collaboratively with AI. See `docs/ARCHITECTURE.md` for the full architectural decisions.

- **Code Implementation:** All source code in `src/` was developed with AI assistance, focusing on clean architecture, proper error handling, and scalability patterns.

- **Prompt Engineering:** The system prompts (`prompts/system_prompt.txt`) were iteratively refined with AI to:
  - Use few-shot examples for better output quality
  - Define strict evidence requirements to prevent hallucination
  - Implement structured JSON output with Pydantic validation

- **Token Optimization Strategy:** AI helped design the **thread summarization approach** that reduces token usage by 73%:
  - Instead of sending all previous emails (O(n²) complexity)
  - Each email is processed with only a summary of previous context (O(n) complexity)
  - Average request: ~1,200 tokens instead of ~5,000+ tokens for long threads
  - **This enables token caching** and dramatically reduces API costs

See `docs/CHANGES.md` for the evolution of the architecture and `docs/images/` for system diagrams.

### 2. Data Analysis with Azure OpenAI

**Azure OpenAI (GPT-4)** powers the core email analysis engine:

- **Model:** GPT-4 (via Azure OpenAI Service)
- **Average Request Size:** ~1,200 tokens (thanks to summarization)
- **Temperature:** 0.2 (for deterministic, fact-based extraction)
- **Processing:** 83 emails analyzed in ~4.5 minutes
- **Total Cost:** ~$4-5 for the entire dataset

**Key Techniques:**
- **Sequential Processing:** Emails analyzed one-by-one in chronological order
- **Context Accumulation:** Thread summary + open issues passed to each request
- **Resolution Tracking:** AI detects when previously flagged issues are resolved
- **Confidence Scoring:** Every detection includes 0-1 confidence score for filtering

This architecture demonstrates how **thoughtful prompt design** and **token optimization** can make AI-powered systems both effective and cost-efficient.

---

**Documentation:** See `docs/` folder for detailed architecture and setup guides.
