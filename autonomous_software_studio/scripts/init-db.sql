-- =============================================================================
-- Autonomous Software Studio - Database Initialization Script
-- PostgreSQL schema for production deployment
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================================
-- Sessions Table - Core session tracking
-- =============================================================================
CREATE TABLE IF NOT EXISTS sessions (
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

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_phase ON sessions(current_phase);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_name);

-- =============================================================================
-- Checkpoints Table - LangGraph state persistence
-- =============================================================================
CREATE TABLE IF NOT EXISTS checkpoints (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(64) NOT NULL,
    checkpoint_id VARCHAR(64) NOT NULL,
    parent_checkpoint_id VARCHAR(64),
    checkpoint_data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(thread_id, checkpoint_id)
);

-- Indexes for checkpoint lookups
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread ON checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_parent ON checkpoints(parent_checkpoint_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_created ON checkpoints(created_at DESC);

-- =============================================================================
-- Artifacts Table - Track generated artifacts
-- =============================================================================
CREATE TABLE IF NOT EXISTS artifacts (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    artifact_type VARCHAR(50) NOT NULL,
    file_path TEXT NOT NULL,
    content_hash VARCHAR(64),
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for artifact queries
CREATE INDEX IF NOT EXISTS idx_artifacts_session ON artifacts(session_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type);

-- =============================================================================
-- Agent Executions Table - Track individual agent runs
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_executions (
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

-- Indexes for execution queries
CREATE INDEX IF NOT EXISTS idx_executions_session ON agent_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_executions_agent ON agent_executions(agent_type);
CREATE INDEX IF NOT EXISTS idx_executions_status ON agent_executions(status);
CREATE INDEX IF NOT EXISTS idx_executions_started ON agent_executions(started_at DESC);

-- =============================================================================
-- Metrics Table - Store aggregated metrics
-- =============================================================================
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL,
    labels JSONB DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for metrics queries
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded ON metrics(recorded_at DESC);

-- =============================================================================
-- Audit Log Table - Track important events
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    session_id VARCHAR(64),
    user_action VARCHAR(255),
    details JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for audit queries
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);

-- =============================================================================
-- Agent Settings Table - Store per-agent configuration
-- =============================================================================
CREATE TABLE IF NOT EXISTS agent_settings (
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

-- Insert default agent profiles
INSERT INTO agent_settings (profile_name, provider, model) VALUES
    ('pm', 'anthropic', 'claude-sonnet-4-20250514'),
    ('arch', 'anthropic', 'claude-sonnet-4-20250514'),
    ('eng', 'anthropic', 'claude-sonnet-4-20250514'),
    ('qa', 'anthropic', 'claude-sonnet-4-20250514')
ON CONFLICT (profile_name) DO NOTHING;

-- =============================================================================
-- Prompt Versions Table - Track prompt history
-- =============================================================================
CREATE TABLE IF NOT EXISTS prompt_versions (
    id SERIAL PRIMARY KEY,
    profile_name VARCHAR(50) NOT NULL,
    version_number INTEGER NOT NULL,
    prompt_content TEXT NOT NULL,
    note TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_name, version_number)
);

-- Index for prompt queries
CREATE INDEX IF NOT EXISTS idx_prompts_profile ON prompt_versions(profile_name);
CREATE INDEX IF NOT EXISTS idx_prompts_active ON prompt_versions(profile_name) WHERE is_active = TRUE;

-- =============================================================================
-- Functions and Triggers
-- =============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to sessions table
DROP TRIGGER IF EXISTS update_sessions_updated_at ON sessions;
CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to agent_settings table
DROP TRIGGER IF EXISTS update_agent_settings_updated_at ON agent_settings;
CREATE TRIGGER update_agent_settings_updated_at
    BEFORE UPDATE ON agent_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to reset daily usage counters
CREATE OR REPLACE FUNCTION reset_daily_usage()
RETURNS void AS $$
BEGIN
    UPDATE agent_settings
    SET usage_today = 0, last_reset_date = CURRENT_DATE
    WHERE last_reset_date < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Views for common queries
-- =============================================================================

-- Active sessions view
CREATE OR REPLACE VIEW active_sessions AS
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

-- Session metrics view
CREATE OR REPLACE VIEW session_metrics AS
SELECT
    status,
    COUNT(*) as count,
    AVG(iteration_count) as avg_iterations,
    COUNT(*) FILTER (WHERE qa_passed) as qa_passed_count
FROM sessions
GROUP BY status;

-- Agent performance view
CREATE OR REPLACE VIEW agent_performance AS
SELECT
    agent_type,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
    AVG(duration_seconds) as avg_duration_seconds,
    SUM(tokens_used) as total_tokens
FROM agent_executions
WHERE started_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY agent_type;

-- =============================================================================
-- Grants for application user (if needed)
-- =============================================================================
-- Uncomment and modify if using a separate application user
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO softwarestudio;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO softwarestudio;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO softwarestudio;

-- =============================================================================
-- Initialization complete
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Autonomous Software Studio database initialized successfully.';
END $$;
