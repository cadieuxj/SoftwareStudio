'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: string
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, ...props }, ref) => {
    return (
      <div className="relative w-full">
        <textarea
          className={cn(
            'flex min-h-[120px] w-full rounded-lg border bg-background-secondary px-4 py-3',
            'text-foreground placeholder:text-foreground-subtle',
            'border-border focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20',
            'focus-visible:outline-none transition-all duration-300',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'font-body resize-y',
            error && 'border-red-500/50 focus:border-red-500 focus:ring-red-500/20',
            className
          )}
          ref={ref}
          {...props}
        />
        {error && (
          <p className="mt-1.5 text-sm text-red-400">{error}</p>
        )}
      </div>
    )
  }
)
Textarea.displayName = 'Textarea'

export { Textarea }
