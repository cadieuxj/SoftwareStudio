import { auth } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'
import { db, sessions, organizations } from '@/lib/db'
import { eq, count, sql } from 'drizzle-orm'

export const runtime = 'nodejs'

export async function GET() {
  const { userId, orgId: clerkOrgId } = await auth()
  if (!userId || !clerkOrgId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const [org] = await db
    .select({ id: organizations.id })
    .from(organizations)
    .where(eq(organizations.clerkOrgId, clerkOrgId))
    .limit(1)

  if (!org) {
    return NextResponse.json({
      total: 0, running: 0, awaiting_approval: 0, completed: 0,
      failed: 0, qa_pass_rate: 0, avg_iterations: 0,
    })
  }

  const [row] = await db
    .select({
      total: count(),
      running: sql<number>`count(*) filter (where status = 'running')`,
      awaiting_approval: sql<number>`count(*) filter (where status = 'awaiting_approval')`,
      completed: sql<number>`count(*) filter (where status = 'completed')`,
      failed: sql<number>`count(*) filter (where status = 'failed')`,
      qa_passed: sql<number>`count(*) filter (where qa_passed = true)`,
      avg_iterations: sql<number>`coalesce(avg(iteration_count), 0)`,
    })
    .from(sessions)
    .where(eq(sessions.orgId, org.id))

  const qa_pass_rate =
    row.completed > 0 ? Math.round((Number(row.qa_passed) / Number(row.completed)) * 100) : 0

  return NextResponse.json({
    total: Number(row.total),
    running: Number(row.running),
    awaiting_approval: Number(row.awaiting_approval),
    completed: Number(row.completed),
    failed: Number(row.failed),
    qa_pass_rate,
    avg_iterations: Math.round(Number(row.avg_iterations) * 10) / 10,
  })
}
