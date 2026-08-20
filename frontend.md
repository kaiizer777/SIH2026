# Frontend Design Guide

> Single source of truth for the SIH 2026 rockfall-warning frontend. The `/pitch` route is the reference implementation — every other page should match it.

---

## 1. Design philosophy

The product is a life-safety system used by geotechnical engineers and mine operators. The interface should feel **editorial and considered**, not consumer-flashy. Three words:

- **Quiet.** Let the data speak. The interface recedes.
- **Precise.** Mono numerics, tight tracking, no decorative noise.
- **Grounded.** White paper, ink-blue accent, hairline separators.

**Anti-patterns (do not ship):**
- Dark slate backgrounds as the default. The reference is light.
- Card grids (2-up or 3-up Q&A, 4-up stat tiles). Use hairlines and full-width rows instead.
- Glassmorphism, blur-backdrop cards, neon glows.
- Purple-to-pink gradients, indigo-500→purple-500 hero sections.
- Emoji as primary visual hierarchy. Emoji only as light punctuation if at all.
- Heavy borders, drop shadows on every block.
- "Inter for everything" with no typographic system behind it.
- Centered hero with three identical feature cards.

---

## 2. Color tokens

Light theme only. Use these values directly in Tailwind arbitrary-value classes (e.g. `bg-[#2563EB]`) or wire them into `globals.css` as CSS variables.

| Token            | Hex        | Usage                                                  |
| ---------------- | ---------- | ------------------------------------------------------ |
| `ink`            | `#2563EB`  | Primary accent. Eyebrows, focus rings, links, active dots. |
| `inkDeep`        | `#1D4ED8`  | Hover state for `ink`.                                |
| `inkSoft`        | `#EFF4FF`  | 10-second summary callout background, subtle blue tint. |
| `paper`          | `#FFFFFF`  | Default surface.                                      |
| `paperWarm`      | `#FBFBFD`  | Alternate surface for inset cards (rare).             |
| `inkDark`        | `#0B1220`  | Primary text. Headlines, numerics, primary buttons.   |
| `muted`          | `#5B6472`  | Secondary text. Descriptions, captions.               |
| `mutedSoft`      | `#8A93A1`  | Tertiary text. Placeholders, kbd hints, axis labels. |
| `hairline`       | `#E6E8EE`  | All dividers, input borders, table lines.             |
| `safe`           | `#047857`  | Safe state, Precision bar, success callouts.          |
| `warning`        | `#B45309`  | Warning state, F1 bar, amber callouts.               |
| `danger`         | `#B91C1C`  | Evacuation state, Recall gap, error callouts.        |

**Page background:** soft radial gradient
```
radial-gradient(1200px 600px at 50% -200px, #EFF4FF 0%, #F7F9FF 35%, #FFFFFF 70%)
```
Attach to `background-attachment: fixed` on the page root for a magazine-paper feel.

---

## 3. Typography

The layout already loads `Geist` (sans + mono). Use it as-is — do not add Inter, Outfit, or any other family.

| Role            | Family    | Size (mobile → desktop)      | Weight | Tracking       | Use                            |
| --------------- | --------- | ---------------------------- | ------ | -------------- | ------------------------------ |
| Page H1         | `Geist`   | hidden (see §1 anti-pattern) | —      | —              | Replaced by search-first UI.   |
| Chapter eyebrow | `Geist Mono` | 11 px                    | normal | `0.22em` uppercase | "CHAPTER 01", "BENCH", "TELE" |
| Chapter title   | `Geist`   | 24 → 30 px                   | 600    | `-0.02em`      | Section H2. Tight leading.     |
| Row Q-num       | `Geist Mono` | 11 px                    | normal | `0.18em` uppercase | "Q01", "T01", "TERM"        |
| Row headline    | `Geist`   | 18 → 20 px                   | 600    | `-0.01em`      | The question itself.           |
| Body            | `Geist`   | 15 → 16 px                   | 400    | 0              | `leading-[1.7]`.               |
| Caption         | `Geist`   | 12.5 → 13 px                 | 400    | 0              | Subtitles, descriptions.       |
| Numeric (big)   | `Geist Mono` | 60 → 84 px              | 600    | `-0.04em`      | Timer display, model recall.   |
| kbd             | `Geist Mono` | 10 px                   | normal | 0              | Keyboard shortcuts.            |

Line height for body: `1.65`–`1.7`. Never below `1.5` for paragraph text.

---

## 4. Spacing & layout

- **Page width:** `max-w-5xl` (1024 px) for the main column. `max-w-3xl` for the teleprompter.
- **Page padding:** `px-6 md:px-10` (24 → 40 px).
- **Vertical rhythm:** `py-7` (28 px) between rows, `pt-12 pb-6` between chapter sections.
- **Container type:** centered single column. No 2-column splits except inside a single row's expand panel.
- **One item per horizontal line.** Q&A, flashcards, glossary terms, and teleprompter segments are all full-width rows. No 2-up / 3-up / 4-up grids.

---

## 5. Component patterns

### 5.1 Page shell

```
<div className="min-h-screen text-[#0B1220]" style={pageBackground}>
  <TopBar />            // search + filter pills, sticky
  <Tabs />              // underline tabs, no box
  <main className="max-w-5xl mx-auto px-6 md:px-10 pb-24">
    {tab content}
  </main>
</div>
```

### 5.2 Top bar

- Sticky, `backdrop-blur-xl`, `bg-white/80`, hairline bottom border.
- **No title block, no H1, no subtitle.** Just the search input and a small Timer icon button.
- Search: pill-shaped (`rounded-full`), `py-2.5`, `pl-10 pr-20`, `Ctrl K` hint inside.
- Filter pills: below the search, `flex-wrap`, `gap-1.5`.

### 5.3 Tabs

- Single row, `flex gap-x-6`, `border-b border-[#E6E8EE]`.
- Each tab: `pb-3 text-[13px] font-medium`, `text-[#5B6472]` inactive, `text-[#0B1220]` active.
- Active underline: `absolute -bottom-px left-0 right-0 h-[2px] bg-[#2563EB]`.

### 5.4 Chapter header

```
<ChapterHeader num="01" title="..." subtitle="..." />
```

Renders:
- Mono eyebrow with hairline divider on the right
- Large H2 (24 → 30 px, semibold, `-0.02em` tracking)
- Muted subtitle paragraph (max-w-2xl)

### 5.5 Row (Q&A, flashcard, glossary, etc.)

Every row uses the same skeleton:

```
<article className="border-b border-[#E6E8EE] py-7 first:pt-2">
  <div className="flex items-baseline gap-4 md:gap-6">
    <div className="flex-shrink-0 w-12 md:w-16 text-right">
      <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">
        Q01
      </div>
    </div>
    <div className="flex-1 min-w-0">
      {content}
    </div>
  </div>
</article>
```

- Left column: tiny mono label, right-aligned, 48 → 64 px wide.
- Right column: the actual content, free to grow.
- Divider is a hairline between rows, not a card border.

### 5.6 10-second summary callout

A callout inside a row that contains the "executive summary":

```html
<div className="mt-3 rounded-md bg-[#EFF4FF] border-l-2 border-[#2563EB] px-4 py-3">
  <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#2563EB] mr-2">
    10-sec
  </span>
  {shortSummary}
</div>
```

Variant for non-tech / plain English: same shape, `bg-emerald-50 border-emerald-500`, `text-emerald-900/80`.

### 5.7 Pills and buttons

- **Primary button:** `bg-[#0B1220] text-white rounded-full px-5 py-2.5 text-[13px] font-medium hover:bg-[#1a2235]`.
- **Secondary button:** `bg-white border border-[#E6E8EE] text-[#0B1220] rounded-full hover:border-[#0B1220]`.
- **Accent button:** `bg-[#2563EB] text-white rounded-full hover:bg-[#1D4ED8]`.
- **Filter pill:** see §5.2.
- All buttons: `transition` on color/border. No scale, no translate, no shadow on hover.

### 5.8 Plus icon toggle

For expand/collapse, use a `+` glyph in a small bordered circle that rotates 45° on open.

```html
<span className={`w-5 h-5 rounded-full border border-[#E6E8EE] flex items-center justify-center
  transition-transform ${open ? 'rotate-45 border-[#0B1220] text-[#0B1220]' : ''}`}>
  <svg viewBox="0 0 24 24" className="w-3 h-3" fill="none" stroke="currentColor"
       strokeWidth="2.2" strokeLinecap="round">
    <path d="M12 5v14M5 12h14" />
  </svg>
</span>
```

### 5.9 Stats blocks (e.g. model cards)

Use a hairline grid, not separate cards:

```html
<div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[#E6E8EE] border border-[#E6E8EE] rounded-2xl overflow-hidden">
  <div className="bg-white p-6">{statBlock1}</div>
  <div className="bg-white p-6">{statBlock2}</div>
  <div className="bg-white p-6">{statBlock3}</div>
</div>
```

The `gap-px` plus the colored background acts as the divider. Inside each block, sections are separated by `border-t border-[#E6E8EE] pt-3` (not by an inset card).

### 5.10 Modal (e.g. timer)

- Backdrop: `fixed inset-0 bg-[#0B1220]/40 backdrop-blur-sm`.
- Card: `bg-white border border-[#E6E8EE] rounded-3xl p-7 shadow-2xl shadow-slate-900/20`.
- Close button: small × in a circle, top right.

---

## 6. Per-page rules

### `/` (home)

Currently a centered hero with three feature cards. **Do not** keep the three-card pattern.

Replace with:
- A single short paragraph (max-w-2xl) explaining the system in plain English.
- A vertical list of routes as full-width click rows: `→ /dashboard`, `→ /alerts`, `→ /trends`, `→ /pitch` (Pitch Companion). Each row is a hairline-bordered, left-aligned, large-text link.
- No background glows (no `bg-sky-500/10 blur-3xl`).
- No emoji as section icons. The route label and a one-line description are enough.

### `/dashboard` (pit heatmap)

- Header bar matches §5.2 (search-first, no title).
- Map fills the remaining viewport below the header.
- Right-side panel (legend + risk legend) uses hairline borders, not inset cards.

### `/alerts` (alert log)

- Same row-based pattern as `/pitch` (one alert per row).
- Severity badge: small mono pill, `bg-{tone}-50 text-{tone}-700 border border-{tone}-200`.
- Each row shows: severity · ID · timestamp · zone · message · sensor · probability · status · action.
- All in one horizontal line on desktop; stacks on mobile.

### `/trends` (sensor trends)

- Same row/chapter pattern.
- Charts sit in a `bg-white border border-[#E6E8EE] rounded-2xl` container with no inner shadow.
- Axis labels in `text-[#5B6472]`, grid in `#EEF1F5`.

### `/pitch` (already correct)

Keep as-is. This is the reference.

---

## 7. Motion

- Hover transitions: `transition` only on color, border, and background. No scale, no translate.
- Expand/collapse: simple opacity + 2 px translateY fade-in keyframe, 180 ms.
- Timer pulse: use color shift (`safe` → `warning` → `danger`), not motion.

No Framer Motion needed for the redesign. CSS transitions only.

---

## 8. Accessibility

- Focus rings: `focus:ring-2 focus:ring-[#2563EB]/15 focus:border-[#2563EB]` on every input.
- Color contrast: `#0B1220` on `#FFFFFF` = 18.7 : 1, AAA. `#5B6472` on `#FFFFFF` = 7.0 : 1, AA. Both pass.
- All interactive elements keyboard-reachable: tab order is search → filter pills → timer → tabs → first row → expand.
- `aria-hidden` on decorative SVGs.
- `aria-label` on icon-only buttons (the timer button).

---

## 9. Responsiveness

The entire frontend **must be fully responsive** across mobile, tablet, and desktop. The pitch page is the reference; every other page must match its responsive behavior.

### 9.1 Breakpoints (Tailwind defaults)

| Prefix | Min width | Typical device                       |
| ------ | --------- | ------------------------------------ |
| (base) | 0         | Small phones (320–479 px)            |
| `sm:`  | 640 px    | Large phones, small tablets          |
| `md:`  | 768 px    | Tablets, small laptops               |
| `lg:`  | 1024 px   | Laptops, desktops                    |
| `xl:`  | 1280 px   | Wide desktops                        |

Design mobile-first. Write the base class for the smallest screen, then add `md:` / `lg:` overrides for larger screens. **Never** write desktop-first and try to scale down.

### 9.2 Page shell (all pages)

```html
<div className="min-h-screen text-[#0B1220]" style={pageBackground}>
  <TopBar />
  <Tabs />
  <main className="max-w-5xl mx-auto px-5 sm:px-6 md:px-10 pb-24">
    {content}
  </main>
</div>
```

- Page padding scales: `px-5` (20 px) on phones → `px-6` (24 px) on tablets → `px-10` (40 px) on desktop.
- Vertical padding under content: `pb-20 md:pb-24`.
- Max width caps the column on large screens so the reading line never exceeds ~75 characters.

### 9.3 Top bar on mobile

- The header stays sticky on every breakpoint.
- The search input is always `flex-1`; the Timer icon button (`w-10 h-10`) sits to its right and never wraps below.
- The `Ctrl K` kbd hint is **hidden on small screens** (`hidden sm:flex`) to free space; it appears from `sm:` up.
- The "clear" button replaces the kbd hint only when a query is active, and the layout shift is intentional.
- Filter pills row uses `flex-wrap gap-1.5` so they flow to multiple lines on narrow viewports. No horizontal scroll on the pill row.

```html
<header className="sticky top-0 z-30 backdrop-blur-xl bg-white/80 border-b border-[#E6E8EE]">
  <div className="max-w-5xl mx-auto px-5 sm:px-6 md:px-10 py-4 md:py-5">
    <div className="flex items-center gap-2 sm:gap-3">
      <div className="relative flex-1">{/* search */}</div>
      <button className="flex-shrink-0 w-10 h-10 rounded-full ...">{/* timer icon */}</button>
    </div>
    <div className="mt-3 flex flex-wrap gap-1.5">{/* filter pills */}</div>
  </div>
</header>
```

### 9.4 Tabs on mobile

- Tab labels can overflow horizontally on narrow screens. Wrap the tab bar in a horizontally scrollable container with hidden scrollbar to keep the design clean:

```html
<nav className="max-w-5xl mx-auto px-5 sm:px-6 md:px-10 mt-8 md:mt-10">
  <div className="flex flex-wrap gap-x-5 sm:gap-x-6 gap-y-2 border-b border-[#E6E8EE] -mx-5 px-5 sm:mx-0 sm:px-0 overflow-x-auto [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
    {tabs.map(...)}
  </div>
</nav>
```

- `flex-wrap` lets tabs break to two lines on small phones if needed.
- `-mx-5 px-5` (mobile only) lets tabs bleed to the screen edge so users can still scroll the bar horizontally if labels are long.

### 9.5 Row pattern (Q&A, flashcards, glossary, alerts, trends)

- The left Q-number column scales: `w-10 md:w-12 lg:w-16`. On phones, the number stays legible but does not eat too much horizontal real estate.
- The gap between the number column and the content scales: `gap-3 md:gap-4 lg:gap-6`.
- Row headlines scale: `text-[17px] md:text-[19px] lg:text-[20px]`.
- The 10-second summary callout uses `text-[13px] md:text-[13.5px]` and stays full-width within the right column.
- Tag chips inside expanded content use `flex-wrap` so they reflow on narrow screens.
- The Copy button can sit on its own line on mobile:

```html
<div className="flex items-center justify-between flex-wrap gap-3 pt-1">
  {/* tags on the left, copy on the right; both wrap naturally */}
</div>
```

### 9.6 Chapter headers

- `pt-12 pb-6` on desktop, `pt-10 pb-5` on mobile.
- Title scale: `text-[22px] md:text-[26px] lg:text-[30px]`.
- Subtitle stays `max-w-2xl`; lines reflow naturally.

### 9.7 Teleprompter

- Use `max-w-3xl` instead of `max-w-5xl` (tighter reading column).
- The "Bigger text" toggle should persist the user's choice in `localStorage` so it survives a refresh.
- Bullet points must remain comfortable to read on a phone held at arm's length — minimum body size `text-[15px]` on mobile.
- On very small screens (`< 380 px`), the chapter title may wrap to three lines; this is acceptable and expected.

### 9.8 Stats blocks (model benchmark)

- The 3-up `grid grid-cols-1 md:grid-cols-3` collapses to a single column on mobile. Each block still shows the full set of metrics, but they stack vertically.
- Inside each block, the 3-metric row uses `grid-cols-3` (not collapsible) so Precision / Recall / F1 stay side-by-side even on a phone.

### 9.9 Charts (Recharts)

- Wrap every chart in `<div className="h-64 sm:h-72 w-full">` so height scales with viewport.
- Use `ResponsiveContainer` with explicit `minHeight` to prevent collapse on first paint.
- Tooltips, legends, axis ticks must remain readable on phones — Recharts will auto-shrink, but verify by viewing at 375 px width.
- If a chart needs to be inspected closely on mobile, add a "View fullscreen" link that opens the chart in a `dialog` or new tab. Optional.

### 9.10 Modal (timer)

- `max-w-md` with `m-4` (16 px gutter) so the modal does not touch screen edges.
- The numeric readout scales: `text-[56px] sm:text-[68px] md:text-[84px]`.
- Close button stays in the top-right corner on every breakpoint.
- Backdrop click and `Esc` both close the modal (and `Esc` must work even on mobile, where external keyboards are rare).

### 9.11 Buttons and tap targets

- Minimum tap target **44 × 44 px** on every interactive element (Apple HIG, WCAG 2.5.5).
- Filter pills: `py-1.5` is too small on its own — wrap them in a `min-h-[44px]` flex parent, or pad the pills to `py-2.5` on touch devices (`sm:py-1.5` for fine pointers).
- The Timer icon button is `w-10 h-10` = 40 px. Bump to `w-11 h-11` (44 px) for stricter compliance.

### 9.12 Tables and long content

- If a table or long horizontal list is required, wrap it in `overflow-x-auto` with a subtle fade on the right edge to hint at scroll:

```html
<div className="overflow-x-auto [mask-image:linear-gradient(to_right,black_95%,transparent_100%)]">
  <table className="min-w-full">...</table>
</div>
```

### 9.13 Forms (search input)

- Use `type="search"` so iOS shows the correct keyboard and a built-in clear button.
- Set `inputMode="search"` as a fallback for older browsers.
- `autoComplete="off"`, `autoCorrect="off"`, `spellCheck="false"`.

### 9.14 Testing checklist (do this before merging)

For every page (`/`, `/dashboard`, `/alerts`, `/trends`, `/pitch`):

- [ ] 320 px (iPhone SE 1st gen) — no horizontal page scroll, no text clipping, no overlapping elements.
- [ ] 375 px (iPhone SE 2nd/3rd gen, standard Android) — comfortable to read with thumb.
- [ ] 414 px (iPhone Plus / Pro Max) — no awkward whitespace.
- [ ] 768 px (iPad portrait) — two-column where it makes sense, otherwise single column with comfortable margins.
- [ ] 1024 px (iPad landscape, small laptop) — full reference layout.
- [ ] 1440 px (desktop) — content capped at `max-w-5xl`, centered, no edge-hugging.
- [ ] Landscape phone (e.g. 812 × 375) — top bar does not cover content; the page background gradient still anchors.
- [ ] All tap targets ≥ 44 × 44 px.
- [ ] All text remains legible at 200% browser zoom.

Use Chrome DevTools device emulation or the Responsive Design Mode in Firefox. **Do not declare done without testing at 320 px, 375 px, and 1440 px at minimum.**

### 9.15 Anti-patterns (responsive)

- **Fixed pixel widths** anywhere in the layout. Use `max-w-*` and `w-full` instead.
- **Fixed heights on text containers.** Let content drive height.
- **Horizontal page scroll** caused by an oversized element. Find and fix the culprit.
- **Hidden content on mobile** ("we'll just hide the description on phones"). Adapt, don't amputate.
- **Hover-only interactions** that have no tap equivalent (mobile has no hover). Every hover state must also have a focus or active state.
- **Tiny tap targets** under 44 px because "the design has many pills in a row". Increase spacing or use a larger pill on touch devices.

---

## 10. Files to touch when redesigning

| File                                  | Action                                                |
| ------------------------------------- | ----------------------------------------------------- |
| `frontend/app/layout.tsx`             | Remove dark body styles if any. Inherit light bg.     |
| `frontend/app/globals.css`            | Reset to light defaults. Remove any `bg-slate-950`.   |
| `frontend/app/page.tsx`               | Rewrite per §6 (`/`).                                 |
| `frontend/app/dashboard/page.tsx`     | Adopt top bar + row legend.                           |
| `frontend/app/alerts/page.tsx`        | Convert to row pattern.                               |
| `frontend/app/trends/page.tsx`        | Adopt top bar + light cards.                          |
| `frontend/app/pitch/PitchClient.tsx`  | Reference. Do not modify unless extending.            |

The pitch page (`PitchClient.tsx`) is the source of truth. Reuse its `TopBar`, `Tabs`, `ChapterHeader`, and `CopyButton` patterns directly — extract them into shared components under `frontend/components/` if they need to be shared across pages.

---

## 11. What "done" looks like

A senior engineer landing on any page in the app — `/`, `/dashboard`, `/alerts`, `/trends`, `/pitch` — should immediately see the same design language:

- Light paper background, ink-blue accents, hairline dividers.
- One search-first top bar with the same pill filter row underneath.
- One tab style (underline) or one row pattern (full-width, hairline-bordered).
- Mono numerics, tight tracking, no emoji-as-icons.
- **Fully responsive** at 320 px, 375 px, 768 px, 1024 px, and 1440 px (per §9.14).

If two pages look like they were built by different teams, the redesign is not done.
