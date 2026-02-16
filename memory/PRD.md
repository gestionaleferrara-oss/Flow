# Flow - Business Analytics App

## Descrizione Prodotto
Applicazione web full-stack per la gestione vendite, magazzino, clienti, fornitori e analytics business con funzionalità AI. Migrazione da Google Apps Script.

## Stack Tecnologico
- **Frontend**: React.js, Tailwind CSS, Recharts, Framer Motion, React.lazy + Suspense
- **Backend**: FastAPI, Pydantic
- **Database**: MongoDB
- **AI**: Google Gemini (Emergent LLM Key) per report e previsioni

## Funzionalità Implementate

### Core Features
- ✅ Import dati CSV/XLSX con gestione automatica clienti/prodotti
- ✅ Dashboard interattiva con 4 card principali (blur/reveal con hover e click)
- ✅ Gestione Magazzino con scorte minime e date scadenza
- ✅ Pagina Clienti con analisi dettagliate
- ✅ Pagina Fornitori con statistiche acquisti
- ✅ Sistema Alert (prodotti sotto scorta, clienti inattivi, in esaurimento)
- ✅ Widget Trend Prodotti e Sales Insight ottimizzati
- ✅ News feed con ticker live

### AI Features
- ✅ Report AI settimanali/mensili (esclusi dati magazzino)
- ✅ **Forecast AI** - Previsioni vendite per prodotto/cliente con analisi storica

### UX/Performance
- ✅ Navigazione fluida con lazy loading e prefetching
- ✅ Card dashboard: blur di default, hover reveal (desktop), tap toggle (mobile)
- ✅ Selettori periodo nei modali (Fatturato, Ordini, Alert)
- ✅ Layout responsive ottimizzato
- ✅ Favicon e titolo personalizzati ("Flow | Business Analytics")

## Changelog Recente

### 2025-02-16
- **Fix hover card desktop**: Corretto rilevamento dispositivo (`pointer: coarse` invece di `ontouchstart`)
- **Fix modal Alert**: Ridotta larghezza (`sm:max-w-lg`) e risolto scroll orizzontale
- **Nuova pagina Forecast AI**: 
  - Selezione prodotto/cliente con ricerca
  - Selettore mese target
  - Grafico storico vendite
  - Previsione AI con range, analisi stagionalità, suggerimenti
- **Fix AI Reports**: Rimossi dati magazzino/stock dai report
- **Favicon**: Aggiunto favicon personalizzato Flow

## Endpoints API Chiave
- `GET /api/dashboard-cards` - Dati card principali
- `GET /api/card-detail/{card_id}?periodo=` - Dettaglio card con periodo
- `GET /api/sales-insight` - Widget insight (ottimizzato)
- `GET /api/forecast/prodotti?search=` - Ricerca prodotti per forecast
- `GET /api/forecast/clienti?search=` - Ricerca clienti per forecast  
- `GET /api/forecast/generate?tipo=&nome=&mese_target=` - Genera previsione AI
- `POST /api/ai-reports/generate` - Genera report AI

## Prossimi Task (Backlog)

### P1
- Aggiungere dati "mese precedente" visibili a tutte le 4 card principali

### P2
- Migliorare interfaccia mobile (tabelle, visualizzazione dati)

### P3
- Fix scraping immagini per `ilcorriereortofrutticolo`
- Refactoring Dashboard.jsx in componenti più piccoli

## File di Riferimento Principali
```
/app/
├── backend/
│   ├── server.py
│   ├── routes/
│   │   ├── dashboard.py (card, AI reports)
│   │   ├── forecast.py (previsioni AI)
│   │   ├── clienti.py, fornitori.py, prodotti.py
│   └── database.py
└── frontend/
    ├── src/
    │   ├── App.js (routing)
    │   ├── components/
    │   │   ├── StatCard.jsx (card con blur/hover)
    │   │   └── Sidebar.jsx (navigazione)
    │   └── pages/
    │       ├── Dashboard.jsx
    │       ├── Forecast.jsx (nuovo)
    │       ├── Clienti.jsx, Fornitori.jsx
    └── public/
        └── index.html (favicon, title)
```
