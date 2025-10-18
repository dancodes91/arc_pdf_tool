'use client'

import { Send } from 'lucide-react'

export default function PublishPage() {
  return (
    <div className="container-max p-6">
      <h1 className="text-display font-medium mb-2">Publish</h1>
      <p className="text-muted-foreground mb-6">
        Publish price books to Baserow
      </p>

      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Send className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">Publish page - Coming soon</p>
        </div>
      </div>
    </div>
  )
}
