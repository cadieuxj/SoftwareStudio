# Autonomous Software Studio - Architecture Documentation

## Overview

Autonomous Software Studio is a multi-agent AI orchestration platform designed for autonomous software development. It leverages LangGraph for state machine orchestration and Claude CLI for AI agent execution, with a Streamlit-based dashboard for human oversight.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTONOMOUS SOFTWARE STUDIO                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │   Dashboard UI   │    │   Orchestrator   │    │   PostgreSQL     │      │
│  │   (Streamlit)    │◄──►│   (LangGraph)    │◄──►│   Database       │      │
│  │   Port: 8501     │    │   Port: 8000     │    │   Port: 5432     │      │
│  └──────────────────┘    └────────┬─────────┘    └──────────────────┘      │
│                                   │                                          │
│                    ┌──────────────┼──────────────┐                          │
│                    │              │              │                          │
│                    ▼              ▼              ▼                          │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                      AGENT LAYER (Claude CLI)                    │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │       │
│  │  │    PM    │  │  ARCH    │  │   ENG    │  │    QA    │        │       │
│  │  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │        │       │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                   │                                          │
│                    ┌──────────────┼──────────────┐                          │
│                    ▼              ▼              ▼                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │   Redis Cache    │    │   File System    │    │   GitHub API     │      │
│  │   Port: 6379     │    │   (Projects)     │    │   (Integration)  │      │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Orchestrator Service (`src/orchestration/`)

The brain of the system - manages session lifecycle, agent coordination, and state persistence.

#### Key Files:
- `orchestrator.py` - Main orchestration engine (~1,100 lines)
- `workflow.py` - LangGraph state machine definition
- `state.py` - State management and validation
- `context_manager.py` - Dynamic CLAUDE.md generation
- `sqlite_checkpointer.py` - State persistence fallback

#### Orchestrator Class:
```python
class Orchestrator:
    """Main orchestration engine for multi-agent workflows."""

    def start_new_session(mission: str, project_name: str = None) -> str
    def approve_and_continue(session_id: str) -> SessionInfo
    def reject_and_iterate(session_id: str, feedback: str, reject_to: str) -> SessionInfo
    def get_session_status(session_id: str) -> SessionInfo
    def get_artifacts(session_id: str) -> dict
    def list_sessions() -> list[SessionInfo]
```

### 2. Agent Wrappers (`src/wrappers/`)

Abstraction layer for Claude CLI execution with persona-specific configurations.

#### Agent Hierarchy:
```
BaseAgent (Abstract)
    │
    ├── ClaudeCLIWrapper (Core execution)
    │
    ├── PMAgent (Product Manager)
    ├── ArchitectAgent (System Architect)
    ├── EngineerAgent (Software Engineer)
    └── QAAgent (Quality Assurance)
```

#### Key Files:
- `base_agent.py` - Abstract base class defining agent interface
- `claude_wrapper.py` - Claude CLI subprocess execution
- `pm_agent.py` - Product Manager implementation
- `architect_agent.py` - Architect implementation
- `engineer_agent.py` - Engineer implementation
- `qa_agent.py` - QA implementation (most complex, ~24KB)
- `env_manager.py` - Environment isolation per agent

### 3. Dashboard Service (`src/interfaces/`)

Streamlit-based web UI for human oversight and control.

#### Key File: `dashboard.py` (~1,300 lines)

#### Pages:
1. **Session Management** - Create/view/filter sessions, Kanban board
2. **Artifact Review** - View PRD, Tech Spec, Code artifacts
3. **Approval Interface** - Approve/reject with feedback
4. **Live Logs** - Real-time execution monitoring
5. **Metrics & Analytics** - Session statistics and quality signals
6. **GitHub Integration** - Repository connection and issue tracking
7. **Project Settings** - Per-project configuration
8. **Agent Account Management** - API keys, models, usage limits

### 4. Configuration System (`src/config/`)

YAML-based configuration with environment variable interpolation.

#### Files:
- `agent_settings.py` - Agent settings management
- `validator.py` - Configuration validation
- `config/development.yaml` - Development settings
- `config/production.yaml` - Production settings
- `config/testing.yaml` - Test settings

### 5. Persona System (`src/personas/`)

System prompts and templates for each agent persona.

#### Files:
- `pm_prompt.md` - Product Manager system prompt
- `architect_prompt.md` - Architect system prompt
- `engineer_prompt.md` - Engineer system prompt
- `qa_prompt.md` - QA system prompt
- `template_manager.py` - Jinja2 template engine

## Workflow Pipeline

### Four-Phase Development Pipeline:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT PIPELINE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐  │
│  │   PM     │────►│  ARCH    │────►│  HUMAN   │────►│   ENG    │  │
│  │  Phase   │     │  Phase   │     │   GATE   │     │  Phase   │  │
│  └──────────┘     └──────────┘     └──────────┘     └──────────┘  │
│       │                │                │                │          │
│       ▼                ▼                ▼                ▼          │
│   docs/PRD.md    docs/TECH_SPEC.md   Approval      Implementation  │
│                                       Required                      │
│                                                                      │
│                           ┌──────────┐                              │
│                           │    QA    │◄─────────────────┘          │
│                           │  Phase   │                              │
│                           └────┬─────┘                              │
│                                │                                     │
│                    ┌───────────┴───────────┐                        │
│                    │                       │                        │
│                    ▼                       ▼                        │
│              QA PASSED              QA FAILED                       │
│              (Complete)          (Iterate → ENG)                    │
│                                  Max 5 iterations                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Phase Details:

#### Phase 1: Product Manager (PM)
- **Input:** User mission statement
- **Output:** `docs/PRD.md` (Product Requirements Document)
- **Responsibilities:**
  - Gather and clarify requirements
  - Define scope and acceptance criteria
  - Create user stories

#### Phase 2: Architect (ARCH)
- **Input:** PRD from PM phase
- **Output:** `docs/TECH_SPEC.md` (Technical Specification)
- **Responsibilities:**
  - Design system architecture
  - Define technology stack
  - Create component diagrams
  - Specify interfaces and APIs

#### Phase 3: Human Gate
- **Input:** PRD + Tech Spec
- **Output:** Approval or feedback
- **Responsibilities:**
  - Human review of artifacts
  - Approve to proceed or request changes
  - Can send back to PM or ARCH

#### Phase 4: Engineer (ENG)
- **Input:** Approved PRD + Tech Spec
- **Output:** Implementation code + tests
- **Responsibilities:**
  - Implement code following spec
  - Write unit tests
  - Create scaffold scripts

#### Phase 5: QA
- **Input:** Implemented code
- **Output:** `docs/BUG_REPORT.md` or approval
- **Responsibilities:**
  - Run tests
  - Validate against requirements
  - Report bugs or approve

## State Management

### Session States:
```python
class SessionStatus(Enum):
    PENDING = "pending"           # Created, not started
    RUNNING = "running"           # Active execution
    AWAITING_APPROVAL = "awaiting_approval"  # Human gate
    COMPLETED = "completed"       # Successfully finished
    FAILED = "failed"            # Error occurred
    EXPIRED = "expired"          # TTL exceeded
```

### Agent State Schema (TypedDict):
```python
class AgentState(TypedDict):
    user_mission: str
    project_name: str
    work_dir: str
    current_phase: str
    qa_passed: bool
    iteration_count: int
    path_prd: str | None
    path_tech_spec: str | None
    path_scaffold_script: str | None
    path_bug_report: str | None
    files_created: list[str]
    errors: list[str]
    execution_log: list[str]
    prd_feedback: list[str]
    architectural_feedback: list[str]
```

## Data Flow

### Request Flow:
```
User Request
     │
     ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Dashboard  │────►│ Orchestrator│────►│  Database   │
│  (HTTP)     │     │  (Python)   │     │ (PostgreSQL)│
└─────────────┘     └──────┬──────┘     └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │ LangGraph   │
                   │ Workflow    │
                   └──────┬──────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         ┌────────┐  ┌────────┐  ┌────────┐
         │ Agent  │  │ Agent  │  │ Agent  │
         │ (CLI)  │  │ (CLI)  │  │ (CLI)  │
         └────────┘  └────────┘  └────────┘
```

## Security Considerations

### Authentication & Authorization:
- API keys per agent (isolation and tracking)
- Environment variable encryption for secrets
- Non-root Docker containers
- Volume mount restrictions

### Input Validation:
- Pydantic models for data validation
- SQL injection prevention (parameterized queries)
- Path traversal protection
- XSS prevention in dashboard

### Network Security:
- Internal Docker network isolation
- CORS protection
- XSRF protection for Streamlit

## Performance Considerations

### Scalability:
- **Horizontal:** Multiple orchestrator instances (requires shared DB)
- **Vertical:** Increase container resources
- **Sessions:** Default max 100 concurrent sessions

### Caching:
- Redis for session caching
- Streamlit `@st.cache_resource` for orchestrator instance
- File-based caching for artifacts

### Timeouts:
- Agent execution: 300s (5 minutes)
- Session TTL: 7 days
- Health check: 30s intervals

## Directory Structure

```
autonomous_software_studio/
├── src/
│   ├── orchestration/        # LangGraph control plane
│   │   ├── __init__.py
│   │   ├── orchestrator.py   # Main orchestration engine
│   │   ├── workflow.py       # LangGraph state machine
│   │   ├── state.py          # State management
│   │   ├── context_manager.py
│   │   └── sqlite_checkpointer.py
│   │
│   ├── wrappers/             # Agent implementations
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── claude_wrapper.py
│   │   ├── pm_agent.py
│   │   ├── architect_agent.py
│   │   ├── engineer_agent.py
│   │   ├── qa_agent.py
│   │   ├── env_manager.py
│   │   └── state.py
│   │
│   ├── personas/             # System prompts
│   │   ├── pm_prompt.md
│   │   ├── architect_prompt.md
│   │   ├── engineer_prompt.md
│   │   ├── qa_prompt.md
│   │   └── template_manager.py
│   │
│   ├── interfaces/           # UI
│   │   ├── __init__.py
│   │   └── dashboard.py
│   │
│   ├── config/               # Configuration
│   │   ├── __init__.py
│   │   ├── agent_settings.py
│   │   └── validator.py
│   │
│   └── mcp/                  # MCP integration
│       ├── __init__.py
│       └── server_manager.py
│
├── config/                   # Configuration files
│   ├── development.yaml
│   ├── production.yaml
│   ├── testing.yaml
│   ├── mcp_servers.json
│   └── profiles/
│       ├── pm/
│       ├── arch/
│       ├── eng/
│       └── qa/
│
├── docs/                     # Documentation
│   ├── internal/            # Internal docs
│   ├── api/                 # API reference
│   └── guides/              # User guides
│
├── tests/                    # Test suites
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── security/
│
├── scripts/                  # Utility scripts
│   ├── start-docker.sh
│   ├── init-db.sql
│   └── ...
│
├── data/                     # Runtime data
├── logs/                     # Execution logs
├── reports/                  # QA reports
├── projects/                 # Work directories
│
├── Dockerfile               # Orchestrator image
├── Dockerfile.dashboard     # Dashboard image
├── docker-compose.yml       # Service orchestration
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Project metadata
└── .env.template           # Environment template
```

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.11+ |
| Orchestration | LangGraph | 0.2.0+ |
| LLM Framework | LangChain | 0.3.0+ |
| Web UI | Streamlit | 1.40.0+ |
| Database | PostgreSQL | 16 |
| Cache | Redis | 7 |
| Container | Docker | 20.10+ |
| AI CLI | Claude Code | Latest |
| Monitoring | Prometheus | Latest |
| Visualization | Grafana | Latest |

## Integration Points

### External Services:
- **Anthropic API** - Claude model access
- **GitHub API** - Repository integration
- **MCP Servers** - Tool extensions

### Internal APIs:
- **Orchestrator HTTP** - Health/metrics endpoints
- **Dashboard Streamlit** - Web interface
- **Database** - PostgreSQL connections
- **Cache** - Redis connections

## Deployment Modes

### Development:
- SQLite database
- Local file system
- Single container
- Debug logging

### Production:
- PostgreSQL database
- Docker volumes
- Multi-container orchestration
- INFO logging
- Health checks
- Auto-restart

### Testing:
- In-memory database
- Mock agents
- Isolated environment
- Verbose logging
