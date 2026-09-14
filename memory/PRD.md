# Flow - Business Analytics App

## Stack
- Frontend: React.js, Tailwind, Recharts
- Backend: FastAPI, MongoDB
- AI: Gemini (Emergent LLM Key)

## Funzionalità Principali

### Dashboard
- 4 card con blur/reveal
- Selettori periodo (Mese corrente, Mese prec., 30gg, 90gg)
- Widget Trend e Sales Insight
- Ricerca unificata prodotti/clienti
- Chat AI con fuzzy matching

### Statistiche
- Switch Vendite/Acquisti
- Filtri rapidi: 30gg, Questo mese, Mese prec., 3 mesi
- **Confronto Mese vs Mese** (NUOVO): seleziona 2 mesi e visualizza variazioni
- Filtri avanzati con autocomplete prodotti/clienti
- Export PDF/CSV
- Grafici: Andamento mensile, Top Clienti (pie), Top Prodotti (bar)

### Report AI
- 3 tipi: Settimanale, Mensile, Dashboard
- Export PDF

### Forecast AI
- Previsioni per 3 mesi (mese target + 2 successivi)
- Grafico barre con range min-max
- Analisi AI esaustiva

### Sidebar
- Icone navigazione principali
- **Pulsante AI unificato** con dropdown (Forecast AI, Report AI)
- **Upload** in fondo alla sidebar
- Status indicator

### Altre Funzionalità
- Import CSV/XLSX (incrementale o sovrascrittura)
- Gestione Magazzino con quantità minime
- Clienti e Fornitori con analisi dettagliata
- Sistema Alert (sotto scorta, clienti inattivi)
- News feed

## Endpoints Principali
- `GET /api/dashboard` - KPIs dashboard
- `GET /api/dashboard/card-detail/{type}?periodo=` - Dettagli card
- `GET /api/statistiche?prodotto=&cliente=&start_date=&end_date=` - Stats vendite
- `GET /api/statistiche/acquisti` - Stats acquisti
- `POST /api/ai-reports/generate?report_type=` - Genera report AI
- `GET /api/forecast/generate` - Previsioni AI
- `POST /api/ai-chat` - Chat AI con dati azienda

## Changelog

### 2026-03-03
- FIX: Dropdown AI sidebar ora appare fuori dalla sidebar (z-index fixed)
- NUOVO: Confronto mese vs mese nelle Statistiche
- FIX: Calcolo "Visite frequenti" ora conta giorni unici di ordine
- FIX: Filtri Autocomplete Statistiche funzionanti (componente estratto)

### 2026-02-28
- Ricerca unificata prodotti/clienti in Dashboard
- Chat AI con accesso a dati vendite, clienti, fornitori
- Fuzzy matching per ricerca entità
- Widget Trend con filtri toggle (richieste, fatturato, margine)
- Import incrementale per evitare perdita dati

### 2026-02-16
- Forecast AI: previsioni 3 mesi con range
- Report AI: export PDF
- Fix encoding PDF

## Known Issues
- (P1) AI Forecast: accuratezza da migliorare — MIGLIORATA (trend YoY più recente)
- (P2) Margine widget Trend: chiarire se assoluto o variazione
- (P3) Image scraper ilcorriereortofrutticolo non funziona

### 2026-03-31 (sessione 5)
- FIX Sidebar: icona AI ora solo colorata (nessun box/sfondo viola) - rimozione definitiva motion.div
- FIX UI Forecast: selettori mese+anno distinti (select nativo) al posto di input type=month
- NUOVO: pdf_helper.py — classe FlowPDF condivisa per tutti i report (header/footer brand, KPI box, tabelle stilizzate, grafico a barre, testo AI formattato)
- MIGLIORATO: PDF Vendite (KPI, trend mensile, top15 prodotti con margine, top15 clienti)
- MIGLIORATO: PDF Acquisti (KPI, top15 fornitori, trend mensile, top15 prodotti acquistati)
- MIGLIORATO: PDF Report AI (KPI metriche, contenuto AI formattato con sezioni)
- MIGLIORATO: PDF Forecast (KPI, tabella previsioni 3 mesi, storico grafico, analisi AI)

## Changelog

### 2026-03-31
- FIX (P1): Calcolo prezzi medi ora usa media ponderata (totale/qty) in tutti gli endpoint di prodotti.py
  - search_prodotti: rimosso `$avg: prezzo_unitario` → aggregazione `totale_sum/qty_sum`
  - storico-clienti: costo_medio acquisto ora ponderato su totale/qty ordini
  - storico-clienti: prezzoMedioVendita ora ponderato su totale/qty vendite
  - storico-clienti: storico prezzi mensile ora usa media ponderata
  - analisi-acquisti: variazione_prezzi mensile ora usa media ponderata

## Backlog
- Fatturazione/DDT
- Gestione Pagamenti
- Mobile optimization
- Refactoring Dashboard.jsx (file troppo grande)

### 2026-07-30 (sessione 6)
- MAGAZZINO: giacenza calcolata da carico/scarico (Acquisti ordini + Resi CARICO - Vendite SCARICO).
  - `recompute_all_quantities()` condivisa in prodotti.py, endpoint `/api/prodotti/recalculate-quantities`
  - Ricalcolo AUTOMATICO ad ogni upload (upload-csv, upload-multiple, upload-incremental)
  - Pulsante "Ricalcola giacenze" (data-testid=recalculate-btn) in Magazzino
  - Fix: import `Package` mancante in Magazzino.jsx
- DASHBOARD card ordini: sostituito "Picco" con "Media Ordini/Giorno" (media_ordini_giornaliera su giorni attivi) + tile Ordini Totali
- DASHBOARD card clienti: sostituito "Più Frequenti" (ridondante con Top 5) con "Clienti in Crescita" (delta spesa vs periodo precedente equivalente)
- FORECAST AI PDF: rimosse colonne Min/Max EUR, aggiunte colonne fatturato reale ultimi 2 anni (Fatt. AAAA), header trend chiarito "Trend 25 vs 24" + nota esplicativa; KPI "mesi dati" ora valorizzato
- UPLOAD: pulsante "Pulisci duplicati" (data-testid=pulisci-duplicati-btn) -> POST /api/pulisci-duplicati (dedup retroattivo su data+cliente/fornitore+prodotto)
- Testing agent: 100% backend (5/5), 100% frontend (4/4 flussi)

### 2026-09-14 (sessione 7) — Ottimizzazione riscritta
- Pagina Ottimizzazione semplificata: NESSUN selettore di date, solo "Previsione prossimi 7/15/30/60/90 gg" da oggi.
- Previsione = venduto reale nella STESSA finestra dell'anno precedente (oggi-365 → oggi-365+N).
- ACQUISTI: ordini completi raggruppati per FORNITORE (tutti gli articoli dello stesso fornitore consumati nella finestra), con domanda prevista, giacenza, copertura, da ordinare, prezzo, prezzo medio mercato, prezzo vendita, margine, valore.
- VENDITE: proposte d'ordine per CLIENTE (articoli comprati l'anno scorso in quei giorni) con stato "già ordinato / da proporre" e azione (CHIAMA ORA / CLIENTE FERMO / PROPONI / IN LINEA).
- Sezione SUGGERIMENTI: rinegozia (margine <10%), giacenze da smaltire, scorte sovrabbondanti; per vendite: clienti fermi, referenze da riproporre, prezzi da ritoccare.
- RIMOSSO su richiesta utente: ogni calcolo di "risparmio" (KPI, colonna, suggerimento cambio fornitore).
- Click su articolo -> drawer con VENDITE COMPLESSIVE PER CLIENTE (finestra anno scorso + ultimi 12 mesi) e acquisti per fornitore. Nuovo endpoint GET /api/ottimizzazione/piano/articolo.
- Endpoint: GET /api/ottimizzazione/piano?tipo=acquisti|vendite&giorni=N (nessun parametro data).
- Testato con curl (entrambi i tipi) + screenshot (tab acquisti, tab vendite, drawer).
