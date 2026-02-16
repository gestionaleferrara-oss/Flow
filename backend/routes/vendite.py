from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime, timedelta

from database import db

router = APIRouter()


@router.get("/vendite")
async def get_vendite(
    search: Optional[str] = None, cliente: Optional[str] = None,
    prodotto: Optional[str] = None, start_date: Optional[str] = None,
    end_date: Optional[str] = None, limit: int = 100, skip: int = 0
):
    query = {}
    if search:
        query["$or"] = [
            {"cliente_nome": {"$regex": search, "$options": "i"}},
            {"prodotto_nome": {"$regex": search, "$options": "i"}}
        ]
    if cliente:
        query["cliente_nome"] = {"$regex": cliente, "$options": "i"}
    if prodotto:
        query["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}
    if start_date:
        query.setdefault("data", {})["$gte"] = start_date
    if end_date:
        query.setdefault("data", {})["$lte"] = end_date
    vendite = await db.vendite.find(query, {"_id": 0}).sort("data", -1).skip(skip).limit(limit).to_list(limit)
    return vendite


@router.get("/vendite/count")
async def get_vendite_count():
    count = await db.vendite.count_documents({})
    return {"count": count}


@router.delete("/vendite/bulk-delete")
async def bulk_delete_vendite(
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    cliente: Optional[str] = None
):
    query = {}
    if start_date:
        query.setdefault("data", {})["$gte"] = start_date
    if end_date:
        query.setdefault("data", {})["$lte"] = end_date
    if cliente:
        query["cliente_nome"] = cliente
    if not query:
        return {"message": "Nessun filtro specificato", "deleted": 0}
    result = await db.vendite.delete_many(query)
    return {"message": f"Eliminate {result.deleted_count} vendite", "deleted": result.deleted_count}


@router.get("/statistiche/export")
async def export_statistiche(
    format: str = "csv", start_date: Optional[str] = None,
    end_date: Optional[str] = None, tipo: str = "vendite"
):
    query = {}
    if start_date:
        query.setdefault("data", {})["$gte"] = start_date
    if end_date:
        query.setdefault("data", {})["$lte"] = end_date
    if tipo == "vendite":
        records = await db.vendite.find(query, {"_id": 0}).sort("data", -1).to_list(100000)
        if format == "csv":
            import csv, io
            output = io.StringIO()
            if records:
                writer = csv.DictWriter(output, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
            return JSONResponse(content={"data": output.getvalue(), "filename": f"vendite_{start_date or 'all'}_{end_date or 'all'}.csv"})
    elif tipo == "acquisti":
        records = await db.ordini.find(query, {"_id": 0}).sort("data", -1).to_list(100000)
        if format == "csv":
            import csv, io
            output = io.StringIO()
            if records:
                writer = csv.DictWriter(output, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
            return JSONResponse(content={"data": output.getvalue(), "filename": f"acquisti_{start_date or 'all'}_{end_date or 'all'}.csv"})
    return {"data": records[:1000]}


# ===== Statistiche =====

@router.get("/statistiche")
async def get_statistiche(
    prodotto: Optional[str] = None, cliente: Optional[str] = None,
    start_date: Optional[str] = None, end_date: Optional[str] = None
):
    query = {}
    if prodotto:
        query["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}
    if cliente:
        query["cliente_nome"] = {"$regex": cliente, "$options": "i"}
    if start_date:
        query.setdefault("data", {})["$gte"] = start_date
    if end_date:
        query.setdefault("data", {})["$lte"] = end_date
    vendite = await db.vendite.find(query, {"_id": 0}).to_list(100000)
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    vendite_filtrate = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    totale_euro = sum(abs(v.get('totale', 0)) for v in vendite_filtrate)
    totale_articoli = sum(abs(v.get('quantita', 0)) for v in vendite_filtrate)
    clienti_attivi = len(set(v.get('cliente_nome', '') for v in vendite_filtrate if v.get('cliente_nome')))
    now = datetime.now()
    current_month_start = now.replace(day=1).strftime("%Y-%m-%d")
    current_month_vendite = [v for v in vendite_filtrate if v.get('data', '') >= current_month_start]
    fatturato_mese = sum(abs(v.get('totale', 0)) for v in current_month_vendite)
    prev_month = now.replace(day=1) - timedelta(days=1)
    prev_month_start = prev_month.replace(day=1).strftime("%Y-%m-%d")
    prev_month_end = prev_month.strftime("%Y-%m-%d")
    prev_month_vendite = [v for v in vendite_filtrate if prev_month_start <= v.get('data', '') <= prev_month_end]
    fatturato_mese_prec = sum(abs(v.get('totale', 0)) for v in prev_month_vendite)
    if fatturato_mese_prec > 0:
        diff_percentuale = ((fatturato_mese - fatturato_mese_prec) / fatturato_mese_prec) * 100
    else:
        diff_percentuale = 100 if fatturato_mese > 0 else 0
    vendite_mensili = {}
    for v in vendite_filtrate:
        data = v.get('data', '')[:7]
        vendite_mensili[data] = vendite_mensili.get(data, 0) + abs(v.get('totale', 0))
    monthly_data = [{"data": k, "totale": v} for k, v in sorted(vendite_mensili.items())]
    vendite_giornaliere = {}
    for v in vendite_filtrate:
        data = v.get('data', '')
        vendite_giornaliere[data] = vendite_giornaliere.get(data, 0) + abs(v.get('totale', 0))
    daily_data = [{"data": k, "totale": v} for k, v in sorted(vendite_giornaliere.items())]
    clienti_fatturato = {}
    for v in vendite_filtrate:
        c = v.get('cliente_nome', '')
        if c:
            clienti_fatturato[c] = clienti_fatturato.get(c, 0) + abs(v.get('totale', 0))
    top_clienti = [{"nome": k, "spesa": v} for k, v in sorted(clienti_fatturato.items(), key=lambda x: x[1], reverse=True)[:10]]
    
    # Calculate margin for products using WEIGHTED average
    prodotti_totale = {}
    prodotti_qty = {}
    for v in vendite_filtrate:
        prod = v.get('prodotto_nome', '')
        prodotti_totale[prod] = prodotti_totale.get(prod, 0) + abs(v.get('totale', 0))
        prodotti_qty[prod] = prodotti_qty.get(prod, 0) + abs(v.get('quantita', 0))
    
    # First pass: Calculate margin for ALL products to get accurate totals
    totale_fatturato_con_margine = 0
    somma_margini_ponderati = 0
    totale_profitto = 0
    prodotti_margine_data = {}  # Store margin data for all products
    
    for nome, totale in prodotti_totale.items():
        qty = prodotti_qty.get(nome, 0)
        if qty <= 0:
            continue
            
        # Get last purchase price
        ultimo_ordine = await db.ordini.find_one(
            {"prodotto_nome": nome, "prezzo_unitario": {"$gt": 0}},
            {"_id": 0, "prezzo_unitario": 1},
            sort=[("data", -1)]
        )
        if ultimo_ordine:
            prezzo_acquisto = ultimo_ordine.get('prezzo_unitario', 0)
            # Weighted average sale price = total revenue / total quantity
            prezzo_vendita_medio = totale / qty
            
            # Filter out anomalous prices
            if prezzo_acquisto > 0 and prezzo_acquisto < 500:
                # Skip if sale price is unreasonably different from purchase price
                if prezzo_vendita_medio <= prezzo_acquisto * 5 and prezzo_vendita_medio >= prezzo_acquisto * 0.2:
                    margine_pct = ((prezzo_vendita_medio - prezzo_acquisto) / prezzo_acquisto) * 100
                    costo_totale = prezzo_acquisto * qty
                    profitto = totale - costo_totale
                    
                    # Only include reasonable margins (-50% to +200%)
                    if -50 < margine_pct < 200:
                        # Accumulate for weighted average margin calculation
                        totale_fatturato_con_margine += totale
                        somma_margini_ponderati += margine_pct * totale
                        totale_profitto += profitto
                        
                        # Store for top products display
                        prodotti_margine_data[nome] = {
                            'margine_pct': round(margine_pct, 1),
                            'profitto': round(profitto, 2),
                            'prezzo_acquisto': round(prezzo_acquisto, 2),
                            'prezzo_vendita': round(prezzo_vendita_medio, 2)
                        }
    
    # Calculate weighted average margin: sum(margine * fatturato) / sum(fatturato)
    margine_medio = (somma_margini_ponderati / totale_fatturato_con_margine) if totale_fatturato_con_margine > 0 else 0
    
    # Build top 10 products with margin data
    top_prodotti = []
    for nome, totale in sorted(prodotti_totale.items(), key=lambda x: x[1], reverse=True)[:10]:
        qty = prodotti_qty.get(nome, 0)
        prod_data = {"nome": nome, "totale_euro": round(totale, 2), "quantita": round(qty, 2)}
        
        # Add margin data if available
        if nome in prodotti_margine_data:
            prod_data.update(prodotti_margine_data[nome])
        
        top_prodotti.append(prod_data)
        
        # Get last purchase price
        ultimo_ordine = await db.ordini.find_one(
            {"prodotto_nome": nome, "prezzo_unitario": {"$gt": 0}},
            {"_id": 0, "prezzo_unitario": 1},
            sort=[("data", -1)]
        )
        if ultimo_ordine and qty > 0:
            prezzo_acquisto = ultimo_ordine.get('prezzo_unitario', 0)
            # Weighted average sale price = total revenue / total quantity
            prezzo_vendita_medio = totale / qty
            
            # Filter out anomalous prices
            if prezzo_acquisto > 0 and prezzo_acquisto < 500:
                # Skip if sale price is unreasonably different from purchase price
                if prezzo_vendita_medio <= prezzo_acquisto * 5 and prezzo_vendita_medio >= prezzo_acquisto * 0.2:
                    margine_pct = ((prezzo_vendita_medio - prezzo_acquisto) / prezzo_acquisto) * 100
                    costo_totale = prezzo_acquisto * qty
                    profitto = totale - costo_totale
                    
                    # Only include reasonable margins (-50% to +200%)
                    if -50 < margine_pct < 200:
                        prod_data['margine_pct'] = round(margine_pct, 1)
                        prod_data['profitto'] = round(profitto, 2)
                        prod_data['prezzo_acquisto'] = round(prezzo_acquisto, 2)
                        prod_data['prezzo_vendita'] = round(prezzo_vendita_medio, 2)
                        
                        # Accumulate for weighted average margin calculation
                        totale_fatturato_con_margine += totale
                        somma_margini_ponderati += margine_pct * totale
                        totale_profitto += profitto
        
        top_prodotti.append(prod_data)
    
    # Calculate weighted average margin: sum(margine * fatturato) / sum(fatturato)
    margine_medio = (somma_margini_ponderati / totale_fatturato_con_margine) if totale_fatturato_con_margine > 0 else 0
    
    return {
        "totaleEuro": totale_euro, "totaleArticoli": totale_articoli, "clientiAttivi": clienti_attivi,
        "fatturatoMese": fatturato_mese, "fatturatoMesePrec": fatturato_mese_prec,
        "diffPercentuale": round(diff_percentuale, 2),
        "margineStimato": round(margine_medio, 1),
        "profittoStimato": round(totale_profitto, 2),
        "venditeMensili": monthly_data, "venditeGiornaliere": daily_data,
        "topClienti": top_clienti, "topProdotti": top_prodotti
    }


@router.get("/statistiche/lists")
async def get_statistiche_lists():
    prodotti = await db.prodotti.find({}, {"_id": 0, "nome": 1}).to_list(10000)
    clienti = await db.clienti.find({}, {"_id": 0, "nome": 1}).to_list(10000)
    return {"prodotti": [p.get('nome', '') for p in prodotti], "clienti": [c.get('nome', '') for c in clienti]}


@router.get("/statistiche/clienti-trend")
async def get_clienti_trend():
    today = datetime.now()
    days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    trend_data = []
    for day in days:
        vendite = await db.vendite.find({"data": day}, {"_id": 0, "cliente_nome": 1}).to_list(10000)
        unique_clients = len(set(v.get('cliente_nome', '') for v in vendite if v.get('cliente_nome')))
        day_date = datetime.strptime(day, "%Y-%m-%d")
        day_names = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
        trend_data.append({"giorno": f"{day_names[day_date.weekday()]} {day_date.day}", "data": day, "clienti": unique_clients})
    return trend_data


@router.get("/statistiche/acquisti")
async def get_statistiche_acquisti(
    prodotto: Optional[str] = None, fornitore: Optional[str] = None,
    start_date: Optional[str] = None, end_date: Optional[str] = None
):
    query = {}
    if prodotto:
        query["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}
    if fornitore:
        query["fornitore_nome"] = {"$regex": fornitore, "$options": "i"}
    if start_date:
        query.setdefault("data", {})["$gte"] = start_date
    if end_date:
        query.setdefault("data", {})["$lte"] = end_date
    ordini = await db.ordini.find(query, {"_id": 0}).to_list(100000)
    totale_euro = sum(abs(o.get('totale', 0)) for o in ordini)
    totale_articoli = sum(abs(o.get('quantita', 0)) for o in ordini)
    fornitori_attivi = len(set(o.get('fornitore_nome', '') for o in ordini))
    now = datetime.now()
    current_month_start = now.replace(day=1).strftime("%Y-%m-%d")
    current_month_ordini = [o for o in ordini if o.get('data', '') >= current_month_start]
    speso_mese = sum(abs(o.get('totale', 0)) for o in current_month_ordini)
    prev_month = now.replace(day=1) - timedelta(days=1)
    prev_month_start = prev_month.replace(day=1).strftime("%Y-%m-%d")
    prev_month_end = prev_month.strftime("%Y-%m-%d")
    prev_month_ordini = [o for o in ordini if prev_month_start <= o.get('data', '') <= prev_month_end]
    speso_mese_prec = sum(abs(o.get('totale', 0)) for o in prev_month_ordini)
    diff_percentuale = ((speso_mese - speso_mese_prec) / speso_mese_prec * 100) if speso_mese_prec > 0 else (100 if speso_mese > 0 else 0)
    acquisti_mensili = {}
    for o in ordini:
        data = o.get('data', '')[:7]
        acquisti_mensili[data] = acquisti_mensili.get(data, 0) + abs(o.get('totale', 0))
    monthly_data = [{"data": k, "totale": v} for k, v in sorted(acquisti_mensili.items())]
    fornitori_spesa = {}
    for o in ordini:
        fn = o.get('fornitore_nome', '')
        if fn:
            fornitori_spesa[fn] = fornitori_spesa.get(fn, 0) + abs(o.get('totale', 0))
    top_fornitori = [{"nome": k, "spesa": v} for k, v in sorted(fornitori_spesa.items(), key=lambda x: x[1], reverse=True)[:10]]
    prodotti_totale = {}
    for o in ordini:
        prod = o.get('prodotto_nome', '')
        prodotti_totale[prod] = prodotti_totale.get(prod, 0) + abs(o.get('totale', 0))
    top_prodotti = [{"nome": k, "totale_euro": round(v, 2)} for k, v in sorted(prodotti_totale.items(), key=lambda x: x[1], reverse=True)[:10]]
    return {
        "totaleEuro": totale_euro, "totaleArticoli": totale_articoli, "fornitoriAttivi": fornitori_attivi,
        "spesoMese": speso_mese, "spesoMesePrec": speso_mese_prec, "diffPercentuale": round(diff_percentuale, 2),
        "acquistiMensili": monthly_data, "topFornitori": top_fornitori, "topProdotti": top_prodotti
    }


@router.get("/statistiche/acquisti/lists")
async def get_statistiche_acquisti_lists():
    prodotti = await db.prodotti.find({}, {"_id": 0, "nome": 1}).to_list(10000)
    fornitori = await db.fornitori.find({}, {"_id": 0, "nome": 1}).to_list(10000)
    return {"prodotti": [p.get('nome', '') for p in prodotti], "fornitori": [f.get('nome', '') for f in fornitori]}


@router.get("/statistiche/fornitori-trend")
async def get_fornitori_trend():
    today = datetime.now()
    days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    trend_data = []
    for day in days:
        ordini = await db.ordini.find({"data": day}, {"_id": 0, "fornitore_nome": 1}).to_list(10000)
        unique_fornitori = len(set(o.get('fornitore_nome', '') for o in ordini if o.get('fornitore_nome')))
        day_date = datetime.strptime(day, "%Y-%m-%d")
        day_names = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
        trend_data.append({"giorno": f"{day_names[day_date.weekday()]} {day_date.day}", "data": day, "fornitori": unique_fornitori})
    return trend_data
