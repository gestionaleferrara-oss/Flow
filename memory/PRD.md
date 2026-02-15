# Flusso - Gestione Aziendale Ortofrutta

## Descrizione
Applicazione web full-stack per la gestione aziendale nel settore ortofrutticolo. Migrazione da Google Apps Script a architettura moderna.

## Stack Tecnologico
- **Frontend**: React.js, Tailwind CSS, Framer Motion, Recharts
- **Backend**: FastAPI, Python
- **Database**: MongoDB
- **UI Components**: Shadcn/UI

## Funzionalità Implementate

### Core Features
- [x] Upload CSV/XLSX per importazione dati vendite e acquisti
- [x] Gestione automatica clienti, fornitori, prodotti
- [x] Calcolo automatico quantità magazzino (CARICO/SCARICO)
- [x] Dashboard con KPI e attività recenti

### Pagine
- [x] **Dashboard**: Overview con statistiche, suggerimenti AI, ricerca prodotti
- [x] **Importa Dati**: Upload file CSV/XLSX
- [x] **Magazzino**: Gestione prodotti con quantità e quantità minima editabile
- [x] **Vendite**: Raggruppamento per cliente/data con righe espandibili
- [x] **Clienti**: Lista con analisi dettagliata e campi editabili (WhatsApp, Email, Note)
- [x] **Fornitori**: Gestione fornitori
- [x] **Acquisti**: Raggruppamento per fornitore/data con righe espandibili
- [x] **Statistiche**: Grafici vendite, top clienti, top prodotti, trend
- [x] **Notizie**: Feed RSS da fonti ortofrutta

### Funzionalità Recenti (15/02/2025)
- [x] Pagina Acquisti con raggruppamento (come Vendite)
- [x] Scheda Analisi Cliente con campi editabili
- [x] Ricerca prodotti da Dashboard con modal dedicato
- [x] Suggerimento AI settimanale basato sui dati aziendali
- [x] Filtro "SCARICO VENDUTO" da tutte le statistiche clienti
- [x] Nuove statistiche prodotto: Fatturato Mensile, Trend, Clienti Unici

## API Endpoints Principali
- `POST /api/upload-csv` - Upload file dati
- `GET /api/dashboard` - Dati dashboard
- `GET /api/ai-suggestion` - Suggerimento AI settimanale
- `GET /api/clienti` - Lista clienti
- `PUT /api/clienti/{id}` - Aggiorna cliente
- `GET /api/clienti/{id}/analisi` - Analisi cliente
- `GET /api/prodotti` - Lista prodotti
- `GET /api/prodotti/{nome}/analisi` - Analisi prodotto
- `GET /api/vendite` - Vendite
- `GET /api/ordini` - Acquisti
- `GET /api/statistiche` - Statistiche vendite

## Backlog / Future Tasks

### P1 - Alta Priorità
- [ ] Fix tooltip grafico a torta (hover non funziona)
- [ ] Fix scraper notizie per immagini ilcorriereortofrutticolo

### P2 - Media Priorità
- [ ] Refactoring server.py in struttura modulare (routes, services, models)
- [ ] Notifica UI per quantità negative in magazzino
- [ ] Review originale Google Apps Script per features mancanti

### P3 - Bassa Priorità
- [ ] Esportazione dati in PDF/Excel
- [ ] Backup automatico database
- [ ] Dashboard mobile-responsive migliorata

## Note Tecniche
- Le quantità negative in magazzino sono tecnicamente corrette (più vendite che carichi registrati)
- Il suggerimento AI viene cachato per settimana nel database
- "SCARICO VENDUTO" è escluso da tutte le statistiche clienti
