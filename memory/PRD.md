# Flusso - PRD (Product Requirements Document)

## Problema Originale
Migrazione di un'applicazione Google Apps Script verso un'app web full-stack moderna chiamata "Flusso" per la gestione aziendale del settore ortofrutticolo.

## Architettura
- **Frontend**: React.js + Tailwind CSS + Recharts + Framer Motion
- **Backend**: FastAPI + Motor (MongoDB async) + Pandas
- **Database**: MongoDB
- **AI**: Gemini Pro via Emergent LLM Key

## Pagine e Funzionalità

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
- Tabella prodotti con quantità, prezzo medio, scadenza
- Quantità minima editabile
- Filtri: da ordinare, in scadenza

### Vendite
- Lista vendite raggruppabili/espandibili
- Ricerca con debounce
- Totali calcolati come prezzo × quantità

### Acquisti (Ordini)
- Lista acquisti con stesso layout vendite
- Ricerca con debounce

### Clienti
- Anagrafica con fatturato, note editabili
- Modal analisi dettagliata

### Fornitori
- Anagrafica con fatturato annuale filtrabile per anno (selettore nel titolo colonna)
- Note editabili inline
- Modal acquisti per fornitore con:
  - Selettore mese tra i mesi disponibili
  - Righe singole d'acquisto (prodotto, quantità, prezzo unitario, totale, data)
  - Riepilogo: n. acquisti, totale speso, mese di riferimento

### Statistiche
- Switch Vendite/Clienti ↔ Acquisti/Fornitori
- Filtri: prodotto, cliente/fornitore, date, preset (30gg, mese corrente, mese precedente, 3 mesi)
- KPI del periodo filtrato (NO totali cumulativi):
  - Vendite: Fatturato Periodo, Articoli Venduti, Clienti Attivi
  - Acquisti: Speso Periodo, Articoli Acquistati, Fornitori Attivi
- Grafici: AreaChart (multi-mese) / BarChart (singolo mese), PieChart top clienti/fornitori
- Trend 7 giorni clienti/fornitori attivi
- Top prodotti per fatturato

### Report AI
- Generazione report con Gemini Pro
- Lista report salvati con eliminazione

### Notizie
- Feed RSS (FreshPlaza, Corriere Ortofrutticolo, MyFruit)
- Widget meteo Bologna
- Widget prezzi mercati ingrosso (scraping FreshPlaza)
- Filtri per categoria

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
- `prodotti`: inventario con quantità, prezzi, scadenze
- `notizie`: articoli news cached
- `reports`: report AI generati
- `ai_suggestions`: cache suggerimenti settimanali

## Issue Note
- **Prezzi nel DB**: Possibile arrotondamento durante import CSV. Fix temporaneo: frontend ricalcola prezzo × quantità
- **Pie chart tooltip**: Funzionante con Tooltip di recharts standard
- **News scraper immagini**: Funzionante per MyFruit, problemi intermittenti con altri feed
