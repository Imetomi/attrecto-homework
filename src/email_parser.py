"""
Email parser - Loads and parses email .txt files into structured Email and EmailThread objects.
"""

import re
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from src.models import Email, EmailThread


class EmailParser:
    """Parses raw email text files into structured Email objects."""

    @staticmethod
    def parse_email_file(file_path: Path) -> List[Email]:
        """
        Parse a single email file containing one or more threaded emails.

        Args:
            file_path: Path to email .txt file

        Returns:
            List of Email objects parsed from the file
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        emails = []

        # Split on blank lines followed by email headers (From: or Subject:)
        parts = re.split(r'\n\n+(?=(?:From|Subject): )', content)

        for part in parts:
            if not part.strip():
                continue

            email = EmailParser._parse_single_email(part)
            if email:
                emails.append(email)

        return emails

    @staticmethod
    def _parse_single_email(text: str) -> Optional[Email]:
        """Parse a single email from text."""
        lines = text.strip().split('\n')

        from_email = ""
        from_name = ""
        to_emails = []
        cc_emails = []
        date = None
        date_raw = ""
        subject = ""
        body_lines = []

        in_body = False
        i = 0

        while i < len(lines):
            line = lines[i]

            if in_body:
                body_lines.append(line)
                i += 1
                continue

            # Parse headers
            if line.startswith('From:'):
                match = re.search(r'From:\s*(.+?)\s*[<(](.+?)[>)]|From:\s*(.+)', line)
                if match:
                    if match.group(1) and match.group(2):
                        from_name = match.group(1).strip()
                        from_email = match.group(2).strip()
                    elif match.group(3):
                        from_email = match.group(3).strip()
                        # Try to extract name from email
                        from_name = from_email.split('@')[0].replace('.', ' ').title()

            elif line.startswith('To:'):
                to_part = line.replace('To:', '').strip()
                to_emails = EmailParser._extract_emails(to_part)

            elif line.startswith('Cc:'):
                cc_part = line.replace('Cc:', '').strip()
                cc_emails = EmailParser._extract_emails(cc_part)

            elif line.startswith('Date:'):
                date_raw = line.replace('Date:', '').strip()
                # Don't parse, just use a dummy date - AI will extract the real date
                date = datetime(2000, 1, 1)

            elif line.startswith('Subject:'):
                subject = line.replace('Subject:', '').strip()

            elif not line.strip() and (subject or from_email):
                # Empty line after headers indicates start of body
                in_body = True

            i += 1

        # If we didn't find proper headers, skip this email
        if not from_email:
            return None

        # Default date if not found - AI will extract the real one
        if not date:
            date = datetime(2000, 1, 1)

        body = '\n'.join(body_lines).strip()

        return Email(
            from_email=from_email,
            from_name=from_name,
            to_emails=to_emails,
            cc_emails=cc_emails,
            date=date,
            date_raw=date_raw,
            subject=subject,
            body=body
        )

    @staticmethod
    def _extract_emails(text: str) -> List[str]:
        """Extract email addresses from a comma-separated string."""
        emails = []

        # Split by comma
        parts = text.split(',')

        for part in parts:
            # Look for email pattern (anything@anything)
            match = re.search(r'[\w\.\-]+@[\w\.\-]+\.\w+', part)
            if match:
                emails.append(match.group(0))

        return emails


    @staticmethod
    def create_thread_from_emails(
        emails: List[Email],
        project_name: str = "Unknown Project"
    ) -> EmailThread:
        """
        Create an EmailThread from a list of emails.

        Args:
            emails: List of Email objects
            project_name: Name of the project (extracted from subject or filename)

        Returns:
            EmailThread object
        """
        if not emails:
            raise ValueError("Cannot create thread from empty email list")

        # Use subject from first email
        subject = emails[0].subject

        # Extract all unique participants
        participants = set()
        for email in emails:
            participants.add(f"{email.from_name} <{email.from_email}>")
            for to_email in email.to_emails:
                # Try to find name for this email
                name = to_email.split('@')[0].replace('.', ' ').title()
                participants.add(f"{name} <{to_email}>")
            for cc_email in email.cc_emails:
                name = cc_email.split('@')[0].replace('.', ' ').title()
                participants.add(f"{name} <{cc_email}>")

        return EmailThread(
            subject=subject,
            project_name=project_name,
            participants=sorted(list(participants)),
            emails=emails
        )

    @staticmethod
    def extract_project_name(subject: str, filename: str = "") -> str:
        """
        Extract project name from email subject or filename.

        Args:
            subject: Email subject line
            filename: Original filename

        Returns:
            Extracted project name
        """
        # Pattern 1: "Project Phoenix - ..."
        match = re.search(r'Project\s+(\w+)', subject, re.IGNORECASE)
        if match:
            return f"Project {match.group(1)}"

        # Pattern 2: Use filename
        if filename:
            # Remove .txt extension and clean up
            name = Path(filename).stem
            return name.replace('_', ' ').replace('-', ' ').title()

        return "Unknown Project"


class EmailFileLoader:
    """Loads all email files from a directory and creates EmailThreads."""

    def __init__(self, data_dir: Path):
        """
        Initialize loader with data directory.

        Args:
            data_dir: Directory containing email .txt files
        """
        self.data_dir = Path(data_dir)

    def load_all_threads(self) -> List[EmailThread]:
        """
        Load all email files and create EmailThread objects.

        Returns:
            List of EmailThread objects
        """
        threads = []

        # Find all .txt files except Colleagues.txt
        email_files = sorted(self.data_dir.glob('email*.txt'))

        print(f"\n📧 Loading email files from {self.data_dir}")
        print(f"Found {len(email_files)} email files\n")

        for file_path in email_files:
            try:
                # Parse emails from file
                emails = EmailParser.parse_email_file(file_path)

                if not emails:
                    print(f"⚠️  No emails found in {file_path.name}")
                    continue

                # Extract project name
                project_name = EmailParser.extract_project_name(
                    emails[0].subject,
                    file_path.name
                )

                # Create thread
                thread = EmailParser.create_thread_from_emails(emails, project_name)

                threads.append(thread)

                print(f"✓ Loaded {file_path.name}: {len(emails)} emails, project: {project_name}")

            except Exception as e:
                print(f"✗ Error loading {file_path.name}: {str(e)}")

        print(f"\n✓ Successfully loaded {len(threads)} threads")

        return threads
