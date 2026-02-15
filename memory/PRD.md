# Gestio - Business Manager PRD

## Original Problem Statement
Migration of a Google Apps Script application to a modern full-stack web application with:
1. Data Import: Upload CSV/XLSX files containing sales data
2. Automated Data Processing: Parse files to add customers, products, suppliers
3. Advanced Statistics: Dashboard with filtered statistics by time, product, customer
4. UI/UX: Modern glassmorphism dark theme
5. News & Market Prices: Daily news from freshplaza, corriereortofrutticolo, freshpoint and market prices from FreshPlaza
6. Functional Parity: All key features from original app

## User Personas
- Italian business user managing fruit/vegetable wholesale operations
- Needs to track sales, inventory, customers, and suppliers
- Follows market news and wholesale prices

## Core Requirements
- Upload CSV/XLSX with auto-detection of columns
- Statistics with charts (area, bar, pie) filtered by product/client/date
- Top Products chart by EURO revenue (not quantity)
- No negative signs in sales totals
- News from: FreshPlaza, Corriere Ortofrutticolo, FreshPoint Magazine
- Dynamic market price links scraped from FreshPlaza
- Weather widget for Bologna
- CRUD for clients, suppliers, products

## Architecture
- **Frontend**: React.js + Tailwind CSS + Shadcn UI + Recharts + Framer Motion
- **Backend**: FastAPI (Python) + MongoDB
- **News**: feedparser + BeautifulSoup for RSS scraping
- **Market Prices**: Dynamic scraping from FreshPlaza homepage

## What's Been Implemented (Feb 15, 2026)
- [x] Full glassmorphism dark theme UI
- [x] Dashboard with KPI cards and quick links
- [x] CSV and XLSX upload with batch processing (21K+ rows)
- [x] Statistics page with area chart, pie chart, bar chart (by euro)
- [x] Filters: product, client, date range, presets (30 days, current/prev month)
- [x] News from FreshPlaza, Corriere Ortofrutticolo, FreshPoint Magazine
- [x] Dynamic market price links from FreshPlaza (8 Italian cities)
- [x] Weather widget (Bologna)
- [x] Vendite, Clienti, Fornitori, Magazzino, Ordini pages
- [x] Math.abs applied to all financial displays (no negative signs)
- [x] data-testid on all interactive elements
- [x] Sidebar navigation with correct Italian labels

## P0 (Completed)
- [x] Correct news sources (FreshPlaza, Corriere Ortofrutticolo, FreshPoint)
- [x] Correct market price links (dynamic from FreshPlaza)
- [x] No negative totals in UI
- [x] XLSX upload support
- [x] Top Prodotti per Fatturato (euro, not quantity)

## P1 (Remaining)
- [ ] Backend refactoring: break server.py into routes/, models/, services/
- [ ] Full feature parity review with original Google Apps Script

## P2 (Backlog)
- [ ] Export data to Excel/PDF
- [ ] User authentication
- [ ] Advanced inventory management (reorder alerts)
- [ ] Email notifications for low stock
