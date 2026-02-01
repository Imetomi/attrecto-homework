"""
AI Analyzer - Core analytical engine using Azure OpenAI.
Processes email threads sequentially with context accumulation.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from src.models import (
    Email, EmailThread, Issue, AIAnalysisResponse,
    NewIssueData, IssueType, IssueStatus, ThreadSummary,
    ThreadAnalysisRecord
)
from src.llm_gateway import LLMGateway
import config


class ThreadAnalyzer:
    """
    Analyzes email threads to detect issues requiring director attention.
    Uses sequential processing with accumulated context to prevent hallucination.
    """

    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        """
        Initialize analyzer with LLM gateway and prompts.

        Args:
            llm_gateway: Optional LLMGateway instance (creates new if None)
        """
        self.llm_gateway = llm_gateway or LLMGateway()

        # Load prompts
        self.system_prompt = self._load_prompt(config.SYSTEM_PROMPT_PATH)
        self.user_prompt_template = self._load_prompt(config.USER_PROMPT_TEMPLATE_PATH)

        # Load few-shot examples
        with open(config.FEW_SHOT_EXAMPLES_PATH, 'r') as f:
            self.few_shot_examples = json.load(f)

    def _load_prompt(self, path: Path) -> str:
        """Load prompt from file."""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def analyze_thread(self, thread: EmailThread) -> tuple[List[Issue], ThreadAnalysisRecord]:
        """
        Analyze an entire email thread sequentially.

        This is the main entry point that orchestrates the analysis:
        1. Process emails one by one in chronological order
        2. Accumulate thread summary and issue list
        3. Enable AI to track issue resolution

        Args:
            thread: EmailThread to analyze

        Returns:
            Tuple of (issues, thread_analysis_record)
            - issues: List of all detected issues (both open and resolved)
            - thread_analysis_record: Complete thread summary for storage
        """
        print(f"\n{'='*60}")
        print(f"Analyzing Thread: {thread.subject}")
        print(f"Project: {thread.project_name}")
        print(f"Emails: {len(thread.emails)}")
        print(f"{'='*60}\n")

        all_issues: List[Issue] = []
        thread_summary_text = ""
        thread_summary_data = ThreadSummary()

        # Sort emails chronologically
        sorted_emails = sorted(thread.emails, key=lambda e: e.date)

        for i, email in enumerate(sorted_emails, 1):
            print(f"Processing email {i}/{len(sorted_emails)} from {email.from_name}...")

            # Analyze single email with context
            result = self._analyze_single_email(
                email=email,
                email_number=i,
                total_emails=len(sorted_emails),
                thread=thread,
                previous_issues=all_issues,
                thread_summary_data=thread_summary_data
            )

            # Process new issues
            for new_issue_data in result['new_issues']:
                issue = self._create_issue_from_data(
                    new_issue_data,
                    email,
                    thread
                )
                all_issues.append(issue)
                print(f"  ✓ New issue detected: {issue.title} (severity: {issue.severity})")

            # Process resolved issues
            for resolved_data in result['resolved_issues']:
                issue = self._mark_issue_resolved(
                    all_issues,
                    resolved_data['issue_id'],
                    resolved_data['resolution_evidence'],
                    email.date
                )
                if issue:
                    print(f"  ✓ Issue resolved: {issue.title}")

            # Update thread summary
            thread_summary_data = result['thread_summary']

        # Calculate days outstanding and priority scores
        for issue in all_issues:
            if issue.status == IssueStatus.OPEN:
                days = (datetime.now() - issue.email_date).days
                issue.days_outstanding = days
                issue.calculate_priority_score()

        print(f"\nThread analysis complete:")
        print(f"  Total issues detected: {len(all_issues)}")
        print(f"  Open issues: {len([i for i in all_issues if i.status == IssueStatus.OPEN])}")
        print(f"  Resolved issues: {len([i for i in all_issues if i.status == IssueStatus.RESOLVED])}")

        # Create thread analysis record for storage
        thread_record = ThreadAnalysisRecord(
            thread_id=thread.thread_id,
            project_name=thread.project_name,
            subject=thread.subject,
            total_emails=len(thread.emails),
            participants=thread.participants,
            first_email_date=thread.get_first_email_date(),
            last_email_date=thread.get_last_email_date(),
            final_summary=thread_summary_data
        )

        return all_issues, thread_record

    def _analyze_single_email(
        self,
        email: Email,
        email_number: int,
        total_emails: int,
        thread: EmailThread,
        previous_issues: List[Issue],
        thread_summary_data: ThreadSummary
    ) -> Dict[str, Any]:
        """
        Analyze a single email with full context.

        Args:
            email: Email to analyze
            email_number: Position in thread (1-indexed)
            total_emails: Total emails in thread
            thread: Parent EmailThread
            previous_issues: List of previously detected issues
            thread_summary_data: Accumulated thread summary

        Returns:
            Dict with new_issues, resolved_issues, thread_summary
        """
        # Build context strings
        previous_issues_text = self._build_previous_issues_summary(previous_issues)
        thread_summary_text = self._build_thread_summary_text(thread_summary_data)

        # Format user prompt
        user_prompt = self._format_user_prompt(
            email=email,
            email_number=email_number,
            total_emails=total_emails,
            project_name=thread.project_name,
            subject=thread.subject,
            previous_issues_text=previous_issues_text,
            thread_summary_text=thread_summary_text
        )

        # Call LLM with JSON response
        try:
            response = self.llm_gateway.call_with_json_response(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt
            )

            # Validate response with Pydantic
            ai_response = AIAnalysisResponse(**response['data'])

            # Validate evidence quotes
            validated_issues = []
            for issue_data in ai_response.new_issues:
                if self._validate_evidence(issue_data.evidence_quote, email.body):
                    validated_issues.append(issue_data)
                else:
                    print(f"  ⚠️  Rejected issue (evidence not found): {issue_data.title}")

            return {
                'new_issues': validated_issues,
                'resolved_issues': ai_response.resolved_issues,
                'thread_summary': ai_response.thread_summary
            }

        except Exception as e:
            print(f"  ⚠️  Error analyzing email: {str(e)}")
            return {
                'new_issues': [],
                'resolved_issues': [],
                'thread_summary': thread_summary_data
            }

    def _format_user_prompt(
        self,
        email: Email,
        email_number: int,
        total_emails: int,
        project_name: str,
        subject: str,
        previous_issues_text: str,
        thread_summary_text: str
    ) -> str:
        """Format the user prompt with all context."""
        cc_line = ""
        if email.cc_emails:
            cc_line = f"**Cc:** {', '.join(email.cc_emails)}"

        return self.user_prompt_template.format(
            project_name=project_name,
            subject=subject,
            email_number=email_number,
            total_emails=total_emails,
            previous_issues=previous_issues_text or "None",
            thread_summary=thread_summary_text or "No summary yet (this is the first email)",
            from_name=email.from_name,
            from_email=email.from_email,
            email_date=email.date.strftime("%Y-%m-%d %H:%M"),
            to_emails=", ".join(email.to_emails),
            cc_line=cc_line,
            email_body=email.body
        )

    def _build_previous_issues_summary(self, issues: List[Issue]) -> str:
        """
        Build summary of previous issues for context.
        Only includes OPEN issues to avoid cluttering prompt.
        """
        if not issues:
            return "None"

        open_issues = [i for i in issues if i.status == IssueStatus.OPEN]

        if not open_issues:
            return "None (all previous issues have been resolved)"

        lines = []
        for i, issue in enumerate(open_issues, 1):
            lines.append(
                f"{i}. [{issue.issue_id}] {issue.title}\n"
                f"   Type: {issue.issue_type.value}\n"
                f"   First seen: {issue.email_date.strftime('%Y-%m-%d')}\n"
                f"   Evidence: \"{issue.evidence_quote[:100]}...\""
            )

        return "\n\n".join(lines)

    def _build_thread_summary_text(self, summary: ThreadSummary) -> str:
        """Build readable thread summary text."""
        if not summary.key_points:
            return "No summary yet"

        parts = []

        if summary.key_points:
            parts.append("Key Points:\n" + "\n".join(f"  - {p}" for p in summary.key_points))

        if summary.topics_discussed:
            parts.append("Topics: " + ", ".join(summary.topics_discussed))

        if summary.participants_active:
            parts.append("Active Participants: " + ", ".join(summary.participants_active))

        return "\n\n".join(parts)

    def _validate_evidence(self, evidence_quote: str, email_body: str) -> bool:
        """
        Validate that evidence quote exists in email body.
        Uses fuzzy matching to account for minor differences.

        Args:
            evidence_quote: Quote claimed as evidence
            email_body: Email body text

        Returns:
            True if quote found in body
        """
        # Normalize for comparison
        quote_norm = evidence_quote.lower().strip()
        body_norm = email_body.lower()

        # Direct substring match
        if quote_norm in body_norm:
            return True

        # Fuzzy match: check if most words are present
        quote_words = set(quote_norm.split())
        body_words = set(body_norm.split())

        # If 80%+ of quote words are in body, consider it valid
        if len(quote_words) > 0:
            overlap = len(quote_words & body_words) / len(quote_words)
            return overlap >= 0.8

        return False

    def _create_issue_from_data(
        self,
        issue_data: NewIssueData,
        email: Email,
        thread: EmailThread
    ) -> Issue:
        """
        Create Issue object from AI response data.
        Determines who to contact based on issue type.
        """
        # Determine primary contact person
        contact_person, contact_email = self._determine_contact_person(
            issue_data.issue_type,
            email,
            thread
        )

        return Issue(
            thread_id=thread.thread_id,
            issue_type=IssueType(issue_data.issue_type),
            severity=issue_data.severity,
            title=issue_data.title,
            description=issue_data.description,
            evidence_quote=issue_data.evidence_quote,
            email_date=email.date,
            email_author=email.from_name,
            email_author_email=email.from_email,
            project_name=thread.project_name,
            subject=thread.subject,
            participants=thread.participants,
            contact_person=contact_person,
            contact_person_email=contact_email,
            confidence=issue_data.confidence
        )

    def _determine_contact_person(
        self,
        issue_type: str,
        email: Email,
        thread: EmailThread
    ) -> tuple[str, str]:
        """
        Determine who should be contacted about this issue.

        Logic:
        - For UNRESOLVED_ACTION: Contact the person who was asked (first recipient)
        - For EMERGING_RISK: Contact the person who raised it (email author)

        Returns:
            Tuple of (name, email)
        """
        if issue_type == "UNRESOLVED_ACTION":
            # Contact the person who was asked the question
            if email.to_emails:
                # Return first recipient
                recipient_email = email.to_emails[0]
                recipient_name = self._extract_name_from_participants(
                    recipient_email,
                    thread.participants
                )
                return recipient_name, recipient_email
            else:
                # Fallback to email author
                return email.from_name, email.from_email

        else:  # EMERGING_RISK
            # Contact the person who raised the risk
            return email.from_name, email.from_email

    def _extract_name_from_participants(
        self,
        email_address: str,
        participants: List[str]
    ) -> str:
        """
        Extract name from participants list based on email.
        Participants are stored as "Name <email>" or just email.
        """
        for participant in participants:
            if email_address in participant:
                # Extract name if in format "Name <email>"
                if '<' in participant:
                    name = participant.split('<')[0].strip()
                    return name
                else:
                    # Just email, extract local part
                    return email_address.split('@')[0].replace('.', ' ').title()

        # Fallback: extract from email address
        return email_address.split('@')[0].replace('.', ' ').title()

    def _mark_issue_resolved(
        self,
        issues: List[Issue],
        issue_id: str,
        resolution_evidence: str,
        resolution_date: datetime
    ) -> Optional[Issue]:
        """
        Mark an issue as resolved.

        Args:
            issues: List of all issues
            issue_id: ID of issue to resolve
            resolution_evidence: Evidence of resolution
            resolution_date: Date of resolution

        Returns:
            Resolved issue or None if not found
        """
        for issue in issues:
            if issue.issue_id == issue_id:
                issue.status = IssueStatus.RESOLVED
                issue.resolution_evidence = resolution_evidence
                issue.resolution_date = resolution_date
                return issue

        return None
