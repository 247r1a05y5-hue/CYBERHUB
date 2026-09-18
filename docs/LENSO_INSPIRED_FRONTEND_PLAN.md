# CYBERHUB — Lenso-Inspired Reverse Image Investigation Frontend Architecture & Implementation Plan

## 1. Executive Summary & Product Vision
CYBERHUB is an image-first, AI-powered forensic visual investigation engine and controlled dataset identity matcher. Moving away from generic enterprise KPI dashboards, the entire user experience is organized directly around the core workflow:
**Input Image / Camera → Multi-Provider Analysis → Category Explorer → Deep Comparison & Forensic Verification → Evidence Preservation**.

---

## 2. Page Map & Route Hierarchy

```
/ (or /login)                     → Authentication / Session Check
├── /dashboard (or /search)        → Main Image-First Investigation Workspace (Home)
│     ├── State: Upload / Capture Area
│     ├── State: Analyzing / SSE Live Progress
│     └── State: Results Explorer (Categories, Grid/List, Filters)
├── /dataset                       → Controlled Dataset & AWS Rekognition Admin
├── /investigations                → Recent Searches / Historical Investigation Explorer
│     └── /investigations/:id      → Dedicated Investigation Deep-Dive
├── /saved                         → Saved Searches & Collections
├── /matches                       → Dataset Matches & Candidate Review
├── /verified                      → Verified Findings Archive
├── /evidence                      → Evidence Vault & Chain of Custody
├── /reports                       → Forensic Dossiers & Compliance Reports
└── /settings                      → System Diagnostics, Providers & Account
```

---

## 3. Component Tree Architecture

```
AppLayout (Shell)
├── AppSidebar (Collapsible, #050505, pure monochrome)
│     ├── Header (CYBERHUB Logo + Status dot)
│     ├── NavGroup: INVESTIGATE (Image Search, Dataset Match)
│     ├── NavGroup: SEARCHES (Recent Investigations, Saved Searches)
│     ├── NavGroup: RESULTS (Matches, Verified Findings, Evidence)
│     ├── NavGroup: TOOLS (Reports, Settings)
│     └── Footer (User Account, Organization, Logout)
├── TopNavigationBar (Compact header with active investigation breadcrumb & status)
└── Main Content View
      ├── SearchWorkspace (Home)
      │     ├── DropZone (Upload / Paste / Drop Area)
      │     ├── CameraModal (Real MediaDevices Camera with face guide & preview)
      │     ├── ImageMetaCard (Preview, dimensions, size, faces, quality score)
      │     └── ActionControls (Search Public Web, Match Dataset)
      │
      ├── SearchProgressStream (Real SSE-driven event checklist)
      │
      ├── ResultExplorer
      │     ├── ResultHeader (Ref thumbnail, query metadata, sort, view toggle, filter button)
      │     ├── CategoryBar (ALL, DATASET, WEB, DUPLICATES, PEOPLE, SIMILAR, RELATED, PLACES, TEXT, HISTORY, VERIFIED)
      │     ├── FilterPanel (Collapsible left/top filter drawer: Source, Match Type, Status, Domain, Date, Similarity)
      │     │
      │     ├── Views:
      │     │     ├── ResultGrid / ResultList (Image-first cards with hover actions)
      │     │     ├── DatasetMatchPanel (Top-K candidates, confidence, confirmed URLs, verification buttons)
      │     │     ├── WebExposurePanel (Multi-provider status & breakdown)
      │     │     ├── PeoplePanel (Potential match cards with face verification)
      │     │     ├── DuplicatesPanel (Exact, cropped, transformed copies)
      │     │     ├── SimilarPanel (Visually similar cluster items)
      │     │     ├── PlacesPanel (Landmarks & location imagery)
      │     │     ├── TextOcrPanel (Extracted text & query links)
      │     │     ├── HistoryPanel (Wayback & historical captures)
      │     │     └── ExposureGraph (Visual investigation node network)
      │     │
      │     ├── ResultDetailDrawer (Slide-over deep investigation panel)
      │     │     ├── DiscoveredImageLarge
      │     │     ├── SourceMetadata (Domain, URL, canonical, title, dates)
      │     │     ├── SignalBreakdown (Image similarity, face similarity, pHash, dHash)
      │     │     └── ActionToolbar (Open Source, Compare, Verify, Reject, Save Evidence)
      │     │
      │     └── SideBySideComparisonModal (Query vs Discovered with forensic diff & signal metrics)
```

---

## 4. API Dependencies & Data Bridges

All frontend components bind strictly to existing backend API endpoints:
1. **Upload & Analysis**: `POST /api/v1/investigations/image-exposure/analyze-and-search` (Multipart form with reference file + options).
2. **Real-Time Progress**: `GET /api/v1/investigations/image-exposure/events` (SSE stream for live provider feedback).
3. **Dataset Ingestion & Stats**: `GET /api/v1/dataset/stats`, `POST /api/v1/dataset/participants`, `POST /api/v1/dataset/match`.
4. **Human Verification**: `POST /api/v1/dataset/matches/{id}/verify` and `POST /api/v1/investigations/findings/{id}/verify`.
5. **System Diagnostics**: `GET /api/v1/system/diagnostics/search`.
6. **Recent & Saved Searches**: `GET /api/v1/investigations` with search query persistence in local/session stores.

---

## 5. State Management

- `investigationStore.ts`: Active reference image, blob URL, metadata, search ID, scanning state, SSE listener, results array, active category, active filters, selected result for drawer, comparison modal state.
- `datasetStore.ts`: Enrolled participants, stats, match candidates, verification queue.
- `authStore.ts`: Current user, token, active organization, role.

---

## 6. Visual Language & Design Tokens

- **Background**: `#000000`
- **Sidebar**: `#050505`
- **Panels & Cards**: `#0C0C0C`, `#111111`
- **Borders**: `#1A1A1A`, `#2B2B2B`
- **Primary Text**: `#F5F5F5`
- **Secondary Text**: `#B3B3B3`
- **Muted Text**: `#777777`
- **Disabled Text**: `#4A4A4A`
- **Semantic Badges**: Restrained green (`#10B981`), amber (`#F59E0B`), red (`#EF4444`).
- **Forbidden**: Blue, cyan, purple, neon gradients, warm beige, gold.

---

## 7. Interaction States & Transitions

- **DropZone**: Default, Drag-Over (high-contrast monochrome dashed border), Dropped, Loading preview, Error.
- **Camera**: Requesting Permissions → Live Stream with SVG Oval Face Frame → Captured Frame → Preview/Retake → Use Image.
- **Search Execution**: Image uploaded → Real SSE events ticking → Category tabs dynamically badged with counts → Result cards rendering with lazy-loaded thumbnails.
- **Card Hover**: Overlay with quick action buttons ([Compare], [Detail], [Open Source]).
- **Detail Drawer**: Smooth slide-in from right with tabs for Overview, Technical Signals, Context, and Actions.
- **Comparison Modal**: Full-screen modal with split-view zoom, visual similarity meter, face signal breakdown, pHash/dHash hamming distances.
