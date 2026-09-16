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

### 2026-09-14 (sessione 7b) — PDF del report AI
- PROBLEMA: chiedendo in chat "fammi il pdf di questo report", l'AI chiamava `genera_pdf` (report standard) su un periodo FUTURO -> PDF senza dati e senza l'analisi scritta in chat.
- NUOVO: `routes/pdf_ai_report.py` + endpoint GET /api/ai/report/{id}.pdf: rende il testo dell'analisi scritta dall'AI, fino a 4 KPI e N tabelle (dati reali) con FlowPDF. Documenti salvati in collection `ai_report_pdf`.
- NUOVO tool AI `genera_pdf_report` (titolo, sottotitolo, testo, kpi, tabelle, note) + regole 11 e 12 nel system prompt (usa questo tool per i PDF di analisi fatte in chat; mai periodi futuri: clamp a oggi).
- FIX: `genera_pdf` ora tronca start/end date a oggi; clean_text applicato a colonne/righe/KPI (il simbolo EUR rompeva FPDF -> 500).
- FIX: AgentMarkdown riconosce come PDF anche i link /api/ai/report/*.pdf (pulsante download).
- Verificato: chat -> report pistacchio -> PDF 4 pagine con KPI, tabelle prodotti/mensile/top clienti e testo dell'analisi.
- NOTA: durante i test il budget dell'Emergent LLM Key e' esaurito (RateLimitError budget exceeded) -> l'utente deve ricaricare da Profile > Manage plan > Universal Key > Add Balance.
- NUOVO (sessione 7b): Archivio report AI. Pulsante "Report salvati" nell'Assistente (data-testid=agent-report-salvati-btn) -> drawer con elenco, apertura PDF e cancellazione. Endpoint GET /api/ai/reports, DELETE /api/ai/reports/{id}.

### 2026-09-14 (sessione 7c) — Restyling completo dei PDF
- Nuova base grafica in `routes/pdf_helper.py`: font IBM Plex Sans embeddato (`backend/assets/fonts/Plex-*.ttf`, istanze statiche generate con fontTools), fondo chiaro, impaginazione editoriale, tabelle senza griglia con zebra, KPI a schede con barra accento, footer con filetto.
- LOGO "FLOW" RIMOSSO dall'intestazione (richiesta utente): resta titolo + sottotitolo + numero pagina + filetto accento.
- Valute in formato italiano con simbolo €: nuove helper `eur()` e `it_num()` in pdf_helper, applicate a pdf_analisi, pdf_sections, pdf_export, forecast, dashboard, ottimizzazione, piano.
- Nuovi grafici riutilizzabili: `line_chart` (andamento con area + serie tratteggiata anno prec.), `compare_chart` (alias su line_chart), `bar_ranking`, `column_chart`, `share_bar`, `chart_caption`.
- `blocco_grafici()` in pdf_sections: andamento mensile vs anno precedente + classifica top 10, inserito in analisi vendite, analisi acquisti e rendiconto.
- PDF report AI: ora apre con KPI + GRAFICI (il tool `genera_pdf_report` accetta `grafici`: colonne/confronto/barre/quote), poi tabelle, e il testo dell'analisi va in coda ("Lettura dei dati e raccomandazioni").
- Fix: celle tabella riducono il corpo prima di troncare (numeri non più tagliati), paragrafi allineati a sinistra, elenchi con "-" non più interpretati come titoli.
- Nota: chiamate AI lunghe superano il timeout dell'ingress -> testare via http://localhost:8001.

### 2026-09-14 (sessione 7d) — PDF senza grafici + Previsione prodotto
- RICHIESTA UTENTE: nessun grafico nei PDF. Rimossi tutti i call site (`blocco_grafici`, `monthly_chart`); le serie sono ora TABELLE (andamento mensile, spesa mensile, classifiche). I metodi grafici restano in pdf_helper ma non sono usati.
- Tool AI `genera_pdf_report`: il campo `grafici` viene reso come tabella (`_grafico_come_tabella`), prompt aggiornato ("nessun grafico: solo KPI, tabelle e testo").
- NUOVO endpoint GET /api/analisi/previsione-prodotto?prodotto=&giorni=30|60|90 -> KPI (quantita/fatturato/margine attesi, giacenza, da ordinare, copertura, fornitore consigliato + prezzo) e lista clienti attesi (qta, prezzo medio, margine, già ordinato negli ultimi N gg, ultimo acquisto).
- Frontend Analisi: link discreto "Previsione su un prodotto" (data-testid=apri-previsione-prodotto) a destra dei tab -> drawer con autocomplete prodotto, chip 30/60/90 gg, 8 KPI e tabella clienti.
- Lint: ripulite import non usate (ruff F401/F821 = clean su tutti i file toccati).

### 2026-09-14 (sessione 7e) — Previsione multi-selezione in Ottimizzazione
- Il pannello previsione e' stato SPOSTATO da Analisi a Ottimizzazione (`components/PrevisioneRicerca.jsx`), come campo di ricerca con autocomplete sopra i piani d'azione.
- Funziona su PRODOTTO, CLIENTE e FORNITORE (chip di tipo), con MULTI-SELEZIONE a chip (piu' prodotti/clienti/fornitori insieme, aggregati).
- I giorni vengono dal selettore principale della pagina (7/15/30/60/90) tramite prop `giorni`: nessun selettore duplicato.
- Tabelle: prodotto -> clienti che compreranno + riepilogo per prodotto (se >1); cliente -> cosa proporre; fornitore -> ordine consigliato.
- Backend: GET /api/analisi/previsione?tipo=&nomi=&nomi=&giorni= (param ripetuto `nomi`, `nome` legacy) e GET /api/analisi/previsione/pdf con gli stessi parametri (PDF senza grafici: KPI + selezione + tabelle).
- Pulsante PDF nel pannello (data-testid=previsione-export-pdf) che apre l'export in nuova scheda.

### 2026-09-14/15 (sessione 7f) — Considerazioni nei PDF, piano PDF professionale
- NUOVO `routes/ai_insight.py`: `considerazioni()` + `blocco_considerazioni_ai(pdf, contesto, chiave)` — genera 4-6 punti con numeri concreti via Emergent LLM Key (claude-sonnet-4-6), cache su collection `report_insight`, fallback silenzioso se LLM non disponibile. MAI menzionare che il testo e' AI (sezione "Considerazioni").
- Considerazioni aggiunte a: analisi vendite, analisi acquisti, rendiconto vendite, rendiconto acquisti, listino, previsione (prodotto/cliente/fornitore), ottimizzazione, statistiche vendite/acquisti. Forecast e dashboard: rinominata la sezione "Analisi AI" in "Considerazioni".
- Analisi PDF vendite: RIMOSSO il confronto con l'anno precedente (KPI VARIAZIONE, colonna Var. %, blocco confronto, frasi YoY nella sintesi).
- Previsione per fornitore: niente calcolo risparmio; ruolo primario/secondario/occasionale in base alla quota di acquisti; colonna "Quota" RIMOSSA da UI e PDF su richiesta utente.
- Intestazioni tabella nei PDF: font auto-ridotto prima del troncamento (niente sovrapposizioni). Note lunghe accorciate, tabelle limitate con riga "Altri N ...".
- NUOVO endpoint GET /api/ottimizzazione/piano/pdf?tipo=acquisti|vendite&giorni=N: piano strutturato come previsione, con quantita' in pezzi (domanda prevista, giacenza, da ordinare), prezzi acq/vendita, margine, totale per fornitore/cliente, punti di attenzione e considerazioni. Pulsante "PDF del piano" nella pagina Ottimizzazione (data-testid=piano-export-pdf).

### 2026-06 (sessione 8) — PDF Piano Fornitore rifinito
- Colonne tabella ordine fornitore: Articolo | Domanda prev. (con VAR% anno prec. tra parentesi) | Rotazione | Riordino ogni | Lotto medio (pz) | Prezzo acq. | Prezzo vend. | Marg. % | Valore. "Da ordinare" rimosso.
- `lotto_medio` = quantita' acquistata / numero ordini storici (media pz per ordine).
- `ai_insight.considerazioni()/blocco_considerazioni_ai()` accettano `extra`: regole aggiuntive per singolo report (incluse nella chiave di cache).
- Piano acquisti: 1o punto sempre sulla leva dello SCONTO sul fatturato ipotetico portato al fornitore (valore ordine + spesa 12 mesi); solo fatturato/sconto/margine/prezzi/gestione fornitore; VIETATO giacenze, la parola "righe", il rischio di dipendenza da unico fornitore o fornitori alternativi.
- Contesto AI: solo articoli con riordino ricorrente (esclusi quelli con riordino "/"), nessuna giacenza.
- Verificato generando il PDF reale (BORGHINI SRL, 30 gg) ed estraendo il testo.
- FIX valore riga (sessione 8b): il "Valore" usava `da_ordinare` (netto giacenza) mentre la colonna mostrata era `domanda_prevista` -> riga non verificabile (es. PISTACCHIO 1.950 x €12 ma valore €15.960). Nuovi campi `valore_domanda` / `margine_eur_domanda` (= quantita' prevista x prezzo) usati SOLO nel PDF; la UI Ottimizzazione resta sul valore d'ordine netto giacenza.
- KPI PDF acquisti: DOMANDA PREVISTA (kg/pz, con VAR% anno prec.), VALORE ACQUISTO, MARGINE PREVISTO, FATTURATO ATTESO; totale riga fornitore coerente con la somma delle righe.
- Unita' di misura: quantita' e prezzi sono registrati nella stessa unita' (kg per gli sfusi, pz per i confezionati), quindi valore = prezzo x quantita' e' corretto; rimosse le etichette fisse "(pz)" -> "kg/pz" + nota esplicativa nel PDF.

### 2026-06 (sessione 8c) — Previsione con media ponderata
- `routes/previsione_peso.py`: PESO_BASE=0.7 (anno base) + PESO_PREC=0.3 (anno precedente), helper `pondera()` e `agg_ponderata()` (stesso $group su due finestre, fusione dei campi numerici). Se l'anno precedente non ha dati resta il solo anno base (evita di dimezzare i prodotti nuovi).
- Applicata a: piano acquisti (`domanda_prevista`, `fatturato_atteso`), piano vendite (qty/fatt per cliente+prodotto), previsione prodotto/cliente/fornitore in analisi.py.
- La % tra parentesi ora e' la variazione della PREVISIONE (2026) rispetto al venduto dell'anno base (2025); nuovo campo `domanda_anno_base`. Intestazione colonna: "Domanda prev. <anno futuro>".
- Nota descrittiva sotto i KPI del piano fornitore RIMOSSA su richiesta utente.
- FIX `ai_insight`: cache su Mongo con replace_one(upsert) invece di insert_one (il duplicate key error faceva sparire le considerazioni).
- Nota: se l'Emergent LLM Key e' a budget esaurito le considerazioni non vengono generate (fallback silenzioso) -> ricaricare da Profile > Manage plan > Universal Key.

### 2026-06 (sessione 8d) — Grafica PDF unificata + report previsione
- `pdf_helper.py` riportato alla grafica richiesta dall'utente (riferimento: PDF "Previsione Pistacchi"): fascia scura in testata con titolo/sottotitolo + "Pag. N" (NIENTE logo FLOW), margini 10mm, schede KPI pastello con bordo e barra accento, titoli sezione su fascia pastello, tabelle con testata navy e griglia completa + righe alternate. Footer attuale invariato ("Documento riservato"). Vale per TUTTI i PDF.
- Previsione: `agg_ponderata` conserva anche i valori reali `{campo}_base` / `{campo}_prec`.
- Report previsione (`/analisi/previsione/pdf`): titoli "REPORT PRODOTTI/CLIENTE/FORNITORE"; rimosse colonne Giacenza e Da ordinare; aggiunta colonna "Venduto <anno base>"; sezioni riordinate (Riepilogo prodotto PRIMA di Previsione per fornitore); colonna "Gia ordinato" sostituita da "Compra piu spesso" (prodotto piu' acquistato dal cliente tra quelli selezionati).
- Ruolo fornitore (primario/secondario/occasionale) ora calcolato sulla quota degli acquisti DEI SOLI PRODOTTI CHE TRATTA (`quota_pct`), non sul totale della selezione (aggiunto `quota_spesa_pct` per la vecchia metrica). Es. BORGHINI su PISTACCHIO SGUSCIATO: da "occasionale" a "primario".
- Considerazioni AI: se la spunta "Clienti" e' disattivata il contesto non contiene clienti e il prompt vieta di nominarli.
- Piano fornitore: Rotazione / Riordino ogni / Lotto medio calcolati sugli ORDINI della stessa finestra dell'anno precedente; rotazione = n. riordini (3+ alta, 2 media, 0-1 bassa).
- ATTENZIONE: Emergent LLM Key a budget esaurito (max 9.601, cost 9.6187) -> le considerazioni AI nei PDF non vengono generate finche' non si ricarica.
- Sessione 8e: nel PDF report prodotti rimosse dalle tabelle clienti le colonne "Compra piu spesso" e "Ultimo acq." (restano in UI). Considerazioni AI: vietato parlare di giacenze/scorte/copertura e vietato commentare la mancanza o parzialita' dei dati; le ISTRUZIONI entrano nella chiave di cache (le regole nuove invalidano il cache); dal contesto della previsione rimosse le chiavi giacenza/da_ordinare e dal rendiconto acquisti la giacenza residua. Chiave LLM ricaricata: considerazioni verificate su report prodotti e piano fornitore.
- Sessione 8f: nuovo modulo `routes/unita.py` (kg_per_unita / kg / etichetta_kg): conversione a kg ricavata dal formato dell'articolo e validata sul prezzo unitario delle vendite (prezzo/kg risultante plausibile su tutti i top 45 articoli). Ordine delle regole: liquidi (ML/L) -> nessun peso; se il nome contiene KG la quantita' e' GIA' in kg (fattore 1, fix del bug "VERDURA CHIPS KG. 2,5 X 2" che veniva moltiplicato x2,5); GR. -> grammi/1000; "0,500 X 12" -> 0,5 kg; "250 X 24" -> 250 g. Nel PDF report prodotti: KPI "DA ORDINARE" sostituito da "KG TOTALI" come seconda scheda, colonna "Kg previsti" con il fattore esplicito (es. "67 kg (x0,25)") nelle tabelle prodotti e fornitori, colonna fatturato etichettata "Fatturato N gg" + nota esplicativa.
- Sessione 8g: chiarita l'unita' di misura dei dati (verificato sui multipli delle quantita' vendute): per gli articoli con "KG" nel nome la quantita' registrata e' GIA' in kg (PISTACCHIO KG.2 -> 2/4/6/10; VERDURA CHIPS KG.2,5 -> 2,5/5/7,5), per i confezionati (GR., "250 X 24", "0,500 X 10") e' in PEZZI (multipli del cartone). `unita()` ed `etichetta_qta()` in routes/unita.py. Nel report prodotti: una sola colonna quantita' con unita' esplicita ("356 kg" / "269 pz"), colonna Kg previsti rimossa; tabella fornitori tutta in kg (Kg previsti / Kg venduti anno base); KPI "KG TOTALI" mantenuto come seconda scheda.
- Sessione 8h: seconda scheda KPI del report prodotti = "VALORE ACQUISTO" (somma domanda prevista x prezzo acquisto) al posto di "KG TOTALI". Nessuna conversione: le quantita' restano quelle usate in tutto il sistema (vendite), con l'unita' specificata nella tabella prodotti (kg per gli sfusi, pz per i confezionati) e nota esplicativa. Tabella fornitori tornata a Domanda prev. / Venduto anno base.
