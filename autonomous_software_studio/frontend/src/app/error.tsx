'use client'

import { useEffect } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center">
      <div className="inline-flex p-4 rounded-full bg-red-500/10 border border-red-500/30 mb-6">
        <AlertCircle className="h-12 w-12 text-red-400" />
      </div>
      <h2 className="font-display text-2xl font-bold text-foreground mb-2">
        Something went wrong
      </h2>
      <p className="text-foreground-muted mb-6 text-center max-w-md">
        {error.message || 'An unexpected error occurred. Please try again.'}
      </p>
      <Button onClick={reset} className="gap-2">
        <RefreshCw className="h-4 w-4" />
        Try Again
      </Button>
    </div>
  )
}
