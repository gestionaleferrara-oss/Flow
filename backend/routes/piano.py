"""Piano d'azione: previsione dei prossimi N giorni da oggi, basata sul venduto reale
dello stesso intervallo dell'anno precedente.

- Acquisti: ordini completi raggruppati per fornitore (tutti gli articoli dello stesso
  fornitore che si consumano nella finestra).
- Vendite: proposte d'ordine per cliente (cosa aveva comprato l'anno scorso in quei giorni).
- In coda, una sezione di suggerimenti (rinegoziazioni, scorte, clienti fermi).
"""
from datetime import datetime, timedelta
from statistics import median
from typing import Dict, List

from fastapi import APIRouter

from database import db
from routes.analisi import EXCLUDED_CLIENTS, esclusi_filter

router = APIRouter()

FORNITORE_IGNOTO = "Fornitore da individuare"


def _d(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _finestra(giorni: int):
    giorni = max(min(giorni, 180), 3)
    oggi = datetime.now()
    fs, fe = oggi, oggi + timedelta(days=giorni - 1)
    return (_d(fs), _d(fe), _d(fs - timedelta(days=365)), _d(fe - timedelta(days=365)), giorni)


async def _base_vendite() -> Dict:
    excl = await esclusi_filter()
    return {"cliente_nome": {"$nin": EXCLUDED_CLIENTS}, **excl}


@router.get("/ottimizzazione/piano")
async def piano_azione(tipo: str = "acquisti", giorni: int = 30, limit: int = 40):
    fs, fe, ly_fs, ly_fe, giorni = _finestra(giorni)
    periodo = {"futuro_start": fs, "futuro_end": fe, "storico_start": ly_fs,
               "storico_end": ly_fe, "giorni": giorni}
    if tipo == "vendite":
        return await _piano_vendite(periodo, limit)
    return await _piano_acquisti(periodo, limit)


# ─────────────────────────── ACQUISTI ───────────────────────────
async def _piano_acquisti(periodo: Dict, limit: int) -> Dict:
    base_v = await _base_vendite()
    fs, fe = periodo['futuro_start'], periodo['futuro_end']
    ly_fs, ly_fe = periodo['storico_start'], periodo['storico_end']
    giorni = periodo['giorni']
    oggi = _d(datetime.now())
    anno_start = _d(datetime.now() - timedelta(days=365))

    domanda = await db.vendite.aggregate([
        {"$match": {**base_v, "data": {"$gte": ly_fs, "$lte": ly_fe}}},
        {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": {"$abs": "$quantita"}},
                    "fatt": {"$sum": {"$abs": "$totale"}},
                    "clienti": {"$addToSet": "$cliente_nome"}}},
    ]).to_list(20000)
    dom_map = {r['_id']: r for r in domanda if r['_id'] and r['qty'] > 0}

    # Prezzi fornitore nella stessa finestra dell'anno scorso (fallback: ultimi 12 mesi)
    async def acq_per_fornitore(s, e):
        rows = await db.ordini.aggregate([
            {"$match": {"data": {"$gte": s, "$lte": e}, "quantita": {"$gt": 0},
                        "totale": {"$gt": 0}}},
            {"$group": {"_id": {"p": "$prodotto_nome", "f": "$fornitore_nome"},
                        "qty": {"$sum": "$quantita"}, "tot": {"$sum": "$totale"},
                        "ultima": {"$max": "$data"}}},
        ]).to_list(200000)
        out: Dict[str, Dict[str, Dict]] = {}
        for a in rows:
            p, f = a['_id'].get('p'), a['_id'].get('f')
            if p and f and a['qty'] > 0:
                out.setdefault(p, {})[f] = {"prezzo": a['tot'] / a['qty'], "qty": a['qty'],
                                            "spesa": a['tot'], "ultima": a['ultima']}
        return out

    acq_ly = await acq_per_fornitore(ly_fs, ly_fe)
    acq_anno = await acq_per_fornitore(anno_start, oggi)
    acq_map = {**acq_anno, **acq_ly}

    # Prezzo di vendita atteso: stessa finestra anno scorso
    pv_map = {n: (d['fatt'] / d['qty']) for n, d in dom_map.items() if d['qty']}

    giacenze = {p['nome']: (p.get('quantita', 0) or 0) for p in
                await db.prodotti.find({}, {"_id": 0, "nome": 1, "quantita": 1}).to_list(20000)}

    articoli: List[Dict] = []
    for nome, d in dom_map.items():
        dom = d['qty']
        giac = giacenze.get(nome, 0) or 0
        da_ordinare = max(dom - giac, 0)
        forns = acq_map.get(nome, {})
        prezzi = {f: v['prezzo'] for f, v in forns.items() if v['prezzo'] > 0}
        best = min(prezzi, key=prezzi.get) if prezzi else None
        p_best = prezzi[best] if best else None
        qty_tot = sum(v['qty'] for v in forns.values())
        p_medio = (sum(v['spesa'] for v in forns.values()) / qty_tot) if qty_tot else None
        pv = pv_map.get(nome) or (d['fatt'] / dom if dom else 0)
        costo = p_best or p_medio or 0
        margine_pct = ((pv - costo) / costo * 100) if (costo and pv) else None
        articoli.append({
            "prodotto": nome,
            "fornitore": best or FORNITORE_IGNOTO,
            "fornitori_alternativi": len(prezzi),
            "domanda_prevista": round(dom, 1),
            "fatturato_atteso": round(d['fatt'], 2),
            "clienti_attesi": len(d.get('clienti') or []),
            "giacenza": round(giac, 1),
            "copertura_giorni": round(giac / (dom / giorni)) if dom > 0 else None,
            "da_ordinare": round(da_ordinare, 1),
            "prezzo_acquisto": round(costo, 4) if costo else None,
            "prezzo_medio_mercato": round(p_medio, 4) if p_medio else None,
            "prezzo_vendita_atteso": round(pv, 4) if pv else None,
            "margine_pct": round(margine_pct, 1) if margine_pct is not None else None,
            "valore": round(costo * da_ordinare, 2),
            "margine_eur": round((pv - costo) * da_ordinare, 2) if pv else 0,
            "ultimo_acquisto": forns.get(best, {}).get('ultima') if best else None,
        })

    da_ordinare_lista = [a for a in articoli if a['da_ordinare'] > 0]

    ordini_map: Dict[str, Dict] = {}
    for a in da_ordinare_lista:
        o = ordini_map.setdefault(a['fornitore'], {"fornitore": a['fornitore'], "articoli": [],
                                                   "valore": 0.0, "margine_eur": 0.0,
                                                   "fatturato_atteso": 0.0})
        o['articoli'].append(a)
        o['valore'] += a['valore']
        o['margine_eur'] += max(a['margine_eur'], 0)
        o['fatturato_atteso'] += a['fatturato_atteso']

    ordini = []
    for o in ordini_map.values():
        o['articoli'].sort(key=lambda x: -x['da_ordinare'])
        spesa_anno = sum(v['spesa'] for p in acq_map.values() for f, v in p.items() if f == o['fornitore'])
        margine_pct = (o['margine_eur'] / o['valore'] * 100) if o['valore'] else None
        ordini.append({
            **{k: round(v, 2) if isinstance(v, float) else v for k, v in o.items() if k != 'articoli'},
            "articoli": o['articoli'][:80],
            "prodotti_n": len(o['articoli']),
            "margine_pct": round(margine_pct, 1) if margine_pct is not None else None,
            "spesa_ultimo_anno": round(spesa_anno, 2),
        })
    ordini.sort(key=lambda o: -o['valore'])

    suggerimenti = _suggerimenti_acquisti(articoli, giacenze, acq_map, giorni)
    top = sorted(articoli, key=lambda a: -a['domanda_prevista'])[:20]

    return {
        "tipo": "acquisti", "periodo": periodo,
        "top_prodotti": [{"prodotto": a['prodotto'], "quantita": a['domanda_prevista'],
                          "fatturato": a['fatturato_atteso'], "clienti": a['clienti_attesi'],
                          "giacenza": a['giacenza']} for a in top],
        "totali": {
            "fornitori": len(ordini),
            "prodotti": len(da_ordinare_lista),
            "valore_ordini": round(sum(o['valore'] for o in ordini), 2),
            "margine_previsto": round(sum(o['margine_eur'] for o in ordini), 2),
            "fatturato_atteso": round(sum(a['fatturato_atteso'] for a in articoli), 2),
        },
        "ordini": ordini[:limit],
        "suggerimenti": suggerimenti,
    }


def _suggerimenti_acquisti(articoli: List[Dict], giacenze: Dict[str, float],
                           acq_map: Dict[str, Dict[str, Dict]], giorni: int) -> List[Dict]:
    sug = []

    bassi = sorted([a for a in articoli if a['da_ordinare'] > 0 and a['margine_pct'] is not None
                    and a['margine_pct'] < 10], key=lambda a: a['margine_pct'])[:12]
    if bassi:
        sug.append({
            "id": "rinegozia", "titolo": "Rinegozia o alza il prezzo",
            "descrizione": "Margine previsto sotto il 10%: chiedi uno sconto al fornitore o ritocca il listino",
            "valore": round(sum(a['valore'] for a in bassi), 2),
            "voci": [{"nome": a['prodotto'],
                      "dettaglio": f"margine {a['margine_pct']}% · acquisto €{a['prezzo_acquisto']:.2f} vs vendita €{a['prezzo_vendita_atteso']:.2f}",
                      "valore": a['valore']} for a in bassi],
        })

    dom_nomi = {a['prodotto'] for a in articoli}
    fermi = []
    for nome, q in giacenze.items():
        if q > 0 and nome not in dom_nomi:
            prezzo = min((v['prezzo'] for v in acq_map.get(nome, {}).values()), default=0)
            fermi.append({"nome": nome, "dettaglio": f"{q:,.0f} pz in giacenza, nessuna vendita prevista",
                          "valore": round(q * prezzo, 2)})
    fermi.sort(key=lambda x: -x['valore'])
    if fermi:
        sug.append({
            "id": "smaltire", "titolo": "Giacenze da smaltire",
            "descrizione": "Capitale fermo su articoli che l'anno scorso non hanno venduto in questa finestra",
            "valore": round(sum(f['valore'] for f in fermi), 2), "voci": fermi[:12],
        })

    eccesso = sorted([a for a in articoli if a['da_ordinare'] == 0 and a['copertura_giorni']
                      and a['copertura_giorni'] > giorni * 2],
                     key=lambda a: -(a['giacenza'] * (a['prezzo_acquisto'] or 0)))[:12]
    if eccesso:
        sug.append({
            "id": "scorte", "titolo": "Scorte sovrabbondanti",
            "descrizione": "Giacenza che copre più del doppio della finestra: non riordinare, spingi la vendita",
            "valore": round(sum(a['giacenza'] * (a['prezzo_acquisto'] or 0) for a in eccesso), 2),
            "voci": [{"nome": a['prodotto'],
                      "dettaglio": f"copertura {a['copertura_giorni']} giorni ({a['giacenza']:,.0f} pz)",
                      "valore": round(a['giacenza'] * (a['prezzo_acquisto'] or 0), 2)} for a in eccesso],
        })
    return sug


# ─────────────────────────── VENDITE ───────────────────────────
async def _piano_vendite(periodo: Dict, limit: int) -> Dict:
    base_v = await _base_vendite()
    ly_fs, ly_fe = periodo['storico_start'], periodo['storico_end']
    oggi = _d(datetime.now())
    recenti_start = _d(datetime.now() - timedelta(days=periodo['giorni']))
    sem_start = _d(datetime.now() - timedelta(days=180))

    storico = await db.vendite.aggregate([
        {"$match": {**base_v, "data": {"$gte": ly_fs, "$lte": ly_fe}}},
        {"$group": {"_id": {"c": "$cliente_nome", "p": "$prodotto_nome"},
                    "qty": {"$sum": {"$abs": "$quantita"}},
                    "fatt": {"$sum": {"$abs": "$totale"}}}},
    ]).to_list(200000)

    recenti = await db.vendite.aggregate([
        {"$match": {**base_v, "data": {"$gte": recenti_start, "$lte": oggi}}},
        {"$group": {"_id": {"c": "$cliente_nome", "p": "$prodotto_nome"},
                    "qty": {"$sum": {"$abs": "$quantita"}}}},
    ]).to_list(200000)
    comprati_ora: Dict[str, set] = {}
    for r in recenti:
        comprati_ora.setdefault(r['_id']['c'], set()).add(r['_id']['p'])

    marg = await db.vendite.aggregate([
        {"$match": {**base_v, "data": {"$gte": sem_start, "$lte": oggi}}},
        {"$group": {"_id": "$cliente_nome", "fatt": {"$sum": {"$abs": "$totale"}},
                    "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                    "ultimo": {"$max": "$data"}}},
    ]).to_list(20000)
    marg_map = {r['_id']: r for r in marg}
    margini = [(r['fatt'] - r['costo']) / r['costo'] * 100 for r in marg if r['costo'] > 0]
    marg_med = median(margini) if margini else 20.0

    ultimo_globale = await db.vendite.aggregate([
        {"$match": base_v},
        {"$group": {"_id": "$cliente_nome", "ultimo": {"$max": "$data"}}},
    ]).to_list(20000)
    ultimo_map = {r['_id']: r['ultimo'] for r in ultimo_globale}

    per_cliente: Dict[str, Dict] = {}
    for r in storico:
        c, p = r['_id']['c'], r['_id']['p']
        if not c or not p:
            continue
        d = per_cliente.setdefault(c, {"cliente": c, "articoli": [], "valore_atteso": 0.0})
        gia = p in comprati_ora.get(c, set())
        d['articoli'].append({
            "prodotto": p, "quantita_attesa": round(r['qty'], 1),
            "valore_atteso": round(r['fatt'], 2),
            "prezzo_atteso": round(r['fatt'] / r['qty'], 4) if r['qty'] else None,
            "gia_ordinato": gia,
        })
        d['valore_atteso'] += r['fatt']

    proposte = []
    for c, d in per_cliente.items():
        d['articoli'].sort(key=lambda a: -a['quantita_attesa'])
        mancanti = [a for a in d['articoli'] if not a['gia_ordinato']]
        m = marg_map.get(c, {})
        mpct = ((m.get('fatt', 0) - m.get('costo', 0)) / m['costo'] * 100) if m.get('costo', 0) > 0 else None
        ultimo = ultimo_map.get(c)
        gg = (datetime.now() - datetime.strptime(ultimo, "%Y-%m-%d")).days if ultimo else None
        valore_mancante = sum(a['valore_atteso'] for a in mancanti)
        if gg is not None and gg > 45:
            azione = "CLIENTE FERMO"
        elif valore_mancante > d['valore_atteso'] * 0.5:
            azione = "CHIAMA ORA"
        elif valore_mancante > 0:
            azione = "PROPONI"
        else:
            azione = "IN LINEA"
        proposte.append({
            "cliente": c,
            "valore_atteso": round(d['valore_atteso'], 2),
            "valore_mancante": round(valore_mancante, 2),
            "prodotti_n": len(d['articoli']),
            "prodotti_mancanti": len(mancanti),
            "margine_pct": round(mpct, 1) if mpct is not None else None,
            "margine_mediano_pct": round(marg_med, 1),
            "margine_eur": round(d['valore_atteso'] * (mpct if mpct is not None else marg_med) / 100, 2),
            "ultimo_ordine": ultimo, "giorni_da_ultimo_ordine": gg,
            "fatturato_ultimi_180": round(m.get('fatt', 0), 2),
            "azione": azione,
            "articoli": d['articoli'][:80],
        })
    proposte.sort(key=lambda p: -p['valore_atteso'])

    suggerimenti = _suggerimenti_vendite(proposte, marg_med)

    top_map: Dict[str, Dict] = {}
    for r in storico:
        p = r['_id']['p']
        if not p:
            continue
        t = top_map.setdefault(p, {"prodotto": p, "quantita": 0.0, "fatturato": 0.0, "clienti": 0})
        t['quantita'] += r['qty']; t['fatturato'] += r['fatt']; t['clienti'] += 1
    top = sorted(top_map.values(), key=lambda t: -t['quantita'])[:20]

    return {
        "tipo": "vendite", "periodo": {**periodo, "recenti_start": recenti_start, "recenti_end": oggi},
        "top_prodotti": [{**t, "quantita": round(t['quantita'], 1),
                          "fatturato": round(t['fatturato'], 2)} for t in top],
        "totali": {
            "clienti": len(proposte),
            "valore_atteso": round(sum(p['valore_atteso'] for p in proposte), 2),
            "valore_mancante": round(sum(p['valore_mancante'] for p in proposte), 2),
            "margine_previsto": round(sum(p['margine_eur'] for p in proposte), 2),
            "da_chiamare": sum(1 for p in proposte if p['azione'] in ("CHIAMA ORA", "CLIENTE FERMO")),
        },
        "ordini": proposte[:limit],
        "suggerimenti": suggerimenti,
    }


def _suggerimenti_vendite(proposte: List[Dict], marg_med: float) -> List[Dict]:
    sug = []

    fermi = sorted([p for p in proposte if p['azione'] == "CLIENTE FERMO"],
                   key=lambda p: -p['valore_atteso'])[:12]
    if fermi:
        sug.append({
            "id": "fermi", "titolo": "Clienti fermi da riattivare",
            "descrizione": "Nessun ordine da oltre 45 giorni, ma l'anno scorso compravano in questa finestra",
            "valore": round(sum(p['valore_atteso'] for p in fermi), 2),
            "voci": [{"nome": p['cliente'],
                      "dettaglio": f"ultimo ordine {p['ultimo_ordine'] or 'mai'} ({p['giorni_da_ultimo_ordine']} gg)",
                      "valore": p['valore_atteso']} for p in fermi],
        })

    ref = sorted([p for p in proposte if p['prodotti_mancanti'] > 0 and p['azione'] != "CLIENTE FERMO"],
                 key=lambda p: -p['valore_mancante'])[:12]
    if ref:
        sug.append({
            "id": "referenze", "titolo": "Referenze da riproporre",
            "descrizione": "Articoli comprati l'anno scorso in questi giorni e non ancora riordinati",
            "valore": round(sum(p['valore_mancante'] for p in ref), 2),
            "voci": [{"nome": p['cliente'],
                      "dettaglio": f"{p['prodotti_mancanti']} referenze: " +
                                   ", ".join(a['prodotto'] for a in p['articoli'] if not a['gia_ordinato'])[:90],
                      "valore": p['valore_mancante']} for p in ref],
        })

    sotto = sorted([p for p in proposte if p['margine_pct'] is not None and p['margine_pct'] < marg_med
                    and p['fatturato_ultimi_180'] > 0],
                   key=lambda p: -(p['fatturato_ultimi_180'] * (marg_med - p['margine_pct']) / 100))[:12]
    if sotto:
        sug.append({
            "id": "margine", "titolo": "Prezzi da ritoccare",
            "descrizione": f"Clienti con margine sotto la mediana ({marg_med:.1f}%): recupero allineandoli",
            "valore": round(sum(p['fatturato_ultimi_180'] * (marg_med - p['margine_pct']) / 100 for p in sotto), 2),
            "voci": [{"nome": p['cliente'],
                      "dettaglio": f"margine {p['margine_pct']}% contro mediana {marg_med:.1f}%",
                      "valore": round(p['fatturato_ultimi_180'] * (marg_med - p['margine_pct']) / 100, 2)}
                     for p in sotto],
        })
    return sug


# ─────────────────────────── DETTAGLIO ARTICOLO ───────────────────────────
def _eur(v) -> str:
    return f"{(v or 0):,.2f} EUR".replace(",", "@").replace(".", ",").replace("@", ".")


def _qt(v) -> str:
    return f"{(v or 0):,.0f}".replace(",", ".")


@router.get("/ottimizzazione/piano/articolo")
async def dettaglio_articolo(prodotto: str, giorni: int = 30, cliente: str = None):
    """Vendite complessive per cliente su un articolo: finestra storica + ultimi 12 mesi."""
    fs, fe, ly_fs, ly_fe, giorni = _finestra(giorni)
    base_v = await _base_vendite()
    oggi = _d(datetime.now())
    anno_start = _d(datetime.now() - timedelta(days=365))

    async def per_cliente(s, e):
        return await db.vendite.aggregate([
            {"$match": {**base_v, "prodotto_nome": prodotto, "data": {"$gte": s, "$lte": e}}},
            {"$group": {"_id": "$cliente_nome", "qty": {"$sum": {"$abs": "$quantita"}},
                        "fatt": {"$sum": {"$abs": "$totale"}},
                        "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                        "ordini": {"$sum": 1}, "ultimo": {"$max": "$data"}}},
            {"$sort": {"fatt": -1}},
        ]).to_list(2000)

    finestra = await per_cliente(ly_fs, ly_fe)
    anno = await per_cliente(anno_start, oggi)

    forn = await db.ordini.aggregate([
        {"$match": {"prodotto_nome": prodotto, "data": {"$gte": anno_start, "$lte": oggi},
                    "quantita": {"$gt": 0}, "totale": {"$gt": 0}}},
        {"$group": {"_id": "$fornitore_nome", "qty": {"$sum": "$quantita"}, "spesa": {"$sum": "$totale"},
                    "ultima": {"$max": "$data"}}},
        {"$sort": {"spesa": -1}},
    ]).to_list(500)

    prod = await db.prodotti.find_one({"nome": prodotto}, {"_id": 0, "quantita": 1})
    giac = (prod or {}).get('quantita', 0) or 0
    qty_fin = sum(r['qty'] for r in finestra)
    fatt_fin = sum(r['fatt'] for r in finestra)
    qty_anno = sum(r['qty'] for r in anno)

    spiegazione = (
        f"Nella stessa finestra dell'anno scorso ({ly_fs} → {ly_fe}) hai venduto {_qt(qty_fin)} pezzi di "
        f"{prodotto} a {len(finestra)} clienti per {_eur(fatt_fin)}. Negli ultimi 12 mesi il totale e' "
        f"{_qt(qty_anno)} pezzi su {len(anno)} clienti. Giacenza attuale: {_qt(giac)} pezzi, quindi la "
        f"previsione per il periodo {fs} → {fe} e' di {_qt(max(qty_fin - giac, 0))} pezzi da ordinare."
    )
    if cliente:
        mio = next((r for r in anno if r['_id'] == cliente), None)
        quota = (mio['fatt'] / sum(r['fatt'] for r in anno) * 100) if (mio and anno) else 0
        spiegazione += (f" {cliente} pesa il {quota:.1f}% del fatturato dell'articolo negli ultimi 12 mesi."
                        if mio else f" {cliente} non ha comprato questo articolo negli ultimi 12 mesi.")

    def tab_clienti(rows, titolo, tot_fatt):
        return {
            "titolo": titolo,
            "colonne": ["Cliente", "Qtà", "Fatturato", "Prezzo medio", "Margine", "% sul totale", "Ultimo acquisto"],
            "righe": [[r['_id'], _qt(r['qty']), _eur(r['fatt']),
                       _eur(r['fatt'] / r['qty']) if r['qty'] else "—",
                       f"{(r['fatt'] - r['costo']) / r['costo'] * 100:.1f}%" if r['costo'] > 0 else "—",
                       f"{(r['fatt'] / tot_fatt * 100):.1f}%" if tot_fatt else "—",
                       r['ultimo']] for r in rows[:200]],
        }

    tabelle = [
        tab_clienti(finestra, f"Vendite per cliente — stessa finestra anno scorso ({ly_fs} → {ly_fe})", fatt_fin),
        tab_clienti(anno, "Vendite per cliente — ultimi 12 mesi", sum(r['fatt'] for r in anno)),
    ]
    if forn:
        tabelle.append({
            "titolo": "Acquisti per fornitore — ultimi 12 mesi",
            "colonne": ["Fornitore", "Qtà", "Spesa", "Prezzo medio", "Ultimo acquisto"],
            "righe": [[f['_id'], _qt(f['qty']), _eur(f['spesa']),
                       _eur(f['spesa'] / f['qty']) if f['qty'] else "—", f['ultima']] for f in forn],
        })

    return {"titolo": prodotto, "spiegazione": spiegazione, "tabelle": tabelle}
