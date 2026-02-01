# Setup Instructions

## Prerequisites

- Python 3.9 or higher
- [uv](https://github.com/astral-sh/uv) package manager

## Installation

### 1. Install uv (if not already installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with brew
brew install uv
```

### 2. Clone and Setup Project

```bash
cd attrecto-homework

# Install dependencies with uv (creates .venv automatically)
uv sync

# Copy environment template
cp .env.example .env
```

### 3. Configure Azure OpenAI

Edit `.env` with your Azure OpenAI credentials:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_API_VERSION=2024-02-15-preview
```

### 4. Verify Configuration

```bash
uv run python config.py
```

You should see:
```
✓ Configuration valid
  Endpoint: https://your-resource.openai.azure.com/
  Deployment: gpt-4
  Rate limits: 50 req/min, 50000 tokens/min
```

## Running the Analysis

```bash
# Run the portfolio analyzer
uv run python main.py

# Or use the configured script
uv run analyze
```

## Development

```bash
# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev pytest

# Remove a dependency
uv remove package-name

# Update dependencies
uv lock --upgrade
```

## Project Structure

```
attrecto-homework/
├── src/                     # Source code
│   ├── models.py           # Pydantic data models
│   ├── llm_gateway.py      # Rate-limited Azure OpenAI client
│   ├── ai_analyzer.py      # Core analysis engine
│   ├── email_parser.py     # Email file parser
│   ├── colleagues_parser.py # Team members parser
│   ├── database.py         # TinyDB wrapper
│   └── report_generator.py # Report generation
├── prompts/                 # AI prompts
├── data/                    # Email data files and Colleagues.txt
├── dashboard/              # Web dashboard
│   ├── app.py             # FastAPI application
│   ├── templates/         # HTML templates
│   └── static/            # CSS/JS assets
├── config.py               # Configuration
├── main.py                 # Entry point
├── pyproject.toml          # UV/Python project config
└── .env                    # Your secrets (git-ignored)
```

## Running the Dashboard

To view the portfolio health data in a web interface:

```bash
# Start the dashboard server
uv run python dashboard/app.py

# Or use the run script
./run_dashboard.sh
```

Then open your browser to http://localhost:8000
