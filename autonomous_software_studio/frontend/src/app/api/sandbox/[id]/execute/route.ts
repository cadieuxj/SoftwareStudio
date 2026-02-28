import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { executeSandboxCode, type SupportedLanguage } from '@/lib/e2b'
import { db, sandboxSessions, executions } from '@/lib/db'
import { eq } from 'drizzle-orm'

export const runtime = 'nodejs'
export const maxDuration = 60

interface ExecuteRequest {
  code: string
  language?: SupportedLanguage
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { userId, orgId } = await auth()
  if (!userId || !orgId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { id } = await params

  let body: ExecuteRequest
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  if (!body.code?.trim()) {
    return NextResponse.json({ error: 'code is required' }, { status: 400 })
  }

  // Look up sandbox record
  const [sandbox] = await db
    .select()
    .from(sandboxSessions)
    .where(eq(sandboxSessions.id, id))
    .limit(1)

  if (!sandbox) {
    return NextResponse.json({ error: 'Sandbox not found' }, { status: 404 })
  }

  if (!sandbox.e2bSandboxId) {
    return NextResponse.json({ error: 'Sandbox has no active E2B session' }, { status: 409 })
  }

  if (sandbox.status !== 'running') {
    return NextResponse.json({ error: `Sandbox is ${sandbox.status}` }, { status: 409 })
  }

  const language = body.language ?? (sandbox.language as SupportedLanguage) ?? 'python'
  const startedAt = Date.now()

  const result = await executeSandboxCode(sandbox.e2bSandboxId, body.code, language)

  const durationMs = Date.now() - startedAt

  // Persist execution record
  const [exec] = await db
    .insert(executions)
    .values({
      sandboxSessionId: sandbox.id,
      orgId: sandbox.orgId,
      code: body.code,
      stdout: result.stdout,
      stderr: result.stderr,
      results: result.results,
      exitCode: result.exitCode ?? 0,
      durationMs,
      error: result.error ?? null,
    })
    .returning()

  return NextResponse.json({ ...result, executionId: exec.id, durationMs })
}
