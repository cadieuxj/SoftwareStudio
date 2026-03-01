import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { db, sessions, organizations } from '@/lib/db'
import { eq, and, desc } from 'drizzle-orm'
import type { SessionStatus, Session } from '@/types'

export const runtime = 'nodejs'

async function resolveOrgId(clerkOrgId: string) {
  const [org] = await db
    .select({ id: organizations.id })
    .from(organizations)
    .where(eq(organizations.clerkOrgId, clerkOrgId))
    .limit(1)
  return org?.id ?? null
}

// Map Drizzle camelCase rows to the snake_case Session shape used across the app
function toSession(row: typeof sessions.$inferSelect): Session {
  return {
    session_id: row.id,
    mission: row.mission,
    project_name: row.projectName ?? '',
    status: row.status as SessionStatus,
    phase: row.phase as Session['phase'],
    created_at: row.createdAt.toISOString(),
    updated_at: row.updatedAt.toISOString(),
    iteration_count: row.iterationCount,
    qa_passed: row.qaPassed,
    work_dir: row.workDir ?? undefined,
    errors: (row.errors as string[] | null) ?? undefined,
  }
}

export async function GET(req: NextRequest) {
  const { userId, orgId: clerkOrgId } = await auth()
  if (!userId || !clerkOrgId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const orgId = await resolveOrgId(clerkOrgId)
  if (!orgId) return NextResponse.json([])

  const status = req.nextUrl.searchParams.get('status') as SessionStatus | null
  const rows = await db
    .select()
    .from(sessions)
    .where(
      status
        ? and(eq(sessions.orgId, orgId), eq(sessions.status, status))
        : eq(sessions.orgId, orgId)
    )
    .orderBy(desc(sessions.createdAt))

  return NextResponse.json(rows.map(toSession))
}

export async function POST(req: NextRequest) {
  const { userId, orgId: clerkOrgId } = await auth()
  if (!userId || !clerkOrgId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const orgId = await resolveOrgId(clerkOrgId)
  if (!orgId) return NextResponse.json({ error: 'Organization not found' }, { status: 404 })

  const body = await req.json()
  if (!body.mission?.trim()) {
    return NextResponse.json({ error: 'mission is required' }, { status: 400 })
  }

  const [session] = await db
    .insert(sessions)
    .values({
      orgId,
      createdByUserId: userId,
      mission: body.mission.trim(),
      projectName: body.project_name?.trim() ?? null,
      status: 'pending',
      phase: 'pm',
    })
    .returning()

  return NextResponse.json(session, { status: 201 })
}
