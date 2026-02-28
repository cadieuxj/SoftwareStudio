import { Sandbox } from '@e2b/code-interpreter'

export type SupportedLanguage = 'python' | 'javascript' | 'typescript' | 'bash'

export interface ExecutionResult {
  stdout: string
  stderr: string
  results: { type: string; data: unknown }[]
  error?: string
  exitCode?: number
}

/**
 * Create a new E2B sandbox.
 * Should only be called in server-side code (Route Handlers).
 */
export async function createSandbox(
  language: SupportedLanguage = 'python',
  timeoutMs = 300_000
): Promise<Sandbox> {
  const apiKey = process.env.E2B_API_KEY
  if (!apiKey) throw new Error('E2B_API_KEY environment variable is not set')

  return Sandbox.create({
    apiKey,
    timeoutMs,
  })
}

/**
 * Execute code inside an existing sandbox (by sandbox ID).
 */
export async function executeSandboxCode(
  sandboxId: string,
  code: string,
  language: SupportedLanguage = 'python'
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

export const LANGUAGE_TEMPLATES: Record<SupportedLanguage, string> = {
  python: '# Python 3\nprint("Hello from Sovereign AI sandbox!")',
  javascript: '// Node.js\nconsole.log("Hello from Sovereign AI sandbox!")',
  typescript: '// TypeScript\nconst msg: string = "Hello from Sovereign AI sandbox!"\nconsole.log(msg)',
  bash: '#!/bin/bash\necho "Hello from Sovereign AI sandbox!"',
}
