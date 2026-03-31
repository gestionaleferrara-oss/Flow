# Flow - Business Analytics App

## Stack
- Frontend: React.js, Tailwind, Recharts
- Backend: FastAPI, MongoDB
- AI: Gemini (Emergent LLM Key)

## Funzionalità Principali

### Dashboard
- 4 card con blur/reveal
- Selettori periodo (Mese corrente, Mese prec., 30gg, 90gg)
- Widget Trend e Sales Insight
- Ricerca unificata prodotti/clienti
- Chat AI con fuzzy matching

### Statistiche
- Switch Vendite/Acquisti
- Filtri rapidi: 30gg, Questo mese, Mese prec., 3 mesi
- **Confronto Mese vs Mese** (NUOVO): seleziona 2 mesi e visualizza variazioni
- Filtri avanzati con autocomplete prodotti/clienti
- Export PDF/CSV
- Grafici: Andamento mensile, Top Clienti (pie), Top Prodotti (bar)

### Report AI
- 3 tipi: Settimanale, Mensile, Dashboard
- Export PDF

### Forecast AI
- Previsioni per 3 mesi (mese target + 2 successivi)
- Grafico barre con range min-max
- Analisi AI esaustiva

### Sidebar
- Icone navigazione principali
- **Pulsante AI unificato** con dropdown (Forecast AI, Report AI)
- **Upload** in fondo alla sidebar
- Status indicator

### Altre Funzionalità
- Import CSV/XLSX (incrementale o sovrascrittura)
- Gestione Magazzino con quantità minime
- Clienti e Fornitori con analisi dettagliata
- Sistema Alert (sotto scorta, clienti inattivi)
- News feed

## Endpoints Principali
- `GET /api/dashboard` - KPIs dashboard
- `GET /api/dashboard/card-detail/{type}?periodo=` - Dettagli card
- `GET /api/statistiche?prodotto=&cliente=&start_date=&end_date=` - Stats vendite
- `GET /api/statistiche/acquisti` - Stats acquisti
- `POST /api/ai-reports/generate?report_type=` - Genera report AI
- `GET /api/forecast/generate` - Previsioni AI
- `POST /api/ai-chat` - Chat AI con dati azienda

## Changelog

### 2026-03-03
- FIX: Dropdown AI sidebar ora appare fuori dalla sidebar (z-index fixed)
- NUOVO: Confronto mese vs mese nelle Statistiche
- FIX: Calcolo "Visite frequenti" ora conta giorni unici di ordine
- FIX: Filtri Autocomplete Statistiche funzionanti (componente estratto)

### 2026-02-28
- Ricerca unificata prodotti/clienti in Dashboard
- Chat AI con accesso a dati vendite, clienti, fornitori
- Fuzzy matching per ricerca entità
- Widget Trend con filtri toggle (richieste, fatturato, margine)
- Import incrementale per evitare perdita dati

### 2026-02-16
- Forecast AI: previsioni 3 mesi con range
- Report AI: export PDF
- Fix encoding PDF

## Known Issues
- (P1) AI Forecast: accuratezza da migliorare — MIGLIORATA (trend YoY più recente)
- (P2) Margine widget Trend: chiarire se assoluto o variazione
- (P3) Image scraper ilcorriereortofrutticolo non funziona

### 2026-03-31 (sessione 3)
- FIX: Ripristinato quadrato viola sidebar AI icon (/forecast, /report-ai) con layoutId separato
- FIX UI: Grid 2 colonne quando Globale selezionato — step 2 nascosta completamente
- FIX: Algoritmo forecast migliorato: anchor anno più recente + trend YoY cappato ±25% + momentum recente
- FIX: AI prompt arricchito con storico completo + tabella YoY anno su anno + analisi trimestrale

## Changelog

### 2026-03-31
- FIX (P1): Calcolo prezzi medi ora usa media ponderata (totale/qty) in tutti gli endpoint di prodotti.py
  - search_prodotti: rimosso `$avg: prezzo_unitario` → aggregazione `totale_sum/qty_sum`
  - storico-clienti: costo_medio acquisto ora ponderato su totale/qty ordini
  - storico-clienti: prezzoMedioVendita ora ponderato su totale/qty vendite
  - storico-clienti: storico prezzi mensile ora usa media ponderata
  - analisi-acquisti: variazione_prezzi mensile ora usa media ponderata

## Backlog
- Fatturazione/DDT
- Gestione Pagamenti
- Mobile optimization
- Refactoring Dashboard.jsx (file troppo grande)
