# Flow - Product Requirements Document

## Original Problem Statement
Migrate a Google Apps Script application to a modern full-stack web app named "Flow" for sales/purchase management with inventory, statistics, AI features, and supplier/customer management.

## Core Requirements
1. Data Import & Processing (CSV/XLSX)
2. Inventory Management (Magazzino)
3. Advanced Statistics (Statistiche)
4. Modern fintech UI/UX
5. News & Market Prices
6. AI-Powered Features (suggestions, reports)
7. Customizable Data Insights
8. Margin Calculation
9. Instant performance
10. Suppliers Page (Fornitori) - mirrors Clienti

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
  App.js
  components/ (Sidebar, PageWrapper, StatCard, LoadingSpinner, ui/)
  pages/ (Dashboard, UploadCSV, Magazzino, Vendite, Clienti, Fornitori, Ordini, Statistiche, Notizie, ReportAI)
```

## What's Been Implemented
- Full dashboard with KPI cards, trends, sales insights, alerts, AI suggestions (FAB)
- CSV/XLSX upload with auto-processing
- Inventory management with editable fields
- Sales/purchases listing and filtering
- Customer page with year-filtered revenue, analysis modal, editable contacts
- Supplier page with year-filtered revenue, purchase detail modal, editable notes
- Statistics page with charts and KPIs
- PDF export with margin/profit calculations
- News page with RSS feeds
- AI Report page
- Interactive dashboard insights: hover opens product/client analysis modals
- Year selector on both Clienti and Fornitori pages
- **Performance optimization**: Sales Insight endpoint rewritten with MongoDB aggregation (22s → 1.1s)
- **Fatturato card**: Shows both margin info AND previous month's revenue

## Key API Endpoints
- GET /api/clienti?search=&anno= → {clienti, anni_disponibili}
- GET /api/clienti/{id}/analisi?periodo= → client analysis
- GET /api/fornitori-with-stats?search=&anno= → {fornitori, anni_disponibili}
- GET /api/fornitori/{nome}/prodotti?mese= → {acquisti, totale_acquisti, totale_speso, mesi_disponibili, mese_selezionato, mese_riferimento}
- GET /api/sales-insight → dashboard insights (optimized with aggregation)
- GET /api/dashboard → KPI data
- GET /api/trends-vendite → product trends
- GET /api/margine-vendite → margin data
- GET /api/prodotti/search?q= → ultra-fast product search

## Performance Notes
- Sales Insight: Uses MongoDB aggregation pipelines instead of loading all documents into memory
- Product Search: Single query without N+1 price lookups
- Compound indexes on vendite: (data, prodotto_nome) and (data, cliente_nome)

## Backlog (Prioritized)
- P2: Fix image scraping for ilcorriereortofrutticolo news source
- P3: Refactor Dashboard.jsx into smaller components
- P3: Review original Google Apps Script for missed features
- P3: Add caching layer for heavy endpoints (margine-vendite, dashboard)
