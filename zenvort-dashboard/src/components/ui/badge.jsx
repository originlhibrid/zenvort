import * as React from 'react'
import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors cursor-default',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-white',
        secondary: 'border-transparent bg-secondary/20 text-secondary font-medium',
        accent: 'border-transparent bg-accent/20 text-accent font-medium',
        outline: 'border-border text-text-secondary',
        success: 'border-transparent bg-emerald-100 text-emerald-800 font-medium',
        processing: 'border-transparent bg-blue-100 text-blue-800 font-medium',
        pending: 'border-transparent bg-amber-100 text-amber-800 font-medium',
        destructive: 'border-transparent bg-red-100 text-red-800',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

function Badge({ className, variant, ...props }) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }