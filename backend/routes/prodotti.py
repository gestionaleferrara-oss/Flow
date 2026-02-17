from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any

from database import db
from models import Prodotto, ProdottoCreate
from utils import serialize_doc

router = APIRouter()


@router.get("/prodotti/search")
async def search_prodotti(q: str = "", limit: int = 30):
    """Fast search with avg selling price"""
    if not q or len(q.strip()) == 0:
        return []

    search_term = q.strip()
    query = {
        "$or": [
            {"nome": {"$regex": search_term, "$options": "i"}},
            {"codice": {"$regex": search_term, "$options": "i"}}
        ]
    }
    prodotti = await db.prodotti.find(query, {"_id": 0}).limit(limit).to_list(limit)

    if prodotti:
        nomi = [p.get('nome', '') for p in prodotti if p.get('nome')]
        pipeline = [
            {"$match": {"prodotto_nome": {"$in": nomi}, "prezzo_unitario": {"$gt": 0}}},
            {"$group": {"_id": "$prodotto_nome", "prezzo_medio": {"$avg": "$prezzo_unitario"}}}
        ]
        prezzi = await db.vendite.aggregate(pipeline).to_list(len(nomi))
        prezzi_map = {p['_id']: round(p['prezzo_medio'], 2) for p in prezzi}
        for p in prodotti:
            p['prezzo_vendita_medio'] = prezzi_map.get(p.get('nome', ''), 0)

    return prodotti


@router.get("/prodotti", response_model=List[Prodotto])
async def get_prodotti(
    search: Optional[str] = None, limit: int = 100, skip: int = 0,
    sort_by: str = "nome", sort_order: int = 1,
    filter_type: Optional[str] = None
):
    query = {}
    if search:
        query["nome"] = {"$regex": search, "$options": "i"}
    
    # Handle filter types for inventory page
    if filter_type == "ordinare":
        # Products under minimum quantity
        query["$expr"] = {"$and": [
            {"$gt": ["$quantita_minima", 0]},
            {"$lte": ["$quantita", "$quantita_minima"]}
        ]}
    elif filter_type == "scadenza":
        # Products with expiry date set
        query["scadenza"] = {"$exists": True, "$ne": "", "$ne": None}
    
    prodotti = await db.prodotti.find(query, {"_id": 0}).sort(sort_by, sort_order).skip(skip).limit(limit).to_list(limit)
    return prodotti


async def get_prodotti_stats():
    """Shared stats function used by both /prodotti/stats and /dashboard"""
    prodotti = await db.prodotti.find({}, {"_id": 0}).to_list(10000)
    total = len(prodotti)
    valore_totale = sum(p.get('quantita', 0) * p.get('prezzo_medio', 0) for p in prodotti)
    sotto_scorta = sum(1 for p in prodotti if p.get('quantita_minima', 0) > 0 and p.get('quantita', 0) <= p.get('quantita_minima', 0))
    scadenza_count = sum(1 for p in prodotti if p.get('scadenza'))
    return {
        "totaleProdotti": total,
        "valoreScorte": round(valore_totale, 2),
        "sottoScorta": sotto_scorta,
        "scadenza_count": scadenza_count
    }


@router.get("/prodotti/stats")
async def get_prodotti_stats_endpoint():
    return await get_prodotti_stats()


@router.post("/prodotti", response_model=Prodotto)
async def create_prodotto(data: ProdottoCreate):
    prodotto = Prodotto(**data.model_dump())
    doc = serialize_doc(prodotto.model_dump())
    await db.prodotti.insert_one(doc)
    return prodotto


@router.put("/prodotti/{prodotto_id}")
async def update_prodotto(prodotto_id: str, data: Dict[str, Any]):
    allowed_fields = ['nome', 'codice', 'quantita', 'kg_per_pezzo', 'imballo', 'prezzo_medio', 'valore_scorte', 'scadenza', 'quantita_minima']
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    if 'quantita' in update_data and 'prezzo_medio' in update_data:
        update_data['valore_scorte'] = round(update_data['quantita'] * update_data['prezzo_medio'], 2)
    result = await db.prodotti.update_one({"id": prodotto_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    updated = await db.prodotti.find_one({"id": prodotto_id}, {"_id": 0})
    return updated


@router.delete("/prodotti/{prodotto_id}")
async def delete_prodotto(prodotto_id: str):
    result = await db.prodotti.delete_one({"id": prodotto_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    return {"message": "Prodotto eliminato"}


@router.post("/prodotti/recalculate-quantities")
async def recalculate_quantities():
    await db.prodotti.update_many({}, {"$set": {"quantita": 0}})
    prodotti = await db.prodotti.find({}, {"_id": 0, "nome": 1}).to_list(10000)
    for p in prodotti:
        nome = p.get('nome', '')
        if not nome:
            continue
        vendite = await db.vendite.find({"prodotto_nome": nome}, {"_id": 0, "quantita": 1, "movimento": 1}).to_list(100000)
        ordini = await db.ordini.find({"prodotto_nome": nome}, {"_id": 0, "quantita": 1}).to_list(100000)
        total_in = sum(abs(o.get('quantita', 0)) for o in ordini)
        total_out = sum(abs(v.get('quantita', 0)) for v in vendite if v.get('movimento', '').upper() == 'SCARICO')
        total_reso = sum(abs(v.get('quantita', 0)) for v in vendite if v.get('movimento', '').upper() == 'CARICO')
        new_qty = total_in + total_reso - total_out
        await db.prodotti.update_one({"nome": nome}, {"$set": {"quantita": round(new_qty, 2)}})
    return {"message": "Quantità ricalcolate", "prodotti_aggiornati": len(prodotti)}


@router.get("/prodotti/{prodotto_nome:path}/analisi")
async def get_prodotto_analisi(prodotto_nome: str, periodo: str = "all"):
    from urllib.parse import unquote
    from datetime import datetime, timedelta
    
    prodotto_nome = unquote(prodotto_nome)
    now = datetime.now()
    
    # Calculate date filter based on periodo
    date_filter_start = None
    date_filter_end = None
    
    if periodo == "prev_month":
        first_of_this_month = now.replace(day=1)
        last_day_prev_month = first_of_this_month - timedelta(days=1)
        first_of_prev_month = last_day_prev_month.replace(day=1)
        date_filter_start = first_of_prev_month.strftime("%Y-%m-%d")
        date_filter_end = last_day_prev_month.strftime("%Y-%m-%d")
    elif periodo == "1m":
        date_filter_start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    elif periodo == "3m":
        date_filter_start = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    elif periodo == "6m":
        date_filter_start = (now - timedelta(days=180)).strftime("%Y-%m-%d")
    
    query = {"prodotto_nome": prodotto_nome}
    if date_filter_start:
        if date_filter_end:
            query["data"] = {"$gte": date_filter_start, "$lte": date_filter_end}
        else:
            query["data"] = {"$gte": date_filter_start}
    
    vendite = await db.vendite.find(query, {"_id": 0}).to_list(10000)
    if not vendite:
        return {"messaggio": "Nessuna vendita trovata", "fatturatoMensile": 0, "mediaMensile": 0, "prezzoMedioVendita": 0, "clientiUnici": 0, "topClienti": [], "venditeMensili": [], "totale_venduto": 0, "quantita_venduta": 0, "prezzo_medio": 0, "numero_clienti": 0}
    totale_fatturato = sum(abs(v.get('totale', 0)) for v in vendite)
    totale_qty = sum(abs(v.get('quantita', 0)) for v in vendite)
    clienti_set = set(v.get('cliente_nome', '') for v in vendite if v.get('cliente_nome'))
    mesi = set(v.get('data', '')[:7] for v in vendite if v.get('data'))
    num_mesi = max(len(mesi), 1)
    # Prezzo medio ponderato = totale fatturato / quantità totale
    prezzo_medio = totale_fatturato / totale_qty if totale_qty > 0 else 0
    clienti_fatturato = {}
    for v in vendite:
        c = v.get('cliente_nome', '')
        if c:
            clienti_fatturato[c] = clienti_fatturato.get(c, 0) + abs(v.get('totale', 0))
    top_clienti = [{"nome": k, "totale": round(v, 2)} for k, v in sorted(clienti_fatturato.items(), key=lambda x: x[1], reverse=True)[:10]]
    vendite_mensili = {}
    for v in vendite:
        mese = v.get('data', '')[:7]
        vendite_mensili[mese] = vendite_mensili.get(mese, 0) + abs(v.get('totale', 0))
    mensili = [{"mese": k, "totale": round(v, 2)} for k, v in sorted(vendite_mensili.items())]
    return {
        "totale_venduto": round(totale_fatturato, 2),
        "quantita_venduta": round(totale_qty, 2),
        "prezzo_medio": round(prezzo_medio, 4),
        "numero_clienti": len(clienti_set),
        "fatturatoMensile": round(totale_fatturato / num_mesi, 2),
        "mediaMensile": round(totale_qty / num_mesi, 2),
        "prezzoMedioVendita": round(prezzo_medio, 4),
        "clientiUnici": len(clienti_set),
        "topClienti": top_clienti,
        "venditeMensili": mensili
    }


@router.get("/prodotti/{prodotto_nome:path}/analisi-acquisti")
async def get_prodotto_analisi_acquisti(prodotto_nome: str, periodo: str = "all"):
    from urllib.parse import unquote
    from datetime import datetime, timedelta
    
    prodotto_nome = unquote(prodotto_nome)
    now = datetime.now()
    
    # Calculate date filter based on periodo
    date_filter_start = None
    date_filter_end = None
    
    if periodo == "prev_month":
        first_of_this_month = now.replace(day=1)
        last_day_prev_month = first_of_this_month - timedelta(days=1)
        first_of_prev_month = last_day_prev_month.replace(day=1)
        date_filter_start = first_of_prev_month.strftime("%Y-%m-%d")
        date_filter_end = last_day_prev_month.strftime("%Y-%m-%d")
    elif periodo == "1m":
        date_filter_start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    elif periodo == "3m":
        date_filter_start = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    elif periodo == "6m":
        date_filter_start = (now - timedelta(days=180)).strftime("%Y-%m-%d")
    
    query = {"prodotto_nome": prodotto_nome}
    if date_filter_start:
        if date_filter_end:
            query["data"] = {"$gte": date_filter_start, "$lte": date_filter_end}
        else:
            query["data"] = {"$gte": date_filter_start}
    
    ordini = await db.ordini.find(query, {"_id": 0}).to_list(10000)
    if not ordini:
        return {"messaggio": "Nessun acquisto trovato", "spesoMensile": 0, "mediaMensile": 0, "prezzoMedioAcquisto": 0, "fornitoriUnici": 0, "topFornitori": [], "acquistiMensili": [], "totale_acquistato": 0, "quantita_acquistata": 0, "costo_medio": 0, "numero_fornitori": 0, "variazionePrezzi": []}
    totale_speso = sum(abs(o.get('totale', 0)) for o in ordini)
    totale_qty = sum(abs(o.get('quantita', 0)) for o in ordini)
    fornitori_set = set(o.get('fornitore_nome', '') for o in ordini if o.get('fornitore_nome'))
    mesi = set(o.get('data', '')[:7] for o in ordini if o.get('data'))
    num_mesi = max(len(mesi), 1)
    # Costo medio ponderato = totale speso / quantità totale
    prezzo_medio = totale_speso / totale_qty if totale_qty > 0 else 0
    fornitori_spesa = {}
    for o in ordini:
        f = o.get('fornitore_nome', '')
        if f:
            fornitori_spesa[f] = fornitori_spesa.get(f, 0) + abs(o.get('totale', 0))
    top_fornitori = [{"nome": k, "totale": round(v, 2)} for k, v in sorted(fornitori_spesa.items(), key=lambda x: x[1], reverse=True)[:10]]
    acquisti_mensili = {}
    for o in ordini:
        mese = o.get('data', '')[:7]
        acquisti_mensili[mese] = acquisti_mensili.get(mese, 0) + abs(o.get('totale', 0))
    mensili = [{"mese": k, "totale": round(v, 2)} for k, v in sorted(acquisti_mensili.items())]
    mesi_sorted = sorted(mesi) if mesi else []
    variazione_prezzi = []
    for m in mesi_sorted:
        ordini_mese = [o for o in ordini if o.get('data', '').startswith(m)]
        prezzi_mese = [o.get('prezzo_unitario', 0) for o in ordini_mese if o.get('prezzo_unitario', 0) > 0]
        pm = sum(prezzi_mese) / len(prezzi_mese) if prezzi_mese else 0
        if pm > 0:
            variazione_prezzi.append({"mese": m, "prezzo_medio": round(pm, 4)})
    return {
        "totale_acquistato": round(totale_speso, 2),
        "quantita_acquistata": round(totale_qty, 2),
        "costo_medio": round(prezzo_medio, 4),
        "numero_fornitori": len(fornitori_set),
        "spesoMensile": round(totale_speso / num_mesi, 2),
        "mediaMensile": round(totale_qty / num_mesi, 2),
        "prezzoMedioAcquisto": round(prezzo_medio, 4),
        "fornitoriUnici": len(fornitori_set),
        "topFornitori": top_fornitori,
        "acquistiMensili": mensili,
        "variazionePrezzi": variazione_prezzi
    }


@router.get("/prodotti/{prodotto_nome:path}/storico-clienti")
async def get_prodotto_storico_clienti(prodotto_nome: str):
    """
    Get price history and last 3 sales per customer for a product.
    Also calculates average margin per customer.
    """
    from urllib.parse import unquote
    from datetime import datetime
    
    prodotto_nome = unquote(prodotto_nome)
    
    # Get all sales for this product
    vendite = await db.vendite.find(
        {"prodotto_nome": prodotto_nome},
        {"_id": 0, "cliente_nome": 1, "data": 1, "quantita": 1, "prezzo_unitario": 1, "totale": 1}
    ).sort("data", -1).to_list(10000)
    
    if not vendite:
        return {"clienti": [], "storicoPrezzi": [], "prezzoMedioVendita": 0, "costoMedioAcquisto": 0}
    
    # Get purchase cost for margin calculation
    ordini = await db.ordini.find(
        {"prodotto_nome": prodotto_nome, "prezzo_unitario": {"$gt": 0}},
        {"_id": 0, "prezzo_unitario": 1}
    ).to_list(1000)
    
    costo_medio = 0
    if ordini:
        prezzi_acquisto = [o.get('prezzo_unitario', 0) for o in ordini if o.get('prezzo_unitario', 0) > 0]
        costo_medio = sum(prezzi_acquisto) / len(prezzi_acquisto) if prezzi_acquisto else 0
    
    # Group sales by customer
    clienti_vendite = {}
    for v in vendite:
        cliente = v.get('cliente_nome', '')
        if not cliente or cliente.upper() in ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']:
            continue
        if cliente not in clienti_vendite:
            clienti_vendite[cliente] = []
        clienti_vendite[cliente].append(v)
    
    # Build response with last 3 sales per customer + margin
    clienti_result = []
    for cliente, vendite_cliente in clienti_vendite.items():
        ultime_3 = vendite_cliente[:3]  # Already sorted by date desc
        
        # Calculate totals for this customer
        totale_venduto = sum(abs(v.get('totale', 0)) for v in vendite_cliente)
        totale_qty = sum(abs(v.get('quantita', 0)) for v in vendite_cliente)
        prezzo_medio_cliente = totale_venduto / totale_qty if totale_qty > 0 else 0
        
        # Calculate margin
        margine_percentuale = 0
        if costo_medio > 0 and prezzo_medio_cliente > 0:
            margine_percentuale = ((prezzo_medio_cliente - costo_medio) / costo_medio) * 100
        
        clienti_result.append({
            "nome": cliente,
            "ultime_vendite": [
                {
                    "data": v.get('data', ''),
                    "quantita": abs(v.get('quantita', 0)),
                    "prezzo_unitario": v.get('prezzo_unitario', 0),
                    "totale": abs(v.get('totale', 0))
                }
                for v in ultime_3
            ],
            "totale_venduto": round(totale_venduto, 2),
            "quantita_totale": round(totale_qty, 2),
            "prezzo_medio": round(prezzo_medio_cliente, 4),
            "margine_percentuale": round(margine_percentuale, 1),
            "num_acquisti": len(vendite_cliente)
        })
    
    # Sort by total sold
    clienti_result.sort(key=lambda x: x['totale_venduto'], reverse=True)
    
    # Price history by month
    prezzi_mensili = {}
    for v in vendite:
        mese = v.get('data', '')[:7]
        prezzo = v.get('prezzo_unitario', 0)
        if mese and prezzo > 0:
            if mese not in prezzi_mensili:
                prezzi_mensili[mese] = []
            prezzi_mensili[mese].append(prezzo)
    
    storico_prezzi = []
    for mese in sorted(prezzi_mensili.keys()):
        prezzi = prezzi_mensili[mese]
        storico_prezzi.append({
            "mese": mese,
            "prezzo_medio": round(sum(prezzi) / len(prezzi), 4),
            "prezzo_min": round(min(prezzi), 4),
            "prezzo_max": round(max(prezzi), 4)
        })
    
    # Overall average selling price
    tutti_prezzi = [v.get('prezzo_unitario', 0) for v in vendite if v.get('prezzo_unitario', 0) > 0]
    prezzo_medio_vendita = sum(tutti_prezzi) / len(tutti_prezzi) if tutti_prezzi else 0
    
    return {
        "clienti": clienti_result[:20],  # Top 20 customers
        "storicoPrezzi": storico_prezzi,
        "prezzoMedioVendita": round(prezzo_medio_vendita, 4),
        "costoMedioAcquisto": round(costo_medio, 4),
        "margineGlobale": round(((prezzo_medio_vendita - costo_medio) / costo_medio * 100) if costo_medio > 0 else 0, 1)
    }


@router.get("/clienti/{cliente_id}/prodotti-acquistati")
async def get_cliente_prodotti_acquistati(cliente_id: str, search: str = ""):
    """
    Get products purchased by a specific customer, with optional search filter.
    Returns last purchase info for each product.
    """
    # Get cliente name from ID
    cliente = await db.clienti.find_one({"id": cliente_id}, {"_id": 0, "nome": 1})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    cliente_nome = cliente.get('nome', '')
    
    # Build query
    query = {"cliente_nome": cliente_nome}
    if search:
        query["prodotto_nome"] = {"$regex": search, "$options": "i"}
    
    # Get all sales for this customer
    vendite = await db.vendite.find(
        query,
        {"_id": 0, "prodotto_nome": 1, "data": 1, "quantita": 1, "prezzo_unitario": 1, "totale": 1}
    ).sort("data", -1).to_list(10000)
    
    if not vendite:
        return {"prodotti": [], "cliente_nome": cliente_nome}
    
    # Group by product
    prodotti_vendite = {}
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        if not prod:
            continue
        if prod not in prodotti_vendite:
            prodotti_vendite[prod] = []
        prodotti_vendite[prod].append(v)
    
    # Build response
    prodotti_result = []
    for prodotto, vendite_prod in prodotti_vendite.items():
        ultima_vendita = vendite_prod[0]  # Most recent
        totale = sum(abs(v.get('totale', 0)) for v in vendite_prod)
        qty_totale = sum(abs(v.get('quantita', 0)) for v in vendite_prod)
        
        prodotti_result.append({
            "prodotto_nome": prodotto,
            "ultima_data": ultima_vendita.get('data', ''),
            "ultimo_prezzo": ultima_vendita.get('prezzo_unitario', 0),
            "ultima_quantita": abs(ultima_vendita.get('quantita', 0)),
            "totale_acquistato": round(totale, 2),
            "quantita_totale": round(qty_totale, 2),
            "num_acquisti": len(vendite_prod),
            "ultime_3": [
                {
                    "data": v.get('data', ''),
                    "quantita": abs(v.get('quantita', 0)),
                    "prezzo_unitario": v.get('prezzo_unitario', 0),
                    "totale": abs(v.get('totale', 0))
                }
                for v in vendite_prod[:3]
            ]
        })
    
    # Sort by most recent purchase
    prodotti_result.sort(key=lambda x: x['ultima_data'], reverse=True)
    
    return {
        "prodotti": prodotti_result,
        "cliente_nome": cliente_nome,
        "totale_prodotti": len(prodotti_result)
    }


@router.get("/clienti-by-name/{cliente_nome:path}/prodotti-acquistati")
async def get_cliente_prodotti_by_name(cliente_nome: str, search: str = ""):
    """
    Get products purchased by a customer (by name), with optional search filter.
    """
    from urllib.parse import unquote
    cliente_nome = unquote(cliente_nome)
    
    # Build query
    query = {"cliente_nome": cliente_nome}
    if search:
        query["prodotto_nome"] = {"$regex": search, "$options": "i"}
    
    # Get all sales for this customer
    vendite = await db.vendite.find(
        query,
        {"_id": 0, "prodotto_nome": 1, "data": 1, "quantita": 1, "prezzo_unitario": 1, "totale": 1}
    ).sort("data", -1).to_list(10000)
    
    if not vendite:
        return {"prodotti": [], "cliente_nome": cliente_nome, "totale_prodotti": 0}
    
    # Group by product
    prodotti_vendite = {}
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        if not prod:
            continue
        if prod not in prodotti_vendite:
            prodotti_vendite[prod] = []
        prodotti_vendite[prod].append(v)
    
    # Build response
    prodotti_result = []
    for prodotto, vendite_prod in prodotti_vendite.items():
        ultima_vendita = vendite_prod[0]
        totale = sum(abs(v.get('totale', 0)) for v in vendite_prod)
        qty_totale = sum(abs(v.get('quantita', 0)) for v in vendite_prod)
        
        prodotti_result.append({
            "prodotto_nome": prodotto,
            "ultima_data": ultima_vendita.get('data', ''),
            "ultimo_prezzo": ultima_vendita.get('prezzo_unitario', 0),
            "ultima_quantita": abs(ultima_vendita.get('quantita', 0)),
            "totale_acquistato": round(totale, 2),
            "quantita_totale": round(qty_totale, 2),
            "num_acquisti": len(vendite_prod),
            "ultime_3": [
                {
                    "data": v.get('data', ''),
                    "quantita": abs(v.get('quantita', 0)),
                    "prezzo_unitario": v.get('prezzo_unitario', 0),
                    "totale": abs(v.get('totale', 0))
                }
                for v in vendite_prod[:3]
            ]
        })
    
    prodotti_result.sort(key=lambda x: x['ultima_data'], reverse=True)
    
    return {
        "prodotti": prodotti_result,
        "cliente_nome": cliente_nome,
        "totale_prodotti": len(prodotti_result)
    }


