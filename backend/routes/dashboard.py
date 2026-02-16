from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta, timezone
import uuid
import os
import random

from database import db, logger
from routes.prodotti import get_prodotti_stats

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard():
    latest_sale = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", -1)])
    if latest_sale and latest_sale.get('data'):
        try:
            reference_date = datetime.strptime(latest_sale['data'], "%Y-%m-%d")
        except Exception:
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()

    current_month_start = reference_date.replace(day=1).strftime("%Y-%m-%d")
    prev_month = reference_date.replace(day=1) - timedelta(days=1)
    prev_month_start = prev_month.replace(day=1).strftime("%Y-%m-%d")
    prev_month_end = prev_month.strftime("%Y-%m-%d")

    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']

    vendite_mese_corrente = await db.vendite.find({"data": {"$gte": current_month_start}}, {"_id": 0}).to_list(100000)
    vendite_mese_corrente = [v for v in vendite_mese_corrente if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]

    fatturato_mese = sum(abs(v.get('totale', 0)) for v in vendite_mese_corrente)
    ordini_mese = len(vendite_mese_corrente)

    vendite_mese_prec = await db.vendite.find({"data": {"$gte": prev_month_start, "$lte": prev_month_end}}, {"_id": 0}).to_list(100000)
    vendite_mese_prec = [v for v in vendite_mese_prec if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    fatturato_mese_prec = sum(abs(v.get('totale', 0)) for v in vendite_mese_prec)
    crescita = ((fatturato_mese - fatturato_mese_prec) / fatturato_mese_prec * 100) if fatturato_mese_prec > 0 else (100 if fatturato_mese > 0 else 0)

    # Unique active clients this month
    EXCLUDED_CLIENTS_DASH = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    clienti_mese_set = set(
        v.get('cliente_nome', '') for v in vendite_mese_corrente
        if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS_DASH]
    )
    nuovi_clienti = len(clienti_mese_set)

    ordini_mese_prec = len(vendite_mese_prec)
    clienti_prec_set = set(
        v.get('cliente_nome', '') for v in vendite_mese_prec
        if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS_DASH]
    )
    clienti_mese_prec = len(clienti_prec_set)
    ordini_crescita = round(((ordini_mese - ordini_mese_prec) / ordini_mese_prec * 100), 1) if ordini_mese_prec > 0 else 0
    clienti_crescita = round(((nuovi_clienti - clienti_mese_prec) / clienti_mese_prec * 100), 1) if clienti_mese_prec > 0 else 0

    prodotti_stats = await get_prodotti_stats()

    attivita_recenti = []
    recent_vendite = await db.vendite.find({}, {"_id": 0}).sort("data", -1).limit(5).to_list(5)
    for v in recent_vendite:
        attivita_recenti.append({
            "tipo": "vendita",
            "descrizione": f"Vendita a {v.get('cliente_nome', 'N/A')}",
            "valore": abs(v.get('totale', 0)),
            "data": v.get('data', '')
        })

    return {
        "fatturatoMese": fatturato_mese,
        "fatturatoMesePrec": fatturato_mese_prec,
        "crescitaPercentuale": round(crescita, 1),
        "ordiniMese": ordini_mese,
        "ordiniMesePrec": ordini_mese_prec,
        "ordiniCrescita": ordini_crescita,
        "nuoviClienti": nuovi_clienti,
        "clientiMesePrec": clienti_mese_prec,
        "clientiCrescita": clienti_crescita,
        "totaleProdotti": prodotti_stats.get('totaleProdotti', 0),
        "valoreScorte": prodotti_stats.get('valoreScorte', 0),
        "sottoScorta": prodotti_stats.get('sottoScorta', 0),
        "prodottiScadenza": prodotti_stats.get('scadenza_count', 0),
        "attivitaRecenti": attivita_recenti
    }


@router.get("/ai-suggestion")
async def get_ai_suggestion():
    import hashlib
    now = datetime.now()
    week_num = now.isocalendar()[1]
    year = now.year
    week_key = f"{year}-W{week_num}"

    cached = await db.ai_suggestions.find_one({"week_key": week_key}, {"_id": 0})
    if cached:
        return cached

    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    ninety_days_ago = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    vendite = await db.vendite.find({"data": {"$gte": ninety_days_ago}}, {"_id": 0}).to_list(10000)
    vendite = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    prodotti = await db.prodotti.find({}, {"_id": 0}).to_list(1000)

    prodotti_revenue = {}
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        prodotti_revenue[prod] = prodotti_revenue.get(prod, 0) + abs(v.get('totale', 0))
    top_products = sorted(prodotti_revenue.items(), key=lambda x: x[1], reverse=True)[:5]
    low_stock = [p for p in prodotti if p.get('quantita', 0) > 0 and p.get('quantita_minima', 0) > 0 and p.get('quantita', 0) <= p.get('quantita_minima', 0)]

    clienti_spending = {}
    for v in vendite:
        c = v.get('cliente_nome', '')
        if c:
            clienti_spending[c] = clienti_spending.get(c, 0) + abs(v.get('totale', 0))
    top_clients = sorted(clienti_spending.items(), key=lambda x: x[1], reverse=True)[:5]
    thirty_days_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    recent_clients = set(v.get('cliente_nome', '') for v in vendite if v.get('data', '') >= thirty_days_ago)
    all_clients = set(v.get('cliente_nome', '') for v in vendite)
    inactive_clients = all_clients - recent_clients

    suggestions = []
    if top_products:
        top_prod_name = top_products[0][0]
        suggestions.append({"tipo": "prodotto_star", "titolo": "Prodotto Star", "messaggio": f"'{top_prod_name}' è il tuo prodotto più venduto. Considera di negoziare un prezzo migliore con il fornitore per aumentare il margine.", "azione": "Contatta il fornitore per sconti volume"})
    if low_stock:
        low_stock_names = [p.get('nome', '') for p in low_stock[:3]]
        suggestions.append({"tipo": "riordino", "titolo": "Riordino Urgente", "messaggio": f"Prodotti sotto scorta minima: {', '.join(low_stock_names)}. Ordina subito per evitare rotture di stock.", "azione": "Vai alla sezione Acquisti"})
    if len(inactive_clients) > 5:
        suggestions.append({"tipo": "clienti_dormienti", "titolo": "Clienti da Riattivare", "messaggio": f"Hai {len(inactive_clients)} clienti che non ordinano da 30+ giorni. Una promozione mirata potrebbe riattivare le vendite.", "azione": "Considera sconti personalizzati o contatto diretto"})
    if top_clients:
        best_client = top_clients[0][0]
        suggestions.append({"tipo": "fidelizzazione", "titolo": "Cliente VIP", "messaggio": f"'{best_client}' è il tuo miglior cliente. Offri un programma fedeltà o sconti esclusivi per mantenerlo.", "azione": "Crea offerta personalizzata"})

    rotating_suggestions = [
        {"tipo": "marketing", "titolo": "Suggerimento Marketing", "messaggio": "Considera di creare un listino prezzi settimanale da inviare ai clienti via WhatsApp per aumentare gli ordini.", "azione": "Prepara listino PDF"},
        {"tipo": "analisi", "titolo": "Analisi Prezzi", "messaggio": "Verifica i prezzi dei concorrenti sul mercato. Piccoli aggiustamenti possono migliorare significativamente i margini.", "azione": "Confronta prezzi mercato"},
        {"tipo": "efficienza", "titolo": "Ottimizza Consegne", "messaggio": "Raggruppa le consegne per zona geografica per ridurre i costi di trasporto e aumentare l'efficienza.", "azione": "Pianifica percorsi ottimali"},
        {"tipo": "cross_selling", "titolo": "Cross-Selling", "messaggio": "Proponi prodotti complementari ai clienti. Chi compra frutta secca potrebbe essere interessato anche a semi e granelle.", "azione": "Crea bundle di prodotti"},
    ]
    rotating_idx = week_num % len(rotating_suggestions)
    suggestions.append(rotating_suggestions[rotating_idx])
    main_suggestion = suggestions[0] if suggestions else rotating_suggestions[rotating_idx]

    result = {"week_key": week_key, "generated_at": now.isoformat(), "suggestion": main_suggestion, "all_suggestions": suggestions[:3]}
    await db.ai_suggestions.update_one({"week_key": week_key}, {"$set": result}, upsert=True)
    return result


@router.post("/ai-suggestion/refresh")
async def refresh_ai_suggestion():
    now = datetime.now()
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    ninety_days_ago = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    vendite = await db.vendite.find({"data": {"$gte": ninety_days_ago}}, {"_id": 0}).to_list(10000)
    vendite = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    prodotti = await db.prodotti.find({}, {"_id": 0}).to_list(1000)

    all_suggestions = []
    prodotti_revenue = {}
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        prodotti_revenue[prod] = prodotti_revenue.get(prod, 0) + abs(v.get('totale', 0))
    top_products = sorted(prodotti_revenue.items(), key=lambda x: x[1], reverse=True)[:5]
    if top_products:
        for i, (prod, rev) in enumerate(top_products[:3]):
            all_suggestions.append({"tipo": "prodotto_star", "titolo": f"Prodotto Top #{i+1}", "messaggio": f"'{prod}' genera molto fatturato. Negozia prezzi migliori o aumenta il margine.", "azione": "Contatta fornitore"})

    low_stock = [p for p in prodotti if p.get('quantita', 0) > 0 and p.get('quantita_minima', 0) > 0 and p.get('quantita', 0) <= p.get('quantita_minima', 0)]
    if low_stock:
        for p in low_stock[:2]:
            all_suggestions.append({"tipo": "riordino", "titolo": "Scorta Bassa", "messaggio": f"'{p.get('nome', '')}' è sotto la quantità minima. Riordina per evitare rotture.", "azione": "Ordina subito"})

    thirty_days_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    recent_clients = set(v.get('cliente_nome', '') for v in vendite if v.get('data', '') >= thirty_days_ago)
    all_clients = set(v.get('cliente_nome', '') for v in vendite)
    inactive_clients = list(all_clients - recent_clients)
    if inactive_clients:
        sample_inactive = random.sample(inactive_clients, min(3, len(inactive_clients)))
        all_suggestions.append({"tipo": "clienti_dormienti", "titolo": "Clienti Inattivi", "messaggio": f"Ricontatta: {', '.join(sample_inactive)}. Non ordinano da 30+ giorni.", "azione": "Invia offerta"})

    marketing_tips = [
        {"titolo": "WhatsApp Marketing", "messaggio": "Invia il listino settimanale via WhatsApp ai tuoi clienti migliori.", "azione": "Crea broadcast"},
        {"titolo": "Promozione Bundle", "messaggio": "Crea pacchetti di prodotti complementari per aumentare lo scontrino medio.", "azione": "Definisci bundle"},
        {"titolo": "Programma Fedeltà", "messaggio": "Premia i clienti più fedeli con sconti progressivi sul volume.", "azione": "Imposta sconti"},
        {"titolo": "Consegna Gratuita", "messaggio": "Offri consegna gratuita sopra una certa soglia per incentivare ordini più grandi.", "azione": "Definisci soglia"},
        {"titolo": "Stagionalità", "messaggio": "Promuovi prodotti di stagione con margini migliori.", "azione": "Aggiorna listino"},
    ]
    for tip in marketing_tips:
        all_suggestions.append({"tipo": "marketing", **tip})

    main_suggestion = random.choice(all_suggestions) if all_suggestions else {"tipo": "marketing", **marketing_tips[0]}
    return {"week_key": f"refresh-{now.isoformat()}", "generated_at": now.isoformat(), "suggestion": main_suggestion, "all_suggestions": random.sample(all_suggestions, min(3, len(all_suggestions))) if all_suggestions else [main_suggestion]}


@router.get("/alerts")
async def get_management_alerts():
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    alerts = {"prodottiSottoScorta": [], "clientiInattivi": [], "prodottiInEsaurimento": []}

    prodotti = await db.prodotti.find({}, {"_id": 0}).to_list(1000)
    for p in prodotti:
        quantita = p.get('quantita', 0)
        quantita_min = p.get('quantita_minima', 0)
        if quantita_min > 0 and quantita <= quantita_min:
            alerts["prodottiSottoScorta"].append({"nome": p.get('nome', ''), "quantita": quantita, "quantita_minima": quantita_min, "urgenza": "alta" if quantita <= 0 else "media"})
    alerts["prodottiSottoScorta"].sort(key=lambda x: (0 if x['urgenza'] == 'alta' else 1, x['quantita']))
    alerts["prodottiSottoScorta"] = alerts["prodottiSottoScorta"][:8]

    latest_sale = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", -1)])
    if latest_sale and latest_sale.get('data'):
        try:
            reference_date = datetime.strptime(latest_sale['data'], "%Y-%m-%d")
        except Exception:
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()

    ninety_days_ago = (reference_date - timedelta(days=90)).strftime("%Y-%m-%d")
    thirty_days_ago = (reference_date - timedelta(days=30)).strftime("%Y-%m-%d")
    vendite = await db.vendite.find({"data": {"$gte": ninety_days_ago}}, {"_id": 0}).to_list(10000)
    vendite = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]

    client_last_order = {}
    client_total = {}
    for v in vendite:
        cliente = v.get('cliente_nome', '')
        if cliente:
            data = v.get('data', '')
            if cliente not in client_last_order or data > client_last_order[cliente]:
                client_last_order[cliente] = data
            client_total[cliente] = client_total.get(cliente, 0) + abs(v.get('totale', 0))

    for cliente, last_order in client_last_order.items():
        days_inactive = (reference_date - datetime.strptime(last_order, "%Y-%m-%d")).days
        if 7 <= days_inactive <= 30:
            alerts["clientiInattivi"].append({"nome": cliente, "ultimo_ordine": last_order, "giorni_inattivo": days_inactive, "fatturato_90gg": round(client_total.get(cliente, 0), 2)})
    alerts["clientiInattivi"].sort(key=lambda x: -x['fatturato_90gg'])
    alerts["clientiInattivi"] = alerts["clientiInattivi"][:8]

    six_months_ago = (reference_date - timedelta(days=180)).strftime("%Y-%m-%d")
    vendite_6m = await db.vendite.find({"data": {"$gte": six_months_ago}}, {"_id": 0}).to_list(10000)
    prodotto_consumption = {}
    for v in vendite_6m:
        prod = v.get('prodotto_nome', '')
        prodotto_consumption[prod] = prodotto_consumption.get(prod, 0) + abs(v.get('quantita', 0))

    for p in prodotti:
        nome = p.get('nome', '')
        quantita = p.get('quantita', 0)
        if quantita > 0 and nome in prodotto_consumption:
            monthly_consumption = prodotto_consumption[nome] / 6
            if monthly_consumption > 0:
                days_left = int(quantita / monthly_consumption * 30)
                if days_left <= 14:
                    alerts["prodottiInEsaurimento"].append({"nome": nome, "quantita": quantita, "consumo_mensile": round(monthly_consumption, 0), "giorni_rimanenti": days_left})
    alerts["prodottiInEsaurimento"].sort(key=lambda x: x['giorni_rimanenti'])
    alerts["prodottiInEsaurimento"] = alerts["prodottiInEsaurimento"][:8]
    return alerts


@router.get("/margine-vendite")
async def get_margine_vendite():
    """Calculate profit margin on sales where we know purchase price"""
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    
    # Get reference date from latest sale
    latest_sale = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", -1)])
    if latest_sale and latest_sale.get('data'):
        try:
            reference_date = datetime.strptime(latest_sale['data'], "%Y-%m-%d")
        except Exception:
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()
    
    current_month_start = reference_date.replace(day=1).strftime("%Y-%m-%d")
    
    # Get current month sales
    vendite = await db.vendite.find({"data": {"$gte": current_month_start}}, {"_id": 0}).to_list(100000)
    vendite = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    
    # Build a map of last purchase price per product
    prodotti_nomi = list(set(v.get('prodotto_nome', '') for v in vendite if v.get('prodotto_nome')))
    prezzi_acquisto = {}
    
    for nome in prodotti_nomi:
        ultimo_ordine = await db.ordini.find_one(
            {"prodotto_nome": nome, "prezzo_unitario": {"$gt": 0}},
            {"_id": 0, "prezzo_unitario": 1},
            sort=[("data", -1)]
        )
        if ultimo_ordine:
            prezzo = ultimo_ordine.get('prezzo_unitario', 0)
            # Filter out anomalous prices (likely data entry errors)
            if 0 < prezzo < 500:  # Reasonable price range
                prezzi_acquisto[nome] = prezzo
    
    # Calculate margin for each sale
    totale_fatturato = 0
    totale_costo = 0
    prodotti_con_margine = 0
    margini_prodotto = []
    
    prodotti_vendite = {}
    for v in vendite:
        nome = v.get('prodotto_nome', '')
        prezzo_vendita = v.get('prezzo_unitario', 0)
        quantita = abs(v.get('quantita', 0))
        totale_vendita = abs(v.get('totale', 0))
        
        if nome in prezzi_acquisto and prezzo_vendita > 0:
            prezzo_acquisto = prezzi_acquisto[nome]
            
            # Skip if sale price is unreasonably different from purchase price
            if prezzo_vendita > prezzo_acquisto * 5 or prezzo_vendita < prezzo_acquisto * 0.2:
                continue
            
            if nome not in prodotti_vendite:
                prodotti_vendite[nome] = {
                    'fatturato': 0, 'costo': 0, 'quantita': 0,
                    'prezzo_vendita': prezzo_vendita, 'prezzo_acquisto': prezzo_acquisto
                }
            
            prodotti_vendite[nome]['fatturato'] += totale_vendita
            prodotti_vendite[nome]['costo'] += prezzo_acquisto * quantita
            prodotti_vendite[nome]['quantita'] += quantita
    
    for nome, dati in prodotti_vendite.items():
        if dati['fatturato'] > 0 and dati['costo'] > 0:
            margine_pct = ((dati['fatturato'] - dati['costo']) / dati['costo']) * 100
            profitto = dati['fatturato'] - dati['costo']
            
            # Only include products with reasonable margins (-50% to +200%)
            if -50 < margine_pct < 200:
                totale_fatturato += dati['fatturato']
                totale_costo += dati['costo']
                prodotti_con_margine += 1
                
                margini_prodotto.append({
                    'prodotto': nome,
                    'fatturato': round(dati['fatturato'], 2),
                    'costo': round(dati['costo'], 2),
                    'profitto': round(profitto, 2),
                    'margine_pct': round(margine_pct, 1),
                    'prezzo_vendita': round(dati['prezzo_vendita'], 2),
                    'prezzo_acquisto': round(dati['prezzo_acquisto'], 2)
                })
    
    # Sort by profit
    margini_prodotto.sort(key=lambda x: x['profitto'], reverse=True)
    
    # Calculate averages
    margine_medio_pct = ((totale_fatturato - totale_costo) / totale_costo * 100) if totale_costo > 0 else 0
    profitto_totale = totale_fatturato - totale_costo
    
    return {
        "mese_riferimento": current_month_start[:7],
        "margine_medio_pct": round(margine_medio_pct, 1),
        "profitto_totale": round(profitto_totale, 2),
        "totale_fatturato": round(totale_fatturato, 2),
        "totale_costo": round(totale_costo, 2),
        "prodotti_con_margine": prodotti_con_margine,
        "top_margini": margini_prodotto[:10],
        "worst_margini": sorted(margini_prodotto, key=lambda x: x['margine_pct'])[:5]
    }


@router.get("/sales-insight")
async def get_sales_insight():
    latest_sale = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", -1)])
    if latest_sale and latest_sale.get('data'):
        try:
            reference_date = datetime.strptime(latest_sale['data'], "%Y-%m-%d")
        except Exception:
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()

    current_month_start = reference_date.replace(day=1).strftime("%Y-%m-%d")
    prev_month = reference_date.replace(day=1) - timedelta(days=1)
    prev_month_start = prev_month.replace(day=1).strftime("%Y-%m-%d")
    prev_month_end = prev_month.strftime("%Y-%m-%d")
    last_30_days = (reference_date - timedelta(days=30)).strftime("%Y-%m-%d")
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']

    insights = []

    # 1. Top product & client this month + prev month products (single query each via aggregation)
    prodotti_mese_pipeline = [
        {"$match": {"data": {"$gte": current_month_start}}},
        {"$group": {"_id": "$prodotto_nome", "fatturato": {"$sum": {"$abs": "$totale"}}, "qty": {"$sum": {"$abs": "$quantita"}}}}
    ]
    prodotti_mese_agg = await db.vendite.aggregate(prodotti_mese_pipeline).to_list(5000)
    prodotti_mese = {p['_id']: {'fatturato': p['fatturato'], 'qty': p['qty']} for p in prodotti_mese_agg if p['_id']}

    if prodotti_mese:
        best_prod_name = max(prodotti_mese, key=lambda k: prodotti_mese[k]['fatturato'])
        best_prod = prodotti_mese[best_prod_name]
        insights.append({"tipo": "top_product", "icona": "\U0001F3C6", "titolo": "Prodotto Top del Mese", "valore": best_prod_name, "dettaglio": f"\u20ac{best_prod['fatturato']:,.0f} \u2022 {best_prod['qty']:,.0f} unit\u00e0", "colore": "emerald"})

    # 2. Growth product vs prev month
    prodotti_prev_pipeline = [
        {"$match": {"data": {"$gte": prev_month_start, "$lte": prev_month_end}}},
        {"$group": {"_id": "$prodotto_nome", "fatturato": {"$sum": {"$abs": "$totale"}}}}
    ]
    prodotti_prev_agg = await db.vendite.aggregate(prodotti_prev_pipeline).to_list(5000)
    prodotti_prev = {p['_id']: p['fatturato'] for p in prodotti_prev_agg if p['_id']}

    best_growth = None
    for prod, curr_data in prodotti_mese.items():
        prev_fatt = prodotti_prev.get(prod, 0)
        if prev_fatt > 0 and curr_data['fatturato'] > prev_fatt:
            crescita_pct = ((curr_data['fatturato'] - prev_fatt) / prev_fatt) * 100
            if crescita_pct > 10 and (not best_growth or crescita_pct > best_growth[1]):
                best_growth = (prod, crescita_pct, curr_data['fatturato'])
    if best_growth:
        insights.append({"tipo": "growth_product", "icona": "\U0001F4C8", "titolo": "Crescita Maggiore", "valore": best_growth[0], "dettaglio": f"+{best_growth[1]:.0f}% vs mese prec. \u2022 \u20ac{best_growth[2]:,.0f}", "colore": "cyan"})

    # 3. Top client this month
    clienti_mese_pipeline = [
        {"$match": {"data": {"$gte": current_month_start}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
        {"$group": {"_id": "$cliente_nome", "totale": {"$sum": {"$abs": "$totale"}}}},
        {"$sort": {"totale": -1}},
        {"$limit": 1}
    ]
    top_client_agg = await db.vendite.aggregate(clienti_mese_pipeline).to_list(1)
    if top_client_agg and top_client_agg[0]['_id']:
        tc = top_client_agg[0]
        nome = tc['_id']
        insights.append({"tipo": "top_client", "icona": "\U0001F464", "titolo": "Miglior Cliente del Mese", "valore": nome[:25] + ('...' if len(nome) > 25 else ''), "dettaglio": f"\u20ac{tc['totale']:,.0f} di acquisti", "colore": "violet"})

    # 4. Restock alert (from prodotti collection - fast)
    prodotti_critici = await db.prodotti.find(
        {"quantita_minima": {"$gt": 0}, "$expr": {"$and": [{"$gt": ["$quantita", 0]}, {"$lte": ["$quantita", {"$multiply": ["$quantita_minima", 1.2]}]}]}},
        {"_id": 0, "nome": 1, "quantita": 1, "quantita_minima": 1}
    ).sort("quantita", 1).limit(1).to_list(1)
    if prodotti_critici:
        c = prodotti_critici[0]
        nome = c.get('nome', '')
        insights.append({"tipo": "restock_alert", "icona": "\u26a0\ufe0f", "titolo": "Da Riordinare Presto", "valore": nome[:20] + ('...' if len(nome) > 20 else ''), "dettaglio": f"Rimaste {c.get('quantita', 0):.0f} (min: {c.get('quantita_minima', 0):.0f})", "colore": "amber"})

    # 5. New client this month (aggregation: find clients whose first sale is this month)
    new_client_pipeline = [
        {"$match": {"cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
        {"$group": {"_id": "$cliente_nome", "prima_vendita": {"$min": "$data"}, "totale_mese": {"$sum": {"$cond": [{"$gte": ["$data", current_month_start]}, {"$abs": "$totale"}, 0]}}}},
        {"$match": {"prima_vendita": {"$gte": current_month_start}}},
        {"$sort": {"totale_mese": -1}},
        {"$limit": 1}
    ]
    new_clients = await db.vendite.aggregate(new_client_pipeline).to_list(1)
    if new_clients and new_clients[0]['_id']:
        nc = new_clients[0]
        nome = nc['_id']
        insights.append({"tipo": "new_client", "icona": "\U0001F195", "titolo": "Nuovo Cliente Acquisito", "valore": nome[:25] + ('...' if len(nome) > 25 else ''), "dettaglio": f"\u20ac{nc['totale_mese']:,.0f} dal {nc['prima_vendita']}", "colore": "blue"})

    # 6. Best margin (from prodotti with prezzo_medio + current month sales)
    prodotti_con_prezzo = await db.prodotti.find({"prezzo_medio": {"$gt": 0}}, {"_id": 0, "nome": 1, "prezzo_medio": 1}).to_list(5000)
    prezzo_acquisto_map = {p['nome']: p['prezzo_medio'] for p in prodotti_con_prezzo}

    margine_pipeline = [
        {"$match": {"data": {"$gte": current_month_start}, "prodotto_nome": {"$in": list(prezzo_acquisto_map.keys())}, "prezzo_unitario": {"$gt": 0}}},
        {"$group": {"_id": "$prodotto_nome", "prezzo_medio_vendita": {"$avg": "$prezzo_unitario"}, "fatturato": {"$sum": {"$abs": "$totale"}}}}
    ]
    margini_agg = await db.vendite.aggregate(margine_pipeline).to_list(5000)
    best_margin = None
    for m in margini_agg:
        nome = m['_id']
        pa = prezzo_acquisto_map.get(nome, 0)
        pv = m['prezzo_medio_vendita']
        fatt = m['fatturato']
        if pa > 0 and pv > pa and fatt > 100:
            margine_pct = ((pv - pa) / pa) * 100
            score = margine_pct * min(fatt, 1000)
            if not best_margin or score > best_margin[5]:
                best_margin = (nome, margine_pct, pv, pa, fatt, score)
    if best_margin:
        insights.append({"tipo": "best_margin", "icona": "\U0001F4B0", "titolo": "Margine Migliore", "valore": best_margin[0][:20] + ('...' if len(best_margin[0]) > 20 else ''), "dettaglio": f"+{best_margin[1]:.0f}% (\u20ac{best_margin[2]:.2f} vs \u20ac{best_margin[3]:.2f})", "colore": "emerald"})

    # 7. Fastest selling product (30 days)
    velocity_pipeline = [
        {"$match": {"data": {"$gte": last_30_days}}},
        {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": {"$abs": "$quantita"}}}},
        {"$sort": {"qty": -1}},
        {"$limit": 1}
    ]
    fastest = await db.vendite.aggregate(velocity_pipeline).to_list(1)
    if fastest and fastest[0]['_id']:
        f = fastest[0]
        media_g = f['qty'] / 30
        nome = f['_id']
        insights.append({"tipo": "velocity", "icona": "\U0001F680", "titolo": "Prodotto Pi\u00f9 Venduto (30gg)", "valore": nome[:20] + ('...' if len(nome) > 20 else ''), "dettaglio": f"{f['qty']:,.0f} unit\u00e0 \u2022 ~{media_g:.1f}/giorno", "colore": "rose"})

    # Summary stats
    fatturato_mese = sum(d['fatturato'] for d in prodotti_mese.values())
    fatturato_prev = sum(prodotti_prev.values())
    diff_pct = ((fatturato_mese - fatturato_prev) / fatturato_prev * 100) if fatturato_prev > 0 else 0

    # Count unique clients
    clienti_count_pipeline = [
        {"$match": {"data": {"$gte": current_month_start}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
        {"$group": {"_id": "$cliente_nome"}},
        {"$count": "total"}
    ]
    clienti_count = await db.vendite.aggregate(clienti_count_pipeline).to_list(1)
    num_clienti = clienti_count[0]['total'] if clienti_count else 0

    mesi_it = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
    mese_nome = mesi_it[reference_date.month - 1]

    return {
        "mese_riferimento": f"{mese_nome} {reference_date.year}",
        "data_aggiornamento": reference_date.strftime("%Y-%m-%d"),
        "riepilogo": {"fatturato_mese": round(fatturato_mese, 2), "fatturato_prev": round(fatturato_prev, 2), "variazione_pct": round(diff_pct, 1), "num_vendite": 0, "num_clienti_attivi": num_clienti, "num_prodotti_venduti": len(prodotti_mese)},
        "insights": insights[:6]
    }


@router.get("/dashboard/card-detail/{card_type}")
async def get_card_detail(card_type: str, periodo: str = "mese"):
    """Get detailed analytics for each KPI card popup"""
    latest_sale = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", -1)])
    if latest_sale and latest_sale.get('data'):
        try:
            ref = datetime.strptime(latest_sale['data'], "%Y-%m-%d")
        except Exception:
            ref = datetime.now()
    else:
        ref = datetime.now()

    month_start = ref.replace(day=1).strftime("%Y-%m-%d")
    prev_m = ref.replace(day=1) - timedelta(days=1)
    prev_start = prev_m.replace(day=1).strftime("%Y-%m-%d")
    prev_end = prev_m.strftime("%Y-%m-%d")
    EXCLUDED = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']

    # Compute date_start based on periodo for fatturato/ordini
    if periodo == "30gg":
        date_start = (ref - timedelta(days=30)).strftime("%Y-%m-%d")
    elif periodo == "90gg":
        date_start = (ref - timedelta(days=90)).strftime("%Y-%m-%d")
    else:
        date_start = month_start
    periodo_labels = {"mese": "Mese corrente", "30gg": "Ultimi 30 giorni", "90gg": "Ultimi 90 giorni"}

    if card_type == "fatturato":
        daily_pipeline = [
            {"$match": {"data": {"$gte": date_start}, "cliente_nome": {"$nin": EXCLUDED}}},
            {"$group": {"_id": "$data", "totale": {"$sum": {"$abs": "$totale"}}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        daily = await db.vendite.aggregate(daily_pipeline).to_list(90)
        top_prod_pipeline = [
            {"$match": {"data": {"$gte": date_start}}},
            {"$group": {"_id": "$prodotto_nome", "totale": {"$sum": {"$abs": "$totale"}}}},
            {"$sort": {"totale": -1}}, {"$limit": 5}
        ]
        top_prod = await db.vendite.aggregate(top_prod_pipeline).to_list(5)
        week_pipeline = [
            {"$match": {"data": {"$gte": date_start}}},
            {"$addFields": {"giorno": {"$dayOfMonth": {"$dateFromString": {"dateString": "$data"}}}}},
            {"$addFields": {"settimana": {"$ceil": {"$divide": ["$giorno", 7]}}}},
            {"$group": {"_id": "$settimana", "totale": {"$sum": {"$abs": "$totale"}}}},
            {"$sort": {"_id": 1}}
        ]
        weekly = await db.vendite.aggregate(week_pipeline).to_list(15)
        return {
            "tipo": "fatturato",
            "periodo_label": periodo_labels.get(periodo, periodo),
            "giornaliero": [{"data": d["_id"], "totale": round(d["totale"], 2), "ordini": d["count"]} for d in daily],
            "top_prodotti": [{"nome": p["_id"], "totale": round(p["totale"], 2)} for p in top_prod],
            "settimanale": [{"settimana": f"Sett. {w['_id']}", "totale": round(w["totale"], 2)} for w in weekly]
        }

    elif card_type == "ordini":
        # Scontrino medio = totale per visita (cliente + data)
        scontrino_pipeline = [
            {"$match": {"data": {"$gte": month_start}, "cliente_nome": {"$nin": EXCLUDED}}},
            {"$group": {"_id": {"cliente": "$cliente_nome", "data": "$data"}, "totale_visita": {"$sum": {"$abs": "$totale"}}}},
            {"$group": {"_id": None, "media": {"$avg": "$totale_visita"}, "num_visite": {"$sum": 1}, "totale": {"$sum": "$totale_visita"}}}
        ]
        scontrino_res = await db.vendite.aggregate(scontrino_pipeline).to_list(1)
        avg_order = scontrino_res[0]["media"] if scontrino_res else 0
        num_visite = scontrino_res[0]["num_visite"] if scontrino_res else 0
        # Daily orders (by unique client visits per day)
        daily_pipeline = [
            {"$match": {"data": {"$gte": month_start}, "cliente_nome": {"$nin": EXCLUDED}}},
            {"$group": {"_id": {"data": "$data", "cliente": "$cliente_nome"}, "totale_visita": {"$sum": {"$abs": "$totale"}}}},
            {"$group": {"_id": "$_id.data", "visite": {"$sum": 1}, "totale": {"$sum": "$totale_visita"}}},
            {"$sort": {"_id": 1}}
        ]
        daily = await db.vendite.aggregate(daily_pipeline).to_list(31)
        # Top products by number of requests (orders count)
        req_pipeline = [
            {"$match": {"data": {"$gte": month_start}}},
            {"$group": {"_id": "$prodotto_nome", "richieste": {"$sum": 1}, "quantita": {"$sum": {"$abs": "$quantita"}}}},
            {"$sort": {"richieste": -1}}, {"$limit": 5}
        ]
        top_req = await db.vendite.aggregate(req_pipeline).to_list(5)
        # Peak days
        peak_pipeline = [
            {"$match": {"data": {"$gte": month_start}, "cliente_nome": {"$nin": EXCLUDED}}},
            {"$group": {"_id": {"data": "$data", "cliente": "$cliente_nome"}}},
            {"$group": {"_id": "$_id.data", "visite": {"$sum": 1}}},
            {"$sort": {"visite": -1}}, {"$limit": 3}
        ]
        peak = await db.vendite.aggregate(peak_pipeline).to_list(3)
        return {
            "tipo": "ordini",
            "giornaliero": [{"data": d["_id"], "ordini": d["visite"], "totale": round(d["totale"], 2)} for d in daily],
            "scontrino_medio": round(avg_order, 2),
            "num_visite_totali": num_visite,
            "top_prodotti_richieste": [{"nome": p["_id"], "richieste": p["richieste"], "quantita": round(p["quantita"], 1)} for p in top_req],
            "giorni_picco": [{"data": p["_id"], "ordini": p["visite"]} for p in peak]
        }

    elif card_type == "clienti":
        # Determine date filter based on periodo
        if periodo == "30gg":
            date_start = (ref - timedelta(days=30)).strftime("%Y-%m-%d")
        elif periodo == "90gg":
            date_start = (ref - timedelta(days=90)).strftime("%Y-%m-%d")
        else:  # "mese" default
            date_start = month_start

        periodo_labels = {"mese": "Mese corrente", "30gg": "Ultimi 30 giorni", "90gg": "Ultimi 90 giorni"}

        # Top clients
        top_pipeline = [
            {"$match": {"data": {"$gte": date_start}, "cliente_nome": {"$nin": EXCLUDED}}},
            {"$group": {"_id": "$cliente_nome", "totale": {"$sum": {"$abs": "$totale"}}, "ordini": {"$sum": 1}}},
            {"$sort": {"totale": -1}}, {"$limit": 5}
        ]
        top_cli = await db.vendite.aggregate(top_pipeline).to_list(5)
        # New clients (first purchase in period)
        new_pipeline = [
            {"$match": {"cliente_nome": {"$nin": EXCLUDED}}},
            {"$group": {"_id": "$cliente_nome", "prima_vendita": {"$min": "$data"}, "totale_periodo": {"$sum": {"$cond": [{"$gte": ["$data", date_start]}, {"$abs": "$totale"}, 0]}}}},
            {"$match": {"prima_vendita": {"$gte": date_start}}},
            {"$sort": {"totale_periodo": -1}}, {"$limit": 5}
        ]
        new_cli = await db.vendite.aggregate(new_pipeline).to_list(5)
        # Most frequent
        freq_pipeline = [
            {"$match": {"data": {"$gte": date_start}, "cliente_nome": {"$nin": EXCLUDED}}},
            {"$group": {"_id": "$cliente_nome", "visite": {"$sum": 1}}},
            {"$sort": {"visite": -1}}, {"$limit": 5}
        ]
        freq_cli = await db.vendite.aggregate(freq_pipeline).to_list(5)
        return {
            "tipo": "clienti",
            "periodo_label": periodo_labels.get(periodo, periodo),
            "top_clienti": [{"nome": c["_id"], "totale": round(c["totale"], 2), "ordini": c["ordini"]} for c in top_cli],
            "nuovi_clienti": [{"nome": c["_id"], "totale": round(c["totale_periodo"], 2), "dal": c["prima_vendita"]} for c in new_cli],
            "piu_frequenti": [{"nome": c["_id"], "visite": c["visite"]} for c in freq_cli]
        }

    elif card_type == "alert":
        # Determine periodo for inactive clients
        if periodo == "7gg":
            inattivo_min, inattivo_max = 3, 7
        elif periodo == "30gg":
            inattivo_min, inattivo_max = 7, 30
        elif periodo == "60gg":
            inattivo_min, inattivo_max = 30, 60
        else:  # default: 7-30gg
            inattivo_min, inattivo_max = 7, 30

        # Products under minimum stock
        sotto_scorta = await db.prodotti.find(
            {"quantita_minima": {"$gt": 0}, "$expr": {"$lte": ["$quantita", "$quantita_minima"]}},
            {"_id": 0, "nome": 1, "quantita": 1, "quantita_minima": 1}
        ).sort("quantita", 1).limit(15).to_list(15)

        # Products running low (within 120% of minimum)
        in_esaurimento = await db.prodotti.find(
            {"quantita_minima": {"$gt": 0},
             "$expr": {"$and": [{"$gt": ["$quantita", "$quantita_minima"]}, {"$lte": ["$quantita", {"$multiply": ["$quantita_minima", 1.2]}]}]}},
            {"_id": 0, "nome": 1, "quantita": 1, "quantita_minima": 1}
        ).sort("quantita", 1).limit(10).to_list(10)

        # Products expiring soon (next 30 days)
        now_str = datetime.now().strftime("%Y-%m-%d")
        exp_str = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        in_scadenza = await db.prodotti.find(
            {"scadenza": {"$gte": now_str, "$lte": exp_str}, "quantita": {"$gt": 0}},
            {"_id": 0, "nome": 1, "scadenza": 1, "quantita": 1}
        ).sort("scadenza", 1).limit(10).to_list(10)

        # Inactive clients with detailed info
        range_start = (ref - timedelta(days=90)).strftime("%Y-%m-%d")
        inattivi_pipeline = [
            {"$match": {"data": {"$gte": range_start}, "cliente_nome": {"$nin": EXCLUDED}}},
            {"$group": {
                "_id": "$cliente_nome",
                "ultimo_ordine": {"$max": "$data"},
                "fatturato_totale": {"$sum": {"$abs": "$totale"}},
                "num_ordini": {"$sum": 1},
                "prodotti": {"$addToSet": "$prodotto_nome"}
            }},
            {"$sort": {"fatturato_totale": -1}}
        ]
        all_clients = await db.vendite.aggregate(inattivi_pipeline).to_list(1000)
        clienti_inattivi = []
        for c in all_clients:
            try:
                last = datetime.strptime(c["ultimo_ordine"], "%Y-%m-%d")
                days = (ref - last).days
                if inattivo_min <= days <= inattivo_max:
                    top_prods = c.get("prodotti", [])[:3]
                    clienti_inattivi.append({
                        "nome": c["_id"],
                        "ultimo_ordine": c["ultimo_ordine"],
                        "giorni_inattivo": days,
                        "fatturato_90gg": round(c["fatturato_totale"], 2),
                        "num_ordini": c["num_ordini"],
                        "top_prodotti": top_prods
                    })
            except Exception:
                pass
        clienti_inattivi = clienti_inattivi[:10]

        return {
            "tipo": "alert",
            "sotto_scorta": [{"nome": p["nome"], "quantita": round(p["quantita"], 1), "minima": round(p["quantita_minima"], 1)} for p in sotto_scorta],
            "in_esaurimento": [{"nome": p["nome"], "quantita": round(p["quantita"], 1), "minima": round(p["quantita_minima"], 1)} for p in in_esaurimento],
            "in_scadenza": [{"nome": p["nome"], "scadenza": p.get("scadenza", ""), "quantita": round(p["quantita"], 1)} for p in in_scadenza],
            "clienti_inattivi": clienti_inattivi
        }

    raise HTTPException(status_code=400, detail="Tipo card non valido")



@router.get("/ai-reports")
async def get_ai_reports():
    reports = await db.ai_reports.find({}, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    return reports


@router.get("/ai-reports/{report_id}")
async def get_ai_report(report_id: str):
    report = await db.ai_reports.find_one({"id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report non trovato")
    return report


@router.delete("/ai-reports/{report_id}")
async def delete_ai_report(report_id: str):
    result = await db.ai_reports.delete_one({"id": report_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Report non trovato")
    return {"success": True, "message": "Report eliminato"}


@router.post("/ai-reports/generate")
async def generate_ai_report(report_type: str = Query("settimanale", enum=["settimanale", "mensile"])):
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    now = datetime.now()

    if report_type == "settimanale":
        start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        period_name = "Settimana"
    else:
        start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        period_name = "Mese"
    end_date = now.strftime("%Y-%m-%d")

    vendite = await db.vendite.find({"data": {"$gte": start_date}}, {"_id": 0}).to_list(10000)
    vendite = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    ordini = await db.ordini.find({"data": {"$gte": start_date}}, {"_id": 0}).to_list(5000)
    prodotti = await db.prodotti.find({}, {"_id": 0}).to_list(1000)
    clienti = await db.clienti.find({}, {"_id": 0}).to_list(1000)

    fatturato_totale = sum(abs(v.get('totale', 0)) for v in vendite)
    num_vendite = len(vendite)
    prodotti_revenue = {}
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        prodotti_revenue[prod] = prodotti_revenue.get(prod, 0) + abs(v.get('totale', 0))
    top_products = sorted(prodotti_revenue.items(), key=lambda x: x[1], reverse=True)[:5]

    clienti_spending = {}
    for v in vendite:
        c = v.get('cliente_nome', '')
        if c:
            clienti_spending[c] = clienti_spending.get(c, 0) + abs(v.get('totale', 0))
    top_clients = sorted(clienti_spending.items(), key=lambda x: x[1], reverse=True)[:5]

    low_stock = [p for p in prodotti if p.get('quantita', 0) > 0 and p.get('quantita_minima', 0) > 0 and p.get('quantita', 0) <= p.get('quantita_minima', 0)]
    recent_clients = set(v.get('cliente_nome', '') for v in vendite)
    all_historical_clients = set(c.get('nome', '') for c in clienti)
    inactive_clients = list(all_historical_clients - recent_clients)[:10]
    acquisti_totale = sum(abs(o.get('totale', 0)) for o in ordini)

    data_summary = f"""
DATI AZIENDALI - {period_name} dal {start_date} al {end_date}

FATTURATO E VENDITE:
- Fatturato totale: €{fatturato_totale:,.2f}
- Numero transazioni: {num_vendite}
- Media per transazione: €{fatturato_totale/num_vendite if num_vendite > 0 else 0:,.2f}

TOP 5 PRODOTTI (per fatturato):
{chr(10).join([f"- {p[0]}: €{p[1]:,.2f}" for p in top_products]) if top_products else "- Nessun dato"}

TOP 5 CLIENTI (per spesa):
{chr(10).join([f"- {c[0]}: €{c[1]:,.2f}" for c in top_clients]) if top_clients else "- Nessun dato"}

MAGAZZINO:
- Prodotti totali: {len(prodotti)}
- Prodotti sotto scorta minima: {len(low_stock)}
{chr(10).join([f"  * {p.get('nome', '')}: {p.get('quantita', 0)}/{p.get('quantita_minima', 0)}" for p in low_stock[:5]]) if low_stock else ""}

ACQUISTI:
- Totale acquisti periodo: €{acquisti_totale:,.2f}

CLIENTI:
- Clienti attivi nel periodo: {len(recent_clients)}
- Clienti inattivi (da ricontattare): {len(inactive_clients)}
{chr(10).join([f"  * {c}" for c in inactive_clients[:5]]) if inactive_clients else ""}
"""

    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="API key LLM non configurata")

    try:
        chat = LlmChat(api_key=api_key, session_id=f"report-{uuid.uuid4()}", system_message="""Sei un analista business esperto nel settore ortofrutticolo italiano.
Il tuo compito è generare report aziendali chiari, professionali e actionable in italiano.
Usa un tono professionale ma accessibile. Struttura il report in sezioni chiare.
Fornisci sempre suggerimenti concreti e specifici basati sui dati.""").with_model("openai", "gpt-4o")

        prompt = f"""Genera un report {report_type} professionale basato sui seguenti dati aziendali.

{data_summary}

Il report deve includere:
1. **Sommario Esecutivo** - panoramica rapida dei risultati chiave
2. **Performance Vendite** - analisi del fatturato e trend
3. **Prodotti** - analisi dei best seller e suggerimenti
4. **Clienti** - analisi dei top clienti e strategia per clienti inattivi
5. **Magazzino** - alert scorte e suggerimenti di riordino
6. **Raccomandazioni** - 3-5 azioni concrete

Formatta il report in markdown."""

        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)

        report_id = str(uuid.uuid4())[:8]
        report = {
            "id": report_id, "tipo": report_type, "periodo_inizio": start_date, "periodo_fine": end_date,
            "contenuto": response,
            "metriche": {
                "fatturato": fatturato_totale, "num_vendite": num_vendite,
                "top_prodotti": [{"nome": p[0], "fatturato": p[1]} for p in top_products[:3]],
                "top_clienti": [{"nome": c[0], "spesa": c[1]} for c in top_clients[:3]],
                "prodotti_sotto_scorta": len(low_stock), "clienti_inattivi": len(inactive_clients)
            },
            "created_at": now.isoformat()
        }
        await db.ai_reports.insert_one(report)
        report.pop('_id', None)
        return report
    except Exception as e:
        logger.error(f"Error generating AI report: {e}")
        raise HTTPException(status_code=500, detail=f"Errore generazione report: {str(e)}")
