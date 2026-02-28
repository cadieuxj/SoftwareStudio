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
      total_sessions: 0, running_sessions: 0, awaiting_approval: 0,
      completed_sessions: 0, failed_sessions: 0, expired_sessions: 0,
      qa_passed_count: 0, average_qa_iterations: 0, status_breakdown: {},
    })
  }

  const [row] = await db
    .select({
      total: count(),
      running: sql<number>`count(*) filter (where status = 'running')`,
      awaiting_approval: sql<number>`count(*) filter (where status = 'awaiting_approval')`,
      completed: sql<number>`count(*) filter (where status = 'completed')`,
      failed: sql<number>`count(*) filter (where status = 'failed')`,
      expired: sql<number>`count(*) filter (where status = 'expired')`,
      qa_passed: sql<number>`count(*) filter (where qa_passed = true)`,
      avg_iterations: sql<number>`coalesce(avg(iteration_count), 0)`,
    })
    .from(sessions)
    .where(eq(sessions.orgId, org.id))

  return NextResponse.json({
    total_sessions: Number(row.total),
    running_sessions: Number(row.running),
    awaiting_approval: Number(row.awaiting_approval),
    completed_sessions: Number(row.completed),
    failed_sessions: Number(row.failed),
    expired_sessions: Number(row.expired),
    qa_passed_count: Number(row.qa_passed),
    average_qa_iterations: Math.round(Number(row.avg_iterations) * 10) / 10,
    status_breakdown: {},
  })
}
