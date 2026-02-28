import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { db, artifacts, sessions, organizations } from '@/lib/db'
import { eq, and } from 'drizzle-orm'

export const runtime = 'nodejs'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { userId, orgId: clerkOrgId } = await auth()
  if (!userId || !clerkOrgId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { id } = await params
  const [org] = await db
    .select({ id: organizations.id })
    .from(organizations)
    .where(eq(organizations.clerkOrgId, clerkOrgId))
    .limit(1)
  if (!org) return NextResponse.json({ error: 'Not found' }, { status: 404 })

  // Verify session belongs to org
  const [session] = await db
    .select({ id: sessions.id })
    .from(sessions)
    .where(and(eq(sessions.id, id), eq(sessions.orgId, org.id)))
    .limit(1)
  if (!session) return NextResponse.json({ error: 'Not found' }, { status: 404 })

  const [artifact] = await db
    .select()
    .from(artifacts)
    .where(eq(artifacts.sessionId, id))
    .limit(1)

  return NextResponse.json(
    artifact ?? { prd: null, techSpec: null, scaffoldScript: null, bugReport: null }
  )
}
