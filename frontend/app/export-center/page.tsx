'use client'

import { Download } from 'lucide-react'

export default function ExportsPage() {
  return (
    <div className="container-max p-6">
      <h1 className="text-display font-medium mb-2">Exports</h1>
      <p className="text-muted-foreground mb-6">
        Export price books to CSV, XLSX, or JSON
      </p>

      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Download className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">Exports page - Coming soon</p>
        </div>
      </div>
    </div>
  )
}
