import {
  pgTable,
  text,
  timestamp,
  integer,
  boolean,
  jsonb,
  uuid,
  pgEnum,
  index,
  uniqueIndex,
} from 'drizzle-orm/pg-core'

// ─── Enums ────────────────────────────────────────────────────────────────────

export const sessionStatusEnum = pgEnum('session_status', [
  'pending',
  'running',
  'awaiting_approval',
  'completed',
  'failed',
  'expired',
])

export const sessionPhaseEnum = pgEnum('session_phase', [
  'pm',
  'arch',
  'human_gate',
  'engineer',
  'qa',
  'complete',
  'failed',
])

export const agentRoleEnum = pgEnum('agent_role', ['pm', 'architect', 'engineer', 'qa'])

export const sandboxStatusEnum = pgEnum('sandbox_status', [
  'starting',
  'running',
  'stopped',
  'error',
])

// ─── Organizations (Tenants) ──────────────────────────────────────────────────

export const organizations = pgTable(
  'organizations',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    clerkOrgId: text('clerk_org_id').notNull(),
    name: text('name').notNull(),
    slug: text('slug').notNull(),
    plan: text('plan').notNull().default('free'),
    maxSessions: integer('max_sessions').notNull().default(10),
    maxSandboxes: integer('max_sandboxes').notNull().default(5),
    portkeyVirtualKeyId: text('portkey_virtual_key_id'),
    createdAt: timestamp('created_at').notNull().defaultNow(),
    updatedAt: timestamp('updated_at').notNull().defaultNow(),
  },
  (t) => [uniqueIndex('organizations_clerk_org_id_idx').on(t.clerkOrgId)]
)

// ─── Workspaces ───────────────────────────────────────────────────────────────

export const workspaces = pgTable(
  'workspaces',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    orgId: uuid('org_id')
      .notNull()
      .references(() => organizations.id, { onDelete: 'cascade' }),
    name: text('name').notNull(),
    description: text('description'),
    repoUrl: text('repo_url'),
    defaultBranch: text('default_branch').notNull().default('main'),
    createdByUserId: text('created_by_user_id').notNull(),
    createdAt: timestamp('created_at').notNull().defaultNow(),
    updatedAt: timestamp('updated_at').notNull().defaultNow(),
  },
  (t) => [index('workspaces_org_id_idx').on(t.orgId)]
)

// ─── Sessions ─────────────────────────────────────────────────────────────────

export const sessions = pgTable(
  'sessions',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    orgId: uuid('org_id')
      .notNull()
      .references(() => organizations.id, { onDelete: 'cascade' }),
    workspaceId: uuid('workspace_id').references(() => workspaces.id, { onDelete: 'set null' }),
    createdByUserId: text('created_by_user_id').notNull(),
    // Legacy Python orchestrator session ID (for integration)
    externalSessionId: text('external_session_id'),
    mission: text('mission').notNull(),
    projectName: text('project_name'),
    status: sessionStatusEnum('status').notNull().default('pending'),
    phase: sessionPhaseEnum('phase').notNull().default('pm'),
    iterationCount: integer('iteration_count').notNull().default(0),
    qaPassed: boolean('qa_passed').notNull().default(false),
    workDir: text('work_dir'),
    errors: jsonb('errors').$type<string[]>(),
    metadata: jsonb('metadata').$type<Record<string, unknown>>(),
    createdAt: timestamp('created_at').notNull().defaultNow(),
    updatedAt: timestamp('updated_at').notNull().defaultNow(),
  },
  (t) => [
    index('sessions_org_id_idx').on(t.orgId),
    index('sessions_status_idx').on(t.status),
    index('sessions_workspace_id_idx').on(t.workspaceId),
  ]
)

// ─── Artifacts ────────────────────────────────────────────────────────────────

export const artifacts = pgTable(
  'artifacts',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    sessionId: uuid('session_id')
      .notNull()
      .references(() => sessions.id, { onDelete: 'cascade' }),
    orgId: uuid('org_id')
      .notNull()
      .references(() => organizations.id, { onDelete: 'cascade' }),
    prd: text('prd'),
    techSpec: text('tech_spec'),
    scaffoldScript: text('scaffold_script'),
    bugReport: text('bug_report'),
    testResults: jsonb('test_results').$type<Record<string, unknown>>(),
    filesCreated: jsonb('files_created').$type<string[]>(),
    createdAt: timestamp('created_at').notNull().defaultNow(),
    updatedAt: timestamp('updated_at').notNull().defaultNow(),
  },
  (t) => [
    uniqueIndex('artifacts_session_id_idx').on(t.sessionId),
    index('artifacts_org_id_idx').on(t.orgId),
  ]
)

// ─── Agent Configurations ─────────────────────────────────────────────────────

export const agentConfigs = pgTable(
  'agent_configs',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    orgId: uuid('org_id')
      .notNull()
      .references(() => organizations.id, { onDelete: 'cascade' }),
    role: agentRoleEnum('role').notNull(),
    provider: text('provider').notNull().default('anthropic'),
    model: text('model').notNull().default('claude-opus-4-6'),
    authType: text('auth_type').notNull().default('api_key'),
    // Secrets stored encrypted or as env var references
    apiKeyRef: text('api_key_ref'),
    accountLabel: text('account_label'),
    claudeProfileDir: text('claude_profile_dir'),
    dailyLimit: integer('daily_limit'),
    dailyLimitUnit: text('daily_limit_unit').default('runs'),
    hardLimit: boolean('hard_limit').notNull().default(false),
    usageToday: integer('usage_today').notNull().default(0),
    customEnvVars: jsonb('custom_env_vars').$type<Record<string, string>>(),
    activePromptVersion: text('active_prompt_version'),
    createdAt: timestamp('created_at').notNull().defaultNow(),
    updatedAt: timestamp('updated_at').notNull().defaultNow(),
  },
  (t) => [
    uniqueIndex('agent_configs_org_role_idx').on(t.orgId, t.role),
    index('agent_configs_org_id_idx').on(t.orgId),
  ]
)

// ─── Sandbox Sessions (E2B) ───────────────────────────────────────────────────

export const sandboxSessions = pgTable(
  'sandbox_sessions',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    orgId: uuid('org_id')
      .notNull()
      .references(() => organizations.id, { onDelete: 'cascade' }),
    sessionId: uuid('session_id').references(() => sessions.id, { onDelete: 'set null' }),
    createdByUserId: text('created_by_user_id').notNull(),
    // E2B sandbox ID from the E2B API
    e2bSandboxId: text('e2b_sandbox_id'),
    templateId: text('template_id').notNull().default('base'),
    status: sandboxStatusEnum('status').notNull().default('starting'),
    language: text('language').notNull().default('python'),
    metadata: jsonb('metadata').$type<Record<string, unknown>>(),
    startedAt: timestamp('started_at'),
    stoppedAt: timestamp('stopped_at'),
    createdAt: timestamp('created_at').notNull().defaultNow(),
    updatedAt: timestamp('updated_at').notNull().defaultNow(),
  },
  (t) => [
    index('sandbox_sessions_org_id_idx').on(t.orgId),
    index('sandbox_sessions_session_id_idx').on(t.sessionId),
  ]
)

// ─── Execution History (E2B) ──────────────────────────────────────────────────

export const executions = pgTable(
  'executions',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    sandboxSessionId: uuid('sandbox_session_id')
      .notNull()
      .references(() => sandboxSessions.id, { onDelete: 'cascade' }),
    orgId: uuid('org_id')
      .notNull()
      .references(() => organizations.id, { onDelete: 'cascade' }),
    code: text('code').notNull(),
    stdout: text('stdout'),
    stderr: text('stderr'),
    results: jsonb('results').$type<{ type: string; data: unknown }[]>(),
    exitCode: integer('exit_code'),
    durationMs: integer('duration_ms'),
    error: text('error'),
    createdAt: timestamp('created_at').notNull().defaultNow(),
  },
  (t) => [
    index('executions_sandbox_session_id_idx').on(t.sandboxSessionId),
    index('executions_org_id_idx').on(t.orgId),
  ]
)

// ─── AI Traces (Portkey) ──────────────────────────────────────────────────────

export const aiTraces = pgTable(
  'ai_traces',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    orgId: uuid('org_id')
      .notNull()
      .references(() => organizations.id, { onDelete: 'cascade' }),
    sessionId: uuid('session_id').references(() => sessions.id, { onDelete: 'set null' }),
    portkeyTraceId: text('portkey_trace_id'),
    model: text('model').notNull(),
    provider: text('provider').notNull(),
    promptTokens: integer('prompt_tokens'),
    completionTokens: integer('completion_tokens'),
    totalTokens: integer('total_tokens'),
    costUsd: text('cost_usd'),
    latencyMs: integer('latency_ms'),
    status: text('status').notNull().default('success'),
    metadata: jsonb('metadata').$type<Record<string, unknown>>(),
    createdAt: timestamp('created_at').notNull().defaultNow(),
  },
  (t) => [
    index('ai_traces_org_id_idx').on(t.orgId),
    index('ai_traces_session_id_idx').on(t.sessionId),
  ]
)

// ─── Types ────────────────────────────────────────────────────────────────────

export type Organization = typeof organizations.$inferSelect
export type NewOrganization = typeof organizations.$inferInsert
export type Workspace = typeof workspaces.$inferSelect
export type NewWorkspace = typeof workspaces.$inferInsert
export type Session = typeof sessions.$inferSelect
export type NewSession = typeof sessions.$inferInsert
export type Artifact = typeof artifacts.$inferSelect
export type AgentConfig = typeof agentConfigs.$inferSelect
export type SandboxSession = typeof sandboxSessions.$inferSelect
export type NewSandboxSession = typeof sandboxSessions.$inferInsert
export type Execution = typeof executions.$inferSelect
export type NewExecution = typeof executions.$inferInsert
export type AiTrace = typeof aiTraces.$inferSelect
