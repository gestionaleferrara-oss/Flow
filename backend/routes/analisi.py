from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from database import db

router = APIRouter()

EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']


async def reference_date() -> datetime:
    latest = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", -1)])
    if latest and latest.get('data'):
        try:
            return datetime.strptime(latest['data'], "%Y-%m-%d")
        except Exception:
            pass
    return datetime.now()


async def resolve_period(start_date: Optional[str], end_date: Optional[str]):
    """Return (start, end, prev_start, prev_end) as YYYY-MM-DD strings."""
    if not start_date or not end_date:
        ref = await reference_date()
        start_date = ref.replace(day=1).strftime("%Y-%m-%d")
        end_date = ref.strftime("%Y-%m-%d")
    s = datetime.strptime(start_date, "%Y-%m-%d")
    e = datetime.strptime(end_date, "%Y-%m-%d")
    days = max((e - s).days, 0)
    prev_e = s - timedelta(days=1)
    prev_s = prev_e - timedelta(days=days)
    return start_date, end_date, prev_s.strftime("%Y-%m-%d"), prev_e.strftime("%Y-%m-%d")


async def esclusi_filter() -> Dict:
    from routes.esclusioni import get_prodotti_esclusi
    esclusi = await get_prodotti_esclusi()
    return {"prodotto_nome": {"$nin": esclusi}} if esclusi else {}


async def prezzi_acquisto(nomi: List[str], start: str, end: str) -> Dict[str, float]:
    """Weighted avg purchase price in period, fallback to last known purchase price."""
    if not nomi:
        return {}
    pipeline = [
        {"$match": {"prodotto_nome": {"$in": nomi}, "quantita": {"$gt": 0},
                    "totale": {"$gt": 0}, "data": {"$gte": start, "$lte": end}}},
        {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": "$quantita"}, "tot": {"$sum": "$totale"}}}
    ]
    rows = await db.ordini.aggregate(pipeline).to_list(20000)
    prezzi = {r['_id']: r['tot'] / r['qty'] for r in rows if r['_id'] and r['qty'] > 0}

    missing = [n for n in nomi if n not in prezzi]
    if missing:
        pipeline2 = [
            {"$match": {"prodotto_nome": {"$in": missing}, "prezzo_unitario": {"$gt": 0},
                        "quantita": {"$gt": 0}, "data": {"$lte": end}}},
            {"$sort": {"data": -1}},
            {"$group": {"_id": "$prodotto_nome", "prezzo": {"$first": "$prezzo_unitario"}}}
        ]
        rows2 = await db.ordini.aggregate(pipeline2).to_list(20000)
        for r in rows2:
            if r['_id'] and 0 < r['prezzo'] < 1000:
                prezzi[r['_id']] = r['prezzo']
    return prezzi


# ═══════════════ VENDITE PER PRODOTTO ═══════════════

@router.get("/analisi/vendite-prodotti")
async def analisi_vendite_prodotti(
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    search: Optional[str] = None, cliente: Optional[str] = None, limit: int = 300
):
    start, end, prev_start, prev_end = await resolve_period(start_date, end_date)
    excl = await esclusi_filter()

    base_match = {"cliente_nome": {"$nin": EXCLUDED_CLIENTS}, **excl}
    if cliente:
        base_match["$and"] = [{"cliente_nome": {"$nin": EXCLUDED_CLIENTS}},
                              {"cliente_nome": {"$regex": cliente, "$options": "i"}}]
    if search:
        base_match["prodotto_nome"] = {"$regex": search, "$options": "i"}

    def agg(s, e):
        return [
            {"$match": {**base_match, "data": {"$gte": s, "$lte": e}}},
            {"$group": {
                "_id": "$prodotto_nome",
                "quantita": {"$sum": {"$abs": "$quantita"}},
                "fatturato": {"$sum": {"$abs": "$totale"}},
                "costo_fifo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                "qty_tracciata": {"$sum": {"$cond": [{"$eq": ["$fifo_tracciato", True]}, {"$abs": "$quantita"}, 0]}},
                "righe": {"$sum": 1},
                "clienti": {"$addToSet": "$cliente_nome"},
            }},
            {"$project": {"quantita": 1, "fatturato": 1, "righe": 1, "costo_fifo": 1,
                          "qty_tracciata": 1, "n_clienti": {"$size": "$clienti"}}},
        ]

    curr = await db.vendite.aggregate(agg(start, end)).to_list(20000)
    prev = await db.vendite.aggregate(agg(prev_start, prev_end)).to_list(20000)
    prev_map = {p['_id']: p for p in prev}

    nomi = [c['_id'] for c in curr if c['_id']]
    costi = await prezzi_acquisto(nomi, start, end)

    rows = []
    tot_fatturato = tot_qty = tot_costo = 0.0
    for c in curr:
        nome = c['_id']
        if not nome:
            continue
        qty = c['quantita']
        fatt = c['fatturato']
        prezzo_medio = fatt / qty if qty > 0 else 0
        # Costo reale FIFO (lotto per lotto); fallback al prezzo di acquisto ponderato del periodo
        costo_tot = c.get('costo_fifo', 0) or 0
        fifo = costo_tot > 0
        costo_unit = (costo_tot / qty) if (fifo and qty > 0) else costi.get(nome, 0)
        if not fifo:
            costo_tot = costo_unit * qty
        margine = ((fatt - costo_tot) / costo_tot * 100) if costo_tot > 0 else None
        copertura = (c.get('qty_tracciata', 0) / qty * 100) if qty > 0 else 0
        p = prev_map.get(nome)
        prev_fatt = p['fatturato'] if p else 0
        prev_qty = p['quantita'] if p else 0
        rows.append({
            "prodotto": nome,
            "quantita": round(qty, 2),
            "fatturato": round(fatt, 2),
            "prezzo_medio": round(prezzo_medio, 4),
            "costo_unitario": round(costo_unit, 4) if costo_unit else None,
            "margine_pct": round(margine, 1) if margine is not None else None,
            "profitto": round(fatt - costo_tot, 2) if costo_tot > 0 else None,
            "da_lotti": fifo,
            "copertura_lotti_pct": round(copertura, 0),
            "n_clienti": c.get('n_clienti', 0),
            "righe": c.get('righe', 0),
            "fatturato_prec": round(prev_fatt, 2),
            "quantita_prec": round(prev_qty, 2),
            "var_fatturato_pct": round((fatt - prev_fatt) / prev_fatt * 100, 1) if prev_fatt > 0 else None,
            "var_quantita_pct": round((qty - prev_qty) / prev_qty * 100, 1) if prev_qty > 0 else None,
        })
        tot_fatturato += fatt
        tot_qty += qty
        tot_costo += costo_tot

    rows.sort(key=lambda r: r['fatturato'], reverse=True)
    tot_prev = sum(p['fatturato'] for p in prev if p['_id'])

    return {
        "periodo": {"start": start, "end": end, "prev_start": prev_start, "prev_end": prev_end},
        "kpi": {
            "fatturato": round(tot_fatturato, 2),
            "fatturato_prec": round(tot_prev, 2),
            "var_pct": round((tot_fatturato - tot_prev) / tot_prev * 100, 1) if tot_prev > 0 else None,
            "quantita": round(tot_qty, 2),
            "n_prodotti": len(rows),
            "margine_medio_pct": round((tot_fatturato - tot_costo) / tot_costo * 100, 1) if tot_costo > 0 else None,
            "profitto_stimato": round(tot_fatturato - tot_costo, 2) if tot_costo > 0 else None,
        },
        "prodotti": rows[:limit],
    }


@router.get("/analisi/prodotto-dettaglio")
async def analisi_prodotto_dettaglio(
    nome: str, start_date: Optional[str] = None, end_date: Optional[str] = None
):
    if not nome:
        raise HTTPException(status_code=400, detail="Nome prodotto richiesto")
    start, end, _, _ = await resolve_period(start_date, end_date)

    trend_pipeline = [
        {"$match": {"prodotto_nome": nome, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
        {"$group": {
            "_id": {"$substr": ["$data", 0, 7]},
            "quantita": {"$sum": {"$abs": "$quantita"}},
            "fatturato": {"$sum": {"$abs": "$totale"}},
            "costo_fifo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
        }},
        {"$sort": {"_id": 1}},
    ]
    trend = await db.vendite.aggregate(trend_pipeline).to_list(200)

    acq_pipeline = [
        {"$match": {"prodotto_nome": nome, "quantita": {"$gt": 0}}},
        {"$group": {
            "_id": {"$substr": ["$data", 0, 7]},
            "quantita": {"$sum": "$quantita"},
            "spesa": {"$sum": "$totale"},
        }},
        {"$sort": {"_id": 1}},
    ]
    acquisti = await db.ordini.aggregate(acq_pipeline).to_list(200)
    acq_map = {a['_id']: a for a in acquisti}

    serie = []
    for t in trend[-24:]:
        a = acq_map.get(t['_id'], {})
        pv = t['fatturato'] / t['quantita'] if t['quantita'] > 0 else 0
        pa = (a.get('spesa', 0) / a['quantita']) if a.get('quantita') else 0
        costo_fifo = t.get('costo_fifo', 0) or 0
        costo_unit_fifo = costo_fifo / t['quantita'] if (costo_fifo > 0 and t['quantita'] > 0) else 0
        base_costo = costo_unit_fifo or pa
        serie.append({
            "mese": t['_id'],
            "quantita": round(t['quantita'], 2),
            "fatturato": round(t['fatturato'], 2),
            "prezzo_vendita": round(pv, 4),
            "prezzo_acquisto": round(pa, 4) if pa else None,
            "costo_lotti": round(costo_unit_fifo, 4) if costo_unit_fifo else None,
            "quantita_acquistata": round(a.get('quantita', 0), 2),
            "margine_pct": round((pv - base_costo) / base_costo * 100, 1) if base_costo > 0 else None,
        })

    clienti_pipeline = [
        {"$match": {"prodotto_nome": nome, "data": {"$gte": start, "$lte": end},
                    "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
        {"$group": {"_id": "$cliente_nome", "quantita": {"$sum": {"$abs": "$quantita"}},
                    "fatturato": {"$sum": {"$abs": "$totale"}}, "ordini": {"$sum": 1},
                    "costo_fifo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}}}},
        {"$sort": {"fatturato": -1}},
        {"$limit": 20},
    ]
    top_clienti = await db.vendite.aggregate(clienti_pipeline).to_list(20)

    fornitori_pipeline = [
        {"$match": {"prodotto_nome": nome, "quantita": {"$gt": 0}, "data": {"$gte": start, "$lte": end}}},
        {"$group": {"_id": "$fornitore_nome", "quantita": {"$sum": "$quantita"},
                    "spesa": {"$sum": "$totale"}}},
        {"$sort": {"spesa": -1}},
    ]
    fornitori = await db.ordini.aggregate(fornitori_pipeline).to_list(100)

    prodotto = await db.prodotti.find_one({"nome": nome}, {"_id": 0})

    lotti = await db.lotti.find({"prodotto": nome}, {"_id": 0}).sort([("data_acquisto", -1)]).limit(60).to_list(60)

    clienti_out = []
    for c in top_clienti:
        if not c['_id']:
            continue
        qty = c['quantita']
        fatt = c['fatturato']
        costo = c.get('costo_fifo', 0) or 0
        prezzo = fatt / qty if qty > 0 else 0
        clienti_out.append({
            "cliente": c['_id'],
            "quantita": round(qty, 2),
            "fatturato": round(fatt, 2),
            "prezzo_medio": round(prezzo, 4),
            "costo_unitario": round(costo / qty, 4) if (costo > 0 and qty > 0) else None,
            "margine_pct": round((fatt - costo) / costo * 100, 1) if costo > 0 else None,
            "ordini": c['ordini'],
        })

    return {
        "nome": nome,
        "periodo": {"start": start, "end": end},
        "giacenza": prodotto.get('quantita', 0) if prodotto else 0,
        "quantita_minima": prodotto.get('quantita_minima', 0) if prodotto else 0,
        "serie_mensile": serie,
        "lotti": lotti,
        "top_clienti": clienti_out,
        "fornitori": [{"fornitore": f['_id'], "quantita": round(f['quantita'], 2),
                       "spesa": round(f['spesa'], 2),
                       "prezzo_medio": round(f['spesa'] / f['quantita'], 4) if f['quantita'] > 0 else 0}
                      for f in fornitori if f['_id']],
    }


# ═══════════════ ACQUISTI FORNITORI ═══════════════

@router.get("/analisi/acquisti")
async def analisi_acquisti(
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    fornitore: Optional[str] = None, prodotto: Optional[str] = None, limit: int = 300
):
    start, end, prev_start, prev_end = await resolve_period(start_date, end_date)
    excl = await esclusi_filter()

    base = {**excl}
    if fornitore:
        base["fornitore_nome"] = {"$regex": fornitore, "$options": "i"}
    if prodotto:
        base["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}

    def by(field, s, e):
        return [
            {"$match": {**base, "data": {"$gte": s, "$lte": e}}},
            {"$group": {
                "_id": f"${field}",
                "quantita": {"$sum": "$quantita"},
                "spesa": {"$sum": "$totale"},
                "qty_v": {"$sum": {"$cond": [{"$and": [{"$gt": ["$totale", 0]}, {"$gt": ["$quantita", 0]}]},
                                             "$quantita", 0]}},
                "spesa_v": {"$sum": {"$cond": [{"$and": [{"$gt": ["$totale", 0]}, {"$gt": ["$quantita", 0]}]},
                                               "$totale", 0]}},
                "righe": {"$sum": 1},
                "altro": {"$addToSet": "$prodotto_nome" if field == "fornitore_nome" else "$fornitore_nome"},
                "resi": {"$sum": {"$cond": [{"$lt": ["$quantita", 0]}, {"$abs": "$totale"}, 0]}},
            }},
            {"$project": {"quantita": 1, "spesa": 1, "righe": 1, "resi": 1, "qty_v": 1, "spesa_v": 1,
                          "n_altro": {"$size": "$altro"}}},
        ]

    def _prezzo_medio(d):
        """Prezzo unitario ponderato escludendo le righe senza importo (dati incompleti)."""
        if d.get('qty_v', 0) > 0:
            return d['spesa_v'] / d['qty_v']
        return d['spesa'] / d['quantita'] if d.get('quantita') else 0

    forn_curr = await db.ordini.aggregate(by("fornitore_nome", start, end)).to_list(5000)
    forn_prev = await db.ordini.aggregate(by("fornitore_nome", prev_start, prev_end)).to_list(5000)
    prev_map = {f['_id']: f['spesa'] for f in forn_prev}
    prod_curr = await db.ordini.aggregate(by("prodotto_nome", start, end)).to_list(20000)

    fornitori = []
    for f in forn_curr:
        if not f['_id']:
            continue
        prev_spesa = prev_map.get(f['_id'], 0)
        fornitori.append({
            "fornitore": f['_id'],
            "spesa": round(f['spesa'], 2),
            "quantita": round(f['quantita'], 2),
            "prezzo_medio": round(_prezzo_medio(f), 4),
            "n_prodotti": f.get('n_altro', 0),
            "righe": f.get('righe', 0),
            "resi": round(f.get('resi', 0), 2),
            "spesa_prec": round(prev_spesa, 2),
            "var_pct": round((f['spesa'] - prev_spesa) / prev_spesa * 100, 1) if prev_spesa > 0 else None,
        })
    fornitori.sort(key=lambda x: x['spesa'], reverse=True)

    prodotti = []
    for p in prod_curr:
        if not p['_id']:
            continue
        prodotti.append({
            "prodotto": p['_id'],
            "spesa": round(p['spesa'], 2),
            "quantita": round(p['quantita'], 2),
            "prezzo_medio": round(_prezzo_medio(p), 4),
            "n_fornitori": p.get('n_altro', 0),
            "resi": round(p.get('resi', 0), 2),
        })
    prodotti.sort(key=lambda x: x['spesa'], reverse=True)

    trend_pipeline = [
        {"$match": {**base, "data": {"$gte": start, "$lte": end}}},
        {"$group": {"_id": {"$substr": ["$data", 0, 7]}, "spesa": {"$sum": "$totale"},
                    "quantita": {"$sum": "$quantita"}}},
        {"$sort": {"_id": 1}},
    ]
    trend = await db.ordini.aggregate(trend_pipeline).to_list(200)

    # Margine reale generato dai lotti acquistati nel periodo (collegamento FIFO)
    lotti_match = {"data_acquisto": {"$gte": start, "$lte": end}}
    if fornitore:
        lotti_match["fornitore"] = {"$regex": fornitore, "$options": "i"}
    if prodotto:
        lotti_match["prodotto"] = {"$regex": prodotto, "$options": "i"}

    async def margini_per(campo):
        rows = await db.lotti.aggregate([
            {"$match": lotti_match},
            {"$group": {"_id": f"${campo}", "ricavo": {"$sum": "$ricavo"},
                        "qty_venduta": {"$sum": "$quantita_venduta"},
                        "costo_venduto": {"$sum": {"$multiply": ["$quantita_venduta", "$prezzo_acquisto"]}}}}
        ]).to_list(20000)
        return {r['_id']: r for r in rows if r['_id']}

    marg_forn = await margini_per("fornitore")
    marg_prod = await margini_per("prodotto")

    def arricchisci(riga, chiave, mappa):
        m = mappa.get(riga[chiave])
        if not m:
            riga.update({"qty_venduta": 0, "ricavo": 0, "margine": None, "margine_pct": None,
                         "prezzo_vendita": None})
            return riga
        costo = m['costo_venduto'] or 0
        riga.update({
            "qty_venduta": round(m['qty_venduta'], 2),
            "ricavo": round(m['ricavo'], 2),
            "margine": round(m['ricavo'] - costo, 2) if costo > 0 else None,
            "margine_pct": round((m['ricavo'] - costo) / costo * 100, 1) if costo > 0 else None,
            "prezzo_vendita": round(m['ricavo'] / m['qty_venduta'], 4) if m['qty_venduta'] else None,
        })
        return riga

    fornitori = [arricchisci(f, 'fornitore', marg_forn) for f in fornitori]
    prodotti = [arricchisci(p, 'prodotto', marg_prod) for p in prodotti]

    tot_spesa = sum(f['spesa'] for f in fornitori)
    tot_prev = sum(prev_map.values())

    return {
        "periodo": {"start": start, "end": end, "prev_start": prev_start, "prev_end": prev_end},
        "kpi": {
            "spesa": round(tot_spesa, 2),
            "spesa_prec": round(tot_prev, 2),
            "var_pct": round((tot_spesa - tot_prev) / tot_prev * 100, 1) if tot_prev > 0 else None,
            "quantita": round(sum(f['quantita'] for f in fornitori), 2),
            "n_fornitori": len(fornitori),
            "n_prodotti": len(prodotti),
            "resi": round(sum(f['resi'] for f in fornitori), 2),
        },
        "fornitori": fornitori[:limit],
        "prodotti": prodotti[:limit],
        "trend": [{"mese": t['_id'], "spesa": round(t['spesa'], 2), "quantita": round(t['quantita'], 2)}
                  for t in trend],
    }


@router.get("/analisi/confronto-fornitori")
async def analisi_confronto_fornitori(
    prodotto: str, start_date: Optional[str] = None, end_date: Optional[str] = None
):
    if not prodotto:
        raise HTTPException(status_code=400, detail="Prodotto richiesto")
    start, end, _, _ = await resolve_period(start_date, end_date)

    pipeline = [
        {"$match": {"prodotto_nome": prodotto, "quantita": {"$gt": 0},
                    "data": {"$gte": start, "$lte": end}}},
        {"$sort": {"data": -1}},
        {"$group": {
            "_id": "$fornitore_nome",
            "quantita": {"$sum": "$quantita"},
            "spesa": {"$sum": "$totale"},
            "ultimo_prezzo": {"$first": "$prezzo_unitario"},
            "ultima_data": {"$first": "$data"},
            "ordini": {"$sum": 1},
        }},
    ]
    rows = await db.ordini.aggregate(pipeline).to_list(200)
    fornitori = [{
        "fornitore": r['_id'],
        "quantita": round(r['quantita'], 2),
        "spesa": round(r['spesa'], 2),
        "prezzo_medio": round(r['spesa'] / r['quantita'], 4) if r['quantita'] > 0 else 0,
        "ultimo_prezzo": round(r.get('ultimo_prezzo', 0) or 0, 4),
        "ultima_data": r.get('ultima_data'),
        "ordini": r['ordini'],
    } for r in rows if r['_id']]
    fornitori.sort(key=lambda x: x['prezzo_medio'])

    # revenue side for reference
    vend = await db.vendite.aggregate([
        {"$match": {"prodotto_nome": prodotto, "data": {"$gte": start, "$lte": end},
                    "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
        {"$group": {"_id": None, "qty": {"$sum": {"$abs": "$quantita"}}, "tot": {"$sum": {"$abs": "$totale"}}}}
    ]).to_list(1)
    prezzo_vendita = (vend[0]['tot'] / vend[0]['qty']) if vend and vend[0]['qty'] > 0 else 0

    risparmio = None
    if len(fornitori) > 1:
        best, worst = fornitori[0], fornitori[-1]
        qty_tot = sum(f['quantita'] for f in fornitori)
        risparmio = {
            "migliore": best['fornitore'], "prezzo_migliore": best['prezzo_medio'],
            "peggiore": worst['fornitore'], "prezzo_peggiore": worst['prezzo_medio'],
            "risparmio_potenziale": round((worst['prezzo_medio'] - best['prezzo_medio']) * qty_tot, 2),
        }

    return {
        "prodotto": prodotto,
        "periodo": {"start": start, "end": end},
        "prezzo_vendita_medio": round(prezzo_vendita, 4),
        "fornitori": fornitori,
        "confronto": risparmio,
    }


@router.get("/analisi/opzioni")
async def analisi_opzioni(q: str = "", tipo: str = "fornitori", limit: int = 25):
    coll = {"fornitori": db.fornitori, "clienti": db.clienti, "prodotti": db.prodotti}.get(tipo, db.prodotti)
    query = {"nome": {"$regex": q, "$options": "i"}} if q else {}
    rows = await coll.find(query, {"_id": 0, "nome": 1}).sort("nome", 1).limit(limit).to_list(limit)
    return {"nomi": [r['nome'] for r in rows if r.get('nome')]}


@router.get("/analisi/previsione-prodotto")
async def previsione_prodotto(prodotto: str, giorni: int = 30):
    """Previsione dei prossimi N giorni per un prodotto, sulla base dello stesso
    intervallo dell'anno precedente, con i clienti che lo hanno comprato."""
    giorni = max(min(giorni, 180), 7)
    oggi = datetime.now()
    fs, fe = oggi, oggi + timedelta(days=giorni - 1)
    ly_fs, ly_fe = fs - timedelta(days=365), fe - timedelta(days=365)
    f = "%Y-%m-%d"
    periodo = {"futuro_start": fs.strftime(f), "futuro_end": fe.strftime(f),
               "storico_start": ly_fs.strftime(f), "storico_end": ly_fe.strftime(f), "giorni": giorni}

    match = {"prodotto_nome": prodotto, "cliente_nome": {"$nin": EXCLUDED_CLIENTS},
             "data": {"$gte": periodo['storico_start'], "$lte": periodo['storico_end']}}
    clienti = await db.vendite.aggregate([
        {"$match": match},
        {"$group": {"_id": "$cliente_nome", "quantita": {"$sum": {"$abs": "$quantita"}},
                    "fatturato": {"$sum": {"$abs": "$totale"}},
                    "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                    "righe": {"$sum": 1}, "ultimo": {"$max": "$data"}}},
        {"$sort": {"fatturato": -1}},
    ]).to_list(2000)

    recenti_start = (oggi - timedelta(days=giorni)).strftime(f)
    recenti = await db.vendite.aggregate([
        {"$match": {"prodotto_nome": prodotto, "cliente_nome": {"$nin": EXCLUDED_CLIENTS},
                    "data": {"$gte": recenti_start, "$lte": oggi.strftime(f)}}},
        {"$group": {"_id": "$cliente_nome", "quantita": {"$sum": {"$abs": "$quantita"}}}},
    ]).to_list(2000)
    gia_ordinato = {r['_id']: r['quantita'] for r in recenti}

    ultimo_ordine = await db.vendite.aggregate([
        {"$match": {"prodotto_nome": prodotto, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
        {"$group": {"_id": "$cliente_nome", "ultimo": {"$max": "$data"}}},
    ]).to_list(5000)
    ultimo_map = {r['_id']: r['ultimo'] for r in ultimo_ordine}

    qty = sum(c['quantita'] for c in clienti)
    fatt = sum(c['fatturato'] for c in clienti)
    costo = sum(c['costo'] for c in clienti)

    prod = await db.prodotti.find_one({"nome": prodotto}, {"_id": 0, "quantita": 1})
    giacenza = (prod or {}).get('quantita', 0) or 0

    ultimo_acq = await db.ordini.aggregate([
        {"$match": {"prodotto_nome": prodotto, "quantita": {"$gt": 0}, "totale": {"$gt": 0}}},
        {"$group": {"_id": "$fornitore_nome", "qty": {"$sum": "$quantita"},
                    "spesa": {"$sum": "$totale"}, "ultima": {"$max": "$data"}}},
        {"$sort": {"ultima": -1}},
    ]).to_list(200)
    fornitore = ultimo_acq[0] if ultimo_acq else None

    return {
        "prodotto": prodotto, "periodo": periodo,
        "kpi": {
            "quantita_attesa": round(qty, 1),
            "fatturato_atteso": round(fatt, 2),
            "prezzo_medio": round(fatt / qty, 4) if qty else None,
            "margine_atteso": round(fatt - costo, 2) if costo else None,
            "margine_pct": round((fatt - costo) / costo * 100, 1) if costo > 0 else None,
            "clienti_attesi": len(clienti),
            "giacenza": round(giacenza, 1),
            "da_ordinare": round(max(qty - giacenza, 0), 1),
            "copertura_giorni": round(giacenza / (qty / giorni)) if qty > 0 else None,
            "fornitore_consigliato": fornitore['_id'] if fornitore else None,
            "prezzo_acquisto": round(fornitore['spesa'] / fornitore['qty'], 4)
            if fornitore and fornitore['qty'] else None,
        },
        "clienti": [{
            "cliente": c['_id'],
            "quantita_attesa": round(c['quantita'], 1),
            "fatturato_atteso": round(c['fatturato'], 2),
            "prezzo_medio": round(c['fatturato'] / c['quantita'], 4) if c['quantita'] else None,
            "margine_pct": round((c['fatturato'] - c['costo']) / c['costo'] * 100, 1) if c['costo'] > 0 else None,
            "righe": c['righe'],
            "ultimo_acquisto": ultimo_map.get(c['_id']),
            "gia_ordinato": round(gia_ordinato.get(c['_id'], 0), 1),
        } for c in clienti[:100]],
    }


def _finestra_previsione(giorni: int):
    giorni = max(min(giorni, 180), 7)
    oggi = datetime.now()
    fs, fe = oggi, oggi + timedelta(days=giorni - 1)
    f = "%Y-%m-%d"
    return {"futuro_start": fs.strftime(f), "futuro_end": fe.strftime(f),
            "storico_start": (fs - timedelta(days=365)).strftime(f),
            "storico_end": (fe - timedelta(days=365)).strftime(f),
            "recenti_start": (oggi - timedelta(days=giorni)).strftime(f),
            "recenti_end": oggi.strftime(f),
            "giorni": giorni}




async def _prev_prodotti(nomi: List[str], giorni: int) -> Dict:
    per = _finestra_previsione(giorni)
    base = {"prodotto_nome": {"$in": nomi}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}

    per_cliente = await db.vendite.aggregate([
        {"$match": {**base, "data": {"$gte": per['storico_start'], "$lte": per['storico_end']}}},
        {"$group": {"_id": "$cliente_nome", "quantita": {"$sum": {"$abs": "$quantita"}},
                    "fatturato": {"$sum": {"$abs": "$totale"}},
                    "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                    "prodotti": {"$addToSet": "$prodotto_nome"}, "ultimo": {"$max": "$data"}}},
        {"$sort": {"fatturato": -1}},
    ]).to_list(3000)

    per_prodotto = await db.vendite.aggregate([
        {"$match": {**base, "data": {"$gte": per['storico_start'], "$lte": per['storico_end']}}},
        {"$group": {"_id": "$prodotto_nome", "quantita": {"$sum": {"$abs": "$quantita"}},
                    "fatturato": {"$sum": {"$abs": "$totale"}},
                    "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                    "clienti": {"$addToSet": "$cliente_nome"}}},
    ]).to_list(3000)

    recenti = await db.vendite.aggregate([
        {"$match": {**base, "data": {"$gte": per['recenti_start'], "$lte": per['recenti_end']}}},
        {"$group": {"_id": "$cliente_nome", "quantita": {"$sum": {"$abs": "$quantita"}}}},
    ]).to_list(3000)
    gia = {r['_id']: r['quantita'] for r in recenti}

    giacenze = {d['nome']: (d.get('quantita', 0) or 0) for d in
                await db.prodotti.find({"nome": {"$in": nomi}}, {"_id": 0, "nome": 1, "quantita": 1}).to_list(2000)}

    forn = await db.ordini.aggregate([
        {"$match": {"prodotto_nome": {"$in": nomi}, "quantita": {"$gt": 0}, "totale": {"$gt": 0},
                    "data": {"$gte": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")}}},
        {"$group": {"_id": {"p": "$prodotto_nome", "f": "$fornitore_nome"},
                    "qty": {"$sum": "$quantita"}, "spesa": {"$sum": "$totale"},
                    "ultima": {"$max": "$data"}}},
    ]).to_list(20000)
    # fornitore di riferimento = quello da cui si acquista la quantita' maggiore (primario)
    best = {}
    for r in forn:
        pnome, fnome = r['_id'].get('p'), r['_id'].get('f')
        if not pnome or not fnome or r['qty'] <= 0:
            continue
        if pnome not in best or r['qty'] > best[pnome]['qty']:
            best[pnome] = {"fornitore": fnome, "prezzo": r['spesa'] / r['qty'], "qty": r['qty']}

    fatt = sum(r['fatturato'] for r in per_cliente)
    costo = sum(r['costo'] for r in per_cliente)
    qty = sum(r['quantita'] for r in per_cliente)
    da_ordinare_tot = 0.0
    valore_ordine = 0.0
    prodotti_righe = []
    for r in per_prodotto:
        giac = giacenze.get(r['_id'], 0) or 0
        da_ord = max(r['quantita'] - giac, 0)
        da_ordinare_tot += da_ord
        b = best.get(r['_id'])
        valore_ordine += da_ord * (b['prezzo'] if b else 0)
        prodotti_righe.append({
            "nome": r['_id'],
            "domanda_prevista": round(r['quantita'], 1),
            "giacenza": round(giac, 1),
            "da_ordinare": round(da_ord, 1),
            "prezzo_acquisto": round(b['prezzo'], 4) if b else None,
            "prezzo_vendita_atteso": round(r['fatturato'] / r['quantita'], 4) if r['quantita'] else None,
            "margine_pct": round((r['fatturato'] - r['costo']) / r['costo'] * 100, 1) if r['costo'] > 0 else None,
            "fatturato_atteso": round(r['fatturato'], 2),
            "clienti_attesi": len(r.get('clienti') or []),
            "fornitore": b['fornitore'] if b else None,
            "valore": round(da_ord * (b['prezzo'] if b else 0), 2),
        })
    prodotti_righe.sort(key=lambda x: -x['fatturato_atteso'])

    # ── Fornitori di questi prodotti: ruolo e previsione (ultimi 12 mesi) ──
    da_ord_map = {r['nome']: r['da_ordinare'] for r in prodotti_righe}
    dom_map = {r['nome']: r['domanda_prevista'] for r in prodotti_righe}
    qty_prodotto: Dict[str, float] = {}
    for r in forn:
        pnome = r['_id'].get('p')
        if pnome and r['qty'] > 0:
            qty_prodotto[pnome] = qty_prodotto.get(pnome, 0) + r['qty']

    forn_agg: Dict[str, Dict] = {}
    for r in forn:
        pnome, fnome = r['_id'].get('p'), r['_id'].get('f')
        if not pnome or not fnome or r['qty'] <= 0:
            continue
        f = forn_agg.setdefault(fnome, {"nome": fnome, "qty": 0.0, "spesa": 0.0,
                                        "prodotti": set(), "domanda": 0.0,
                                        "da_ordinare": 0.0, "valore": 0.0, "ultima": ""})
        quota = r['qty'] / qty_prodotto[pnome]
        f['qty'] += r['qty']
        f['spesa'] += r['spesa']
        f['prodotti'].add(pnome)
        f['domanda'] += dom_map.get(pnome, 0) * quota
        f['da_ordinare'] += da_ord_map.get(pnome, 0) * quota
        f['valore'] += da_ord_map.get(pnome, 0) * quota * (r['spesa'] / r['qty'])
        f['ultima'] = max(f['ultima'], r.get('ultima') or '')

    spesa_tot = sum(f['spesa'] for f in forn_agg.values()) or 1
    righe_fornitori = []
    for f in sorted(forn_agg.values(), key=lambda x: -x['spesa']):
        quota_pct = f['spesa'] / spesa_tot * 100
        righe_fornitori.append({
            "nome": f['nome'],
            "ruolo": "primario" if quota_pct >= 40 else ("secondario" if quota_pct >= 10 else "occasionale"),
            "quota_pct": round(quota_pct, 1),
            "quantita_acquistata": round(f['qty'], 1),
            "spesa": round(f['spesa'], 2),
            "prezzo_medio": round(f['spesa'] / f['qty'], 4) if f['qty'] else None,
            "prodotti_trattati": len(f['prodotti']),
            "domanda_prevista": round(f['domanda'], 1),
            "da_ordinare": round(f['da_ordinare'], 1),
            "valore_ordine": round(f['valore'], 2),
            "ultimo_acquisto": f['ultima'] or None,
        })

    return {
        "tipo": "prodotto", "nomi": nomi, "periodo": per,
        "righe_fornitori": righe_fornitori[:100],
        "kpi": {
            "quantita_attesa": round(qty, 1),
            "fatturato_atteso": round(fatt, 2),
            "margine_atteso": round(fatt - costo, 2) if costo else None,
            "margine_pct": round((fatt - costo) / costo * 100, 1) if costo > 0 else None,
            "clienti_attesi": len(per_cliente),
            "giacenza": round(sum(giacenze.get(n, 0) or 0 for n in nomi), 1),
            "da_ordinare": round(da_ordinare_tot, 1),
            "valore_ordine": round(valore_ordine, 2),
            "prodotti": len(nomi),
        },
        "righe": [{
            "nome": r['_id'],
            "quantita_attesa": round(r['quantita'], 1),
            "fatturato_atteso": round(r['fatturato'], 2),
            "prezzo_medio": round(r['fatturato'] / r['quantita'], 4) if r['quantita'] else None,
            "margine_pct": round((r['fatturato'] - r['costo']) / r['costo'] * 100, 1) if r['costo'] > 0 else None,
            "referenze": len(r.get('prodotti') or []),
            "gia_ordinato": round(gia.get(r['_id'], 0), 1),
            "ultimo_acquisto": r['ultimo'],
        } for r in per_cliente[:200]],
        "righe_prodotti": prodotti_righe[:200],
    }


async def _prev_clienti(nomi: List[str], giorni: int) -> Dict:
    per = _finestra_previsione(giorni)
    esclusi = await esclusi_filter()
    base = {**esclusi, "cliente_nome": {"$in": nomi}}

    storico = await db.vendite.aggregate([
        {"$match": {**base, "data": {"$gte": per['storico_start'], "$lte": per['storico_end']}}},
        {"$group": {"_id": "$prodotto_nome", "quantita": {"$sum": {"$abs": "$quantita"}},
                    "fatturato": {"$sum": {"$abs": "$totale"}},
                    "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}}}},
        {"$sort": {"fatturato": -1}},
    ]).to_list(5000)

    recenti = await db.vendite.aggregate([
        {"$match": {"cliente_nome": {"$in": nomi},
                    "data": {"$gte": per['recenti_start'], "$lte": per['recenti_end']}}},
        {"$group": {"_id": "$prodotto_nome", "quantita": {"$sum": {"$abs": "$quantita"}}}},
    ]).to_list(5000)
    gia = {r['_id']: r['quantita'] for r in recenti}

    ultimi = await db.vendite.aggregate([
        {"$match": {"cliente_nome": {"$in": nomi}}},
        {"$group": {"_id": None, "ultimo": {"$max": "$data"}}},
    ]).to_list(1)
    ultimo_data = ultimi[0]['ultimo'] if ultimi else None
    gg = (datetime.now() - datetime.strptime(ultimo_data, "%Y-%m-%d")).days if ultimo_data else None

    fatt = sum(r['fatturato'] for r in storico)
    costo = sum(r['costo'] for r in storico)
    righe = [{
        "nome": r['_id'],
        "quantita_attesa": round(r['quantita'], 1),
        "fatturato_atteso": round(r['fatturato'], 2),
        "prezzo_medio": round(r['fatturato'] / r['quantita'], 4) if r['quantita'] else None,
        "margine_pct": round((r['fatturato'] - r['costo']) / r['costo'] * 100, 1) if r['costo'] > 0 else None,
        "gia_ordinato": round(gia.get(r['_id'], 0), 1),
    } for r in storico]
    mancanti = [r for r in righe if not r['gia_ordinato']]

    return {
        "tipo": "cliente", "nomi": nomi, "periodo": per,
        "kpi": {
            "fatturato_atteso": round(fatt, 2),
            "margine_atteso": round(fatt - costo, 2) if costo else None,
            "margine_pct": round((fatt - costo) / costo * 100, 1) if costo > 0 else None,
            "referenze": len(righe),
            "referenze_da_proporre": len(mancanti),
            "valore_da_proporre": round(sum(r['fatturato_atteso'] for r in mancanti), 2),
            "ultimo_ordine": ultimo_data,
            "giorni_da_ultimo_ordine": gg,
            "clienti": len(nomi),
        },
        "righe": righe[:200],
    }


async def _prev_fornitori(nomi: List[str], giorni: int) -> Dict:
    per = _finestra_previsione(giorni)
    esclusi = await esclusi_filter()
    anno_start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    forniti = await db.ordini.aggregate([
        {"$match": {"fornitore_nome": {"$in": nomi}, "data": {"$gte": anno_start, "$lte": per['recenti_end']},
                    "quantita": {"$gt": 0}, "totale": {"$gt": 0}}},
        {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": "$quantita"},
                    "spesa": {"$sum": "$totale"}, "ultima": {"$max": "$data"},
                    "fornitori": {"$addToSet": "$fornitore_nome"}}},
    ]).to_list(20000)
    prezzi = {r['_id']: {"prezzo": r['spesa'] / r['qty'], "spesa": r['spesa'], "ultima": r['ultima'],
                         "fornitore": (r.get('fornitori') or [None])[0]}
              for r in forniti if r['_id'] and r['qty'] > 0}
    if not prezzi:
        return {"tipo": "fornitore", "nomi": nomi, "periodo": per,
                "kpi": {"valore_ordine": 0, "articoli_da_ordinare": 0, "articoli_trattati": 0,
                        "margine_previsto": None, "margine_pct": None, "fatturato_atteso": 0,
                        "spesa_ultimo_anno": 0, "fornitori": len(nomi)},
                "righe": []}

    domanda = await db.vendite.aggregate([
        {"$match": {**esclusi, "prodotto_nome": {"$in": list(prezzi.keys())},
                    "cliente_nome": {"$nin": EXCLUDED_CLIENTS},
                    "data": {"$gte": per['storico_start'], "$lte": per['storico_end']}}},
        {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": {"$abs": "$quantita"}},
                    "fatt": {"$sum": {"$abs": "$totale"}},
                    "clienti": {"$addToSet": "$cliente_nome"}}},
    ]).to_list(20000)
    dom = {r['_id']: r for r in domanda}

    giacenze = {d['nome']: (d.get('quantita', 0) or 0) for d in
                await db.prodotti.find({"nome": {"$in": list(prezzi.keys())}},
                                       {"_id": 0, "nome": 1, "quantita": 1}).to_list(20000)}

    righe = []
    for nome, pr in prezzi.items():
        d = dom.get(nome) or {}
        q_dom = d.get('qty', 0) or 0
        giac = giacenze.get(nome, 0) or 0
        da_ord = max(q_dom - giac, 0)
        pv = (d.get('fatt', 0) / q_dom) if q_dom else None
        costo = pr['prezzo']
        righe.append({
            "nome": nome,
            "fornitore": pr['fornitore'],
            "domanda_prevista": round(q_dom, 1),
            "giacenza": round(giac, 1),
            "copertura_giorni": round(giac / (q_dom / per['giorni'])) if q_dom > 0 else None,
            "da_ordinare": round(da_ord, 1),
            "prezzo_acquisto": round(costo, 4),
            "prezzo_vendita_atteso": round(pv, 4) if pv else None,
            "margine_pct": round((pv - costo) / costo * 100, 1) if (pv and costo) else None,
            "valore": round(costo * da_ord, 2),
            "fatturato_atteso": round(d.get('fatt', 0), 2),
            "clienti_attesi": len(d.get('clienti') or []),
            "ultimo_acquisto": pr['ultima'],
        })
    righe.sort(key=lambda r: -r['da_ordinare'])

    da_ordinare = [r for r in righe if r['da_ordinare'] > 0]
    valore = sum(r['valore'] for r in da_ordinare)
    margine = sum(((r['prezzo_vendita_atteso'] or 0) - r['prezzo_acquisto']) * r['da_ordinare']
                  for r in da_ordinare if r['prezzo_vendita_atteso'])
    return {
        "tipo": "fornitore", "nomi": nomi, "periodo": per,
        "kpi": {
            "valore_ordine": round(valore, 2),
            "articoli_da_ordinare": len(da_ordinare),
            "articoli_trattati": len(righe),
            "margine_previsto": round(margine, 2),
            "margine_pct": round(margine / valore * 100, 1) if valore else None,
            "fatturato_atteso": round(sum(r['fatturato_atteso'] for r in righe), 2),
            "spesa_ultimo_anno": round(sum(p['spesa'] for p in prezzi.values()), 2),
            "fornitori": len(nomi),
        },
        "righe": righe[:200],
    }


async def _previsione_dati(tipo: str, nomi: List[str], giorni: int) -> Dict:
    tipo = (tipo or 'prodotto').lower()
    nomi = [n for n in (nomi or []) if n]
    if not nomi:
        raise HTTPException(status_code=400, detail="Indica almeno un nome")
    if tipo == 'prodotto':
        return await _prev_prodotti(nomi, giorni)
    if tipo == 'cliente':
        return await _prev_clienti(nomi, giorni)
    if tipo == 'fornitore':
        return await _prev_fornitori(nomi, giorni)
    raise HTTPException(status_code=400, detail="tipo non valido")


@router.get("/analisi/previsione")
async def previsione(tipo: str = "prodotto", nomi: List[str] = Query(default=[]),
                     nome: Optional[str] = None, giorni: int = 30):
    """Previsione dei prossimi N giorni per uno o piu' prodotti, clienti o fornitori,
    basata sullo stesso intervallo dell'anno precedente."""
    lista = list(nomi) or ([nome] if nome else [])
    return await _previsione_dati(tipo, lista, giorni)


@router.get("/analisi/previsione/pdf")
async def previsione_pdf(tipo: str = "prodotto", nomi: List[str] = Query(default=[]),
                         nome: Optional[str] = None, giorni: int = 30, vista: str = "entrambi"):
    """Esporta in PDF la previsione (nessun grafico: KPI, sintesi e tabelle)."""
    from fastapi.responses import Response
    from routes.pdf_helper import (C_AMBER, C_BLUE, C_EMERALD, C_SLATE, C_VIOLET,
                                   FlowPDF, clean_text, eur, it_num)

    lista = list(nomi) or ([nome] if nome else [])
    d = await _previsione_dati(tipo, lista, giorni)
    per, k = d['periodo'], d['kpi']
    dm = lambda x: x[8:10] + '/' + x[5:7] + '/' + x[2:4]  # noqa: E731
    etichetta = {"prodotto": "PRODOTTI", "cliente": "CLIENTI", "fornitore": "FORNITORI"}[d['tipo']]
    titolo = f"PREVISIONE {etichetta}"
    sottotitolo = (f"Prossimi {per['giorni']} giorni: {dm(per['futuro_start'])} - {dm(per['futuro_end'])}  |  "
                   f"Base: {dm(per['storico_start'])} - {dm(per['storico_end'])} (anno precedente)")

    pdf = FlowPDF(titolo, sottotitolo)
    pdf.add_page()

    if d['tipo'] == 'prodotto':
        pdf.kpi_row([
            ("QUANTITA ATTESA", f"{it_num(k['quantita_attesa'], 0)} pz", C_BLUE, f"{k['prodotti']} prodotti"),
            ("FATTURATO ATTESO", eur(k['fatturato_atteso']), C_EMERALD, f"{k['clienti_attesi']} clienti"),
            ("MARGINE PREVISTO", eur(k['margine_atteso']) if k['margine_atteso'] is not None else '-',
             C_VIOLET, f"{k['margine_pct']}% sul costo" if k['margine_pct'] is not None else None),
            ("DA ORDINARE", f"{it_num(k['da_ordinare'], 0)} pz", C_AMBER, eur(k['valore_ordine'])),
        ])
    elif d['tipo'] == 'cliente':
        pdf.kpi_row([
            ("FATTURATO ATTESO", eur(k['fatturato_atteso']), C_BLUE, f"{k['clienti']} clienti"),
            ("MARGINE PREVISTO", eur(k['margine_atteso']) if k['margine_atteso'] is not None else '-',
             C_VIOLET, f"{k['margine_pct']}% sul costo" if k['margine_pct'] is not None else None),
            ("REFERENZE ATTESE", f"{k['referenze']}", C_EMERALD, f"{k['referenze_da_proporre']} da proporre"),
            ("VALORE DA PROPORRE", eur(k['valore_da_proporre']), C_AMBER,
             f"ultimo ordine {dm(k['ultimo_ordine'])}" if k.get('ultimo_ordine') else None),
        ])
    else:
        pdf.kpi_row([
            ("VALORE ORDINE", eur(k['valore_ordine']), C_BLUE,
             f"{k['articoli_da_ordinare']} di {k['articoli_trattati']} articoli"),
            ("MARGINE PREVISTO", eur(k['margine_previsto']) if k['margine_previsto'] is not None else '-',
             C_VIOLET, f"{k['margine_pct']}% sul costo" if k.get('margine_pct') is not None else None),
            ("FATTURATO ATTESO", eur(k['fatturato_atteso']), C_EMERALD, f"{k['fornitori']} fornitori"),
            ("SPESA ULTIMI 12 MESI", eur(k['spesa_ultimo_anno']), C_AMBER, None),
        ])

    pdf.section_title("Selezione", C_SLATE, top_gap=2)
    pdf.lead_text(", ".join(d['nomi'])[:900])

    if d['tipo'] == 'fornitore':
        da_ord = [r for r in d['righe'] if r['da_ordinare'] > 0][:30]
        pdf.section_title(f"Ordine consigliato ({len(da_ord)} articoli)", C_BLUE)
        pdf.smart_table(['Articolo', 'Domanda prev.', 'Giacenza', 'Da ordinare', 'Prz. acq.',
                         'Prz. vendita', 'Marg. %', 'Valore'],
                        [58, 22, 18, 20, 20, 22, 16, 24],
                        [[clean_text(r['nome'])[:44], it_num(r['domanda_prevista'], 0), it_num(r['giacenza'], 0),
                          it_num(r['da_ordinare'], 0), eur(r['prezzo_acquisto']),
                          eur(r['prezzo_vendita_atteso']) if r['prezzo_vendita_atteso'] else '-',
                          f"{r['margine_pct']}%" if r['margine_pct'] is not None else '-',
                          eur(r['valore'])] for r in da_ord],
                        aligns=['L', 'R', 'R', 'R', 'R', 'R', 'R', 'R'])
    elif d['tipo'] == 'cliente':
        top = d['righe'][:30]
        resto = d['righe'][30:]
        pdf.section_title(f"Cosa proporre ({len(d['righe'])} referenze)", C_BLUE)
        pdf.smart_table(['Articolo', 'Qta attesa', 'Prezzo medio', 'Fatturato', 'Marg. %', 'Stato'],
                        [72, 22, 26, 28, 18, 24],
                        [[clean_text(r['nome'])[:50], it_num(r['quantita_attesa'], 0),
                          eur(r['prezzo_medio']) if r['prezzo_medio'] else '-',
                          eur(r['fatturato_atteso']),
                          f"{r['margine_pct']}%" if r['margine_pct'] is not None else '-',
                          f"{it_num(r['gia_ordinato'], 0)} pz" if r['gia_ordinato'] else 'da proporre']
                         for r in top],
                        aligns=['L', 'R', 'R', 'R', 'R', 'R'])
        if resto:
            pdf.note_text(f"Altre {len(resto)} referenze minori per "
                          f"{eur(sum(r['fatturato_atteso'] for r in resto))} attesi.")
    else:
        mostra_clienti = vista in ('entrambi', 'clienti')
        mostra_fornitori = vista in ('entrambi', 'fornitori')
        if mostra_clienti:
            top = d['righe'][:25]
            resto = d['righe'][25:]
            pdf.section_title(f"Clienti che compreranno ({len(d['righe'])})", C_BLUE)
            pdf.smart_table(['Cliente', 'Qta attesa', 'Prezzo medio', 'Fatturato', 'Marg. %', 'Gia ordinato', 'Ultimo acq.'],
                        [62, 20, 24, 26, 16, 22, 20],
                        [[clean_text(r['nome'])[:44], it_num(r['quantita_attesa'], 0),
                          eur(r['prezzo_medio']) if r['prezzo_medio'] else '-',
                          eur(r['fatturato_atteso']),
                          f"{r['margine_pct']}%" if r['margine_pct'] is not None else '-',
                          f"{it_num(r['gia_ordinato'], 0)} pz" if r['gia_ordinato'] else '-',
                          dm(r['ultimo_acquisto']) if r.get('ultimo_acquisto') else '-']
                             for r in top],
                            aligns=['L', 'R', 'R', 'R', 'R', 'R', 'R'])
            if resto:
                pdf.note_text(f"Altri {len(resto)} clienti per {eur(sum(r['fatturato_atteso'] for r in resto))} "
                              f"e {it_num(sum(r['quantita_attesa'] for r in resto), 0)} pezzi attesi.")
        if mostra_fornitori and d.get('righe_fornitori'):
            pdf.section_title("Previsione per fornitore", C_EMERALD)
            pdf.smart_table(['Fornitore', 'Ruolo', 'Articoli', 'Prz. medio',
                             'Domanda prev.', 'Da ordinare', 'Valore'],
                            [60, 24, 18, 24, 26, 24, 24],
                            [[clean_text(r['nome'])[:38], r['ruolo'],
                              f"{r['prodotti_trattati']}",
                              eur(r['prezzo_medio']) if r['prezzo_medio'] else '-',
                              it_num(r['domanda_prevista'], 0),
                              it_num(r['da_ordinare'], 0) if r['da_ordinare'] else '-',
                              eur(r['valore_ordine']) if r['valore_ordine'] else '-']
                             for r in d['righe_fornitori'][:15]],
                            aligns=['L', 'L', 'R', 'R', 'R', 'R', 'R'])
        if d.get('righe_prodotti'):
            pdf.section_title("Riepilogo per prodotto", C_AMBER)
            pdf.smart_table(['Prodotto', 'Domanda prev.', 'Giacenza', 'Da ordinare', 'Prz. acq.',
                             'Marg. %', 'Fatturato', 'Fornitore'],
                            [52, 22, 18, 20, 20, 16, 24, 28],
                            [[clean_text(r['nome'])[:40], it_num(r['domanda_prevista'], 0),
                              it_num(r['giacenza'], 0), it_num(r['da_ordinare'], 0),
                              eur(r['prezzo_acquisto']) if r['prezzo_acquisto'] else '-',
                              f"{r['margine_pct']}%" if r['margine_pct'] is not None else '-',
                              eur(r['fatturato_atteso']),
                              clean_text(r['fornitore'] or '-')[:22]] for r in d['righe_prodotti'][:30]],
                            aligns=['L', 'R', 'R', 'R', 'R', 'R', 'R', 'L'])

    pdf.note_text("Le quantita' e i valori attesi sono il venduto reale dello stesso intervallo dell'anno "
                  "precedente. Margini calcolati sul costo reale dei lotti (FIFO).")

    from routes.ai_insight import blocco_considerazioni_ai
    ctx_righe = "; ".join(
        f"{r['nome']} qta {r.get('quantita_attesa') or r.get('da_ordinare')} "
        f"val € {r.get('fatturato_atteso') or r.get('valore')} marg {r.get('margine_pct')}%"
        for r in d['righe'][:12])
    ctx = (f"Previsione {d['tipo']} per i prossimi {per['giorni']} giorni "
           f"({per['futuro_start']} - {per['futuro_end']}), basata sullo stesso intervallo dell'anno precedente.\n"
           f"Selezione: {', '.join(d['nomi'])[:300]}\nKPI: {k}\nRighe principali: {ctx_righe}")
    if d.get('righe_fornitori'):
        ctx += ("\nFornitori: " + "; ".join(
            f"{f['nome']} ruolo {f['ruolo']} prz € {f['prezzo_medio']} da ordinare {f['da_ordinare']}"
            for f in d['righe_fornitori'][:8]))
    await blocco_considerazioni_ai(pdf, ctx, f"previsione-{d['tipo']}-{per['futuro_start']}-{per['giorni']}")

    out = pdf.output(dest='S')
    fname = f"previsione_{d['tipo']}_{per['futuro_start']}_{per['futuro_end']}.pdf"
    return Response(bytes(out), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})
