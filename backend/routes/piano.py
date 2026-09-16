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

from fastapi import APIRouter, HTTPException

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
               "storico_end": ly_fe, "giorni": giorni,
               "anno_base": ly_fs[:4], "anno_confronto": str(int(ly_fs[:4]) - 1)}
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

    ly2_fs = _d(datetime.strptime(ly_fs, "%Y-%m-%d") - timedelta(days=365))
    ly2_fe = _d(datetime.strptime(ly_fe, "%Y-%m-%d") - timedelta(days=365))
    dom2_map = {r['_id']: r for r in await db.vendite.aggregate([
        {"$match": {**base_v, "data": {"$gte": ly2_fs, "$lte": ly2_fe}}},
        {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": {"$abs": "$quantita"}},
                    "fatt": {"$sum": {"$abs": "$totale"}}}},
    ]).to_list(20000) if r['_id']}

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

    venduto_anno = {r['_id']: r['qty'] for r in await db.vendite.aggregate([
        {"$match": {**base_v, "data": {"$gte": anno_start, "$lte": oggi}}},
        {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": {"$abs": "$quantita"}}}},
    ]).to_list(20000) if r['_id']}

    date_ordini = {r['_id']: sorted(r['date']) for r in await db.ordini.aggregate([
        {"$match": {"data": {"$gte": anno_start, "$lte": oggi}, "quantita": {"$gt": 0}}},
        {"$group": {"_id": "$prodotto_nome", "date": {"$addToSet": "$data"}}},
    ]).to_list(20000) if r['_id']}

    def _riordino(nome):
        d = date_ordini.get(nome) or []
        if len(d) < 2:
            return None
        da = datetime.strptime(d[0], "%Y-%m-%d")
        a = datetime.strptime(d[-1], "%Y-%m-%d")
        return round((a - da).days / (len(d) - 1))

    def _rotazione(nome, giac):
        venduto = venduto_anno.get(nome, 0)
        if venduto <= 0:
            return "bassa", None
        mesi = giac / (venduto / 12)
        return ("alta" if mesi < 1 else "media" if mesi <= 3 else "bassa"), round(mesi, 1)

    articoli: List[Dict] = []
    for nome, d in dom_map.items():
        dom = d['qty']
        giac = giacenze.get(nome, 0) or 0
        da_ordinare = max(dom - giac, 0)
        forns = acq_map.get(nome, {})
        prezzi = {f: v['prezzo'] for f, v in forns.items() if v['prezzo'] > 0}
        # fornitore primario = quello da cui si acquista la quantita' maggiore
        best = max(prezzi, key=lambda f: forns[f]['qty']) if prezzi else None
        p_best = prezzi[best] if best else None
        qty_tot = sum(v['qty'] for v in forns.values())
        p_medio = (sum(v['spesa'] for v in forns.values()) / qty_tot) if qty_tot else None
        quota_best = (forns[best]['qty'] / qty_tot * 100) if (best and qty_tot) else None
        pv = pv_map.get(nome) or (d['fatt'] / dom if dom else 0)
        costo = p_best or p_medio or 0
        margine_pct = ((pv - costo) / costo * 100) if (costo and pv) else None
        rotazione, rot_indice = _rotazione(nome, giac)
        d2 = dom2_map.get(nome) or {}
        q2 = d2.get('qty', 0) or 0
        var_anno = ((dom - q2) / q2 * 100) if q2 else None
        n_ord = len(date_ordini.get(nome) or [])
        qty_acq = sum(v['qty'] for v in forns.values())
        lotto_medio = (qty_acq / n_ord) if n_ord else None
        articoli.append({
            "prodotto": nome,
            "quota_fornitore_pct": round(quota_best, 1) if quota_best is not None else None,
            "ruolo_fornitore": ("primario" if (quota_best or 0) >= 40 else
                                "secondario" if (quota_best or 0) >= 10 else "occasionale")
            if quota_best is not None else None,
            "rotazione": rotazione,
            "mesi_copertura": rot_indice,
            "riordino_giorni": _riordino(nome),
            "ordini_ultimo_anno": n_ord,
            "lotto_medio": round(lotto_medio, 1) if lotto_medio else None,
            "domanda_anno_prec": round(q2, 1),
            "var_anno_pct": round(var_anno, 1) if var_anno is not None else None,
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
            # valore della domanda prevista (quantita' x prezzo, senza netting della giacenza)
            "valore_domanda": round(costo * dom, 2),
            "margine_eur_domanda": round((pv - costo) * dom, 2) if pv else 0,
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
            "quantita_attesa": round(sum(a['domanda_prevista'] for a in articoli), 1),
            "quantita_anno_prec": round(sum(a['domanda_anno_prec'] for a in articoli), 1),
            "var_quantita_pct": round(
                (sum(a['domanda_prevista'] for a in articoli) - sum(a['domanda_anno_prec'] for a in articoli))
                / sum(a['domanda_anno_prec'] for a in articoli) * 100, 1)
            if sum(a['domanda_anno_prec'] for a in articoli) else None,
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
    return f"\u20ac {(v or 0):,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _qt(v) -> str:
    return f"{(v or 0):,.0f}".replace(",", ".")


@router.get("/ottimizzazione/piano/articolo")
async def dettaglio_articolo(prodotto: str, giorni: int = 30, cliente: str = None):
    """Scheda approfondita del prodotto: confronto clienti anno su anno, andamento mensile,
    fornitori con ruolo e prezzi, rotazione e riordino."""
    fs, fe, ly_fs, ly_fe, giorni = _finestra(giorni)
    base_v = await _base_vendite()
    oggi = _d(datetime.now())
    anno_start = _d(datetime.now() - timedelta(days=365))
    rec_start = _d(datetime.now() - timedelta(days=giorni))

    async def per_cliente(s, e):
        rows = await db.vendite.aggregate([
            {"$match": {**base_v, "prodotto_nome": prodotto, "data": {"$gte": s, "$lte": e}}},
            {"$group": {"_id": "$cliente_nome", "qty": {"$sum": {"$abs": "$quantita"}},
                        "fatt": {"$sum": {"$abs": "$totale"}},
                        "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                        "ultimo": {"$max": "$data"}}},
        ]).to_list(3000)
        return {r['_id']: r for r in rows if r['_id']}

    ly = await per_cliente(ly_fs, ly_fe)          # stessa finestra anno scorso
    rec = await per_cliente(rec_start, oggi)      # ultimi N giorni
    anno = await per_cliente(anno_start, oggi)    # ultimi 12 mesi

    mesi = await db.vendite.aggregate([
        {"$match": {**base_v, "prodotto_nome": prodotto, "data": {"$gte": anno_start, "$lte": oggi}}},
        {"$group": {"_id": {"$substr": ["$data", 0, 7]}, "qty": {"$sum": {"$abs": "$quantita"}},
                    "fatt": {"$sum": {"$abs": "$totale"}},
                    "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                    "clienti": {"$addToSet": "$cliente_nome"}}},
        {"$sort": {"_id": 1}},
    ]).to_list(24)

    forn = await db.ordini.aggregate([
        {"$match": {"prodotto_nome": prodotto, "data": {"$gte": anno_start, "$lte": oggi},
                    "quantita": {"$gt": 0}, "totale": {"$gt": 0}}},
        {"$group": {"_id": "$fornitore_nome", "qty": {"$sum": "$quantita"}, "spesa": {"$sum": "$totale"},
                    "ultima": {"$max": "$data"}, "date": {"$addToSet": "$data"}}},
        {"$sort": {"qty": -1}},
    ]).to_list(200)
    qty_forn_tot = sum(f['qty'] for f in forn) or 1
    tutte_date = sorted({d for f in forn for d in f['date']})
    riordino = None
    if len(tutte_date) >= 2:
        riordino = round((datetime.strptime(tutte_date[-1], "%Y-%m-%d")
                          - datetime.strptime(tutte_date[0], "%Y-%m-%d")).days / (len(tutte_date) - 1))

    prod = await db.prodotti.find_one({"nome": prodotto}, {"_id": 0, "quantita": 1})
    giac = (prod or {}).get('quantita', 0) or 0
    qty_ly = sum(r['qty'] for r in ly.values())
    fatt_ly = sum(r['fatt'] for r in ly.values())
    qty_anno = sum(r['qty'] for r in anno.values())
    qty_rec = sum(r['qty'] for r in rec.values())
    costo_anno = sum(r['costo'] for r in anno.values())
    fatt_anno = sum(r['fatt'] for r in anno.values())
    mesi_cop = (giac / (qty_anno / 12)) if qty_anno else None
    rotazione = "bassa" if not qty_anno else ("alta" if mesi_cop < 1 else "media" if mesi_cop <= 3 else "bassa")

    spiegazione = (
        f"Negli ultimi 12 mesi: {_qt(qty_anno)} pz a {len(anno)} clienti per {_eur(fatt_anno)}"
        + (f", margine {_eur(fatt_anno - costo_anno)} "
           f"({(fatt_anno - costo_anno) / costo_anno * 100:.1f}% sul costo lotti). " if costo_anno > 0 else ". ")
        + f"Rotazione {rotazione}"
        + (f" ({mesi_cop:.1f} mesi di copertura con {_qt(giac)} pz in giacenza)" if mesi_cop is not None else "")
        + (f", riordinato in media ogni {riordino} giorni su {len(tutte_date)} ordini. " if riordino else ". ")
        + f"Nella finestra {ly_fs} - {ly_fe} dell'anno scorso ne sono stati venduti {_qt(qty_ly)} pz "
          f"({_eur(fatt_ly)}) a {len(ly)} clienti: e' la previsione per {fs} - {fe}. "
        + f"Negli ultimi {giorni} giorni ne sono usciti {_qt(qty_rec)} pz."
    )

    # ── clienti: confronto anno su anno ──
    nomi = sorted(set(ly) | set(rec), key=lambda n: -(ly.get(n, {}).get('fatt', 0) + rec.get(n, {}).get('fatt', 0)))
    righe_cli = []
    for n in nomi[:150]:
        a = ly.get(n, {})
        b = rec.get(n, {})
        qa, qb = a.get('qty', 0), b.get('qty', 0)
        var = ((qb - qa) / qa * 100) if qa else (100.0 if qb else 0.0)
        pa = (a['fatt'] / qa) if qa else None
        pb = (b['fatt'] / qb) if qb else None
        righe_cli.append([n, _qt(qa), _qt(qb), f"{var:+.0f}%",
                          _eur(pa) if pa else "-", _eur(pb) if pb else "-",
                          "fermo" if (qa and not qb) else ("nuovo" if (qb and not qa) else "attivo"),
                          (anno.get(n, {}).get('ultimo')) or "-"])

    tabelle = [{
        "titolo": f"Clienti: anno scorso ({ly_fs} - {ly_fe}) contro ultimi {giorni} giorni",
        "colonne": ["Cliente", "Qtà anno scorso", f"Qtà ultimi {giorni} gg", "Var. %",
                    "Prezzo allora", "Prezzo ora", "Stato", "Ultimo acquisto"],
        "righe": righe_cli,
    }, {
        "titolo": "Andamento mensile (ultimi 12 mesi)",
        "colonne": ["Mese", "Qtà", "Fatturato", "Prezzo medio", "Margine %", "Clienti"],
        "righe": [[m['_id'], _qt(m['qty']), _eur(m['fatt']),
                   _eur(m['fatt'] / m['qty']) if m['qty'] else "-",
                   f"{(m['fatt'] - m['costo']) / m['costo'] * 100:.1f}%" if m['costo'] > 0 else "-",
                   str(len(m.get('clienti') or []))] for m in mesi],
    }]
    if forn:
        tabelle.append({
            "titolo": "Fornitori: ruolo, prezzi e quantità acquistate (ultimi 12 mesi)",
            "colonne": ["Fornitore", "Ruolo", "Qtà", "Quota", "Spesa", "Prezzo medio", "Ordini", "Ultimo acquisto"],
            "righe": [[f['_id'],
                       "primario" if f['qty'] / qty_forn_tot >= 0.4 else
                       ("secondario" if f['qty'] / qty_forn_tot >= 0.1 else "occasionale"),
                       _qt(f['qty']), f"{f['qty'] / qty_forn_tot * 100:.0f}%", _eur(f['spesa']),
                       _eur(f['spesa'] / f['qty']) if f['qty'] else "-",
                       str(len(f.get('date') or [])), f['ultima']] for f in forn],
        })

    return {"titolo": prodotto, "spiegazione": spiegazione, "tabelle": tabelle}


# ─────────────────────────── PDF DEL PIANO ───────────────────────────
@router.get("/ottimizzazione/piano/pdf")
async def piano_pdf(tipo: str = "acquisti", giorni: int = 30, limit: int = 25,
                    nome: str = None):
    from fastapi.responses import Response
    from routes.ai_insight import blocco_considerazioni_ai
    from routes.pdf_helper import (C_AMBER, C_BLUE, C_EMERALD, C_NAVY, C_VIOLET,
                                   FlowPDF, clean_text, eur, it_num)

    d = await piano_azione(tipo=tipo, giorni=giorni, limit=200 if nome else limit)
    chiave = 'fornitore' if tipo == 'acquisti' else 'cliente'
    if nome:
        d['ordini'] = [o for o in d['ordini'] if o[chiave] == nome]
        if not d['ordini']:
            raise HTTPException(status_code=404, detail="Nessun piano per questa scheda")
        o = d['ordini'][0]
        if tipo == 'acquisti':
            q_att = sum(a['domanda_prevista'] for a in o['articoli'])
            q_prec = sum(a['domanda_anno_prec'] for a in o['articoli'])
            d['totali'] = {
                "fornitori": 1, "prodotti": len(o['articoli']),
                "valore_ordini": o['valore'], "margine_previsto": o['margine_eur'],
                "fatturato_atteso": o['fatturato_atteso'],
                "quantita_attesa": round(q_att, 1), "quantita_anno_prec": round(q_prec, 1),
                "var_quantita_pct": round((q_att - q_prec) / q_prec * 100, 1) if q_prec else None,
            }
        else:
            d['totali'] = {
                "clienti": 1, "valore_atteso": o['valore_atteso'],
                "valore_mancante": o['valore_mancante'], "margine_previsto": o['margine_eur'],
                "da_chiamare": 1 if o['azione'] in ("CHIAMA ORA", "CLIENTE FERMO") else 0,
            }
        d['suggerimenti'] = []
    per, tot = d['periodo'], d['totali']
    dm = lambda x: f"{x[8:10]}/{x[5:7]}/{x[2:4]}"  # noqa: E731
    acquisti = d['tipo'] == 'acquisti'

    titolo = ("PIANO DI ACQUISTO" if acquisti else "PIANO DI VENDITA") if not nome else \
        (f"ORDINE FORNITORE - {nome}" if acquisti else f"PROPOSTA CLIENTE - {nome}")
    pdf = FlowPDF(
        titolo,
        f"Previsione {per['giorni']} giorni: {dm(per['futuro_start'])} - {dm(per['futuro_end'])}  |  "
        f"Base {per['anno_base']}: {dm(per['storico_start'])} - {dm(per['storico_end'])}  |  "
        f"Confronto con {per['anno_confronto']}")
    pdf.add_page()

    if acquisti:
        arts = [a for o in d['ordini'] for a in o['articoli']]
        qty_tot = sum(a['domanda_prevista'] for a in arts)
        val_tot = sum(a['valore_domanda'] for a in arts)
        marg_tot = sum(max(a['margine_eur_domanda'], 0) for a in arts)
        fatt_tot = sum(a['fatturato_atteso'] for a in arts)
        pdf.kpi_row([
            ("DOMANDA PREVISTA", f"{it_num(qty_tot, 0)} kg/pz", C_BLUE, f"{len(arts)} articoli"
             + (f" ({tot['var_quantita_pct']:+.1f}% su {per['anno_confronto']})"
                if tot.get('var_quantita_pct') is not None else "")),
            ("VALORE ACQUISTO", eur(val_tot), C_AMBER,
             f"{tot['fornitori']} " + ("fornitore" if tot['fornitori'] == 1 else "fornitori")),
            ("MARGINE PREVISTO", eur(marg_tot), C_VIOLET, f"su {eur(fatt_tot)} attesi"),
            ("FATTURATO ATTESO", eur(fatt_tot), C_EMERALD, f"{eur(val_tot)} di acquisto"),
        ])
        pdf.note_text(
            "Valore = domanda prevista x prezzo di acquisto, nella stessa unita' di misura con cui "
            "l'articolo viene comprato e venduto (a kg per gli sfusi, a pezzo per i confezionati). "
            "La quantita' effettiva da ordinare si decide sul lotto medio, al netto della giacenza.")
        for o in d['ordini']:
            qty_forn = sum(a['domanda_prevista'] for a in o['articoli'])
            val_forn = sum(a['valore_domanda'] for a in o['articoli'])
            marg_forn = sum(max(a['margine_eur_domanda'], 0) for a in o['articoli'])
            mp_forn = (marg_forn / val_forn * 100) if val_forn else None
            pdf.section_title(f"{o['fornitore']} — {it_num(qty_forn, 0)} kg/pz · {eur(val_forn)}", C_BLUE)
            righe = [[clean_text(a['prodotto'])[:40],
                      it_num(a['domanda_prevista'], 0) +
                      (f" ({a['var_anno_pct']:+.0f}%)" if a['var_anno_pct'] is not None else ""),
                      a['rotazione'], f"{a['riordino_giorni']} gg" if a['riordino_giorni'] else '/',
                      it_num(a['lotto_medio'], 0) if a['lotto_medio'] else '-',
                      eur(a['prezzo_acquisto']) if a['prezzo_acquisto'] else '-',
                      eur(a['prezzo_vendita_atteso']) if a['prezzo_vendita_atteso'] else '-',
                      f"{a['margine_pct']}%" if a['margine_pct'] is not None else '-',
                      eur(a['valore_domanda'])] for a in o['articoli'][:40]]
            righe.append(['TOTALE', it_num(qty_forn, 0), '', '', '', '', '',
                          f"{mp_forn:.1f}%" if mp_forn is not None else '-', eur(val_forn)])
            pdf.smart_table(["Articolo", f"Domanda prev. {per['anno_base']}", 'Rotazione',
                             'Riordino ogni', 'Lotto medio', 'Prezzo acq.', 'Prezzo vend.',
                             'Marg. %', 'Valore'],
                            [46, 24, 17, 19, 20, 19, 19, 14, 21], righe,
                            aligns=['L', 'R', 'C', 'R', 'R', 'R', 'R', 'R', 'R'])
    else:
        qty_tot = sum(a['quantita_attesa'] for o in d['ordini'] for a in o['articoli'])
        pdf.kpi_row([
            ("FATTURATO ATTESO", eur(tot['valore_atteso']), C_BLUE, f"{it_num(qty_tot, 0)} kg/pz attesi"),
            ("DA PROPORRE", eur(tot['valore_mancante']), C_AMBER, "non ancora riordinato"),
            ("MARGINE PREVISTO", eur(tot['margine_previsto']), C_VIOLET, "sul costo lotti (FIFO)"),
            ("CLIENTI DA SENTIRE", f"{tot['da_chiamare']} di {tot['clienti']}", C_EMERALD,
             f"prossimi {per['giorni']} giorni"),
        ])
        for o in d['ordini']:
            qty_cli = sum(a['quantita_attesa'] for a in o['articoli'])
            pdf.section_title(f"{o['cliente']} — {o['azione']} · {eur(o['valore_atteso'])}", C_EMERALD)
            righe = [[clean_text(a['prodotto'])[:44], it_num(a['quantita_attesa'], 0),
                      eur(a['prezzo_atteso']) if a['prezzo_atteso'] else '-',
                      eur(a['valore_atteso']),
                      'gia ordinato' if a['gia_ordinato'] else 'da proporre']
                     for a in o['articoli'][:40]]
            righe.append(['TOTALE', it_num(qty_cli, 0), '', eur(o['valore_atteso']),
                          f"{o['prodotti_mancanti']} da proporre"])
            pdf.smart_table(['Articolo', 'Qta attesa', 'Prezzo atteso', 'Valore', 'Stato'],
                            [76, 24, 26, 28, 26], righe,
                            aligns=['L', 'R', 'R', 'R', 'R'])

    if d.get('suggerimenti'):
        pdf.section_title("Punti di attenzione", C_NAVY)
        pdf.smart_table(['Area', 'Voce', 'Dettaglio', 'Valore'],
                        [44, 52, 70, 24],
                        [[s['titolo'], clean_text(v['nome'])[:40], clean_text(v['dettaglio'])[:60],
                          eur(v['valore'])]
                         for s in d['suggerimenti'] for v in s['voci'][:5]],
                        aligns=['L', 'L', 'L', 'R'])

    ctx_righe = []
    for o in d['ordini'][:8]:
        if acquisti:
            ctx_righe.append(
                f"{o['fornitore']}: {o['prodotti_n']} articoli, valore acquisto previsto € "
                f"{round(sum(a['valore_domanda'] for a in o['articoli']), 2)}, "
                f"margine previsto {o['margine_pct']}%, spesa ultimi 12 mesi € {o['spesa_ultimo_anno']}, "
                f"fatturato atteso € {o['fatturato_atteso']}. Articoli con riordino ricorrente: " +
                "; ".join(f"{a['prodotto']} domanda prevista {a['domanda_prevista']} "
                          f"({a['var_anno_pct']:+.0f}% sull'anno precedente) "
                          f"rotazione {a['rotazione']}, riordino ogni {a['riordino_giorni']} gg, "
                          f"lotto medio {a['lotto_medio']}, acquisto € {a['prezzo_acquisto']}, "
                          f"vendita € {a['prezzo_vendita_atteso']}, margine {a['margine_pct']}%, "
                          f"valore acquisto € {a['valore_domanda']}, "
                          f"fatturato atteso € {a['fatturato_atteso']}"
                          for a in o['articoli'][:8]
                          if a['riordino_giorni'] and a['var_anno_pct'] is not None))
        else:
            ctx_righe.append(f"{o['cliente']}: {o['azione']}, atteso € {o['valore_atteso']}, "
                             f"{o['prodotti_mancanti']} referenze da proporre su {o['prodotti_n']}, "
                             f"ultimo ordine {o['ultimo_ordine']}")
    ctx = (f"Piano {d['tipo']} per i prossimi {per['giorni']} giorni ({per['futuro_start']} - "
           f"{per['futuro_end']}), previsione basata sul venduto dello stesso intervallo dell'anno precedente.\n"
           f"Totali: {tot}\n" + "\n".join(ctx_righe))
    extra = (
        "- Il PRIMO punto deve riguardare la leva dello SCONTO sul fatturato ipotetico che porti al "
        "fornitore: cita il valore dell'ordine previsto (e la spesa degli ultimi 12 mesi se presente) e "
        "indica quale sconto chiedere e su quali articoli, con gli importi.\n"
        "- Parla SOLO di: fatturato/valore ordine, sconto e margine, prezzi di acquisto e vendita, "
        "gestione complessiva del fornitore (numero di ordini, entita' dell'ordine, frequenza di riordino, "
        "concentrazione della spesa su pochi articoli).\n"
        "- Considera SOLO gli articoli elencati nei dati; non parlare di giacenze, scorte o copertura "
        "di magazzino.\n"
        "- Le quantita' sono espresse nell'unita' con cui l'articolo viene comprato e venduto "
        "(kg per gli sfusi, pezzi per i confezionati): non aggiungere mai 'pz' o 'kg' alle quantita'.\n"
        "- VIETATO: usare le parole 'riga' o 'righe' (usa 'articoli'); parlare del rischio di dipendenza "
        "da un unico fornitore, di fornitori alternativi o di secondo fornitore.\n"
    ) if acquisti else ""
    await blocco_considerazioni_ai(pdf, ctx, f"piano-{d['tipo']}-{per['futuro_start']}-{per['giorni']}",
                                   extra=extra)

    out = pdf.output()
    base = "".join(c if c.isalnum() else "_" for c in nome)[:40] if nome else d['tipo']
    fname = f"piano_{base}_{per['futuro_start']}_{per['futuro_end']}.pdf"
    return Response(bytes(out), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={fname}"})
