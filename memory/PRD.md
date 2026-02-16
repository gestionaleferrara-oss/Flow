# Flow - Business Analytics App

## Descrizione
App full-stack per gestione vendite, magazzino, clienti, fornitori e analytics business con AI.

## Stack
- Frontend: React.js, Tailwind, Recharts
- Backend: FastAPI
- Database: MongoDB
- AI: Gemini (Emergent LLM Key)

## Funzionalità

### Dashboard
- 4 card principali con blur/reveal (hover desktop, tap mobile)
- Selettori periodo: Mese corrente, Mese prec., 30gg, 90gg
- Widget Trend Prodotti e Sales Insight

### Report AI
- **3 tipi**: Settimanale, Mensile, Dashboard (con confronto mese precedente)
- **Export PDF** funzionante
- Metriche chiave e analisi AI

### Forecast AI
- Previsione vendite per **prodotto** o **cliente**
- **Storico completo** (tutti i dati, non solo ultimo anno)
- Analisi **focalizzata SOLO sul mese target**
- **Counter**: Media Mese, Max Mese, Min Mese, Anni Dati
- **Export PDF** e **Reset**

### Altre Funzionalità
- Import dati CSV/XLSX
- Gestione Magazzino
- Pagine Clienti e Fornitori con analisi
- Sistema Alert
- News feed

## Endpoints Principali
- `GET /api/dashboard-cards` 
- `GET /api/card-detail/{id}?periodo=`
- `POST /api/ai-reports/generate?report_type=`
- `POST /api/ai-reports/export-pdf`
- `GET /api/forecast/generate?tipo=&nome=&mese_target=`
- `POST /api/forecast/export-pdf`

## Changelog 2025-02-16
- Report AI: aggiunto tipo Dashboard + export PDF
- Forecast AI: storico completo, analisi solo mese target, nuovi counter
- Fix PDF export (encoding caratteri)

## Backlog
- P2: Migliorare mobile UI
- P3: Fix scraping news
- P3: Refactoring Dashboard.jsx
