# Flusso - Gestione Aziendale

## Problem Statement
Migrazione di un'applicazione Google Apps Script a un'applicazione web full-stack moderna per la gestione aziendale di un'attività ortofrutticola.

## Core Requirements
1. **Data Import**: Caricamento CSV/XLSX con vendite, automaticamente crea clienti/prodotti
2. **Inventory Management (Magazzino)**: Visualizza stock con quantità minime editabili
3. **Sales Tracking (Vendite)**: Storico vendite con dettaglio prodotti per cliente/giorno
4. **Statistics Dashboard**: Grafici vendite mensili, top clienti, top prodotti
5. **News Feed**: Notizie dal settore ortofrutticolo

## Tech Stack
- **Frontend**: React.js, Tailwind CSS, Recharts, Framer Motion
- **Backend**: FastAPI, Python
- **Database**: MongoDB

## Current Status: MVP Operational

### Implemented Features
- [x] Upload CSV/XLSX con parsing automatico
- [x] Dashboard con KPI principali
- [x] Grafico a torta Top Clienti con percentuali
- [x] Grafico andamento vendite mensili
- [x] Trend clienti attivi (ultimi 7 giorni)
- [x] Magazzino con Q.tà importata (non editabile) e Q.tà Minima (editabile)
- [x] Vendite raggruppate per cliente/giorno con espansione dettagli
- [x] Calcolo automatico quantità prodotti da movimenti CARICO/SCARICO
- [x] Esclusione "SCARICO VENDUTO" e "CLIENTE CORRISPETTIVI" dalle statistiche
- [x] Font Quicksand e nome app "Flusso"
- [x] Spinner soft senza testo

### Known Issues
- Alcuni prodotti mostrano quantità negative (vendite > carichi nel DB)
- Il tooltip del pie chart potrebbe non essere visibile in tutti i browser

### API Endpoints
- POST `/api/upload-csv` - Import dati
- GET `/api/statistiche` - KPI e grafici
- GET `/api/statistiche/clienti-trend` - Trend clienti 7 giorni
- GET `/api/prodotti` - Lista prodotti con filtri
- POST `/api/prodotti/recalculate-quantities` - Ricalcola quantità
- PUT `/api/prodotti/{id}` - Aggiorna Q.tà Minima/Scadenza
- GET `/api/vendite` - Lista vendite raggruppate

## Backlog (P2)
- [ ] Migliorare scraping immagini notizie
- [ ] Refactoring server.py in moduli
- [ ] Report esportabili
