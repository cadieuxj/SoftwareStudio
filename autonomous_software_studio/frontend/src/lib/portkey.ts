import Portkey from 'portkey-ai'

/**
 * Server-side Portkey client.
 * Only instantiate in Route Handlers or Server Components — never in client bundles.
 */
export function createPortkeyClient(virtualKey?: string) {
  const apiKey = process.env.PORTKEY_API_KEY
  if (!apiKey) {
    throw new Error('PORTKEY_API_KEY environment variable is not set')
  }

  return new Portkey({
    apiKey,
    virtualKey: virtualKey ?? process.env.PORTKEY_DEFAULT_VIRTUAL_KEY,
  })
}

/**
 * Build a Portkey config for routing, fallbacks, and observability.
 */
export function buildPortkeyConfig(options: {
  orgId: string
  sessionId?: string
  traceId?: string
  environment?: string
  budget?: number
}) {
  return {
    metadata: {
      org_id: options.orgId,
      session_id: options.sessionId ?? '',
      trace_id: options.traceId ?? '',
      environment: options.environment ?? process.env.NODE_ENV,
    },
    cache: { mode: 'simple' as const },
    retry: { attempts: 2, on_status_codes: [429, 500, 502, 503] },
    ...(options.budget ? { budget: { total_budget: options.budget } } : {}),
  }
}

/**
 * Supported model configurations for the gateway.
 */
export const MODELS = {
  fast: 'claude-haiku-4-5-20251001',
  balanced: 'claude-sonnet-4-6',
  powerful: 'claude-opus-4-6',
} as const

export type ModelTier = keyof typeof MODELS
