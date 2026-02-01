# Portfolio Health Report - Implementation Plan

## Project Overview
Build an AI-powered system that analyzes project email threads to generate a Portfolio Health Report for a Director of Engineering, identifying unresolved action items, emerging risks, and blockers.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Ingestion Layer                    │
│  - Email File Parser                                        │
│  - Thread Reconstruction                                    │
│  - Metadata Extraction (project, participants, dates)       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   AI Analytical Engine                      │
│  - Sequential Email Processing                              │
│  - Thread Context Accumulation                              │
│  - Azure OpenAI GPT-4 Integration                           │
│  - Issue Detection & Resolution Tracking                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│               Prioritization & Aggregation                  │
│  - Priority Score Calculation                               │
│  - Issue Lifecycle Management (Open/Resolved)               │
│  - Evidence Validation                                      │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Report Generation                        │
│  - JSON Report Output                                       │
│  - Terminal Visualization (colored)                         │
│  - Summary Statistics                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Project Setup & Structure
**Goal**: Establish project foundation

**Tasks**:
1. ✅ Create `.gitignore` (secrets, Python artifacts)
2. Create project directory structure:
   ```
   attrecto-homework/
   ├── data/                    # Email .txt files
   ├── docs/                    # Documentation
   ├── prompts/                 # AI prompts
   │   ├── system_prompt.txt
   │   ├── user_prompt_template.txt
   │   ├── few_shot_examples.json
   │   └── output_schema.json
   ├── src/                     # Source code
   │   ├── __init__.py
   │   ├── email_parser.py      # Parse email files
   │   ├── ai_analyzer.py       # Azure OpenAI integration
   │   ├── database.py          # TinyDB wrapper with Pydantic validation
   │   ├── report_generator.py  # Report creation
   │   └── models.py            # Pydantic data models
   ├── config.py                # Configuration
   ├── main.py                  # Entry point
   ├── requirements.txt         # Dependencies
   ├── .env.example             # Example secrets file
   ├── README.md                # AI model justifications
   └── Blueprint.md             # Architecture document
   ```
3. Create `requirements.txt` with dependencies
4. Create `.env.example` for Azure credentials

**Deliverables**:
- Complete directory structure
- Dependency management setup

---

### Phase 2: Email Parsing & Data Extraction
**Goal**: Parse email .txt files into structured data

**Components**:

#### 2.1 Data Models (`src/models.py`)
**Using Pydantic for Schema Validation**

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum

class IssueType(str, Enum):
    UNRESOLVED_ACTION = "UNRESOLVED_ACTION"
    EMERGING_RISK = "EMERGING_RISK"

class IssueStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    MONITORING = "MONITORING"

class Email(BaseModel):
    from_email: str
    from_name: str
    to_emails: List[str]
    cc_emails: List[str] = []
    date: datetime
    subject: str
    body: str

    @validator('from_email', 'to_emails')
    def validate_email(cls, v):
        # Basic email validation
        if isinstance(v, list):
            return [e for e in v if '@' in e]
        return v if '@' in v else f"{v}@unknown.com"

class EmailThread(BaseModel):
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str
    project_name: str
    participants: List[str]
    emails: List[Email]

class Issue(BaseModel):
    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    issue_type: IssueType
    status: IssueStatus = IssueStatus.OPEN
    severity: int = Field(ge=1, le=10)  # 1-10 validation
    title: str = Field(min_length=5, max_length=200)
    description: str
    evidence_quote: str = Field(min_length=10)
    email_date: datetime
    email_author: str
    confidence: float = Field(ge=0.0, le=1.0)  # 0.0-1.0 validation
    resolution_evidence: Optional[str] = None
    resolution_date: Optional[datetime] = None
    days_outstanding: int = 0
    priority_score: float = 0.0

    @validator('evidence_quote')
    def validate_evidence(cls, v):
        if len(v) < 10:
            raise ValueError("Evidence quote must be at least 10 characters")
        return v

class AIAnalysisResponse(BaseModel):
    """Schema for AI response validation"""
    new_issues: List[dict]  # Will be converted to Issue objects
    resolved_issues: List[dict]
    thread_summary: dict = Field(default_factory=dict)

    class Config:
        extra = 'forbid'  # Reject any extra fields from AI
```

**Benefits of Pydantic**:
- Automatic validation of AI responses
- Type safety throughout the codebase
- Easy serialization to/from JSON (for TinyDB)
- Clear error messages when validation fails
- Prevents hallucination by rejecting invalid outputs

#### 2.2 Email Parser (`src/email_parser.py`)
**Functions**:
- `parse_email_file(filepath: str) -> List[Email]`
  - Split file by "From:" headers
  - Parse each email section
  - Extract: sender, recipients, date, subject, body

- `extract_project_name(emails: List[Email]) -> str`
  - Parse from subject line (e.g., "Project Phoenix - ...")
  - Fallback to filename if not in subject

- `extract_participants(emails: List[Email]) -> List[str]`
  - Collect unique email addresses from all From/To/Cc fields
  - Extract names from Colleagues.txt mapping

- `create_thread(emails: List[Email]) -> EmailThread`
  - Group emails by subject/thread
  - Sort by date chronologically
  - Generate unique thread_id

**Deliverables**:
- Fully functional email parser
- Validated against all 18 sample emails
- Unit tests (optional for PoC)

---

### Phase 3: Prompt Engineering
**Goal**: Design prompts that minimize hallucination and extract accurate issues

#### 3.1 System Prompt (`prompts/system_prompt.txt`)
```
Role: You are a FACT-EXTRACTION system for engineering project analysis.

Objective: Identify explicit issues requiring director-level attention from email threads.

Rules:
1. ONLY flag issues with explicit evidence in the email text
2. NEVER infer or assume problems not directly mentioned
3. ALWAYS provide exact quotes as evidence
4. Mark issues as RESOLVED only if resolution is explicitly stated
5. Assign confidence scores honestly (0.0-1.0)
6. Focus on: unanswered questions, blockers, risks, scope changes, delays

Output Format: Valid JSON matching the provided schema

Temperature: 0.2 (prioritize accuracy over creativity)
```

#### 3.2 User Prompt Template (`prompts/user_prompt_template.txt`)
```
Thread Context:
Project: {project_name}
Subject: {subject}
Total Emails in Thread: {total_emails}

Previously Identified Issues:
{previous_issues_summary}

Current Email to Analyze (Email #{email_number}):
---
From: {from_name} <{from_email}>
Date: {date}
To: {to_emails}

{email_body}
---

Task:
1. Identify any NEW issues in this email
2. Check if any PREVIOUS issues are now RESOLVED based on this email
3. Provide exact quotes as evidence
4. Assign confidence scores

Constraints:
- Only flag issues that would concern a Director of Engineering
- Ignore: casual conversations, off-topic messages, already-resolved items
- Focus on: unanswered questions (>7 days), blockers, risks, budget/timeline impacts
```

#### 3.3 Few-Shot Examples (`prompts/few_shot_examples.json`)
**Example 1**: Unresolved question
**Example 2**: Emerging risk (scope not in estimate)
**Example 3**: Issue raised and resolved (should NOT flag)

#### 3.4 Output Schema (`prompts/output_schema.json`)
**Using Pydantic for Schema Validation**

```json
{
  "new_issues": [
    {
      "issue_type": "UNRESOLVED_ACTION | EMERGING_RISK",
      "severity": 1-10,
      "title": "brief title",
      "description": "detailed description",
      "evidence_quote": "exact quote from email",
      "confidence": 0.0-1.0
    }
  ],
  "resolved_issues": [
    {
      "issue_id": "from previous_issues",
      "resolution_evidence": "exact quote showing resolution",
      "confidence": 0.0-1.0
    }
  ],
  "thread_summary": {
    "key_points": ["summary point 1", "summary point 2"],
    "participants_active": ["name1", "name2"],
    "topics_discussed": ["topic1", "topic2"]
  }
}
```

**Note**: The `thread_summary` is crucial for building context for subsequent emails in the thread. Each AI response contributes to the cumulative understanding.

**Deliverables**:
- 4 prompt files
- Tested with manual GPT-4 calls
- Validated output quality

---

### Phase 4: Azure OpenAI Integration
**Goal**: Connect to Azure OpenAI and process emails sequentially

#### 4.1 Configuration (`config.py`)
```python
import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")  # gpt-4
AZURE_API_VERSION = "2024-02-15-preview"
TEMPERATURE = 0.2
MAX_TOKENS = 2000
```

#### 4.2 AI Analyzer (`src/ai_analyzer.py`)
**Main Class**: `ThreadAnalyzer`

**Methods**:
- `__init__(azure_config)`
  - Initialize Azure OpenAI client
  - Load prompts from files

- `analyze_thread(thread: EmailThread) -> List[Issue]`
  - Main orchestration method
  - Process emails sequentially
  - Return all detected issues

- `_analyze_single_email(email: Email, previous_issues: List[Issue], thread_summary: str) -> dict`
  - Build prompt with context (previous issues + thread summary)
  - Call Azure OpenAI API
  - Parse JSON response using Pydantic validation
  - Validate evidence quotes exist in email
  - Return: new_issues, resolved_issues, updated_thread_summary

- `_build_previous_issues_summary(issues: List[Issue]) -> str`
  - Format open issues for context
  - Include: issue_id, title, date, status

- `_build_thread_context(thread_summary: str, previous_issues: List[Issue]) -> str`
  - Combine thread summary with open issues
  - Creates grounding context for AI

- `_call_azure_openai(prompt: str) -> dict`
  - Make API request with retry logic
  - Handle rate limits
  - Validate JSON response

- `_validate_evidence(evidence_quote: str, email_body: str) -> bool`
  - Verify quote exists in email (anti-hallucination)
  - Fuzzy matching for minor differences

**Anti-Hallucination Measures**:
1. Grounding with previous issues summary
2. Evidence quote validation
3. Low temperature (0.2)
4. Confidence scoring
5. Few-shot examples
6. Strict output schema

**Deliverables**:
- Working Azure OpenAI integration
- Sequential email processing with thread summary accumulation
- Issue tracking across thread
- Pydantic models for response validation

---

#### 4.3 Data Persistence (`src/database.py`)
**Goal**: Store analysis results in TinyDB for querying and persistence

**Class**: `PortfolioDB`

**Methods**:
- `__init__(db_path: str = "portfolio_data.json")`
  - Initialize TinyDB instance
  - Create tables: threads, issues, analysis_runs

- `save_thread(thread: EmailThread) -> str`
  - Store email thread with unique ID
  - Return thread_id

- `save_issue(issue: Issue) -> str`
  - Store issue with unique ID
  - Link to thread_id
  - Return issue_id

- `get_open_issues() -> List[Issue]`
  - Query all issues with status="OPEN"
  - Return sorted by priority

- `get_resolved_issues() -> List[Issue]`
  - Query all issues with status="RESOLVED"

- `update_issue_status(issue_id: str, status: str, resolution_evidence: str)`
  - Update issue when resolved

- `save_analysis_run(metadata: dict)`
  - Store metadata about each run
  - Timestamp, emails processed, issues found

**Schema Validation with Pydantic**:
All data going into TinyDB is validated using Pydantic models first, ensuring:
- Type safety
- Required fields present
- Valid enum values (issue_type, status)
- Date format consistency

**Production Migration Path** (documented in Blueprint):
```
PoC: TinyDB (JSON file)
  ↓
Production: PostgreSQL/MongoDB
  - Add async operations
  - Better concurrent access
  - Full-text search
  - Audit logging
  - Backup/restore capabilities
```

**Deliverables**:
- TinyDB wrapper class
- Pydantic validation on all DB operations
- Query methods for report generation

---

### Phase 5: Prioritization & Aggregation
**Goal**: Calculate priority scores and aggregate issues across all threads

#### 5.1 Priority Scoring Algorithm
```python
def calculate_priority_score(issue: Issue) -> float:
    """
    Priority = (Severity × 3) + (Days_Outstanding × 0.5) + (Confidence × 2)

    Components:
    - Severity: 1-10 (from AI)
    - Days_Outstanding: days since issue first appeared
    - Confidence: 0.0-1.0 (from AI)

    Max Score: 30 + variable days
    """
    severity_weight = 3.0
    time_weight = 0.5
    confidence_weight = 2.0

    score = (
        issue.severity * severity_weight +
        issue.days_outstanding * time_weight +
        issue.confidence * confidence_weight
    )

    return score
```

#### 5.2 Issue Aggregation
**Functions**:
- `aggregate_issues(all_threads: List[EmailThread]) -> Dict`
  - Collect all issues from all threads
  - Remove duplicates (same issue across multiple threads)
  - Separate OPEN vs RESOLVED issues
  - Calculate statistics

**Deliverables**:
- Priority scoring implementation
- Issue deduplication logic

---

### Phase 6: Report Generation & Visualization
**Goal**: Create actionable output for the Director

#### 6.1 JSON Report Structure
```json
{
  "report_metadata": {
    "generated_at": "2025-02-01T10:00:00Z",
    "total_threads_analyzed": 18,
    "total_emails_processed": 85,
    "total_issues_detected": 12,
    "total_issues_resolved": 4,
    "total_issues_open": 8
  },
  "open_issues": [
    {
      "priority_score": 25.5,
      "issue_id": "uuid",
      "issue_type": "UNRESOLVED_ACTION",
      "severity": 8,
      "project": "Project Phoenix",
      "subject": "Login Page Specification",
      "title": "Google SSO estimation not included",
      "description": "...",
      "evidence_quote": "This wasn't included in the estimate",
      "email_date": "2025-06-02",
      "email_author": "István Nagy",
      "days_outstanding": 15,
      "confidence": 0.9,
      "participants": ["István Nagy", "Péter Kovács"]
    }
  ],
  "resolved_issues": [...],
  "statistics": {
    "issues_by_type": {
      "UNRESOLVED_ACTION": 5,
      "EMERGING_RISK": 3
    },
    "issues_by_project": {
      "Project Phoenix": 4,
      "email10": 2
    },
    "avg_resolution_time_days": 8.5
  }
}
```

#### 6.2 Terminal Visualization (`src/report_generator.py`)
```
╔══════════════════════════════════════════════════════════════╗
║         PORTFOLIO HEALTH REPORT - Director Summary           ║
╚══════════════════════════════════════════════════════════════╝

Generated: 2025-02-01 10:00:00
Analyzed: 18 threads, 85 emails

┌─ SUMMARY ────────────────────────────────────────────────────┐
│ 🔴 HIGH Priority Issues:    3                                │
│ 🟡 MEDIUM Priority Issues:  5                                │
│ ✅ Resolved This Period:    4                                │
└──────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
 OPEN ISSUES (Sorted by Priority)
═══════════════════════════════════════════════════════════════

[1] 🔴 PRIORITY: 25.5 | UNRESOLVED_ACTION
    Project: Project Phoenix
    Subject: Login Page Specification

    Issue: Google SSO not included in original estimate
    Outstanding: 15 days | Confidence: 90%

    Evidence: "This wasn't included in the estimate"
              - István Nagy, 2025-06-02

    👥 Participants: István Nagy, Péter Kovács, Zsuzsa Varga

    📋 Recommended Action: Follow up on scope/budget re-planning

---

[... more issues ...]

═══════════════════════════════════════════════════════════════
 RESOLVED ISSUES
═══════════════════════════════════════════════════════════════

✅ CI/CD Pipeline setup issue (Resolved after 30 days)
   Resolution: "Thanks a lot, it works now!"

[... more resolved issues ...]
```

**Deliverables**:
- JSON report generator
- Colored terminal output
- Summary statistics

---

### Phase 7: Documentation
**Goal**: Create comprehensive documentation for interview submission

#### 7.1 README.md
**Sections**:
1. Project Overview
2. AI Model Justification
   - Why Azure OpenAI GPT-4?
   - Why not GPT-3.5-turbo? (accuracy vs cost tradeoff)
   - Temperature settings rationale
3. Installation & Setup
4. Usage Instructions
5. Example Output
6. Cost Estimation

#### 7.2 Blueprint.md
**Sections** (as per PDF requirements):
1. **Data Ingestion & Initial Processing**
   - Architecture diagram
   - Scalability considerations
   - Email parsing approach

2. **The Analytical Engine**
   - Attention flags definition
   - Multi-step AI process design
   - Hallucination mitigation strategies
   - Security considerations
   - Final engineered prompts (full text)

3. **Cost & Robustness Considerations**
   - Cost management strategy
   - Robustness against ambiguous information

4. **Monitoring & Trust**
   - Key metrics to track
   - Accuracy validation approach

5. **Architectural Risk & Mitigation**
   - Biggest risk: AI hallucination / false positives
   - Mitigation: Evidence validation, confidence scoring

**Deliverables**:
- Complete README.md
- Complete Blueprint.md

---

## Technical Stack

### Core Dependencies
```
openai>=1.0.0           # Azure OpenAI integration
python-dotenv>=1.0.0    # Environment variables
pydantic>=2.0.0         # Schema validation & data models
rich>=13.0.0            # Terminal formatting
tinydb>=4.8.0           # Lightweight local JSON database
pytest>=7.0.0           # Testing (optional)
```

### Why TinyDB?
- **PoC-Perfect**: Lightweight, zero-config, file-based storage
- **No Infrastructure**: No need for PostgreSQL/MySQL setup
- **JSON-Native**: Stores documents as JSON (perfect for our use case)
- **Queryable**: Can filter/search issues easily
- **Migration Path**: Blueprint will document upgrade to production DB (PostgreSQL, MongoDB)

**Storage Schema**:
```python
# Database: portfolio_data.json
{
  "threads": [...],           # All analyzed email threads
  "issues": [...],            # All detected issues
  "analysis_runs": [...]      # Metadata about each analysis run
}
```

### Python Version
- Python 3.9+

---

## Anti-Hallucination Strategy Summary

1. **Grounding with Thread Context**
   - Each API call receives summary of all previous issues
   - AI can track resolution status
   - Prevents duplicate/contradictory flags

2. **Evidence Requirement**
   - All issues MUST have exact quote from email
   - Post-processing validation confirms quote exists
   - No quote = issue rejected

3. **Few-Shot Learning**
   - 3 examples showing correct detection patterns
   - Teaches AI what's director-level vs noise

4. **Strict Output Schema with Pydantic Validation**
   - GPT-4 JSON mode enforces structure
   - Pydantic validates all AI responses before acceptance
   - Required fields prevent vague outputs
   - Type checking (severity 1-10, confidence 0.0-1.0)
   - Reject responses with extra/missing fields

5. **Confidence Scoring**
   - AI self-assesses certainty
   - Filter out low-confidence (<0.7) issues

6. **Low Temperature**
   - Temperature=0.2 for deterministic output
   - Reduces creative "interpretation"

7. **Validation Layer**
   - Code verifies all evidence quotes
   - Checks dates are valid
   - Confirms authors exist in emails

---

## Cost Estimation

### For PoC (18 email files, ~85 emails):
- Average prompt size: ~1,500 tokens (system + user + context)
- Average completion: ~500 tokens (JSON output)
- Total per email: ~2,000 tokens
- Total for all emails: ~170,000 tokens

**Azure OpenAI GPT-4 Pricing** (approximate):
- Input: $0.03 / 1K tokens
- Output: $0.06 / 1K tokens
- Estimated cost: ~$7-10 for complete PoC run

### For Production (1000 emails/month):
- ~$400-500/month at current pricing
- **Optimization opportunities**:
  - Cache thread summaries
  - Batch processing
  - Use GPT-3.5-turbo for low-priority threads
  - Only re-analyze new emails, not entire threads

---

## Testing Strategy

### Unit Tests (Optional for PoC)
1. Email parser tests
2. Date parsing edge cases
3. Evidence validation logic

### Integration Tests
1. End-to-end test with sample email
2. Validate JSON output schema
3. Priority scoring calculation

### Manual Validation
1. Review flagged issues against actual emails
2. Check for false positives
3. Verify resolved issues are actually resolved

---

## Success Criteria

✅ **Functional Requirements**:
- [ ] Parses all 18 email files successfully
- [ ] Detects unresolved action items
- [ ] Detects emerging risks/blockers
- [ ] Tracks issue resolution
- [ ] Generates JSON report
- [ ] Generates terminal visualization
- [ ] Calculates priority scores

✅ **Quality Requirements**:
- [ ] No hallucinated issues (all have valid evidence)
- [ ] No false positives on resolved issues
- [ ] Confidence scores are calibrated
- [ ] Report is actionable for a Director

✅ **Documentation Requirements**:
- [ ] Complete Blueprint.md
- [ ] Complete README.md with AI justifications
- [ ] Prompts are explained and justified
- [ ] Architecture diagrams included

---

## Implementation Timeline

| Phase | Estimated Time | Dependencies |
|-------|---------------|--------------|
| Phase 1: Setup | 30 min | None |
| Phase 2: Email Parsing | 1-2 hours | Phase 1 |
| Phase 3: Prompt Engineering | 2-3 hours | None (parallel) |
| Phase 4: Azure Integration | 2-3 hours | Phase 2, 3 |
| Phase 5: Prioritization | 1 hour | Phase 4 |
| Phase 6: Report Generation | 1-2 hours | Phase 5 |
| Phase 7: Documentation | 2-3 hours | All phases |
| **Total** | **10-15 hours** | |

---

## Next Steps

When you say **"get started"**, I will:

1. Create all directory structures
2. Implement email parser (`src/email_parser.py`)
3. Create prompt files with examples
4. Implement Azure OpenAI integration
5. Build prioritization logic
6. Create report generator
7. Write documentation
8. Test end-to-end

Ready to proceed when you are! 🚀
