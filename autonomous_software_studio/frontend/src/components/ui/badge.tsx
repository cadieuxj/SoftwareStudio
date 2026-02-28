'use client'

import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-neon-cyan/10 border-neon-cyan/20 text-neon-cyan',
        secondary: 'bg-white/[0.06] border-white/[0.08] text-foreground-muted',
        success: 'bg-neon-green/10 border-neon-green/20 text-neon-green',
        warning: 'bg-neon-orange/10 border-neon-orange/20 text-neon-orange',
        error: 'bg-red-500/10 border-red-500/20 text-red-400',
        info: 'bg-neon-blue/10 border-neon-blue/20 text-neon-blue',
        magenta: 'bg-neon-magenta/10 border-neon-magenta/20 text-neon-magenta',
        pending: 'bg-status-pending/10 border-status-pending/20 text-status-pending',
        running: 'bg-status-running/10 border-status-running/20 text-status-running',
        awaiting: 'bg-status-awaiting/10 border-status-awaiting/20 text-status-awaiting',
        completed: 'bg-status-completed/10 border-status-completed/20 text-status-completed',
        failed: 'bg-status-failed/10 border-status-failed/20 text-status-failed',
        expired: 'bg-status-expired/10 border-status-expired/20 text-status-expired',
      },
      size: {
        default: 'px-2.5 py-0.5 text-xs',
        sm: 'px-2 py-px text-[10px]',
        lg: 'px-3 py-1 text-sm',
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
