import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import { createPortkeyClient, buildPortkeyConfig, MODELS, type ModelTier } from '@/lib/portkey'

export const runtime = 'nodejs'
export const maxDuration = 60

interface ChatRequest {
  messages: { role: 'user' | 'assistant' | 'system'; content: string }[]
  model?: ModelTier
  sessionId?: string
  stream?: boolean
}

export async function POST(req: NextRequest) {
  const { userId, orgId } = await auth()
  if (!userId || !orgId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  let body: ChatRequest
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  const { messages, model = 'balanced', sessionId, stream = false } = body

  if (!messages?.length) {
    return NextResponse.json({ error: 'messages is required' }, { status: 400 })
  }

  try {
    const portkey = createPortkeyClient()
    const config = buildPortkeyConfig({ orgId, sessionId })

    if (stream) {
      const streamResponse = await portkey.chat.completions.create({
        model: MODELS[model],
        messages,
        stream: true,
        ...config,
      })

      const encoder = new TextEncoder()
      const readable = new ReadableStream({
        async start(controller) {
          for await (const chunk of streamResponse) {
            const delta = chunk.choices[0]?.delta?.content ?? ''
            if (delta) {
              controller.enqueue(encoder.encode(`data: ${JSON.stringify({ delta })}\n\n`))
            }
          }
          controller.enqueue(encoder.encode('data: [DONE]\n\n'))
          controller.close()
        },
      })

      return new Response(readable, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          Connection: 'keep-alive',
        },
      })
    }

    const completion = await portkey.chat.completions.create({
      model: MODELS[model],
      messages,
      ...config,
    })

    return NextResponse.json({
      content: completion.choices[0]?.message?.content ?? '',
      model: MODELS[model],
      usage: completion.usage,
    })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'AI gateway error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
