from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from database import db
from models import Cliente, ClienteCreate, Fornitore, FornitoreCreate, Ordine, OrdineCreate
from utils import serialize_doc

router = APIRouter()

# ===== Clienti =====

@router.get("/clienti")
async def get_clienti(search: Optional[str] = None, anno: Optional[str] = None, limit: int = 100, skip: int = 0):
    """Get clients with calculated total revenue, optionally filtered by year"""
    query = {}
    if search:
        query["nome"] = {"$regex": search, "$options": "i"}
    clienti = await db.clienti.find(query, {"_id": 0}).sort("nome", 1).skip(skip).limit(limit).to_list(limit)

    # Get available years from vendite
    all_dates = await db.vendite.distinct("data")
    anni_disponibili = sorted(set(d[:4] for d in all_dates if d and len(d) >= 4), reverse=True)

    # Calculate fatturato_totale for each client from vendite
    for cliente in clienti:
        nome = cliente.get('nome', '')
        if nome:
            match_filter = {"cliente_nome": nome}
            if anno:
                match_filter["data"] = {"$regex": f"^{anno}"}
            pipeline = [
                {"$match": match_filter},
                {"$group": {"_id": None, "totale": {"$sum": {"$abs": "$totale"}}}}
            ]
            result = await db.vendite.aggregate(pipeline).to_list(1)
            cliente['fatturato_totale'] = result[0]['totale'] if result else 0
        else:
            cliente['fatturato_totale'] = 0

    return {"clienti": clienti, "anni_disponibili": anni_disponibili}


@router.post("/clienti", response_model=Cliente)
async def create_cliente(data: ClienteCreate):
    cliente = Cliente(**data.model_dump())
    doc = serialize_doc(cliente.model_dump())
    await db.clienti.insert_one(doc)
    return cliente


@router.get("/clienti/{cliente_id}")
async def get_cliente(cliente_id: str):
    cliente = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    return cliente


@router.put("/clienti/{cliente_id}")
async def update_cliente(cliente_id: str, data: ClienteCreate):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    result = await db.clienti.update_one({"id": cliente_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    updated = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    return updated


@router.delete("/clienti/{cliente_id}")
async def delete_cliente(cliente_id: str):
    result = await db.clienti.delete_one({"id": cliente_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    return {"message": "Cliente eliminato"}


@router.get("/clienti/{cliente_id}/analisi")
async def get_cliente_analisi(cliente_id: str, periodo: str = "mese"):
    """
    Analisi cliente con periodo selezionabile.
    periodo: 'mese' (default), '3mesi', '6mesi', 'anno', 'tutto'
    """
    from datetime import datetime, timedelta
    
    cliente = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    nome = cliente.get('nome', '')
    
    # Calculate date range based on periodo
    oggi = datetime.now()
    if periodo == "mese":
        start_date = oggi.replace(day=1).strftime("%Y-%m-%d")
    elif periodo == "3mesi":
        start_date = (oggi - timedelta(days=90)).strftime("%Y-%m-%d")
    elif periodo == "6mesi":
        start_date = (oggi - timedelta(days=180)).strftime("%Y-%m-%d")
    elif periodo == "anno":
        start_date = (oggi - timedelta(days=365)).strftime("%Y-%m-%d")
    else:  # tutto
        start_date = "2000-01-01"
    
    end_date = oggi.strftime("%Y-%m-%d")
    
    # Get all sales for this client in period
    query = {"cliente_nome": nome, "data": {"$gte": start_date, "$lte": end_date}}
    vendite = await db.vendite.find(query, {"_id": 0}).sort("data", -1).to_list(10000)
    
    totale_speso = sum(abs(v.get('totale', 0)) for v in vendite)
    
    # Products purchased
    prodotti_acquistati = {}
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        prodotti_acquistati[prod] = prodotti_acquistati.get(prod, 0) + abs(v.get('totale', 0))
    top_prodotti = [{"nome": k, "totale": round(v, 2)} for k, v in sorted(prodotti_acquistati.items(), key=lambda x: x[1], reverse=True)[:10]]
    
    # Count unique visits (orders) by date
    visite_per_data = {}
    for v in vendite:
        data = v.get('data', '')
        if data:
            visite_per_data[data] = visite_per_data.get(data, 0) + abs(v.get('totale', 0))
    
    num_visite = len(visite_per_data)
    
    # List of visits with totals
    lista_visite = [{"data": data, "totale": round(tot, 2)} 
                    for data, tot in sorted(visite_per_data.items(), reverse=True)[:20]]
    
    # Last visit
    ultimo_ordine = lista_visite[0]["data"] if lista_visite else "N/A"
    
    # Average per visit
    media_ordine = totale_speso / num_visite if num_visite > 0 else 0
    
    # Monthly breakdown
    vendite_mensili = {}
    for v in vendite:
        mese = v.get('data', '')[:7]
        vendite_mensili[mese] = vendite_mensili.get(mese, 0) + abs(v.get('totale', 0))
    mensili = [{"mese": k, "totale": round(v, 2)} for k, v in sorted(vendite_mensili.items())]
    
    # Top products as string for old compatibility
    prodotti_str = ", ".join([p["nome"] for p in top_prodotti[:3]]) if top_prodotti else "Nessun dato"
    
    return {
        "cliente": cliente,
        "totaleSpeso": round(totale_speso, 2),
        "totaleSpesoMese": round(totale_speso, 2),  # Alias for frontend
        "numOrdini": num_visite,
        "ordiniMese": num_visite,  # Alias for frontend
        "ultimoOrdine": ultimo_ordine,
        "mediaOrdine": round(media_ordine, 2),
        "topProdotti": top_prodotti,
        "prodottiPiuAcquistati": prodotti_str,
        "venditeMensili": mensili,
        "listaVisite": lista_visite,
        "periodo": periodo,
        "dataInizio": start_date,
        "dataFine": end_date
    }


@router.get("/clienti-search")
async def search_clienti_quick(search: str, limit: int = 10):
    """
    Quick search for clients with summary data for search modal.
    Returns basic info + total revenue + last order date.
    """
    if not search or len(search) < 1:
        return []
    
    query = {"nome": {"$regex": search, "$options": "i"}}
    clienti = await db.clienti.find(query, {"_id": 0}).sort("nome", 1).limit(limit).to_list(limit)
    
    results = []
    for cliente in clienti:
        nome = cliente.get('nome', '')
        
        # Get total revenue
        pipeline = [
            {"$match": {"cliente_nome": nome}},
            {"$group": {"_id": None, "totale": {"$sum": {"$abs": "$totale"}}, "count": {"$sum": 1}}}
        ]
        agg_result = await db.vendite.aggregate(pipeline).to_list(1)
        fatturato = agg_result[0]['totale'] if agg_result else 0
        num_ordini = agg_result[0]['count'] if agg_result else 0
        
        # Get last order date
        ultima_vendita = await db.vendite.find_one(
            {"cliente_nome": nome},
            {"_id": 0, "data": 1}
        , sort=[("data", -1)])
        
        results.append({
            "id": cliente.get('id'),
            "nome": nome,
            "codice": cliente.get('codice', ''),
            "fatturato_totale": round(fatturato, 2),
            "num_ordini": num_ordini,
            "ultimo_ordine": ultima_vendita.get('data') if ultima_vendita else None
        })
    
    return results


@router.get("/clienti/{cliente_id}/quick-view")
async def get_cliente_quick_view(cliente_id: str):
    """
    Get quick view data for a client: last sales and top 3 products.
    Used in search modal.
    """
    cliente = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    nome = cliente.get('nome', '')
    
    # Get last 5 sales
    ultime_vendite = await db.vendite.find(
        {"cliente_nome": nome},
        {"_id": 0, "data": 1, "prodotto_nome": 1, "quantita": 1, "prezzo_unitario": 1, "totale": 1}
    ).sort("data", -1).limit(5).to_list(5)
    
    # Get all sales for top products
    all_vendite = await db.vendite.find(
        {"cliente_nome": nome},
        {"_id": 0, "prodotto_nome": 1, "totale": 1, "quantita": 1}
    ).to_list(10000)
    
    # Calculate top products by revenue
    prodotti_stats = {}
    for v in all_vendite:
        prod = v.get('prodotto_nome', '')
        if prod:
            if prod not in prodotti_stats:
                prodotti_stats[prod] = {'totale': 0, 'quantita': 0, 'ordini': 0}
            prodotti_stats[prod]['totale'] += abs(v.get('totale', 0))
            prodotti_stats[prod]['quantita'] += abs(v.get('quantita', 0))
            prodotti_stats[prod]['ordini'] += 1
    
    top_prodotti = sorted(
        [{'nome': k, **v} for k, v in prodotti_stats.items()],
        key=lambda x: x['totale'],
        reverse=True
    )[:3]
    
    # Total stats
    fatturato_totale = sum(abs(v.get('totale', 0)) for v in all_vendite)
    num_ordini = len(set(v.get('data', '') for v in all_vendite))
    
    return {
        "cliente": cliente,
        "fatturato_totale": round(fatturato_totale, 2),
        "num_ordini": num_ordini,
        "ultime_vendite": [
            {
                "data": v.get('data', ''),
                "prodotto": v.get('prodotto_nome', ''),
                "quantita": abs(v.get('quantita', 0)),
                "prezzo_unitario": v.get('prezzo_unitario', 0),
                "totale": abs(v.get('totale', 0))
            }
            for v in ultime_vendite
        ],
        "top_prodotti": [
            {
                "nome": p['nome'],
                "totale": round(p['totale'], 2),
                "quantita": round(p['quantita'], 2),
                "ordini": p['ordini']
            }
            for p in top_prodotti
        ]
    }


@router.get("/clienti-by-name/{cliente_nome}/quick-view")
async def get_cliente_quick_view_by_name(cliente_nome: str, periodo: str = "3m"):
    """
    Get quick view data for a client by name.
    Period: 1m, 3m, 6m, all
    """
    from urllib.parse import unquote
    from datetime import datetime, timedelta
    
    cliente_nome = unquote(cliente_nome)
    
    cliente = await db.clienti.find_one({"nome": cliente_nome}, {"_id": 0})
    if not cliente:
        # Create a minimal cliente object for clients not in the database
        cliente = {"nome": cliente_nome, "id": None}
    
    nome = cliente_nome
    
    # Calculate date filter based on period
    now = datetime.now()
    if periodo == "prev_month":
        # Previous month: from 1st of last month to last day of last month
        first_of_this_month = now.replace(day=1)
        last_day_prev_month = first_of_this_month - timedelta(days=1)
        first_of_prev_month = last_day_prev_month.replace(day=1)
        date_filter_start = first_of_prev_month.strftime("%Y-%m-%d")
        date_filter_end = last_day_prev_month.strftime("%Y-%m-%d")
    elif periodo == "1m":
        date_filter_start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        date_filter_end = None
    elif periodo == "3m":
        date_filter_start = (now - timedelta(days=90)).strftime("%Y-%m-%d")
        date_filter_end = None
    elif periodo == "6m":
        date_filter_start = (now - timedelta(days=180)).strftime("%Y-%m-%d")
        date_filter_end = None
    else:
        date_filter_start = None  # all time
        date_filter_end = None
    
    # Build query with optional date filter
    base_query = {"cliente_nome": nome}
    if date_filter_start:
        if date_filter_end:
            base_query["data"] = {"$gte": date_filter_start, "$lte": date_filter_end}
        else:
            base_query["data"] = {"$gte": date_filter_start}
    
    # Get last 5 sales (always most recent)
    ultime_vendite = await db.vendite.find(
        {"cliente_nome": nome},
        {"_id": 0, "data": 1, "prodotto_nome": 1, "quantita": 1, "prezzo_unitario": 1, "totale": 1}
    ).sort("data", -1).limit(5).to_list(5)
    
    # Get sales within period for stats
    period_vendite = await db.vendite.find(
        base_query,
        {"_id": 0, "prodotto_nome": 1, "totale": 1, "quantita": 1, "data": 1}
    ).to_list(10000)
    
    # Calculate top products by revenue
    prodotti_stats = {}
    for v in period_vendite:
        prod = v.get('prodotto_nome', '')
        if prod:
            if prod not in prodotti_stats:
                prodotti_stats[prod] = {'totale': 0, 'quantita': 0, 'ordini': 0}
            prodotti_stats[prod]['totale'] += abs(v.get('totale', 0))
            prodotti_stats[prod]['quantita'] += abs(v.get('quantita', 0))
            prodotti_stats[prod]['ordini'] += 1
    
    top_prodotti = sorted(
        [{'nome': k, **v} for k, v in prodotti_stats.items()],
        key=lambda x: x['totale'],
        reverse=True
    )[:3]
    
    # Total stats for period
    fatturato_totale = sum(abs(v.get('totale', 0)) for v in period_vendite)
    num_ordini = len(set(v.get('data', '') for v in period_vendite))
    
    return {
        "cliente": cliente,
        "fatturato_totale": round(fatturato_totale, 2),
        "num_ordini": num_ordini,
        "periodo": periodo,
        "ultime_vendite": [
            {
                "data": v.get('data', ''),
                "prodotto": v.get('prodotto_nome', ''),
                "quantita": abs(v.get('quantita', 0)),
                "prezzo_unitario": v.get('prezzo_unitario', 0),
                "totale": abs(v.get('totale', 0))
            }
            for v in ultime_vendite
        ],
        "top_prodotti": [
            {
                "nome": p['nome'],
                "totale": round(p['totale'], 2),
                "quantita": round(p['quantita'], 2),
                "ordini": p['ordini']
            }
            for p in top_prodotti
        ]
    }


# ===== Fornitori =====

@router.get("/fornitori", response_model=List[Fornitore])
async def get_fornitori(search: Optional[str] = None, limit: int = 100, skip: int = 0):
    query = {}
    if search:
        query["nome"] = {"$regex": search, "$options": "i"}
    fornitori = await db.fornitori.find(query, {"_id": 0}).sort("nome", 1).skip(skip).limit(limit).to_list(limit)
    return fornitori


@router.post("/fornitori", response_model=Fornitore)
async def create_fornitore(data: FornitoreCreate):
    fornitore = Fornitore(**data.model_dump())
    doc = serialize_doc(fornitore.model_dump())
    await db.fornitori.insert_one(doc)
    return fornitore


@router.put("/fornitori/{fornitore_id}")
async def update_fornitore(fornitore_id: str, data: FornitoreCreate):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    result = await db.fornitori.update_one({"id": fornitore_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    updated = await db.fornitori.find_one({"id": fornitore_id}, {"_id": 0})
    return updated


@router.delete("/fornitori/{fornitore_id}")
async def delete_fornitore(fornitore_id: str):
    result = await db.fornitori.delete_one({"id": fornitore_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    return {"message": "Fornitore eliminato"}


@router.get("/fornitori-with-stats")
async def get_fornitori_with_stats(search: Optional[str] = None, anno: Optional[str] = None, limit: int = 100, skip: int = 0):
    query = {}
    if search:
        query["nome"] = {"$regex": search, "$options": "i"}
    fornitori = await db.fornitori.find(query, {"_id": 0}).sort("nome", 1).skip(skip).limit(limit).to_list(limit)

    # Get available years from ordini
    all_dates = await db.ordini.distinct("data")
    anni_set = sorted(set(d[:4] for d in all_dates if d and len(d) >= 4), reverse=True)

    result = []
    for f in fornitori:
        nome = f.get('nome', '')
        ordini_query = {"fornitore_nome": nome}
        if anno:
            ordini_query["data"] = {"$regex": f"^{anno}"}
        ordini = await db.ordini.find(ordini_query, {"_id": 0, "totale": 1, "data": 1}).to_list(10000)
        fatturato = sum(abs(o.get('totale', 0)) for o in ordini)
        ultimo_ordine = max((o.get('data', '') for o in ordini), default='') if ordini else ''
        result.append({
            **f,
            "fatturato_totale": round(fatturato, 2),
            "num_ordini": len(ordini),
            "ultimo_ordine": ultimo_ordine
        })
    return {"fornitori": result, "anni_disponibili": anni_set}


@router.put("/fornitori/{fornitore_id}/note")
async def update_fornitore_note(fornitore_id: str, data: Dict[str, Any]):
    result = await db.fornitori.update_one(
        {"id": fornitore_id},
        {"$set": {"note": data.get("note", "")}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    return {"message": "Note aggiornate"}


@router.get("/fornitori/{fornitore_nome}/prodotti")
async def get_fornitore_prodotti(fornitore_nome: str, mese: Optional[str] = None):
    from urllib.parse import unquote
    fornitore_nome = unquote(fornitore_nome)

    # Get all orders from this supplier to determine available months
    all_ordini = await db.ordini.find({"fornitore_nome": fornitore_nome}, {"_id": 0, "data": 1}).to_list(50000)
    all_months = sorted(set(o.get('data', '')[:7] for o in all_ordini if o.get('data')), reverse=True)

    # Default to latest month if not specified
    mese_selezionato = mese if mese else (all_months[0] if all_months else '')

    # Build month labels
    MESI_NOMI = {
        '01': 'Gennaio', '02': 'Febbraio', '03': 'Marzo', '04': 'Aprile',
        '05': 'Maggio', '06': 'Giugno', '07': 'Luglio', '08': 'Agosto',
        '09': 'Settembre', '10': 'Ottobre', '11': 'Novembre', '12': 'Dicembre'
    }
    mesi_disponibili = []
    for m in all_months:
        parts = m.split('-')
        label = f"{MESI_NOMI.get(parts[1], parts[1])} {parts[0]}" if len(parts) == 2 else m
        mesi_disponibili.append({"value": m, "label": label})

    # Query filtered orders
    query = {"fornitore_nome": fornitore_nome}
    if mese_selezionato:
        query["data"] = {"$regex": f"^{mese_selezionato}"}
    ordini = await db.ordini.find(query, {"_id": 0}).sort("data", -1).to_list(10000)

    acquisti = []
    totale_speso = 0
    for o in ordini:
        tot = abs(o.get('totale', 0))
        totale_speso += tot
        acquisti.append({
            "prodotto": o.get('prodotto_nome', ''),
            "quantita": abs(o.get('quantita', 0)),
            "prezzo_unitario": o.get('prezzo_unitario', 0),
            "totale": round(tot, 2),
            "data": o.get('data', '')
        })

    # Month reference label
    mese_riferimento = ''
    if mese_selezionato:
        parts = mese_selezionato.split('-')
        mese_riferimento = f"{MESI_NOMI.get(parts[1], parts[1])} {parts[0]}" if len(parts) == 2 else mese_selezionato

    return {
        "acquisti": acquisti,
        "totale_acquisti": len(acquisti),
        "totale_speso": round(totale_speso, 2),
        "mesi_disponibili": mesi_disponibili,
        "mese_selezionato": mese_selezionato,
        "mese_riferimento": mese_riferimento
    }


# ===== Ordini =====

@router.get("/ordini")
async def get_ordini(
    search: Optional[str] = None, fornitore: Optional[str] = None,
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    limit: int = 100, skip: int = 0
):
    query = {}
    if search:
        query["$or"] = [
            {"fornitore_nome": {"$regex": search, "$options": "i"}},
            {"prodotto_nome": {"$regex": search, "$options": "i"}}
        ]
    if fornitore:
        query["fornitore_nome"] = {"$regex": fornitore, "$options": "i"}
    if start_date:
        query.setdefault("data", {})["$gte"] = start_date
    if end_date:
        query.setdefault("data", {})["$lte"] = end_date
    ordini = await db.ordini.find(query, {"_id": 0}).sort("data", -1).skip(skip).limit(limit).to_list(limit)
    return ordini


@router.post("/ordini", response_model=Ordine)
async def create_ordine(data: OrdineCreate):
    totale_kg = data.quantita * data.kg_per_pezzo
    totale = data.quantita * data.prezzo_unitario
    giorni = 0
    if data.data_inizio and data.data_fine:
        try:
            d1 = datetime.strptime(data.data_inizio, "%Y-%m-%d")
            d2 = datetime.strptime(data.data_fine, "%Y-%m-%d")
            giorni = (d2 - d1).days
        except ValueError:
            pass
    ordine = Ordine(
        data=datetime.now().strftime("%Y-%m-%d"),
        fornitore_nome=data.fornitore_nome,
        prodotto_nome=data.prodotto_nome,
        quantita=data.quantita,
        kg_per_pezzo=data.kg_per_pezzo,
        totale_kg=totale_kg,
        prezzo_unitario=data.prezzo_unitario,
        totale=totale,
        data_inizio=data.data_inizio,
        data_fine=data.data_fine,
        giorni_durata=giorni
    )
    doc = serialize_doc(ordine.model_dump())
    await db.ordini.insert_one(doc)
    return ordine
