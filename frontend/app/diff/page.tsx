'use client'

import { GitCompare } from 'lucide-react'

export default function DiffPage() {
  return (
    <div className="container-max p-6">
      <h1 className="text-display font-medium mb-2">Diff Review</h1>
      <p className="text-muted-foreground mb-6">
        Review differences between price books
      </p>

      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <GitCompare className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">Diff Review page - Coming soon</p>
        </div>
      </div>
    </div>
  )
}
