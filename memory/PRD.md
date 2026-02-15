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
- Lista vendite raggruppabili/espandibili (fix: rimosso motion.tbody annidato)
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
- Filtri: prodotto, cliente/fornitore, date, preset (30gg, mese corrente, mese precedente, 3 mesi)
- KPI visibili SOLO con almeno un filtro attivo
- Grafici: AreaChart/BarChart, PieChart, HBarChart
- Export CSV/Excel

### Report AI
- Generazione report con Gemini Pro
- Lista report salvati con eliminazione

### Notizie
- Feed RSS (FreshPlaza, Corriere Ortofrutticolo, MyFruit)
- Widget meteo Bologna
- Widget prezzi mercati ingrosso

## Sidebar
- Solo icone (76px fissi)
- Hover su singolo item: popup con zoom icona+testo (effetto wow)
- Glow cyan, ombra, animazione spring framer-motion
- Footer con indicatore online

## Integrazioni 3rd Party
- `feedparser` + `beautifulsoup4`: RSS e scraping notizie
- `emergentintegrations` + Gemini Pro: AI suggestions e reports
- Open-Meteo API: dati meteo
- FreshPlaza scraping: prezzi mercati ingrosso

## Schema DB Chiave
- `vendite`: transazioni vendita (SCARICO)
- `ordini`: transazioni acquisto (CARICO)
- `clienti`: anagrafica clienti
- `fornitori`: anagrafica fornitori + note
- `prodotti`: inventario con quantita, prezzi, scadenze
- `notizie`: articoli news cached
- `reports`: report AI generati
- `ai_suggestions`: cache suggerimenti settimanali

## Issue Note
- **Prezzi nel DB**: Possibile arrotondamento durante import CSV. Fix temporaneo: frontend ricalcola prezzo x quantita
- **Pie chart tooltip**: Funzionante con Tooltip di recharts standard
- **News scraper immagini**: Funzionante per MyFruit, problemi intermittenti con altri feed

## Completato (15 Feb 2026)
- Fix tabella Vendite (rimosso motion.tbody annidato, usato React.Fragment)
- Sidebar effetto wow: solo icone, hover mostra popup zoomato con icona+testo su singolo item
- KPI Statistiche visibili solo con filtri attivi

## Backlog Prioritizzato
- P1: Fix totali prezzi errati durante import CSV/XLSX (backend)
- P2: Implementare export PDF statistiche
- P2: Fix tooltip pie chart
- P3: Fix news scraper immagini
- P1: Refactoring backend/server.py in moduli
- P3: Revisione Google Apps Script per feature mancanti
