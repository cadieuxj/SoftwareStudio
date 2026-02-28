import { NextRequest, NextResponse } from 'next/server'
import { Webhook } from 'svix'
import { db, organizations } from '@/lib/db'
import { eq } from 'drizzle-orm'

export const runtime = 'nodejs'

interface ClerkOrganizationEvent {
  type: string
  data: {
    id: string
    name: string
    slug: string
  }
}

export async function POST(req: NextRequest) {
  const secret = process.env.CLERK_WEBHOOK_SECRET
  if (!secret) {
    return NextResponse.json({ error: 'Webhook secret not configured' }, { status: 500 })
  }

  // Verify signature via svix
  const payload = await req.text()
  const headers = {
    'svix-id': req.headers.get('svix-id') ?? '',
    'svix-timestamp': req.headers.get('svix-timestamp') ?? '',
    'svix-signature': req.headers.get('svix-signature') ?? '',
  }

  let event: ClerkOrganizationEvent
  try {
    const wh = new Webhook(secret)
    event = wh.verify(payload, headers) as ClerkOrganizationEvent
  } catch {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 })
  }

  const { type, data } = event

  if (type === 'organization.created') {
    await db
      .insert(organizations)
      .values({ clerkOrgId: data.id, name: data.name, slug: data.slug })
      .onConflictDoNothing()
  }

  if (type === 'organization.updated') {
    await db
      .update(organizations)
      .set({ name: data.name, slug: data.slug, updatedAt: new Date() })
      .where(eq(organizations.clerkOrgId, data.id))
  }

  if (type === 'organization.deleted') {
    await db
      .delete(organizations)
      .where(eq(organizations.clerkOrgId, data.id))
  }

  return NextResponse.json({ received: true })
}
