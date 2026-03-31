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
    mese_target: str = Query(...),  # Format: YYYY-MM
    metrica: str = Query("fatturato", enum=["fatturato", "richieste"])  # Which metric to forecast
):
    """Generate AI-powered sales forecast for revenue or order count"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    EXCLUDED = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    
    # Parse target month
    try:
        target_year, target_month = map(int, mese_target.split("-"))
        target_date = datetime(target_year, target_month, 1)
    except Exception:
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
                "richieste": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        storico = await db.vendite.aggregate(pipeline).to_list(100)
        
        # Get top clients for this product - ALL TIME
        top_clienti_pipeline = [
            {"$match": {"prodotto_nome": nome, "cliente_nome": {"$nin": EXCLUDED}}},
            {"$group": {"_id": "$cliente_nome", "totale": {"$sum": {"$abs": "$totale"}}, "ordini": {"$sum": 1}}},
            {"$sort": {"totale": -1}},
            {"$limit": 5}
        ]
        top_clienti = await db.vendite.aggregate(top_clienti_pipeline).to_list(5)
        
        entity_name = nome
        entity_type = "prodotto"
        if top_clienti:
            clienti_strs = [c['_id'] + ' (' + str(c['ordini']) + ' ord.)' for c in top_clienti]
            extra_context = 'Top clienti: ' + ', '.join(clienti_strs)
        else:
            extra_context = ""
        
    else:  # cliente
        # Get monthly purchases for this client - ALL TIME
        pipeline = [
            {"$match": {"cliente_nome": nome}},
            {"$addFields": {"mese": {"$substr": ["$data", 0, 7]}}},
            {"$group": {
                "_id": "$mese",
                "fatturato": {"$sum": {"$abs": "$totale"}},
                "richieste": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        storico = await db.vendite.aggregate(pipeline).to_list(100)
        
        # Get top products for this client - ALL TIME
        top_prod_pipeline = [
            {"$match": {"cliente_nome": nome}},
            {"$group": {"_id": "$prodotto_nome", "totale": {"$sum": {"$abs": "$totale"}}, "ordini": {"$sum": 1}}},
            {"$sort": {"totale": -1}},
            {"$limit": 5}
        ]
        top_prodotti = await db.vendite.aggregate(top_prod_pipeline).to_list(5)
        
        entity_name = nome
        entity_type = "cliente"
        if top_prodotti:
            prodotti_strs = [p['_id'] + ' (' + str(p['ordini']) + ' ord.)' for p in top_prodotti]
            extra_context = 'Prodotti preferiti: ' + ', '.join(prodotti_strs)
        else:
            extra_context = ""
    
    if not storico:
        return {
            "success": False,
            "error": f"Nessun dato storico trovato per {entity_type} '{nome}'"
        }
    
    mesi_it = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 
               'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
    target_month_name = mesi_it[target_month - 1]
    
    # Use selected metric for calculations
    metric_key = metrica  # 'fatturato' or 'richieste'
    metric_label = "Fatturato" if metrica == "fatturato" else "Richieste"
    metric_unit = "€" if metrica == "fatturato" else ""
    metric_suffix = "" if metrica == "fatturato" else " ordini"
    
    # Calculate statistics using selected metric
    values = [s.get(metric_key, 0) for s in storico]
    media_mensile = sum(values) / len(values) if values else 0
    ultimo_mese = storico[-1] if storico else None
    ultimo_mese_val = ultimo_mese.get(metric_key, 0) if ultimo_mese else 0
    ultimo_mese_str = f"{ultimo_mese['_id']}: {metric_unit}{ultimo_mese_val:,.2f}{metric_suffix}" if ultimo_mese else "N/A"
    
    # Data for the SAME month in previous years (key for forecast)
    same_month_data = [s for s in storico if s['_id'].endswith(f"-{target_month:02d}")]
    same_month_values = [s.get(metric_key, 0) for s in same_month_data]
    same_month_avg = sum(same_month_values) / len(same_month_values) if same_month_values else 0
    same_month_max = max(same_month_values) if same_month_values else 0
    same_month_min = min(same_month_values) if same_month_values else 0
    
    # Year over year comparison for same month
    same_month_trend = ""
    if len(same_month_data) >= 2:
        sorted_same = sorted(same_month_data, key=lambda x: x['_id'])
        last_year = sorted_same[-1].get(metric_key, 0)
        prev_year = sorted_same[-2].get(metric_key, 0)
        yoy_change = ((last_year - prev_year) / prev_year * 100) if prev_year > 0 else 0
        same_month_trend = f"Trend anno su anno: {yoy_change:+.1f}%"
    
    same_month_context = ""
    if same_month_data:
        same_month_context = f"""
Dati storici per {target_month_name} ({metric_label}):
- Media: {metric_unit}{same_month_avg:,.2f}{metric_suffix}
- Massimo: {metric_unit}{same_month_max:,.2f}{metric_suffix}
- Minimo: {metric_unit}{same_month_min:,.2f}{metric_suffix}
{same_month_trend}"""
    
    # Calculate forecasts for 3 months (target + next 2)
    previsioni_mesi = []
    for i in range(3):
        forecast_month = target_month + i
        forecast_year = target_year
        if forecast_month > 12:
            forecast_month -= 12
            forecast_year += 1
        
        month_name = mesi_it[forecast_month - 1]
        month_key = f"{forecast_year}-{forecast_month:02d}"
        
        # Get historical data for this specific month
        month_historical = [s for s in storico if s['_id'].endswith(f"-{forecast_month:02d}")]
        month_values = [s.get(metric_key, 0) for s in month_historical]
        
        # Calculate confidence based on data availability
        confidence = "alta" if len(month_historical) >= 3 else "media" if len(month_historical) >= 2 else "bassa"
        
        if month_values:
            hist_avg = sum(month_values) / len(month_values)
            hist_max = max(month_values)
            hist_min = min(month_values)
            
            # Calculate variance for reliability
            if len(month_values) > 1:
                variance = sum((v - hist_avg) ** 2 for v in month_values) / len(month_values)
                std_dev = variance ** 0.5
                cv = (std_dev / hist_avg * 100) if hist_avg > 0 else 0  # Coefficient of variation
            else:
                cv = 50  # High uncertainty with single data point
            
            # Calculate trend
            if len(month_historical) >= 2:
                sorted_hist = sorted(month_historical, key=lambda x: x['_id'])
                recent = sorted_hist[-1].get(metric_key, 0)
                older = sorted_hist[0].get(metric_key, 0)
                trend_pct = ((recent - older) / older * 100) if older > 0 else 0
            else:
                trend_pct = 0
            
            # Apply trend to calculate forecast (weighted by confidence)
            trend_weight = 0.4 if confidence == "alta" else 0.25 if confidence == "media" else 0.1
            trend_factor = 1 + (trend_pct / 100) * trend_weight
            forecast_value = hist_avg * trend_factor
            
            # Range calculation based on variance
            range_factor = max(0.15, min(0.35, cv / 100))  # 15%-35% range
            forecast_min = forecast_value * (1 - range_factor)
            forecast_max = forecast_value * (1 + range_factor)
        else:
            # No historical data for this month, use general average with high uncertainty
            forecast_value = media_mensile
            forecast_min = media_mensile * 0.6
            forecast_max = media_mensile * 1.4
            trend_pct = 0
            hist_avg = 0
            cv = 100
            confidence = "molto_bassa"
        
        previsioni_mesi.append({
            "mese": month_key,
            "mese_nome": f"{month_name} {forecast_year}",
            "previsione": round(forecast_value, 2) if metrica == "fatturato" else round(forecast_value),
            "minimo": round(forecast_min, 2) if metrica == "fatturato" else round(forecast_min),
            "massimo": round(forecast_max, 2) if metrica == "fatturato" else round(forecast_max),
            "storico_avg": round(hist_avg, 2) if metrica == "fatturato" else round(hist_avg),
            "trend": round(trend_pct, 1),
            "anni_dati": len(month_historical),
            "confidenza": confidence,
            "variabilita": round(cv, 1)
        })
    
    # Build context for AI
    storico_recente = storico[-6:] if len(storico) > 6 else storico
    storico_str = "\n".join([f"- {s['_id']}: {metric_unit}{s.get(metric_key, 0):,.2f}{metric_suffix}" for s in storico_recente])
    
    previsioni_str = "\n".join([
        f"- {p['mese_nome']}: {metric_unit}{p['previsione']:,.2f}{metric_suffix} (range {metric_unit}{p['minimo']:,.2f} - {metric_unit}{p['massimo']:,.2f}{metric_suffix}) [Confidenza: {p['confidenza']}, {p['anni_dati']} anni dati]"
        for p in previsioni_mesi
    ])
    
    # Generate AI forecast
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="API key LLM non configurata")
    
    # Calculate additional context for better predictions
    total_storico_value = sum(s.get(metric_key, 0) for s in storico)
    months_with_data = len(storico)
    
    # Trend analysis
    if len(storico) >= 3:
        recent_3 = sum(s.get(metric_key, 0) for s in storico[-3:]) / 3
        older_3 = sum(s.get(metric_key, 0) for s in storico[:3]) / 3 if len(storico) >= 6 else recent_3
        overall_trend = ((recent_3 - older_3) / older_3 * 100) if older_3 > 0 else 0
    else:
        overall_trend = 0
    
    trend_description = "in crescita" if overall_trend > 10 else "in calo" if overall_trend < -10 else "stabile"
    
    try:
        chat = LlmChat(
            api_key=api_key, 
            session_id=f"forecast-{uuid.uuid4()}", 
            system_message=f"""Sei un analista business esperto nel settore ortofrutticolo italiano.
REGOLE FONDAMENTALI:
1. USA SOLO I NUMERI FORNITI - non inventare mai cifre
2. Le previsioni devono essere REALISTICHE e basate sui dati storici
3. Rispondi in italiano, in modo conciso e professionale
4. Se i dati sono insufficienti, dillo chiaramente
5. Non ripetere gli stessi numeri - varia le previsioni mese per mese in base ai trend"""
        ).with_model("openai", "gpt-4o")
        
        prompt = f"""ANALISI PREVISIONALE: {entity_type.upper()} "{entity_name}"

DATI STORICI ({months_with_data} mesi disponibili):
{storico_str}

STATISTICHE CHIAVE:
- Media mensile: {metric_unit}{media_mensile:,.2f}{metric_suffix}
- Trend generale: {trend_description} ({overall_trend:+.1f}%)
- Dati storici per {target_month_name}: {len(same_month_data)} anni disponibili
{f'- Media storica {target_month_name}: {metric_unit}{same_month_avg:,.2f}{metric_suffix}' if same_month_data else '- Nessun dato storico per questo mese'}

PREVISIONI CALCOLATE (algoritmo statistico):
{previsioni_str}

{extra_context}

Genera un'analisi CONCISA e SPECIFICA basata SOLO sui dati forniti:

## PREVISIONE {previsioni_mesi[0]['mese_nome'].upper()}
Indica il valore previsto ({metric_unit}{previsioni_mesi[0]['previsione']:,.2f}{metric_suffix}) e spiega il ragionamento basato sui dati (max 2-3 righe).
Indica il livello di affidabilità: {previsioni_mesi[0]['confidenza']} (basato su {previsioni_mesi[0]['anni_dati']} anni di dati).

## TREND ATTESO TRIMESTRE
Per i prossimi 3 mesi, descrivi:
- Andamento previsto (crescita/stabile/calo)  
- Range di variazione atteso
- Fattori stagionali se rilevanti

## AZIONI CONSIGLIATE
2-3 suggerimenti PRATICI e SPECIFICI per questo {entity_type}, basati sui pattern osservati.

REGOLE: Usa SOLO i numeri forniti. Non inventare cifre. Sii specifico e concreto."""

        user_message = UserMessage(text=prompt)
        ai_response = await chat.send_message(user_message)
        
        return {
            "success": True,
            "tipo": entity_type,
            "nome": entity_name,
            "metrica": metrica,
            "metrica_label": metric_label,
            "mese_target": mese_target,
            "mese_target_nome": f"{target_month_name} {target_year}",
            "previsioni": previsioni_mesi,
            "storico": [{"mese": s["_id"], "valore": round(s.get(metric_key, 0), 2)} for s in storico[-12:]],
            "statistiche": {
                "media_mensile": round(media_mensile, 2),
                "stesso_mese_avg": round(same_month_avg, 2),
                "stesso_mese_max": round(same_month_max, 2),
                "stesso_mese_min": round(same_month_min, 2),
                "anni_dati_mese": len(same_month_data),
                "trend_generale": round(overall_trend, 1)
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
            headers={"Content-Disposition": "attachment; filename=forecast.pdf"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Errore esportazione PDF: {str(e)}")
