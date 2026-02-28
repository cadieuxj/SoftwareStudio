import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { db, sessions, organizations } from '@/lib/db'
import { eq, and } from 'drizzle-orm'
import * as fs from 'fs'
import * as path from 'path'

export const runtime = 'nodejs'

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { userId, orgId: clerkOrgId } = await auth()
  if (!userId || !clerkOrgId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { id } = await params
  const limit = parseInt(req.nextUrl.searchParams.get('limit') ?? '100', 10)

  const [org] = await db
    .select({ id: organizations.id })
    .from(organizations)
    .where(eq(organizations.clerkOrgId, clerkOrgId))
    .limit(1)
  if (!org) return NextResponse.json([])

  const [session] = await db
    .select({ id: sessions.id, externalSessionId: sessions.externalSessionId })
    .from(sessions)
    .where(and(eq(sessions.id, id), eq(sessions.orgId, org.id)))
    .limit(1)
  if (!session) return NextResponse.json({ error: 'Not found' }, { status: 404 })

  // Attempt to read log file from Python orchestrator if available
  const logDir = process.env.LOG_DIR ?? path.join(process.cwd(), '..', '..', 'logs')
  const externalId = session.externalSessionId
  const logFile = externalId ? path.join(logDir, `${externalId}.log`) : null

  if (logFile && fs.existsSync(logFile)) {
    const lines = fs
      .readFileSync(logFile, 'utf-8')
      .split('\n')
      .filter(Boolean)
      .slice(-limit)
      .map((line, i) => {
        try {
          return JSON.parse(line)
        } catch {
          return { id: String(i), timestamp: new Date().toISOString(), level: 'info', message: line }
        }
      })
    return NextResponse.json(lines)
  }

  // Return empty list when no log file available
  return NextResponse.json([])
}
