import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-accent-blue text-white',
        secondary: 'border-transparent bg-surface-light text-gray-300',
        outline: 'border-border text-gray-300',
        critical: 'border-transparent bg-risk-critical/20 text-risk-critical border-risk-critical',
        high: 'border-transparent bg-risk-high/20 text-risk-high border-risk-high',
        medium: 'border-transparent bg-risk-medium/20 text-risk-medium border-risk-medium',
        low: 'border-transparent bg-risk-low/20 text-risk-low border-risk-low',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
