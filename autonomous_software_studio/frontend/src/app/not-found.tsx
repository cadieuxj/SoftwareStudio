'use client'

import Link from 'next/link'
import { FileQuestion, Home } from 'lucide-react'
import { Button } from '@/components/ui'

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center">
      <div className="inline-flex p-4 rounded-full bg-neon-magenta/10 border border-neon-magenta/30 mb-6">
        <FileQuestion className="h-12 w-12 text-neon-magenta" />
      </div>
      <h2 className="font-display text-4xl font-bold text-foreground mb-2">
        404
      </h2>
      <p className="text-xl text-foreground-muted mb-6">
        Page not found
      </p>
      <p className="text-foreground-subtle mb-8 text-center max-w-md">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Link href="/">
        <Button className="gap-2">
          <Home className="h-4 w-4" />
          Back to Dashboard
        </Button>
      </Link>
    </div>
  )
}
