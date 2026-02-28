import 'server-only'
import { Sandbox } from '@e2b/code-interpreter'

// Re-export client-safe constants so server-side callers can use one import.
export type { SupportedLanguage } from './e2b-constants'

export interface ExecutionResult {
  stdout: string
  stderr: string
  results: { type: string; data: unknown }[]
  error?: string
  exitCode?: number
}

/**
 * Create a new E2B sandbox.
 * Only callable from Route Handlers or Server Components.
 */
export async function createSandbox(
  _language: import('./e2b-constants').SupportedLanguage = 'python',
  timeoutMs = 300_000
): Promise<Sandbox> {
  const apiKey = process.env.E2B_API_KEY
  if (!apiKey) throw new Error('E2B_API_KEY environment variable is not set')

  return Sandbox.create({ apiKey, timeoutMs })
}

/**
 * Execute code inside an existing sandbox (by E2B sandbox ID).
 */
export async function executeSandboxCode(
  sandboxId: string,
  code: string,
  language: import('./e2b-constants').SupportedLanguage = 'python'
): Promise<ExecutionResult> {
  const apiKey = process.env.E2B_API_KEY
  if (!apiKey) throw new Error('E2B_API_KEY environment variable is not set')

  const sandbox = await Sandbox.connect(sandboxId, { apiKey })

  try {
    const execution = await sandbox.runCode(code, { language })

    return {
      stdout: execution.logs.stdout.join('\n'),
      stderr: execution.logs.stderr.join('\n'),
      results: execution.results.map((r) => ({
        type: r.type ?? 'unknown',
        data: r.data,
      })),
      error: execution.error?.value,
      exitCode: 0,
    }
  } catch (err) {
    return {
      stdout: '',
      stderr: '',
      results: [],
      error: err instanceof Error ? err.message : String(err),
      exitCode: 1,
    }
  }
}

/**
 * Kill and clean up an E2B sandbox.
 */
export async function killSandbox(sandboxId: string): Promise<void> {
  const apiKey = process.env.E2B_API_KEY
  if (!apiKey) throw new Error('E2B_API_KEY environment variable is not set')

  const sandbox = await Sandbox.connect(sandboxId, { apiKey })
  await sandbox.kill()
}
