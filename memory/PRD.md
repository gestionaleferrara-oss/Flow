# Flusso - PRD (Product Requirements Document)

## Problema Originale
Migrazione di un'applicazione Google Apps Script verso un'app web full-stack moderna chiamata "Flusso" per la gestione aziendale del settore ortofrutticolo.

## Architettura
- **Frontend**: React.js + Tailwind CSS + Recharts + Framer Motion
- **Backend**: FastAPI + Motor (MongoDB async) + Pandas
- **Database**: MongoDB
- **AI**: Gemini Pro via Emergent LLM Key

## Pagine e Funzionalita

### Dashboard
- KPI: fatturato mese, ordini, clienti, prodotti da ordinare
- Suggerimento AI settimanale
- Centro allerta (scadenze, scorte basse)
- Modal analisi prodotto con switch Vendite/Acquisti

### Importa Dati
- Upload CSV/XLSX con auto-detect colonne
- Gestione CARICO (acquisti) e SCARICO (vendite)
- Aggiornamento automatico clienti, fornitori, prodotti, magazzino

### Magazzino
- Tabella prodotti con quantita, prezzo medio, scadenza
- Quantita minima editabile, quantita non negativa
- Filtri: da ordinare, in scadenza
- Stato con icone

### Vendite
- Lista vendite raggruppabili/espandibili (fix: React.Fragment)
- Ricerca con debounce
- Totali calcolati come prezzo x quantita
- Cancellazione vendite (per periodo o tutte)

### Acquisti (Ordini)
- Lista acquisti con stesso layout vendite
- Ricerca con debounce

### Clienti
- Anagrafica con fatturato, note editabili
- Modal analisi dettagliata

### Fornitori
- Anagrafica con fatturato annuale filtrabile per anno
- Note editabili inline
- Modal acquisti per fornitore con selettore mese

### Statistiche
- Switch Vendite/Clienti - Acquisti/Fornitori
- Filtri: prodotto, cliente/fornitore, date, preset
- KPI visibili SOLO con almeno un filtro attivo
- Grafici: AreaChart/BarChart, PieChart, HBarChart
- Export CSV/Excel

### Report AI
- Generazione report con Gemini Pro
- Lista report salvati con eliminazione

### Notizie & Mercati (REDESIGNED 15 Feb 2026)
- 3 widget in riga:
  1. Meteo compatto Bologna: temp attuale, vento, min/max, previsioni 4gg
  2. Listini Mercato: link PDF prezzi ingrosso 8 citta
  3. **Trend Frutta Secca (NUOVO)**: Google Trends Italia per pistacchi, mandorle, noci, nocciole, anacardi con sparkline, % variazione, interesse/100
- Hero article full-width
- Griglia magazine-style con zoom hover
- Filtri categoria con conteggio

## Sidebar
- Solo icone (76px fissi)
- Hover su singolo item: popup fixed con zoom icona+testo (effetto wow)
- Anti-flicker con delay timer su mouseLeave

## Integrazioni 3rd Party
- `feedparser` + `beautifulsoup4`: RSS e scraping notizie
- `emergentintegrations` + Gemini Pro: AI suggestions e reports
- Open-Meteo API: dati meteo
- FreshPlaza scraping: prezzi mercati ingrosso
- `pytrends`: Google Trends API per frutta secca (NUOVO)

## Schema DB Chiave
- `vendite`, `ordini`, `clienti`, `fornitori`, `prodotti`, `notizie`, `reports`, `ai_suggestions`
- `cache`: cache per trends Google (TTL 6h)

## Completato
- 15 Feb 2026: Fix tabella Vendite, Sidebar effetto wow, KPI Statistiche condizionali
- 15 Feb 2026: Redesign pagina Notizie & Mercati + widget Trend Frutta Secca (Google Trends)

## Backlog Prioritizzato
- P1: Fix totali prezzi errati durante import CSV/XLSX (backend)
- P2: Implementare export PDF statistiche
- P2: Fix tooltip pie chart
- P3: Fix news scraper immagini
- P1: Refactoring backend/server.py in moduli
- P3: Revisione Google Apps Script per feature mancanti
