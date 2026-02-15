# Flusso - Gestione Aziendale Ortofrutta

## Descrizione
Applicazione web full-stack per la gestione aziendale nel settore ortofrutticolo italiano. Migrazione da Google Apps Script a architettura moderna con funzionalità AI integrate.

## Stack Tecnologico
- **Frontend**: React.js, Tailwind CSS, Framer Motion, Recharts
- **Backend**: FastAPI, Python
- **Database**: MongoDB
- **UI Components**: Shadcn/UI
- **Font**: Plus Jakarta Sans (fintech style)
- **AI**: OpenAI GPT-4o via Emergent LLM Key

## Funzionalità Implementate

### Core Features
- [x] Upload CSV/XLSX per importazione dati vendite e acquisti
- [x] Gestione automatica clienti, fornitori, prodotti
- [x] Calcolo automatico quantità magazzino (CARICO/SCARICO)
- [x] Dashboard con KPI, alert e suggerimenti AI

### Pagine
- [x] **Dashboard**: Overview con statistiche, suggerimenti AI, ricerca prodotti, Centro Alert
- [x] **Importa Dati**: Upload file CSV/XLSX
- [x] **Magazzino**: Gestione prodotti con quantità e quantità minima editabile
- [x] **Vendite**: Raggruppamento per cliente/data con righe espandibili
- [x] **Clienti**: Lista con analisi dettagliata e campi editabili (WhatsApp, Email, Note)
- [x] **Fornitori**: Gestione fornitori
- [x] **Acquisti**: Raggruppamento per fornitore/data con righe espandibili
- [x] **Statistiche**: Grafici vendite, top clienti, top prodotti, trend
- [x] **Report AI**: Report automatici settimanali/mensili generati dall'AI
- [x] **Notizie**: Feed RSS da fonti ortofrutta

### Funzionalità AI (15/02/2025)
- [x] **Report AI Automatici**: Generazione report settimanali/mensili con GPT-4o
- [x] **Suggerimenti AI**: Consigli personalizzati basati sui dati aziendali
- [x] **Centro Alert**: Prodotti sotto scorta, clienti inattivi, prodotti in esaurimento
- [x] **Analisi Prodotto**: Fatturato mensile, prezzo medio vendita, trend, clienti unici

## API Endpoints Principali
- `POST /api/upload-csv` - Upload file dati
- `GET /api/dashboard` - Dati dashboard
- `GET /api/alerts` - Alert gestione (scorte, clienti, esaurimenti)
- `GET /api/ai-suggestion` - Suggerimento AI settimanale
- `POST /api/ai-suggestion/refresh` - Nuovo suggerimento AI
- `GET /api/ai-reports` - Lista report AI
- `POST /api/ai-reports/generate` - Genera nuovo report AI
- `GET /api/clienti/{id}/analisi` - Analisi cliente
- `GET /api/prodotti/{nome}/analisi` - Analisi prodotto con prezzo medio vendita

## Credenziali
- **EMERGENT_LLM_KEY**: Configurata in `/app/backend/.env` per generazione report AI

## Backlog / Future Tasks

### P1 - Alta Priorità
- [ ] Fix tooltip grafico a torta (hover non funziona)
- [ ] Fix scraper notizie per immagini ilcorriereortofrutticolo

### P2 - Media Priorità
- [ ] Refactoring server.py in struttura modulare (routes, services, models)
- [ ] Notifiche WhatsApp per scorte basse
- [ ] Esportazione report AI in PDF

### P3 - Bassa Priorità
- [ ] Esportazione dati in Excel
- [ ] Backup automatico database
- [ ] Dashboard mobile-responsive migliorata

## Note Tecniche
- I report AI vengono generati con GPT-4o e salvati nel database
- Il suggerimento settimanale viene cachato per settimana
- "SCARICO VENDUTO" è escluso da tutte le statistiche clienti
- Font Plus Jakarta Sans per look professionale fintech
