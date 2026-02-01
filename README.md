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

**Documentation:** See `docs/` folder for detailed architecture and setup guides.
