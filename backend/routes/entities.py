from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from database import db
from models import Cliente, ClienteCreate, Fornitore, FornitoreCreate, Ordine, OrdineCreate
from utils import serialize_doc

router = APIRouter()

# ===== Clienti =====

@router.get("/clienti")
async def get_clienti(search: Optional[str] = None, limit: int = 100, skip: int = 0):
    """Get clients with calculated total revenue"""
    query = {}
    if search:
        query["nome"] = {"$regex": search, "$options": "i"}
    clienti = await db.clienti.find(query, {"_id": 0}).sort("nome", 1).skip(skip).limit(limit).to_list(limit)
    
    # Calculate fatturato_totale for each client from vendite
    for cliente in clienti:
        nome = cliente.get('nome', '')
        if nome:
            # Sum all sales for this client
            pipeline = [
                {"$match": {"cliente_nome": nome}},
                {"$group": {"_id": None, "totale": {"$sum": {"$abs": "$totale"}}}}
            ]
            result = await db.vendite.aggregate(pipeline).to_list(1)
            cliente['fatturato_totale'] = result[0]['totale'] if result else 0
        else:
            cliente['fatturato_totale'] = 0
    
    return clienti


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
async def get_fornitori_with_stats(search: Optional[str] = None, limit: int = 100, skip: int = 0):
    query = {}
    if search:
        query["nome"] = {"$regex": search, "$options": "i"}
    fornitori = await db.fornitori.find(query, {"_id": 0}).sort("nome", 1).skip(skip).limit(limit).to_list(limit)
    result = []
    for f in fornitori:
        nome = f.get('nome', '')
        ordini = await db.ordini.find({"fornitore_nome": nome}, {"_id": 0, "totale": 1, "data": 1}).to_list(10000)
        totale_acquisti = sum(abs(o.get('totale', 0)) for o in ordini)
        ultimo_ordine = max((o.get('data', '') for o in ordini), default='') if ordini else ''
        result.append({
            **f,
            "totale_acquisti": round(totale_acquisti, 2),
            "num_ordini": len(ordini),
            "ultimo_ordine": ultimo_ordine
        })
    return result


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
    query = {"fornitore_nome": fornitore_nome}
    if mese:
        query["data"] = {"$regex": f"^{mese}"}
    ordini = await db.ordini.find(query, {"_id": 0}).to_list(10000)
    prodotti_dict = {}
    for o in ordini:
        prod = o.get('prodotto_nome', '')
        if prod not in prodotti_dict:
            prodotti_dict[prod] = {
                'nome': prod,
                'quantita_totale': 0,
                'totale_euro': 0,
                'num_ordini': 0,
                'prezzi': [],
                'date': []
            }
        prodotti_dict[prod]['quantita_totale'] += abs(o.get('quantita', 0))
        prodotti_dict[prod]['totale_euro'] += abs(o.get('totale', 0))
        prodotti_dict[prod]['num_ordini'] += 1
        if o.get('prezzo_unitario', 0) > 0:
            prodotti_dict[prod]['prezzi'].append(o['prezzo_unitario'])
        if o.get('data'):
            prodotti_dict[prod]['date'].append(o['data'])
    result = []
    for p in prodotti_dict.values():
        prezzi = p['prezzi']
        prezzo_medio = sum(prezzi) / len(prezzi) if prezzi else 0
        prezzo_min = min(prezzi) if prezzi else 0
        prezzo_max = max(prezzi) if prezzi else 0
        ultimo_ordine = max(p['date']) if p['date'] else ''
        result.append({
            'nome': p['nome'],
            'quantita_totale': round(p['quantita_totale'], 2),
            'totale_euro': round(p['totale_euro'], 2),
            'num_ordini': p['num_ordini'],
            'prezzo_medio': round(prezzo_medio, 4),
            'prezzo_min': round(prezzo_min, 4),
            'prezzo_max': round(prezzo_max, 4),
            'ultimo_ordine': ultimo_ordine
        })
    result.sort(key=lambda x: x['totale_euro'], reverse=True)
    mesi_disponibili = sorted(set(o.get('data', '')[:7] for o in ordini if o.get('data')))
    return {"prodotti": result, "mesi_disponibili": mesi_disponibili}


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
