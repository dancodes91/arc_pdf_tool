import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors duration-fast focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        // Primary Button (filled)
        default:
          "bg-button-primary-bg text-button-primary-text hover:bg-button-primary-hover active:bg-button-primary-active shadow-sm",

        // Secondary Button (outline)
        outline:
          "border border-button-secondary-border bg-button-secondary-bg text-button-secondary-text hover:bg-button-secondary-hover-bg",

        // Tertiary Button (text/ghost)
        ghost:
          "text-button-tertiary-text hover:bg-button-tertiary-hover-bg",

        // Destructive Button
        destructive:
          "bg-button-destructive-bg text-button-destructive-text hover:bg-button-destructive-hover shadow-sm",

        // Link style
        link:
          "text-primary underline-offset-4 hover:underline",
      },
      size: {
        // S = 32px
        sm: "h-8 px-3 text-sm gap-2",

        // M = 40px (default)
        default: "h-10 px-4 gap-2",

        // L = 48px
        lg: "h-12 px-6 text-base gap-2",

        // Icon-only (square)
        icon: "h-10 w-10",
        "icon-sm": "h-8 w-8",
        "icon-lg": "h-12 w-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
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
  ({ className, variant, size, asChild = false, loading = false, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"

    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        {children}
      </Comp>
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
