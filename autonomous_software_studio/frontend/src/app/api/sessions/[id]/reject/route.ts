import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { db, sessions, organizations } from '@/lib/db'
import { eq, and } from 'drizzle-orm'
import type { SessionPhase } from '@/types'

export const runtime = 'nodejs'

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { userId, orgId: clerkOrgId } = await auth()
  if (!userId || !clerkOrgId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { id } = await params
  const body: { feedback: string; reject_phase: SessionPhase } = await req.json()

  if (!body.feedback?.trim()) {
    return NextResponse.json({ error: 'feedback is required' }, { status: 400 })
  }

  const [org] = await db
    .select({ id: organizations.id })
    .from(organizations)
    .where(eq(organizations.clerkOrgId, clerkOrgId))
    .limit(1)
  if (!org) return NextResponse.json({ error: 'Not found' }, { status: 404 })

  const [session] = await db
    .select()
    .from(sessions)
    .where(and(eq(sessions.id, id), eq(sessions.orgId, org.id)))
    .limit(1)

  if (!session) return NextResponse.json({ error: 'Not found' }, { status: 404 })
  if (session.status !== 'awaiting_approval') {
    return NextResponse.json({ error: 'Session is not awaiting approval' }, { status: 409 })
  }

  const targetPhase: SessionPhase = body.reject_phase ?? 'pm'
  const [updated] = await db
    .update(sessions)
    .set({
      status: 'running',
      phase: targetPhase,
      metadata: { ...(session.metadata ?? {}), rejection_feedback: body.feedback },
      updatedAt: new Date(),
    })
    .where(eq(sessions.id, id))
    .returning()

  return NextResponse.json(updated)
}
