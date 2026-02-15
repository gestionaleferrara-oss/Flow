# Gestio - Business Manager PRD

## Original Problem Statement
Migration of a Google Apps Script application to a modern full-stack web app (FastAPI + React + MongoDB). Key features: CSV/XLSX data import, automated customer/product/supplier creation, advanced statistics with filters, glassmorphism UI, news & market prices from Italian produce industry sources.

## Architecture
- **Frontend:** React.js, Tailwind CSS, Recharts, Framer Motion, Shadcn UI
- **Backend:** FastAPI (Python), Motor (async MongoDB), Pandas, feedparser, BeautifulSoup4
- **Database:** MongoDB (collections: vendite, prodotti, clienti, fornitori, notizie)
- **3rd Party:** RSS feeds (FreshPlaza, Corriere Ortofrutticolo), HTML scraping (Myfruit.it)

## What's Been Implemented
- [x] Full-stack app with dashboard, vendite, clienti, prodotti, fornitori, statistiche, notizie pages
- [x] CSV/XLSX file upload with batch processing (~21K rows)
- [x] Statistics with filtering by date, product, customer
- [x] Glassmorphism dark UI theme
- [x] News from 3 Italian sources (FreshPlaza, Corriere Ortofrutticolo, Myfruit)
- [x] Market prices with dynamic scraping from FreshPlaza
- [x] Dashboard with growth % card, KPI cards, recent activity
- [x] Top products by EUR value (not quantity)
- [x] Chronological news sorting
- [x] Pie chart with readable hover labels
- [x] Calculated sale totals (qty * price) for accurate display
- [x] OR-based search in vendite (search across cliente and prodotto)
- [x] Single-parameter filters working correctly

## Bug Fixes (Feb 15, 2026)
1. Fixed market price links (verified working Azure blob PDFs)
2. Fixed news sources: replaced FreshPoint Magazine with Myfruit.it scraper
3. Fixed news chronological sorting (newest first)
4. Fixed pie chart hover labels (white text on dark background)
5. Fixed sale total rounding (now calculates qty * price for display)
6. Fixed single-parameter filter logic (OR-based search)
7. Replaced "Ordini Mese" card with "Crescita Vendite" percentage
8. Removed welcome/hero card from dashboard

## Prioritized Backlog
### P1
- Full feature parity review with original Google Apps Script

### P2
- Refactor server.py into modular structure (routes/, models/, services/)
- Export data to Excel/PDF
- Inventory management (reorder alerts)
- Email notifications for low stock
