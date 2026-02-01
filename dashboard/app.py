"""
Portfolio Health Dashboard - FastAPI Application
Provides a web interface to visualize portfolio health metrics.
"""

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
import sys

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import PortfolioDB
from src.models import IssueStatus, IssueType
import config

app = FastAPI(
    title="Portfolio Health Dashboard",
    description="Director-level insights from engineering project communications",
    version="1.0.0"
)

# Setup templates and static files
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

# Initialize database
db = PortfolioDB(config.DB_PATH)


@app.get("/")
async def dashboard(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/summary")
async def get_summary():
    """Get portfolio summary statistics."""
    stats = db.get_statistics()

    open_issues = db.get_open_issues(sort_by_priority=True)
    resolved_issues = db.get_resolved_issues()

    # Calculate severity breakdown
    high_severity = len([i for i in open_issues if i.severity >= 7])
    medium_severity = len([i for i in open_issues if 4 <= i.severity < 7])
    low_severity = len([i for i in open_issues if i.severity < 4])

    # Issues by type
    unresolved_actions = len([i for i in open_issues if i.issue_type == IssueType.UNRESOLVED_ACTION])
    emerging_risks = len([i for i in open_issues if i.issue_type == IssueType.EMERGING_RISK])

    # Get latest analysis run
    latest_run = db.get_latest_analysis_run()

    return {
        "total_issues": stats['total_issues'],
        "open_issues": stats['open_issues'],
        "resolved_issues": stats['resolved_issues'],
        "total_threads": stats['total_threads'],
        "total_projects": stats['total_projects'],
        "projects": stats['projects'],
        "avg_priority": stats['avg_priority_open'],
        "severity_breakdown": {
            "high": high_severity,
            "medium": medium_severity,
            "low": low_severity
        },
        "type_breakdown": {
            "unresolved_actions": unresolved_actions,
            "emerging_risks": emerging_risks
        },
        "latest_run": {
            "timestamp": latest_run.timestamp.isoformat() if latest_run else None,
            "total_emails": latest_run.total_emails if latest_run else 0,
            "api_calls": latest_run.total_api_calls if latest_run else 0,
            "tokens_used": latest_run.total_tokens_used if latest_run else 0,
            "execution_time": latest_run.execution_time_seconds if latest_run else 0
        } if latest_run else None
    }


@app.get("/api/issues/open")
async def get_open_issues(limit: int = 50):
    """Get open issues sorted by priority."""
    issues = db.get_open_issues(sort_by_priority=True)[:limit]

    issues_data = []
    for issue in issues:
        # Get project name from database
        project_name = "Unknown Project"
        if issue.project_id:
            project = db.get_project_by_id(issue.project_id)
            if project:
                project_name = project.project_name

        issues_data.append({
            "issue_id": issue.issue_id,
            "title": issue.title,
            "description": issue.description,
            "severity": issue.severity,
            "priority_score": round(issue.priority_score, 2),
            "issue_type": issue.issue_type.value,
            "status": issue.status.value,
            "project_name": project_name,
            "project_id": issue.project_id,
            "subject": issue.subject,
            "contact_person": issue.contact_person,
            "contact_person_email": issue.contact_person_email,
            "email_author": issue.email_author,
            "email_date": issue.email_date.isoformat(),
            "days_outstanding": issue.days_outstanding,
            "confidence": issue.confidence,
            "evidence_quote": issue.evidence_quote[:200] + "..." if len(issue.evidence_quote) > 200 else issue.evidence_quote,
            "participants": issue.participants[:5]  # Limit to 5 for display
        })

    return {"issues": issues_data}


@app.get("/api/issues/resolved")
async def get_resolved_issues(limit: int = 20):
    """Get recently resolved issues."""
    issues = db.get_resolved_issues()[:limit]

    issues_data = []
    for issue in issues:
        # Get project name from database
        project_name = "Unknown Project"
        if issue.project_id:
            project = db.get_project_by_id(issue.project_id)
            if project:
                project_name = project.project_name

        issues_data.append({
            "issue_id": issue.issue_id,
            "title": issue.title,
            "severity": issue.severity,
            "issue_type": issue.issue_type.value,
            "project_name": project_name,
            "project_id": issue.project_id,
            "days_outstanding": issue.days_outstanding,
            "resolution_evidence": issue.resolution_evidence[:150] + "..." if issue.resolution_evidence and len(issue.resolution_evidence) > 150 else issue.resolution_evidence,
            "resolution_date": issue.resolution_date.isoformat() if issue.resolution_date else None
        })

    return {"issues": issues_data}


@app.get("/api/projects")
async def get_projects():
    """Get project-level statistics."""
    all_projects = db.get_all_projects()
    projects_data = []

    for project in all_projects:
        project_issues = db.get_issues_by_project(project.project_id)
        open_count = len([i for i in project_issues if i.status == IssueStatus.OPEN])
        resolved_count = len([i for i in project_issues if i.status == IssueStatus.RESOLVED])

        projects_data.append({
            "project_id": project.project_id,
            "name": project.project_name,
            "description": project.description,
            "keywords": project.related_keywords,
            "total_issues": len(project_issues),
            "open_issues": open_count,
            "resolved_issues": resolved_count
        })

    # Sort by open issues (descending)
    projects_data.sort(key=lambda p: p['open_issues'], reverse=True)

    return {"projects": projects_data}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "database": str(config.DB_PATH)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
