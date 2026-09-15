"""Agente AI con strumenti: interroga e modifica i dati del gestionale."""
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from database import db
from routes.analisi import EXCLUDED_CLIENTS, esclusi_filter, reference_date

router = APIRouter()
logger = logging.getLogger(__name__)

MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-6"
MAX_TOOL_ROUNDS = 12

# ═══════════════════════ TOOL IMPLEMENTATIONS ═══════════════════════


def _period(args: Dict[str, Any]):
    return args.get('start_date') or '0000-01-01', args.get('end_date') or '9999-12-31'


async def t_panoramica(args):
    ref = await reference_date()
    first = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", 1)])
    from routes.esclusioni import get_prodotti_esclusi
    esclusi = await get_prodotti_esclusi()
    prodotti = await db.prodotti.count_documents({})
    sotto_scorta = await db.prodotti.count_documents(
        {"quantita_minima": {"$gt": 0}, "$expr": {"$lte": ["$quantita", "$quantita_minima"]}})
    val = await db.prodotti.aggregate([
        {"$group": {"_id": None, "v": {"$sum": {"$multiply": ["$quantita", "$prezzo_medio"]}}}}]).to_list(1)
    return {
        "data_odierna": datetime.now().strftime("%Y-%m-%d"),
        "dati_disponibili_da": first.get('data') if first else None,
        "dati_disponibili_fino_a": ref.strftime("%Y-%m-%d"),
        "n_vendite": await db.vendite.count_documents({}),
        "n_ordini_acquisto": await db.ordini.count_documents({}),
        "n_clienti": await db.clienti.count_documents({}),
        "n_fornitori": await db.fornitori.count_documents({}),
        "n_prodotti": prodotti,
        "prodotti_sotto_scorta": sotto_scorta,
        "valore_magazzino": round(val[0]['v'], 2) if val else 0,
        "prodotti_esclusi_dai_calcoli": esclusi,
    }


async def t_query_vendite(args):
    start, end = _period(args)
    excl = await esclusi_filter()
    match = {"data": {"$gte": start, "$lte": end}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}, **excl}
    if args.get('prodotto'):
        match["prodotto_nome"] = {"$regex": args['prodotto'], "$options": "i"}
    if args.get('cliente'):
        match["cliente_nome"] = {"$regex": args['cliente'], "$options": "i"}

    limit = min(int(args.get('limit') or 20), 100)
    group_by = args.get('group_by') or 'prodotto'
    field = {"prodotto": "$prodotto_nome", "cliente": "$cliente_nome",
             "mese": {"$substr": ["$data", 0, 7]}, "giorno": "$data"}.get(group_by)

    totali = await db.vendite.aggregate([
        {"$match": match},
        {"$group": {"_id": None, "fatturato": {"$sum": {"$abs": "$totale"}},
                    "quantita": {"$sum": {"$abs": "$quantita"}}, "righe": {"$sum": 1}}}]).to_list(1)
    tot = totali[0] if totali else {"fatturato": 0, "quantita": 0, "righe": 0}

    if group_by == 'nessuno':
        rows = await db.vendite.find(match, {"_id": 0, "data": 1, "cliente_nome": 1, "prodotto_nome": 1,
                                             "quantita": 1, "prezzo_unitario": 1, "totale": 1}
                                     ).sort("data", -1).limit(limit).to_list(limit)
        risultati = rows
    else:
        sort_field = "quantita" if (args.get('sort_by') == 'quantita') else "fatturato"
        pipeline = [
            {"$match": match},
            {"$group": {"_id": field, "fatturato": {"$sum": {"$abs": "$totale"}},
                        "quantita": {"$sum": {"$abs": "$quantita"}}, "righe": {"$sum": 1}}},
            {"$sort": {"_id": 1} if group_by in ('mese', 'giorno') else {sort_field: -1}},
            {"$limit": limit},
        ]
        rows = await db.vendite.aggregate(pipeline).to_list(limit)
        risultati = [{
            group_by: r['_id'],
            "fatturato": round(r['fatturato'], 2),
            "quantita": round(r['quantita'], 2),
            "prezzo_medio": round(r['fatturato'] / r['quantita'], 4) if r['quantita'] else 0,
            "righe": r['righe'],
        } for r in rows]

    return {"periodo": {"start": start, "end": end}, "totali": {
        "fatturato": round(tot['fatturato'], 2), "quantita": round(tot['quantita'], 2), "righe": tot['righe']},
        "risultati": risultati}


async def t_query_acquisti(args):
    start, end = _period(args)
    match = {"data": {"$gte": start, "$lte": end}}
    if args.get('fornitore'):
        match["fornitore_nome"] = {"$regex": args['fornitore'], "$options": "i"}
    if args.get('prodotto'):
        match["prodotto_nome"] = {"$regex": args['prodotto'], "$options": "i"}

    limit = min(int(args.get('limit') or 20), 100)
    group_by = args.get('group_by') or 'fornitore'
    field = {"fornitore": "$fornitore_nome", "prodotto": "$prodotto_nome",
             "mese": {"$substr": ["$data", 0, 7]},
             "prodotto_fornitore": {"p": "$prodotto_nome", "f": "$fornitore_nome"}}.get(group_by)

    totali = await db.ordini.aggregate([
        {"$match": match},
        {"$group": {"_id": None, "spesa": {"$sum": "$totale"}, "quantita": {"$sum": "$quantita"},
                    "righe": {"$sum": 1},
                    "resi": {"$sum": {"$cond": [{"$lt": ["$quantita", 0]}, {"$abs": "$totale"}, 0]}}}}]).to_list(1)
    tot = totali[0] if totali else {"spesa": 0, "quantita": 0, "righe": 0, "resi": 0}

    if group_by == 'nessuno':
        risultati = await db.ordini.find(match, {"_id": 0, "data": 1, "fornitore_nome": 1, "prodotto_nome": 1,
                                                 "quantita": 1, "prezzo_unitario": 1, "totale": 1}
                                         ).sort("data", -1).limit(limit).to_list(limit)
    else:
        pipeline = [
            {"$match": match},
            {"$group": {"_id": field, "spesa": {"$sum": "$totale"}, "quantita": {"$sum": "$quantita"},
                        "righe": {"$sum": 1}}},
            {"$sort": {"_id": 1} if group_by == 'mese' else {"spesa": -1}},
            {"$limit": limit},
        ]
        rows = await db.ordini.aggregate(pipeline).to_list(limit)
        if group_by == 'prodotto_fornitore':
            qty_prod: dict = {}
            for r in rows:
                pn = r['_id'].get('p')
                qty_prod[pn] = qty_prod.get(pn, 0) + max(r['quantita'], 0)
            risultati = []
            for r in rows:
                pn, fn = r['_id'].get('p'), r['_id'].get('f')
                quota = (max(r['quantita'], 0) / qty_prod[pn] * 100) if qty_prod.get(pn) else 0
                risultati.append({
                    "prodotto": pn, "fornitore": fn,
                    "quantita_acquistata": round(r['quantita'], 2),
                    "spesa": round(r['spesa'], 2),
                    "prezzo_medio": round(r['spesa'] / r['quantita'], 4) if r['quantita'] else 0,
                    "quota_pct": round(quota, 1),
                    "ruolo": "primario" if quota >= 40 else ("secondario" if quota >= 10 else "occasionale"),
                    "righe": r['righe'],
                })
            risultati.sort(key=lambda x: (x['prodotto'], -x['quantita_acquistata']))
        else:
            risultati = [{
                group_by: r['_id'], "spesa": round(r['spesa'], 2), "quantita": round(r['quantita'], 2),
                "prezzo_medio": round(r['spesa'] / r['quantita'], 4) if r['quantita'] else 0,
                "righe": r['righe'],
            } for r in rows]

    return {"periodo": {"start": start, "end": end},
            "totali": {"spesa": round(tot['spesa'], 2), "quantita": round(tot['quantita'], 2),
                       "righe": tot['righe'], "resi_a_fornitore": round(tot.get('resi', 0), 2)},
            "risultati": risultati}


async def t_confronto_fornitori(args):
    from routes.analisi import analisi_confronto_fornitori
    return await analisi_confronto_fornitori(args['prodotto'], args.get('start_date'), args.get('end_date'))


async def t_analisi_margini(args):
    from routes.analisi import analisi_vendite_prodotti
    res = await analisi_vendite_prodotti(args.get('start_date'), args.get('end_date'), args.get('prodotto'), 500)
    rows = [r for r in res['prodotti'] if r['margine_pct'] is not None]
    rows.sort(key=lambda r: r['margine_pct'], reverse=(args.get('ordine') != 'peggiori'))
    limit = min(int(args.get('limit') or 15), 60)
    return {"periodo": res['periodo'], "kpi": res['kpi'], "prodotti": rows[:limit]}


async def t_get_giacenze(args):
    query = {}
    if args.get('prodotto'):
        query["nome"] = {"$regex": args['prodotto'], "$options": "i"}
    if args.get('solo_sotto_scorta'):
        query["quantita_minima"] = {"$gt": 0}
        query["$expr"] = {"$lte": ["$quantita", "$quantita_minima"]}
    if args.get('solo_esaurite'):
        query["quantita"] = {"$lte": 0}
    limit = min(int(args.get('limit') or 30), 200)
    rows = await db.prodotti.find(query, {"_id": 0, "nome": 1, "quantita": 1, "quantita_minima": 1,
                                          "prezzo_medio": 1, "scadenza": 1, "codice": 1}
                                  ).sort("quantita", -1).limit(limit).to_list(limit)
    return {"totale_trovati": await db.prodotti.count_documents(query), "prodotti": rows}


async def t_cerca_entita(args):
    tipo = args.get('tipo', 'prodotto')
    q = args.get('query', '')
    coll = {"cliente": db.clienti, "fornitore": db.fornitori, "prodotto": db.prodotti}[tipo]
    rows = await coll.find({"nome": {"$regex": q, "$options": "i"}}, {"_id": 0}
                           ).limit(min(int(args.get('limit') or 15), 50)).to_list(50)
    return {"tipo": tipo, "risultati": rows}


async def t_confronta_periodi(args):
    tipo = args.get('tipo', 'vendite')
    group_by = args.get('group_by', 'prodotto')
    limit = min(int(args.get('limit') or 20), 60)
    coll = db.vendite if tipo == 'vendite' else db.ordini
    field_map = {"prodotto": "$prodotto_nome", "cliente": "$cliente_nome", "fornitore": "$fornitore_nome"}
    field = field_map.get(group_by, "$prodotto_nome")
    val_field = "$totale"
    excl = await esclusi_filter() if tipo == 'vendite' else {}

    async def agg(s, e):
        match = {"data": {"$gte": s, "$lte": e}, **excl}
        if tipo == 'vendite':
            match["cliente_nome"] = {"$nin": EXCLUDED_CLIENTS}
        rows = await coll.aggregate([
            {"$match": match},
            {"$group": {"_id": field, "valore": {"$sum": {"$abs": val_field}},
                        "quantita": {"$sum": {"$abs": "$quantita"}}}}]).to_list(20000)
        return {r['_id']: r for r in rows if r['_id']}

    p1 = await agg(args['periodo1_start'], args['periodo1_end'])
    p2 = await agg(args['periodo2_start'], args['periodo2_end'])
    nomi = set(p1) | set(p2)
    out = []
    for n in nomi:
        v1 = p1.get(n, {}).get('valore', 0)
        v2 = p2.get(n, {}).get('valore', 0)
        out.append({
            group_by: n, "periodo1": round(v1, 2), "periodo2": round(v2, 2),
            "delta": round(v2 - v1, 2),
            "delta_pct": round((v2 - v1) / v1 * 100, 1) if v1 > 0 else None,
            "qty_periodo1": round(p1.get(n, {}).get('quantita', 0), 2),
            "qty_periodo2": round(p2.get(n, {}).get('quantita', 0), 2),
        })
    ordine = args.get('ordine', 'crescita')
    out.sort(key=lambda r: r['delta'], reverse=(ordine != 'calo'))
    return {
        "periodo1": {"start": args['periodo1_start'], "end": args['periodo1_end'],
                     "totale": round(sum(r['valore'] for r in p1.values()), 2)},
        "periodo2": {"start": args['periodo2_start'], "end": args['periodo2_end'],
                     "totale": round(sum(r['valore'] for r in p2.values()), 2)},
        "risultati": out[:limit],
    }


# ── azioni di scrittura ──

async def t_gestisci_esclusioni(args):
    from routes.esclusioni import get_prodotti_esclusi, SETTINGS_KEY
    azione = args.get('azione', 'lista')
    correnti = set(await get_prodotti_esclusi())
    if azione == 'lista':
        return {"prodotti_esclusi": sorted(correnti)}
    nomi = args.get('prodotti') or []
    risolti = []
    for n in nomi:
        p = await db.prodotti.find_one({"nome": {"$regex": f"^{n}$", "$options": "i"}}, {"_id": 0, "nome": 1})
        if not p:
            p = await db.prodotti.find_one({"nome": {"$regex": n, "$options": "i"}}, {"_id": 0, "nome": 1})
        risolti.append(p['nome'] if p else n)
    if azione == 'escludi':
        correnti |= set(risolti)
    else:
        correnti -= set(risolti)
    await db.settings.update_one({"key": SETTINGS_KEY},
                                 {"$set": {"key": SETTINGS_KEY, "nomi": sorted(correnti)}}, upsert=True)
    return {"success": True, "azione": azione, "prodotti_interessati": risolti,
            "prodotti_esclusi": sorted(correnti)}


async def t_aggiorna_prodotto(args):
    nome = args['nome']
    prodotto = await db.prodotti.find_one({"nome": {"$regex": f"^{nome}$", "$options": "i"}}, {"_id": 0})
    if not prodotto:
        prodotto = await db.prodotti.find_one({"nome": {"$regex": nome, "$options": "i"}}, {"_id": 0})
    if not prodotto:
        return {"success": False, "errore": f"Prodotto '{nome}' non trovato"}
    update = {}
    for k in ('quantita_minima', 'quantita', 'prezzo_medio'):
        if args.get(k) is not None:
            update[k] = float(args[k])
    if args.get('scadenza') is not None:
        update['scadenza'] = args['scadenza']
    if not update:
        return {"success": False, "errore": "Nessun campo da aggiornare"}
    await db.prodotti.update_one({"id": prodotto['id']}, {"$set": update})
    nuovo = await db.prodotti.find_one({"id": prodotto['id']}, {"_id": 0})
    return {"success": True, "prodotto": nuovo['nome'], "modifiche": update, "stato_attuale": nuovo}


async def t_gestisci_entita(args):
    tipo = args['tipo']
    azione = args['azione']
    nome = args.get('nome', '')
    coll = {"cliente": db.clienti, "fornitore": db.fornitori, "prodotto": db.prodotti}[tipo]
    campi = args.get('campi') or {}

    if azione == 'crea':
        esistente = await coll.find_one({"nome": {"$regex": f"^{nome}$", "$options": "i"}}, {"_id": 0})
        if esistente:
            return {"success": False, "errore": f"{tipo} '{nome}' già esistente", "esistente": esistente}
        doc = {"id": str(uuid.uuid4()), "nome": nome,
               "created_at": datetime.now(timezone.utc).isoformat(), **campi}
        await coll.insert_one(dict(doc))
        doc.pop('_id', None)
        return {"success": True, "creato": doc}

    esistente = await coll.find_one({"nome": {"$regex": f"^{nome}$", "$options": "i"}}, {"_id": 0})
    if not esistente:
        esistente = await coll.find_one({"nome": {"$regex": nome, "$options": "i"}}, {"_id": 0})
    if not esistente:
        return {"success": False, "errore": f"{tipo} '{nome}' non trovato"}

    if azione == 'elimina':
        await coll.delete_one({"id": esistente['id']})
        return {"success": True, "eliminato": esistente['nome']}

    if not campi:
        return {"success": False, "errore": "Nessun campo da aggiornare"}
    await coll.update_one({"id": esistente['id']}, {"$set": campi})
    aggiornato = await coll.find_one({"id": esistente['id']}, {"_id": 0})
    return {"success": True, "aggiornato": aggiornato}


async def t_ricalcola_giacenze(args):
    from routes.prodotti import recompute_all_quantities
    res = await recompute_all_quantities()
    return {"success": True, "risultato": res}


async def t_pulisci_duplicati(args):
    from routes.upload import pulisci_duplicati
    res = await pulisci_duplicati()
    return {"success": True, "risultato": res}


async def t_prodotto_dettaglio(args):
    from routes.analisi import analisi_prodotto_dettaglio
    return await analisi_prodotto_dettaglio(args['nome'], args.get('start_date'), args.get('end_date'))


async def t_ottimizzazione(args):
    tipo = (args.get('tipo') or 'acquisti').lower()
    if tipo == 'vendite':
        from routes.ottimizzazione import ottimizzazione_vendite
        res = await ottimizzazione_vendite(args.get('start_date'), args.get('end_date'),
                                           args.get('cliente'), args.get('prodotto'),
                                           min(int(args.get('limit') or 10), 25))
    else:
        from routes.ottimizzazione import ottimizzazione_acquisti
        res = await ottimizzazione_acquisti(args.get('start_date'), args.get('end_date'),
                                            int(args.get('giorni_copertura') or 30),
                                            args.get('fornitore'), args.get('prodotto'),
                                            min(int(args.get('limit') or 10), 25))
    if args.get('modulo'):
        mod = args['modulo']
        res['moduli'] = {mod: res['moduli'].get(mod, [])}
    return res


async def t_genera_pdf(args):
    from urllib.parse import urlencode
    tipo = (args.get('tipo') or 'rendiconto').lower()
    params = {}
    oggi = datetime.now().strftime("%Y-%m-%d")
    if args.get('start_date'):
        params['start_date'] = min(args['start_date'], oggi)
    if args.get('end_date'):
        params['end_date'] = min(args['end_date'], oggi)
    if tipo == 'rendiconto':
        params['provvigione_pct'] = args.get('provvigione_pct') or 3
        params['dettaglio'] = str(bool(args.get('dettaglio', False))).lower()
        path = "/api/analisi/export/rendiconto"
        titolo = "Rendiconto vendite (provvigione sul margine)"
    elif tipo in ('listino_cliente', 'listino_prodotto'):
        params['ordina'] = args.get('ordina') or 'quantita'
        if tipo == 'listino_cliente':
            params['cliente'] = args.get('cliente') or ''
            titolo = f"Listino cliente {params['cliente']}"
        else:
            params['prodotto'] = args.get('prodotto') or ''
            titolo = f"Listino clienti del prodotto {params['prodotto']}"
        path = "/api/analisi/export/listino"
    elif tipo in ('ottimizzazione_acquisti', 'ottimizzazione_vendite'):
        params['tipo'] = 'vendite' if tipo.endswith('vendite') else 'acquisti'
        if args.get('giorni_copertura'):
            params['giorni_copertura'] = args['giorni_copertura']
        path = "/api/ottimizzazione/export/pdf"
        titolo = f"Ottimizzazione {params['tipo']}"
    elif tipo == 'rendiconto_acquisti':
        params['provvigione_pct'] = args.get('provvigione_pct') or 3
        if args.get('fornitore'):
            params['fornitore'] = args['fornitore']
        path = "/api/analisi/export/rendiconto-acquisti"
        titolo = "Rendiconto acquisti e lotti (resa dei lotti)"
    else:
        params['tipo'] = 'acquisti' if tipo == 'acquisti' else 'vendite'
        if args.get('fornitore'):
            params['fornitore'] = args['fornitore']
        if args.get('prodotto'):
            params['prodotto'] = args['prodotto']
        path = "/api/analisi/export/pdf"
        titolo = f"Analisi {params['tipo']}"
    url = f"{path}?{urlencode(params)}"
    return {"success": True, "titolo": titolo, "url": url,
            "istruzioni": ("Mostra all'utente il link markdown copiando ESATTAMENTE il campo url "
                           "(inizia con /api/...). NON aggiungere alcun dominio o host.")}


async def t_genera_pdf_report(args):
    from routes.pdf_ai_report import salva_report
    titolo = (args.get('titolo') or 'Report Flow AI')[:90]
    testo = args.get('testo') or ''
    if not testo.strip():
        return {"errore": "Serve il testo dell'analisi da riportare nel PDF"}
    rid = await salva_report(titolo, args.get('sottotitolo') or '', testo,
                             args.get('kpi'), args.get('tabelle'), args.get('note') or '',
                             args.get('grafici'))
    return {"success": True, "titolo": titolo, "url": f"/api/ai/report/{rid}.pdf",
            "istruzioni": ("Mostra all'utente il link markdown copiando ESATTAMENTE il campo url "
                           "(inizia con /api/...). NON aggiungere alcun dominio.")}


async def t_lotto_vendite(args):
    from routes.fifo import fifo_lotto_vendite
    return await fifo_lotto_vendite(args['lotto_id'])


async def t_lotti_prodotto(args):
    from routes.fifo import fifo_lotti
    return await fifo_lotti(args.get('prodotto'), args.get('fornitore'), args.get('start_date'),
                            args.get('end_date'), bool(args.get('solo_esauriti')),
                            min(int(args.get('limit') or 40), 200))


async def t_ricalcola_lotti(args):
    from routes.fifo import rebuild_fifo
    return await rebuild_fifo(args.get('prodotto'))


TOOL_IMPL = {
    "panoramica": t_panoramica,
    "query_vendite": t_query_vendite,
    "query_acquisti": t_query_acquisti,
    "confronto_fornitori": t_confronto_fornitori,
    "analisi_margini": t_analisi_margini,
    "get_giacenze": t_get_giacenze,
    "cerca_entita": t_cerca_entita,
    "confronta_periodi": t_confronta_periodi,
    "prodotto_dettaglio": t_prodotto_dettaglio,
    "lotti_prodotto": t_lotti_prodotto,
    "lotto_vendite": t_lotto_vendite,
    "genera_pdf": t_genera_pdf,
    "genera_pdf_report": t_genera_pdf_report,
    "ottimizzazione": t_ottimizzazione,
    "gestisci_esclusioni": t_gestisci_esclusioni,
    "aggiorna_prodotto": t_aggiorna_prodotto,
    "gestisci_entita": t_gestisci_entita,
    "ricalcola_giacenze": t_ricalcola_giacenze,
    "ricalcola_lotti": t_ricalcola_lotti,
    "pulisci_duplicati": t_pulisci_duplicati,
}

WRITE_TOOLS = {"gestisci_esclusioni", "aggiorna_prodotto", "gestisci_entita",
               "ricalcola_giacenze", "ricalcola_lotti", "pulisci_duplicati"}

TOOL_LABELS = {
    "panoramica": "Panoramica azienda",
    "query_vendite": "Analisi vendite",
    "query_acquisti": "Analisi acquisti",
    "confronto_fornitori": "Confronto prezzi fornitori",
    "analisi_margini": "Calcolo margini",
    "get_giacenze": "Lettura giacenze",
    "cerca_entita": "Ricerca anagrafiche",
    "confronta_periodi": "Confronto periodi",
    "prodotto_dettaglio": "Dettaglio prodotto",
    "lotti_prodotto": "Lotti FIFO",
    "lotto_vendite": "Vendite del lotto",
    "genera_pdf": "Generazione PDF",
    "genera_pdf_report": "PDF del report",
    "ottimizzazione": "Analisi di ottimizzazione",
    "ricalcola_lotti": "Ricalcolo lotti FIFO",
    "gestisci_esclusioni": "Gestione esclusioni",
    "aggiorna_prodotto": "Modifica prodotto",
    "gestisci_entita": "Modifica anagrafica",
    "ricalcola_giacenze": "Ricalcolo giacenze",
    "pulisci_duplicati": "Pulizia duplicati",
}


def _fn(name, description, properties, required=None):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required or []}}}


DATE_PROPS = {
    "start_date": {"type": "string", "description": "Data inizio YYYY-MM-DD"},
    "end_date": {"type": "string", "description": "Data fine YYYY-MM-DD"},
}

TOOLS = [
    _fn("panoramica", "Panoramica generale: intervallo date dei dati disponibili, conteggi, valore magazzino, prodotti esclusi. Usala SEMPRE come prima chiamata se non conosci il periodo dei dati.", {}),
    _fn("query_vendite", "Interroga le vendite con filtri e raggruppamenti. Restituisce fatturato, quantità e prezzo medio ponderato.", {
        **DATE_PROPS,
        "prodotto": {"type": "string", "description": "Filtro parziale nome prodotto"},
        "cliente": {"type": "string", "description": "Filtro parziale nome cliente"},
        "group_by": {"type": "string", "enum": ["prodotto", "cliente", "mese", "giorno", "nessuno"]},
        "sort_by": {"type": "string", "enum": ["fatturato", "quantita"]},
        "limit": {"type": "integer"},
    }),
    _fn("query_acquisti", "Interroga gli acquisti dai fornitori (collezione ordini). Quantità negative = resi al fornitore. Per i PREZZI DI ACQUISTO di uno o piu' prodotti usa SEMPRE group_by='prodotto_fornitore': restituisce prezzo medio, quantita', quota % e ruolo (primario/secondario/occasionale) per ogni fornitore. Il prezzo medio con group_by='prodotto' mescola fornitori diversi e NON e' attendibile.", {
        **DATE_PROPS,
        "fornitore": {"type": "string"}, "prodotto": {"type": "string"},
        "group_by": {"type": "string", "enum": ["fornitore", "prodotto", "prodotto_fornitore", "mese", "nessuno"]},
        "limit": {"type": "integer"},
    }),
    _fn("confronto_fornitori", "Confronta il prezzo dello stesso prodotto tra i diversi fornitori, con risparmio potenziale.", {
        "prodotto": {"type": "string", "description": "Nome esatto del prodotto"}, **DATE_PROPS}, ["prodotto"]),
    _fn("analisi_margini", "Margini reali per prodotto nel periodo, calcolati con il costo FIFO del lotto effettivamente venduto.", {
        **DATE_PROPS, "prodotto": {"type": "string"},
        "ordine": {"type": "string", "enum": ["migliori", "peggiori"]}, "limit": {"type": "integer"}}),
    _fn("lotti_prodotto", "Lotti di acquisto FIFO: per ogni lotto data di acquisto, fornitore, quantità, prezzo, quantità venduta, residuo, DATA DI ESAURIMENTO e margine reale del lotto. Usalo per domande tipo 'quando è finito il lotto X e a che margine l'ho venduto'.", {
        "prodotto": {"type": "string"}, "fornitore": {"type": "string"}, **DATE_PROPS,
        "solo_esauriti": {"type": "boolean"}, "limit": {"type": "integer"}}),
    _fn("lotto_vendite", "Elenco delle vendite collegate a un singolo lotto (usa il campo lotto_id ottenuto da lotti_prodotto).", {
        "lotto_id": {"type": "string"}}, ["lotto_id"]),
    _fn("ricalcola_lotti", "Ricostruisce i lotti FIFO e i costi/margini reali di tutte le vendite (o di un solo prodotto).", {
        "prodotto": {"type": "string"}}),
    _fn("ottimizzazione", "Opportunita' di ottimizzazione quantificate in euro, confrontate con lo stesso periodo dell'anno precedente. tipo=acquisti -> moduli: cambio_fornitore, sconto_quantita, prezzi_aumento, rotazione, consolidamento, margine_basso. tipo=vendite -> moduli: sotto_prezzo, clienti_calo, clienti_margine_basso, margine_calo, sconto_quantita_vendita.", {
        "tipo": {"type": "string", "enum": ["acquisti", "vendite"]}, **DATE_PROPS,
        "modulo": {"type": "string", "description": "Filtra un singolo modulo per risposte piu' brevi"},
        "fornitore": {"type": "string"}, "cliente": {"type": "string"}, "prodotto": {"type": "string"},
        "giorni_copertura": {"type": "integer"}, "limit": {"type": "integer"}}, ["tipo"]),
    _fn("genera_pdf", "Genera un PDF scaricabile. 'rendiconto' = venduto del periodo con margini e provvigione. 'rendiconto_acquisti' = lotti acquistati nel periodo con resa e provvigione. 'ottimizzazione_acquisti'/'ottimizzazione_vendite' = report delle opportunita' di ottimizzazione. 'vendite'/'acquisti' = analisi del periodo. 'listino_cliente' = prodotti e prezzi di un cliente. 'listino_prodotto' = clienti che comprano un prodotto e prezzo pagato.", {
        "tipo": {"type": "string", "enum": ["rendiconto", "rendiconto_acquisti", "vendite", "acquisti",
                                            "listino_cliente", "listino_prodotto",
                                            "ottimizzazione_acquisti", "ottimizzazione_vendite"]},
        **DATE_PROPS,
        "provvigione_pct": {"type": "number", "description": "Percentuale provvigione sul margine (default 3)"},
        "dettaglio": {"type": "boolean", "description": "Includi l'elenco riga per riga degli scarichi"},
        "ordina": {"type": "string", "enum": ["quantita", "margine", "prezzo"],
                   "description": "Ordinamento dei listini (default quantita)"},
        "cliente": {"type": "string"},
        "giorni_copertura": {"type": "integer"},
        "fornitore": {"type": "string"}, "prodotto": {"type": "string"}}, ["tipo"]),
    _fn("genera_pdf_report", "PDF dell'analisi che hai appena scritto in chat: riporta il TUO testo, i KPI e le tabelle con i numeri reali che hai ottenuto dagli altri strumenti. Usalo SEMPRE quando l'utente chiede il PDF di un'analisi, di un ragionamento o di una risposta data in chat (es. 'fammi il pdf di questo report').", {
        "titolo": {"type": "string", "description": "Titolo del report, es. 'Analisi pistacchio 2026'"},
        "sottotitolo": {"type": "string", "description": "Periodo o filtri applicati"},
        "testo": {"type": "string", "description": "Il testo completo dell'analisi: sezioni, elenchi con '-', numeri reali. Righe in MAIUSCOLO come titoli di sezione."},
        "kpi": {"type": "array", "description": "Massimo 4 KPI principali",
                "items": {"type": "object", "properties": {
                    "label": {"type": "string"}, "valore": {"type": "string"}, "nota": {"type": "string"}}}},
        "tabelle": {"type": "array", "description": "Tabelle con i dati reali usati nell'analisi",
                    "items": {"type": "object", "properties": {
                        "titolo": {"type": "string"},
                        "colonne": {"type": "array", "items": {"type": "string"}},
                        "righe": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
                        "nota": {"type": "string"}}}},
        "grafici": {"type": "array", "description": "Serie di dati aggiuntive rese come tabella (es. andamento mensile, confronto con l'anno precedente)",
                    "items": {"type": "object", "properties": {
                        "tipo": {"type": "string", "enum": ["colonne", "confronto", "barre", "quote"]},
                        "titolo": {"type": "string"},
                        "etichette": {"type": "array", "items": {"type": "string"}, "description": "Es. ['Apr','Mag','Giu'] o nomi prodotto"},
                        "valori": {"type": "array", "items": {"type": "number"}},
                        "valori2": {"type": "array", "items": {"type": "number"}, "description": "Serie di confronto (anno precedente)"},
                        "legenda": {"type": "string"}, "legenda2": {"type": "string"},
                        "unita": {"type": "string", "description": "Es. ' EUR' o ' pz'"},
                        "nota": {"type": "string"}}}},
        "note": {"type": "string"}}, ["titolo", "testo"]),
    _fn("get_giacenze", "Giacenze di magazzino, quantità minime e scadenze.", {
        "prodotto": {"type": "string"}, "solo_sotto_scorta": {"type": "boolean"},
        "solo_esaurite": {"type": "boolean"}, "limit": {"type": "integer"}}),
    _fn("cerca_entita", "Cerca clienti, fornitori o prodotti per nome (match parziale). Usala per risolvere nomi imprecisi.", {
        "tipo": {"type": "string", "enum": ["cliente", "fornitore", "prodotto"]},
        "query": {"type": "string"}, "limit": {"type": "integer"}}, ["tipo", "query"]),
    _fn("confronta_periodi", "Confronta due periodi qualsiasi per prodotto/cliente/fornitore e mostra crescite e cali.", {
        "tipo": {"type": "string", "enum": ["vendite", "acquisti"]},
        "group_by": {"type": "string", "enum": ["prodotto", "cliente", "fornitore"]},
        "periodo1_start": {"type": "string"}, "periodo1_end": {"type": "string"},
        "periodo2_start": {"type": "string"}, "periodo2_end": {"type": "string"},
        "ordine": {"type": "string", "enum": ["crescita", "calo"]}, "limit": {"type": "integer"}},
        ["tipo", "periodo1_start", "periodo1_end", "periodo2_start", "periodo2_end"]),
    _fn("prodotto_dettaglio", "Scheda completa di un prodotto: serie mensile vendite/acquisti, prezzi, margini, top clienti, fornitori.", {
        "nome": {"type": "string", "description": "Nome esatto prodotto"}, **DATE_PROPS}, ["nome"]),
    _fn("gestisci_esclusioni", "Legge o modifica la lista dei prodotti esclusi da tutti i calcoli.", {        "azione": {"type": "string", "enum": ["lista", "escludi", "includi"]},
        "prodotti": {"type": "array", "items": {"type": "string"}}}, ["azione"]),
    _fn("aggiorna_prodotto", "Modifica un prodotto: quantità minima, scadenza, giacenza, prezzo medio.", {
        "nome": {"type": "string"}, "quantita_minima": {"type": "number"},
        "scadenza": {"type": "string", "description": "YYYY-MM-DD o stringa vuota"},
        "quantita": {"type": "number"}, "prezzo_medio": {"type": "number"}}, ["nome"]),
    _fn("gestisci_entita", "Crea, aggiorna o elimina un cliente, fornitore o prodotto.", {
        "azione": {"type": "string", "enum": ["crea", "aggiorna", "elimina"]},
        "tipo": {"type": "string", "enum": ["cliente", "fornitore", "prodotto"]},
        "nome": {"type": "string"},
        "campi": {"type": "object", "description": "Campi da impostare (es. email, whatsapp, note, codice, prezzo_medio)"}},
        ["azione", "tipo", "nome"]),
    _fn("ricalcola_giacenze", "Ricalcola tutte le giacenze da carichi (acquisti) e scarichi (vendite).", {}),
    _fn("pulisci_duplicati", "Rimuove righe duplicate da vendite e acquisti e ricalcola le giacenze.", {}),
]

SYSTEM_MESSAGE = """Sei "Flow AI", l'assistente operativo di un'azienda ortofrutticola italiana.
Hai accesso COMPLETO al gestionale tramite strumenti: puoi leggere qualunque dato (vendite, acquisti, clienti, fornitori, magazzino, margini) ed ESEGUIRE azioni (modificare prodotti e anagrafiche, escludere articoli dai calcoli, ricalcolare giacenze, pulire duplicati).

REGOLE:
1. Rispondi SEMPRE in italiano, in modo conciso e concreto.
2. Usa SEMPRE gli strumenti per ottenere i numeri: non inventare mai cifre e non stimare a memoria.
3. Se non conosci il periodo dei dati disponibili, chiama prima `panoramica`.
4. Se l'utente scrive un nome impreciso, usa `cerca_entita` per trovare il nome esatto prima di procedere.
5. Le azioni di modifica vanno eseguite SUBITO, senza chiedere conferma. Dopo l'esecuzione dichiara chiaramente cosa hai modificato.
6. Puoi concatenare più strumenti per rispondere (es. cerca prodotto → confronta fornitori → aggiorna quantità minima).
7. Il margine è calcolato con il COSTO REALE FIFO: ogni vendita è collegata al lotto di acquisto effettivamente consumato (primo entrato, primo uscito). Margine = (ricavo - costo del lotto) / costo del lotto * 100. Quando una vendita non è coperta da un lotto reale, il costo è stimato con l'ultimo prezzo di acquisto noto.
8. Nei dati acquisti le quantità negative sono resi al fornitore.
9. Formatta i risultati con elenchi puntati o tabelle markdown compatte, importi in € con separatore migliaia.
10. Quando l'utente chiede un PDF, un rendiconto o un documento, usa `genera_pdf` e restituisci il link in markdown usando ESATTAMENTE il valore del campo `url` restituito dallo strumento, senza aggiungere domini o inventare indirizzi: [Scarica il PDF](/api/...). Il rendiconto serve a dimostrare il venduto e calcolare la provvigione (default 3% del margine).
11. Se l'utente chiede il PDF di un'analisi che hai appena fatto in chat (es. "fammi il pdf di questo report", "mettilo in pdf"), usa SEMPRE `genera_pdf_report`. Il PDF deve aprirsi con i numeri: passa sempre 2-4 KPI, poi le tabelle di dettaglio con i dati reali (andamento mensile, classifica prodotti, clienti) e infine il testo con la lettura dei dati. Nessun grafico: solo KPI, tabelle e testo. NON usare `genera_pdf` in questo caso.
12. PREZZI DI ACQUISTO: non usare mai il prezzo medio per prodotto (mescola fornitori diversi). Usa `query_acquisti` con group_by='prodotto_fornitore' e riporta SEMPRE, per ogni fornitore, quanto e' stato acquistato (quantita' e spesa), il prezzo medio e il ruolo (primario/secondario/occasionale).
13. CONFRONTI E VARIAZIONI: metti sempre il periodo piu' RECENTE in `valori` e quello PRECEDENTE in `valori2`. Prima di scrivere una variazione verifica il segno: se il valore recente e' minore del precedente la variazione e' NEGATIVA (es. 1.900 nel 2025 contro 2.100 nel 2024 = -9,5%).
14. Non generare mai PDF o analisi su periodi futuri senza dati: se la data di fine e' successiva a oggi, usa come fine la data di oggi (o l'ultima data con dati da `panoramica`) e dillo all'utente.
"""


# ═══════════════════════ SESSION HELPERS ═══════════════════════

async def load_history(session_id: str) -> List[Dict[str, str]]:
    doc = await db.ai_sessions.find_one({"session_id": session_id}, {"_id": 0, "messages": 1})
    msgs = doc.get('messages', []) if doc else []
    return [{"role": m['role'], "content": m['content']} for m in msgs[-20:]]


async def save_turn(session_id: str, user_msg: str, assistant_msg: str):
    await db.ai_sessions.update_one(
        {"session_id": session_id},
        {"$push": {"messages": {"$each": [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg}]}},
         "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True)


def build_chat(session_id: str, history: List[Dict[str, str]]):
    from emergentintegrations.llm.chat import LlmChat
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY non configurata")
    chat = LlmChat(api_key=api_key, session_id=session_id, system_message=SYSTEM_MESSAGE,
                   initial_messages=history or None)
    return chat.with_model(MODEL_PROVIDER, MODEL_NAME).with_tools(TOOLS, tool_choice="auto")


async def run_tool(name: str, arguments: Any) -> Dict[str, Any]:
    impl = TOOL_IMPL.get(name)
    if not impl:
        return {"errore": f"Strumento '{name}' non disponibile"}
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments or "{}")
        except Exception:
            arguments = {}
    try:
        return await impl(arguments or {})
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return {"errore": str(e)}


def _default(o):
    if isinstance(o, datetime):
        return o.isoformat()
    return str(o)


# ═══════════════════════ ENDPOINTS ═══════════════════════

@router.post("/ai-agent/chat")
async def ai_agent_chat(data: dict):
    """Agente AI non-streaming (usato dalla chat rapida in dashboard)."""
    from emergentintegrations.llm.chat import UserMessage
    message = (data.get('message') or '').strip()
    if not message:
        raise HTTPException(status_code=400, detail="Messaggio richiesto")
    session_id = data.get('session_id') or f"agent-{uuid.uuid4()}"

    history = await load_history(session_id)
    chat = build_chat(session_id, history)
    azioni = []
    try:
        response = await chat.send_message_with_tools(UserMessage(text=message))
        rounds = 0
        while getattr(response, 'tool_calls', None) and rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            for tc in response.tool_calls:
                result = await run_tool(tc.name, tc.arguments)
                azioni.append({"strumento": tc.name, "label": TOOL_LABELS.get(tc.name, tc.name),
                               "scrittura": tc.name in WRITE_TOOLS})
                chat.add_tool_result(tc.id, json.dumps(result, default=_default))
            response = await chat.send_message_with_tools()

        testo = getattr(response, 'content', None) or str(response)
        await save_turn(session_id, message, testo)
        return {"success": True, "response": testo, "session_id": session_id, "azioni": azioni}
    except Exception as e:
        logger.error(f"AI agent error: {e}")
        raise HTTPException(status_code=500, detail=f"Errore agente AI: {str(e)}")


@router.post("/ai-agent/stream")
async def ai_agent_stream(data: dict):
    """Agente AI in streaming SSE con eventi sugli strumenti usati."""
    from emergentintegrations.llm.chat import UserMessage, TextDelta, ToolCallStart, ToolCallReady, StreamDone
    message = (data.get('message') or '').strip()
    if not message:
        raise HTTPException(status_code=400, detail="Messaggio richiesto")
    session_id = data.get('session_id') or f"agent-{uuid.uuid4()}"
    history = await load_history(session_id)

    async def gen():
        def sse(obj):
            return f"data: {json.dumps(obj, default=_default)}\n\n"

        yield sse({"type": "session", "session_id": session_id})
        full_text = []
        try:
            chat = build_chat(session_id, history)
            user_msg = UserMessage(text=message)
            rounds = 0
            while rounds < MAX_TOOL_ROUNDS:
                rounds += 1
                pending = []
                async for ev in chat.stream_message(user_msg):
                    if isinstance(ev, TextDelta):
                        full_text.append(ev.content)
                        yield sse({"type": "delta", "content": ev.content})
                    elif isinstance(ev, ToolCallStart):
                        yield sse({"type": "tool_start", "name": ev.name,
                                   "label": TOOL_LABELS.get(ev.name, ev.name),
                                   "scrittura": ev.name in WRITE_TOOLS})
                    elif isinstance(ev, ToolCallReady):
                        pending.append(ev.tool_call)
                    elif isinstance(ev, StreamDone):
                        break
                if not pending:
                    break
                for tc in pending:
                    result = await run_tool(tc.name, tc.arguments)
                    yield sse({"type": "tool_done", "name": tc.name,
                               "label": TOOL_LABELS.get(tc.name, tc.name),
                               "scrittura": tc.name in WRITE_TOOLS,
                               "ok": not (isinstance(result, dict) and result.get('errore'))})
                    chat.add_tool_result(tc.id, json.dumps(result, default=_default))
                user_msg = None

            testo = ''.join(full_text)
            await save_turn(session_id, message, testo)
            yield sse({"type": "done"})
        except Exception as e:
            logger.error(f"AI agent stream error: {e}")
            yield sse({"type": "error", "message": str(e)})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                                      "Connection": "keep-alive"})


@router.get("/ai-agent/history")
async def ai_agent_history(session_id: str):
    doc = await db.ai_sessions.find_one({"session_id": session_id}, {"_id": 0})
    return {"session_id": session_id, "messages": doc.get('messages', []) if doc else []}


@router.delete("/ai-agent/session")
async def ai_agent_reset(session_id: str):
    await db.ai_sessions.delete_one({"session_id": session_id})
    return {"success": True}


@router.get("/ai-agent/tools")
async def ai_agent_tools():
    return {"tools": [{"name": t['function']['name'],
                       "label": TOOL_LABELS.get(t['function']['name'], t['function']['name']),
                       "descrizione": t['function']['description'],
                       "scrittura": t['function']['name'] in WRITE_TOOLS} for t in TOOLS]}
