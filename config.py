"""
Configuration management for Portfolio Health Report system.
Loads settings from environment variables.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")

# AI Model Parameters
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))

# Rate Limiting Configuration (from Azure limits)
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "50"))
RATE_LIMIT_TOKENS_PER_MINUTE = int(os.getenv("RATE_LIMIT_TOKENS_PER_MINUTE", "50000"))

# Issue Detection Thresholds
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
MIN_DAYS_FOR_UNRESOLVED = int(os.getenv("MIN_DAYS_FOR_UNRESOLVED", "7"))

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
DB_PATH = PROJECT_ROOT / "portfolio_data.json"

# Prompt File Paths
SYSTEM_PROMPT_PATH = PROMPTS_DIR / "system_prompt.txt"
USER_PROMPT_TEMPLATE_PATH = PROMPTS_DIR / "user_prompt_template.txt"
FEW_SHOT_EXAMPLES_PATH = PROMPTS_DIR / "few_shot_examples.json"


def validate_config():
    """Validate that required configuration is present."""
    errors = []

    if not AZURE_OPENAI_ENDPOINT:
        errors.append("AZURE_OPENAI_ENDPOINT is not set")

    if not AZURE_OPENAI_KEY:
        errors.append("AZURE_OPENAI_KEY is not set")

    if not AZURE_OPENAI_DEPLOYMENT:
        errors.append("AZURE_OPENAI_DEPLOYMENT is not set")

    if errors:
        error_msg = "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
        error_msg += "\n\nPlease set these in your .env file (see .env.example)"
        raise ValueError(error_msg)


if __name__ == "__main__":
    # Test configuration
    try:
        validate_config()
        print("✓ Configuration valid")
        print(f"  Endpoint: {AZURE_OPENAI_ENDPOINT}")
        print(f"  Deployment: {AZURE_OPENAI_DEPLOYMENT}")
        print(f"  Rate limits: {RATE_LIMIT_REQUESTS_PER_MINUTE} req/min, {RATE_LIMIT_TOKENS_PER_MINUTE} tokens/min")
    except ValueError as e:
        print(f"✗ {e}")
