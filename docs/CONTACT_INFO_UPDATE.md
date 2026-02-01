# Contact Information & Summary Storage Updates

## Changes Made

### 1. Enhanced Issue Model with Contact Information

**Added fields to `Issue` model:**
```python
email_author_email: str = ""          # Email of person who raised the issue
participants: List[str] = []          # All people involved in thread
contact_person: str = ""              # Primary person to contact
contact_person_email: str = ""        # Email of primary contact
```

**Contact Person Logic:**
- **For UNRESOLVED_ACTION**: Contact the person who was asked the question (first recipient)
  - Example: If Alice asks Bob a question, contact person = Bob
- **For EMERGING_RISK**: Contact the person who raised the risk (email author)
  - Example: If Bob raises a blocker, contact person = Bob

### 2. Thread Summary Storage

**New model: `ThreadAnalysisRecord`**
```python
class ThreadAnalysisRecord(BaseModel):
    thread_id: str
    project_name: str
    subject: str
    total_emails: int
    participants: List[str]
    first_email_date: datetime
    last_email_date: datetime
    final_summary: ThreadSummary        # ← Stored in TinyDB!
    analyzed_at: datetime
```

**What gets stored:**
- Complete thread metadata
- Final accumulated thread summary
- All participants
- Timeline information

### 3. Analyzer Return Value Updated

**Before:**
```python
def analyze_thread(thread) -> List[Issue]:
```

**After:**
```python
def analyze_thread(thread) -> tuple[List[Issue], ThreadAnalysisRecord]:
```

Now returns both issues AND the thread analysis record for TinyDB storage.

## Why This Matters

### For Directors
When reviewing issues, they can immediately see:
- **Who to talk to**: `contact_person` and `contact_person_email`
- **Who's involved**: `participants` list
- **Thread context**: Historical summaries in database

### Example Issue Output
```json
{
  "issue_id": "abc-123",
  "title": "Google SSO not in original estimate",
  "severity": 7,
  "email_author": "István Nagy",
  "email_author_email": "nagy.istvan@kisjozsitech.hu",
  "contact_person": "István Nagy",
  "contact_person_email": "nagy.istvan@kisjozsitech.hu",
  "participants": [
    "István Nagy <nagy.istvan@kisjozsitech.hu>",
    "Péter Kovács <kovacs.peter@kisjozsitech.hu>",
    "Zsuzsa Varga <varga.zsuzsa@kisjozsitech.hu>"
  ],
  "evidence_quote": "This wasn't included in the estimate"
}
```

Director can immediately:
1. Email István Nagy directly
2. See all people in the thread
3. Understand the full context

## Database Schema

**TinyDB will store:**
```json
{
  "threads": [
    {
      "thread_id": "...",
      "project_name": "Project Phoenix",
      "final_summary": {
        "key_points": [...],
        "participants_active": [...],
        "topics_discussed": [...]
      }
    }
  ],
  "issues": [
    {
      "issue_id": "...",
      "contact_person": "István Nagy",
      "contact_person_email": "nagy.istvan@kisjozsitech.hu",
      "participants": [...]
    }
  ]
}
```

## Next Steps

Need to implement:
1. ✅ Updated models
2. ✅ Contact determination logic
3. ✅ Thread record creation
4. ⏳ TinyDB wrapper to store both issues and thread records
5. ⏳ Report generator to display contact info prominently
