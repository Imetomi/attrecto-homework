"""
Parser for colleagues data file.
Extracts team member information for context in AI analysis.
"""

import re
from typing import List
from pathlib import Path

from src.models import Colleague


class ColleaguesParser:
    """Parses the Colleagues.txt file to extract team member information."""

    def __init__(self, colleagues_file: Path):
        """
        Initialize parser.

        Args:
            colleagues_file: Path to Colleagues.txt file
        """
        self.colleagues_file = Path(colleagues_file)

    def parse(self) -> List[Colleague]:
        """
        Parse colleagues file and return list of Colleague objects.

        Returns:
            List of Colleague objects

        Example line format:
            "Project Manager (PM): Péter Kovács (kovacs.peter@kisjozsitech.hu)"
        """
        colleagues = []

        if not self.colleagues_file.exists():
            return colleagues

        with open(self.colleagues_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pattern: Role: Name (email)
        # Example: "Project Manager (PM): Péter Kovács (kovacs.peter@kisjozsitech.hu)"
        pattern = r'([^:]+):\s*([^(]+)\(([^)]+@[^)]+)\)'

        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('Characters:'):
                continue

            match = re.search(pattern, line)
            if match:
                role = match.group(1).strip()
                name = match.group(2).strip()
                email = match.group(3).strip()

                colleague = Colleague(
                    name=name,
                    email=email,
                    role=role
                )
                colleagues.append(colleague)

        return colleagues

    def format_for_prompt(self, colleagues: List[Colleague]) -> str:
        """
        Format colleagues list for inclusion in AI prompt.

        Args:
            colleagues: List of Colleague objects

        Returns:
            Formatted string for prompt
        """
        if not colleagues:
            return "No colleagues data available."

        lines = ["Team Members:"]
        for colleague in colleagues:
            lines.append(f"- {colleague.name} ({colleague.email}): {colleague.role}")

        return "\n".join(lines)
