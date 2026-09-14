"""Motore FIFO: collega ogni vendita al lotto di acquisto reale e calcola il costo/margine esatto.

Regole:
- Ogni riga di acquisto (ordini con quantita > 0) e' un lotto con prezzo unitario ponderato (totale/quantita).
- Gli eventi (acquisti, resi a fornitore, vendite) vengono processati in ordine cronologico;
  a pari data gli acquisti precedono le vendite.
- Le vendite consumano i lotti aperti in ordine FIFO. Quando un lotto finisce viene registrata
  la data di esaurimento e le vendite successive passano al lotto successivo.
- Quantita' non coperta da lotti reali (vendite precedenti al primo acquisto o venduto > acquistato):
  costo stimato con l'ultimo prezzo di acquisto conosciuto (flag fifo_tracciato = False).
"""
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks
from pymongo import UpdateOne

from database import db

router = APIRouter()
logger = logging.getLogger(__name__)

META_KEY = "fifo_meta"


def _unit_price(doc) -> float:
    q = abs(doc.get('quantita', 0) or 0)
    tot = abs(doc.get('totale', 0) or 0)
    if q > 0 and tot > 0:
        return tot / q
    return abs(doc.get('prezzo_unitario', 0) or 0)


async def rebuild_fifo_prodotto(nome: str) -> Dict:
    ordini = await db.ordini.find(
        {"prodotto_nome": nome},
        {"_id": 1, "id": 1, "data": 1, "fornitore_nome": 1, "quantita": 1, "totale": 1, "prezzo_unitario": 1}
    ).sort([("data", 1), ("_id", 1)]).to_list(None)
    vendite = await db.vendite.find(
        {"prodotto_nome": nome},
        {"_id": 1, "data": 1, "cliente_nome": 1, "quantita": 1, "totale": 1, "prezzo_unitario": 1}
    ).sort([("data", 1), ("_id", 1)]).to_list(None)

    if not vendite:
        await db.lotti.delete_many({"prodotto": nome})
        if ordini:
            lotti_docs = []
            for o in ordini:
                q = o.get('quantita', 0) or 0
                if q <= 0:
                    continue
                prezzo = _unit_price(o)
                lotti_docs.append({
                    "lotto_id": str(o.get('id') or o['_id']), "prodotto": nome, "data_acquisto": o.get('data'),
                    "fornitore": o.get('fornitore_nome', ''), "quantita": round(q, 2),
                    "prezzo_acquisto": round(prezzo, 4), "costo_totale": round(prezzo * q, 2),
                    "quantita_venduta": 0, "residuo": round(q, 2), "ricavo": 0,
                    "data_esaurimento": None, "margine_pct": None, "n_vendite": 0,
                })
            if lotti_docs:
                await db.lotti.insert_many(lotti_docs)
        return {"vendite": 0, "lotti": len(ordini)}

    primo_prezzo = next((_unit_price(o) for o in ordini if (o.get('quantita', 0) or 0) > 0 and _unit_price(o) > 0), 0)
    # prezzi noti in ordine cronologico: servono a stimare i lotti con prezzo mancante (0)
    prezzi_noti = [(o.get('data') or '', _unit_price(o)) for o in ordini
                   if (o.get('quantita', 0) or 0) > 0 and _unit_price(o) > 0]

    def stima_prezzo(data: str, ultimo: float) -> float:
        if ultimo > 0:
            return ultimo
        for d, p in prezzi_noti:
            if d >= data:
                return p
        return primo_prezzo

    # eventi cronologici: 0 = acquisto/reso, 1 = vendita
    eventi = []
    for o in ordini:
        eventi.append((o.get('data') or '', 0, 'ordine', o))
    for v in vendite:
        eventi.append((v.get('data') or '', 1, 'vendita', v))
    eventi.sort(key=lambda e: (e[0], e[1]))

    lots: List[Dict] = []          # tutti i lotti del prodotto (in ordine)
    open_idx = 0                   # primo lotto potenzialmente aperto
    ultimo_prezzo = primo_prezzo
    ultimo_costo_unitario = primo_prezzo
    ops: List[UpdateOne] = []
    non_tracciate = 0

    for data, _, tipo, doc in eventi:
        if tipo == 'ordine':
            q = doc.get('quantita', 0) or 0
            prezzo = _unit_price(doc)
            if q > 0:
                stimato = False
                if prezzo > 0:
                    ultimo_prezzo = prezzo
                else:
                    # riga di acquisto senza prezzo/totale: stima con l'ultimo prezzo noto
                    prezzo = stima_prezzo(data, ultimo_prezzo)
                    stimato = True
                lots.append({
                    "lotto_id": str(doc.get('id') or doc['_id']), "prodotto": nome, "data_acquisto": data,
                    "fornitore": doc.get('fornitore_nome', ''), "quantita": q, "prezzo_acquisto": prezzo,
                    "prezzo_stimato": stimato,
                    "residuo": q, "quantita_venduta": 0.0, "ricavo": 0.0,
                    "data_esaurimento": None, "n_vendite": 0,
                })
            elif q < 0:
                # reso al fornitore: sottrae dai lotti aperti piu' recenti
                resto = -q
                for lot in reversed(lots[open_idx:]):
                    if resto <= 0:
                        break
                    take = min(lot['residuo'], resto)
                    lot['residuo'] -= take
                    resto -= take
                    if lot['residuo'] <= 0.0001 and not lot['data_esaurimento']:
                        lot['data_esaurimento'] = data
            continue

        # vendita
        qty = doc.get('quantita', 0) or 0
        prezzo_vendita = _unit_price(doc)

        if qty < 0:
            # reso da cliente: rimette merce nell'ultimo lotto consumato
            q_reso = -qty
            costo = -(ultimo_costo_unitario * q_reso)
            for lot in reversed(lots[:max(open_idx + 1, 1)]):
                if lot['quantita_venduta'] > 0:
                    take = min(q_reso, lot['quantita_venduta'])
                    lot['quantita_venduta'] -= take
                    lot['residuo'] += take
                    lot['ricavo'] -= take * prezzo_vendita
                    if lot['residuo'] > 0.0001:
                        lot['data_esaurimento'] = None
                    break
            ops.append(UpdateOne({"_id": doc['_id']}, {"$set": {
                "costo_fifo": round(costo, 4),
                "costo_unitario_fifo": round(ultimo_costo_unitario, 4),
                "fifo_tracciato": True, "lotto_id": None}}))
            continue

        restante = qty
        costo_totale = 0.0
        tracciato = True
        lotto_principale = None
        max_take = 0.0

        while restante > 0.0001 and open_idx < len(lots):
            lot = lots[open_idx]
            if lot['residuo'] <= 0.0001:
                open_idx += 1
                continue
            take = min(lot['residuo'], restante)
            lot['residuo'] -= take
            lot['quantita_venduta'] += take
            lot['ricavo'] += take * prezzo_vendita
            lot['n_vendite'] += 1
            costo_totale += take * lot['prezzo_acquisto']
            restante -= take
            if take > max_take:
                max_take = take
                lotto_principale = lot['lotto_id']
            if lot.get('prezzo_stimato'):
                tracciato = False
            if lot['residuo'] <= 0.0001:
                lot['data_esaurimento'] = data
                open_idx += 1

        if restante > 0.0001:
            # quantita' non coperta da lotti reali -> stima con ultimo prezzo noto
            tracciato = False
            non_tracciate += 1
            costo_totale += restante * (ultimo_prezzo or 0)

        if qty > 0:
            ultimo_costo_unitario = costo_totale / qty if costo_totale else ultimo_costo_unitario

        ops.append(UpdateOne({"_id": doc['_id']}, {"$set": {
            "costo_fifo": round(costo_totale, 4),
            "costo_unitario_fifo": round(costo_totale / qty, 4) if qty > 0 else 0,
            "fifo_tracciato": tracciato,
            "lotto_id": lotto_principale,
        }}))

    if ops:
        for i in range(0, len(ops), 2000):
            await db.vendite.bulk_write(ops[i:i + 2000], ordered=False)

    # salva i lotti con il margine reale
    await db.lotti.delete_many({"prodotto": nome})
    if lots:
        docs = []
        for lot in lots:
            venduto = lot['quantita_venduta']
            costo_venduto = venduto * lot['prezzo_acquisto']
            docs.append({
                "lotto_id": lot['lotto_id'], "prodotto": nome, "data_acquisto": lot['data_acquisto'],
                "fornitore": lot['fornitore'], "quantita": round(lot['quantita'], 2),
                "prezzo_acquisto": round(lot['prezzo_acquisto'], 4),
                "prezzo_stimato": bool(lot.get('prezzo_stimato')),
                "costo_totale": round(lot['quantita'] * lot['prezzo_acquisto'], 2),
                "quantita_venduta": round(venduto, 2), "residuo": round(max(lot['residuo'], 0), 2),
                "ricavo": round(lot['ricavo'], 2),
                "prezzo_vendita_medio": round(lot['ricavo'] / venduto, 4) if venduto > 0 else None,
                "data_esaurimento": lot['data_esaurimento'],
                "margine_pct": round((lot['ricavo'] - costo_venduto) / costo_venduto * 100, 1) if costo_venduto > 0 else None,
                "profitto": round(lot['ricavo'] - costo_venduto, 2) if venduto > 0 else 0,
                "n_vendite": lot['n_vendite'],
            })
        await db.lotti.insert_many(docs)

    return {"vendite": len(vendite), "lotti": len(lots), "vendite_non_tracciate": non_tracciate}


async def rebuild_fifo(prodotto: Optional[str] = None) -> Dict:
    start = datetime.now(timezone.utc)
    filtro = {"prodotto_nome": prodotto} if prodotto else {}
    nomi = [n for n in await db.vendite.distinct("prodotto_nome", filtro) if n]
    if prodotto and not nomi:
        nomi = [prodotto]

    tot_vendite = tot_lotti = tot_non_tracciate = 0
    for nome in nomi:
        try:
            res = await rebuild_fifo_prodotto(nome)
            tot_vendite += res.get('vendite', 0)
            tot_lotti += res.get('lotti', 0)
            tot_non_tracciate += res.get('vendite_non_tracciate', 0)
        except Exception as e:
            logger.error(f"FIFO rebuild failed for {nome}: {e}")

    durata = (datetime.now(timezone.utc) - start).total_seconds()
    meta = {
        "key": META_KEY, "ultimo_rebuild": start.isoformat(), "durata_sec": round(durata, 1),
        "prodotti": len(nomi), "vendite_elaborate": tot_vendite, "lotti": tot_lotti,
        "vendite_non_tracciate": tot_non_tracciate,
    }
    if not prodotto:
        await db.settings.update_one({"key": META_KEY}, {"$set": meta}, upsert=True)
    logger.info(f"FIFO rebuild: {meta}")
    return meta


@router.post("/fifo/rebuild")
async def fifo_rebuild(background_tasks: BackgroundTasks, prodotto: Optional[str] = None, attendi: bool = False):
    if attendi or prodotto:
        return await rebuild_fifo(prodotto)
    background_tasks.add_task(rebuild_fifo, None)
    return {"success": True, "messaggio": "Ricalcolo FIFO avviato in background"}


@router.get("/fifo/stato")
async def fifo_stato():
    meta = await db.settings.find_one({"key": META_KEY}, {"_id": 0})
    coperte = await db.vendite.count_documents({"costo_fifo": {"$exists": True}})
    totali = await db.vendite.count_documents({})
    return {
        "meta": meta,
        "vendite_con_costo_fifo": coperte,
        "vendite_totali": totali,
        "copertura_pct": round(coperte / totali * 100, 1) if totali else 0,
    }


@router.get("/fifo/lotto/vendite")
async def fifo_lotto_vendite(lotto_id: str):
    """Vendite collegate a un singolo lotto (drill-down dal lotto agli scarichi)."""
    lotto = await db.lotti.find_one({"lotto_id": lotto_id}, {"_id": 0})
    vendite = await db.vendite.find(
        {"lotto_id": lotto_id},
        {"_id": 0, "data": 1, "cliente_nome": 1, "prodotto_nome": 1, "quantita": 1,
         "prezzo_unitario": 1, "totale": 1, "costo_fifo": 1, "costo_unitario_fifo": 1,
         "fifo_tracciato": 1}
    ).sort([("data", 1)]).to_list(5000)

    righe = []
    for v in vendite:
        qty = abs(v.get('quantita', 0) or 0)
        fatt = abs(v.get('totale', 0) or 0)
        costo = v.get('costo_fifo', 0) or 0
        righe.append({
            "data": v.get('data'), "cliente": v.get('cliente_nome'), "prodotto": v.get('prodotto_nome'),
            "quantita": round(qty, 2), "fatturato": round(fatt, 2),
            "prezzo_vendita": round(fatt / qty, 4) if qty else 0,
            "costo_unitario": round(costo / qty, 4) if (costo and qty) else None,
            "margine": round(fatt - costo, 2) if costo else None,
            "margine_pct": round((fatt - costo) / costo * 100, 1) if costo > 0 else None,
        })
    tot_fatt = sum(r['fatturato'] for r in righe)
    tot_costo = sum((v.get('costo_fifo', 0) or 0) for v in vendite)
    return {
        "lotto": lotto,
        "totali": {
            "quantita": round(sum(r['quantita'] for r in righe), 2),
            "fatturato": round(tot_fatt, 2),
            "costo": round(tot_costo, 2),
            "margine": round(tot_fatt - tot_costo, 2),
            "margine_pct": round((tot_fatt - tot_costo) / tot_costo * 100, 1) if tot_costo > 0 else None,
            "n_vendite": len(righe),
        },
        "vendite": righe,
    }


@router.get("/fifo/lotti")
async def fifo_lotti(prodotto: Optional[str] = None, fornitore: Optional[str] = None,
                     start_date: Optional[str] = None, end_date: Optional[str] = None,
                     solo_esauriti: bool = False, limit: int = 200):
    query = {}
    if prodotto:
        query["prodotto"] = {"$regex": re.escape(prodotto), "$options": "i"}
    if fornitore:
        query["fornitore"] = {"$regex": re.escape(fornitore), "$options": "i"}
    if start_date or end_date:
        query["data_acquisto"] = {}
        if start_date:
            query["data_acquisto"]["$gte"] = start_date
        if end_date:
            query["data_acquisto"]["$lte"] = end_date
    if solo_esauriti:
        query["data_esaurimento"] = {"$ne": None}
    lotti = await db.lotti.find(query, {"_id": 0}).sort([("data_acquisto", -1)]).limit(limit).to_list(limit)
    return {"totale": await db.lotti.count_documents(query), "lotti": lotti}
