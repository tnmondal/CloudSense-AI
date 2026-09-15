# Frontend Architecture

This document describes `frontend/` — the React + TypeScript + Vite
dashboard that consumes the CloudSense AI FastAPI backend. It complements
`docs/api_architecture_and_reference.md` (endpoint reference) and
`docs/gemini_finops_copilot.md` (the Copilot's backend design).

## Stack

React 19, TypeScript (strict mode: `noUnusedLocals`, `noUnusedParameters`,
`verbatimModuleSyntax`), Vite 8, React Router 7, Tailwind CSS 3, Recharts 3,
Axios, `react-markdown`, `lucide-react`.

## Guiding principle

**The frontend contains no analytics logic.** Every number rendered on
screen — cost totals, utilization percentages, anomaly scores, savings
estimates, carbon figures, forecast values — is fetched from the FastAPI
backend and displayed as-is (only formatted, never recomputed or
approximated in the browser). This mirrors the same grounding discipline
used in the Gemini Copilot's backend design.

## Component Structure

```
src/
├── types/api.ts          Types mirroring verified backend response shapes
├── services/
│   ├── apiClient.ts       Axios instance, base URL from VITE_API_BASE_URL,
│   │                      normalized ApiError (network / timeout / HTTP)
│   └── analyticsApi.ts    One typed function per real backend endpoint
├── hooks/useApiData.ts    Generic fetch hook: { data, loading, error, refetch }
├── lib/
│   ├── format.ts           Currency / percent / date / carbon / energy formatting
│   └── severity.ts         Severity color mapping, optimization category labels
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx      8-item nav, responsive (overlay drawer on mobile)
│   │   ├── TopBar.tsx       Page title + live backend health indicator
│   │   └── AppLayout.tsx    Sidebar + TopBar + <Outlet /> shell
│   ├── ui/
│   │   ├── KpiCard.tsx       Metric card with optional trend indicator
│   │   ├── DataView.tsx      Wraps loading/error/empty branching around children
│   │   ├── StateViews.tsx    LoadingState / ErrorState (with retry) / EmptyState
│   │   ├── Section.tsx       Card section wrapper + DisclaimerBanner
│   │   └── SeverityBadge.tsx Critical/High/Medium/Low pill
│   └── charts/
│       ├── TrendChart.tsx         Generic area/line chart (cost/carbon/forecast)
│       └── BreakdownBarChart.tsx  Horizontal ranked bar chart (dimension breakdowns)
└── pages/
    ├── OverviewPage.tsx, CostPage.tsx, UsagePage.tsx, AnomaliesPage.tsx,
    └── OptimizationPage.tsx, CarbonPage.tsx, ForecastPage.tsx, CopilotPage.tsx
```

Every page follows the same pattern: call one or more `useApiData(fetcher)`
hooks from `services/analyticsApi.ts`, then render through `<DataView>` so
loading/error/empty states are handled consistently without being
reimplemented per page.

## Data Flow

```
Page component
  → useApiData(fetcher, deps)              (src/hooks/useApiData.ts)
      → fetcher = a function from analyticsApi.ts
          → apiClient.get/post(...)         (src/services/apiClient.ts, Axios)
              → FastAPI backend (VITE_API_BASE_URL)
  ← { data, loading, error, refetch }
  → <DataView data loading error>            renders LoadingState / ErrorState / EmptyState / children(data)
  → children render KPI cards / charts / tables using `src/lib/format.ts`
```

`useApiData` is race-condition safe (a stale in-flight request cannot
overwrite a newer one) and exposes `refetch` so `ErrorState`'s "Retry" button
can re-run the exact same fetch.

## TypeScript Types

`src/types/api.ts` was built by directly inspecting
`src/api/services/analytics_service.py` and capturing live JSON responses
from the running backend — every field name, not just the general shape,
matches what the API actually returns. Notably, `CostDimension` is
intentionally restricted to `"service" | "region" | "department"` because
those are the only three dimensions with dedicated `/cost/by-*` endpoints;
`OptimizationItem` includes the exact fields the optimizer emits
(`estimated_monthly_saving_usd`, `estimated_annual_saving_usd`, `reason`,
`action_item`, `confidence`, etc.) rather than a guessed generic shape.

## AI Copilot Integration

`pages/CopilotPage.tsx` implements the chat UI:

- **Endpoint**: `POST /api/v1/chat` via `postChatMessage()`
  (`services/analyticsApi.ts`), using the exact `ChatRequest`/`ChatResponse`
  shapes from `src/ai/schemas.py`.
- **Conversation history**: each new request includes the prior turns as
  `conversation_history` (mapped to the `"user" | "model"` roles the backend
  schema expects), so multi-turn context is preserved for the session. State
  is kept in memory only (component state) — no browser storage is used.
- **Markdown rendering**: the `answer` field is rendered with
  `react-markdown` inside a small custom `.prose-chat` style block (headings,
  lists, bold, inline code) — the backend returns markdown-formatted prose in
  both live and deterministic mode.
- **Grounding UI**: every assistant message shows a footer with:
  - an **"Grounded in analytics"** pill (`is_grounded`)
  - the **tools used** (`tools_used`)
  - any **warnings** (e.g. the carbon-estimate disclaimer, or causation
    hedging for root-cause questions)
  - the **analytical sources** (warehouse table names)
  - a collapsible **"View underlying metrics"** panel showing the raw
    `relevant_metrics` JSON, so any number in the prose answer can be
    cross-checked directly against what the backend returned.
- **Capabilities disclosure**: before the first message, an optional
  "What can the Copilot actually check?" disclosure fetches
  `GET /api/v1/ai/tools-manifest` and lists the real tool names/descriptions
  the backend exposes — this is informational only and never used to
  fabricate a result client-side.
- **Suggested prompts**: a fixed set of example questions (matching the
  categories the tool registry actually supports: cost, optimization,
  carbon, forecast, utilization) are offered as one-click starters.
- **Loading/error states**: a typing-indicator bubble while awaiting a
  response; network/timeout/HTTP failures are caught and rendered as an
  inline error bubble (via the same `ApiError` normalization used
  everywhere else in the app) rather than crashing the chat.
- **No API key exposure**: the frontend never references `GEMINI_API_KEY` or
  any Gemini SDK — it only ever calls the FastAPI backend, which holds the
  key server-side (see `docs/gemini_finops_copilot.md`, Section 10).

## Responsive Strategy

- **Sidebar**: fixed 256px column on `lg:` and above; below that it becomes
  an off-canvas drawer (`-translate-x-full` / `translate-x-0`) triggered by a
  hamburger button in `TopBar`, with a click-to-dismiss scrim.
- **Grids**: KPI card grids use `grid-cols-1 sm:grid-cols-2 xl:grid-cols-4`
  (or `sm:grid-cols-3`) so cards reflow from a single column on mobile up to
  a full row on desktop.
- **Tables**: every data table is wrapped in `overflow-x-auto` so it scrolls
  horizontally on narrow viewports instead of breaking the layout; row
  content uses `truncate`/`min-w-0` to avoid overflow.
- **Charts**: all Recharts components are wrapped in `ResponsiveContainer`,
  so they resize fluidly with their parent card rather than using a fixed
  pixel width.
- **Copilot**: the chat column uses `flex flex-col` with a scrollable message
  area (`flex-1 overflow-y-auto`) and a fixed input row, and message bubbles
  cap their width (`max-w-[85%] sm:max-w-[75%]`) so long answers stay
  readable at any viewport size.
- **Code splitting**: every page is lazy-loaded (`React.lazy` + `Suspense` in
  `App.tsx`), so the initial bundle only includes the shell and Overview
  page; heavier per-page dependencies (Recharts, `react-markdown`) are
  fetched on navigation.

## Verification

- `npm run build` — runs `tsc -b` (strict type-check) followed by
  `vite build`. All chart components are generic over their row type
  (`TrendChart<T>`) so real API response arrays can be passed directly
  without lossy `Record<string, unknown>` casts.
- `npm run lint` — `oxlint` over the full `src/` tree.
- No `frontend` unit-test runner is currently configured; verification is via
  the TypeScript compiler, `oxlint`, a production build, and manual
  route/API smoke checks against the running backend (see the root
  `README.md` for exact commands).
