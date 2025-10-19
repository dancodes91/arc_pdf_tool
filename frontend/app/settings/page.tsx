'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { useTheme } from '@/components/theme-provider'
import { Sun, Moon, Monitor, Table, Keyboard } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const [density, setDensity] = useState<'dense' | 'comfortable'>('comfortable')

  // Save density preference to localStorage
  const handleDensityChange = (newDensity: 'dense' | 'comfortable') => {
    setDensity(newDensity)
    localStorage.setItem('table-density', newDensity)
  }

  // Load density preference on mount
  useEffect(() => {
    const saved = localStorage.getItem('table-density')
    if (saved === 'dense' || saved === 'comfortable') {
      setDensity(saved)
    }
  }, [])

  const themeOptions = [
    { value: 'light' as const, label: 'Light', icon: Sun, description: 'Clean and bright interface' },
    { value: 'dark' as const, label: 'Dark', icon: Moon, description: 'Easy on the eyes in low light' },
    { value: 'system' as const, label: 'System', icon: Monitor, description: 'Matches your OS preference' },
  ]

  const densityOptions = [
    { value: 'comfortable' as const, label: 'Comfortable', height: '52px', description: 'More spacing for better readability' },
    { value: 'dense' as const, label: 'Dense', height: '40-44px', description: 'Compact view to see more data' },
  ]

  const keyboardShortcuts = [
    { key: 'Tab / Shift+Tab', action: 'Navigate between interactive elements' },
    { key: 'Esc', action: 'Close dialogs and modals' },
    { key: 'Arrow keys', action: 'Navigate table cells and menu items' },
    { key: '/', action: 'Focus table search (when in table)' },
    { key: 'F', action: 'Open filters (when in table)' },
    { key: 'Enter', action: 'Activate focused element' },
  ]

  return (
    <div className="container-max p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-display font-medium mb-2">Settings</h1>
        <p className="text-muted-foreground">
          Configure your preferences and interface options
        </p>
      </div>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>
            Customize how the interface looks and feels
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Theme Selection */}
          <div className="space-y-3">
            <Label className="text-base">Color Theme</Label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {themeOptions.map((option) => {
                const Icon = option.icon
                const isActive = theme === option.value

                return (
                  <button
                    key={option.value}
                    onClick={() => setTheme(option.value)}
                    className={`flex items-start gap-3 p-4 border rounded-lg text-left transition-all ${
                      isActive
                        ? 'border-primary bg-primary/5 ring-2 ring-primary ring-offset-2'
                        : 'border-border hover:border-primary/50 hover:bg-muted/50'
                    }`}
                  >
                    <div className={`p-2 rounded-md ${
                      isActive ? 'bg-primary text-white' : 'bg-muted'
                    }`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{option.label}</span>
                        {isActive && <Badge variant="brand">Active</Badge>}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {option.description}
                      </p>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          <Separator />

          {/* Density Selection */}
          <div className="space-y-3">
            <Label className="text-base">Table Density</Label>
            <p className="text-sm text-muted-foreground">
              Controls the spacing in data tables across the application
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {densityOptions.map((option) => {
                const isActive = density === option.value

                return (
                  <button
                    key={option.value}
                    onClick={() => handleDensityChange(option.value)}
                    className={`flex items-start gap-3 p-4 border rounded-lg text-left transition-all ${
                      isActive
                        ? 'border-primary bg-primary/5 ring-2 ring-primary ring-offset-2'
                        : 'border-border hover:border-primary/50 hover:bg-muted/50'
                    }`}
                  >
                    <div className={`p-2 rounded-md ${
                      isActive ? 'bg-primary text-white' : 'bg-muted'
                    }`}>
                      <Table className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{option.label}</span>
                        {isActive && <Badge variant="brand">Active</Badge>}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {option.description}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1 font-mono">
                        Row height: {option.height}
                      </p>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Keyboard Shortcuts */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Keyboard className="h-5 w-5 text-muted-foreground" />
            <CardTitle>Keyboard Shortcuts</CardTitle>
          </div>
          <CardDescription>
            Improve your workflow with keyboard navigation
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {keyboardShortcuts.map((shortcut, index) => (
              <div
                key={index}
                className="flex items-center justify-between py-2 border-b last:border-0"
              >
                <span className="text-sm">{shortcut.action}</span>
                <kbd className="px-2 py-1 text-xs font-mono bg-muted border border-border rounded">
                  {shortcut.key}
                </kbd>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Data Persistence */}
      <Card>
        <CardHeader>
          <CardTitle>Data & Persistence</CardTitle>
          <CardDescription>
            Manage your local data and preferences
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Theme Preference</p>
              <p className="text-sm text-muted-foreground">Saved in browser local storage</p>
            </div>
            <Badge variant="neutral">Persisted</Badge>
          </div>

          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Table Density</p>
              <p className="text-sm text-muted-foreground">Saved in browser local storage</p>
            </div>
            <Badge variant="neutral">Persisted</Badge>
          </div>

          <Separator />

          <div className="pt-2">
            <Button
              variant="outline"
              onClick={() => {
                if (confirm('Are you sure you want to clear all settings? This will reset theme and density preferences.')) {
                  localStorage.removeItem('arc-ui-theme')
                  localStorage.removeItem('table-density')
                  setTheme('system')
                  setDensity('comfortable')
                  window.location.reload()
                }
              }}
            >
              Reset All Settings
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Accessibility */}
      <Card>
        <CardHeader>
          <CardTitle>Accessibility</CardTitle>
          <CardDescription>
            Features to improve usability for all users
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
            <CheckCircleIcon className="h-5 w-5 text-success flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium">AA Contrast Compliance</p>
              <p className="text-xs text-muted-foreground">All text meets WCAG AA standards (≥4.5:1 contrast ratio)</p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
            <CheckCircleIcon className="h-5 w-5 text-success flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium">Keyboard Navigation</p>
              <p className="text-xs text-muted-foreground">Full keyboard support with visible focus indicators</p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
            <CheckCircleIcon className="h-5 w-5 text-success flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium">Reduced Motion Support</p>
              <p className="text-xs text-muted-foreground">Respects prefers-reduced-motion system preference</p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
            <CheckCircleIcon className="h-5 w-5 text-success flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium">Color-Blind Safe</p>
              <p className="text-xs text-muted-foreground">Diff colors use icons + labels, not color alone</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}
