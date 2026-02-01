"""
Report generator - Creates formatted reports from analysis results.
Supports both JSON and terminal (Rich) output.
"""

import json
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from src.models import Issue, ThreadAnalysisRecord, AnalysisRun, IssueStatus, IssueType
from src.database import PortfolioDB


class ReportGenerator:
    """Generates portfolio health reports in various formats."""

    def __init__(self, db: 'PortfolioDB' = None):
        self.console = Console()
        self.db = db

    def generate_json_report(
        self,
        open_issues: List[Issue],
        resolved_issues: List[Issue],
        thread_records: List[ThreadAnalysisRecord],
        analysis_run: AnalysisRun,
        output_path: Path
    ):
        """
        Generate JSON report file.

        Args:
            open_issues: List of open issues
            resolved_issues: List of resolved issues
            thread_records: List of thread analysis records
            analysis_run: Analysis run metadata
            output_path: Path to save JSON report
        """
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "analysis_run_id": analysis_run.run_id,
                "total_threads_analyzed": analysis_run.total_threads,
                "total_emails_processed": analysis_run.total_emails,
                "total_issues_detected": analysis_run.total_issues_found,
                "total_issues_resolved": analysis_run.total_issues_resolved,
                "execution_time_seconds": analysis_run.execution_time_seconds,
                "total_api_calls": analysis_run.total_api_calls,
                "total_tokens_used": analysis_run.total_tokens_used
            },
            "summary": {
                "open_issues_count": len(open_issues),
                "resolved_issues_count": len(resolved_issues),
                "high_priority_count": len([i for i in open_issues if i.severity >= 7]),
                "medium_priority_count": len([i for i in open_issues if 4 <= i.severity < 7]),
                "low_priority_count": len([i for i in open_issues if i.severity < 4])
            },
            "open_issues": [self._issue_to_dict(issue) for issue in open_issues],
            "resolved_issues": [self._issue_to_dict(issue) for issue in resolved_issues],
            "thread_summaries": [record.model_dump(mode='json') for record in thread_records]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return output_path

    def _issue_to_dict(self, issue: Issue) -> Dict[str, Any]:
        """Convert Issue to dict for JSON report."""
        # Get project name from database
        project_name = "Unknown Project"
        if self.db and issue.project_id:
            project = self.db.get_project_by_id(issue.project_id)
            if project:
                project_name = project.project_name

        return {
            "issue_id": issue.issue_id,
            "priority_score": round(issue.priority_score, 2),
            "issue_type": issue.issue_type.value,
            "status": issue.status.value,
            "severity": issue.severity,
            "confidence": issue.confidence,
            "project": project_name,
            "project_id": issue.project_id,
            "subject": issue.subject,
            "title": issue.title,
            "description": issue.description,
            "evidence_quote": issue.evidence_quote,
            "email_date": issue.email_date.isoformat(),
            "email_author": issue.email_author,
            "email_author_email": issue.email_author_email,
            "contact_person": issue.contact_person,
            "contact_person_email": issue.contact_person_email,
            "participants": issue.participants,
            "days_outstanding": issue.days_outstanding,
            "resolution_evidence": issue.resolution_evidence,
            "resolution_date": issue.resolution_date.isoformat() if issue.resolution_date else None
        }

    def print_terminal_report(
        self,
        open_issues: List[Issue],
        resolved_issues: List[Issue],
        analysis_run: AnalysisRun
    ):
        """
        Print formatted terminal report using Rich.

        Args:
            open_issues: List of open issues (sorted by priority)
            resolved_issues: List of resolved issues
            analysis_run: Analysis run metadata
        """
        self.console.clear()

        # Header
        header = Text()
        header.append("PORTFOLIO HEALTH REPORT\n", style="bold white on blue")
        header.append(f"Director of Engineering - Quarterly Business Review", style="italic")

        self.console.print(Panel(header, box=box.DOUBLE))

        # Metadata
        self.console.print(f"\n📊 [bold]Analysis Run:[/bold]")
        self.console.print(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.console.print(f"   Threads Analyzed: {analysis_run.total_threads}")
        self.console.print(f"   Emails Processed: {analysis_run.total_emails}")
        self.console.print(f"   Execution Time: {analysis_run.execution_time_seconds:.1f}s")
        self.console.print(f"   API Calls: {analysis_run.total_api_calls}")
        self.console.print(f"   Tokens Used: {analysis_run.total_tokens_used:,}")

        # Summary Box
        high_priority = len([i for i in open_issues if i.severity >= 7])
        medium_priority = len([i for i in open_issues if 4 <= i.severity < 7])
        low_priority = len([i for i in open_issues if i.severity < 4])

        summary_text = Text()
        summary_text.append(f"🔴 HIGH Priority Issues:    {high_priority}\n", style="bold red")
        summary_text.append(f"🟡 MEDIUM Priority Issues:  {medium_priority}\n", style="bold yellow")
        summary_text.append(f"🟢 LOW Priority Issues:     {low_priority}\n", style="bold green")
        summary_text.append(f"✅ Resolved This Period:    {len(resolved_issues)}", style="bold cyan")

        self.console.print(Panel(summary_text, title="Summary", box=box.ROUNDED))

        # Open Issues
        if open_issues:
            self.console.print(f"\n{'='*80}")
            self.console.print("[bold white on red] OPEN ISSUES (Sorted by Priority) [/bold white on red]")
            self.console.print(f"{'='*80}\n")

            for i, issue in enumerate(open_issues, 1):
                self._print_issue(i, issue)

        else:
            self.console.print("\n✅ [bold green]No open issues found. Portfolio health is good![/bold green]")

        # Resolved Issues
        if resolved_issues:
            self.console.print(f"\n{'='*80}")
            self.console.print("[bold white on green] RESOLVED ISSUES [/bold white on green]")
            self.console.print(f"{'='*80}\n")

            for i, issue in enumerate(resolved_issues, 1):
                self._print_resolved_issue(i, issue)

        self.console.print(f"\n{'='*80}\n")

    def _print_issue(self, number: int, issue: Issue):
        """Print a single open issue with formatting."""
        # Priority indicator
        if issue.severity >= 7:
            priority_color = "red"
            priority_label = "🔴 HIGH"
        elif issue.severity >= 4:
            priority_color = "yellow"
            priority_label = "🟡 MEDIUM"
        else:
            priority_color = "green"
            priority_label = "🟢 LOW"

        # Get project name
        project_name = "Unknown Project"
        if self.db and issue.project_id:
            project = self.db.get_project_by_id(issue.project_id)
            if project:
                project_name = project.project_name

        # Header
        self.console.print(f"[{number}] [{priority_color}]PRIORITY: {issue.priority_score:.1f} | {priority_label}[/{priority_color}] | {issue.issue_type.value}")

        # Project and Subject
        self.console.print(f"    [bold]Project:[/bold] {project_name}")
        self.console.print(f"    [bold]Subject:[/bold] {issue.subject}")

        # Issue Details
        self.console.print(f"\n    [bold cyan]Issue:[/bold cyan] {issue.title}")
        self.console.print(f"    [italic]{issue.description}[/italic]")

        # Metrics
        self.console.print(f"\n    [bold]Severity:[/bold] {issue.severity}/10 | [bold]Confidence:[/bold] {issue.confidence*100:.0f}% | [bold]Outstanding:[/bold] {issue.days_outstanding} days")

        # Contact Information
        self.console.print(f"\n    [bold yellow]👤 Contact:[/bold yellow] {issue.contact_person} <{issue.contact_person_email}>")

        # Evidence
        evidence_preview = issue.evidence_quote[:150] + "..." if len(issue.evidence_quote) > 150 else issue.evidence_quote
        self.console.print(f"\n    [bold]Evidence:[/bold]")
        self.console.print(f"    [dim]\"{ evidence_preview}\"[/dim]")
        self.console.print(f"    [dim]— {issue.email_author}, {issue.email_date.strftime('%Y-%m-%d')}[/dim]")

        # Participants
        if issue.participants:
            participants_str = ", ".join(issue.participants[:3])
            if len(issue.participants) > 3:
                participants_str += f" (+{len(issue.participants)-3} more)"
            self.console.print(f"\n    [bold]Participants:[/bold] {participants_str}")

        self.console.print()  # Blank line

    def _print_resolved_issue(self, number: int, issue: Issue):
        """Print a resolved issue."""
        self.console.print(f"[{number}] ✅ [bold green]{issue.title}[/bold green]")
        self.console.print(f"    [dim]Resolved after {issue.days_outstanding} days[/dim]")

        if issue.resolution_evidence:
            evidence_preview = issue.resolution_evidence[:100] + "..." if len(issue.resolution_evidence) > 100 else issue.resolution_evidence
            self.console.print(f"    [dim italic]\"{evidence_preview}\"[/dim italic]")

        self.console.print()

    def print_summary_table(self, open_issues: List[Issue]):
        """Print a compact summary table of open issues."""
        if not open_issues:
            self.console.print("✅ No open issues")
            return

        table = Table(title="Open Issues Summary", box=box.SIMPLE)

        table.add_column("#", style="cyan", width=3)
        table.add_column("Priority", style="magenta", width=8)
        table.add_column("Type", width=18)
        table.add_column("Title", style="bold", width=40)
        table.add_column("Contact", style="yellow", width=20)
        table.add_column("Days", style="red", width=5)

        for i, issue in enumerate(open_issues[:10], 1):  # Top 10
            priority_str = f"{issue.priority_score:.1f}"

            type_str = "🔄 Action" if issue.issue_type == IssueType.UNRESOLVED_ACTION else "⚠️  Risk"

            title_str = issue.title[:37] + "..." if len(issue.title) > 40 else issue.title

            contact_str = issue.contact_person[:17] + "..." if len(issue.contact_person) > 20 else issue.contact_person

            table.add_row(
                str(i),
                priority_str,
                type_str,
                title_str,
                contact_str,
                str(issue.days_outstanding)
            )

        self.console.print(table)
