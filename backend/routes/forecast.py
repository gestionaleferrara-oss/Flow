from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional
import os
import uuid

from database import db, logger

router = APIRouter()


@router.get("/forecast/prodotti")
async def get_forecast_prodotti(search: str = ""):
    """Get products with sales history for forecasting"""
    query = {}
    if search:
        query["nome"] = {"$regex": search, "$options": "i"}
    
    # Get products that have been sold
    vendite_prodotti = await db.vendite.distinct("prodotto_nome")
    query["nome"] = {"$in": vendite_prodotti}
    if search:
        query["nome"] = {"$regex": search, "$options": "i", "$in": vendite_prodotti}
    
    prodotti = await db.prodotti.find(query, {"_id": 0, "nome": 1, "codice": 1}).limit(50).to_list(50)
    return prodotti


@router.get("/forecast/clienti")
async def get_forecast_clienti(search: str = ""):
    """Get clients with sales history for forecasting"""
    EXCLUDED = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    
    # Get clients that have purchased
    pipeline = [
        {"$match": {"cliente_nome": {"$nin": EXCLUDED}}},
        {"$group": {"_id": "$cliente_nome", "totale": {"$sum": {"$abs": "$totale"}}}},
        {"$sort": {"totale": -1}},
        {"$limit": 100}
    ]
    if search:
        pipeline[0]["$match"]["cliente_nome"] = {"$regex": search, "$options": "i", "$nin": EXCLUDED}
    
    clienti = await db.vendite.aggregate(pipeline).to_list(100)
    return [{"nome": c["_id"], "fatturato_storico": round(c["totale"], 2)} for c in clienti if c["_id"]]


@router.get("/forecast/generate")
async def generate_forecast(
    tipo: str = Query("prodotto", enum=["prodotto", "cliente"]),
    nome: str = Query(...),
    mese_target: str = Query(...)  # Format: YYYY-MM
):
    """Generate AI-powered sales forecast"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    EXCLUDED = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    
    # Parse target month
    try:
        target_year, target_month = map(int, mese_target.split("-"))
        target_date = datetime(target_year, target_month, 1)
    except:
        raise HTTPException(status_code=400, detail="Formato mese non valido. Usa YYYY-MM")
    
    # Get historical data (last 12 months from today, not target)
    now = datetime.now()
    twelve_months_ago = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    
    if tipo == "prodotto":
        # Get monthly sales for this product
        pipeline = [
            {"$match": {"prodotto_nome": nome, "data": {"$gte": twelve_months_ago}}},
            {"$addFields": {"mese": {"$substr": ["$data", 0, 7]}}},
            {"$group": {
                "_id": "$mese",
                "fatturato": {"$sum": {"$abs": "$totale"}},
                "quantita": {"$sum": {"$abs": "$quantita"}},
                "num_ordini": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        storico = await db.vendite.aggregate(pipeline).to_list(24)
        
        # Get top clients for this product
        top_clienti_pipeline = [
            {"$match": {"prodotto_nome": nome, "data": {"$gte": twelve_months_ago}, "cliente_nome": {"$nin": EXCLUDED}}},
            {"$group": {"_id": "$cliente_nome", "totale": {"$sum": {"$abs": "$totale"}}}},
            {"$sort": {"totale": -1}},
            {"$limit": 5}
        ]
        top_clienti = await db.vendite.aggregate(top_clienti_pipeline).to_list(5)
        
        entity_name = nome
        entity_type = "prodotto"
        extra_context = f"Top clienti: {', '.join([c['_id'] for c in top_clienti])}" if top_clienti else ""
        
    else:  # cliente
        # Get monthly purchases for this client
        pipeline = [
            {"$match": {"cliente_nome": nome, "data": {"$gte": twelve_months_ago}}},
            {"$addFields": {"mese": {"$substr": ["$data", 0, 7]}}},
            {"$group": {
                "_id": "$mese",
                "fatturato": {"$sum": {"$abs": "$totale"}},
                "num_ordini": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        storico = await db.vendite.aggregate(pipeline).to_list(24)
        
        # Get top products for this client
        top_prod_pipeline = [
            {"$match": {"cliente_nome": nome, "data": {"$gte": twelve_months_ago}}},
            {"$group": {"_id": "$prodotto_nome", "totale": {"$sum": {"$abs": "$totale"}}}},
            {"$sort": {"totale": -1}},
            {"$limit": 5}
        ]
        top_prodotti = await db.vendite.aggregate(top_prod_pipeline).to_list(5)
        
        entity_name = nome
        entity_type = "cliente"
        extra_context = f"Prodotti preferiti: {', '.join([p['_id'] for p in top_prodotti])}" if top_prodotti else ""
    
    if not storico:
        return {
            "success": False,
            "error": f"Nessun dato storico trovato per {entity_type} '{nome}'"
        }
    
    # Build historical data string
    storico_str = "\n".join([
        f"- {s['_id']}: €{s['fatturato']:,.2f}" + (f" ({s.get('quantita', 0):.0f} pz)" if 'quantita' in s else "")
        for s in storico
    ])
    
    # Calculate simple statistics for context
    tot_fatturato = sum(s['fatturato'] for s in storico)
    media_mensile = tot_fatturato / len(storico) if storico else 0
    ultimo_mese = storico[-1] if storico else None
    ultimo_mese_str = f"{ultimo_mese['_id']}: €{ultimo_mese['fatturato']:,.2f}" if ultimo_mese else "N/A"
    
    mesi_it = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 
               'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
    target_month_name = mesi_it[target_month - 1]
    
    # Check if we have data for this month in previous years
    same_month_data = [s for s in storico if s['_id'].endswith(f"-{target_month:02d}")]
    same_month_context = ""
    if same_month_data:
        same_month_avg = sum(s['fatturato'] for s in same_month_data) / len(same_month_data)
        same_month_context = f"\nDati storici per {target_month_name}: media €{same_month_avg:,.2f}"
    
    # Generate AI forecast
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="API key LLM non configurata")
    
    try:
        chat = LlmChat(
            api_key=api_key, 
            session_id=f"forecast-{uuid.uuid4()}", 
            system_message="""Sei un analista business esperto nel settore ortofrutticolo italiano.
Genera previsioni accurate e concise per il mese specifico richiesto.
Rispondi SEMPRE in italiano con formattazione chiara e professionale.
NON ripetere i dati storici già forniti - concentrati solo sulla previsione."""
        ).with_model("openai", "gpt-4o")
        
        prompt = f"""PREVISIONE VENDITE: {target_month_name} {target_year}

{entity_type.upper()}: {entity_name}

DATI RILEVANTI:
- Media mensile storica: €{media_mensile:,.2f}
- Ultimo mese registrato: {ultimo_mese_str}
{same_month_context if same_month_context else f"- Nessun dato storico per {target_month_name}"}
{extra_context}

Genera una previsione SOLO per {target_month_name} {target_year}:

## PREVISIONE FATTURATO
Indica: valore minimo, valore massimo, valore più probabile

## ANALISI MESE
Spiega brevemente i fattori che influenzano questa previsione (stagionalità, trend, eventi)

## AZIONI CONSIGLIATE
Elenca 2-3 azioni concrete per ottimizzare le vendite nel mese target

Sii conciso e vai dritto al punto."""

        user_message = UserMessage(text=prompt)
        ai_response = await chat.send_message(user_message)
        
        return {
            "success": True,
            "tipo": entity_type,
            "nome": entity_name,
            "mese_target": mese_target,
            "mese_target_nome": f"{target_month_name} {target_year}",
            "storico": [{"mese": s["_id"], "fatturato": round(s["fatturato"], 2), "quantita": round(s.get("quantita", 0), 1)} for s in storico],
            "statistiche": {
                "totale_periodo": round(tot_fatturato, 2),
                "media_mensile": round(media_mensile, 2),
                "num_mesi_dati": len(storico)
            },
            "previsione_ai": ai_response,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating forecast: {e}")
        raise HTTPException(status_code=500, detail=f"Errore generazione previsione: {str(e)}")
