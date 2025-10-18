# ARC Price Books - Frontend

Professional admin UI for price book parsing, diffing, and publishing built with Next.js 14, React, and Tailwind CSS.

## 🎨 Design System

This application follows the **ARC UI Design Guide v1.0** with a comprehensive design token system.

### Design Tokens Implemented
- ✅ **Typography**: Display, H1-H3, body-16, body-14, mono-13 scales
- ✅ **Colors**: Full semantic system with AA contrast compliance
- ✅ **Spacing**: 4px base unit with consistent scales
- ✅ **Motion**: 120-320ms transitions with proper easing
- ✅ **Dark Mode**: Complete light/dark theme support
- ✅ **Accessibility**: 3px focus rings, keyboard nav, reduced motion support

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn
- Backend API running (Flask on port 5000)

### Installation

```bash
# Install dependencies
npm install

# Set up environment
cp .env.local.example .env.local
# Edit .env.local and set NEXT_PUBLIC_API_URL

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Type checking
npm run typecheck

# Linting
npm run lint
```

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

For production, update to your deployed backend URL.

## 📁 Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── page.tsx           # Dashboard (/)
│   ├── upload/            # Upload wizard (/upload)
│   ├── books/             # Price Books (/books)
│   ├── diff/              # Diff Review (/diff)
│   ├── export-center/     # Exports (/export-center)
│   ├── publish/           # Publish (/publish)
│   ├── settings/          # Settings (/settings)
│   ├── layout.tsx         # Root layout with shell
│   └── globals.css        # Global styles + token imports
├── components/
│   ├── nav/               # Navigation (Sidebar, Topbar, Breadcrumbs)
│   ├── ui/                # Core UI components
│   └── theme-provider.tsx # Theme context provider
├── styles/
│   ├── tokens.css         # Design tokens (colors, spacing, etc.)
│   ├── semantic.css       # Semantic color aliases
│   └── dark.css           # Dark theme overrides
├── lib/
│   ├── stores/            # Zustand state management
│   └── utils.ts           # Utility functions
└── hooks/
    └── use-toast.ts       # Toast notifications
```

## 🎯 Features Implemented

### ✅ Core Infrastructure
- [x] Design token system (tokens, semantic, dark mode)
- [x] App shell with collapsible sidebar
- [x] Topbar with global search and theme toggle
- [x] ThemeProvider (light/dark/system)
- [x] Toast notification system
- [x] Responsive layout (max-width 1280px)

### ✅ Pages Completed

#### Dashboard (/)
- KPI cards (Total Books, Products, Completed, Processing)
- Recent price books list with status badges
- Quick action cards
- Empty state with CTA
- Error alerts

#### Upload (/upload)
**3-Step Wizard:**
1. Select manufacturer + drag-drop PDF upload
2. Parse progress with live stats, logs, and ETA
3. Summary with KPIs and action buttons

Features:
- Visual step indicators
- Drag & drop with scale animation
- Collapsible live parse log
- Success/error states
- File size validation

#### Settings (/settings)
- Theme switcher (Light/Dark/System) with persistence
- Table density toggle (Comfortable/Dense)
- Keyboard shortcuts reference
- Data persistence controls
- Accessibility features showcase
- Reset settings functionality

### ✅ UI Components Built
- Button (Primary, Secondary, Tertiary, Destructive, sizes S/M/L, loading states)
- Input, Textarea, Label (with error states)
- Select dropdown
- Card with Header, Content, Footer
- Badge (neutral, brand, success, warning, error)
- Alert/Banner (success, info, warning, error)
- Toast & Toaster
- Dialog (modals)
- Tabs, Separator
- Dropdown Menu
- Progress bar

All components:
- Use design tokens
- Support dark mode
- Include 3px focus rings
- Meet AA contrast requirements
- Respect reduced motion preferences

## 🎨 Design System Usage

### Typography

```tsx
<h1 className="text-display">Display Text</h1>
<h1 className="text-h1">Heading 1</h1>
<h2 className="text-h2">Heading 2</h2>
<h3 className="text-h3">Heading 3</h3>
<p className="text-body-16">Body text</p>
<span className="text-mono-13">Code/IDs</span>
```

### Colors

```tsx
// Status badges
<Badge variant="success">Completed</Badge>
<Badge variant="warning">Processing</Badge>
<Badge variant="error">Failed</Badge>
<Badge variant="brand">Featured</Badge>
<Badge variant="neutral">Default</Badge>

// Alerts
<Alert variant="success">...</Alert>
<Alert variant="error">...</Alert>
```

### Theme Toggle

```tsx
import { useTheme } from '@/components/theme-provider'

const { theme, setTheme } = useTheme()
setTheme('dark') // 'light' | 'dark' | 'system'
```

## 🔧 Configuration

### Tailwind Config
The Tailwind configuration extends with design tokens:
- Custom color system from CSS variables
- Typography scales
- Spacing, sizing, radius from tokens
- Animation durations and easing
- Custom z-index layers

### Theme Persistence
- Theme preference: `localStorage.getItem('arc-ui-theme')`
- Table density: `localStorage.getItem('table-density')`

## 📋 Remaining Work

### Pages to Implement
- [ ] Price Books list (/books) - with search, filters, table
- [ ] Price Books detail (/books/[id]) - with tabs for Items, Options, Finishes, Rules, Provenance
- [ ] Diff Review (/diff) - with filter chips, side-by-side view, approval
- [ ] Export Center (/export-center) - CSV/XLSX/JSON downloads
- [ ] Publish (/publish) - Baserow integration with dry run

### Components Needed
- [ ] Data table with toolbar (search, filters, column chooser, density toggle)
- [ ] Side panel for row details
- [ ] Virtualized table for large datasets
- [ ] Diff cell component (before/after split view)

## 🎯 Design Guide Compliance

Following **ARC UI Design Guide v1.0**:
- ✅ Section 1-4: Bootstrap, env, tokens, app shell
- ✅ Section 5.1: Upload wizard (3 steps)
- ✅ Section 9: Dark mode with system preference
- ✅ Section 8: Keyboard navigation
- ✅ Section 14: AA contrast, focus rings
- ⏳ Section 5.2-5.5: Remaining pages (Books, Diff, Exports, Publish)
- ⏳ Section 6.4: Data-dense tables

## 📱 Responsive Design
- Mobile-first approach
- Sidebar collapses on narrow screens
- Container max-width 1280px
- Page padding 16-24px
- Grid system: 12-column pages, 8-column in cards

## ♿ Accessibility
- WCAG AA contrast compliance (≥4.5:1)
- 3px focus rings on all interactive elements
- Keyboard navigation (Tab, Esc, Arrow keys)
- Screen reader support with ARIA labels
- Color-blind safe (icons + labels, not color alone)
- Respects `prefers-reduced-motion`

## 🚦 QA Checklist

- [x] Type scale and spacing consistent
- [x] AA contrast in light and dark modes
- [x] Theme toggle works and persists
- [x] Focus rings visible on all interactive elements
- [x] Motion respects user preference
- [x] Empty/loading states present
- [ ] Table density toggle works and persists
- [ ] Diff highlights readable for color-blind users
- [ ] Destructive actions require confirm dialog
- [ ] Keyboard-only navigation completes core flows

## 📦 Dependencies

### Core
- Next.js 14.2.25
- React 18.2.0
- TypeScript 5.3.2

### UI & Styling
- Tailwind CSS 3.3.5
- Radix UI (accessible component primitives)
- Lucide React (icons)
- class-variance-authority (component variants)

### State & Forms
- Zustand 4.4.7 (state management)
- React Hook Form 7.48.2
- Zod 3.22.4 (validation)

### Utilities
- Axios 1.6.2
- date-fns 2.30.0
- clsx, tailwind-merge

## 🤝 Contributing

### Code Style
- Use TypeScript for type safety
- Follow design token system for all styling
- Ensure AA contrast and keyboard accessibility
- Include loading, error, and empty states
- Add focus rings to all interactive elements

### Commit Messages
Follow Conventional Commits format:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring

## 📄 License

Proprietary - Internal use only

---

**Built with** [Claude Code](https://claude.com/claude-code)
