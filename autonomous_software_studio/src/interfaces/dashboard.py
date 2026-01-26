"""Streamlit dashboard for human-in-the-loop oversight."""

from __future__ import annotations

import html
import os
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import streamlit as st

from src.config.agent_settings import AgentSettingsManager, PROVIDERS
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestration.orchestrator import (  # noqa: E402
    InvalidOperationError,
    Orchestrator,
    SessionInfo,
    SessionNotFoundError,
    SessionStatus,
)


PHASE_PROGRESS: dict[str, float] = {
    "pm": 0.15,
    "arch": 0.35,
    "human_gate": 0.5,
    "engineer": 0.7,
    "eng": 0.7,
    "qa": 0.85,
    "human_help": 0.9,
    "complete": 1.0,
    "failed": 1.0,
}


@dataclass
class SessionRow:
    """Renderable session row for the dashboard."""

    session_id: str
    mission: str
    status: SessionStatus
    phase: str
    progress: float
    updated_at: datetime
    project_name: str
    iteration_count: int
    qa_passed: bool


@st.cache_resource(show_spinner=False)
def _init_orchestrator() -> Orchestrator:
    """Create a cached orchestrator instance."""
    return Orchestrator()


def get_orchestrator() -> Orchestrator:
    """Return orchestrator instance, allowing tests to inject a fake."""
    if "orchestrator" in st.session_state:
        return st.session_state["orchestrator"]
    return _init_orchestrator()


def inject_styles() -> None:
    """Inject custom CSS for a distinctive control-panel feel."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&family=Space+Grotesk:wght@400;600&display=swap');

        :root {
            --ink: #1b1b1d;
            --muted: #5f646b;
            --accent: #0f4c5c;
            --accent-2: #e09f3e;
            --surface: rgba(255, 255, 255, 0.82);
            --surface-strong: rgba(255, 255, 255, 0.95);
            --border: rgba(15, 76, 92, 0.2);
        }

        .stApp {
            background: radial-gradient(circle at top left, rgba(224,159,62,0.15), transparent 35%),
                        linear-gradient(145deg, #f7f1e1 0%, #eef4f6 45%, #f7fafc 100%);
            color: var(--ink);
            font-family: "Space Grotesk", "Montserrat", "Trebuchet MS", sans-serif;
        }

        .stApp, .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li,
        .stTextInput label, .stTextArea label, .stSelectbox label,
        .stExpanderHeader, .stCaption, .stMetricLabel,
        .stTabs [data-baseweb="tab"], .stTabs [data-baseweb="tab"] * ,
        .stTable, .stDataFrame, .stDataFrame * ,
        .stSidebar .stMarkdown, .stSidebar .stCaption {
            color: var(--ink) !important;
        }

        .stTextInput input, .stTextArea textarea {
            color: var(--ink) !important;
            background-color: #ffffff !important;
        }

        .stMarkdown a {
            color: #0f4c5c !important;
        }

        .stTabs [data-baseweb="tab"] {
            background: rgba(255,255,255,0.85) !important;
        }

        .stTabs [aria-selected="true"] {
            border-bottom: 3px solid var(--accent-2) !important;
        }

        .stButton > button {
            background: var(--accent);
            color: #ffffff;
            border: none;
            border-radius: 999px;
        }

        .stButton > button:disabled {
            background: #9db2b8;
            color: #f2f2f2;
        }

        .block-container {
            padding-top: 2.5rem;
        }

        .panel-title {
            letter-spacing: 0.04em;
            text-transform: uppercase;
            font-size: 0.8rem;
            color: var(--muted);
        }

        .kanban-card {
            border-radius: 14px;
            padding: 12px 14px;
            border: 1px solid var(--border);
            background: var(--surface);
            box-shadow: 0 12px 30px rgba(15, 76, 92, 0.08);
            margin-bottom: 12px;
            animation: fadeUp 0.4s ease-out;
        }

        .kanban-card__title {
            font-weight: 600;
            font-size: 0.95rem;
            margin-bottom: 6px;
            color: var(--ink);
        }

        .kanban-card__meta {
            font-size: 0.8rem;
            color: var(--muted);
        }

        .kanban-column {
            background: var(--surface-strong);
            border-radius: 16px;
            padding: 12px;
            border: 1px solid var(--border);
            min-height: 140px;
            box-shadow: 0 10px 24px rgba(15, 76, 92, 0.08);
        }

        .status-pill {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            background: rgba(15, 76, 92, 0.1);
            color: var(--accent);
            font-size: 0.75rem;
            margin-bottom: 8px;
        }

        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def request_rerun() -> None:
    """Trigger a Streamlit rerun across versions."""
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def has_claude_cli() -> bool:
    """Check whether the Claude CLI is available."""
    override = os.getenv("CLAUDE_BINARY")
    if override:
        return bool(shutil.which(override) or Path(override).exists())
    return bool(shutil.which("claude") or shutil.which("claude-code"))


def build_session_rows(sessions: Iterable[SessionInfo]) -> list[SessionRow]:
    """Convert session info into render-friendly rows."""
    rows: list[SessionRow] = []
    for session in sessions:
        progress = PHASE_PROGRESS.get(session.current_phase, 0.1)
        if session.status in (
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.EXPIRED,
        ):
            progress = 1.0
        rows.append(
            SessionRow(
                session_id=session.session_id,
                mission=session.user_mission,
                status=session.status,
                phase=session.current_phase,
                progress=progress,
                updated_at=session.updated_at,
                project_name=session.project_name,
                iteration_count=session.iteration_count,
                qa_passed=session.qa_passed,
            )
        )
    return rows


def select_session_id(sessions: list[SessionRow]) -> str | None:
    """Select a session from the available list."""
    if not sessions:
        st.info("No sessions available yet.")
        return None

    session_ids = [session.session_id for session in sessions]
    default_id = st.session_state.get("selected_session_id", session_ids[0])
    default_index = session_ids.index(default_id) if default_id in session_ids else 0
    return st.selectbox(
        "Select Session",
        session_ids,
        index=default_index,
        key="selected_session_id",
    )


def read_text_safe(path: Path | str | None) -> str | None:
    """Read a text file safely, returning None on failure."""
    if not path:
        return None
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception:
        return None


def render_session_management(orchestrator: Orchestrator, sessions: list[SessionRow]) -> None:
    """Render the session management page."""
    st.title("Active Sessions")

    cli_available = has_claude_cli()
    if not cli_available:
        st.warning(
            "Claude CLI not found. Install claude-code or set CLAUDE_BINARY "
            "before starting sessions."
        )

    with st.expander("Start New Session", expanded=False):
        mission = st.text_area("Mission", key="new_session_mission")
        project_name = st.text_input("Project name (optional)", key="new_session_project")
        if st.button("Start Session", key="start_session", disabled=not cli_available):
            if not mission.strip():
                st.warning("Please provide a mission before starting.")
            else:
                try:
                    session_id = orchestrator.start_new_session(
                        mission,
                        project_name.strip() or None,
                    )
                    st.success(f"Session created: {session_id}")
                    st.session_state["selected_session_id"] = session_id
                    request_rerun()
                except Exception as exc:
                    st.error(f"Failed to start session: {exc}")

    if not sessions:
        st.info("No active sessions found. Start a new session to populate the board.")
        return

    status_filter = st.selectbox(
        "Filter by status",
        ["All"] + [status.value for status in SessionStatus],
        key="status_filter",
    )

    filtered = sessions
    if status_filter != "All":
        filtered = [s for s in sessions if s.status.value == status_filter]

    for session in filtered:
        with st.expander(f"Session {session.session_id}"):
            st.write(f"Mission: {session.mission}")
            st.write(f"Phase: {session.phase}")
            st.write(f"Status: {session.status.value}")
            st.write(f"Project: {session.project_name}")
            st.progress(session.progress)
            st.caption(f"Updated: {session.updated_at.isoformat()}")

    st.markdown("### Kanban Board")
    render_kanban_board(filtered)


def render_kanban_board(sessions: list[SessionRow]) -> None:
    """Render a kanban-style board grouped by status."""
    status_order = [
        SessionStatus.PENDING,
        SessionStatus.RUNNING,
        SessionStatus.AWAITING_APPROVAL,
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.EXPIRED,
    ]

    grouped: dict[SessionStatus, list[SessionRow]] = {status: [] for status in status_order}
    for session in sessions:
        grouped.setdefault(session.status, []).append(session)

    columns = st.columns(len(status_order))

    for col, status in zip(columns, status_order):
        with col:
            cards_html = ""
            for session in grouped.get(status, []):
                mission = html.escape(session.mission)
                cards_html += (
                    "<div class='kanban-card'>"
                    f"<div class='kanban-card__title'>Session {session.session_id[:8]}</div>"
                    f"<div class='kanban-card__meta'>Phase: {session.phase}</div>"
                    f"<div class='kanban-card__meta'>{mission[:80]}</div>"
                    "</div>"
                )
            column_html = (
                "<div class='kanban-column'>"
                f"<div class='status-pill'>{status.value.replace('_', ' ').title()}</div>"
                f"{cards_html}</div>"
            )
            st.markdown(column_html, unsafe_allow_html=True)


def render_artifact_review(orchestrator: Orchestrator, sessions: list[SessionRow]) -> None:
    """Render the artifact review page."""
    st.title("Review Artifacts")

    session_id = select_session_id(sessions)
    if not session_id:
        return

    try:
        artifacts = orchestrator.get_artifacts(session_id)
    except SessionNotFoundError as exc:
        st.error(str(exc))
        return

    tabs = st.tabs(["PRD", "Tech Spec", "Code"])

    with tabs[0]:
        prd_content = read_text_safe(artifacts.get("prd"))
        if prd_content:
            st.markdown(prd_content)
        else:
            st.info("PRD artifact not available yet.")

    with tabs[1]:
        spec_content = read_text_safe(artifacts.get("tech_spec"))
        if spec_content:
            st.markdown(spec_content)
        else:
            st.info("Tech spec artifact not available yet.")

    with tabs[2]:
        scaffold_content = read_text_safe(artifacts.get("scaffold"))
        if scaffold_content:
            st.subheader("Scaffold Script")
            st.code(scaffold_content, language="bash")
        else:
            st.info("No scaffold script available.")

        bug_report = read_text_safe(artifacts.get("bug_report"))
        if bug_report:
            with st.expander("QA Bug Report", expanded=False):
                st.markdown(bug_report)

        work_dir = artifacts.get("work_dir")
        if work_dir and Path(work_dir).exists():
            with st.expander("Work Directory Files", expanded=False):
                files = list(Path(work_dir).rglob("*"))
                display_files = [str(path) for path in files if path.is_file()][:50]
                if display_files:
                    st.code("\n".join(display_files), language="bash")
                else:
                    st.caption("No files created yet.")


def render_approval_interface(orchestrator: Orchestrator, sessions: list[SessionRow]) -> None:
    """Render the approval interface page."""
    st.title("Approval Interface")

    session_id = select_session_id(sessions)
    if not session_id:
        return

    try:
        info = orchestrator.get_session_status(session_id)
    except SessionNotFoundError as exc:
        st.error(str(exc))
        return

    st.write(f"Current status: {info.status.value}")
    st.write(f"Current phase: {info.current_phase}")

    approval_required = info.status == SessionStatus.AWAITING_APPROVAL
    if not approval_required:
        st.info("Session is not awaiting approval. Actions are disabled.")

    if st.button("Approve & Build", disabled=not approval_required):
        try:
            orchestrator.approve_and_continue(session_id)
            st.success("Building in progress...")
            st.balloons()
        except (InvalidOperationError, SessionNotFoundError) as exc:
            st.error(str(exc))

    with st.expander("Request Changes", expanded=True):
        feedback = st.text_area("Feedback", key="feedback_input")
        reject_phase = st.selectbox(
            "Send back to",
            ["PM", "Architect"],
            key="reject_phase",
        )
        reject_to = "pm" if reject_phase == "PM" else "architect"

        if st.button("Submit Feedback", disabled=not approval_required):
            if not feedback.strip():
                st.warning("Please provide feedback before submitting.")
            else:
                try:
                    orchestrator.reject_and_iterate(session_id, feedback, reject_to)
                    st.success("Feedback submitted. Iteration queued.")
                except (InvalidOperationError, SessionNotFoundError) as exc:
                    st.error(str(exc))


def render_live_logs(orchestrator: Orchestrator, sessions: list[SessionRow]) -> None:
    """Render live logs page with polling."""
    st.title("Live Execution Logs")

    session_id = select_session_id(sessions)
    if not session_id:
        return

    auto_refresh = st.toggle("Auto refresh", value=False, key="log_auto_refresh")
    st.button("Refresh now")

    log_container = st.empty()

    try:
        logs = orchestrator.get_recent_logs(session_id, lines=50)
    except SessionNotFoundError as exc:
        st.error(str(exc))
        return

    log_container.code(logs or "No logs available yet.", language="bash")

    if auto_refresh and orchestrator.is_running(session_id):
        time.sleep(2)
        request_rerun()


def render_metrics_analytics(sessions: list[SessionRow]) -> None:
    """Render metrics and analytics view."""
    st.title("Metrics & Analytics")

    if not sessions:
        st.info("No session data available for analytics.")
        return

    total = len(sessions)
    running = sum(1 for s in sessions if s.status == SessionStatus.RUNNING)
    awaiting = sum(1 for s in sessions if s.status == SessionStatus.AWAITING_APPROVAL)
    completed = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)
    failed = sum(1 for s in sessions if s.status == SessionStatus.FAILED)
    qa_passed = sum(1 for s in sessions if s.qa_passed)

    metric_cols = st.columns(5)
    metric_cols[0].metric("Total Sessions", total)
    metric_cols[1].metric("Running", running)
    metric_cols[2].metric("Awaiting Approval", awaiting)
    metric_cols[3].metric("Completed", completed)
    metric_cols[4].metric("Failed", failed)

    st.markdown("### Quality Signals")
    st.write(f"QA Passed: {qa_passed}/{total}")
    avg_iterations = sum(s.iteration_count for s in sessions) / max(total, 1)
    st.write(f"Average QA iterations: {avg_iterations:.2f}")

    status_breakdown: dict[str, int] = {}
    for session in sessions:
        status_breakdown[session.status.value] = status_breakdown.get(session.status.value, 0) + 1

    st.markdown("### Status Breakdown")
    st.table(
        [{"status": status.title().replace("_", " "), "count": count} for status, count in status_breakdown.items()]
    )


def _env_rows(env_overrides: dict[str, str]) -> list[dict[str, str]]:
    return [{"key": k, "value": v} for k, v in env_overrides.items()]


def _env_dict(rows: list[dict[str, str]]) -> dict[str, str]:
    env: dict[str, str] = {}
    for row in rows:
        key = row.get("key", "").strip()
        if key:
            env[key] = row.get("value", "")
    return env


def render_agent_account_management() -> None:
    """Render agent account and prompt management page."""
    st.title("Agent Account Management")
    st.caption("Manage API keys, provider/model, usage limits, and persona prompts.")

    settings_manager = AgentSettingsManager()
    agents = settings_manager.get_settings().get("agents", {})

    tabs = st.tabs([name.upper() for name in agents.keys()])

    for tab, profile in zip(tabs, agents.keys()):
        with tab:
            agent = settings_manager.get_agent(profile)

            st.markdown("### Provider & Model")
            provider_index = PROVIDERS.index(agent.get("provider")) if agent.get("provider") in PROVIDERS else 0
            provider = st.selectbox(
                "Provider",
                PROVIDERS,
                index=provider_index,
                key=f"{profile}_provider",
            )
            model = st.text_input(
                "Model",
                value=agent.get("model", ""),
                key=f"{profile}_model",
            )

            st.markdown("### Auth & Keys")
            auth_type = st.selectbox(
                "Auth Type",
                ["api_key", "token", "none"],
                index=["api_key", "token", "none"].index(agent.get("auth_type", "api_key")),
                key=f"{profile}_auth_type",
                help="Use token for claude-code account auth if API key is not applicable.",
            )
            api_key = st.text_input(
                "API Key",
                value=agent.get("api_key", ""),
                key=f"{profile}_api_key",
                type="password",
            )
            auth_token = st.text_input(
                "Auth Token",
                value=agent.get("auth_token", ""),
                key=f"{profile}_auth_token",
                type="password",
            )
            auth_env_var = st.text_input(
                "Token Env Var Name",
                value=agent.get("auth_env_var", "CLAUDE_CODE_TOKEN"),
                key=f"{profile}_auth_env_var",
                help="Set the environment variable name expected by claude-code for token auth.",
            )
            account_label = st.text_input(
                "Account Label",
                value=agent.get("account_label", ""),
                key=f"{profile}_account_label",
            )
            claude_profile_dir = st.text_input(
                "Claude Profile Dir (optional)",
                value=agent.get("claude_profile_dir", ""),
                key=f"{profile}_claude_profile_dir",
            )

            st.markdown("### Daily Usage")
            usage_unit = st.selectbox(
                "Usage Unit",
                ["runs", "sessions", "minutes"],
                index=["runs", "sessions", "minutes"].index(agent.get("usage_unit", "runs"))
                if agent.get("usage_unit", "runs") in ["runs", "sessions", "minutes"]
                else 0,
                key=f"{profile}_usage_unit",
            )
            daily_limit = st.number_input(
                f"Daily Limit ({usage_unit})",
                min_value=0,
                value=int(agent.get("daily_limit", 0)),
                step=1,
                key=f"{profile}_daily_limit",
                help="0 means unlimited.",
            )
            hard_limit = st.toggle(
                "Hard stop when limit reached",
                value=bool(agent.get("hard_limit", False)),
                key=f"{profile}_hard_limit",
            )
            st.write(f"Usage today: {agent.get('usage_today', 0)} {usage_unit}")
            if st.button("Reset usage counter", key=f"{profile}_reset_usage"):
                settings_manager.reset_usage(profile)
                request_rerun()

            st.markdown("### Custom Environment Variables")
            env_overrides = agent.get("env_overrides", {})
            env_rows = _env_rows(env_overrides)
            edited_rows = st.data_editor(
                env_rows,
                num_rows="dynamic",
                use_container_width=True,
                key=f"{profile}_env_overrides",
            )

            st.markdown("### Persona Prompt")
            active_path = settings_manager.get_prompt_path(profile)
            st.caption(f"Active prompt: {active_path}")
            prompt_content = settings_manager.read_prompt(profile)
            prompt_note = st.text_input(
                "Prompt version note (optional)",
                key=f"{profile}_prompt_note",
            )
            edited_prompt = st.text_area(
                "Edit prompt",
                value=prompt_content,
                height=350,
                key=f"{profile}_prompt_editor",
            )
            prompt_cols = st.columns(2)
            with prompt_cols[0]:
                if st.button("Save new prompt version", key=f"{profile}_save_prompt"):
                    settings_manager.save_prompt_version(profile, edited_prompt, prompt_note)
                    st.success("Prompt version saved.")
                    request_rerun()
            with prompt_cols[1]:
                if st.button("Use default prompt", key=f"{profile}_use_default_prompt"):
                    settings_manager.use_default_prompt(profile)
                    st.success("Default prompt restored.")
                    request_rerun()

            versions = settings_manager.list_prompt_versions(profile)
            if versions:
                st.markdown("#### Prompt History")
                version_labels = [
                    f"{v.created_at} | {Path(v.path).name} | {v.note}".strip()
                    for v in versions
                ]
                selected = st.selectbox(
                    "Select version to review",
                    version_labels,
                    key=f"{profile}_prompt_version_select",
                )
                selected_idx = version_labels.index(selected)
                selected_version = versions[selected_idx]
                try:
                    content = Path(selected_version.path).read_text(encoding="utf-8")
                except Exception:
                    content = "[Unable to read prompt version]"
                st.text_area(
                    "Selected version (read-only)",
                    value=content,
                    height=250,
                    key=f"{profile}_prompt_version_view",
                )
                if st.button("Revert to selected version", key=f"{profile}_prompt_revert"):
                    settings_manager.set_active_prompt(profile, Path(selected_version.path))
                    st.success("Prompt reverted.")
                    request_rerun()

            if st.button("Save agent settings", key=f"{profile}_save_settings"):
                settings_manager.update_agent(
                    profile,
                    {
                        "provider": provider,
                        "model": model,
                        "auth_type": auth_type,
                        "api_key": api_key,
                        "auth_token": auth_token,
                        "auth_env_var": auth_env_var,
                        "account_label": account_label,
                        "claude_profile_dir": claude_profile_dir,
                        "daily_limit": int(daily_limit),
                        "hard_limit": bool(hard_limit),
                        "usage_unit": usage_unit,
                        "env_overrides": _env_dict(edited_rows),
                    },
                )
                st.success("Settings saved.")


def main() -> None:
    """Run the Streamlit dashboard."""
    st.set_page_config(page_title="Autonomous Software Studio Control Panel", layout="wide")
    inject_styles()

    orchestrator = get_orchestrator()
    try:
        sessions = build_session_rows(orchestrator.list_sessions())
    except Exception as exc:
        st.error(f"Failed to load sessions: {exc}")
        sessions = []

    st.sidebar.markdown("## Control Panel")
    st.sidebar.caption("Human oversight for autonomous workflows.")

    page = st.sidebar.radio(
        "Navigation",
        [
            "Session Management",
            "Artifact Review",
            "Approval Interface",
            "Live Logs",
            "Metrics & Analytics",
            "Agent Account Management",
        ],
        key="nav_page",
    )

    if page == "Session Management":
        render_session_management(orchestrator, sessions)
    elif page == "Artifact Review":
        render_artifact_review(orchestrator, sessions)
    elif page == "Approval Interface":
        render_approval_interface(orchestrator, sessions)
    elif page == "Live Logs":
        render_live_logs(orchestrator, sessions)
    elif page == "Metrics & Analytics":
        render_metrics_analytics(sessions)
    elif page == "Agent Account Management":
        render_agent_account_management()


if __name__ == "__main__":
    main()
