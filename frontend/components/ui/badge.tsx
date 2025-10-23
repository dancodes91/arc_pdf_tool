import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "badge-base",
  {
    variants: {
      variant: {
        // Neutral (default)
        neutral: "bg-badge-neutral-bg text-badge-neutral-text",

        // Brand/Primary
        brand: "bg-badge-brand-bg text-badge-brand-text",

        // Status variants
        success: "bg-badge-success-bg text-badge-success-text",
        warning: "bg-badge-warning-bg text-badge-warning-text",
        error: "bg-badge-error-bg text-badge-error-text",

        // Outline style
        outline: "border border-border bg-transparent text-foreground",
      },
    },
    defaultVariants: {
      variant: "neutral",
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
