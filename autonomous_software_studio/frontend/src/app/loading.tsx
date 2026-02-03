'use client'

import { Sparkles } from 'lucide-react'

export default function Loading() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center">
      <div className="relative">
        <Sparkles className="h-16 w-16 text-neon-cyan animate-pulse" />
        <div className="absolute inset-0 blur-xl bg-neon-cyan/30 animate-pulse" />
      </div>
      <div className="mt-8 flex items-center gap-2">
        <div className="spinner h-4 w-4" />
        <span className="font-display text-lg text-foreground-muted">Loading...</span>
      </div>
    </div>
  )
}
