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
- Gestione automatica di tutte le causali:
  - VENDITA → Vendite a clienti
  - C/ACQUISTO → Acquisti da fornitori
  - CESSIONE GRATUITA / CAMPIONE OMAGGIO → Omaggi
  - RESO SU ACQUISTI → Resi a fornitori
  - RETTIFICHE, TRASFERIMENTO INT., VUOTATI → Movimenti interni
- Calcolo automatico quantità magazzino
- Pre-caricamento cache per performance ottimizzate
- Indici MongoDB per query veloci

### Dashboard (v1.0)
- Fatturato mese corrente vs mese precedente completo
- Percentuale crescita/decrescita
- Ordini del mese
- Nuovi clienti
- Suggerimento AI settimanale
- Centro Alert (clienti inattivi, prodotti in esaurimento, sotto scorta)

### Statistiche (v1.0)
- Grafico andamento vendite mensili
- Grafico a torta Top Clienti con tooltip funzionante
- Top Prodotti per fatturato
- Filtri per periodo, cliente, prodotto
- Export CSV/Excel

### Notizie & Mercati (v1.0)
- Widget Meteo Bologna
- Listini prezzi mercati (Cesena, Lusia, Torino, Verona)
- Google Trends Italia con switch categorie:
  - Frutta Secca
  - Frutta
  - Verdura
  - Spezie
- News ticker live da fonti esterne
- Griglia notizie con immagini

### Magazzino (v1.0)
- Visualizzazione prodotti con quantità
- Quantità minima editabile
- Scadenza editabile
- Ricerca prodotti

### Vendite/Ordini (v1.0)
- Storico vendite raggruppate per cliente/data
- Storico acquisti raggruppati per fornitore/data
- Dettaglio espandibile

### Clienti/Fornitori (v1.0)
- Schede clienti con statistiche
- Schede fornitori con statistiche
- Analisi dettagliata per cliente/fornitore

### Report AI (v1.0)
- Generazione report con Gemini Pro
- Storico report salvati

## Backlog / Future Tasks

### P2 - Media Priorità
- [ ] Export PDF statistiche
- [ ] Miglioramento scraper immagini notizie

### P3 - Bassa Priorità
- [ ] Refactoring server.py in moduli separati
- [ ] Revisione completa script Google Apps originale

## API Endpoints Principali

### Dashboard & Stats
- GET /api/dashboard - Overview dashboard
- GET /api/statistiche - Statistiche vendite/acquisti
- GET /api/alerts - Alert gestione

### Data Import
- POST /api/upload-csv - Upload singolo file
- POST /api/upload-multiple - Upload multiplo file

### CRUD
- GET/POST /api/clienti - Clienti
- GET/POST /api/fornitori - Fornitori
- GET/POST /api/prodotti - Prodotti
- GET /api/vendite - Vendite
- GET /api/ordini - Ordini/Acquisti

### Notizie & Trends
- GET /api/notizie - News
- GET /api/meteo - Meteo Bologna
- GET /api/prezzi-mercati - Listini mercati
- GET /api/trends/{categoria} - Google Trends per categoria
- GET /api/ticker-news - Breaking news ticker

### AI
- GET /api/ai-suggestion - Suggerimento settimanale
- GET/POST /api/ai-reports - Report AI

## Note Tecniche

### Date Reference
Il sistema usa la data più recente nel database come riferimento per:
- Calcolo fatturato mese corrente
- Calcolo clienti inattivi
- Confronti mese precedente

### Performance
- Indici MongoDB su campi: data, cliente_nome, prodotto_nome, fornitore_nome
- Pre-caricamento cache durante upload
- Aggregation pipeline per query pesanti
- Cache 6 ore per Google Trends

## Ultimo Aggiornamento
16 Febbraio 2026
