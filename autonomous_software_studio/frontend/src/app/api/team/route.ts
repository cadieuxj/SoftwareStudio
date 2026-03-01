import { auth, clerkClient } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'
import { db, sessions, organizations } from '@/lib/db'
import { eq, count, sql } from 'drizzle-orm'

export const runtime = 'nodejs'

export async function GET() {
  const { userId, orgId: clerkOrgId } = await auth()
  if (!userId || !clerkOrgId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // Fetch org members from Clerk
  const clerk = await clerkClient()
  const { data: memberships } = await clerk.organizations.getOrganizationMembershipList({
    organizationId: clerkOrgId,
    limit: 100,
  })

  // Resolve internal org id for DB queries
  const [org] = await db
    .select({ id: organizations.id })
    .from(organizations)
    .where(eq(organizations.clerkOrgId, clerkOrgId))
    .limit(1)

  // Count sessions per user for this org
  const sessionCounts: Record<string, number> = {}
  if (org) {
    const rows = await db
      .select({
        userId: sessions.createdByUserId,
        count: count(),
      })
      .from(sessions)
      .where(eq(sessions.orgId, org.id))
      .groupBy(sessions.createdByUserId)

    for (const row of rows) {
      sessionCounts[row.userId] = Number(row.count)
    }

    // Count latest session per user
    const latestRows = await db
      .select({
        userId: sessions.createdByUserId,
        lastActive: sql<string>`max(${sessions.updatedAt})`,
      })
      .from(sessions)
      .where(eq(sessions.orgId, org.id))
      .groupBy(sessions.createdByUserId)

    for (const row of latestRows) {
      sessionCounts[`${row.userId}_last`] = row.lastActive as unknown as number
    }
  }

  const members = memberships.map((m) => {
    const u = m.publicUserData
    const uid = u?.userId ?? ''
    return {
      id: uid,
      firstName: u?.firstName ?? null,
      lastName: u?.lastName ?? null,
      email: u?.identifier ?? null,
      avatarUrl: u?.imageUrl ?? null,
      role: m.role,
      joinedAt: m.createdAt ? new Date(m.createdAt).toISOString() : null,
      sessionCount: sessionCounts[uid] ?? 0,
      lastActive: (sessionCounts[`${uid}_last`] as unknown as string) ?? null,
    }
  })

  return NextResponse.json(members)
}
