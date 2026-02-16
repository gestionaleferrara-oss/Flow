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

### Report AI
- 3 tipi: Settimanale, Mensile, Dashboard
- Export PDF

### Forecast AI (NUOVO)
- **Previsioni per 3 mesi** (mese target + 2 successivi)
- **Grafico barre** con range min-max visualizzato
- **Dati per ogni mese**:
  - Valore previsto
  - Range (minimo - massimo)
  - Trend vs anni precedenti
  - Anni di dati storici disponibili
- **Counter**: Totale Previsto, Media Prevista, Media Storica
- **Analisi AI esaustiva**: Sintesi, Fattori Chiave, Opportunità, Rischi, Raccomandazioni
- Funziona per prodotti e clienti
- Export PDF e Reset

### Altre Funzionalità
- Import CSV/XLSX
- Gestione Magazzino
- Clienti e Fornitori con analisi
- Sistema Alert
- News feed

## Endpoints
- `GET /api/dashboard-cards`
- `GET /api/card-detail/{id}?periodo=`
- `POST /api/ai-reports/generate?report_type=`
- `POST /api/ai-reports/export-pdf`
- `GET /api/forecast/generate` - Restituisce previsioni per 3 mesi con range
- `POST /api/forecast/export-pdf`

## Changelog 2025-02-16
- Forecast AI: previsioni 3 mesi, grafico barre con range, analisi AI esaustiva
- Report AI: export PDF
- Fix vari encoding PDF

## Backlog
- P2: Mobile UI
- P3: Fix news scraping
- P3: Refactoring Dashboard.jsx
