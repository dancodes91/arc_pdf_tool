import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ThemeProvider } from '@/components/theme-provider'
import { Sidebar } from '@/components/nav/Sidebar'
import { Topbar } from '@/components/nav/Topbar'
import { Toaster } from '@/components/ui/toaster'

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
            <Sidebar />

            {/* Main content area */}
            <div className="flex flex-1 flex-col overflow-hidden pl-64">
              {/* Topbar */}
              <Topbar />

              {/* Page content */}
              <main className="flex-1 overflow-y-auto bg-background">
                {children}
              </main>
            </div>
          </div>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  )
}
