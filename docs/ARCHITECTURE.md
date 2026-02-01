# Architecture Overview

## System Flow

The Portfolio Health Report system has been redesigned with a **project-centric architecture** where email threads can reference multiple projects, and projects are tracked independently in the database.

### High-Level Flow

```
1. Parse Colleagues.txt → Load team member context
2. Load email threads from data/*.txt files
3. For each email thread:
   a. AI detects project mentions in emails
   b. Search database for existing matching projects
   c. Create new projects if no match found
   d. Detect issues and link them to projects
   e. Track issue resolution
4. Store everything in database (projects, issues, threads)
5. Generate reports (JSON + Terminal + Dashboard)
```

## Key Architectural Changes

### Before (Old Architecture)
- Email threads were treated as projects
- `project_name` was extracted from email subject/filename
- Issues stored `project_name` as a text field
- No colleagues context in AI analysis
- Projects were implicit, not explicitly tracked

### After (New Architecture)
- **Projects are first-class entities** with their own table
- **Email threads reference projects** via mentions detected by AI
- **Issues reference projects** via `project_id` foreign key
- **Colleagues context** is passed to AI for better contact person identification
- **Project matching logic** prevents duplicate projects

## Database Schema

### Tables

#### 1. `projects` Table
```json
{
  "project_id": "uuid",
  "project_name": "string",
  "description": "string",
  "related_keywords": ["keyword1", "keyword2"],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**Purpose**: Stores all unique projects detected across email threads.

**Matching Logic**:
- Search by project name (case-insensitive)
- Search by related keywords (case-insensitive)
- If match found → use existing project
- If no match → create new project

#### 2. `issues` Table
```json
{
  "issue_id": "uuid",
  "thread_id": "string",
  "project_id": "string",  // ← Changed from project_name
  "issue_type": "UNRESOLVED_ACTION | EMERGING_RISK",
  "status": "OPEN | RESOLVED | MONITORING",
  "severity": 1-10,
  "title": "string",
  "description": "string",
  "evidence_quote": "string",
  "email_date": "datetime",
  "email_author": "string",
  "email_author_email": "string",
  "subject": "string",
  "participants": ["email1", "email2"],
  "contact_person": "string",
  "contact_person_email": "string",
  "confidence": 0.0-1.0,
  "resolution_evidence": "string | null",
  "resolution_date": "datetime | null",
  "days_outstanding": "int",
  "priority_score": "float"
}
```

**Changes**:
- Removed `project_name` field
- Added `project_id` field (references projects table)
- Contact person now informed by colleagues data

#### 3. `threads` Table
```json
{
  "thread_id": "uuid",
  "project_name": "string",  // Primary project for the thread
  "subject": "string",
  "total_emails": "int",
  "participants": ["email1", "email2"],
  "first_email_date": "datetime",
  "last_email_date": "datetime",
  "final_summary": {
    "key_points": ["point1", "point2"],
    "participants_active": ["name1", "name2"],
    "topics_discussed": ["topic1", "topic2"]
  },
  "analyzed_at": "datetime"
}
```

#### 4. `analysis_runs` Table
```json
{
  "run_id": "uuid",
  "timestamp": "datetime",
  "total_threads": "int",
  "total_emails": "int",
  "total_issues_found": "int",
  "total_issues_resolved": "int",
  "total_api_calls": "int",
  "total_tokens_used": "int",
  "execution_time_seconds": "float"
}
```

## AI Analysis Flow

### Components

#### 1. ColleaguesParser
**File**: `src/colleagues_parser.py`

**Purpose**: Parses `data/Colleagues.txt` to extract team member information.

**Output**: List of `Colleague` objects with name, email, and role.

**Usage**: Passed to AI analyzer as context for better contact person identification.

#### 2. ThreadAnalyzer (Updated)
**File**: `src/ai_analyzer.py`

**New Parameters**:
- `db: PortfolioDB` - Database instance for project lookups
- `colleagues: List[Colleague]` - Team members context

**New Flow**:
```python
def analyze_thread(thread):
    detected_projects = []

    for email in thread.emails:
        # AI analyzes email and returns:
        ai_response = {
            "project_mentions": [...],  # NEW
            "new_issues": [...],
            "resolved_issues": [...],
            "thread_summary": {...}
        }

        # Match or create projects
        for mention in ai_response.project_mentions:
            project = _match_or_create_project(mention)
            detected_projects.append(project)

        # Create issues linked to projects
        for issue_data in ai_response.new_issues:
            issue = _create_issue_from_data(
                issue_data,
                email,
                thread,
                detected_projects  # Link to first project
            )
            all_issues.append(issue)

    return all_issues, thread_record, detected_projects
```

#### 3. Project Matching Logic
**Method**: `_match_or_create_project()`

**Algorithm**:
```python
def _match_or_create_project(project_mention):
    # 1. Search by project name
    matches = db.search_projects(project_mention.project_name)

    # 2. Search by keywords
    for keyword in project_mention.keywords:
        matches.extend(db.search_projects(keyword))

    # 3. Remove duplicates
    unique_matches = deduplicate(matches)

    # 4. Return first match OR create new
    if unique_matches:
        return unique_matches[0]  # Use existing
    else:
        new_project = Project(
            project_name=project_mention.project_name,
            related_keywords=project_mention.keywords
        )
        db.save_project(new_project)
        return new_project
```

## AI Prompts Updates

### System Prompt Changes

Added project detection capability:
```json
{
  "project_mentions": [
    {
      "project_name": "name of the project mentioned",
      "keywords": ["keyword1", "keyword2"],
      "confidence": 0.0-1.0
    }
  ],
  "new_issues": [...],
  "resolved_issues": [...],
  "thread_summary": {...}
}
```

### User Prompt Changes

Added two new context sections:
```
## Team Members Context
{colleagues_context}

## Existing Projects
{existing_projects}
```

**Colleagues Context Example**:
```
Team Members:
- Péter Kovács (kovacs.peter@kisjozsitech.hu): Project Manager (PM)
- Zsuzsa Varga (varga.zsuzsa@kisjozsitech.hu): Business Analyst (BA)
- István Nagy (nagy.istvan@kisjozsitech.hu): Senior Developer
...
```

**Existing Projects Context Example**:
```
Existing Projects in Database:
- Project Phoenix (keywords: phoenix, rebirth, migration)
- KisJózsi Webshop (keywords: webshop, ecommerce, kisjozsi)
...
```

## Report Generation

### Changes to ReportGenerator

**New Parameter**: `db: PortfolioDB`

**Issue Display**:
- Issues no longer have `project_name` field
- Report generator looks up project name via `project_id`:
  ```python
  project = db.get_project_by_id(issue.project_id)
  project_name = project.project_name if project else "Unknown Project"
  ```

### Dashboard API Changes

All endpoints updated to resolve project names:
- `/api/issues/open` - Resolves `project_id` → `project_name`
- `/api/issues/resolved` - Resolves `project_id` → `project_name`
- `/api/projects` - Returns full project details with issue counts

### Dashboard UI Changes

**Removed**: Drop shadows on all cards and containers

**Before**: `class="bg-white rounded-lg shadow p-6"`

**After**: `class="bg-white rounded-lg p-6"`

## Data Migration

**Important**: The schema change is **not backward compatible**.

**Required Action**: Delete old data files before running:
```bash
rm portfolio_data.json portfolio_health_report.json
```

**Why**:
- Old issues have `project_name` field (string)
- New issues have `project_id` field (UUID)
- Projects table didn't exist before

## Benefits of New Architecture

### 1. Better Project Tracking
- Projects are explicit entities, not derived from email subjects
- One project can span multiple email threads
- Projects accumulate metadata (keywords, description)

### 2. Reduced Duplication
- AI can match similar project names (e.g., "Project Phoenix" vs "Phoenix Project")
- Keyword matching catches variations (e.g., "webshop" matches "KisJózsi webshop")

### 3. Improved Contact Person Identification
- AI has full team context with roles
- Better matching of email addresses to people
- More accurate routing of issues

### 4. Scalability
- Normalized database structure
- Easier to query issues by project
- Project statistics are more accurate

### 5. Consistency
- Single source of truth for project names
- No more "Email8" or "Email Thread 14" as project names
- More meaningful project categorization

## Example Scenario

**Email Thread**: Subject "Re: Phoenix Migration - Database Questions"

**Old Behavior**:
```
project_name = "Re: Phoenix Migration - Database Questions"  // From subject
```

**New Behavior**:
```
AI detects: project_mention = {
  "project_name": "Project Phoenix",
  "keywords": ["phoenix", "migration", "database"],
  "confidence": 0.9
}

Database search finds existing:
  - Project(id=123, name="Project Phoenix", keywords=["phoenix", "rebirth"])

Link issue to project_id=123
```

**Result**: All Phoenix-related issues are now grouped under the same project, even if they come from different email threads with different subjects.

## Future Enhancements

### Potential Improvements
1. **Multi-project Issues**: An issue could reference multiple projects
2. **Project Hierarchy**: Parent/child project relationships
3. **Project Owners**: Assign project managers from colleagues data
4. **Project Timeline**: Track project start/end dates
5. **Historical Trends**: Track how projects evolve over time
6. **Smart Deduplication**: ML-based project name matching

### Backwards Compatibility
If needed, a migration script could:
```python
# Pseudo-code for migration
for old_issue in old_database:
    # Search or create project from old project_name
    project = get_or_create_project(old_issue.project_name)

    # Update issue with project_id
    new_issue = Issue(**old_issue.dict(), project_id=project.project_id)
    new_database.save_issue(new_issue)
```

## Testing the New Flow

### Verification Steps

1. **Delete old data**:
   ```bash
   rm portfolio_data.json portfolio_health_report.json
   ```

2. **Run analysis**:
   ```bash
   uv run python main.py
   ```

3. **Check project detection**:
   - Look for "✓ Project detected: {name}" in logs
   - Look for "→ Matched to existing project" or "→ Created new project"

4. **Verify database**:
   ```python
   from src.database import PortfolioDB
   db = PortfolioDB("portfolio_data.json")

   # Check projects table
   projects = db.get_all_projects()
   print(f"Total projects: {len(projects)}")

   # Check issue-project links
   for issue in db.get_all_issues():
       project = db.get_project_by_id(issue.project_id)
       print(f"Issue: {issue.title} → Project: {project.project_name}")
   ```

5. **Test dashboard**:
   ```bash
   ./run_dashboard.sh
   ```
   - Verify projects appear in /api/projects
   - Verify issue cards show correct project names
   - Verify no drop shadows on UI elements

## Troubleshooting

### Issue: "Unknown Project" in reports

**Cause**: Issue's `project_id` not found in projects table

**Solution**:
- Check if projects were saved: `db.get_all_projects()`
- Verify AI is detecting projects in emails
- Check project matching logic

### Issue: Duplicate projects created

**Cause**: Project matching logic not finding similar projects

**Solution**:
- Add more keywords to projects
- Improve keyword extraction in AI prompt
- Manual project merging if needed

### Issue: Wrong contact person

**Cause**: Colleagues data not loaded or emails don't match

**Solution**:
- Verify `Colleagues.txt` format
- Check email addresses match exactly
- AI should fallback to email sender/recipient if no colleague match
