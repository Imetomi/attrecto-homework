#!/usr/bin/env python3
"""
Portfolio Health Report - Main Entry Point
Analyzes engineering project emails to generate director-level insights.
"""

import time
from datetime import datetime
from pathlib import Path

import config
from src.email_parser import EmailFileLoader
from src.ai_analyzer import ThreadAnalyzer
from src.llm_gateway import LLMGateway
from src.database import PortfolioDB
from src.report_generator import ReportGenerator
from src.colleagues_parser import ColleaguesParser
from src.models import AnalysisRun


def main():
    """Main execution function."""
    print("=" * 80)
    print("PORTFOLIO HEALTH REPORT SYSTEM")
    print("AI-Powered Analysis for Engineering Directors")
    print("=" * 80)

    start_time = time.time()

    # Validate configuration
    try:
        config.validate_config()
        print("\n✓ Configuration validated")
    except ValueError as e:
        print(f"\n✗ {e}")
        return 1

    # Initialize components
    print("\n📦 Initializing components...")

    llm_gateway = LLMGateway()
    db = PortfolioDB(config.DB_PATH)

    # Load colleagues data
    colleagues_file = Path(config.DATA_DIR) / "Colleagues.txt"
    colleagues_parser = ColleaguesParser(colleagues_file)
    colleagues = colleagues_parser.parse()
    print(f"   ✓ Loaded {len(colleagues)} team members")

    analyzer = ThreadAnalyzer(llm_gateway, db=db, colleagues=colleagues)
    report_gen = ReportGenerator(db=db)
    loader = EmailFileLoader(config.DATA_DIR)

    # Load email threads
    print("\n" + "=" * 80)
    print("STEP 1: LOADING EMAIL THREADS")
    print("=" * 80)

    threads = loader.load_all_threads()

    if not threads:
        print("\n✗ No email threads found. Please check your data directory.")
        return 1

    # Analyze threads
    print("\n" + "=" * 80)
    print("STEP 2: AI ANALYSIS")
    print("=" * 80)

    all_issues = []
    all_thread_records = []
    all_projects = []

    for i, thread in enumerate(threads, 1):
        print(f"\n--- Thread {i}/{len(threads)} ---")

        try:
            # Analyze thread (returns issues, thread_record, and projects)
            issues, thread_record, projects = analyzer.analyze_thread(thread)

            # Store projects in database
            for project in projects:
                db.save_project(project)
                if project not in all_projects:
                    all_projects.append(project)

            # Store thread record
            db.save_thread_record(thread_record)

            # Store issues
            for issue in issues:
                db.save_issue(issue)
                all_issues.append(issue)

            all_thread_records.append(thread_record)

        except Exception as e:
            print(f"✗ Error analyzing thread: {str(e)}")
            import traceback

            traceback.print_exc()

    # Separate open and resolved issues
    open_issues = [i for i in all_issues if i.status.value == "OPEN"]
    resolved_issues = [i for i in all_issues if i.status.value == "RESOLVED"]

    # Sort open issues by priority
    open_issues.sort(key=lambda i: i.priority_score, reverse=True)

    # Create analysis run record
    end_time = time.time()
    execution_time = end_time - start_time

    gateway_stats = llm_gateway.get_stats()

    analysis_run = AnalysisRun(
        total_threads=len(threads),
        total_emails=sum(len(t.emails) for t in threads),
        total_issues_found=len(all_issues),
        total_issues_resolved=len(resolved_issues),
        total_api_calls=gateway_stats["total_requests"],
        total_tokens_used=gateway_stats["total_tokens"],
        execution_time_seconds=execution_time,
    )

    db.save_analysis_run(analysis_run)

    # Generate reports
    print("\n" + "=" * 80)
    print("STEP 3: GENERATING REPORTS")
    print("=" * 80)

    # JSON Report
    json_report_path = config.OUTPUT_DIR / "portfolio_health_report.json"
    report_gen.generate_json_report(
        open_issues=open_issues,
        resolved_issues=resolved_issues,
        thread_records=all_thread_records,
        analysis_run=analysis_run,
        output_path=json_report_path,
    )

    print(f"\n✓ JSON report saved: {json_report_path}")

    # Terminal Report
    print("\n" + "=" * 80)
    print("STEP 4: PORTFOLIO HEALTH REPORT")
    print("=" * 80)

    report_gen.print_terminal_report(
        open_issues=open_issues,
        resolved_issues=resolved_issues,
        analysis_run=analysis_run,
    )

    # LLM Gateway Stats
    llm_gateway.print_stats()

    # Database Stats
    print("\n" + "=" * 80)
    print("DATABASE STATISTICS")
    print("=" * 80)

    db_stats = db.get_statistics()
    print(f"Total Issues:          {db_stats['total_issues']}")
    print(f"Open Issues:           {db_stats['open_issues']}")
    print(f"Resolved Issues:       {db_stats['resolved_issues']}")
    print(f"Total Threads:         {db_stats['total_threads']}")
    print(f"Total Projects:        {db_stats['total_projects']}")
    print(f"Projects:              {', '.join(db_stats['projects'])}")
    print(f"Avg Priority (Open):   {db_stats['avg_priority_open']}")
    print(f"Analysis Runs:         {db_stats['total_analysis_runs']}")
    print("=" * 80)

    print(f"\n✓ Analysis complete!")
    print(f"   Database: {config.DB_PATH}")
    print(f"   JSON Report: {json_report_path}")

    # Close database
    db.close()

    return 0


if __name__ == "__main__":
    exit(main())
