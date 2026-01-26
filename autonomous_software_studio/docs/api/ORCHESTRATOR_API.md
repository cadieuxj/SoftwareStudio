# Orchestrator API Reference

## Overview

The Orchestrator is the central component that manages session lifecycle, agent coordination, and workflow execution. It exposes both a Python API for internal use and HTTP endpoints for health monitoring.

## HTTP Endpoints

### Health Check

```http
GET /healthz
```

Returns the health status of the orchestrator service.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2055-01-26T12:00:00Z"
}
```

**Status Codes:**
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is unhealthy

### Readiness Check

```http
GET /readyz
```

Returns whether the service is ready to accept requests.

**Response:**
```json
{
  "status": "ready",
  "database": "connected",
  "timestamp": "2055-01-26T12:00:00Z"
}
```

### Metrics

```http
GET /metrics
```

Returns Prometheus-formatted metrics.

**Response:**
```
# HELP sessions_total Total number of sessions
# TYPE sessions_total counter
sessions_total 150

# HELP sessions_active Current active sessions
# TYPE sessions_active gauge
sessions_active 12

# HELP approvals_total Total approvals
# TYPE approvals_total counter
approvals_total 85

# HELP rejections_total Total rejections
# TYPE rejections_total counter
rejections_total 23
```

---

## Python API

### Orchestrator Class

```python
from src.orchestration.orchestrator import Orchestrator, OrchestratorConfig

# Initialize with default config
orchestrator = Orchestrator()

# Initialize with custom config
config = OrchestratorConfig(
    db_path=Path("data/custom.db"),
    max_iterations=5,
    session_ttl_days=7,
    work_dir_base=Path("projects"),
    use_sqlite_checkpointer=True
)
orchestrator = Orchestrator(config=config)
```

---

### Session Management

#### start_new_session

Creates a new development session.

```python
def start_new_session(
    user_mission: str,
    project_name: str | None = None
) -> str
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_mission` | `str` | Yes | The mission/goal for the session |
| `project_name` | `str` | No | Optional project name for grouping |

**Returns:** `str` - The unique session ID

**Example:**
```python
session_id = orchestrator.start_new_session(
    user_mission="Build a REST API for user authentication",
    project_name="auth-service"
)
# Returns: "sess_abc123..."
```

**Raises:**
- `ValueError` - If mission is empty
- `RuntimeError` - If maximum sessions exceeded

---

#### get_session_status

Retrieves the current status of a session.

```python
def get_session_status(session_id: str) -> SessionInfo
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | `str` | Yes | The session identifier |

**Returns:** `SessionInfo` dataclass

```python
@dataclass
class SessionInfo:
    session_id: str
    user_mission: str
    project_name: str
    status: SessionStatus
    current_phase: str
    created_at: datetime
    updated_at: datetime
    iteration_count: int
    qa_passed: bool
    work_dir: str
```

**Example:**
```python
info = orchestrator.get_session_status("sess_abc123")
print(f"Status: {info.status.value}")
print(f"Phase: {info.current_phase}")
print(f"QA Passed: {info.qa_passed}")
```

**Raises:**
- `SessionNotFoundError` - If session doesn't exist

---

#### list_sessions

Lists all sessions with optional filtering.

```python
def list_sessions(
    status: SessionStatus | None = None,
    limit: int = 100
) -> list[SessionInfo]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | `SessionStatus` | No | Filter by status |
| `limit` | `int` | No | Maximum results (default: 100) |

**Returns:** `list[SessionInfo]`

**Example:**
```python
# Get all sessions
all_sessions = orchestrator.list_sessions()

# Get only running sessions
running = orchestrator.list_sessions(status=SessionStatus.RUNNING)

# Get recent 10 sessions
recent = orchestrator.list_sessions(limit=10)
```

---

### Approval Workflow

#### approve_and_continue

Approves the current state and continues execution.

```python
def approve_and_continue(session_id: str) -> SessionInfo
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | `str` | Yes | The session identifier |

**Returns:** `SessionInfo` - Updated session information

**Example:**
```python
info = orchestrator.approve_and_continue("sess_abc123")
print(f"Session continuing to: {info.current_phase}")
```

**Raises:**
- `SessionNotFoundError` - If session doesn't exist
- `InvalidOperationError` - If session is not awaiting approval

---

#### reject_and_iterate

Rejects the current state with feedback and sends back for iteration.

```python
def reject_and_iterate(
    session_id: str,
    feedback: str,
    reject_to: str = "architect"
) -> SessionInfo
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | `str` | Yes | The session identifier |
| `feedback` | `str` | Yes | Feedback explaining the rejection |
| `reject_to` | `str` | No | Phase to return to: "pm" or "architect" |

**Returns:** `SessionInfo` - Updated session information

**Example:**
```python
info = orchestrator.reject_and_iterate(
    session_id="sess_abc123",
    feedback="Please add rate limiting to the API spec",
    reject_to="architect"
)
```

**Raises:**
- `SessionNotFoundError` - If session doesn't exist
- `InvalidOperationError` - If session is not awaiting approval
- `ValueError` - If reject_to is invalid

---

### Artifacts

#### get_artifacts

Retrieves all artifacts for a session.

```python
def get_artifacts(session_id: str) -> dict[str, str | None]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | `str` | Yes | The session identifier |

**Returns:** Dictionary of artifact paths

```python
{
    "prd": "/path/to/docs/PRD.md",
    "tech_spec": "/path/to/docs/TECH_SPEC.md",
    "scaffold": "/path/to/scaffold.sh",
    "bug_report": "/path/to/docs/BUG_REPORT.md",
    "work_dir": "/path/to/projects/session_id"
}
```

**Example:**
```python
artifacts = orchestrator.get_artifacts("sess_abc123")
if artifacts["prd"]:
    with open(artifacts["prd"]) as f:
        prd_content = f.read()
```

**Raises:**
- `SessionNotFoundError` - If session doesn't exist

---

### Logging

#### get_recent_logs

Retrieves recent execution logs for a session.

```python
def get_recent_logs(
    session_id: str,
    lines: int = 50
) -> str
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | `str` | Yes | The session identifier |
| `lines` | `int` | No | Number of recent lines (default: 50) |

**Returns:** `str` - Log content

**Example:**
```python
logs = orchestrator.get_recent_logs("sess_abc123", lines=100)
print(logs)
```

---

### Session State

#### is_running

Checks if a session is currently executing.

```python
def is_running(session_id: str) -> bool
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | `str` | Yes | The session identifier |

**Returns:** `bool` - True if session is running

---

## Data Types

### SessionStatus Enum

```python
from src.orchestration.orchestrator import SessionStatus

class SessionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
```

### OrchestratorConfig

```python
from src.orchestration.orchestrator import OrchestratorConfig

@dataclass
class OrchestratorConfig:
    db_path: Path = Path("data/orchestrator.db")
    max_iterations: int = 5
    session_ttl_days: int = 7
    work_dir_base: Path = Path("projects")
    use_sqlite_checkpointer: bool = True
```

---

## Exceptions

### SessionNotFoundError

Raised when a session cannot be found.

```python
from src.orchestration.orchestrator import SessionNotFoundError

try:
    info = orchestrator.get_session_status("invalid_id")
except SessionNotFoundError as e:
    print(f"Session not found: {e}")
```

### InvalidOperationError

Raised when an operation is not valid for the current session state.

```python
from src.orchestration.orchestrator import InvalidOperationError

try:
    orchestrator.approve_and_continue("sess_running")
except InvalidOperationError as e:
    print(f"Cannot approve: {e}")
```

---

## Usage Examples

### Complete Workflow Example

```python
from src.orchestration.orchestrator import Orchestrator, SessionStatus

# Initialize
orchestrator = Orchestrator()

# Start a new session
session_id = orchestrator.start_new_session(
    user_mission="Create a CLI tool for file encryption",
    project_name="encrypt-cli"
)
print(f"Created session: {session_id}")

# Monitor progress
while True:
    info = orchestrator.get_session_status(session_id)
    print(f"Phase: {info.current_phase}, Status: {info.status.value}")

    if info.status == SessionStatus.AWAITING_APPROVAL:
        # Review artifacts
        artifacts = orchestrator.get_artifacts(session_id)
        print(f"PRD: {artifacts['prd']}")
        print(f"Tech Spec: {artifacts['tech_spec']}")

        # Approve or reject
        user_input = input("Approve? (y/n): ")
        if user_input.lower() == 'y':
            orchestrator.approve_and_continue(session_id)
        else:
            feedback = input("Feedback: ")
            orchestrator.reject_and_iterate(session_id, feedback)

    elif info.status in (SessionStatus.COMPLETED, SessionStatus.FAILED):
        break

    time.sleep(5)

# Final status
final_info = orchestrator.get_session_status(session_id)
print(f"Final Status: {final_info.status.value}")
print(f"QA Passed: {final_info.qa_passed}")
```

### Dashboard Integration Example

```python
import streamlit as st
from src.orchestration.orchestrator import Orchestrator

@st.cache_resource
def get_orchestrator():
    return Orchestrator()

orchestrator = get_orchestrator()

# Display sessions
sessions = orchestrator.list_sessions()
for session in sessions:
    st.write(f"{session.session_id}: {session.status.value}")

# Approval interface
if st.button("Approve"):
    orchestrator.approve_and_continue(selected_session_id)
    st.rerun()
```
