'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Upload,
  BookOpen,
  GitCompare,
  Download,
  Send,
  Settings,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

const navigationItems = [
  {
    name: 'Upload',
    href: '/upload',
    icon: Upload,
  },
  {
    name: 'Price Books',
    href: '/books',
    icon: BookOpen,
  },
  {
    name: 'Diff Review',
    href: '/diff',
    icon: GitCompare,
  },
  {
    name: 'Exports',
    href: '/export-center',
    icon: Download,
  },
  {
    name: 'Publish',
    href: '/publish',
    icon: Send,
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
  },
]

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-nav flex h-screen flex-col border-r border-border bg-nav-bg transition-all duration-standard',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo/Brand */}
      <div className="flex h-16 items-center justify-between border-b border-nav-border px-4">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <span className="text-sm font-semibold">ARC</span>
            </div>
            <span className="text-h3 font-semibold">Price Books</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="rounded-md p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-700 focus-ring"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-5 w-5" />
          ) : (
            <ChevronLeft className="h-5 w-5" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {navigationItems.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')
          const Icon = item.icon

          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors focus-ring',
                isActive
                  ? 'bg-nav-bg-active text-nav-text-active'
                  : 'text-nav-text hover:bg-neutral-100 dark:hover:bg-neutral-700',
                collapsed && 'justify-center'
              )}
              title={collapsed ? item.name : undefined}
            >
              <Icon className={cn('h-5 w-5 flex-shrink-0', collapsed && 'h-6 w-6')} />
              {!collapsed && <span>{item.name}</span>}
            </Link>
          )
        })}
      </nav>

      {/* Environment Badge (Dev/Prod) */}
      {!collapsed && (
        <div className="border-t border-nav-border p-3">
          <div className="rounded-md bg-info-light px-2.5 py-1.5 text-center">
            <span className="text-xs font-medium text-info-dark">
              {process.env.NODE_ENV === 'production' ? 'Production' : 'Development'}
            </span>
          </div>
        </div>
      )}
    </aside>
  )
}
