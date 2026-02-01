"""
TinyDB database wrapper with Pydantic validation.
Stores issues, thread analysis records, and analysis run metadata.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from tinydb import TinyDB, Query
from datetime import datetime

from src.models import Issue, ThreadAnalysisRecord, AnalysisRun, IssueStatus, Project


class PortfolioDB:
    """
    Database wrapper for storing portfolio analysis results.
    Uses TinyDB for lightweight, file-based storage.
    """

    def __init__(self, db_path: Path):
        """
        Initialize database.

        Args:
            db_path: Path to TinyDB JSON file
        """
        self.db_path = Path(db_path)
        self.db = TinyDB(db_path)

        # Create tables
        self.issues_table = self.db.table('issues')
        self.threads_table = self.db.table('threads')
        self.runs_table = self.db.table('analysis_runs')
        self.projects_table = self.db.table('projects')

    def save_issue(self, issue: Issue) -> str:
        """
        Save an issue to database.

        Args:
            issue: Issue object to save

        Returns:
            issue_id
        """
        # Convert Pydantic model to dict for storage
        issue_data = issue.model_dump(mode='json')

        # Check if issue already exists
        IssueQuery = Query()
        existing = self.issues_table.search(IssueQuery.issue_id == issue.issue_id)

        if existing:
            # Update existing issue
            self.issues_table.update(issue_data, IssueQuery.issue_id == issue.issue_id)
        else:
            # Insert new issue
            self.issues_table.insert(issue_data)

        return issue.issue_id

    def save_thread_record(self, thread_record: ThreadAnalysisRecord) -> str:
        """
        Save thread analysis record to database.

        Args:
            thread_record: ThreadAnalysisRecord to save

        Returns:
            thread_id
        """
        thread_data = thread_record.model_dump(mode='json')

        ThreadQuery = Query()
        existing = self.threads_table.search(ThreadQuery.thread_id == thread_record.thread_id)

        if existing:
            self.threads_table.update(thread_data, ThreadQuery.thread_id == thread_record.thread_id)
        else:
            self.threads_table.insert(thread_data)

        return thread_record.thread_id

    def save_analysis_run(self, run: AnalysisRun) -> str:
        """
        Save analysis run metadata.

        Args:
            run: AnalysisRun metadata

        Returns:
            run_id
        """
        run_data = run.model_dump(mode='json')
        self.runs_table.insert(run_data)
        return run.run_id

    def get_all_issues(self) -> List[Issue]:
        """Get all issues from database."""
        issues_data = self.issues_table.all()
        return [Issue(**data) for data in issues_data]

    def get_open_issues(self, sort_by_priority: bool = True) -> List[Issue]:
        """
        Get all open issues.

        Args:
            sort_by_priority: Whether to sort by priority score (default: True)

        Returns:
            List of open Issue objects
        """
        IssueQuery = Query()
        issues_data = self.issues_table.search(IssueQuery.status == IssueStatus.OPEN.value)

        issues = [Issue(**data) for data in issues_data]

        if sort_by_priority:
            issues.sort(key=lambda i: i.priority_score, reverse=True)

        return issues

    def get_resolved_issues(self) -> List[Issue]:
        """Get all resolved issues."""
        IssueQuery = Query()
        issues_data = self.issues_table.search(IssueQuery.status == IssueStatus.RESOLVED.value)
        return [Issue(**data) for data in issues_data]

    def get_issues_by_project(self, project_id: str) -> List[Issue]:
        """Get all issues for a specific project."""
        IssueQuery = Query()
        issues_data = self.issues_table.search(IssueQuery.project_id == project_id)
        return [Issue(**data) for data in issues_data]

    def update_issue_status(
        self,
        issue_id: str,
        status: IssueStatus,
        resolution_evidence: Optional[str] = None
    ):
        """
        Update issue status.

        Args:
            issue_id: ID of issue to update
            status: New status
            resolution_evidence: Evidence of resolution (if resolved)
        """
        IssueQuery = Query()

        update_data = {'status': status.value}

        if resolution_evidence:
            update_data['resolution_evidence'] = resolution_evidence
            update_data['resolution_date'] = datetime.now().isoformat()

        self.issues_table.update(update_data, IssueQuery.issue_id == issue_id)

    def get_thread_record(self, thread_id: str) -> Optional[ThreadAnalysisRecord]:
        """Get thread analysis record by ID."""
        ThreadQuery = Query()
        result = self.threads_table.search(ThreadQuery.thread_id == thread_id)

        if result:
            return ThreadAnalysisRecord(**result[0])
        return None

    def get_all_thread_records(self) -> List[ThreadAnalysisRecord]:
        """Get all thread analysis records."""
        threads_data = self.threads_table.all()
        return [ThreadAnalysisRecord(**data) for data in threads_data]

    def save_project(self, project: Project) -> str:
        """
        Save a project to database.

        Args:
            project: Project object to save

        Returns:
            project_id
        """
        project_data = project.model_dump(mode='json')

        ProjectQuery = Query()
        existing = self.projects_table.search(ProjectQuery.project_id == project.project_id)

        if existing:
            # Update timestamp
            project_data['updated_at'] = datetime.now().isoformat()
            self.projects_table.update(project_data, ProjectQuery.project_id == project.project_id)
        else:
            self.projects_table.insert(project_data)

        return project.project_id

    def get_all_projects(self) -> List[Project]:
        """Get all projects from database."""
        projects_data = self.projects_table.all()
        return [Project(**data) for data in projects_data]

    def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        ProjectQuery = Query()
        result = self.projects_table.search(ProjectQuery.project_id == project_id)

        if result:
            return Project(**result[0])
        return None

    def search_projects(self, search_term: str) -> List[Project]:
        """
        Search projects by name or keywords.

        Args:
            search_term: Term to search for (case-insensitive)

        Returns:
            List of matching Project objects
        """
        search_term_lower = search_term.lower()
        all_projects = self.get_all_projects()

        matching_projects = []
        for project in all_projects:
            # Check project name
            if search_term_lower in project.project_name.lower():
                matching_projects.append(project)
                continue

            # Check keywords
            if any(search_term_lower in keyword.lower() for keyword in project.related_keywords):
                matching_projects.append(project)

        return matching_projects

    def get_latest_analysis_run(self) -> Optional[AnalysisRun]:
        """Get the most recent analysis run."""
        runs = self.runs_table.all()

        if not runs:
            return None

        # Sort by timestamp (descending)
        sorted_runs = sorted(runs, key=lambda r: r.get('timestamp', ''), reverse=True)

        return AnalysisRun(**sorted_runs[0])

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dict with various statistics
        """
        all_issues = self.get_all_issues()
        open_issues = [i for i in all_issues if i.status == IssueStatus.OPEN]
        resolved_issues = [i for i in all_issues if i.status == IssueStatus.RESOLVED]

        # Get unique projects
        all_projects = self.get_all_projects()
        projects = {p.project_name for p in all_projects}

        # Calculate average priority for open issues
        avg_priority = 0.0
        if open_issues:
            avg_priority = sum(i.priority_score for i in open_issues) / len(open_issues)

        # Issues by type
        issues_by_type = {}
        for issue in all_issues:
            issue_type = issue.issue_type.value
            issues_by_type[issue_type] = issues_by_type.get(issue_type, 0) + 1

        return {
            'total_issues': len(all_issues),
            'open_issues': len(open_issues),
            'resolved_issues': len(resolved_issues),
            'total_threads': len(self.threads_table),
            'total_projects': len(projects),
            'projects': sorted(list(projects)),
            'avg_priority_open': round(avg_priority, 2),
            'issues_by_type': issues_by_type,
            'total_analysis_runs': len(self.runs_table)
        }

    def clear_all_data(self):
        """Clear all data from database (use with caution!)."""
        self.issues_table.truncate()
        self.threads_table.truncate()
        self.runs_table.truncate()
        self.projects_table.truncate()

    def close(self):
        """Close database connection."""
        self.db.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
