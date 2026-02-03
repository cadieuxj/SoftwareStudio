'use client'

import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-display font-semibold uppercase tracking-wider ring-offset-background transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default:
          'bg-gradient-to-r from-neon-cyan/20 to-neon-magenta/20 border border-neon-cyan/50 text-neon-cyan hover:text-white hover:from-neon-cyan/30 hover:to-neon-magenta/30 hover:border-neon-cyan hover:shadow-neon-cyan',
        destructive:
          'bg-gradient-to-r from-red-500/20 to-neon-orange/20 border border-red-500/50 text-red-400 hover:text-white hover:from-red-500/30 hover:to-neon-orange/30 hover:border-red-500 hover:shadow-neon-orange',
        success:
          'bg-gradient-to-r from-neon-green/20 to-neon-cyan/20 border border-neon-green/50 text-neon-green hover:text-white hover:from-neon-green/30 hover:to-neon-cyan/30 hover:border-neon-green hover:shadow-neon-green',
        outline:
          'border border-border bg-transparent text-foreground-muted hover:border-neon-cyan/50 hover:text-foreground hover:bg-background-secondary',
        secondary:
          'bg-background-tertiary border border-border text-foreground-muted hover:text-foreground hover:border-foreground-muted hover:bg-background-secondary',
        ghost:
          'text-foreground-muted hover:text-foreground hover:bg-background-secondary',
        link: 'text-neon-cyan underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-11 px-6 py-2 rounded-lg',
        sm: 'h-9 px-4 py-1 rounded-md text-xs',
        lg: 'h-12 px-8 py-3 rounded-lg text-base',
        xl: 'h-14 px-10 py-4 rounded-xl text-lg',
        icon: 'h-10 w-10 rounded-lg',
        'icon-sm': 'h-8 w-8 rounded-md',
        'icon-lg': 'h-12 w-12 rounded-lg',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <>
            <span className="spinner h-4 w-4" />
            <span>Processing...</span>
          </>
        ) : (
          children
        )}
      </Comp>
    )
  }
)
Button.displayName = 'Button'

export { Button, buttonVariants }
