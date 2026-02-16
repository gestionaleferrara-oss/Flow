# Flow - Business Analytics App

## Descrizione Prodotto
Applicazione web full-stack per la gestione vendite, magazzino, clienti, fornitori e analytics business con funzionalità AI. Migrazione da Google Apps Script.

## Stack Tecnologico
- **Frontend**: React.js, Tailwind CSS, Recharts, Framer Motion
- **Backend**: FastAPI, Pydantic
- **Database**: MongoDB
- **AI**: Google Gemini (Emergent LLM Key)

## Funzionalità Implementate

### Core Features
- ✅ Import dati CSV/XLSX con gestione automatica clienti/prodotti
- ✅ Dashboard interattiva con 4 card principali (blur/reveal hover/click)
- ✅ Gestione Magazzino con scorte minime
- ✅ Pagina Clienti e Fornitori con analisi
- ✅ Sistema Alert (prodotti sotto scorta, clienti inattivi)
- ✅ Widget Trend Prodotti e Sales Insight
- ✅ News feed con ticker live

### AI Features
- ✅ **Report AI** con 3 tipi:
  - Settimanale (ultimi 7gg)
  - Mensile (ultimi 30gg)
  - **Dashboard** (confronto mese corrente vs precedente)
- ✅ **Forecast AI** - Previsioni vendite per prodotto/cliente con:
  - Analisi focalizzata SOLO sul mese target
  - Export PDF funzionante
  - Pulsante Reset
  - Funziona per prodotti E clienti

### UX/Performance
- ✅ Selettori periodo in TUTTI i modal (Mese corrente, Mese prec., 30gg, 90gg)
- ✅ Navigazione fluida con lazy loading
- ✅ Layout responsive ottimizzato
- ✅ Favicon e titolo personalizzati

## Changelog

### 2025-02-16
- **Report AI Dashboard**: Nuovo tipo report con confronto mese precedente, variazioni %, alert attivi
- **Forecast PDF**: Corretto export PDF (fix encoding caratteri speciali)
- **Selettore "Mese prec."**: Aggiunto a tutti i 4 modal card
- **Forecast migliorato**: Analisi focalizzata solo sul mese, pulsanti PDF/Reset

## Endpoints API
- `GET /api/dashboard-cards` - Dati card
- `GET /api/card-detail/{id}?periodo=` - Dettaglio (mese, mese_prec, 30gg, 90gg)
- `POST /api/ai-reports/generate?report_type=` - Report (settimanale, mensile, dashboard)
- `GET /api/forecast/generate?tipo=&nome=&mese_target=` - Previsione AI
- `POST /api/forecast/export-pdf` - Export PDF

## Backlog
- P2: Migliorare interfaccia mobile
- P3: Fix scraping immagini news
- P3: Refactoring Dashboard.jsx
