# Flow - Product Requirements Document

## Original Problem Statement
Migrate a Google Apps Script application to a modern full-stack web app named "Flow" for sales/purchase management with inventory, statistics, AI features, and supplier/customer management.

## Tech Stack
- **Frontend**: React.js, Tailwind CSS, Recharts, Framer Motion, Shadcn/UI
- **Backend**: FastAPI, Pandas, Pydantic, FPDF2
- **Database**: MongoDB
- **AI**: Gemini Pro via Emergent LLM Key

## What's Been Implemented
- Full dashboard with blurred KPI cards (reveal on hover/eye click), trends, sales insights, alerts
- All 4 KPI cards: click on icon opens detailed analysis popup (Fatturato: daily chart + weekly + top products; Ordini: avg receipt + peak days + top qty; Clienti: top spenders + new + frequent; Alert: sotto scorta + clienti persi + scadenze)
- Card blur with Eye/EyeOff toggle (pinned state persists, hover is temporary)
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
- Sales Insight optimized with MongoDB aggregation (22s -> 1.1s)
- Product search with avg selling price (~200ms)

## Key API Endpoints
- GET /api/dashboard -> KPI data with prev month comparisons
- GET /api/dashboard/card-detail/{card_type} -> detailed analytics per card (fatturato/ordini/clienti/alert)
- GET /api/clienti?search=&anno= -> {clienti, anni_disponibili}
- GET /api/fornitori-with-stats?search=&anno= -> {fornitori, anni_disponibili}
- GET /api/sales-insight -> optimized dashboard insights
- GET /api/prodotti/search?q= -> product search with prezzo_vendita_medio

## Backlog
- P2: Fix image scraping for ilcorriereortofrutticolo news source
- P3: Refactor Dashboard.jsx into smaller components
- P3: Review original Google Apps Script for missed features
- P3: Add caching layer for heavy endpoints
