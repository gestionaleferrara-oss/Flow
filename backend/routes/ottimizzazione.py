"""Ottimizzazione acquisti e vendite: opportunita' quantificate in euro."""
import logging
from datetime import datetime
from statistics import median
from typing import Dict, List, Optional

from fastapi import APIRouter

from database import db
from routes.analisi import EXCLUDED_CLIENTS, esclusi_filter, resolve_period
from routes.pdf_sections import periodi_anno_su_anno

router = APIRouter()
logger = logging.getLogger(__name__)

MARGINE_TARGET = 15.0


def _giorni(start: str, end: str) -> int:
    d = (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days + 1
    return max(d, 1)


# ═══════════════════════ ACQUISTI ═══════════════════════

@router.get("/ottimizzazione/acquisti")
async def ottimizzazione_acquisti(
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    giorni_copertura: int = 30, fornitore: Optional[str] = None, prodotto: Optional[str] = None,
    limit: int = 25
):
    start, end, _, _ = await resolve_period(start_date, end_date)
    (ly_start, ly_end), _ = periodi_anno_su_anno(start, end)
    giorni_periodo = _giorni(start, end)

    base = {"data": {"$gte": start, "$lte": end}}
    if fornitore:
        base["fornitore_nome"] = {"$regex": fornitore, "$options": "i"}
    if prodotto:
        base["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}

    righe = await db.ordini.find(
        {**base, "quantita": {"$gt": 0}, "totale": {"$gt": 0}},
        {"_id": 0, "data": 1, "fornitore_nome": 1, "prodotto_nome": 1, "quantita": 1, "totale": 1}
    ).to_list(200000)

    # ── 1. Cambio fornitore ──
    per_prod: Dict[str, Dict[str, Dict]] = {}
    for r in righe:
        p = per_prod.setdefault(r['prodotto_nome'], {})
        f = p.setdefault(r['fornitore_nome'], {"qty": 0.0, "spesa": 0.0, "righe": 0})
        f['qty'] += r['quantita']; f['spesa'] += r['totale']; f['righe'] += 1

    cambio_fornitore = []
    for nome, forns in per_prod.items():
        if len(forns) < 2:
            continue
        prezzi = {f: d['spesa'] / d['qty'] for f, d in forns.items() if d['qty'] > 0}
        if not prezzi:
            continue
        migliore = min(prezzi, key=prezzi.get)
        p_best = prezzi[migliore]
        risparmio = sum((prezzi[f] - p_best) * d['qty'] for f, d in forns.items() if d['qty'] > 0)
        if risparmio <= 1:
            continue
        qty_tot = sum(d['qty'] for d in forns.values())
        spesa_tot = sum(d['spesa'] for d in forns.values())
        cambio_fornitore.append({
            "prodotto": nome, "fornitori": len(forns),
            "migliore": migliore, "prezzo_migliore": round(p_best, 4),
            "peggiore": max(prezzi, key=prezzi.get), "prezzo_peggiore": round(max(prezzi.values()), 4),
            "prezzo_medio": round(spesa_tot / qty_tot, 4) if qty_tot else 0,
            "quantita": round(qty_tot, 2), "spesa": round(spesa_tot, 2),
            "risparmio": round(risparmio, 2),
            "dettaglio": [{"fornitore": f, "prezzo": round(prezzi[f], 4), "quantita": round(d['qty'], 2)}
                          for f, d in sorted(forns.items(), key=lambda x: prezzi.get(x[0], 0))],
        })
    cambio_fornitore.sort(key=lambda x: -x['risparmio'])

    # ── 2. Sconto quantita' (prezzo per taglia d'ordine) ──
    sconto_quantita = []
    righe_per_prod: Dict[str, List] = {}
    for r in righe:
        righe_per_prod.setdefault(r['prodotto_nome'], []).append(r)
    for nome, rows in righe_per_prod.items():
        if len(rows) < 4:
            continue
        qty_list = [r['quantita'] for r in rows]
        med = median(qty_list)
        piccoli = [r for r in rows if r['quantita'] <= med]
        grandi = [r for r in rows if r['quantita'] > med]
        if not piccoli or not grandi:
            continue
        qp = sum(r['quantita'] for r in piccoli); sp = sum(r['totale'] for r in piccoli)
        qg = sum(r['quantita'] for r in grandi); sg = sum(r['totale'] for r in grandi)
        if qp <= 0 or qg <= 0:
            continue
        p_piccoli, p_grandi = sp / qp, sg / qg
        if p_grandi >= p_piccoli:
            continue
        qty_tot = qp + qg
        prezzo_attuale = (sp + sg) / qty_tot
        risparmio = (prezzo_attuale - p_grandi) * qty_tot
        if risparmio <= 1:
            continue
        sconto_quantita.append({
            "prodotto": nome,
            "qta_media_piccoli": round(sum(r['quantita'] for r in piccoli) / len(piccoli), 1),
            "prezzo_ordini_piccoli": round(p_piccoli, 4),
            "qta_media_grandi": round(sum(r['quantita'] for r in grandi) / len(grandi), 1),
            "prezzo_ordini_grandi": round(p_grandi, 4),
            "sconto_pct": round((p_piccoli - p_grandi) / p_piccoli * 100, 1),
            "prezzo_attuale": round(prezzo_attuale, 4),
            "quantita": round(qty_tot, 2), "ordini": len(rows),
            "risparmio": round(risparmio, 2),
        })
    sconto_quantita.sort(key=lambda x: -x['risparmio'])

    # ── 3. Prezzi in aumento vs stesso periodo anno precedente ──
    ly_rows = await db.ordini.aggregate([
        {"$match": {**{k: v for k, v in base.items() if k != 'data'},
                    "data": {"$gte": ly_start, "$lte": ly_end},
                    "quantita": {"$gt": 0}, "totale": {"$gt": 0}}},
        {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": "$quantita"}, "tot": {"$sum": "$totale"}}},
    ]).to_list(20000)
    prezzi_ly = {r['_id']: r['tot'] / r['qty'] for r in ly_rows if r['_id'] and r['qty'] > 0}

    prezzi_aumento = []
    for nome, forns in per_prod.items():
        qty = sum(d['qty'] for d in forns.values())
        spesa = sum(d['spesa'] for d in forns.values())
        if qty <= 0:
            continue
        ora = spesa / qty
        prima = prezzi_ly.get(nome)
        if not prima or prima <= 0 or ora <= prima:
            continue
        var = (ora - prima) / prima * 100
        if var < 3:
            continue
        prezzi_aumento.append({
            "prodotto": nome, "prezzo_anno_prec": round(prima, 4), "prezzo_attuale": round(ora, 4),
            "var_pct": round(var, 1), "quantita": round(qty, 2),
            "impatto": round((ora - prima) * qty, 2),
            "fornitori": ", ".join(sorted(forns.keys()))[:60],
        })
    prezzi_aumento.sort(key=lambda x: -x['impatto'])

    # ── 4. Rotazione, domanda prevista e ordine ottimale (previsione forward) ──
    # finestra futura: i giorni di copertura dopo il periodo selezionato,
    # stimati sui dati dell'anno precedente nella stessa finestra
    from datetime import timedelta
    e_dt = datetime.strptime(end, "%Y-%m-%d")
    fut_start = (e_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    fut_end = (e_dt + timedelta(days=giorni_copertura)).strftime("%Y-%m-%d")
    (ly_fut_start, ly_fut_end), _ = periodi_anno_su_anno(fut_start, fut_end)

    async def vendite_qty(s, e):
        rows = await db.vendite.aggregate([
            {"$match": {"data": {"$gte": s, "$lte": e}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
            {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": {"$abs": "$quantita"}}}},
        ]).to_list(20000)
        return {r['_id']: r['qty'] for r in rows if r['_id']}

    qty_ly_fut = await vendite_qty(ly_fut_start, ly_fut_end)
    qty_ly_per = await vendite_qty(ly_start, ly_end)

    giacenze = {p['nome']: p.get('quantita', 0) or 0 for p in
                await db.prodotti.find({}, {"_id": 0, "nome": 1, "quantita": 1}).to_list(20000)}

    lotti = await db.lotti.find(
        {"data_acquisto": {"$gte": ly_start, "$lte": end},
         **({"fornitore": {"$regex": fornitore, "$options": "i"}} if fornitore else {}),
         **({"prodotto": {"$regex": prodotto, "$options": "i"}} if prodotto else {})},
        {"_id": 0}).to_list(50000)

    vend_rows = await db.vendite.aggregate([
        {"$match": {"data": {"$gte": start, "$lte": end}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
        {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": {"$abs": "$quantita"}},
                    "fatt": {"$sum": {"$abs": "$totale"}},
                    "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}}}},
    ]).to_list(20000)
    vend_map = {v['_id']: v for v in vend_rows if v['_id']}

    rot: Dict[str, Dict] = {}
    for lot in lotti:
        nome = lot.get('prodotto')
        if not nome:
            continue
        d = rot.setdefault(nome, {"giorni": [], "residuo_val": 0.0, "lotti": 0, "qta_ordine": []})
        d['lotti'] += 1
        d['qta_ordine'].append(lot.get('quantita', 0) or 0)
        d['residuo_val'] += (lot.get('residuo', 0) or 0) * (lot.get('prezzo_acquisto', 0) or 0)
        if lot.get('data_esaurimento'):
            try:
                g = (datetime.strptime(lot['data_esaurimento'], "%Y-%m-%d")
                     - datetime.strptime(lot['data_acquisto'], "%Y-%m-%d")).days
                if g >= 0:
                    d['giorni'].append(g)
            except Exception:
                pass

    rotazione = []
    for nome, d in rot.items():
        v = vend_map.get(nome, {})
        qty_ora = v.get('qty', 0) or 0
        consumo = qty_ora / giorni_periodo
        # previsione domanda nei giorni di copertura: anno scorso nella finestra successiva,
        # corretta dal trend YoY del periodo selezionato
        base_ly = qty_ly_fut.get(nome, 0)
        prev_periodo_ly = qty_ly_per.get(nome, 0)
        fattore = (qty_ora / prev_periodo_ly) if prev_periodo_ly > 0 else None
        if fattore is not None:
            fattore = max(0.5, min(fattore, 2.0))
        domanda_prevista = base_ly * (fattore if fattore is not None else 1)
        if base_ly <= 0:
            domanda_prevista = consumo * giorni_copertura
        giacenza = giacenze.get(nome, 0)
        da_ordinare = max(domanda_prevista - giacenza, 0)
        qta_media = sum(d['qta_ordine']) / len(d['qta_ordine']) if d['qta_ordine'] else 0
        giorni_medi = (sum(d['giorni']) / len(d['giorni'])) if d['giorni'] else None
        eccesso = qta_media - domanda_prevista
        prezzo = (v['costo'] / v['qty']) if (v.get('qty') and v.get('costo')) else None
        capitale = d['residuo_val']
        rotazione.append({
            "prodotto": nome, "lotti": d['lotti'],
            "giorni_smaltimento": round(giorni_medi, 0) if giorni_medi is not None else None,
            "consumo_giornaliero": round(consumo, 2),
            "domanda_prevista": round(domanda_prevista, 1),
            "base_anno_prec": round(base_ly, 1),
            "trend_yoy_pct": round((fattore - 1) * 100, 0) if fattore is not None else None,
            "giacenza": round(giacenza, 1),
            "da_ordinare": round(da_ordinare, 1),
            "copertura_giorni": round(giacenza / (domanda_prevista / giorni_copertura), 0)
            if domanda_prevista > 0 else None,
            "qta_media_ordine": round(qta_media, 1),
            "ordine_consigliato": round(da_ordinare, 1),
            "eccesso_pct": round(eccesso / domanda_prevista * 100, 0) if domanda_prevista > 0 else None,
            "capitale_immobilizzato": round(capitale, 2),
            "impatto": round(max(eccesso, 0) * (prezzo or 0), 2) if prezzo else round(capitale, 2),
        })
    rotazione = [r for r in rotazione
                 if (r['capitale_immobilizzato'] > 0 or r['da_ordinare'] > 0 or (r['eccesso_pct'] or 0) > 20)]
    rotazione.sort(key=lambda x: -(x['impatto'] or 0))

    # previsione della domanda nei giorni di copertura, per prodotto
    def domanda_futura(nome: str) -> float:
        base = qty_ly_fut.get(nome, 0)
        ora = (vend_map.get(nome, {}) or {}).get('qty', 0) or 0
        prima = qty_ly_per.get(nome, 0)
        if base > 0:
            f = max(0.5, min(ora / prima, 2.0)) if prima > 0 else 1
            return base * f
        return ora / giorni_periodo * giorni_copertura

    for r in cambio_fornitore:
        q_fut = domanda_futura(r['prodotto'])
        r['quantita_prevista'] = round(q_fut, 1)
        r['risparmio_previsto'] = round((r['prezzo_medio'] - r['prezzo_migliore']) * q_fut, 2)
    for r in prezzi_aumento:
        q_fut = domanda_futura(r['prodotto'])
        r['quantita_prevista'] = round(q_fut, 1)
        r['impatto_previsto'] = round((r['prezzo_attuale'] - r['prezzo_anno_prec']) * q_fut, 2)

    # ── 5. Consolidamento fornitore ──
    catalogo = await db.ordini.aggregate([
        {"$group": {"_id": {"f": "$fornitore_nome", "p": "$prodotto_nome"}}},
    ]).to_list(200000)
    cat_map: Dict[str, set] = {}
    for c in catalogo:
        f = c['_id'].get('f'); p = c['_id'].get('p')
        if f and p:
            cat_map.setdefault(f, set()).add(p)

    spesa_forn: Dict[str, float] = {}
    spesa_prod_forn: Dict[str, Dict[str, float]] = {}
    for r in righe:
        spesa_forn[r['fornitore_nome']] = spesa_forn.get(r['fornitore_nome'], 0) + r['totale']
        spesa_prod_forn.setdefault(r['prodotto_nome'], {})
        spesa_prod_forn[r['prodotto_nome']][r['fornitore_nome']] = \
            spesa_prod_forn[r['prodotto_nome']].get(r['fornitore_nome'], 0) + r['totale']

    consolidamento = []
    for f, spesa in sorted(spesa_forn.items(), key=lambda x: -x[1])[:20]:
        cat = cat_map.get(f, set())
        spostabile = 0.0
        prodotti_spostabili = []
        for p, per_f in spesa_prod_forn.items():
            if p in cat and f not in per_f:
                val = sum(per_f.values())
                spostabile += val
                prodotti_spostabili.append({"prodotto": p, "spesa_altrove": round(val, 2),
                                            "fornitori_attuali": ", ".join(per_f.keys())[:50]})
        if spostabile <= 0:
            continue
        prodotti_spostabili.sort(key=lambda x: -x['spesa_altrove'])
        consolidamento.append({
            "fornitore": f, "spesa_attuale": round(spesa, 2),
            "spesa_spostabile": round(spostabile, 2),
            "nuovo_volume": round(spesa + spostabile, 2),
            "crescita_pct": round(spostabile / spesa * 100, 0) if spesa else None,
            "prodotti": prodotti_spostabili[:8],
            "impatto": round(spostabile * 0.03, 2),
        })
    consolidamento.sort(key=lambda x: -x['spesa_spostabile'])

    # ── 6. Acquisti a margine basso/negativo ──
    margine_basso = []
    for nome, v in vend_map.items():
        costo = v.get('costo', 0) or 0
        fatt = v.get('fatt', 0) or 0
        qty = v.get('qty', 0) or 0
        if costo <= 0 or qty <= 0 or fatt < 100:
            continue
        marg = (fatt - costo) / costo * 100
        if marg >= 8:
            continue
        prezzo_v = fatt / qty
        costo_u = costo / qty
        costo_target = prezzo_v / (1 + MARGINE_TARGET / 100)
        margine_basso.append({
            "prodotto": nome, "quantita": round(qty, 2), "fatturato": round(fatt, 2),
            "prezzo_vendita": round(prezzo_v, 4), "costo_attuale": round(costo_u, 4),
            "margine_pct": round(marg, 1),
            "costo_target": round(costo_target, 4),
            "sconto_da_chiedere_pct": round((costo_u - costo_target) / costo_u * 100, 1) if costo_u else None,
            "impatto": round((costo_u - costo_target) * qty, 2),
        })
    margine_basso.sort(key=lambda x: -x['impatto'])

    moduli = {
        "cambio_fornitore": cambio_fornitore[:limit],
        "sconto_quantita": sconto_quantita[:limit],
        "prezzi_aumento": prezzi_aumento[:limit],
        "rotazione": rotazione[:limit],
        "consolidamento": consolidamento[:limit],
        "margine_basso": margine_basso[:limit],
    }
    tot = {k: round(sum(r.get('risparmio', r.get('impatto', 0)) or 0 for r in v), 2) for k, v in moduli.items()}
    return {
        "periodo": {"start": start, "end": end, "ly_start": ly_start, "ly_end": ly_end,
                    "giorni": giorni_periodo, "giorni_copertura": giorni_copertura,
                    "futuro_start": fut_start, "futuro_end": fut_end,
                    "futuro_ly_start": ly_fut_start, "futuro_ly_end": ly_fut_end},
        "opportunita": tot,
        "opportunita_totale": round(sum(tot.values()), 2),
        "moduli": moduli,
    }


# ═══════════════════════ VENDITE ═══════════════════════

@router.get("/ottimizzazione/vendite")
async def ottimizzazione_vendite(
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    cliente: Optional[str] = None, prodotto: Optional[str] = None, limit: int = 25
):
    start, end, _, _ = await resolve_period(start_date, end_date)
    (ly_start, ly_end), _ = periodi_anno_su_anno(start, end)
    excl = await esclusi_filter()
    giorni_periodo = _giorni(start, end)

    base = {"cliente_nome": {"$nin": EXCLUDED_CLIENTS}, **excl}
    if cliente:
        base["cliente_nome"] = {"$regex": cliente, "$options": "i"}
    if prodotto:
        base["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}

    coppie = await db.vendite.aggregate([
        {"$match": {**base, "data": {"$gte": start, "$lte": end}}},
        {"$group": {"_id": {"p": "$prodotto_nome", "c": "$cliente_nome"},
                    "qty": {"$sum": {"$abs": "$quantita"}},
                    "fatt": {"$sum": {"$abs": "$totale"}},
                    "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                    "giorni": {"$addToSet": "$data"}}},
        {"$project": {"qty": 1, "fatt": 1, "costo": 1, "ordini": {"$size": "$giorni"}}},
    ]).to_list(200000)

    # ── 1. Clienti sotto prezzo ──
    prezzi_per_prod: Dict[str, List] = {}
    for c in coppie:
        if c['qty'] <= 0 or c['fatt'] <= 0:
            continue
        prezzi_per_prod.setdefault(c['_id']['p'], []).append({
            "cliente": c['_id']['c'], "prezzo": c['fatt'] / c['qty'], "qty": c['qty'],
            "fatt": c['fatt'], "costo": c.get('costo', 0) or 0, "ordini": c.get('ordini', 0),
        })

    sotto_prezzo = []
    for p, lista in prezzi_per_prod.items():
        if len(lista) < 3:
            continue
        med = median([x['prezzo'] for x in lista])
        for x in lista:
            if x['prezzo'] >= med * 0.98 or x['qty'] < 5:
                continue
            recupero = (med - x['prezzo']) * x['qty']
            if recupero < 5:
                continue
            marg = ((x['fatt'] - x['costo']) / x['costo'] * 100) if x['costo'] > 0 else None
            sotto_prezzo.append({
                "prodotto": p, "cliente": x['cliente'],
                "prezzo_cliente": round(x['prezzo'], 4), "prezzo_mediano": round(med, 4),
                "gap_pct": round((med - x['prezzo']) / med * 100, 1),
                "quantita": round(x['qty'], 2), "fatturato": round(x['fatt'], 2),
                "margine_pct": round(marg, 1) if marg is not None else None,
                "impatto": round(recupero, 2),
            })
    sotto_prezzo.sort(key=lambda x: -x['impatto'])

    # ── 2. Clienti in calo vs stesso periodo anno precedente ──
    async def per_cliente(s, e):
        rows = await db.vendite.aggregate([
            {"$match": {**base, "data": {"$gte": s, "$lte": e}}},
            {"$group": {"_id": "$cliente_nome", "fatt": {"$sum": {"$abs": "$totale"}},
                        "qty": {"$sum": {"$abs": "$quantita"}},
                        "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                        "prodotti": {"$addToSet": "$prodotto_nome"}}},
        ]).to_list(20000)
        return {r['_id']: r for r in rows if r['_id']}

    ora_cli = await per_cliente(start, end)
    ly_cli = await per_cliente(ly_start, ly_end)

    async def prodotti_persi(nome, limite=5):
        rows = await db.vendite.aggregate([
            {"$match": {**base, "cliente_nome": nome, "data": {"$gte": ly_start, "$lte": ly_end}}},
            {"$group": {"_id": "$prodotto_nome", "fatt": {"$sum": {"$abs": "$totale"}}}},
            {"$sort": {"fatt": -1}},
        ]).to_list(2000)
        attuali = set(ora_cli.get(nome, {}).get('prodotti', []))
        return [{"prodotto": r['_id'], "fatturato_perso": round(r['fatt'], 2)}
                for r in rows if r['_id'] and r['_id'] not in attuali][:limite]

    clienti_calo = []
    for nome, prima in sorted(ly_cli.items(), key=lambda x: -x[1]['fatt']):
        ora = ora_cli.get(nome, {})
        f_prima, f_ora = prima['fatt'], ora.get('fatt', 0)
        if f_prima <= 0 or f_ora >= f_prima * 0.95:
            continue
        clienti_calo.append({
            "cliente": nome, "fatturato_anno_prec": round(f_prima, 2), "fatturato_attuale": round(f_ora, 2),
            "var_pct": round((f_ora - f_prima) / f_prima * 100, 1),
            "quantita_anno_prec": round(prima['qty'], 2), "quantita_attuale": round(ora.get('qty', 0), 2),
            "prodotti_anno_prec": len(prima.get('prodotti', [])),
            "prodotti_attuali": len(ora.get('prodotti', [])),
            "impatto": round(f_prima - f_ora, 2),
            "prodotti_persi": await prodotti_persi(nome) if (f_prima - f_ora) > 200 else [],
        })
        if len(clienti_calo) >= limit * 2:
            break
    clienti_calo.sort(key=lambda x: -x['impatto'])

    # ── 3. Clienti a margine basso ──
    margini = [((r['fatt'] - r['costo']) / r['costo'] * 100)
               for r in ora_cli.values() if (r.get('costo') or 0) > 0]
    marg_mediano = median(margini) if margini else MARGINE_TARGET
    clienti_margine_basso = []
    for nome, r in ora_cli.items():
        costo = r.get('costo', 0) or 0
        if costo <= 0 or r['fatt'] < 300:
            continue
        marg = (r['fatt'] - costo) / costo * 100
        if marg >= marg_mediano:
            continue
        target = costo * (1 + marg_mediano / 100)
        clienti_margine_basso.append({
            "cliente": nome, "fatturato": round(r['fatt'], 2), "costo": round(costo, 2),
            "margine_pct": round(marg, 1), "margine_mediano_pct": round(marg_mediano, 1),
            "quantita": round(r['qty'], 2), "prodotti": len(r.get('prodotti', [])),
            "aumento_prezzo_pct": round((target - r['fatt']) / r['fatt'] * 100, 1),
            "impatto": round(target - r['fatt'], 2),
        })
    clienti_margine_basso.sort(key=lambda x: -x['impatto'])

    # ── 4. Prodotti con margine in calo vs anno precedente ──
    async def per_prodotto(s, e):
        rows = await db.vendite.aggregate([
            {"$match": {**base, "data": {"$gte": s, "$lte": e}}},
            {"$group": {"_id": "$prodotto_nome", "fatt": {"$sum": {"$abs": "$totale"}},
                        "qty": {"$sum": {"$abs": "$quantita"}},
                        "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}}}},
        ]).to_list(20000)
        return {r['_id']: r for r in rows if r['_id']}

    ora_prod = await per_prodotto(start, end)
    ly_prod = await per_prodotto(ly_start, ly_end)

    margine_calo = []
    for nome, ora in ora_prod.items():
        prima = ly_prod.get(nome)
        if not prima or (ora.get('costo') or 0) <= 0 or (prima.get('costo') or 0) <= 0:
            continue
        m_ora = (ora['fatt'] - ora['costo']) / ora['costo'] * 100
        m_prima = (prima['fatt'] - prima['costo']) / prima['costo'] * 100
        if m_ora >= m_prima - 1 or ora['fatt'] < 100:
            continue
        prezzo_ora = ora['fatt'] / ora['qty'] if ora['qty'] else 0
        costo_ora = ora['costo'] / ora['qty'] if ora['qty'] else 0
        prezzo_target = costo_ora * (1 + m_prima / 100)
        margine_calo.append({
            "prodotto": nome, "margine_attuale_pct": round(m_ora, 1),
            "margine_anno_prec_pct": round(m_prima, 1),
            "delta_punti": round(m_ora - m_prima, 1),
            "prezzo_vendita": round(prezzo_ora, 4), "costo_attuale": round(costo_ora, 4),
            "costo_anno_prec": round(prima['costo'] / prima['qty'], 4) if prima['qty'] else None,
            "prezzo_target": round(prezzo_target, 4),
            "quantita": round(ora['qty'], 2),
            "impatto": round(max(prezzo_target - prezzo_ora, 0) * ora['qty'], 2),
        })
    margine_calo.sort(key=lambda x: -x['impatto'])

    # ── 5. Sconto quantita' in vendita (proporre lotti piu' grandi) ──
    sconto_quantita_vendita = []
    for p, lista in prezzi_per_prod.items():
        if len(lista) < 4:
            continue
        qta_per_ordine = [(x['qty'] / x['ordini']) if x['ordini'] else x['qty'] for x in lista]
        med_ordine = median(qta_per_ordine)
        prezzo_mediano = median([x['prezzo'] for x in lista])
        for x, q_ord in zip(lista, qta_per_ordine):
            if x['ordini'] < 3 or q_ord >= med_ordine:
                continue
            upside = (med_ordine - q_ord) * x['ordini'] * prezzo_mediano * 0.5
            if upside < 20:
                continue
            sconto_quantita_vendita.append({
                "prodotto": p, "cliente": x['cliente'], "ordini": x['ordini'],
                "qta_per_ordine": round(q_ord, 1), "qta_mediana_mercato": round(med_ordine, 1),
                "prezzo_cliente": round(x['prezzo'], 4), "prezzo_mediano": round(prezzo_mediano, 4),
                "quantita": round(x['qty'], 2),
                "frequenza_giorni": round(giorni_periodo / x['ordini'], 1) if x['ordini'] else None,
                "impatto": round(upside, 2),
            })
    sconto_quantita_vendita.sort(key=lambda x: -x['impatto'])
    moduli = {
        "sotto_prezzo": sotto_prezzo[:limit],
        "clienti_calo": clienti_calo[:limit],
        "clienti_margine_basso": clienti_margine_basso[:limit],
        "margine_calo": margine_calo[:limit],
        "sconto_quantita_vendita": sconto_quantita_vendita[:limit],
    }
    tot = {k: round(sum(r.get('impatto', 0) or 0 for r in v), 2) for k, v in moduli.items()}
    return {
        "periodo": {"start": start, "end": end, "ly_start": ly_start, "ly_end": ly_end,
                    "giorni": giorni_periodo},
        "opportunita": tot,
        "opportunita_totale": round(sum(tot.values()), 2),
        "moduli": moduli,
    }


@router.get("/ottimizzazione/export/pdf")
async def export_ottimizzazione_pdf(
    tipo: str = "acquisti", start_date: Optional[str] = None, end_date: Optional[str] = None,
    giorni_copertura: int = 30, fornitore: Optional[str] = None, cliente: Optional[str] = None,
    prodotto: Optional[str] = None, max_righe: int = 12
):
    from fastapi.responses import Response
    from routes.pdf_helper import (C_AMBER, C_BLUE, C_EMERALD, C_RED, C_SLATE, C_VIOLET, FlowPDF,
                                   clean_text)
    from routes.pdf_sections import blocco_sintesi, it_eur, label_periodo

    def short(t, n):
        t = clean_text(str(t or ''))
        return t if len(t) <= n else t[:n - 1] + '.'

    def eur(v):
        return it_eur(v, 2)

    if tipo == "vendite":
        data = await ottimizzazione_vendite(start_date, end_date, cliente, prodotto, max_righe)
    else:
        data = await ottimizzazione_acquisti(start_date, end_date, giorni_copertura,
                                             fornitore, prodotto, max_righe)
    per = data['periodo']
    opp = data['opportunita']
    m = data['moduli']
    lab = label_periodo(per['start'], per['end'])
    lab_ly = label_periodo(per['ly_start'], per['ly_end'])

    titolo = "OTTIMIZZAZIONE VENDITE" if tipo == "vendite" else "OTTIMIZZAZIONE ACQUISTI"
    pdf = FlowPDF(titolo, f"Periodo: {lab}  |  Confronto con {lab_ly}")
    pdf.add_page()

    if tipo == "vendite":
        pdf.kpi_row([
            ("OPPORTUNITA TOTALE", eur(data['opportunita_totale']), C_EMERALD, "somma dei moduli"),
            ("ALLINEAMENTO PREZZI", eur(opp['sotto_prezzo']), C_BLUE, f"{len(m['sotto_prezzo'])} casi"),
            ("CLIENTI IN CALO", eur(opp['clienti_calo']), C_RED, f"{len(m['clienti_calo'])} clienti"),
            ("MARGINI DA RECUPERARE", eur(opp['clienti_margine_basso'] + opp['margine_calo']), C_AMBER, None),
        ])
        testo = (
            f"Nel periodo {lab}, confrontato con lo stesso periodo dell'anno precedente ({lab_ly}), "
            f"le leve di ottimizzazione delle vendite valgono complessivamente {eur(data['opportunita_totale'])}. "
            f"L'allineamento dei prezzi dei clienti che pagano sotto la mediana vale {eur(opp['sotto_prezzo'])}; "
            f"il recupero dei clienti in calo riguarda {len(m['clienti_calo'])} nominativi per "
            f"{eur(opp['clienti_calo'])} di fatturato perso; la rinegoziazione dei clienti a margine basso vale "
            f"{eur(opp['clienti_margine_basso'])} e l'adeguamento dei prezzi sui prodotti con margine in calo "
            f"{eur(opp['margine_calo'])}. Proporre lotti piu' grandi ai clienti che ordinano poco per volta "
            f"puo' aggiungere {eur(opp['sconto_quantita_vendita'])}. "
            f"Tutti i margini sono calcolati sul costo reale del lotto venduto (FIFO)."
        )
        blocco_sintesi(pdf, testo)

        sezioni = [
            ("Clienti che pagano sotto il prezzo mediano", C_BLUE,
             ['Prodotto', 'Cliente', 'Prz. cliente', 'Prz. mediano', 'Gap', 'Qta', 'Recupero'],
             [46, 46, 20, 20, 14, 18, 26],
             [[short(r['prodotto'], 30), short(r['cliente'], 30), eur(r['prezzo_cliente']),
               eur(r['prezzo_mediano']), f"{r['gap_pct']}%", f"{r['quantita']:,.0f}", eur(r['impatto'])]
              for r in m['sotto_prezzo'][:max_righe]]),
            ("Clienti in calo rispetto all'anno precedente", C_RED,
             ['Cliente', 'Anno prec.', 'Periodo sel.', 'Var. %', 'Prodotti', 'Fatturato perso'],
             [62, 26, 26, 18, 22, 36],
             [[short(r['cliente'], 40), eur(r['fatturato_anno_prec']), eur(r['fatturato_attuale']),
               f"{r['var_pct']}%", f"{r['prodotti_attuali']}/{r['prodotti_anno_prec']}", eur(r['impatto'])]
              for r in m['clienti_calo'][:max_righe]]),
            ("Clienti a margine basso da rinegoziare", C_AMBER,
             ['Cliente', 'Fatturato', 'Margine %', 'Mediano %', 'Aumento sugg.', 'Recupero'],
             [64, 28, 22, 22, 26, 28],
             [[short(r['cliente'], 42), eur(r['fatturato']), f"{r['margine_pct']}%",
               f"{r['margine_mediano_pct']}%", f"+{r['aumento_prezzo_pct']}%", eur(r['impatto'])]
              for r in m['clienti_margine_basso'][:max_righe]]),
            ("Prodotti con margine in calo", C_VIOLET,
             ['Prodotto', 'Marg. ora', 'Marg. prec.', 'Prz. vendita', 'Costo', 'Prz. target', 'Recupero'],
             [56, 20, 22, 24, 20, 22, 26],
             [[short(r['prodotto'], 36), f"{r['margine_attuale_pct']}%", f"{r['margine_anno_prec_pct']}%",
               eur(r['prezzo_vendita']), eur(r['costo_attuale']), eur(r['prezzo_target']), eur(r['impatto'])]
              for r in m['margine_calo'][:max_righe]]),
            ("Clienti a cui proporre lotti piu' grandi", C_SLATE,
             ['Prodotto', 'Cliente', 'Ordini', 'Qta/ordine', 'Mediana', 'Ogni gg', 'Opportunita'],
             [44, 44, 16, 22, 20, 18, 26],
             [[short(r['prodotto'], 28), short(r['cliente'], 28), f"{r['ordini']}",
               f"{r['qta_per_ordine']}", f"{r['qta_mediana_mercato']}",
               f"{r['frequenza_giorni'] or '-'}", eur(r['impatto'])]
              for r in m['sconto_quantita_vendita'][:max_righe]]),
        ]
    else:
        pdf.kpi_row([
            ("OPPORTUNITA TOTALE", eur(data['opportunita_totale']), C_EMERALD, "somma dei moduli"),
            ("CAMBIO FORNITORE", eur(opp['cambio_fornitore']), C_BLUE, f"{len(m['cambio_fornitore'])} prodotti"),
            ("AUMENTI DI PREZZO", eur(opp['prezzi_aumento']), C_RED, "da rinegoziare"),
            ("CAPITALE FERMO", eur(opp['rotazione']), C_AMBER, "lotti a rotazione lenta"),
        ])
        testo = (
            f"Nel periodo {lab}, confrontato con lo stesso periodo dell'anno precedente ({lab_ly}), le leve di "
            f"ottimizzazione degli acquisti valgono complessivamente {eur(data['opportunita_totale'])}. "
            f"Spostando ogni prodotto sul fornitore piu' conveniente si risparmiano {eur(opp['cambio_fornitore'])}; "
            f"consolidando gli ordini per ottenere i prezzi delle forniture maggiori si aggiungono "
            f"{eur(opp['sconto_quantita'])}. Gli aumenti di prezzo rispetto all'anno precedente pesano "
            f"{eur(opp['prezzi_aumento'])} sulle quantita' attuali e riguardano {len(m['prezzi_aumento'])} "
            f"prodotti. Le quantita' da ordinare per i prossimi {per.get('giorni_copertura', 30)} giorni "
            f"({label_periodo(per.get('futuro_start', per['start']), per.get('futuro_end', per['end']))}) sono "
            f"stimate sui dati dello stesso periodo dell'anno scorso "
            f"({label_periodo(per.get('futuro_ly_start', per['ly_start']), per.get('futuro_ly_end', per['ly_end']))}) "
            f"corretti dal trend in corso; nei lotti a rotazione lenta sono fermi {eur(opp['rotazione'])} di "
            f"capitale. Il consolidamento sui fornitori principali permette di spostare volumi per "
            f"{eur(sum(r['spesa_spostabile'] for r in m['consolidamento']))} e negoziare condizioni migliori."
        )
        blocco_sintesi(pdf, testo)

        sezioni = [
            ("Cambio fornitore: stesso prodotto a prezzo migliore", C_BLUE,
             ['Prodotto', 'Fornitore migliore', 'Prz. migliore', 'Prz. medio', 'Prz. peggiore', 'Qta', 'Risparmio'],
             [50, 44, 22, 20, 22, 16, 26],
             [[short(r['prodotto'], 32), short(r['migliore'], 28), eur(r['prezzo_migliore']),
               eur(r['prezzo_medio']), eur(r['prezzo_peggiore']), f"{r['quantita']:,.0f}", eur(r['risparmio'])]
              for r in m['cambio_fornitore'][:max_righe]]),
            ("Sconto quantita': prezzo negli ordini grandi vs piccoli", C_EMERALD,
             ['Prodotto', 'Qta piccoli', 'Prz. piccoli', 'Qta grandi', 'Prz. grandi', 'Sconto', 'Risparmio'],
             [56, 22, 22, 22, 22, 18, 28],
             [[short(r['prodotto'], 36), f"{r['qta_media_piccoli']}", eur(r['prezzo_ordini_piccoli']),
               f"{r['qta_media_grandi']}", eur(r['prezzo_ordini_grandi']), f"{r['sconto_pct']}%",
               eur(r['risparmio'])]
              for r in m['sconto_quantita'][:max_righe]]),
            ("Prezzi in aumento rispetto all'anno precedente", C_RED,
             ['Prodotto', 'Prz. anno prec.', 'Prz. attuale', 'Var. %', 'Qta', 'Impatto'],
             [62, 28, 26, 20, 20, 34],
             [[short(r['prodotto'], 40), eur(r['prezzo_anno_prec']), eur(r['prezzo_attuale']),
               f"+{r['var_pct']}%", f"{r['quantita']:,.0f}", eur(r['impatto'])]
              for r in m['prezzi_aumento'][:max_righe]]),
            (f"Previsione domanda e ordini per i prossimi {per.get('giorni_copertura', 30)} giorni "
             f"({label_periodo(per.get('futuro_start', per['start']), per.get('futuro_end', per['end']))})", C_AMBER,
             ['Prodotto', 'Domanda prevista', 'Trend YoY', 'Giacenza', 'Copertura gg', 'Da ordinare', 'Capitale fermo'],
             [56, 26, 18, 20, 22, 22, 26],
             [[short(r['prodotto'], 36), f"{r['domanda_prevista']}",
               (f"{r['trend_yoy_pct']:+.0f}%" if r.get('trend_yoy_pct') is not None else '-'),
               f"{r['giacenza']}", f"{r['copertura_giorni'] or '-'}", f"{r['da_ordinare']}",
               eur(r['capitale_immobilizzato'])]
              for r in m['rotazione'][:max_righe]]),
            ("Consolidamento fornitori: volumi spostabili", C_VIOLET,
             ['Fornitore', 'Spesa attuale', 'Spostabile', 'Nuovo volume', 'Crescita', 'Leva stimata'],
             [60, 28, 26, 28, 20, 28],
             [[short(r['fornitore'], 40), eur(r['spesa_attuale']), eur(r['spesa_spostabile']),
               eur(r['nuovo_volume']), f"+{r['crescita_pct']}%", eur(r['impatto'])]
              for r in m['consolidamento'][:max_righe]]),
            ("Acquisti che non reggono il prezzo di vendita", C_SLATE,
             ['Prodotto', 'Prz. vendita', 'Costo attuale', 'Margine %', 'Costo target', 'Sconto', 'Impatto'],
             [54, 24, 24, 20, 24, 18, 26],
             [[short(r['prodotto'], 34), eur(r['prezzo_vendita']), eur(r['costo_attuale']),
               f"{r['margine_pct']}%", eur(r['costo_target']),
               f"{r['sconto_da_chiedere_pct'] or '-'}%", eur(r['impatto'])]
              for r in m['margine_basso'][:max_righe]]),
        ]

    for titolo_s, colore, cols, widths, rows in sezioni:
        if not rows:
            continue
        pdf.section_title(titolo_s, colore)
        aligns = ['L'] + (['L'] if 'Cliente' in cols[1] or 'Fornitore' in cols[1] else ['R']) + \
                 ['R'] * (len(cols) - 2)
        pdf.smart_table(cols, widths, rows, aligns=aligns)

    out = pdf.output()
    fname = f"ottimizzazione_{tipo}_{per['start']}_{per['end']}.pdf"
    return Response(bytes(out), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={fname}"})
