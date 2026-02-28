import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { db, sessions, organizations } from '@/lib/db'
import { eq, and } from 'drizzle-orm'

export const runtime = 'nodejs'

async function resolveOrgId(clerkOrgId: string) {
  const [org] = await db
    .select({ id: organizations.id })
    .from(organizations)
    .where(eq(organizations.clerkOrgId, clerkOrgId))
    .limit(1)
  return org?.id ?? null
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { userId, orgId: clerkOrgId } = await auth()
  if (!userId || !clerkOrgId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { id } = await params
  const orgId = await resolveOrgId(clerkOrgId)
  if (!orgId) return NextResponse.json({ error: 'Not found' }, { status: 404 })

  const [session] = await db
    .select()
    .from(sessions)
    .where(and(eq(sessions.id, id), eq(sessions.orgId, orgId)))
    .limit(1)

  if (!session) return NextResponse.json({ error: 'Not found' }, { status: 404 })
  return NextResponse.json(session)
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { userId, orgId: clerkOrgId } = await auth()
  if (!userId || !clerkOrgId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { id } = await params
  const orgId = await resolveOrgId(clerkOrgId)
  if (!orgId) return NextResponse.json({ error: 'Not found' }, { status: 404 })

  const body = await req.json()
  const [updated] = await db
    .update(sessions)
    .set({ ...body, updatedAt: new Date() })
    .where(and(eq(sessions.id, id), eq(sessions.orgId, orgId)))
    .returning()

  if (!updated) return NextResponse.json({ error: 'Not found' }, { status: 404 })
  return NextResponse.json(updated)
}
