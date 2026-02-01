"""
Pydantic data models for Portfolio Health Report system.
Provides schema validation and type safety throughout the application.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid


class IssueType(str, Enum):
    """Types of issues that require director attention."""
    UNRESOLVED_ACTION = "UNRESOLVED_ACTION"
    EMERGING_RISK = "EMERGING_RISK"


class IssueStatus(str, Enum):
    """Issue lifecycle status."""
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    MONITORING = "MONITORING"


class Email(BaseModel):
    """Represents a single email in a thread."""
    from_email: str
    from_name: str
    to_emails: List[str]
    cc_emails: List[str] = Field(default_factory=list)
    date: datetime
    subject: str
    body: str

    @field_validator('from_email')
    @classmethod
    def validate_from_email(cls, v: str) -> str:
        """Ensure from_email has @ symbol."""
        if '@' not in v:
            return f"{v}@unknown.com"
        return v

    @field_validator('to_emails')
    @classmethod
    def validate_to_emails(cls, v: List[str]) -> List[str]:
        """Filter valid email addresses."""
        return [e for e in v if '@' in e]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EmailThread(BaseModel):
    """Represents a threaded email conversation."""
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str
    project_name: str
    participants: List[str] = Field(default_factory=list)
    emails: List[Email] = Field(default_factory=list)

    def get_first_email_date(self) -> datetime:
        """Get timestamp of first email in thread."""
        if not self.emails:
            return datetime.now()
        return min(email.date for email in self.emails)

    def get_last_email_date(self) -> datetime:
        """Get timestamp of last email in thread."""
        if not self.emails:
            return datetime.now()
        return max(email.date for email in self.emails)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Issue(BaseModel):
    """Represents an issue requiring director attention."""
    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thread_id: str = ""
    issue_type: IssueType
    status: IssueStatus = IssueStatus.OPEN
    severity: int = Field(ge=1, le=10, description="Severity from 1-10")
    title: str = Field(min_length=5, max_length=200)
    description: str
    evidence_quote: str = Field(min_length=10)
    email_date: datetime
    email_author: str
    email_author_email: str = ""  # Email address of the person who raised the issue
    project_name: str = ""
    subject: str = ""
    participants: List[str] = Field(default_factory=list)  # All people involved in thread
    contact_person: str = ""  # Primary person to contact about this issue
    contact_person_email: str = ""  # Email of primary contact
    confidence: float = Field(ge=0.0, le=1.0, description="AI confidence 0.0-1.0")
    resolution_evidence: Optional[str] = None
    resolution_date: Optional[datetime] = None
    days_outstanding: int = 0
    priority_score: float = 0.0

    @field_validator('evidence_quote')
    @classmethod
    def validate_evidence(cls, v: str) -> str:
        """Ensure evidence quote is substantive."""
        if len(v) < 10:
            raise ValueError("Evidence quote must be at least 10 characters")
        return v

    def calculate_priority_score(self) -> float:
        """
        Calculate priority score based on multiple factors.

        Formula: (Severity × 3) + (Days_Outstanding × 0.5) + (Confidence × 2)

        Returns:
            float: Priority score (higher = more urgent)
        """
        severity_weight = 3.0
        time_weight = 0.5
        confidence_weight = 2.0

        score = (
            self.severity * severity_weight +
            self.days_outstanding * time_weight +
            self.confidence * confidence_weight
        )

        self.priority_score = score
        return score

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ThreadSummary(BaseModel):
    """Summary of key points from email thread analysis."""
    key_points: List[str] = Field(default_factory=list)
    participants_active: List[str] = Field(default_factory=list)
    topics_discussed: List[str] = Field(default_factory=list)


class ThreadAnalysisRecord(BaseModel):
    """Complete record of a thread analysis for storage in TinyDB."""
    thread_id: str
    project_name: str
    subject: str
    total_emails: int
    participants: List[str]
    first_email_date: datetime
    last_email_date: datetime
    final_summary: ThreadSummary
    analyzed_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NewIssueData(BaseModel):
    """Schema for new issue detected by AI."""
    issue_type: str
    severity: int = Field(ge=1, le=10)
    title: str
    description: str
    evidence_quote: str
    confidence: float = Field(ge=0.0, le=1.0)


class ResolvedIssueData(BaseModel):
    """Schema for issue resolution detected by AI."""
    issue_id: str
    resolution_evidence: str
    confidence: float = Field(ge=0.0, le=1.0)


class AIAnalysisResponse(BaseModel):
    """
    Schema for validating AI response.
    Ensures GPT-4 returns properly structured output.
    """
    new_issues: List[NewIssueData] = Field(default_factory=list)
    resolved_issues: List[ResolvedIssueData] = Field(default_factory=list)
    thread_summary: ThreadSummary = Field(default_factory=ThreadSummary)

    class Config:
        extra = 'forbid'  # Reject any extra fields from AI


class AnalysisRun(BaseModel):
    """Metadata about an analysis run."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    total_threads: int = 0
    total_emails: int = 0
    total_issues_found: int = 0
    total_issues_resolved: int = 0
    total_api_calls: int = 0
    total_tokens_used: int = 0
    execution_time_seconds: float = 0.0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
