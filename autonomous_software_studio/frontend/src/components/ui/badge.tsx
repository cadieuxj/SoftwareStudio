'use client'

import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-display font-semibold uppercase tracking-wider border transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-neon-cyan/20 border-neon-cyan/50 text-neon-cyan',
        secondary: 'bg-background-tertiary border-border text-foreground-muted',
        success: 'bg-neon-green/20 border-neon-green/50 text-neon-green',
        warning: 'bg-neon-orange/20 border-neon-orange/50 text-neon-orange',
        error: 'bg-red-500/20 border-red-500/50 text-red-400',
        info: 'bg-neon-blue/20 border-neon-blue/50 text-neon-blue',
        magenta: 'bg-neon-magenta/20 border-neon-magenta/50 text-neon-magenta',
        pending: 'bg-status-pending/20 border-status-pending/50 text-status-pending',
        running: 'bg-status-running/20 border-status-running/50 text-status-running',
        awaiting: 'bg-status-awaiting/20 border-status-awaiting/50 text-status-awaiting',
        completed: 'bg-status-completed/20 border-status-completed/50 text-status-completed',
        failed: 'bg-status-failed/20 border-status-failed/50 text-status-failed',
        expired: 'bg-status-expired/20 border-status-expired/50 text-status-expired',
      },
      size: {
        default: 'px-3 py-1 text-xs',
        sm: 'px-2 py-0.5 text-[10px]',
        lg: 'px-4 py-1.5 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  pulse?: boolean
}

function Badge({ className, variant, size, pulse, ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        badgeVariants({ variant, size }),
        pulse && 'animate-pulse-glow',
        className
      )}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
