"""Streamlit dashboard for human-in-the-loop oversight - 2055+ Edition."""

from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

import streamlit as st

from src.config.agent_settings import AgentSettingsManager, PROVIDERS


# GitHub integration helpers
def get_github_token() -> str | None:
    """Get GitHub token from environment."""
    return os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")


def run_gh_command(args: list[str], capture_output: bool = True) -> subprocess.CompletedProcess | None:
    """Run a GitHub CLI command safely."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=capture_output,
            text=True,
            timeout=30,
            env={**os.environ, "GH_TOKEN": get_github_token() or ""},
        )
        return result
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def check_gh_auth() -> bool:
    """Check if GitHub CLI is authenticated."""
    result = run_gh_command(["auth", "status"])
    return result is not None and result.returncode == 0


def list_github_repos(org: str | None = None, limit: int = 30) -> list[dict]:
    """List GitHub repositories."""
    args = ["repo", "list", "--json", "name,description,url,isPrivate,updatedAt"]
    if org:
        args.insert(2, org)
    args.extend(["--limit", str(limit)])
    result = run_gh_command(args)
    if result and result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
    return []


def get_repo_info(repo: str) -> dict | None:
    """Get detailed information about a repository."""
    result = run_gh_command([
        "repo", "view", repo, "--json",
        "name,description,url,defaultBranchRef,isPrivate,languages,issues,pullRequests"
    ])
    if result and result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
    return None


def list_repo_issues(repo: str, state: str = "open", limit: int = 20) -> list[dict]:
    """List issues for a repository."""
    result = run_gh_command([
        "issue", "list", "-R", repo, "--state", state,
        "--json", "number,title,state,author,createdAt,labels",
        "--limit", str(limit)
    ])
    if result and result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
    return []


def list_repo_prs(repo: str, state: str = "open", limit: int = 20) -> list[dict]:
    """List pull requests for a repository."""
    result = run_gh_command([
        "pr", "list", "-R", repo, "--state", state,
        "--json", "number,title,state,author,createdAt,headRefName",
        "--limit", str(limit)
    ])
    if result and result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
    return []


@dataclass
class ProjectConfig:
    """Configuration for a project."""
    name: str
    github_repo: str | None = None
    work_dir: str | None = None
    default_agent: str = "eng"
    auto_commit: bool = False
    branch_prefix: str = "auto/"
    custom_settings: dict = field(default_factory=dict)
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
    """Inject custom CSS for a futuristic 2055+ cyberpunk control panel."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700&family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap');

        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-tertiary: #1a1a25;
            --bg-card: rgba(18, 18, 26, 0.95);
            --text-primary: #e8e8f0;
            --text-secondary: #a0a0b0;
            --text-muted: #6a6a7a;
            --neon-cyan: #00f0ff;
            --neon-magenta: #ff00e5;
            --neon-green: #00ff9d;
            --neon-orange: #ff6b35;
            --neon-purple: #9d00ff;
            --border-glow: rgba(0, 240, 255, 0.3);
            --border-subtle: rgba(255, 255, 255, 0.08);
            --gradient-cyber: linear-gradient(135deg, var(--neon-cyan), var(--neon-magenta));
        }

        /* Main app container - Dark futuristic background */
        .stApp {
            background:
                radial-gradient(ellipse at top left, rgba(0, 240, 255, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at bottom right, rgba(255, 0, 229, 0.06) 0%, transparent 50%),
                radial-gradient(ellipse at center, rgba(157, 0, 255, 0.04) 0%, transparent 70%),
                linear-gradient(180deg, var(--bg-primary) 0%, #0d0d15 50%, var(--bg-primary) 100%) !important;
            color: var(--text-primary) !important;
            font-family: "Rajdhani", "Share Tech Mono", sans-serif !important;
            min-height: 100vh;
        }

        /* Animated grid background overlay */
        .stApp::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image:
                linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            pointer-events: none;
            z-index: 0;
        }

        /* GLOBAL TEXT COLOR - Light text on dark backgrounds */
        .stApp *, .stApp *::before, .stApp *::after {
            color: var(--text-primary) !important;
        }

        /* Sidebar - Futuristic panel */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%) !important;
            border-right: 1px solid var(--border-glow) !important;
            box-shadow: 4px 0 20px rgba(0, 240, 255, 0.1) !important;
        }

        [data-testid="stSidebar"] *,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] p {
            color: var(--text-primary) !important;
        }

        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
            font-family: "Orbitron", sans-serif !important;
            color: var(--neon-cyan) !important;
            text-shadow: 0 0 10px rgba(0, 240, 255, 0.5) !important;
        }

        /* Radio buttons - Neon style */
        [data-testid="stSidebar"] [data-baseweb="radio"] label,
        [data-testid="stSidebar"] [role="radiogroup"] label {
            color: var(--text-primary) !important;
            transition: all 0.3s ease !important;
        }

        [data-testid="stSidebar"] [data-baseweb="radio"] label:hover {
            color: var(--neon-cyan) !important;
            text-shadow: 0 0 8px rgba(0, 240, 255, 0.6) !important;
        }

        /* All headings - Orbitron futuristic font */
        h1, h2, h3 {
            font-family: "Orbitron", sans-serif !important;
            color: var(--neon-cyan) !important;
            text-shadow: 0 0 15px rgba(0, 240, 255, 0.4) !important;
            letter-spacing: 0.05em !important;
        }

        h4, h5, h6 {
            font-family: "Rajdhani", sans-serif !important;
            color: var(--text-primary) !important;
        }

        /* All text elements */
        p, span, div, label, li, td, th,
        .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li,
        .stTextInput label, .stTextArea label, .stSelectbox label,
        .stExpanderHeader, .stCaption,
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] * {
            color: var(--text-primary) !important;
        }

        /* Metric components - Neon glow */
        [data-testid="stMetric"],
        [data-testid="stMetric"] *,
        .stMetric, .stMetric * {
            color: var(--text-primary) !important;
        }

        [data-testid="stMetricValue"] {
            color: var(--neon-cyan) !important;
            font-family: "Orbitron", sans-serif !important;
            font-weight: 700 !important;
            font-size: 2rem !important;
            text-shadow: 0 0 20px rgba(0, 240, 255, 0.6) !important;
        }

        [data-testid="stMetricLabel"] {
            color: var(--text-secondary) !important;
            font-family: "Rajdhani", sans-serif !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.1em !important;
        }

        [data-testid="stMetricDelta"] {
            color: var(--neon-green) !important;
        }

        /* Input fields - Cyber style */
        .stTextInput input, .stTextArea textarea, .stSelectbox select,
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea {
            color: var(--text-primary) !important;
            background: var(--bg-tertiary) !important;
            border: 1px solid var(--border-glow) !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
        }

        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: var(--neon-cyan) !important;
            box-shadow: 0 0 15px rgba(0, 240, 255, 0.3), inset 0 0 10px rgba(0, 240, 255, 0.1) !important;
        }

        .stTextInput input::placeholder, .stTextArea textarea::placeholder {
            color: var(--text-muted) !important;
        }

        /* Select boxes and dropdowns */
        [data-baseweb="select"], [data-baseweb="select"] *,
        [data-baseweb="popover"], [data-baseweb="popover"] *,
        .stSelectbox *, [data-testid="stSelectbox"] * {
            color: var(--text-primary) !important;
            background: var(--bg-tertiary) !important;
        }

        [data-baseweb="menu"] {
            background: var(--bg-secondary) !important;
            border: 1px solid var(--border-glow) !important;
        }

        /* Links - Neon cyan */
        .stMarkdown a, a {
            color: var(--neon-cyan) !important;
            text-decoration: none !important;
            transition: all 0.3s ease !important;
        }

        .stMarkdown a:hover, a:hover {
            color: var(--neon-magenta) !important;
            text-shadow: 0 0 10px rgba(255, 0, 229, 0.6) !important;
        }

        /* Tabs - Futuristic */
        .stTabs [data-baseweb="tab-list"] {
            background: var(--bg-secondary) !important;
            border-bottom: 1px solid var(--border-glow) !important;
            gap: 4px;
        }

        .stTabs [data-baseweb="tab"] {
            background: transparent !important;
            color: var(--text-secondary) !important;
            border-radius: 8px 8px 0 0 !important;
            font-family: "Rajdhani", sans-serif !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }

        .stTabs [data-baseweb="tab"]:hover {
            color: var(--neon-cyan) !important;
            background: rgba(0, 240, 255, 0.1) !important;
        }

        .stTabs [aria-selected="true"] {
            background: rgba(0, 240, 255, 0.15) !important;
            border-bottom: 3px solid var(--neon-cyan) !important;
            color: var(--neon-cyan) !important;
            box-shadow: 0 0 15px rgba(0, 240, 255, 0.3) !important;
        }

        /* Buttons - Neon glow */
        .stButton > button {
            background: linear-gradient(135deg, rgba(0, 240, 255, 0.2), rgba(157, 0, 255, 0.2)) !important;
            color: var(--neon-cyan) !important;
            border: 1px solid var(--neon-cyan) !important;
            border-radius: 8px !important;
            font-family: "Rajdhani", sans-serif !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.1em !important;
            padding: 0.6rem 1.8rem !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 0 10px rgba(0, 240, 255, 0.2) !important;
        }

        .stButton > button:hover {
            background: linear-gradient(135deg, rgba(0, 240, 255, 0.4), rgba(157, 0, 255, 0.4)) !important;
            box-shadow: 0 0 25px rgba(0, 240, 255, 0.5), inset 0 0 15px rgba(0, 240, 255, 0.2) !important;
            transform: translateY(-2px) !important;
        }

        .stButton > button:disabled {
            background: rgba(100, 100, 120, 0.3) !important;
            color: var(--text-muted) !important;
            border-color: var(--text-muted) !important;
            box-shadow: none !important;
        }

        /* Expanders - Glass morphism */
        [data-testid="stExpander"], .stExpander {
            background: rgba(18, 18, 26, 0.8) !important;
            backdrop-filter: blur(10px) !important;
            border: 1px solid var(--border-glow) !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
        }

        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary *,
        .streamlit-expanderHeader, .streamlit-expanderHeader * {
            color: var(--text-primary) !important;
            font-weight: 600 !important;
        }

        /* Tables - Cyber grid */
        .stTable, .stTable *, .stDataFrame, .stDataFrame *,
        [data-testid="stTable"], [data-testid="stTable"] *,
        table, table * {
            color: var(--text-primary) !important;
        }

        table {
            background: var(--bg-card) !important;
            border: 1px solid var(--border-glow) !important;
            border-radius: 8px !important;
        }

        table th {
            background: linear-gradient(135deg, rgba(0, 240, 255, 0.2), rgba(157, 0, 255, 0.15)) !important;
            color: var(--neon-cyan) !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            border-bottom: 1px solid var(--neon-cyan) !important;
        }

        table td {
            background: transparent !important;
            color: var(--text-primary) !important;
            border-bottom: 1px solid var(--border-subtle) !important;
        }

        table tr:hover td {
            background: rgba(0, 240, 255, 0.05) !important;
        }

        /* Code blocks - Terminal style */
        .stCode, .stCodeBlock, [data-testid="stCode"], pre, code {
            background: linear-gradient(180deg, #0d0d15 0%, #0a0a0f 100%) !important;
            border: 1px solid var(--border-glow) !important;
            border-radius: 8px !important;
            font-family: "Share Tech Mono", monospace !important;
        }

        .stCode *, .stCodeBlock *, pre *, code * {
            color: var(--neon-green) !important;
        }

        /* Progress bar - Neon */
        .stProgress > div > div {
            background: var(--gradient-cyber) !important;
            box-shadow: 0 0 15px rgba(0, 240, 255, 0.5) !important;
        }

        .stProgress {
            background: var(--bg-tertiary) !important;
            border-radius: 10px !important;
        }

        /* Block container */
        .block-container {
            padding-top: 2.5rem;
            max-width: 1400px;
        }

        /* Panel title class */
        .panel-title {
            font-family: "Orbitron", sans-serif !important;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            font-size: 0.75rem;
            color: var(--neon-cyan) !important;
            font-weight: 600;
            text-shadow: 0 0 8px rgba(0, 240, 255, 0.4);
        }

        /* Kanban cards - Holographic */
        .kanban-card {
            border-radius: 12px;
            padding: 16px 18px;
            border: 1px solid var(--border-glow);
            background: linear-gradient(135deg, rgba(18, 18, 26, 0.95), rgba(26, 26, 37, 0.9));
            backdrop-filter: blur(10px);
            box-shadow:
                0 4px 20px rgba(0, 0, 0, 0.4),
                0 0 15px rgba(0, 240, 255, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.05);
            margin-bottom: 12px;
            animation: fadeUp 0.4s ease-out, holoPulse 4s ease-in-out infinite;
            transition: all 0.3s ease;
        }

        .kanban-card:hover {
            border-color: var(--neon-cyan);
            box-shadow:
                0 8px 30px rgba(0, 0, 0, 0.5),
                0 0 25px rgba(0, 240, 255, 0.25);
            transform: translateY(-3px);
        }

        .kanban-card__title {
            font-family: "Orbitron", sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.9rem;
            margin-bottom: 8px;
            color: var(--neon-cyan) !important;
            text-shadow: 0 0 8px rgba(0, 240, 255, 0.4);
        }

        .kanban-card__meta {
            font-size: 0.85rem;
            color: var(--text-secondary) !important;
            line-height: 1.5;
        }

        /* Kanban column */
        .kanban-column {
            background: linear-gradient(180deg, rgba(18, 18, 26, 0.8), rgba(10, 10, 15, 0.9));
            border-radius: 16px;
            padding: 16px;
            border: 1px solid var(--border-subtle);
            min-height: 180px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
        }

        /* Status pill - Glowing badges */
        .status-pill {
            display: inline-block;
            padding: 5px 14px;
            border-radius: 999px;
            background: linear-gradient(135deg, rgba(0, 240, 255, 0.2), rgba(157, 0, 255, 0.2));
            border: 1px solid var(--neon-cyan);
            color: var(--neon-cyan) !important;
            font-family: "Orbitron", sans-serif !important;
            font-size: 0.7rem;
            font-weight: 600;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            box-shadow: 0 0 12px rgba(0, 240, 255, 0.3);
        }

        /* GitHub connection badge */
        .github-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 8px;
            background: linear-gradient(135deg, rgba(0, 255, 157, 0.15), rgba(0, 240, 255, 0.1));
            border: 1px solid var(--neon-green);
            color: var(--neon-green) !important;
            font-family: "Share Tech Mono", monospace !important;
            font-size: 0.85rem;
            box-shadow: 0 0 15px rgba(0, 255, 157, 0.2);
        }

        /* Alerts - Styled notifications */
        .stAlert, [data-testid="stAlert"] {
            border-radius: 10px !important;
            border-left: 4px solid var(--neon-cyan) !important;
            background: rgba(0, 240, 255, 0.08) !important;
        }

        .stAlert *, [data-testid="stAlert"] * {
            color: var(--text-primary) !important;
        }

        /* Spinner - Neon */
        .stSpinner > div {
            border-top-color: var(--neon-cyan) !important;
        }

        /* Caption */
        .stCaption, [data-testid="stCaption"] {
            color: var(--text-muted) !important;
            font-family: "Share Tech Mono", monospace !important;
        }

        /* Animations */
        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes holoPulse {
            0%, 100% { border-color: var(--border-glow); }
            50% { border-color: rgba(0, 240, 255, 0.5); }
        }

        @keyframes neonFlicker {
            0%, 100% { opacity: 1; }
            92% { opacity: 1; }
            93% { opacity: 0.8; }
            94% { opacity: 1; }
            96% { opacity: 0.9; }
        }

        /* Scrollbar - Cyber style */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }

        ::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, var(--neon-cyan), var(--neon-purple));
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--neon-cyan);
        }

        /* Data editor */
        [data-testid="stDataEditor"], [data-testid="stDataEditor"] * {
            color: var(--text-primary) !important;
            background: var(--bg-tertiary) !important;
        }

        /* Toggle */
        [data-testid="stToggle"] label, .stToggle label {
            color: var(--text-primary) !important;
        }

        /* File uploader */
        [data-testid="stFileUploader"], [data-testid="stFileUploader"] * {
            color: var(--text-primary) !important;
        }

        /* Number input */
        .stNumberInput input {
            color: var(--text-primary) !important;
            background: var(--bg-tertiary) !important;
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


def render_github_integration() -> None:
    """Render the GitHub integration page."""
    st.title("GitHub Integration")
    st.caption("Connect repositories, manage issues, and track pull requests.")

    # Check GitHub authentication
    gh_authenticated = check_gh_auth()
    token_configured = bool(get_github_token())

    # Status indicators
    col1, col2, col3 = st.columns(3)
    with col1:
        if gh_authenticated:
            st.markdown(
                "<div class='github-badge'>GitHub CLI: Connected</div>",
                unsafe_allow_html=True
            )
        else:
            st.warning("GitHub CLI not authenticated")
    with col2:
        if token_configured:
            st.markdown(
                "<div class='github-badge'>Token: Configured</div>",
                unsafe_allow_html=True
            )
        else:
            st.info("Set GITHUB_TOKEN in .env")
    with col3:
        default_org = os.getenv("GITHUB_DEFAULT_ORG", "")
        if default_org:
            st.markdown(
                f"<div class='github-badge'>Org: {default_org}</div>",
                unsafe_allow_html=True
            )

    st.divider()

    # Repository connection
    st.markdown("### Connect Repository")

    with st.expander("Add Repository Connection", expanded=not gh_authenticated):
        token_input = st.text_input(
            "GitHub Token (PAT)",
            type="password",
            help="Personal Access Token with repo scope"
        )
        org_input = st.text_input(
            "Organization/Username",
            value=os.getenv("GITHUB_DEFAULT_ORG", ""),
            help="Leave empty to list your personal repositories"
        )

        if st.button("Save GitHub Settings"):
            if token_input:
                st.info("Token configured. Add to .env file for persistence: GITHUB_TOKEN=your_token")
                os.environ["GITHUB_TOKEN"] = token_input
            if org_input:
                os.environ["GITHUB_DEFAULT_ORG"] = org_input
            st.success("Settings updated!")
            request_rerun()

    # List repositories
    if gh_authenticated or token_configured:
        st.markdown("### Your Repositories")

        org = os.getenv("GITHUB_DEFAULT_ORG", "")
        repos = list_github_repos(org if org else None, limit=50)

        if repos:
            # Repository filter
            search = st.text_input("Search repositories", key="repo_search")
            filtered_repos = [
                r for r in repos
                if not search or search.lower() in r.get("name", "").lower()
            ]

            # Display as cards
            for repo in filtered_repos[:20]:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        repo_name = repo.get("name", "Unknown")
                        repo_desc = repo.get("description", "No description")
                        is_private = repo.get("isPrivate", False)
                        privacy_badge = "Private" if is_private else "Public"

                        st.markdown(f"""
                        <div class='kanban-card'>
                            <div class='kanban-card__title'>{html.escape(repo_name)}</div>
                            <div class='kanban-card__meta'>{html.escape(repo_desc or 'No description')}</div>
                            <div class='status-pill'>{privacy_badge}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        full_name = f"{org}/{repo_name}" if org else repo_name
                        if st.button("View Details", key=f"view_{repo_name}"):
                            st.session_state["selected_repo"] = full_name
                            request_rerun()
        else:
            st.info("No repositories found. Check your token permissions.")

        # Repository details view
        selected_repo = st.session_state.get("selected_repo")
        if selected_repo:
            st.divider()
            st.markdown(f"### Repository: {selected_repo}")

            repo_info = get_repo_info(selected_repo)
            if repo_info:
                # Repo metrics
                m1, m2, m3, m4 = st.columns(4)
                issues = repo_info.get("issues", {})
                prs = repo_info.get("pullRequests", {})
                m1.metric("Open Issues", issues.get("totalCount", 0))
                m2.metric("Open PRs", prs.get("totalCount", 0))
                m3.metric("Default Branch", repo_info.get("defaultBranchRef", {}).get("name", "main"))
                m4.metric("Languages", len(repo_info.get("languages", {}).get("nodes", [])))

            # Tabs for issues and PRs
            tab_issues, tab_prs, tab_actions = st.tabs(["Issues", "Pull Requests", "Actions"])

            with tab_issues:
                issues = list_repo_issues(selected_repo)
                if issues:
                    for issue in issues:
                        with st.expander(f"#{issue['number']}: {issue['title']}"):
                            st.write(f"State: {issue['state']}")
                            st.write(f"Author: {issue['author']['login']}")
                            st.write(f"Created: {issue['createdAt']}")
                            labels = [l['name'] for l in issue.get('labels', [])]
                            if labels:
                                st.write(f"Labels: {', '.join(labels)}")

                            if st.button(f"Create session from issue #{issue['number']}", key=f"issue_session_{issue['number']}"):
                                st.session_state["new_session_mission"] = f"Issue #{issue['number']}: {issue['title']}"
                                st.session_state["nav_page"] = "Session Management"
                                request_rerun()
                else:
                    st.info("No open issues.")

            with tab_prs:
                prs = list_repo_prs(selected_repo)
                if prs:
                    for pr in prs:
                        with st.expander(f"#{pr['number']}: {pr['title']}"):
                            st.write(f"State: {pr['state']}")
                            st.write(f"Author: {pr['author']['login']}")
                            st.write(f"Branch: {pr['headRefName']}")
                            st.write(f"Created: {pr['createdAt']}")
                else:
                    st.info("No open pull requests.")

            with tab_actions:
                st.markdown("#### Quick Actions")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Clone to Project"):
                        st.info(f"Clone command: git clone https://github.com/{selected_repo}.git")
                with col2:
                    if st.button("Clear Selection"):
                        del st.session_state["selected_repo"]
                        request_rerun()
    else:
        st.info("Configure GitHub token to view repositories.")


def render_project_settings(orchestrator: Orchestrator, sessions: list[SessionRow]) -> None:
    """Render the project settings page."""
    st.title("Project Settings")
    st.caption("Configure per-project settings, agents, and automation rules.")

    # Project list from sessions
    projects = {}
    for session in sessions:
        project = session.project_name or "Default"
        if project not in projects:
            projects[project] = []
        projects[project].append(session)

    if not projects:
        st.info("No projects found. Start a session to create a project.")
        return

    # Project selector
    selected_project = st.selectbox(
        "Select Project",
        list(projects.keys()),
        key="selected_project"
    )

    st.divider()

    # Project overview
    project_sessions = projects.get(selected_project, [])
    st.markdown(f"### Project: {selected_project}")

    # Project metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Sessions", len(project_sessions))
    m2.metric("Running", sum(1 for s in project_sessions if s.status == SessionStatus.RUNNING))
    m3.metric("Completed", sum(1 for s in project_sessions if s.status == SessionStatus.COMPLETED))
    m4.metric("QA Passed", sum(1 for s in project_sessions if s.qa_passed))

    # Project configuration
    with st.expander("Project Configuration", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Repository Settings")
            github_repo = st.text_input(
                "GitHub Repository",
                placeholder="owner/repo",
                key=f"{selected_project}_github_repo"
            )
            work_dir = st.text_input(
                "Work Directory",
                value=f"projects/{selected_project.lower().replace(' ', '_')}",
                key=f"{selected_project}_work_dir"
            )

        with col2:
            st.markdown("#### Automation Settings")
            auto_commit = st.toggle(
                "Auto-commit changes",
                key=f"{selected_project}_auto_commit"
            )
            branch_prefix = st.text_input(
                "Branch Prefix",
                value="auto/",
                key=f"{selected_project}_branch_prefix"
            )
            default_agent = st.selectbox(
                "Default Agent",
                ["pm", "arch", "eng", "qa"],
                index=2,
                key=f"{selected_project}_default_agent"
            )

        if st.button("Save Project Settings", key=f"save_{selected_project}"):
            st.success(f"Settings saved for {selected_project}")

    # Agent assignments
    st.markdown("### Agent Assignments")
    st.caption("Assign specific agents or models to this project.")

    agent_cols = st.columns(4)
    agents = ["pm", "arch", "eng", "qa"]
    agent_labels = ["Product Manager", "Architect", "Engineer", "QA"]

    for col, agent, label in zip(agent_cols, agents, agent_labels):
        with col:
            st.markdown(f"**{label}**")
            model = st.selectbox(
                "Model",
                ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "custom"],
                key=f"{selected_project}_{agent}_model",
                label_visibility="collapsed"
            )
            priority = st.slider(
                "Priority",
                1, 10, 5,
                key=f"{selected_project}_{agent}_priority",
                help="Higher = more resources allocated"
            )

    # Project sessions list
    st.markdown("### Project Sessions")
    for session in project_sessions:
        with st.expander(f"Session {session.session_id[:8]} - {session.status.value}"):
            st.write(f"**Mission:** {session.mission}")
            st.write(f"**Phase:** {session.phase}")
            st.write(f"**Iterations:** {session.iteration_count}")
            st.progress(session.progress)
            st.caption(f"Updated: {session.updated_at.isoformat()}")


def main() -> None:
    """Run the Streamlit dashboard - 2055+ Edition."""
    st.set_page_config(
        page_title="Autonomous Software Studio // 2055",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    inject_styles()

    orchestrator = get_orchestrator()
    try:
        sessions = build_session_rows(orchestrator.list_sessions())
    except Exception as exc:
        st.error(f"Failed to load sessions: {exc}")
        sessions = []

    # Sidebar with futuristic styling
    st.sidebar.markdown("## CONTROL NEXUS")
    st.sidebar.caption("Neural Interface // v2055.1.0")

    # System status indicators
    st.sidebar.markdown("---")
    st.sidebar.markdown("**SYSTEM STATUS**")
    status_col1, status_col2 = st.sidebar.columns(2)
    with status_col1:
        st.markdown(f"Sessions: **{len(sessions)}**")
    with status_col2:
        running = sum(1 for s in sessions if s.status == SessionStatus.RUNNING)
        st.markdown(f"Active: **{running}**")

    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        [
            "Session Management",
            "Artifact Review",
            "Approval Interface",
            "Live Logs",
            "Metrics & Analytics",
            "GitHub Integration",
            "Project Settings",
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
    elif page == "GitHub Integration":
        render_github_integration()
    elif page == "Project Settings":
        render_project_settings(orchestrator, sessions)
    elif page == "Agent Account Management":
        render_agent_account_management()


if __name__ == "__main__":
    main()
