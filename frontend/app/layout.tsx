import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ThemeProvider } from '@/components/theme-provider'
import { SidebarProvider } from '@/components/nav/SidebarContext'
import { Sidebar } from '@/components/nav/Sidebar'
import { Topbar } from '@/components/nav/Topbar'
import { Toaster } from '@/components/ui/toaster'
import { LayoutContent } from '@/components/nav/LayoutContent'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'ARC Price Books',
  description: 'Professional price book parsing, diffing, and publishing system',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider defaultTheme="system" storageKey="arc-ui-theme">
          <div className="flex h-screen overflow-hidden">
            {/* Sidebar */}
            <SidebarProvider>
            <div className="flex flex-1 h-screen overflow-hidden">
              <Sidebar />
              <LayoutContent>
                {/* Topbar */}
                <Topbar />
                {/* Page content */}
                <main className="flex-1 overflow-y-auto bg-background">
                  {children}
                </main>
              </LayoutContent>
            </div>
            </SidebarProvider>
          </div>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  )
}
