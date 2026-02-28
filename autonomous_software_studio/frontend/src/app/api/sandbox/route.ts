import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { createSandbox, type SupportedLanguage } from '@/lib/e2b'
import { db, sandboxSessions } from '@/lib/db'
import { eq } from 'drizzle-orm'

export const runtime = 'nodejs'
export const maxDuration = 30

/**
 * POST /api/sandbox — create a new E2B sandbox and persist it.
 */
export async function POST(req: NextRequest) {
  const { userId, orgId } = await auth()
  if (!userId || !orgId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  let body: { language?: SupportedLanguage; sessionId?: string; templateId?: string } = {}
  try {
    body = await req.json()
  } catch {
    // allow empty body
  }

  const { language = 'python', sessionId, templateId = 'base' } = body

  // Resolve org UUID from Clerk org ID
  const { organizations } = await import('@/lib/db/schema')
  const [org] = await db
    .select({ id: organizations.id })
    .from(organizations)
    .where(eq(organizations.clerkOrgId, orgId))
    .limit(1)

  if (!org) {
    return NextResponse.json({ error: 'Organization not found' }, { status: 404 })
  }

  // Create the E2B sandbox
  let e2bSandboxId: string | null = null
  try {
    const sandbox = await createSandbox(language)
    e2bSandboxId = sandbox.sandboxId
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'Failed to create sandbox' },
      { status: 500 }
    )
  }

  // Persist to DB
  const [record] = await db
    .insert(sandboxSessions)
    .values({
      orgId: org.id,
      sessionId: sessionId ?? null,
      createdByUserId: userId,
      e2bSandboxId,
      templateId,
      status: 'running',
      language,
      startedAt: new Date(),
    })
    .returning()

  return NextResponse.json({ sandboxId: record.id, e2bSandboxId, language, status: 'running' })
}

/**
 * GET /api/sandbox — list sandboxes for the org.
 */
export async function GET(_req: NextRequest) {
  const { orgId } = await auth()
  if (!orgId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { organizations } = await import('@/lib/db/schema')
  const [org] = await db
    .select({ id: organizations.id })
    .from(organizations)
    .where(eq(organizations.clerkOrgId, orgId))
    .limit(1)

  if (!org) return NextResponse.json([])

  const rows = await db
    .select()
    .from(sandboxSessions)
    .where(eq(sandboxSessions.orgId, org.id))

  return NextResponse.json(rows)
}
