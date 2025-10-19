import * as React from "react"

import { cn } from "@/lib/utils"

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-md border px-3 py-2 text-sm transition-colors duration-fast",
          "bg-input-bg text-input-text placeholder:text-input-placeholder",
          "border-input-border hover:border-input-border-hover",
          "focus:outline-none focus:ring-[3px] focus:ring-ring focus:ring-offset-0 focus:border-input-border-focus",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "file:border-0 file:bg-transparent file:text-sm file:font-medium",
          error && "border-input-error-border bg-input-error-bg focus:border-input-error-border focus:ring-error/20",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
