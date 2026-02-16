# Flow - Product Requirements Document

## Overview
Flow è un'applicazione gestionale full-stack per il settore ortofrutticolo, migrata da Google Apps Script a una moderna architettura React + FastAPI + MongoDB.

## Core Features

### 1. Data Import & Processing
- Upload CSV/XLSX sales data
- Automatic customer/product handling
- Price updates and stock management

### 2. Inventory Management (Magazzino)
- Current stock display with editable minimum quantity
- Expiry date tracking
- Alphabetical ordering by product name

### 3. Advanced Statistics (Statistiche)
- Dashboard with charts and KPIs
- PDF/CSV export with € currency
- Margin calculation using weighted average
- Transaction-based average ticket calculation

### 4. Dashboard
- Fatturato card with margin and profit
- Trend Prodotti (left) with period filters
- Sales Insight (center-right) with clickable items
- Quick Links (right column)
- AI floating button (violet, bottom-right)
- Alert section with 3 columns

### 5. News & Market Prices (Notizie)
- Hero article (larger)
- 4-column news grid
- Breaking News widget (today + yesterday with LIVE badge)
- Weather and market prices

### 6. Client Management (Clienti)
- Total revenue per client
- Analysis modal with period selector (Mese, 3 Mesi, 6 Mesi, Anno, Tutto)
- Visit history with dates and totals
- Contact info editing

### 7. AI Features
- Weekly AI suggestions via floating button
- Sales insights (clickable for analysis)

## Technical Stack
- **Frontend**: React.js, Tailwind CSS, Recharts, Framer Motion, Shadcn/UI
- **Backend**: FastAPI, Pandas, Pydantic, FPDF2
- **Database**: MongoDB
- **AI**: Gemini Pro via Emergent LLM Key

## API Endpoints
- `GET /api/dashboard` - Main dashboard data
- `GET /api/sales-insight` - Sales insights with tipos: top_product, growth_product, top_client, new_client
- `GET /api/statistiche` - Statistics with margin calculation
- `GET /api/statistiche/export/pdf` - PDF export with € currency
- `GET /api/clienti/{id}/analisi?periodo=X` - Client analysis with period filter
- `GET /api/prodotti` - Products with sorting and filter_type
- `GET /api/trends-vendite` - Product trends with period/sort options

## Completed (Feb 2026)
- [x] Margin calculation using weighted average on ALL products
- [x] Dashboard layout: Trends | Insight | Quick Links aligned
- [x] AI floating button
- [x] Client fatturato_totale via aggregation
- [x] PDF with € instead of EUR
- [x] Insight clickable with correct type mapping
- [x] Improved loading message for insights
- [x] News: Hero larger, 4-column grid
- [x] Breaking News: today + yesterday filter with LIVE badge
- [x] App renamed to "Flow"

## Pending
- [ ] Image scraper for ilcorriereortofrutticolo
- [ ] Dashboard.jsx refactoring into smaller components
- [ ] Google Apps Script feature review
