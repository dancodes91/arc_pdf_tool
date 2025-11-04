# ARC UI Design Guide — Code Agent Edition

**Audience:** product/design/dev teams (and your AI code agent).  
**Scope:** Professional admin UI for Price Book parsing, diffing, and publishing.  
**Format:** Markdown, copy into your repo as `docs/ui-design-guide.md`.  
**Version:** v1.0

---

## 1) Product UX Principles

- **Clarity over cleverness:** dense data, clear hierarchy, minimal chrome.
- **Progressive disclosure:** summarize first; reveal detail (diffs, provenance) on demand.
- **Trust & traceability:** always show source (PDF, page, section) and effective dates.
- **Speed cues:** clear loading/progress; optimistic UI where safe.

**Do / Don’t**

- Do keep primary actions visible and predictable.
- Do prefer side panels over full-page modals for row details.
- Don’t hide provenance or effective dates behind multiple clicks.
- Don’t use color alone to communicate meaning.

---

## 2) Information Architecture (IA)

**Primary navigation (left sidebar):**
- Upload
- Price Books
- Diff Review
- Exports
- Publish
- Settings

**Inside a Price Book (tabs):**
- Overview
- Items
- Options
- Finishes
- Rules
- Provenance

**Object detail pattern:**
- Sticky header: manufacturer, edition, effective date, key actions.
- Body: tabbed content with toolbars per tab.

---

## 3) Visual System (Tokens & Scales)

### 3.1 Typography
- **Font:** Inter (or system UI fallback).
- **Scale, desktop (size/line-height, weight):**
  - Display: 32 / 40, medium
  - H1: 24 / 32, semibold
  - H2: 20 / 28, semibold
  - H3: 18 / 26, medium
  - Body standard: 16 / 24
  - Body dense tables: 14 / 22
  - Mono (IDs/keys): 13 / 20

### 3.2 Spacing & Density
- **Base unit:** 4px.
- **Common spacings:** 4, 8, 12, 16, 24, 32.
- **Table row height:** 40–44px (dense), 52px (comfortable).

### 3.3 Color (semantic, accessible)
- **Background / Text:** white background, near-black text (#0B0C0E on #FFFFFF).
- **Neutrals:** Slate 50–900; use 100/200 for backgrounds, 600 for body text.
- **Brand/accent:** saturated blue (#2563EB). Secondary data blue (#1D4ED8).
- **States:**
  - Success: #16A34A (use 50 tint for backgrounds)
  - Warning: #F59E0B
  - Error: #DC2626
  - Info: #2563EB
- **Diff colors:**
  - Added: green #10B981
  - Removed: red #EF4444
  - Changed: amber #F59E0B
- **Contrast:** WCAG AA (≥ 4.5:1) for text on backgrounds.

### 3.4 Shape & Elevation
- **Radius:** 12px (cards/dialogs), 8px (inputs/buttons), 6px (table cells).
- **Shadows:** soft ambient for cards; flat tables to reduce glare.

### 3.5 Breakpoints & Layout
- **Content width:** max 1280px; page padding 16–24px.
- **Grid:** 12-column pages; 8-column inside cards.
- **Breakpoints:** 640, 768, 1024, 1280, 1536.

---

## 4) Navigation & Page Layout

### 4.1 App Shell
- **Left sidebar:** primary nav, environment badge (Dev/Prod), collapsible to icons.
- **Top toolbar:** global search, quick actions (Upload, Export), account menu.
- **Breadcrumbs:** inside content for deep routes.

### 4.2 Card & Table Composition
- **Card header:** title + meta (edition, effective date) + compact actions (Export, Publish).
- **Content:** tabs; each tab has a toolbar (filters, density toggle, column visibility, download).

---

## 5) Key Screens & Patterns

### 5.1 Upload Flow (3 steps)
1. **Select Manufacturer + Upload PDF**  
   Drag-drop area with constraints (file type, max size).
2. **Parse Progress**  
   Progress bar, “x pages parsed”, ETA, collapsible live log.
3. **Result Summary**  
   Effective date, item/option/finish counts. Actions: **Preview parsed**, **Export**, **Go to Diff**.

**Empty state:** friendly illustration and “Drop a price book PDF to get started.”  
**Error state:** clear message, retry, link to logs.

### 5.2 Price Book Overview
- **Hero band:** manufacturer logo, edition label, effective date lozenge, source PDF link.
- **KPIs:** Items, Options, Finishes, Rules, low-confidence count.
- **Provenance:** “Parsed from …, pages 1–155”.
- **Tabs:** Items / Options / Finishes / Rules / Provenance.

### 5.3 Data Tables (Items, Options, Finishes)
- **Toolbar:** search, column filters (popover), density toggle, column chooser, export.
- **Row affordances:** hover to reveal row actions (view source, copy ID).
- **Sticky columns:** model code and finish; right-pinned actions column.
- **Large data UX:** virtualized body; stable header; skeleton rows when loading.
- **Inline metadata:** tiny provenance icon opens side panel with PDF preview and coordinates.

### 5.4 Diff Review
- **Filters:** Added / Removed / Changed / Renamed / Low confidence (chips with counts).
- **Grouped sections:** Items, Options, Rules (each with mini-KPIs).
- **Changed row pattern:** side-by-side **Before vs After**, changed cells highlighted, % delta badge.
- **Rename handling:** “Matched by similarity 0.92” tag; allow relink; show reason (similarity, family).
- **Approval footer:** “Selected N changes → **Approve & Apply**”; secondary: Export diff CSV.
- **Safety:** persistent “Pending changes” banner until applied.

### 5.5 Publish (Baserow)
- **Publish card:** choose price book; mapping summary (field ↔ field).
- **Dry run:** created/updated/unchanged counts, warnings; action “Run publish”.
- **History:** table of runs with status, timestamps, durations; view logs.

---

## 6) Components & Interaction Guidelines

### 6.1 Buttons
- **Variants:** Primary (filled), Secondary (outline/subtle), Tertiary (text), Destructive (error).
- **Sizes:** S 32px, M 40px, L 48px.
- **States:** hover (tint), active (pressed), focus (high-contrast ring), loading (spinner replaces icon), disabled (dim).
- **Icon spacing:** 8px between icon and label; single-icon buttons are square.

### 6.2 Inputs & Forms
- **Field anatomy:** label (always visible), control, helper text, error text.
- **Validation:** inline on blur and submit; error summary at top of long forms.
- **File upload:** drag-drop with progress, file chips, hard limits shown.

### 6.3 Cards & Panels
- **Cards:** consistent padding; subtle dividers; header with actions.
- **Side panels:** for row details with provenance; keep page context visible.

### 6.4 Tables (Data-dense)
- **Density:** 40–44px rows (dense) or 52px (comfortable).
- **Sticky header and first column** for large sets.
- **Alignment:** text left; numbers right; codes center.
- **Row states:** hover tint; selected with subtle brand border; optional zebra striping.
- **Tooling bar:** search, visibility, filters, density, export; persist user prefs.
- **Truncation:** ellipsis + tooltip; never wrap identifiers.
- **Diff views:** green tint for added, red for removed, split before/after cell for changes with % delta badge.

### 6.5 Navigation
- **Sidebar:** icon + label; current route highlighted with pill; small count badges for pending items.
- **Breadcrumbs:** final crumb muted, non-link.

### 6.6 Tabs & Segments
- **Tabs:** underlined or pill; bold active tab; visible focus ring.
- **Segmented controls:** for density (dense/comfortable) and view (table/cards).

### 6.7 Feedback (Toasts, Banners, Empty, Error)
- **Toasts:** short confirmations; auto-dismiss; pause on hover.
- **Banners:** system messages (e.g., “New price book uploaded; review diff”).
- **Empty states:** icon/illustration + concise copy + primary action.
- **Errors:** actionable message, context, link to logs.

### 6.8 Dialogs
- **Use for:** destructive confirms, multi-step, authentication.
- **Anatomy:** title, succinct body, primary/danger on right, cancel on left.

### 6.9 Motion
- **Micro-transitions:** 120–160ms.
- **Entry/exit:** ease-out for enter, ease-in for exit.
- **Tables:** brief row pulse on update; diff highlight fades after a short delay.

---

## 7) Content Design (Microcopy)

- **Tone:** professional, concise, friendly. Avoid non-standard jargon.
- **Empty:** “No options found. Try changing filters or re-parsing the book.”
- **Error:** “We couldn’t parse some pages. Retry or download the log to share.”
- **Success:** “Parsed successfully. 1,247 items, 112 options, 23 finishes.”
- **Diff CTA:** “You’re reviewing 86 changes. Approve to apply them to the catalog.”

---

## 8) Accessibility & Keyboard

- **Focus order:** mirrors visual order; visible 3px high-contrast focus ring.
- **Keyboard tables:** arrow keys move cells, `F` filters, `/` focuses search.
- **Color independence:** pair color with icons or labels (Added/Removed/Changed).
- **ARIA:** landmarks; `aria-modal="true"` for dialogs; proper table headers and roles.

---

## 9) Dark Mode (recommended)

- **Neutrals:** invert thoughtfully; avoid pure black/white.
- **Diff colors:** keep meaning, slightly mute saturation for comfort.
- **System:** honor `prefers-color-scheme`; include a manual toggle in Settings.

---

## 10) CSS Principles (How We Work)

- **Semantics first:** classes reflect meaning (error, warning) not raw colors.
- **Composition over overrides:** tokens → utilities → components → patterns. Avoid `!important`.
- **Predictable cascade:** low specificity; single class per component where possible.
- **Mobile-first:** base styles at small screens; enhance upwards.
- **Accessible by default:** AA contrast, visible focus, respect reduced motion.
- **Themeable:** tokens and semantic aliases enable light/dark/brand without rewrites.
- **Auditable:** single source of truth for tokens; log token changes.

---

## 11) CSS Architecture & Organization

- **Layers (top → bottom):**
  1. Foundations: reset/normalize, box sizing, base typography.
  2. Design tokens: color, spacing, radius, shadows, sizing, z-index, timing, easing, type scales.
  3. Utilities: single-purpose helpers (spacing, layout, truncation, display).
  4. Components: buttons, inputs, cards, tables, banners, toasts, dialogs, tabs, nav.
  5. Patterns: upload flow, diff row, side panel, wizard steps.
  6. Pages/overrides: page-specific tweaks (sparingly).
- **Naming convention:** choose BEM or CUBE CSS and stick to it.
- **Specificity rules:** max 2 levels; prefer class selectors; avoid IDs for styling; avoid element selectors for components.
- **File import order:** foundations → tokens → utilities → components → patterns. No cycles.

---

## 12) Design Tokens (What to Standardize)

- **Color:** neutrals, brand, feedback, diff palette, semantic aliases (`bg/surface`, `text/*`, `border/*`, `focus-ring`).
- **Typography:** families (UI sans/mono), scale (display → caption), weights (regular/medium/semibold), tracking rules.
- **Spacing:** base 4px; scale 4–64.
- **Sizing:** control heights (32, 40, 48), icon grid (16, 20, 24), container widths (640–1280).
- **Radius:** buttons/inputs 8; cards/dialogs 12; pills 999.
- **Elevation:** surface none; card ambient; popover medium; modal high.
- **Z-index:** Nav 10, Popover 20, Toast 30, Modal 40, Tooltip 50.
- **Motion:** micro 120–160ms; standard 200–240ms; modal 280–320ms; easing per section 6.9.
- **Breakpoints:** S ≤640, M 641–768, L 769–1024, XL 1025–1280, 2XL 1281+.
- **Density:** comfortable (default), dense (−20% vertical on tables).

---

## 13) Layout System

- **Page shell:** left sidebar (collapsible), main grid; keep top toolbar on wide screens.
- **Containers:** max width 1280; gutters consistent; page padding 16–24.
- **Grid:** 12-column pages; 8-column cards.
- **Stacking:** use vertical stacks with spacing tokens; avoid ad-hoc margins.
- **Responsive:** at larger widths show more table columns; on small screens collapse metadata into drawers.
- **Container queries:** adapt table tools/density to container width where supported.

---

## 14) States & Accessibility

- **Focus:** always visible; meets AA.
- **Contrast:** text on background ≥ 4.5:1.
- **Not color-only:** pair color with icons/labels.
- **Keyboard:** tab order logical; Esc closes modals; arrow keys navigate menus/lists.
- **Reduced motion:** disable non-essential transitions if requested.
- **Error discoverability:** show inline and in a summary for long forms.

---

## 15) Motion & Micro-interactions

- **Purpose:** guide attention and confirm actions.
- **Durations:** 120–160ms (hover/press), 200–240ms (navigation), 280–320ms (dialogs).
- **Easing:** ease-out for enter, ease-in for exit.
- **Tables:** row update pulse; diff highlight fades after delay.
- **Drag & drop:** subtle lift, slightly stronger shadow.

---

## 16) Data Visualization (If Needed)

- **Palette:** neutral gridlines; primary series in accent color; color-blind friendly alternates.
- **Type:** titles H3; axes/legends body-14.
- **States:** loading skeletons; empty guidance; readable tooltips in both themes.

---

## 17) Performance & Maintainability

- **Repaint/reflow:** avoid heavy shadows on scrolling regions; prefer GPU transforms sparingly.
- **Critical path:** keep initial CSS lean; load heavy component styles on demand.
- **No deep nesting:** shallow selectors; single-class hooks for components.
- **Lint & review:** style audits; specificity ceiling; document all exceptions.

---

## 18) Documentation & Governance

- **Living style guide:** tokens, components, usage examples, do/don’t notes.
- **Changelog:** record token and component changes; announce deprecations early.
- **Decision records:** log major UI decisions (colors, density defaults, motion thresholds).

---

## 19) Visual QA Checklist (Every Release)

- [ ] Type scale and spacing consistent across pages.  
- [ ] AA contrast met in light and dark modes.  
- [ ] Table density toggle works and persists.  
- [ ] Diff highlights readable for color-blind users.  
- [ ] Destructive actions require confirm dialog.  
- [ ] Upload shows 0% / 50% / 100% progress clearly.  
- [ ] Empty / loading / error states present across pages.  
- [ ] Keyboard-only navigation completes core flows.  
- [ ] Motion respects user “reduced motion” preference.

---

## 20) Page-Specific Guidance (Your App)

- **Upload wizard:** calm hero, 3-step progress, collapsible parse log, strong **View parsed data** CTA.
- **Price book overview:** hero with manufacturer + effective date lozenge; KPI cards; provenance line.
- **Diff review:** sticky filter chips (Added/Removed/Changed/Renamed/Low-confidence); batch approval footer; side panel shows PDF provenance.
- **Publish:** mapping summary card; dry-run counts; run history with statuses and logs.

---

## 21) Design Assets to Prepare (Handoff)

- **Brand & tokens:** color palette, typography, spacing, radii, shadows.
- **Components:** Button, Input, Select, Tabs, Dialog, Toaster, Table (all states).
- **Patterns:** Upload wizard, Diff row (before/after), Side panel with provenance.
- **Icons:** Add, Remove, Change, Confidence, Export, Publish, Provenance.
- **Illustrations:** empty upload, error, publish success.

---

## 22) Success Criteria (UI Acceptance)

- Users can complete: **Upload → Preview → Diff → Apply → Export → Publish** without ambiguity.
- Provenance and effective date **always** visible where relevant.
- Diff review communicates **what changed** and **why it’s matched**, with safe approvals.
- Tables perform smoothly with large datasets (virtualization or pagination).
- Light and dark modes both meet accessibility standards.

---

**End of Guide.** Save as `docs/ui-design-guide.md` and reference it in PR templates and design reviews.
