# Flusso - Product Requirements Document

## Overview
Flusso è un'applicazione web full-stack per la gestione aziendale, migrata da Google Apps Script a React/FastAPI/MongoDB.

## Original Problem Statement
L'utente vuole migrare un'applicazione Google Apps Script a un'applicazione web moderna con:
- Import dati da CSV/XLSX
- Gestione inventario (Magazzino)
- Statistiche avanzate
- News e prezzi di mercato
- Funzionalità AI per suggerimenti e report

## Tech Stack
- **Frontend:** React.js, Tailwind CSS, Axios, Recharts, react-markdown
- **Backend:** FastAPI, Pandas, BeautifulSoup4, feedparser
- **Database:** MongoDB
- **AI/LLM:** emergentintegrations + Google Gemini Pro (Emergent LLM Key)

## Core Features Implemented

### Data Management
- [x] Upload CSV/XLSX con auto-detect colonne
- [x] Gestione Clienti con campi editabili (WhatsApp, Email, Note)
- [x] Gestione Fornitori
- [x] Gestione Prodotti/Magazzino

### Inventory (Magazzino)
- [x] Visualizzazione stock con quantità importate
- [x] Quantità minima editabile per alert riordino
- [x] Scadenza editabile
- [x] Filtri "Da Ordinare" e "In Scadenza"
- [x] Colonne semplificate (rimossi Imballo, Kg/pz, Kg Rim.)

### Sales & Purchases
- [x] Vendite con vista raggruppata per cliente/data
- [x] Acquisti (Ordini) con vista raggruppata per fornitore/data

### Statistics
- [x] Dashboard con KPI principali
- [x] Grafici vendite mensili/giornaliere
- [x] Top clienti e prodotti
- [x] Trend clienti attivi

### AI Features
- [x] Suggerimento settimanale AI sulla dashboard
- [x] Pulsante refresh suggerimento
- [x] Report AI settimanali/mensili con Gemini Pro
- [x] Eliminazione report AI (pulsante cestino)

### Alerts & Notifications
- [x] Centro Alert sulla dashboard
- [x] Prodotti sotto scorta minima
- [x] Clienti inattivi
- [x] Prodotti in esaurimento

### News & Market
- [x] Aggregazione notizie da RSS
- [x] Prezzi di mercato

## Key API Endpoints
- `GET/POST /api/clienti` - CRUD clienti
- `GET/POST /api/prodotti` - CRUD prodotti
- `GET /api/vendite` - Lista vendite
- `GET /api/ordini` - Lista ordini/acquisti
- `GET /api/statistiche` - Statistiche vendite
- `GET /api/dashboard` - Dati dashboard
- `GET /api/ai-suggestion` - Suggerimento AI settimanale
- `POST /api/ai-suggestion/refresh` - Rigenera suggerimento
- `GET /api/alerts` - Alert gestione
- `GET/POST /api/ai-reports` - Report AI
- `DELETE /api/ai-reports/{id}` - Elimina report AI
- `GET /api/fornitori-with-stats` - Fornitori con fatturato calcolato
- `PUT /api/fornitori/{id}/note` - Aggiorna note fornitore
- `GET /api/fornitori/{nome}/prodotti` - Prodotti acquistati da fornitore

## Database Collections
- `clienti` - Anagrafica clienti
- `fornitori` - Anagrafica fornitori
- `prodotti` - Inventario prodotti
- `vendite` - Transazioni vendita
- `ordini` - Transazioni acquisto
- `ai_suggestions` - Cache suggerimenti AI
- `ai_reports` - Report AI generati

## Known Issues (Low Priority)
- Tooltip grafico a torta non interattivo in Stats.js
- Scraper news non recupera immagini per alcune fonti

## Future Tasks (Backlog)
- P2: Refactoring server.py in struttura modulare
- P2: Gestione quantità negative inventario
- P3: Revisione script originale Google Apps

---
Last Updated: 2026-02-15
