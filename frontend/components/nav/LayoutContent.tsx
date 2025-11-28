'use client'

import { useSidebar } from './SidebarContext'
import { cn } from '@/lib/utils'

export function LayoutContent({ children }: { children: React.ReactNode }) {
  const { collapsed } = useSidebar()

  return (
    <div
      className={cn(
        'flex flex-1 flex-col overflow-hidden transition-all duration-standard',
        collapsed ? 'pl-16' : 'pl-64'
      )}
    >
      {children}
    </div>
  )
}
