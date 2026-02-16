# Flusso - Gestione Magazzino e Vendite

## Descrizione
Applicazione web per la gestione di magazzino, vendite e acquisti per aziende del settore ortofrutticolo. Migrazione da Google Apps Script a stack moderno.

## Stack Tecnologico
- **Frontend**: React.js, Tailwind CSS, Framer Motion, Recharts
- **Backend**: FastAPI, Python, Pandas
- **Database**: MongoDB
- **Integrazioni**: Google Trends (pytrends), RSS feeds, Web scraping

## Funzionalità Implementate

### Data Import & Processing (v1.0 - 16/02/2026)
- Upload singolo e multiplo di file CSV/XLSX
- Gestione automatica di tutte le causali
- Calcolo automatico quantità magazzino
- Indici MongoDB per query veloci

### Dashboard (v1.3 - 16/02/2026) ⭐ OTTIMIZZATO
- KPI compatte (Fatturato, Ordini, Clienti, Alert)
- Suggerimento AI con refresh
- **Sales Insight** - 4 insight con hover tooltip per dettagli
- **Trend Prodotti** - Top 5 con **popup hover** per Top 20 + filtri
- **Quick Links** compatti (Importa, Stats, Magazzino)
- Centro Alert compatto (Sotto Scorta, Inattivi, Esaurimento)
- **Responsive mobile/tablet** - Grid adattivo
- **Caricamento parallelo** - Tutte le API caricate in parallelo

### Statistiche (v1.0)
- Grafico andamento vendite mensili
- Grafico a torta Top Clienti con tooltip funzionante
- Top Prodotti per fatturato
- Export CSV/Excel

### Notizie & Mercati (v1.3 - 16/02/2026) ⭐ AGGIORNATO
- Widget Meteo Bologna (previsioni 7 giorni)
- **Breaking News LIVE** - ticker scrollabile con notizie settore
- **Listini Mercato DINAMICI** - Scraping automatico da FreshPlaza
  - Link diretti ai PDF aggiornati (Cesena, Lusia, Torino, Verona, etc.)
  - Fallback a link statici se scraping fallisce
- Griglia notizie con immagini e filtri categoria

### Magazzino (v1.0)
- Visualizzazione prodotti con quantità
- Quantità minima e scadenza editabili

### Vendite/Ordini (v1.0)
- Storico vendite/acquisti raggruppati
- Dettaglio espandibile

### Clienti/Fornitori (v1.0)
- Schede con statistiche dettagliate

### Report AI (v1.0)
- Generazione report con Gemini Pro

## API Endpoints Principali

### Dashboard & Stats
- GET /api/dashboard
- GET /api/statistiche
- GET /api/alerts

### Data Import
- POST /api/upload-csv
- POST /api/upload-multiple

### Notizie & Trends
- GET /api/notizie
- POST /api/notizie/refresh
- GET /api/meteo
- GET /api/prezzi-mercati
- GET /api/trends-vendite (NEW - Top 5 prodotti venduti)
- GET /api/trends/{categoria} (Google Trends)
- GET /api/ticker-news

## Backlog / Future Tasks

### P2 - Media Priorità
- [ ] Export PDF statistiche

### P3 - Bassa Priorità
- [ ] Refactoring server.py in moduli
- [ ] Miglioramento scraper immagini notizie

## Note Tecniche

### Trends Vendite
- Confronto ultime 2 settimane vs 2 settimane precedenti
- Basato sulla data più recente nel database
- Mostra Top 5 per quantità venduta

### Performance
- Indici MongoDB su campi: data, cliente_nome, prodotto_nome
- Cache 6 ore per Google Trends

## Ultimo Aggiornamento
16 Febbraio 2026
