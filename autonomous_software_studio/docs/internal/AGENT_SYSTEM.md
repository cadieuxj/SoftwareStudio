# Agent System Documentation

## Overview

The Autonomous Software Studio uses a multi-agent architecture with four specialized Claude AI personas. Each agent has a specific role in the software development pipeline, working together through LangGraph orchestration.

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AGENT ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      BaseAgent (Abstract)                        │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │  - execute(mission, context) → AgentResult                │  │   │
│  │  │  - get_persona() → str                                     │  │   │
│  │  │  - get_system_prompt() → str                              │  │   │
│  │  │  - validate_output(result) → bool                         │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│              ┌─────────────────────┼─────────────────────┐             │
│              │                     │                     │             │
│              ▼                     ▼                     ▼             │
│  ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐   │
│  │   ClaudeCLIWrapper │ │    PMAgent        │ │   ArchitectAgent  │   │
│  │   (Core Execution) │ │   (PM Persona)    │ │   (Arch Persona)  │   │
│  └───────────────────┘ └───────────────────┘ └───────────────────┘   │
│                              │                     │                    │
│                              └──────────┬──────────┘                    │
│                                         │                               │
│              ┌───────────────────┐ ┌───────────────────┐               │
│              │   EngineerAgent   │ │     QAAgent       │               │
│              │   (Eng Persona)   │ │   (QA Persona)    │               │
│              └───────────────────┘ └───────────────────┘               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Agent Personas

### 1. Product Manager (PM) Agent

**Role:** Requirements gathering and PRD creation

**System Prompt Location:** `src/personas/pm_prompt.md`

**Responsibilities:**
- Analyze user mission and clarify requirements
- Create comprehensive Product Requirements Document (PRD)
- Define scope, acceptance criteria, and user stories
- Identify constraints and dependencies

**Input:**
```python
{
    "user_mission": "Build a REST API for user authentication",
    "project_name": "auth-service",
    "context": {}
}
```

**Output:**
```python
{
    "artifact_path": "docs/PRD.md",
    "summary": "Created PRD with 5 user stories and acceptance criteria",
    "success": True
}
```

**PRD Structure:**
```markdown
# Product Requirements Document

## 1. Overview
- Project description
- Goals and objectives

## 2. User Stories
- As a [user], I want [feature] so that [benefit]

## 3. Acceptance Criteria
- Measurable success criteria

## 4. Constraints
- Technical limitations
- Timeline considerations

## 5. Dependencies
- External systems
- Third-party services
```

---

### 2. Architect Agent

**Role:** Technical design and specification

**System Prompt Location:** `src/personas/architect_prompt.md`

**Responsibilities:**
- Design system architecture based on PRD
- Create technical specification document
- Define technology stack and components
- Specify APIs and interfaces

**Input:**
```python
{
    "prd_path": "docs/PRD.md",
    "prd_content": "...",
    "context": {
        "existing_tech": ["Python", "PostgreSQL"],
        "constraints": ["Must use REST"]
    }
}
```

**Output:**
```python
{
    "artifact_path": "docs/TECH_SPEC.md",
    "summary": "Created tech spec with microservices architecture",
    "success": True
}
```

**Tech Spec Structure:**
```markdown
# Technical Specification

## 1. Architecture Overview
- System diagram
- Component descriptions

## 2. Technology Stack
- Languages and frameworks
- Databases and storage

## 3. API Design
- Endpoints and methods
- Request/response schemas

## 4. Data Models
- Entity definitions
- Relationships

## 5. Security Considerations
- Authentication
- Authorization
- Data protection

## 6. Deployment
- Infrastructure requirements
- CI/CD considerations
```

---

### 3. Engineer Agent

**Role:** Implementation and coding

**System Prompt Location:** `src/personas/engineer_prompt.md`

**Responsibilities:**
- Implement code following technical specification
- Write unit tests for implemented code
- Create scaffold/setup scripts
- Follow coding best practices

**Input:**
```python
{
    "prd_path": "docs/PRD.md",
    "tech_spec_path": "docs/TECH_SPEC.md",
    "work_dir": "projects/session_123",
    "context": {
        "iteration": 1,
        "previous_feedback": None
    }
}
```

**Output:**
```python
{
    "files_created": [
        "src/main.py",
        "src/auth.py",
        "tests/test_auth.py"
    ],
    "scaffold_script": "scripts/setup.sh",
    "summary": "Implemented authentication module with 3 files",
    "success": True
}
```

**Code Standards:**
- Follow language-specific style guides
- Include docstrings and comments
- Write accompanying unit tests
- Handle errors appropriately

---

### 4. QA Agent

**Role:** Testing and validation

**System Prompt Location:** `src/personas/qa_prompt.md`

**Responsibilities:**
- Run implemented tests
- Validate against requirements (PRD)
- Validate against specification (Tech Spec)
- Report bugs or approve implementation

**Input:**
```python
{
    "prd_path": "docs/PRD.md",
    "tech_spec_path": "docs/TECH_SPEC.md",
    "work_dir": "projects/session_123",
    "files_created": ["src/main.py", "tests/test_main.py"]
}
```

**Output:**
```python
{
    "qa_passed": True,  # or False
    "bug_report_path": "docs/BUG_REPORT.md",  # if failed
    "test_results": {
        "passed": 15,
        "failed": 0,
        "skipped": 2
    },
    "summary": "All tests passed, implementation matches spec"
}
```

**Bug Report Structure:**
```markdown
# QA Bug Report

## Summary
Brief overview of issues found

## Critical Issues
- Issue 1: Description
  - Expected: ...
  - Actual: ...
  - Steps to reproduce: ...

## Minor Issues
- Issue 2: ...

## Test Results
- Passed: X
- Failed: Y
- Skipped: Z

## Recommendation
PASS / FAIL with suggested fixes
```

---

## Agent Execution Flow

### Claude CLI Wrapper

The core execution mechanism uses Claude CLI subprocess calls.

```python
class ClaudeCLIWrapper:
    """Executes Claude CLI commands in isolated environments."""

    def execute(
        self,
        prompt: str,
        work_dir: Path,
        env_vars: dict[str, str] = None,
        timeout: int = 300
    ) -> ExecutionResult:
        """
        Execute Claude CLI with the given prompt.

        Args:
            prompt: The prompt to send to Claude
            work_dir: Working directory for execution
            env_vars: Environment variables to set
            timeout: Execution timeout in seconds

        Returns:
            ExecutionResult with output and status
        """
```

### Execution Process

```
1. Prepare Environment
   ├── Create isolated work directory
   ├── Set environment variables
   └── Generate CLAUDE.md context file

2. Execute Agent
   ├── Build command: claude --prompt "..." --cwd work_dir
   ├── Run subprocess with timeout
   └── Capture stdout/stderr

3. Process Output
   ├── Parse execution result
   ├── Validate output format
   └── Extract artifacts

4. Update State
   ├── Record execution in database
   ├── Update session state
   └── Trigger next phase
```

---

## Environment Isolation

Each agent runs in an isolated environment to prevent conflicts.

### EnvironmentManager

```python
class EnvironmentManager:
    """Manages isolated environments for agent execution."""

    def create_environment(
        self,
        session_id: str,
        agent_type: str
    ) -> EnvironmentConfig:
        """Create isolated environment for agent."""

    def cleanup_environment(
        self,
        session_id: str
    ) -> None:
        """Clean up environment after execution."""
```

### Environment Variables

Each agent can have custom environment variables:

```python
# Per-agent API keys
ANTHROPIC_API_KEY_PM=sk-ant-pm-xxx
ANTHROPIC_API_KEY_ARCH=sk-ant-arch-xxx
ANTHROPIC_API_KEY_ENG=sk-ant-eng-xxx
ANTHROPIC_API_KEY_QA=sk-ant-qa-xxx

# Agent-specific overrides
CLAUDE_MODEL_PM=claude-sonnet-4-20250514
CLAUDE_MODEL_ENG=claude-opus-4-20250514
```

---

## Context Management

### CLAUDE.md Generation

Each agent receives a dynamically generated `CLAUDE.md` file with context.

```python
class ContextManager:
    """Generates CLAUDE.md context files for agents."""

    def generate_context(
        self,
        session_id: str,
        phase: str,
        state: AgentState
    ) -> str:
        """Generate CLAUDE.md content for the current phase."""
```

**CLAUDE.md Structure:**
```markdown
# Context for {{agent_name}}

## Mission
{{user_mission}}

## Project
{{project_name}}

## Current Phase
{{current_phase}}

## Previous Artifacts
{{#if prd_path}}
### PRD
{{prd_content}}
{{/if}}

{{#if tech_spec_path}}
### Technical Specification
{{tech_spec_content}}
{{/if}}

## Instructions
{{phase_specific_instructions}}

## Constraints
- Follow the provided specifications
- Output artifacts to specified locations
- Report any blockers or questions
```

---

## Prompt Versioning

Prompts can be versioned and managed through the dashboard.

### Prompt Storage

```
config/profiles/
├── pm/
│   ├── default_prompt.md
│   └── versions/
│       ├── v1_2024-01-01.md
│       └── v2_2024-06-15.md
├── arch/
│   └── ...
├── eng/
│   └── ...
└── qa/
    └── ...
```

### Version Management

```python
class AgentSettingsManager:
    """Manages agent settings and prompt versions."""

    def save_prompt_version(
        self,
        profile: str,
        content: str,
        note: str = None
    ) -> PromptVersion:
        """Save a new prompt version."""

    def get_active_prompt(
        self,
        profile: str
    ) -> str:
        """Get the currently active prompt."""

    def set_active_prompt(
        self,
        profile: str,
        version_path: Path
    ) -> None:
        """Set a specific version as active."""
```

---

## Usage Limits

Agents can have configurable usage limits.

### Limit Types

| Unit | Description |
|------|-------------|
| `runs` | Number of agent executions |
| `sessions` | Number of sessions started |
| `minutes` | Total execution time |

### Configuration

```python
agent_settings = {
    "pm": {
        "daily_limit": 100,
        "usage_unit": "runs",
        "hard_limit": False  # Warn but don't block
    },
    "eng": {
        "daily_limit": 50,
        "usage_unit": "runs",
        "hard_limit": True  # Block when exceeded
    }
}
```

### Reset Schedule

Usage counters reset daily at midnight UTC.

---

## Error Handling

### Execution Errors

```python
class AgentExecutionError(Exception):
    """Raised when agent execution fails."""
    pass

class AgentTimeoutError(AgentExecutionError):
    """Raised when agent execution times out."""
    pass

class AgentValidationError(AgentExecutionError):
    """Raised when agent output validation fails."""
    pass
```

### Retry Logic

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(AgentExecutionError)
)
def execute_with_retry(agent, context):
    return agent.execute(context)
```

---

## Extending Agents

### Creating a New Agent

1. **Create prompt file:**
```bash
touch src/personas/custom_prompt.md
```

2. **Implement agent class:**
```python
# src/wrappers/custom_agent.py
from src.wrappers.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    """Custom agent implementation."""

    @property
    def persona(self) -> str:
        return "custom"

    def get_system_prompt(self) -> str:
        return self._load_prompt("custom_prompt.md")

    def execute(self, context: AgentContext) -> AgentResult:
        # Custom execution logic
        pass
```

3. **Register in workflow:**
```python
# src/orchestration/workflow.py
from src.wrappers.custom_agent import CustomAgent

workflow.add_node("custom", CustomAgent().execute)
```

4. **Add configuration:**
```yaml
# config/profiles/custom/settings.yaml
provider: anthropic
model: claude-sonnet-4-20250514
```

---

## MCP Integration

Agents can use Model Context Protocol (MCP) servers for extended capabilities.

### Available MCP Servers

| Server | Agents | Capabilities |
|--------|--------|--------------|
| filesystem | arch, eng, qa | File operations |
| browser | pm, arch | Web browsing |
| github | pm, eng | GitHub operations |

### Configuration

```json
// config/mcp_servers.json
{
  "servers": {
    "filesystem": {
      "command": "mcp-server-filesystem",
      "args": ["--root", "/app/projects"]
    },
    "github": {
      "command": "mcp-server-github",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  },
  "agent_assignments": {
    "pm": ["browser", "github"],
    "arch": ["filesystem", "browser"],
    "eng": ["filesystem", "github"],
    "qa": ["filesystem"]
  }
}
```

---

## Performance Optimization

### Parallel Execution

Where possible, agents can execute in parallel:
- PM and initial context gathering
- Multiple file operations within Engineer phase

### Caching

- Prompt templates cached in memory
- Context files cached per session
- MCP server connections pooled

### Resource Management

```python
# Limit concurrent agent executions
MAX_CONCURRENT_AGENTS = 4
agent_semaphore = asyncio.Semaphore(MAX_CONCURRENT_AGENTS)

async def execute_agent(agent, context):
    async with agent_semaphore:
        return await agent.execute(context)
```
