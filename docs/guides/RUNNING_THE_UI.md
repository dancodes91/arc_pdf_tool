# 🚀 How to Run and See the New UI

## Quick Start (5 minutes)

### 1. Start the Development Server

```bash
cd frontend
npm run dev
```

The app will be available at: **http://localhost:3000**

### 2. Open in Your Browser

Navigate to `http://localhost:3000` and you'll see the **new ARC UI**!

---

## 📱 What to Explore

### ✅ Pages You Can See NOW:

#### 1. **Dashboard** (/)
- **URL:** `http://localhost:3000`
- **Features:**
  - KPI cards showing price book statistics
  - Recent price books list
  - Quick action cards
  - Empty state (if no books uploaded)

#### 2. **Upload Wizard** (/upload)
- **URL:** `http://localhost:3000/upload`
- **Features:**
  - **Step 1:** Drag & drop PDF upload + manufacturer selection
  - **Step 2:** Parse progress with live stats and collapsible log
  - **Step 3:** Summary with KPIs and action buttons
  - Visual step indicators with checkmarks
  - Try dragging a file to see the scale animation!

#### 3. **Price Books** (/books)
- **URL:** `http://localhost:3000/books`
- **Features:**
  - **Full DataTable** with search, sorting, pagination
  - **Density toggle:** Try "Comfortable" vs "Dense" view
  - **Column visibility:** Hide/show columns
  - **Search:** Filter by manufacturer
  - **Export button** (toolbar)
  - Stats cards at the top
  - Empty state if no books

#### 4. **Price Books Detail** (/books/[id])
- **URL:** `http://localhost:3000/books/[id]` (click any book from /books)
- **Features:**
  - **Hero Band:** Manufacturer logo, edition badge, effective date, source PDF link
  - **5 KPI Cards:** Items, Options, Finishes, Rules, Low Confidence counts
  - **Tabs Navigation:** Overview, Items, Options, Finishes, Rules, Provenance
  - **Items Tab:** Full DataTable with all products
  - **Back Navigation:** Return to Price Books list
  - **Export Button:** Download price book data

#### 5. **Diff Review** (/diff)
- **URL:** `http://localhost:3000/diff`
- **Features:**
  - **Price Book Selection:** Choose old vs new versions to compare
  - **Filter Chips:** All Changes, Added, Removed, Changed, Renamed, Low Confidence
  - **Summary KPIs:** Total changes, new products, retired products, price changes
  - **Changes List:** Side-by-side before/after view with delta badges
  - **Multi-Select:** Check individual changes to approve
  - **Approval Footer:** Sticky footer with "Approve & Apply" button
  - **Export:** Download diff as CSV

#### 6. **Export Center** (/export-center)
- **URL:** `http://localhost:3000/export-center`
- **Features:**
  - **Format Cards:** Excel (XLSX), CSV, JSON with feature descriptions
  - **Export Buttons:** One-click export in any format per price book
  - **Loading States:** Animated "Exporting..." indicator
  - **Export History:** Recent exports with timestamps and file sizes
  - **Empty State:** Shows when no price books available

#### 7. **Publish** (/publish)
- **URL:** `http://localhost:3000/publish`
- **Features:**
  - **Price Book Selection:** Choose which book to publish to Baserow
  - **Field Mapping:** Visual summary of field mappings
  - **Dry Run Option:** Preview changes without publishing
  - **Dry Run Results:** KPI cards showing created/updated/unchanged/warnings
  - **Warning Alerts:** Validation issues before publishing
  - **Publish History:** Recent runs with status badges and duration
  - **View Logs:** Access to detailed logs for each run

#### 8. **Settings** (/settings)
- **URL:** `http://localhost:3000/settings`
- **Features:**
  - **Theme Switcher:** Try Light / Dark / System
  - **Table Density:** Changes persist to localStorage
  - **Keyboard Shortcuts:** Reference guide
  - **Accessibility:** Shows compliance features
  - **Reset Settings:** Clear all preferences

---

## 🎨 Things to Test

### Theme Switching
1. Click the theme toggle in **top-right corner** (Topbar)
2. Try all three: Light / Dark / System
3. Notice how **all colors adapt** automatically
4. Check **AA contrast** is maintained

### Dark Mode
1. Go to **Settings** → Select "Dark"
2. Navigate through pages - everything adapts
3. Diff colors remain readable
4. Focus rings stay visible

### Table Density
1. Go to **Settings** → Change "Table Density"
2. Navigate to **Price Books** (`/books`)
3. Open toolbar → Click "Density" dropdown
4. Toggle between Comfortable (52px) and Dense (40px)
5. **Notice:** Setting persists when you reload!

### Navigation
1. Use **sidebar** to navigate between pages
2. Try **collapsing sidebar** (arrow button)
3. Click breadcrumbs (if on detail pages)
4. Use **keyboard:** Tab through buttons

### Upload Wizard Flow
1. Go to `/upload`
2. Select manufacturer
3. Drag a file or click to browse
4. Click "Start Upload & Parse"
5. Watch progress animation
6. See summary with action buttons

### DataTable Features (on /books and /books/[id])
1. **Search:** Type in search box to filter
2. **Sort:** Click column headers (up/down arrows)
3. **Columns:** Hide/show columns via dropdown
4. **Density:** Toggle row height
5. **Export:** Click export button
6. **Pagination:** Navigate pages at bottom

### Diff Review Flow
1. Go to `/diff`
2. Select an old price book and a new price book
3. Click "Compare" to see differences
4. Use filter chips to view specific types of changes
5. Check individual changes to approve
6. Click "Approve & Apply" in sticky footer
7. Export diff to CSV for records

### Export Center Flow
1. Go to `/export-center`
2. Review format options (Excel, CSV, JSON)
3. Click format button next to any price book
4. File downloads automatically
5. Check export history for recent downloads

### Publish Flow
1. Go to `/publish`
2. Select a price book to publish
3. Review field mapping summary
4. Enable "Dry run" to preview changes
5. Click "Run Dry Run" to see what would happen
6. Review created/updated/unchanged counts
7. If satisfied, uncheck dry run and publish
8. View publish history for past runs

---

## ⌨️ Keyboard Navigation

All pages support keyboard navigation:

- **Tab / Shift+Tab:** Navigate between elements
- **Enter:** Activate buttons/links
- **Esc:** Close dialogs/dropdowns
- **Arrow Keys:** Navigate table cells
- **/** Focus search (when in table)

**Test:** Try navigating the entire app using ONLY your keyboard!

---

## 🎯 Design System Features

### Typography Scale
Open browser DevTools and inspect text elements:
- Display: 32px (page titles)
- H1: 24px
- H2: 20px
- H3: 18px
- Body: 16px (default)
- Body-14: 14px (table cells)
- Mono-13: 13px (IDs, codes)

### Color System
All colors use **semantic tokens**:
- `--color-brand-primary` (blue buttons)
- `--color-success` (green badges)
- `--color-warning` (yellow badges)
- `--color-error` (red badges)

### Focus Rings
- **3px visible focus rings** on all interactive elements
- Test: Tab through buttons to see them

### Motion
- Transitions: 120-320ms with proper easing
- Hover effects on cards and buttons
- Progress bar animations
- Drag & drop scale effect

---

## 🔍 What's Under the Hood

### Design Tokens
Open DevTools → Inspect element → Computed styles:
- `--space-4` = 16px
- `--radius-lg` = 12px
- `--duration-fast` = 160ms
- `--text-h1-size` = 24px

### Responsive Breakpoints
Resize browser window:
- **Mobile:** < 640px (sidebar collapses)
- **Tablet:** 768px
- **Desktop:** 1280px max width

### Dark Mode CSS Variables
Inspect `<html>` element:
- Without `.dark` class → Light theme
- With `.dark` class → Dark theme variables

---

## 📊 Current Status

### ✅ Fully Implemented:
- [x] Design token system (tokens.css, semantic.css, dark.css)
- [x] App shell (Sidebar, Topbar, Layout)
- [x] Theme provider (Light/Dark/System)
- [x] 20+ UI components (Button, Input, Card, Badge, etc.)
- [x] Dashboard page with KPIs
- [x] Upload wizard (3-step flow)
- [x] Settings page (theme + density)
- [x] **DataTable component** (search, sort, pagination, density)
- [x] **Price Books list page** (full table implementation)
- [x] **Price Books detail page** (/books/[id]) with tabs and hero band
- [x] **Diff Review page** with filter chips and side-by-side comparison
- [x] **Export Center** with format options and export history
- [x] **Publish page** with Baserow integration, dry run, and history

### 🎉 All Core Pages Complete!
The UI implementation is now complete with all major pages functional. The application is ready for testing and refinement.

---

## 🐛 Troubleshooting

### Port Already in Use?
```bash
# Kill process on port 3000
npx kill-port 3000

# Or use a different port
npm run dev -- -p 3001
```

### Dependencies Issues?
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### TypeScript Errors?
```bash
npm run typecheck
```

---

## 📸 Screenshot Locations

Take screenshots of these pages:

1. **Dashboard** (light mode)
   - `http://localhost:3001`

2. **Dashboard** (dark mode)
   - Toggle theme first

3. **Upload - Step 1** (file selected)
   - `http://localhost:3001/upload`

4. **Upload - Step 2** (progress)
   - After clicking "Start Upload"

5. **Price Books** (with table)
   - `http://localhost:3001/books`

6. **Price Books Detail** (with tabs)
   - `http://localhost:3001/books/[id]`

7. **Diff Review** (with comparison results)
   - `http://localhost:3001/diff`

8. **Export Center** (format options)
   - `http://localhost:3001/export-center`

9. **Publish** (dry run results)
   - `http://localhost:3001/publish`

10. **Settings**
    - `http://localhost:3001/settings`

---

## 🎉 Quality Checklist

Test these to verify design guide compliance:

- [ ] **Typography:** Consistent sizes, no rogue fonts
- [ ] **AA Contrast:** Text readable in light AND dark modes
- [ ] **Focus Rings:** 3px visible on all interactive elements
- [ ] **Keyboard Nav:** Can Tab through entire app
- [ ] **Theme Toggle:** Works and persists
- [ ] **Density Toggle:** Works and persists
- [ ] **Empty States:** Show on all pages when no data
- [ ] **Loading States:** Spinner appears correctly
- [ ] **Hover States:** Buttons/cards respond to hover
- [ ] **Responsive:** Sidebar collapses on narrow screens

---

## 🚀 Next Steps

### To Complete the Implementation:

1. **Price Books Detail** (/books/[id])
   - Hero band with logo, edition, effective date
   - Tabs: Overview, Items, Options, Finishes, Rules
   - Large tables with the DataTable component

2. **Diff Review** (/diff)
   - Filter chips: Added/Removed/Changed
   - Side-by-side diff view
   - Approval footer

3. **Export & Publish Pages**
   - Format selection
   - Baserow integration

---

## 💡 Tips

- **Use browser DevTools** to inspect design tokens
- **Try color-blind simulation** to verify diff colors
- **Test keyboard-only navigation** (no mouse!)
- **Compare light vs dark** side by side
- **Check mobile view** by resizing browser

---

**Enjoy exploring the new UI!** 🎨

The foundation is solid and production-ready. The design token system makes implementing the remaining pages fast and consistent.
