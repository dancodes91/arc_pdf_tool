'use client'

import { Search, Upload, Download, Moon, Sun, Monitor } from 'lucide-react'
import { useTheme } from '@/components/theme-provider'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import Link from 'next/link'

export function Topbar() {
  const { theme, setTheme } = useTheme()

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-border bg-background px-6">
      {/* Global Search */}
      <div className="flex flex-1 items-center gap-4">
        <div className="relative max-w-md flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            placeholder="Search price books, items..."
            className="h-10 w-full rounded-md border border-input bg-background pl-10 pr-4 text-sm focus-ring focus:border-input-border-focus"
          />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex items-center gap-2">
        <Link href="/upload">
          <Button size="sm">
            <Upload className="mr-2 h-4 w-4" />
            Upload
          </Button>
        </Link>

        <Link href="/export-center">
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </Link>

        {/* Theme Toggle */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              {theme === 'light' && <Sun className="h-4 w-4" />}
              {theme === 'dark' && <Moon className="h-4 w-4" />}
              {theme === 'system' && <Monitor className="h-4 w-4" />}
              <span className="sr-only">Toggle theme</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setTheme('light')}>
              <Sun className="mr-2 h-4 w-4" />
              Light
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme('dark')}>
              <Moon className="mr-2 h-4 w-4" />
              Dark
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme('system')}>
              <Monitor className="mr-2 h-4 w-4" />
              System
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
