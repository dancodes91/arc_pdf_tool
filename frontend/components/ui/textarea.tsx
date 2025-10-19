import * as React from "react"

import { cn } from "@/lib/utils"

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[80px] w-full rounded-md border px-3 py-2 text-sm transition-colors duration-fast",
          "bg-input-bg text-input-text placeholder:text-input-placeholder",
          "border-input-border hover:border-input-border-hover",
          "focus:outline-none focus:ring-[3px] focus:ring-ring focus:ring-offset-0 focus:border-input-border-focus",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "resize-vertical",
          error && "border-input-error-border bg-input-error-bg focus:border-input-error-border focus:ring-error/20",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

export { Textarea }
