# Database Schema Documentation

## Overview

Autonomous Software Studio uses PostgreSQL as its primary database in production, with SQLite available for development. The schema supports session management, checkpointing, artifact tracking, and agent execution history.

## Entity Relationship Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    sessions     │     │   checkpoints   │     │    artifacts    │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ PK session_id   │◄───┐│ PK id           │     │ PK id           │
│    user_mission │    ││    thread_id    │     │ FK session_id   │───┐
│    project_name │    ││    checkpoint_id│     │    artifact_type│   │
│    status       │    ││    parent_id    │     │    file_path    │   │
│    current_phase│    ││    data (JSONB) │     │    content_hash │   │
│    created_at   │    ││    metadata     │     │    version      │   │
│    updated_at   │    ││    created_at   │     │    created_at   │   │
│    iteration_cnt│    │└─────────────────┘     │    metadata     │   │
│    qa_passed    │    │                        └─────────────────┘   │
│    work_dir     │    │                                              │
│    state_json   │    │┌─────────────────┐     ┌─────────────────┐   │
│    metadata     │    ││agent_executions │     │  agent_settings │   │
└─────────────────┘    │├─────────────────┤     ├─────────────────┤   │
         │             ││ PK id           │     │ PK id           │   │
         │             ││ FK session_id   │─────│    profile_name │   │
         │             ││    agent_type   │     │    provider     │   │
         └─────────────┤│    started_at   │     │    model        │   │
                       ││    completed_at │     │    auth_type    │   │
                       ││    status       │     │    api_key_enc  │   │
                       ││    tokens_used  │     │    daily_limit  │   │
                       ││    duration_sec │     │    usage_today  │   │
                       ││    metadata     │     │    env_overrides│   │
                       │└─────────────────┘     └─────────────────┘   │
                       │                                              │
                       │┌─────────────────┐     ┌─────────────────┐   │
                       ││    audit_log    │     │ prompt_versions │   │
                       │├─────────────────┤     ├─────────────────┤   │
                       ││ PK id           │     │ PK id           │   │
                       ││    event_type   │     │    profile_name │   │
                       ││    session_id   │─────│    version_num  │   │
                       ││    user_action  │     │    content      │   │
                       ││    details      │     │    note         │   │
                       ││    ip_address   │     │    is_active    │   │
                       ││    created_at   │     │    created_at   │   │
                       │└─────────────────┘     └─────────────────┘   │
                       │                                              │
                       └──────────────────────────────────────────────┘
```

## Tables

### sessions

Core table for tracking development sessions.

```sql
CREATE TABLE sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    user_mission TEXT NOT NULL,
    project_name VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    current_phase VARCHAR(50) NOT NULL DEFAULT 'pm',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    iteration_count INTEGER DEFAULT 0,
    qa_passed BOOLEAN DEFAULT FALSE,
    work_dir TEXT,
    state_json JSONB,
    metadata JSONB DEFAULT '{}'::jsonb
);
```

**Columns:**

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `session_id` | VARCHAR(64) | No | - | Primary key, unique identifier |
| `user_mission` | TEXT | No | - | The mission/goal for the session |
| `project_name` | VARCHAR(255) | Yes | NULL | Optional project grouping |
| `status` | VARCHAR(50) | No | 'pending' | Session status |
| `current_phase` | VARCHAR(50) | No | 'pm' | Current execution phase |
| `created_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | Last update timestamp |
| `iteration_count` | INTEGER | No | 0 | QA iteration count |
| `qa_passed` | BOOLEAN | No | FALSE | Whether QA passed |
| `work_dir` | TEXT | Yes | NULL | Working directory path |
| `state_json` | JSONB | Yes | NULL | Full state snapshot |
| `metadata` | JSONB | No | '{}' | Additional metadata |

**Status Values:**
- `pending` - Session created, not started
- `running` - Active execution
- `awaiting_approval` - Waiting for human review
- `completed` - Successfully finished
- `failed` - Error occurred
- `expired` - TTL exceeded

**Phase Values:**
- `pm` - Product Manager phase
- `arch` - Architect phase
- `human_gate` - Human approval gate
- `eng` - Engineer phase
- `qa` - QA phase
- `complete` - Workflow complete

**Indexes:**
```sql
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_updated ON sessions(updated_at DESC);
CREATE INDEX idx_sessions_created ON sessions(created_at DESC);
CREATE INDEX idx_sessions_phase ON sessions(current_phase);
CREATE INDEX idx_sessions_project ON sessions(project_name);
```

---

### checkpoints

LangGraph state persistence for workflow recovery.

```sql
CREATE TABLE checkpoints (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(64) NOT NULL,
    checkpoint_id VARCHAR(64) NOT NULL,
    parent_checkpoint_id VARCHAR(64),
    checkpoint_data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(thread_id, checkpoint_id)
);
```

**Columns:**

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | No | Auto | Internal ID |
| `thread_id` | VARCHAR(64) | No | - | LangGraph thread ID |
| `checkpoint_id` | VARCHAR(64) | No | - | Checkpoint identifier |
| `parent_checkpoint_id` | VARCHAR(64) | Yes | NULL | Parent checkpoint |
| `checkpoint_data` | JSONB | No | - | Full state data |
| `metadata` | JSONB | No | '{}' | Checkpoint metadata |
| `created_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | Creation time |

**Indexes:**
```sql
CREATE INDEX idx_checkpoints_thread ON checkpoints(thread_id);
CREATE INDEX idx_checkpoints_parent ON checkpoints(parent_checkpoint_id);
CREATE INDEX idx_checkpoints_created ON checkpoints(created_at DESC);
```

---

### artifacts

Tracks generated artifacts (PRD, Tech Spec, Code).

```sql
CREATE TABLE artifacts (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    artifact_type VARCHAR(50) NOT NULL,
    file_path TEXT NOT NULL,
    content_hash VARCHAR(64),
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);
```

**Columns:**

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | No | Auto | Internal ID |
| `session_id` | VARCHAR(64) | No | - | Foreign key to sessions |
| `artifact_type` | VARCHAR(50) | No | - | Type of artifact |
| `file_path` | TEXT | No | - | Path to artifact file |
| `content_hash` | VARCHAR(64) | Yes | NULL | SHA256 hash |
| `version` | INTEGER | No | 1 | Version number |
| `created_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | Creation time |
| `metadata` | JSONB | No | '{}' | Additional metadata |

**Artifact Types:**
- `prd` - Product Requirements Document
- `tech_spec` - Technical Specification
- `scaffold` - Scaffold script
- `bug_report` - QA Bug Report
- `code` - Implementation code
- `test` - Test files

**Indexes:**
```sql
CREATE INDEX idx_artifacts_session ON artifacts(session_id);
CREATE INDEX idx_artifacts_type ON artifacts(artifact_type);
```

---

### agent_executions

Tracks individual agent runs for analytics.

```sql
CREATE TABLE agent_executions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'running',
    input_summary TEXT,
    output_summary TEXT,
    error_message TEXT,
    tokens_used INTEGER DEFAULT 0,
    duration_seconds NUMERIC(10, 2),
    metadata JSONB DEFAULT '{}'::jsonb
);
```

**Columns:**

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | No | Auto | Internal ID |
| `session_id` | VARCHAR(64) | No | - | Foreign key to sessions |
| `agent_type` | VARCHAR(50) | No | - | Agent persona |
| `started_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | Start time |
| `completed_at` | TIMESTAMPTZ | Yes | NULL | Completion time |
| `status` | VARCHAR(50) | No | 'running' | Execution status |
| `input_summary` | TEXT | Yes | NULL | Input summary |
| `output_summary` | TEXT | Yes | NULL | Output summary |
| `error_message` | TEXT | Yes | NULL | Error if failed |
| `tokens_used` | INTEGER | No | 0 | Token count |
| `duration_seconds` | NUMERIC | Yes | NULL | Execution duration |
| `metadata` | JSONB | No | '{}' | Additional metadata |

**Agent Types:**
- `pm` - Product Manager
- `arch` - Architect
- `eng` - Engineer
- `qa` - QA Engineer

**Indexes:**
```sql
CREATE INDEX idx_executions_session ON agent_executions(session_id);
CREATE INDEX idx_executions_agent ON agent_executions(agent_type);
CREATE INDEX idx_executions_status ON agent_executions(status);
CREATE INDEX idx_executions_started ON agent_executions(started_at DESC);
```

---

### agent_settings

Per-agent configuration and credentials.

```sql
CREATE TABLE agent_settings (
    id SERIAL PRIMARY KEY,
    profile_name VARCHAR(50) UNIQUE NOT NULL,
    provider VARCHAR(50) DEFAULT 'anthropic',
    model VARCHAR(100),
    auth_type VARCHAR(50) DEFAULT 'api_key',
    api_key_encrypted TEXT,
    daily_limit INTEGER DEFAULT 0,
    hard_limit BOOLEAN DEFAULT FALSE,
    usage_unit VARCHAR(20) DEFAULT 'runs',
    usage_today INTEGER DEFAULT 0,
    last_reset_date DATE DEFAULT CURRENT_DATE,
    env_overrides JSONB DEFAULT '{}'::jsonb,
    active_prompt_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | No | Auto | Internal ID |
| `profile_name` | VARCHAR(50) | No | - | Agent profile name |
| `provider` | VARCHAR(50) | No | 'anthropic' | LLM provider |
| `model` | VARCHAR(100) | Yes | NULL | Model identifier |
| `auth_type` | VARCHAR(50) | No | 'api_key' | Authentication type |
| `api_key_encrypted` | TEXT | Yes | NULL | Encrypted API key |
| `daily_limit` | INTEGER | No | 0 | Daily usage limit (0=unlimited) |
| `hard_limit` | BOOLEAN | No | FALSE | Enforce hard limit |
| `usage_unit` | VARCHAR(20) | No | 'runs' | Limit unit |
| `usage_today` | INTEGER | No | 0 | Today's usage |
| `last_reset_date` | DATE | No | CURRENT_DATE | Last reset date |
| `env_overrides` | JSONB | No | '{}' | Environment overrides |
| `active_prompt_path` | TEXT | Yes | NULL | Active prompt file |
| `created_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | Last update |

**Default Profiles:**
```sql
INSERT INTO agent_settings (profile_name, provider, model) VALUES
    ('pm', 'anthropic', 'claude-sonnet-4-20250514'),
    ('arch', 'anthropic', 'claude-sonnet-4-20250514'),
    ('eng', 'anthropic', 'claude-sonnet-4-20250514'),
    ('qa', 'anthropic', 'claude-sonnet-4-20250514');
```

---

### prompt_versions

Tracks prompt history for versioning.

```sql
CREATE TABLE prompt_versions (
    id SERIAL PRIMARY KEY,
    profile_name VARCHAR(50) NOT NULL,
    version_number INTEGER NOT NULL,
    prompt_content TEXT NOT NULL,
    note TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_name, version_number)
);
```

**Columns:**

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | No | Auto | Internal ID |
| `profile_name` | VARCHAR(50) | No | - | Agent profile |
| `version_number` | INTEGER | No | - | Version number |
| `prompt_content` | TEXT | No | - | Full prompt text |
| `note` | TEXT | Yes | NULL | Version note |
| `is_active` | BOOLEAN | No | FALSE | Currently active |
| `created_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | Creation time |

**Indexes:**
```sql
CREATE INDEX idx_prompts_profile ON prompt_versions(profile_name);
CREATE INDEX idx_prompts_active ON prompt_versions(profile_name) WHERE is_active = TRUE;
```

---

### audit_log

Audit trail for important events.

```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    session_id VARCHAR(64),
    user_action VARCHAR(255),
    details JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | No | Auto | Internal ID |
| `event_type` | VARCHAR(100) | No | - | Event type |
| `session_id` | VARCHAR(64) | Yes | NULL | Related session |
| `user_action` | VARCHAR(255) | Yes | NULL | User action |
| `details` | JSONB | No | '{}' | Event details |
| `ip_address` | INET | Yes | NULL | Client IP |
| `created_at` | TIMESTAMPTZ | No | CURRENT_TIMESTAMP | Event time |

**Event Types:**
- `session_created` - New session created
- `session_approved` - Session approved
- `session_rejected` - Session rejected
- `session_completed` - Session completed
- `session_failed` - Session failed
- `agent_started` - Agent execution started
- `agent_completed` - Agent execution completed
- `settings_changed` - Agent settings modified
- `prompt_updated` - Prompt version created

**Indexes:**
```sql
CREATE INDEX idx_audit_event ON audit_log(event_type);
CREATE INDEX idx_audit_session ON audit_log(session_id);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);
```

---

### metrics

Aggregated metrics storage.

```sql
CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL,
    labels JSONB DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
```sql
CREATE INDEX idx_metrics_name ON metrics(metric_name);
CREATE INDEX idx_metrics_recorded ON metrics(recorded_at DESC);
```

---

## Views

### active_sessions

Shows currently active sessions.

```sql
CREATE VIEW active_sessions AS
SELECT
    session_id,
    user_mission,
    project_name,
    status,
    current_phase,
    created_at,
    updated_at,
    iteration_count,
    qa_passed
FROM sessions
WHERE status IN ('pending', 'running', 'awaiting_approval')
ORDER BY updated_at DESC;
```

### session_metrics

Aggregated session statistics.

```sql
CREATE VIEW session_metrics AS
SELECT
    status,
    COUNT(*) as count,
    AVG(iteration_count) as avg_iterations,
    COUNT(*) FILTER (WHERE qa_passed) as qa_passed_count
FROM sessions
GROUP BY status;
```

### agent_performance

Agent performance over last 7 days.

```sql
CREATE VIEW agent_performance AS
SELECT
    agent_type,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
    AVG(duration_seconds) as avg_duration_seconds,
    SUM(tokens_used) as total_tokens
FROM agent_executions
WHERE started_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY agent_type;
```

---

## Triggers

### update_updated_at_column

Automatically updates `updated_at` timestamp.

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_settings_updated_at
    BEFORE UPDATE ON agent_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### reset_daily_usage

Resets daily usage counters.

```sql
CREATE OR REPLACE FUNCTION reset_daily_usage()
RETURNS void AS $$
BEGIN
    UPDATE agent_settings
    SET usage_today = 0, last_reset_date = CURRENT_DATE
    WHERE last_reset_date < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;
```

---

## Migration Notes

### SQLite to PostgreSQL

When migrating from SQLite (development) to PostgreSQL (production):

1. Export SQLite data:
```bash
sqlite3 data/orchestrator.db ".dump" > backup.sql
```

2. Convert types:
- `TEXT` → `TEXT` (no change)
- `INTEGER` → `INTEGER` (no change)
- `REAL` → `NUMERIC`
- `BLOB` → `BYTEA`

3. Import to PostgreSQL:
```bash
psql -U softwarestudio -d softwarestudio < backup.sql
```

### Schema Versioning

Track schema version in a dedicated table:

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description) VALUES (1, 'Initial schema');
```
