// Session Types
export type SessionStatus =
  | 'pending'
  | 'running'
  | 'awaiting_approval'
  | 'completed'
  | 'failed'
  | 'expired'

export type SessionPhase =
  | 'pm'
  | 'arch'
  | 'human_gate'
  | 'engineer'
  | 'qa'
  | 'complete'
  | 'failed'

export interface Session {
  session_id: string
  mission: string
  project_name: string
  status: SessionStatus
  phase: SessionPhase
  created_at: string
  updated_at: string
  iteration_count: number
  qa_passed: boolean
  work_dir?: string
  errors?: string[]
}

export interface SessionArtifacts {
  prd?: string
  tech_spec?: string
  scaffold_script?: string
  bug_report?: string
  test_results?: TestResults
  files_created?: string[]
}

export interface TestResults {
  passed: number
  failed: number
  skipped: number
  total: number
  failures?: TestFailure[]
}

export interface TestFailure {
  test_name: string
  error: string
  severity: 'critical' | 'high' | 'medium' | 'low'
}

// Metrics Types
export interface Metrics {
  total_sessions: number
  running_sessions: number
  awaiting_approval: number
  completed_sessions: number
  failed_sessions: number
  expired_sessions: number
  qa_passed_count: number
  average_qa_iterations: number
  status_breakdown: Record<SessionStatus, number>
}

// Agent Types
export type AgentRole = 'pm' | 'architect' | 'engineer' | 'qa'

export type Provider =
  | 'anthropic'
  | 'claude_code'
  | 'groq'
  | 'openai'
  | 'azure_openai'
  | 'custom'

export type AuthType = 'api_key' | 'token' | 'none'

export type UsageLimitUnit = 'runs' | 'sessions' | 'minutes'

export interface AgentSettings {
  provider: Provider
  model: string
  auth_type: AuthType
  api_key?: string
  auth_token?: string
  auth_token_env_var?: string
  account_label?: string
  claude_profile_dir?: string
  daily_limit?: number
  daily_limit_unit?: UsageLimitUnit
  hard_limit?: boolean
  usage_today?: number
  last_reset?: string
  custom_env_vars?: Record<string, string>
  active_prompt_path?: string
  prompt_version_note?: string
}

export interface PromptVersion {
  path: string
  timestamp: string
  note?: string
  content?: string
}

export interface AgentConfig {
  pm: AgentSettings
  architect: AgentSettings
  engineer: AgentSettings
  qa: AgentSettings
}

// GitHub Types
export interface GitHubRepo {
  name: string
  full_name: string
  description?: string
  html_url: string
  clone_url: string
  ssh_url: string
  default_branch: string
  open_issues_count: number
  stargazers_count: number
  forks_count: number
  language?: string
  updated_at: string
  private: boolean
}

export interface GitHubIssue {
  number: number
  title: string
  body?: string
  state: 'open' | 'closed'
  labels: GitHubLabel[]
  assignees: GitHubUser[]
  created_at: string
  updated_at: string
  html_url: string
}

export interface GitHubLabel {
  name: string
  color: string
}

export interface GitHubUser {
  login: string
  avatar_url: string
}

export interface GitHubPR {
  number: number
  title: string
  body?: string
  state: 'open' | 'closed' | 'merged'
  head: { ref: string }
  base: { ref: string }
  created_at: string
  updated_at: string
  merged_at?: string
  html_url: string
  user: GitHubUser
}

// Project Types
export interface ProjectSettings {
  project_name: string
  session_id: string
  github_repo?: string
  work_dir: string
  auto_commit: boolean
  branch_prefix: string
  default_agent?: AgentRole
  agent_assignments: {
    pm: string
    architect: string
    engineer: string
    qa: string
  }
}

// MCP Types
export interface MCPServer {
  name: string
  command: string
  args?: string[]
  env?: Record<string, string>
  description?: string
}

export interface MCPConfig {
  servers: Record<string, MCPServer>
  agent_assignments: Record<AgentRole, string[]>
}

// Log Types
export interface LogEntry {
  timestamp: string
  level: 'debug' | 'info' | 'warning' | 'error'
  message: string
  agent?: AgentRole
  session_id?: string
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

// Form Types
export interface CreateSessionForm {
  mission: string
  project_name?: string
}

export interface FeedbackForm {
  feedback: string
  reject_phase: SessionPhase
}

export interface AgentSettingsForm extends AgentSettings {
  prompt_content?: string
}
