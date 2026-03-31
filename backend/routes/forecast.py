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
    tipo: str = Query("prodotto", enum=["prodotto", "cliente", "globale"]),
    nome: Optional[str] = Query(None),
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
    if tipo == "globale":
        # Aggregate ALL sales by month (excluding internal movements)
        pipeline = [
            {"$match": {"cliente_nome": {"$nin": EXCLUDED}, "totale": {"$gt": 0}}},
            {"$addFields": {"mese": {"$substr": ["$data", 0, 7]}}},
            {"$group": {
                "_id": "$mese",
                "fatturato": {"$sum": {"$abs": "$totale"}},
                "quantita": {"$sum": {"$abs": "$quantita"}},
                "richieste": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        storico = await db.vendite.aggregate(pipeline).to_list(200)
        
        # Top products globally
        top_prod_pipeline = [
            {"$match": {"cliente_nome": {"$nin": EXCLUDED}}},
            {"$group": {"_id": "$prodotto_nome", "totale": {"$sum": {"$abs": "$totale"}}}},
            {"$sort": {"totale": -1}},
            {"$limit": 5}
        ]
        top_prodotti = await db.vendite.aggregate(top_prod_pipeline).to_list(5)
        
        entity_name = "Vendite Globali"
        entity_type = "globale"
        if top_prodotti:
            prodotti_strs = [f"{p['_id']} (€{p['totale']:,.0f})" for p in top_prodotti if p['_id']]
            extra_context = 'Top prodotti per fatturato: ' + ', '.join(prodotti_strs)
        else:
            extra_context = ""

    elif tipo == "prodotto":
        if not nome:
            raise HTTPException(status_code=400, detail="nome richiesto per tipo prodotto")
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
        if not nome:
            raise HTTPException(status_code=400, detail="nome richiesto per tipo cliente")
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
    
    # Year over year comparison for same month (most recent YoY)
    same_month_trend = ""
    if len(same_month_data) >= 2:
        sorted_same = sorted(same_month_data, key=lambda x: x['_id'])
        last_year = sorted_same[-1].get(metric_key, 0)
        prev_year = sorted_same[-2].get(metric_key, 0)
        yoy_change = ((last_year - prev_year) / prev_year * 100) if prev_year > 0 else 0
        same_month_trend = f"Trend anno su anno (ultimo): {yoy_change:+.1f}%"
    
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
            sorted_hist = sorted(month_historical, key=lambda x: x['_id'])
            hist_avg = sum(month_values) / len(month_values)
            hist_max = max(month_values)
            hist_min = min(month_values)
            
            # Calculate variance for reliability
            if len(month_values) > 1:
                variance = sum((v - hist_avg) ** 2 for v in month_values) / len(month_values)
                std_dev = variance ** 0.5
                cv = (std_dev / hist_avg * 100) if hist_avg > 0 else 0
            else:
                cv = 50
            
            # Anchor to the most recent year's same-month value
            most_recent = sorted_hist[-1].get(metric_key, 0)
            
            # YoY trend capped at ±25% to avoid extreme projections
            if len(month_historical) >= 2:
                prev_year = sorted_hist[-2].get(metric_key, 0)
                trend_pct = ((most_recent - prev_year) / prev_year * 100) if prev_year > 0 else 0
                trend_pct_capped = max(-25.0, min(25.0, trend_pct))
            else:
                trend_pct = 0
                trend_pct_capped = 0
            
            # Primary projection: most recent year + capped YoY growth
            primary = most_recent * (1 + trend_pct_capped / 100)
            
            # Recent momentum: last 3 months vs overall average
            recent_months = storico[-3:] if len(storico) >= 3 else storico
            recent_avg = sum(s.get(metric_key, 0) for s in recent_months) / len(recent_months) if recent_months else media_mensile
            momentum = (recent_avg - media_mensile) / media_mensile if media_mensile > 0 else 0
            momentum_adj = max(-0.08, min(0.08, momentum * 0.12))  # gentle nudge max ±8%
            
            # Blend primary with historical average (regression to mean based on confidence)
            blend_primary = 0.65 if confidence == "alta" else 0.55 if confidence == "media" else 0.40
            blend_hist = 1 - blend_primary
            forecast_value = (primary * blend_primary + hist_avg * blend_hist) * (1 + momentum_adj)
            
            # Range calculation based on variance
            range_factor = max(0.12, min(0.30, cv / 100))
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
    
    # Build rich context for AI
    # Full historical data (not just last 6)
    storico_str = "\n".join([f"- {s['_id']}: {metric_unit}{s.get(metric_key, 0):,.2f}{metric_suffix}" for s in storico])
    
    # Year-over-year comparison table
    from collections import defaultdict
    by_year = defaultdict(dict)
    for s in storico:
        year = s['_id'][:4]
        month_num = s['_id'][5:7]
        by_year[year][month_num] = s.get(metric_key, 0)
    
    years_available = sorted(by_year.keys())
    yoy_table = ""
    if len(years_available) >= 2:
        yoy_table = f"\nCONFRONTO ANNO SU ANNO ({' vs '.join(years_available)}):\n"
        mesi_brevi = ['Gen','Feb','Mar','Apr','Mag','Giu','Lug','Ago','Set','Ott','Nov','Dic']
        for m_num in [f"{i:02d}" for i in range(1, 13)]:
            vals = [by_year[y].get(m_num, 0) for y in years_available]
            if any(v > 0 for v in vals):
                vals_str = " | ".join([f"{y}: {metric_unit}{v:>10,.0f}" for y, v in zip(years_available, vals)])
                # Calculate YoY change
                if len(vals) >= 2 and vals[-2] > 0:
                    yoy = (vals[-1] - vals[-2]) / vals[-2] * 100
                    yoy_str = f" ({yoy:+.1f}%)"
                else:
                    yoy_str = ""
                yoy_table += f"- {mesi_brevi[int(m_num)-1]}: {vals_str}{yoy_str}\n"
    
    previsioni_str = "\n".join([
        f"- {p['mese_nome']}: {metric_unit}{p['previsione']:,.2f}{metric_suffix} (range {metric_unit}{p['minimo']:,.2f} - {metric_unit}{p['massimo']:,.2f}{metric_suffix}) [Confidenza: {p['confidenza']}, {p['anni_dati']} anni dati, trend YoY: {p['trend']:+.1f}%]"
        for p in previsioni_mesi
    ])
    
    # Generate AI forecast
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="API key LLM non configurata")
    
    # Calculate additional context for better predictions
    months_with_data = len(storico)
    
    # Trend analysis (last 3 months vs previous 3)
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
            system_message=f"""Sei un analista business senior specializzato nel settore ortofrutticolo italiano.
Il tuo compito è analizzare dati reali e fornire previsioni di vendita accurate e consigli pratici.
REGOLE FONDAMENTALI:
1. USA SOLO I NUMERI FORNITI - non inventare mai cifre
2. Analizza la stagionalità in base al confronto anno su anno fornito
3. Rispondi in italiano, professionale e conciso
4. Commenta i trend mese per mese usando i dati storici concreti
5. Le raccomandazioni devono essere specifiche al settore ortofrutticolo"""
        ).with_model("openai", "gpt-4o")
        
        prompt = f"""ANALISI PREVISIONALE COMPLETA: {entity_type.upper()} "{entity_name}"

═══ DATI STORICI COMPLETI ({months_with_data} mesi) ═══
{storico_str}

{yoy_table}
═══ STATISTICHE ═══
- Media mensile storica: {metric_unit}{media_mensile:,.2f}{metric_suffix}
- Trend recente (ultimi 3 mesi vs precedenti): {trend_description} ({overall_trend:+.1f}%)
- Dati disponibili per {target_month_name}: {len(same_month_data)} anni
{f'- Storico {target_month_name} → media: {metric_unit}{same_month_avg:,.2f} | min: {metric_unit}{same_month_min:,.2f} | max: {metric_unit}{same_month_max:,.2f}' if same_month_data else '- Nessun dato storico per questo mese specifico'}
{same_month_trend}

═══ PREVISIONI CALCOLATE (algoritmo statistico) ═══
{previsioni_str}

{extra_context}

═══ ANALISI RICHIESTA ═══

## PREVISIONE {previsioni_mesi[0]['mese_nome'].upper()}
Analizza il valore previsto di **{metric_unit}{previsioni_mesi[0]['previsione']:,.2f}**{metric_suffix}.
- Confronta con lo stesso mese dell'anno precedente (usa i dati forniti)
- Spiega se la previsione è ottimistica, conservativa o in linea con la stagionalità
- Affidabilità: {previsioni_mesi[0]['confidenza']} ({previsioni_mesi[0]['anni_dati']} anni di dati disponibili)

## ANALISI TRIMESTRALE ({previsioni_mesi[0]['mese_nome']} - {previsioni_mesi[-1]['mese_nome']})
Per ciascuno dei 3 mesi previsti:
- Commenta il trend YoY specifico di quel mese
- Indica se ci sono pattern stagionali evidenti dai dati storici
- Totale trimestre previsto: {metric_unit}{sum(p['previsione'] for p in previsioni_mesi):,.2f}

## AZIONI CONSIGLIATE
3 azioni pratiche e specifiche per ottimizzare le vendite nel trimestre, basate sui pattern osservati nei dati. Sii concreto (es: "nel mese X storicamente si vendono bene Y e Z, considera di aumentare lo stock").

IMPORTANTE: Usa SOLO i numeri dei dati forniti. Sii specifico e operativo."""

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
    from fastapi.responses import Response
    from routes.pdf_helper import FlowPDF, clean_text, C_BLUE, C_EMERALD, C_VIOLET, C_AMBER, C_RED, C_SLATE
    try:
        nome     = clean_text(str(data.get('nome','N/D')))
        tipo     = str(data.get('tipo','prodotto'))
        tipo_lbl = {'prodotto':'Prodotto','cliente':'Cliente','globale':'Vendite Globali'}.get(tipo, tipo.capitalize())
        mese_lbl = clean_text(str(data.get('mese_target_nome','')))
        stats    = data.get('statistiche', {})
        previsioni = data.get('previsioni', [])
        storico    = data.get('storico', [])
        ai_text    = str(data.get('previsione_ai',''))

        media_m   = stats.get('media_mensile', 0)
        tot_prev  = sum(p.get('previsione',0) for p in previsioni)
        media_prev = tot_prev / len(previsioni) if previsioni else 0
        var = (media_prev - media_m) / media_m * 100 if media_m > 0 else 0

        subtitle = f"{tipo_lbl}: {nome}  |  Previsione da {mese_lbl}"
        pdf = FlowPDF("FORECAST AI — PREVISIONI VENDITE", subtitle)
        pdf.add_page()

        pdf.kpi_row([
            ("MEDIA MENSILE STORICA",  f"EUR {media_m:,.2f}",   C_BLUE,    f"{stats.get('num_mesi_dati',0)} mesi dati"),
            ("PREVISIONE TRIMESTRALE", f"EUR {tot_prev:,.2f}",   C_EMERALD, "prossimi 3 mesi"),
            ("MEDIA MENSILE PREVISTA", f"EUR {media_prev:,.2f}", C_VIOLET,  None),
            ("VARIAZ. VS STORICO",     f"{var:+.1f}%",
             C_EMERALD if var >= 0 else C_RED, None),
        ])

        # 3-month forecast table
        pdf.section_title("Previsioni per mese", C_EMERALD, top_gap=3)
        rows_p = []
        for p in previsioni:
            trend_str = f"{p.get('trend',0):+.1f}%"
            rows_p.append([
                clean_text(p.get('mese_nome','')),
                f"{p.get('previsione',0):,.2f}",
                f"{p.get('minimo',0):,.2f}",
                f"{p.get('massimo',0):,.2f}",
                trend_str,
                p.get('confidenza','N/D'),
                str(p.get('anni_dati',0))
            ])
        pdf.smart_table(
            ["Mese","Previsione EUR","Min EUR","Max EUR","Trend YoY","Confidenza","Dati"],
            [34, 34, 30, 30, 22, 28, 12],
            rows_p,
            ['L','R','R','R','R','C','C']
        )

        # Historical bar chart
        if storico:
            pdf.section_title("Storico mensile — ultimi 12 mesi", C_BLUE, top_gap=3)
            pairs = [(s['mese'], s['valore']) for s in storico]
            pdf.monthly_chart(pairs, 'EUR ')

        # AI analysis
        if ai_text.strip():
            pdf.section_title("Analisi AI", C_VIOLET, top_gap=3)
            pdf.ai_text_block(ai_text)

        pdf_bytes = pdf.output()
        safe = nome.replace(' ','_')[:30]
        return Response(bytes(pdf_bytes), media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename=forecast_{safe}.pdf"})
    except Exception as e:
        logger.error(f"Error exporting PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Errore esportazione PDF: {str(e)}")
