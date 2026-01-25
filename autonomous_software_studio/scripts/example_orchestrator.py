#!/usr/bin/env python3
"""Example usage script for the Orchestrator.

This script demonstrates how to use the Orchestrator to start and manage
a multi-agent software development session.

Usage:
    python scripts/example_orchestrator.py --mission "Build a task management app"
    python scripts/example_orchestrator.py --list
    python scripts/example_orchestrator.py --status <session_id>
    python scripts/example_orchestrator.py --approve <session_id>
    python scripts/example_orchestrator.py --reject <session_id> --feedback "Add more features"
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.orchestrator import (
    Orchestrator,
    OrchestratorConfig,
    OrchestratorError,
    SessionNotFoundError,
    SessionStatus,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_orchestrator() -> Orchestrator:
    """Create and configure an Orchestrator instance."""
    config = OrchestratorConfig(
        db_path=Path("data/orchestrator.db"),
        work_dir_base=Path("projects"),
        max_iterations=5,
        session_ttl_days=7,
        use_sqlite_checkpointer=True,
    )
    return Orchestrator(config)


def start_session(orchestrator: Orchestrator, mission: str, project_name: str | None) -> None:
    """Start a new orchestration session."""
    print(f"\nStarting new session...")
    print(f"Mission: {mission}")
    if project_name:
        print(f"Project: {project_name}")

    try:
        session_id = orchestrator.start_new_session(mission, project_name)
        print(f"\n{'=' * 50}")
        print(f"Session created successfully!")
        print(f"Session ID: {session_id}")

        # Get status
        info = orchestrator.get_session_status(session_id)
        print(f"Status: {info.status.value}")
        print(f"Phase: {info.current_phase}")

        if info.status == SessionStatus.AWAITING_APPROVAL:
            print(f"\n{'=' * 50}")
            print("Session is awaiting human approval.")
            print("Use the following commands to continue:")
            print(f"  Approve: python scripts/example_orchestrator.py --approve {session_id}")
            print(f"  Reject:  python scripts/example_orchestrator.py --reject {session_id} --feedback 'Your feedback'")

    except OrchestratorError as e:
        print(f"\nError starting session: {e}")
        sys.exit(1)


def list_sessions(orchestrator: Orchestrator, status_filter: str | None) -> None:
    """List all sessions."""
    status = SessionStatus(status_filter) if status_filter else None
    sessions = orchestrator.list_sessions(status=status)

    if not sessions:
        print("No sessions found.")
        return

    print(f"\n{'Session ID':<40} {'Status':<20} {'Phase':<15} {'Mission'}")
    print("-" * 100)

    for session in sessions:
        mission_preview = session.user_mission[:30] + "..." if len(session.user_mission) > 30 else session.user_mission
        print(f"{session.session_id:<40} {session.status.value:<20} {session.current_phase:<15} {mission_preview}")


def show_status(orchestrator: Orchestrator, session_id: str) -> None:
    """Show detailed status of a session."""
    try:
        info = orchestrator.get_session_status(session_id)
        artifacts = orchestrator.get_artifacts(session_id)

        print(f"\n{'=' * 50}")
        print(f"Session: {session_id}")
        print(f"{'=' * 50}")
        print(f"Mission: {info.user_mission}")
        print(f"Project: {info.project_name}")
        print(f"Status: {info.status.value}")
        print(f"Phase: {info.current_phase}")
        print(f"Iteration: {info.iteration_count}")
        print(f"QA Passed: {info.qa_passed}")
        print(f"Created: {info.created_at}")
        print(f"Updated: {info.updated_at}")

        print(f"\nArtifacts:")
        for name, path in artifacts.items():
            if path:
                exists = "exists" if path.exists() else "missing"
                print(f"  {name}: {path} [{exists}]")
            else:
                print(f"  {name}: Not created yet")

    except SessionNotFoundError:
        print(f"Session not found: {session_id}")
        sys.exit(1)


def approve_session(orchestrator: Orchestrator, session_id: str) -> None:
    """Approve a session and continue execution."""
    try:
        print(f"\nApproving session {session_id}...")
        info = orchestrator.approve_and_continue(session_id)

        print(f"\n{'=' * 50}")
        print(f"Session approved and continuing!")
        print(f"New Status: {info.status.value}")
        print(f"New Phase: {info.current_phase}")

        if info.status == SessionStatus.COMPLETED:
            print("\nSession completed successfully!")
            artifacts = orchestrator.get_artifacts(session_id)
            print("\nGenerated artifacts:")
            for name, path in artifacts.items():
                if path and path.exists():
                    print(f"  {name}: {path}")

    except SessionNotFoundError:
        print(f"Session not found: {session_id}")
        sys.exit(1)
    except OrchestratorError as e:
        print(f"Error: {e}")
        sys.exit(1)


def reject_session(orchestrator: Orchestrator, session_id: str, feedback: str, reject_to: str) -> None:
    """Reject a session with feedback."""
    try:
        print(f"\nRejecting session {session_id}...")
        print(f"Feedback: {feedback}")
        print(f"Return to: {reject_to}")

        info = orchestrator.reject_and_iterate(session_id, feedback, reject_to)

        print(f"\n{'=' * 50}")
        print(f"Session rejected with feedback!")
        print(f"New Status: {info.status.value}")
        print(f"New Phase: {info.current_phase}")

    except SessionNotFoundError:
        print(f"Session not found: {session_id}")
        sys.exit(1)
    except OrchestratorError as e:
        print(f"Error: {e}")
        sys.exit(1)


def export_session(orchestrator: Orchestrator, session_id: str, output_path: str) -> None:
    """Export a session to a file."""
    try:
        path = Path(output_path)
        orchestrator.export_session(session_id, path)
        print(f"Session exported to: {path}")

    except SessionNotFoundError:
        print(f"Session not found: {session_id}")
        sys.exit(1)


def import_session(orchestrator: Orchestrator, input_path: str) -> None:
    """Import a session from a file."""
    try:
        path = Path(input_path)
        session_id = orchestrator.import_session(path)
        print(f"Session imported with ID: {session_id}")

    except FileNotFoundError:
        print(f"File not found: {input_path}")
        sys.exit(1)
    except ValueError as e:
        print(f"Invalid file: {e}")
        sys.exit(1)


def cleanup(orchestrator: Orchestrator) -> None:
    """Clean up expired sessions."""
    count = orchestrator.cleanup_expired_sessions()
    print(f"Cleaned up {count} expired sessions.")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Orchestrator example usage script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Actions
    parser.add_argument("--mission", type=str, help="Start a new session with this mission")
    parser.add_argument("--project", type=str, help="Project name (optional, used with --mission)")
    parser.add_argument("--list", action="store_true", help="List all sessions")
    parser.add_argument("--filter", type=str, choices=["pending", "running", "awaiting_approval", "completed", "failed", "expired"], help="Filter sessions by status")
    parser.add_argument("--status", type=str, metavar="SESSION_ID", help="Show detailed status of a session")
    parser.add_argument("--approve", type=str, metavar="SESSION_ID", help="Approve a session")
    parser.add_argument("--reject", type=str, metavar="SESSION_ID", help="Reject a session")
    parser.add_argument("--feedback", type=str, help="Feedback for rejection (used with --reject)")
    parser.add_argument("--reject-to", type=str, choices=["pm", "architect"], default="architect", help="Phase to return to on rejection")
    parser.add_argument("--export", type=str, nargs=2, metavar=("SESSION_ID", "OUTPUT_PATH"), help="Export a session to a file")
    parser.add_argument("--import", type=str, metavar="INPUT_PATH", dest="import_path", help="Import a session from a file")
    parser.add_argument("--cleanup", action="store_true", help="Clean up expired sessions")
    parser.add_argument("--delete", type=str, metavar="SESSION_ID", help="Delete a session")

    args = parser.parse_args()

    # Create orchestrator
    orchestrator = create_orchestrator()

    # Execute action
    if args.mission:
        start_session(orchestrator, args.mission, args.project)
    elif args.list:
        list_sessions(orchestrator, args.filter)
    elif args.status:
        show_status(orchestrator, args.status)
    elif args.approve:
        approve_session(orchestrator, args.approve)
    elif args.reject:
        if not args.feedback:
            print("Error: --feedback is required with --reject")
            sys.exit(1)
        reject_session(orchestrator, args.reject, args.feedback, args.reject_to)
    elif args.export:
        export_session(orchestrator, args.export[0], args.export[1])
    elif args.import_path:
        import_session(orchestrator, args.import_path)
    elif args.cleanup:
        cleanup(orchestrator)
    elif args.delete:
        result = orchestrator.delete_session(args.delete)
        if result:
            print(f"Session {args.delete} deleted.")
        else:
            print(f"Session {args.delete} not found.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
