import type {
  Session,
  SessionStatus,
  SessionArtifacts,
  AgentRole,
  AgentSettings,
  LogEntry,
  PromptVersion,
  Metrics,
  GitHubRepo,
  GitHubIssue,
  GitHubPR,
} from '@/types'

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

// ─── Sessions ────────────────────────────────────────────────────────────────

export const sessionsApi = {
  list: (status?: SessionStatus) =>
    request<Session[]>(`/sessions${status ? `?status=${status}` : ''}`),

  get: (id: string) => request<Session>(`/sessions/${id}`),

  create: (body: { mission: string; project_name?: string }) =>
    request<Session>('/sessions', { method: 'POST', body: JSON.stringify(body) }),

  approve: (id: string) =>
    request<Session>(`/sessions/${id}/approve`, { method: 'POST' }),

  reject: (id: string, body: { feedback: string; reject_phase: string }) =>
    request<Session>(`/sessions/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getArtifacts: (id: string) =>
    request<SessionArtifacts>(`/sessions/${id}/artifacts`),

  getLogs: (id: string, limit = 100) =>
    request<LogEntry[]>(`/sessions/${id}/logs?limit=${limit}`),
}

// ─── Metrics ─────────────────────────────────────────────────────────────────

export const metricsApi = {
  get: () => request<Metrics>('/metrics'),

  getHealth: () => request<{ status: string }>('/healthz'),
}

// ─── Agent Settings ───────────────────────────────────────────────────────────

export const agentSettingsApi = {
  getAll: () => request<Record<AgentRole, AgentSettings>>('/agents/settings'),

  get: (agent: AgentRole) =>
    request<AgentSettings>(`/agents/${agent}/settings`),

  update: (agent: AgentRole, settings: Partial<AgentSettings>) =>
    request<AgentSettings>(`/agents/${agent}/settings`, {
      method: 'PATCH',
      body: JSON.stringify(settings),
    }),

  getActivePrompt: (agent: AgentRole) =>
    request<{ content: string; version: string }>(`/agents/${agent}/prompt`),

  getPromptHistory: (agent: AgentRole) =>
    request<PromptVersion[]>(`/agents/${agent}/prompt/history`),

  savePromptVersion: (agent: AgentRole, content: string, note: string) =>
    request<{ version: string }>(`/agents/${agent}/prompt`, {
      method: 'POST',
      body: JSON.stringify({ content, note }),
    }),

  revertPrompt: (agent: AgentRole, path: string) =>
    request<{ content: string }>(`/agents/${agent}/prompt/revert`, {
      method: 'POST',
      body: JSON.stringify({ path }),
    }),

  resetPromptToDefault: (agent: AgentRole) =>
    request<{ content: string }>(`/agents/${agent}/prompt/reset`, {
      method: 'POST',
    }),

  resetUsage: (agent: AgentRole) =>
    request<void>(`/agents/${agent}/usage/reset`, { method: 'POST' }),
}

// ─── GitHub ───────────────────────────────────────────────────────────────────

export const githubApi = {
  checkAuth: () => request<{ authenticated: boolean; username?: string }>('/github/auth'),

  listRepos: (org?: string) =>
    request<GitHubRepo[]>(`/github/repos${org ? `?org=${org}` : ''}`),

  listIssues: (owner: string, repo: string, state = 'open') =>
    request<GitHubIssue[]>(`/github/repos/${owner}/${repo}/issues?state=${state}`),

  listPRs: (owner: string, repo: string, state = 'open') =>
    request<GitHubPR[]>(`/github/repos/${owner}/${repo}/pulls?state=${state}`),

  createSessionFromIssue: (owner: string, repo: string, issueNumber: number) =>
    request<Session>('/github/create-session', {
      method: 'POST',
      body: JSON.stringify({ owner, repo, issue_number: issueNumber }),
    }),
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const queryKeys = {
  sessions: ['sessions'] as const,
  session: (id: string) => ['sessions', id] as const,
  sessionArtifacts: (id: string) => ['sessions', id, 'artifacts'] as const,
  sessionLogs: (id: string) => ['sessions', id, 'logs'] as const,
  metrics: ['metrics'] as const,
  health: ['health'] as const,
  agentSettings: ['agents', 'settings'] as const,
  agentSetting: (agent: AgentRole) => ['agents', agent, 'settings'] as const,
  agentActivePrompt: (agent: AgentRole) => ['agents', agent, 'prompt'] as const,
  agentPromptHistory: (agent: AgentRole) => ['agents', agent, 'prompt', 'history'] as const,
  githubAuth: ['github', 'auth'] as const,
  githubRepos: (org?: string) => ['github', 'repos', org ?? 'all'] as const,
  githubIssues: (owner: string, repo: string) => ['github', owner, repo, 'issues'] as const,
  githubPRs: (owner: string, repo: string) => ['github', owner, repo, 'prs'] as const,
} as const
