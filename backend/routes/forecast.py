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
    
    # Get ALL historical data (no date limit)
    if tipo == "prodotto":
        # Get monthly sales for this product - ALL TIME
        pipeline = [
            {"$match": {"prodotto_nome": nome}},
            {"$addFields": {"mese": {"$substr": ["$data", 0, 7]}}},
            {"$group": {
                "_id": "$mese",
                "fatturato": {"$sum": {"$abs": "$totale"}},
                "quantita": {"$sum": {"$abs": "$quantita"}},
                "num_ordini": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        storico = await db.vendite.aggregate(pipeline).to_list(100)
        
        # Get top clients for this product - ALL TIME
        top_clienti_pipeline = [
            {"$match": {"prodotto_nome": nome, "cliente_nome": {"$nin": EXCLUDED}}},
            {"$group": {"_id": "$cliente_nome", "totale": {"$sum": {"$abs": "$totale"}}}},
            {"$sort": {"totale": -1}},
            {"$limit": 5}
        ]
        top_clienti = await db.vendite.aggregate(top_clienti_pipeline).to_list(5)
        
        entity_name = nome
        entity_type = "prodotto"
        extra_context = f"Top clienti: {', '.join([c['_id'] for c in top_clienti])}" if top_clienti else ""
        
    else:  # cliente
        # Get monthly purchases for this client - ALL TIME
        pipeline = [
            {"$match": {"cliente_nome": nome}},
            {"$addFields": {"mese": {"$substr": ["$data", 0, 7]}}},
            {"$group": {
                "_id": "$mese",
                "fatturato": {"$sum": {"$abs": "$totale"}},
                "num_ordini": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        storico = await db.vendite.aggregate(pipeline).to_list(100)
        
        # Get top products for this client - ALL TIME
        top_prod_pipeline = [
            {"$match": {"cliente_nome": nome}},
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
    
    mesi_it = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 
               'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
    target_month_name = mesi_it[target_month - 1]
    
    # Calculate statistics
    media_mensile = sum(s['fatturato'] for s in storico) / len(storico) if storico else 0
    ultimo_mese = storico[-1] if storico else None
    ultimo_mese_str = f"{ultimo_mese['_id']}: €{ultimo_mese['fatturato']:,.2f}" if ultimo_mese else "N/A"
    
    # Data for the SAME month in previous years (key for forecast)
    same_month_data = [s for s in storico if s['_id'].endswith(f"-{target_month:02d}")]
    same_month_avg = sum(s['fatturato'] for s in same_month_data) / len(same_month_data) if same_month_data else 0
    same_month_max = max(s['fatturato'] for s in same_month_data) if same_month_data else 0
    same_month_min = min(s['fatturato'] for s in same_month_data) if same_month_data else 0
    
    # Year over year comparison for same month
    same_month_trend = ""
    if len(same_month_data) >= 2:
        sorted_same = sorted(same_month_data, key=lambda x: x['_id'])
        last_year = sorted_same[-1]['fatturato']
        prev_year = sorted_same[-2]['fatturato']
        yoy_change = ((last_year - prev_year) / prev_year * 100) if prev_year > 0 else 0
        same_month_trend = f"Trend anno su anno: {yoy_change:+.1f}%"
    
    same_month_context = ""
    if same_month_data:
        same_month_context = f"""
Dati storici per {target_month_name}:
- Media: €{same_month_avg:,.2f}
- Massimo: €{same_month_max:,.2f}
- Minimo: €{same_month_min:,.2f}
{same_month_trend}"""
    
    # Generate AI forecast
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="API key LLM non configurata")
    
    try:
        chat = LlmChat(
            api_key=api_key, 
            session_id=f"forecast-{uuid.uuid4()}", 
            system_message="""Sei un analista business esperto nel settore ortofrutticolo italiano.
Genera previsioni accurate e concise SOLO per il mese specifico richiesto.
Rispondi SEMPRE in italiano. Sii breve e diretto. 
Basa la previsione PRINCIPALMENTE sui dati dello stesso mese negli anni precedenti."""
        ).with_model("openai", "gpt-4o")
        
        prompt = f"""PREVISIONE: {target_month_name} {target_year}

{entity_type.upper()}: {entity_name}
{same_month_context if same_month_context else f"Nessun dato storico per {target_month_name} - usa la media generale: €{media_mensile:,.2f}"}
{extra_context}

Genera previsione SOLO per {target_month_name} {target_year}:

## PREVISIONE FATTURATO
- Minimo: €X
- Massimo: €X  
- Probabile: €X

## ANALISI
Breve spiegazione (2-3 righe max)

## AZIONI
2-3 azioni concrete"""

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
                "media_mensile": round(media_mensile, 2),
                "stesso_mese_avg": round(same_month_avg, 2),
                "stesso_mese_max": round(same_month_max, 2),
                "stesso_mese_min": round(same_month_min, 2),
                "anni_dati_mese": len(same_month_data)
            },
            "previsione_ai": ai_response,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating forecast: {e}")
        raise HTTPException(status_code=500, detail=f"Errore generazione previsione: {str(e)}")


@router.post("/forecast/export-pdf")
async def export_forecast_pdf(data: dict):
    """Export forecast to PDF"""
    from fpdf import FPDF
    from fastapi.responses import Response
    import re
    
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Header
        pdf.set_font('Helvetica', 'B', 18)
        pdf.set_text_color(30, 64, 175)
        pdf.cell(0, 12, 'FORECAST AI', ln=True, align='C')
        
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(100, 100, 100)
        mese_target = str(data.get('mese_target_nome', '')).encode('ascii', errors='replace').decode('ascii')
        pdf.cell(0, 8, f"Previsione per {mese_target}", ln=True, align='C')
        pdf.ln(5)
        
        # Entity info
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(0, 0, 0)
        tipo_label = "PRODOTTO" if data.get('tipo') == 'prodotto' else "CLIENTE"
        nome = str(data.get('nome', '')).encode('ascii', errors='replace').decode('ascii')
        pdf.cell(0, 8, f"{tipo_label}: {nome}", ln=True)
        pdf.ln(3)
        
        # Statistics
        stats = data.get('statistiche', {})
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 7, 'STATISTICHE STORICHE', ln=True, fill=True)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, f"Media mensile: EUR {stats.get('media_mensile', 0):.2f}", ln=True)
        pdf.cell(0, 6, f"Totale periodo analizzato: EUR {stats.get('totale_periodo', 0):.2f}", ln=True)
        pdf.cell(0, 6, f"Mesi con dati: {stats.get('num_mesi_dati', 0)}", ln=True)
        pdf.ln(5)
        
        # AI Forecast
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 7, 'PREVISIONE AI', ln=True, fill=True)
        pdf.set_font('Helvetica', '', 9)
        
        # Clean and format AI response
        ai_text = str(data.get('previsione_ai', ''))
        ai_text = ai_text.replace('€', 'EUR ')
        ai_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', ai_text)
        ai_text = re.sub(r'\*([^*]+)\*', r'\1', ai_text)
        ai_text = re.sub(r'#{1,3}\s*', '', ai_text)
        ai_text = ai_text.encode('ascii', errors='replace').decode('ascii')
        
        # Simple text output - each line
        for line in ai_text.split('\n'):
            line = line.strip()
            if not line:
                pdf.ln(2)
                continue
            # Check if it's a header
            if line.isupper() or (len(line) < 40 and line.endswith(':')):
                pdf.set_font('Helvetica', 'B', 10)
                pdf.ln(2)
                pdf.cell(0, 5, line, ln=True)
            else:
                pdf.set_font('Helvetica', '', 9)
                # Wrap long lines manually
                words = line.split()
                current_line = ""
                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    if pdf.get_string_width(test_line) < 180:
                        current_line = test_line
                    else:
                        if current_line:
                            pdf.cell(0, 4, current_line, ln=True)
                        current_line = word
                if current_line:
                    pdf.cell(0, 4, current_line, ln=True)
        
        pdf.ln(8)
        
        # Footer
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(150, 150, 150)
        generated_at = str(data.get('generated_at', ''))[:10] if data.get('generated_at') else ''
        pdf.cell(0, 6, f"Generato il {generated_at} - Flow Business Analytics", ln=True, align='C')
        
        # Output PDF
        pdf_bytes = pdf.output()
        
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=forecast.pdf"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Errore esportazione PDF: {str(e)}")
