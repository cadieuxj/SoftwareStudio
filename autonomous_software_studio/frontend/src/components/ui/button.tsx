'use client'

import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan/40 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]',
  {
    variants: {
      variant: {
        default:
          'bg-neon-cyan text-white hover:opacity-90',
        destructive:
          'bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20',
        success:
          'bg-neon-green/10 border border-neon-green/20 text-neon-green hover:bg-neon-green/20',
        outline:
          'border border-white/[0.1] bg-transparent text-foreground-muted hover:border-white/[0.18] hover:text-foreground hover:bg-white/[0.04]',
        secondary:
          'bg-white/[0.06] border border-white/[0.08] text-foreground-muted hover:bg-white/[0.09] hover:text-foreground',
        ghost:
          'text-foreground-muted hover:text-foreground hover:bg-white/[0.06]',
        link: 'text-neon-cyan underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2 rounded-lg',
        sm: 'h-8 px-3 py-1 rounded-md text-xs',
        lg: 'h-10 px-6 py-2 rounded-lg',
        xl: 'h-12 px-8 py-3 rounded-xl',
        icon: 'h-9 w-9 rounded-lg',
        'icon-sm': 'h-7 w-7 rounded-md',
        'icon-lg': 'h-11 w-11 rounded-lg',
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
