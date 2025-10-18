'use client'

import { FileText } from 'lucide-react'

export default function BooksPage() {
  return (
    <div className="container-max p-6">
      <h1 className="text-display font-medium mb-2">Price Books</h1>
      <p className="text-muted-foreground mb-6">
        Browse and manage your parsed price books
      </p>

      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <FileText className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">Price Books page - Coming soon</p>
        </div>
      </div>
    </div>
  )
}
