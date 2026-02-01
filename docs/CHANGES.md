# Major Architecture Changes

## Summary

The Portfolio Health Report system has been completely redesigned with a **project-centric architecture**. Email threads can now reference multiple projects, and projects are tracked as first-class entities in the database.

## What Changed

### 1. **Database Schema**
- ✅ Added new `projects` table
- ✅ Changed `issues.project_name` (string) → `issues.project_id` (UUID)
- ✅ Issues now reference projects via foreign key

### 2. **AI Analysis Flow**
- ✅ AI now detects project mentions in emails
- ✅ Projects are matched against existing database entries
- ✅ New projects created only if no match found
- ✅ Colleagues context integrated for better contact person identification

### 3. **Project Detection & Matching**
- ✅ AI extracts project names and keywords from emails
- ✅ Search by project name (case-insensitive)
- ✅ Search by related keywords (case-insensitive)
- ✅ Prevents duplicate projects

### 4. **Colleagues Integration**
- ✅ New `ColleaguesParser` parses `data/Colleagues.txt`
- ✅ Team member data passed to AI as context
- ✅ Better contact person identification based on roles

### 5. **UI/UX Improvements**
- ✅ Removed all drop shadows from dashboard
- ✅ Cleaner, more modern design

### 6. **Code Changes**
- ✅ Updated `src/models.py` - Added `Project`, `Colleague`, `ProjectMention` models
- ✅ Created `src/colleagues_parser.py` - New colleagues data parser
- ✅ Updated `src/database.py` - Added projects table and methods
- ✅ Updated `src/ai_analyzer.py` - Project detection and matching logic
- ✅ Updated `src/report_generator.py` - Resolve project names from IDs
- ✅ Updated `dashboard/app.py` - API endpoints use project IDs
- ✅ Updated `dashboard/templates/dashboard.html` - Removed shadows
- ✅ Updated `prompts/system_prompt.txt` - Project detection schema
- ✅ Updated `prompts/user_prompt_template.txt` - Colleagues and projects context
- ✅ Updated `main.py` - Integration of new flow

### 7. **Documentation**
- ✅ Created `docs/ARCHITECTURE.md` - Comprehensive architecture documentation
- ✅ Updated `docs/SETUP.md` - Added dashboard instructions

## Breaking Changes

⚠️ **This update is NOT backward compatible**

The database schema has changed significantly. You must:

1. **Delete old data files**:
   ```bash
   rm portfolio_data.json portfolio_health_report.json
   ```

2. **Run fresh analysis**:
   ```bash
   uv run python main.py
   ```

## Migration Path

If you need to preserve old data:

```python
# Pseudo-code - not implemented
from src.database import PortfolioDB
from src.models import Project

old_db = PortfolioDB("old_portfolio_data.json")
new_db = PortfolioDB("new_portfolio_data.json")

# For each old issue
for old_issue in old_db.get_all_issues():
    # Create or find project
    project = new_db.search_projects(old_issue.project_name)
    if not project:
        project = Project(
            project_name=old_issue.project_name,
            related_keywords=[old_issue.project_name.lower()]
        )
        new_db.save_project(project)
    else:
        project = project[0]

    # Update issue with project_id
    old_issue.project_id = project.project_id
    del old_issue.project_name  # Remove old field
    new_db.save_issue(old_issue)
```

## Benefits

### Before
- Email threads treated as projects
- Project names like "Email8", "Email Thread 14"
- No deduplication
- No colleagues context
- Inconsistent categorization

### After
- Projects are explicit, tracked entities
- Meaningful project names (e.g., "Project Phoenix")
- Automatic matching prevents duplicates
- Team member roles inform contact routing
- Better data organization

## Testing

All components tested successfully:

```bash
✅ Colleagues Parser - 18 team members loaded
✅ Projects Table - CRUD operations working
✅ Project Search - Name and keyword matching
✅ Issue-Project Linking - Foreign key relationships
✅ Database Schema - All tables functional
```

Run the test suite:
```bash
uv run python test_new_flow.py
```

## Examples

### Project Detection

**Email Subject**: "Re: Phoenix Migration - Database Questions"

**Old Behavior**:
```
project_name = "Re: Phoenix Migration - Database Questions"
```

**New Behavior**:
```json
{
  "project_mention": {
    "project_name": "Project Phoenix",
    "keywords": ["phoenix", "migration", "database"],
    "confidence": 0.9
  }
}
```

Database search finds existing "Project Phoenix" → Links issue to that project

### Colleagues Context

**Before**:
```
Contact Person: first.last@example.com (extracted from email)
```

**After**:
```
Team Members Context:
- Péter Kovács (kovacs.peter@kisjozsitech.hu): Project Manager (PM)
- Zsuzsa Varga (varga.zsuzsa@kisjozsitech.hu): Business Analyst (BA)
...

AI Decision:
Contact Person: Zsuzsa Varga <varga.zsuzsa@kisjozsitech.hu>
Reason: Business Analyst role matches the requirement gathering issue
```

## API Changes

### Dashboard Endpoints

All endpoints now return full project details:

**GET /api/issues/open**
```json
{
  "issues": [{
    "project_id": "uuid",
    "project_name": "Project Phoenix",  // Resolved from database
    ...
  }]
}
```

**GET /api/projects**
```json
{
  "projects": [{
    "project_id": "uuid",
    "name": "Project Phoenix",
    "description": "Auto-detected from email thread",
    "keywords": ["phoenix", "migration"],
    "total_issues": 5,
    "open_issues": 2,
    "resolved_issues": 3
  }]
}
```

## Future Enhancements

Potential improvements enabled by this architecture:

1. **Multi-project Issues** - One issue affecting multiple projects
2. **Project Hierarchy** - Parent/child relationships
3. **Project Owners** - Auto-assign from colleagues data
4. **Project Timeline** - Track start/end dates
5. **ML-based Matching** - Smarter project name deduplication
6. **Project Dashboard** - Dedicated project views
7. **Historical Trends** - Track project evolution over time

## Rollback

To revert to the old system:

```bash
git checkout <previous-commit>
```

Note: You'll lose the new architecture benefits.

## Questions?

See detailed documentation:
- `docs/ARCHITECTURE.md` - Full technical specification
- `docs/SETUP.md` - Setup and running instructions
- `test_new_flow.py` - Example usage and testing

## Credits

This redesign implements the following improvements requested:

- ✅ Projects as separate entities (not email threads)
- ✅ Project detection and matching to prevent duplicates
- ✅ Colleagues file integration for context
- ✅ Removed drop shadows from dashboard
- ✅ Better issue categorization by actual projects
- ✅ Comprehensive documentation

---

**Version**: 2.0.0
**Date**: 2026-02-01
**Status**: ✅ Complete and Tested
