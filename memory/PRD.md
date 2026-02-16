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
- ✅ **Forecast AI** - Previsioni vendite per prodotto/cliente con:
  - Analisi focalizzata sul mese target
  - Export PDF
  - Tasto Reset
  - Formattazione AI migliorata

### UX/Performance
- ✅ Navigazione fluida con lazy loading e prefetching
- ✅ Card dashboard: blur di default, hover reveal (desktop), tap toggle (mobile)
- ✅ **Selettori periodo in TUTTI i modal** (Mese corrente, Mese prec., 30gg, 90gg)
- ✅ Layout responsive ottimizzato
- ✅ Favicon e titolo personalizzati ("Flow | Business Analytics")

## Changelog Recente

### 2025-02-16 (Sessione corrente)
- **Selettore "Mese precedente"**: Aggiunto a tutti i 4 modal delle card dashboard (Fatturato, Ordini, Clienti, Alert)
- **Forecast AI migliorato**:
  - Previsione ora focalizzata SOLO sul mese selezionato
  - Aggiunto pulsante "PDF" per esportazione
  - Aggiunto pulsante "Reset" per nuova ricerca
  - Funziona sia per prodotti che per clienti
  - Formattazione testo AI migliorata con colori e bullet points
- **Fix hover card desktop**: Corretto rilevamento dispositivo
- **Fix modal Alert**: Ridotta larghezza e rimosso scroll orizzontale

## Endpoints API Chiave
- `GET /api/dashboard-cards` - Dati card principali
- `GET /api/card-detail/{card_id}?periodo=` - Dettaglio card (mese, mese_prec, 30gg, 90gg)
- `GET /api/forecast/prodotti?search=` - Ricerca prodotti per forecast
- `GET /api/forecast/clienti?search=` - Ricerca clienti per forecast  
- `GET /api/forecast/generate?tipo=&nome=&mese_target=` - Genera previsione AI
- `POST /api/forecast/export-pdf` - Esporta forecast in PDF
- `POST /api/ai-reports/generate` - Genera report AI

## Prossimi Task (Backlog)

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
│   │   ├── dashboard.py (card, AI reports, selettori periodo)
│   │   ├── forecast.py (previsioni AI, export PDF)
│   │   ├── clienti.py, fornitori.py, prodotti.py
│   └── database.py
└── frontend/
    ├── src/
    │   ├── App.js (routing)
    │   ├── components/
    │   │   ├── StatCard.jsx (card con blur/hover)
    │   │   └── Sidebar.jsx (navigazione)
    │   └── pages/
    │       ├── Dashboard.jsx (modal con selettori periodo)
    │       ├── Forecast.jsx (PDF, Reset, ricerca clienti)
    │       ├── Clienti.jsx, Fornitori.jsx
    └── public/
        └── index.html (favicon, title)
```
