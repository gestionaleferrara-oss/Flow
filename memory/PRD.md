# Gestio - Business Manager PRD

## Original Problem Statement
L'utente vuole migrare un'applicazione esistente (Google Apps Script) per la gestione di un magazzino ortofrutticolo a un'applicazione web moderna con:
1. **Upload CSV** per importare vendite/acquisti
2. **Auto-riconoscimento** delle colonne prezzo e totale pagato
3. **Statistiche avanzate** filtrabili per periodo, prodotto e cliente  
4. **UI Glassmorphism** moderna come Apple iOS
5. **Notizie di mercato** con preview, prezzi mercati e meteo

## Tech Stack
- **Frontend**: React 18, Tailwind CSS, Framer Motion, Recharts
- **Backend**: FastAPI (Python)
- **Database**: MongoDB

## Core Features Implemented ✅

### 1. CSV Upload & Import
- Drag & drop file upload
- **Auto-detection** delle colonne CSV (Movimento, Data, Importo Unitario, Importo Totale, Quantità)
- Supporto encoding UTF-8, Latin-1, Windows-1252
- Parsing numeri italiano (virgola decimale, punto migliaia, simbolo €)
- Creazione automatica clienti/fornitori/prodotti

### 2. Dashboard
- KPI cards (Fatturato mese, Ordini, Nuovi clienti, Prodotti da riordinare)
- Quick links per navigazione rapida
- Attività recenti

### 3. Statistiche Avanzate
- Filtri per prodotto, cliente, data inizio/fine
- Preset: Ultimi 30 giorni, Mese corrente, Mese precedente
- Grafici: Andamento vendite mensili (Area chart), Top clienti (Pie chart)
- KPI: Totale vendite €, Articoli venduti, Clienti attivi

### 4. Gestione Magazzino
- Lista prodotti con ricerca
- Filtri: Da ordinare, In scadenza
- Dettagli: Quantità, Kg/pz, Prezzo, Valore scorte, Stato

### 5. Notizie di Mercato
- **Widget Meteo** con previsioni (Open-Meteo API)
- **Widget Prezzi Mercati** (Bologna, Milano, Roma, Torino, Verona, Padova)
- News cards con immagini preview da RSS feeds (ANSA, Il Sole 24 Ore)
- Filtri per categoria (Tutte, Finanza, Economia)
- Refresh manuale

### 6. CRUD Completo
- Clienti: lista, dettaglio, analisi acquisti
- Fornitori: lista, dettaglio
- Vendite: lista, filtri
- Ordini/Acquisti: lista, filtri

## UI/UX Design
- **Glassmorphism** premium con effetti blur e trasparenze
- **Aurora animated background** con gradient orbs
- **Noise texture** overlay
- **Cards** con hover effects e glow
- **Responsive** sidebar navigation
- **Dark theme** con accenti blu/viola

## API Endpoints

### Core
- `POST /api/upload-csv` - Import CSV con auto-detection colonne
- `GET /api/dashboard` - Overview dashboard
- `GET /api/statistiche` - Statistiche filtrabili

### Resources
- `GET/POST /api/clienti` - CRUD clienti
- `GET/POST /api/fornitori` - CRUD fornitori
- `GET/POST /api/prodotti` - CRUD prodotti
- `GET /api/vendite` - Lista vendite
- `GET /api/ordini` - Lista ordini

### Utilities
- `GET /api/notizie` - News da RSS feeds
- `POST /api/notizie/refresh` - Aggiorna news
- `GET /api/meteo` - Dati meteo (Open-Meteo)
- `GET /api/prezzi-mercati` - Link prezzi mercati

## Data Model

### Vendita
```json
{
  "id": "uuid",
  "data": "YYYY-MM-DD",
  "cliente_id": "uuid",
  "cliente_nome": "string",
  "prodotto_nome": "string",
  "quantita": "float",
  "prezzo_unitario": "float",
  "totale": "float",
  "movimento": "SCARICO|CARICO"
}
```

### Prodotto
```json
{
  "id": "uuid",
  "nome": "string",
  "codice": "string",
  "quantita": "float",
  "kg_per_pezzo": "float",
  "quantita_minima": "float",
  "prezzo_medio": "float",
  "scadenza": "YYYY-MM-DD"
}
```

## Known Issues / Future Improvements

### P1 - High Priority
- [ ] RSS feeds: alcune fonti potrebbero non essere raggiungibili (FreshPlaza, Italiafruit)
- [ ] Notizie agricoltura: aggiungere fonti RSS specifiche per ortofrutta

### P2 - Medium Priority
- [ ] Export dati in Excel/PDF
- [ ] Notifiche prodotti in scadenza
- [ ] Storico prezzi prodotti
- [ ] Multi-utente con autenticazione

### P3 - Low Priority
- [ ] Mobile app (React Native)
- [ ] Integrazione con bilance/lettori barcode
- [ ] Analisi predittiva con AI

## Changelog

### 2026-02-15
- ✅ Implementato auto-detection colonne CSV
- ✅ Corretto parsing numeri italiani con \x80 (€ Windows-1252)
- ✅ Corretto calcolo statistiche con valori assoluti (SCARICO ha valori negativi)
- ✅ Implementata pagina Notizie con widget meteo e prezzi mercati
- ✅ Aggiornato design glassmorphism su tutte le pagine
- ✅ RSS feeds funzionanti (ANSA, Il Sole 24 Ore)
