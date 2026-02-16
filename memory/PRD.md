# Flow - Product Requirements Document

## Original Problem Statement
Migrate a Google Apps Script application to a modern full-stack web app named "Flow" for sales/purchase management with inventory, statistics, AI features, and supplier/customer management.

## Tech Stack
- **Frontend**: React.js, Tailwind CSS, Recharts, Framer Motion, Shadcn/UI
- **Backend**: FastAPI, Pandas, Pydantic, FPDF2
- **Database**: MongoDB
- **AI**: Gemini Pro via Emergent LLM Key

## Architecture
```
/app/backend/
  server.py, database.py, models.py, utils.py
  routes/ (upload, entities, prodotti, vendite, dashboard, news, pdf_export)
/app/frontend/src/
  App.js (React.lazy + Suspense for code splitting)
  components/ (Sidebar with prefetch, PageWrapper, StatCard with blur, LoadingSpinner, ui/)
  pages/ (Dashboard, UploadCSV, Magazzino, Vendite, Clienti, Fornitori, Ordini, Statistiche, Notizie, ReportAI)
```

## Implemented Features
- Full dashboard with blurred KPI cards (reveal on hover/eye click), trends, sales insights, alerts
- All 4 KPI cards show: current value, previous month, trend %, extra detail
- CSV/XLSX upload with auto-processing
- Inventory management with editable fields
- Sales/purchases listing and filtering
- Customer page with year-filtered revenue, analysis modal
- Supplier page with year-filtered revenue, purchase detail modal
- Statistics page with charts and KPIs
- PDF export with margin/profit calculations
- News page with RSS feeds, AI Report page
- Interactive dashboard insights (click to open product/client analysis modals)
- Lazy-loaded pages with sidebar prefetch for instant navigation
- Sales Insight optimized with MongoDB aggregation (22s → 1.1s)
- Product search ultra-fast (~170ms, no N+1 queries)

## Key API Endpoints
- GET /api/dashboard → KPI data with prev month comparisons
- GET /api/clienti?search=&anno= → {clienti, anni_disponibili}
- GET /api/fornitori-with-stats?search=&anno= → {fornitori, anni_disponibili}
- GET /api/sales-insight → optimized dashboard insights
- GET /api/margine-vendite → margin data
- GET /api/prodotti/search?q= → ultra-fast product search

## Backlog (Prioritized)
- P2: Fix image scraping for ilcorriereortofrutticolo news source
- P3: Refactor Dashboard.jsx into smaller components
- P3: Review original Google Apps Script for missed features
- P3: Add caching layer for heavy endpoints
