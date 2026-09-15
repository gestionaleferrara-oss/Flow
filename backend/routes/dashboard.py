from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta, timezone
import uuid
import os
import random

from database import db, logger
from routes.pdf_helper import it_num
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
    from routes.esclusioni import get_prodotti_esclusi_set
    prod_esclusi = await get_prodotti_esclusi_set()

    def _keep(v):
        return (v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]
                and v.get('prodotto_nome', '') not in prod_esclusi)

    vendite_mese_corrente = await db.vendite.find({"data": {"$gte": current_month_start}}, {"_id": 0}).to_list(100000)
    vendite_mese_corrente = [v for v in vendite_mese_corrente if _keep(v)]

    fatturato_mese = sum(abs(v.get('totale', 0)) for v in vendite_mese_corrente)
    # An "order" = one customer on one day (unique cliente+data), not individual product lines
    ordini_mese = len(set((v.get('cliente_nome', ''), v.get('data', '')) for v in vendite_mese_corrente))

    vendite_mese_prec = await db.vendite.find({"data": {"$gte": prev_month_start, "$lte": prev_month_end}}, {"_id": 0}).to_list(100000)
    vendite_mese_prec = [v for v in vendite_mese_prec if _keep(v)]
    fatturato_mese_prec = sum(abs(v.get('totale', 0)) for v in vendite_mese_prec)
    crescita = ((fatturato_mese - fatturato_mese_prec) / fatturato_mese_prec * 100) if fatturato_mese_prec > 0 else (100 if fatturato_mese > 0 else 0)

    # Unique active clients this month
    EXCLUDED_CLIENTS_DASH = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    clienti_mese_set = set(
        v.get('cliente_nome', '') for v in vendite_mese_corrente
        if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS_DASH]
    )
    nuovi_clienti = len(clienti_mese_set)

    ordini_mese_prec = len(set((v.get('cliente_nome', ''), v.get('data', '')) for v in vendite_mese_prec))
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
    """Margine reale sulle vendite del mese usando il costo FIFO lotto per lotto."""
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    from routes.esclusioni import get_prodotti_esclusi
    prod_esclusi = await get_prodotti_esclusi()

    latest_sale = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", -1)])
    if latest_sale and latest_sale.get('data'):
        try:
            reference_date = datetime.strptime(latest_sale['data'], "%Y-%m-%d")
        except Exception:
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()

    current_month_start = reference_date.replace(day=1).strftime("%Y-%m-%d")
    match = {"data": {"$gte": current_month_start}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}
    if prod_esclusi:
        match["prodotto_nome"] = {"$nin": prod_esclusi}

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$prodotto_nome",
            "fatturato": {"$sum": {"$abs": "$totale"}},
            "quantita": {"$sum": {"$abs": "$quantita"}},
            "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
            "qty_tracciata": {"$sum": {"$cond": [{"$eq": ["$fifo_tracciato", True]}, {"$abs": "$quantita"}, 0]}},
        }},
    ]
    rows = await db.vendite.aggregate(pipeline).to_list(20000)

    totale_fatturato = totale_costo = 0.0
    margini_prodotto = []
    for r in rows:
        nome, fatt, qty, costo = r['_id'], r['fatturato'], r['quantita'], r['costo']
        if not nome or costo <= 0 or fatt <= 0 or qty <= 0:
            continue
        margine_pct = (fatt - costo) / costo * 100
        totale_fatturato += fatt
        totale_costo += costo
        margini_prodotto.append({
            'prodotto': nome,
            'fatturato': round(fatt, 2),
            'costo': round(costo, 2),
            'profitto': round(fatt - costo, 2),
            'margine_pct': round(margine_pct, 1),
            'prezzo_vendita': round(fatt / qty, 2),
            'prezzo_acquisto': round(costo / qty, 2),
            'copertura_lotti_pct': round(r.get('qty_tracciata', 0) / qty * 100, 0),
        })

    margini_prodotto.sort(key=lambda x: x['profitto'], reverse=True)
    margine_medio_pct = ((totale_fatturato - totale_costo) / totale_costo * 100) if totale_costo > 0 else 0

    return {
        "mese_riferimento": current_month_start[:7],
        "metodo": "FIFO (costo reale del lotto)",
        "margine_medio_pct": round(margine_medio_pct, 1),
        "profitto_totale": round(totale_fatturato - totale_costo, 2),
        "totale_fatturato": round(totale_fatturato, 2),
        "totale_costo": round(totale_costo, 2),
        "prodotti_con_margine": len(margini_prodotto),
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
    from routes.esclusioni import get_prodotti_esclusi
    prod_esclusi = await get_prodotti_esclusi()
    excl_prod = {"prodotto_nome": {"$nin": prod_esclusi}} if prod_esclusi else {}
    esclusi_set = set(prod_esclusi)

    insights = []

    # 1. Top product & client this month + prev month products (single query each via aggregation)
    prodotti_mese_pipeline = [
        {"$match": {"data": {"$gte": current_month_start}, **excl_prod}},
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
        {"$match": {"data": {"$gte": prev_month_start, "$lte": prev_month_end}, **excl_prod}},
        {"$group": {"_id": "$prodotto_nome", "fatturato": {"$sum": {"$abs": "$totale"}}}}
    ]
    prodotti_prev_agg = await db.vendite.aggregate(prodotti_prev_pipeline).to_list(5000)
    prodotti_prev = {p['_id']: p['fatturato'] for p in prodotti_prev_agg if p['_id']}

    best_growth = None
    for prod, curr_data in prodotti_mese.items():
        prev_fatt = prodotti_prev.get(prod, 0)
        # Require minimum €50 previous month to avoid extreme percentages
        if prev_fatt >= 50 and curr_data['fatturato'] > prev_fatt:
            crescita_pct = ((curr_data['fatturato'] - prev_fatt) / prev_fatt) * 100
            # Cap growth at 500% for display purposes
            crescita_pct_display = min(crescita_pct, 500)
            if crescita_pct > 10 and (not best_growth or crescita_pct > best_growth[1]):
                best_growth = (prod, crescita_pct_display, curr_data['fatturato'])
    if best_growth:
        insights.append({"tipo": "growth_product", "icona": "\U0001F4C8", "titolo": "Crescita Maggiore", "valore": best_growth[0], "dettaglio": f"+{best_growth[1]:.0f}% vs mese prec. • €{best_growth[2]:,.0f}", "colore": "cyan"})

    # 3. Top client this month
    clienti_mese_pipeline = [
        {"$match": {"data": {"$gte": current_month_start}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}, **excl_prod}},
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
        {"$match": {"cliente_nome": {"$nin": EXCLUDED_CLIENTS}, **excl_prod}},
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

    # 6. Best margin — costo reale FIFO delle vendite del mese
    margine_pipeline = [
        {"$match": {"data": {"$gte": current_month_start}, "costo_fifo": {"$gt": 0}, **excl_prod}},
        {"$group": {"_id": "$prodotto_nome", "fatturato": {"$sum": {"$abs": "$totale"}},
                    "quantita": {"$sum": {"$abs": "$quantita"}}, "costo": {"$sum": "$costo_fifo"}}}
    ]
    margini_agg = await db.vendite.aggregate(margine_pipeline).to_list(20000)
    best_margin = None
    for m in margini_agg:
        nome = m['_id']
        if not nome or nome in esclusi_set:
            continue
        fatt, qty, costo = m['fatturato'], m['quantita'], m['costo']
        if costo <= 0 or qty <= 0 or fatt <= 100:
            continue
        pv = fatt / qty
        pa = costo / qty
        margine_pct = (fatt - costo) / costo * 100
        if margine_pct <= 0 or margine_pct > 300:
            continue
        score = margine_pct * min(fatt, 1000)
        if not best_margin or score > best_margin[5]:
            best_margin = (nome, margine_pct, pv, pa, fatt, score)
    if best_margin:
        insights.append({"tipo": "best_margin", "icona": "\U0001F4B0", "titolo": "Margine Migliore", "valore": best_margin[0][:20] + ('...' if len(best_margin[0]) > 20 else ''), "dettaglio": f"+{best_margin[1]:.0f}% (€{best_margin[2]:.2f} vs €{best_margin[3]:.2f})", "colore": "emerald"})

    # 7. Fastest selling product (30 days)
    velocity_pipeline = [
        {"$match": {"data": {"$gte": last_30_days}, **excl_prod}},
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
        {"$match": {"data": {"$gte": current_month_start}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}, **excl_prod}},
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
    from routes.esclusioni import get_prodotti_esclusi
    prod_esclusi = await get_prodotti_esclusi()
    excl_prod = {"prodotto_nome": {"$nin": prod_esclusi}} if prod_esclusi else {}

    # Compute date_start based on periodo for fatturato/ordini
    if periodo == "30gg":
        date_start = (ref - timedelta(days=30)).strftime("%Y-%m-%d")
    elif periodo == "90gg":
        date_start = (ref - timedelta(days=90)).strftime("%Y-%m-%d")
    elif periodo == "mese_prec":
        date_start = prev_start
        date_end = prev_end
    else:
        date_start = month_start
    
    # For mese_prec, we need to filter by date range
    if periodo == "mese_prec":
        date_filter = {"$gte": date_start, "$lte": date_end}
    else:
        date_filter = {"$gte": date_start}
    
    periodo_labels = {"mese": "Mese corrente", "30gg": "Ultimi 30 giorni", "90gg": "Ultimi 90 giorni", "mese_prec": "Mese precedente"}

    if card_type == "fatturato":
        daily_pipeline = [
            {"$match": {"data": date_filter, "cliente_nome": {"$nin": EXCLUDED}, **excl_prod}},
            {"$group": {"_id": "$data", "totale": {"$sum": {"$abs": "$totale"}}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        daily = await db.vendite.aggregate(daily_pipeline).to_list(90)
        top_prod_pipeline = [
            {"$match": {"data": date_filter, **excl_prod}},
            {"$group": {"_id": "$prodotto_nome", "totale": {"$sum": {"$abs": "$totale"}}}},
            {"$sort": {"totale": -1}}, {"$limit": 5}
        ]
        top_prod = await db.vendite.aggregate(top_prod_pipeline).to_list(5)
        week_pipeline = [
            {"$match": {"data": date_filter, **excl_prod}},
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
        scontrino_pipeline = [
            {"$match": {"data": date_filter, "cliente_nome": {"$nin": EXCLUDED}, **excl_prod}},
            {"$group": {"_id": {"cliente": "$cliente_nome", "data": "$data"}, "totale_visita": {"$sum": {"$abs": "$totale"}}}},
            {"$group": {"_id": None, "media": {"$avg": "$totale_visita"}, "num_visite": {"$sum": 1}, "totale": {"$sum": "$totale_visita"}}}
        ]
        scontrino_res = await db.vendite.aggregate(scontrino_pipeline).to_list(1)
        avg_order = scontrino_res[0]["media"] if scontrino_res else 0
        num_visite = scontrino_res[0]["num_visite"] if scontrino_res else 0
        daily_pipeline = [
            {"$match": {"data": date_filter, "cliente_nome": {"$nin": EXCLUDED}, **excl_prod}},
            {"$group": {"_id": {"data": "$data", "cliente": "$cliente_nome"}, "totale_visita": {"$sum": {"$abs": "$totale"}}}},
            {"$group": {"_id": "$_id.data", "visite": {"$sum": 1}, "totale": {"$sum": "$totale_visita"}}},
            {"$sort": {"_id": 1}}
        ]
        daily = await db.vendite.aggregate(daily_pipeline).to_list(90)
        req_pipeline = [
            {"$match": {"data": date_filter, **excl_prod}},
            {"$group": {"_id": "$prodotto_nome", "richieste": {"$sum": 1}, "quantita": {"$sum": {"$abs": "$quantita"}}}},
            {"$sort": {"richieste": -1}}, {"$limit": 5}
        ]
        top_req = await db.vendite.aggregate(req_pipeline).to_list(5)
        # Daily average orders across active days in the period
        giorni_attivi = len(daily)
        media_ordini_giornaliera = round(num_visite / giorni_attivi, 1) if giorni_attivi > 0 else 0
        return {
            "tipo": "ordini",
            "periodo_label": periodo_labels.get(periodo, periodo),
            "giornaliero": [{"data": d["_id"], "ordini": d["visite"], "totale": round(d["totale"], 2)} for d in daily],
            "scontrino_medio": round(avg_order, 2),
            "num_visite_totali": num_visite,
            "media_ordini_giornaliera": media_ordini_giornaliera,
            "giorni_attivi": giorni_attivi,
            "top_prodotti_richieste": [{"nome": p["_id"], "richieste": p["richieste"], "quantita": round(p["quantita"], 1)} for p in top_req]
        }

    elif card_type == "clienti":
        # Determine date filter based on periodo
        if periodo == "30gg":
            cli_date_start = (ref - timedelta(days=30)).strftime("%Y-%m-%d")
            cli_date_filter = {"$gte": cli_date_start}
        elif periodo == "90gg":
            cli_date_start = (ref - timedelta(days=90)).strftime("%Y-%m-%d")
            cli_date_filter = {"$gte": cli_date_start}
        elif periodo == "mese_prec":
            cli_date_filter = {"$gte": prev_start, "$lte": prev_end}
            cli_date_start = prev_start
        else:  # "mese" default
            cli_date_start = month_start
            cli_date_filter = {"$gte": cli_date_start}

        cli_periodo_labels = {"mese": "Mese corrente", "mese_prec": "Mese precedente", "30gg": "Ultimi 30 giorni", "90gg": "Ultimi 90 giorni"}

        # Top clients
        top_pipeline = [
            {"$match": {"data": cli_date_filter, "cliente_nome": {"$nin": EXCLUDED}, **excl_prod}},
            {"$group": {"_id": "$cliente_nome", "totale": {"$sum": {"$abs": "$totale"}}, "ordini": {"$sum": 1}}},
            {"$sort": {"totale": -1}}, {"$limit": 5}
        ]
        top_cli = await db.vendite.aggregate(top_pipeline).to_list(5)
        # New clients (first purchase in period)
        new_pipeline = [
            {"$match": {"cliente_nome": {"$nin": EXCLUDED}, **excl_prod}},
            {"$group": {"_id": "$cliente_nome", "prima_vendita": {"$min": "$data"}, "totale_periodo": {"$sum": {"$cond": [{"$and": [{"$gte": ["$data", cli_date_start]}, {"$lte": ["$data", prev_end if periodo == "mese_prec" else ref.strftime("%Y-%m-%d")]}]}, {"$abs": "$totale"}, 0]}}}},
            {"$match": {"prima_vendita": cli_date_filter}},
            {"$sort": {"totale_periodo": -1}}, {"$limit": 5}
        ]
        new_cli = await db.vendite.aggregate(new_pipeline).to_list(5)
        # Clienti in crescita: confronto spesa periodo corrente vs periodo precedente equivalente
        from datetime import datetime as _dt
        def _d(days):
            return (ref - timedelta(days=days)).strftime("%Y-%m-%d")
        if periodo == "30gg":
            cur_lo, cur_hi = _d(30), ref.strftime("%Y-%m-%d")
            prev_lo, prev_hi = _d(60), _d(30)
        elif periodo == "90gg":
            cur_lo, cur_hi = _d(90), ref.strftime("%Y-%m-%d")
            prev_lo, prev_hi = _d(180), _d(90)
        elif periodo == "mese_prec":
            cur_lo, cur_hi = prev_start, prev_end
            pp_end = (prev_m.replace(day=1) - timedelta(days=1))
            prev_lo, prev_hi = pp_end.replace(day=1).strftime("%Y-%m-%d"), pp_end.strftime("%Y-%m-%d")
        else:  # mese corrente
            cur_lo, cur_hi = month_start, ref.strftime("%Y-%m-%d")
            prev_lo, prev_hi = prev_start, prev_end

        async def _spesa_map(lo, hi):
            pipe = [
                {"$match": {"data": {"$gte": lo, "$lte": hi}, "cliente_nome": {"$nin": EXCLUDED}, **excl_prod}},
                {"$group": {"_id": "$cliente_nome", "totale": {"$sum": {"$abs": "$totale"}}}}
            ]
            res = await db.vendite.aggregate(pipe).to_list(100000)
            return {r["_id"]: r["totale"] for r in res if r["_id"]}

        cur_map = await _spesa_map(cur_lo, cur_hi)
        prev_map = await _spesa_map(prev_lo, prev_hi)
        crescita = []
        calo = []
        tutti_clienti = set(cur_map.keys()) | set(prev_map.keys())
        for nome_c in tutti_clienti:
            spesa_cur = cur_map.get(nome_c, 0)
            spesa_prev = prev_map.get(nome_c, 0)
            delta = spesa_cur - spesa_prev
            var_pct = ((delta / spesa_prev) * 100) if spesa_prev > 0 else None
            row = {
                "nome": nome_c,
                "spesa_corrente": round(spesa_cur, 2),
                "spesa_precedente": round(spesa_prev, 2),
                "crescita_eur": round(delta, 2),
                "crescita_pct": round(var_pct, 1) if var_pct is not None else None
            }
            if delta > 0:
                crescita.append(row)
            elif delta < 0:
                calo.append(row)
        crescita.sort(key=lambda x: x["crescita_eur"], reverse=True)
        calo.sort(key=lambda x: x["crescita_eur"])
        clienti_in_crescita = crescita[:5]
        clienti_in_calo = calo[:5]
        return {
            "tipo": "clienti",
            "periodo_label": cli_periodo_labels.get(periodo, periodo),
            "top_clienti": [{"nome": c["_id"], "totale": round(c["totale"], 2), "ordini": c["ordini"]} for c in top_cli],
            "nuovi_clienti": [{"nome": c["_id"], "totale": round(c["totale_periodo"], 2), "dal": c["prima_vendita"]} for c in new_cli],
            "clienti_in_crescita": clienti_in_crescita,
            "clienti_in_calo": clienti_in_calo
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


@router.get("/top-clienti-prodotti-calo")
async def get_top_clienti_prodotti_calo():
    """
    Get products that are declining in quantity across ALL sales.
    Compares current month with previous month.
    """
    EXCLUDED = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    from routes.esclusioni import get_prodotti_esclusi_set
    esclusi_set = await get_prodotti_esclusi_set()
    
    now = datetime.now()
    current_month_start = now.replace(day=1).strftime("%Y-%m-%d")
    prev_month = now.replace(day=1) - timedelta(days=1)
    prev_month_start = prev_month.replace(day=1).strftime("%Y-%m-%d")
    prev_month_end = prev_month.strftime("%Y-%m-%d")
    current_end = now.strftime("%Y-%m-%d")
    
    # Get current month sales (ALL customers)
    current_sales = await db.vendite.find({
        "data": {"$gte": current_month_start, "$lte": current_end},
        "cliente_nome": {"$nin": EXCLUDED}
    }, {"_id": 0, "prodotto_nome": 1, "quantita": 1}).to_list(100000)
    
    # Get previous month sales (ALL customers)
    prev_sales = await db.vendite.find({
        "data": {"$gte": prev_month_start, "$lte": prev_month_end},
        "cliente_nome": {"$nin": EXCLUDED}
    }, {"_id": 0, "prodotto_nome": 1, "quantita": 1}).to_list(100000)
    
    # Aggregate by product
    current_by_prod = {}
    for s in current_sales:
        prod = s.get("prodotto_nome", "")
        if prod and prod not in esclusi_set:
            current_by_prod[prod] = current_by_prod.get(prod, 0) + abs(s.get("quantita", 0))
    
    prev_by_prod = {}
    for s in prev_sales:
        prod = s.get("prodotto_nome", "")
        if prod and prod not in esclusi_set:
            prev_by_prod[prod] = prev_by_prod.get(prod, 0) + abs(s.get("quantita", 0))
    
    # Find products with decline
    prodotti_calo = []
    for prod, prev_qty in prev_by_prod.items():
        curr_qty = current_by_prod.get(prod, 0)
        if prev_qty > 0:
            variazione = ((curr_qty - prev_qty) / prev_qty) * 100
            # Only include significant declines (> 20% drop and at least 10 units less)
            if variazione < -20 and (prev_qty - curr_qty) >= 10:
                prodotti_calo.append({
                    "prodotto": prod,
                    "qty_mese_prec": round(prev_qty, 1),
                    "qty_mese_curr": round(curr_qty, 1),
                    "variazione_pct": round(variazione, 1),
                    "diff_assoluta": round(prev_qty - curr_qty, 1)
                })
    
    # Sort by absolute difference (biggest drops first)
    prodotti_calo.sort(key=lambda x: x["diff_assoluta"], reverse=True)
    
    return {
        "prodotti_calo": prodotti_calo[:10],
        "totale_prodotti_calo": len(prodotti_calo),
        "mese_corrente": current_month_start[:7],
        "mese_precedente": prev_month_start[:7]
    }


@router.get("/confronta-periodi")
async def confronta_periodi(
    start1: str = Query(..., description="Start date periodo 1 (YYYY-MM-DD)"),
    end1: str = Query(..., description="End date periodo 1 (YYYY-MM-DD)"),
    start2: str = Query(..., description="Start date periodo 2 (YYYY-MM-DD)"),
    end2: str = Query(..., description="End date periodo 2 (YYYY-MM-DD)")
):
    """
    Compare two periods and return detailed product-level differences.
    Diff is calculated as: periodo1 - periodo2 (positive means periodo1 has more)
    """
    # Determine which period is more recent for proper labeling
    is_period1_newer = start1 > start2
    
    # Get sales for period 1
    vendite1 = await db.vendite.find(
        {"data": {"$gte": start1, "$lte": end1}},
        {"_id": 0, "prodotto_nome": 1, "quantita": 1, "totale": 1}
    ).to_list(100000)
    
    # Get sales for period 2
    vendite2 = await db.vendite.find(
        {"data": {"$gte": start2, "$lte": end2}},
        {"_id": 0, "prodotto_nome": 1, "quantita": 1, "totale": 1}
    ).to_list(100000)
    
    # Aggregate by product for period 1
    prod1 = {}
    for v in vendite1:
        nome = v.get('prodotto_nome', '')
        if nome:
            if nome not in prod1:
                prod1[nome] = {'qty': 0, 'totale': 0}
            prod1[nome]['qty'] += abs(v.get('quantita', 0))
            prod1[nome]['totale'] += abs(v.get('totale', 0))
    
    # Aggregate by product for period 2
    prod2 = {}
    for v in vendite2:
        nome = v.get('prodotto_nome', '')
        if nome:
            if nome not in prod2:
                prod2[nome] = {'qty': 0, 'totale': 0}
            prod2[nome]['qty'] += abs(v.get('quantita', 0))
            prod2[nome]['totale'] += abs(v.get('totale', 0))
    
    # Combine all products
    all_products = set(prod1.keys()) | set(prod2.keys())
    
    # Determine which period is more recent (for correct diff calculation)
    # diff should show: periodo1 compared to periodo2 (periodo1 - periodo2)
    # If user selected periodo1=Feb2026, periodo2=Jan2026 -> diff shows how Feb changed vs Jan
    # Positive diff means periodo1 has MORE than periodo2
    
    confronto = []
    for nome in all_products:
        p1 = prod1.get(nome, {'qty': 0, 'totale': 0})
        p2 = prod2.get(nome, {'qty': 0, 'totale': 0})
        
        qty1 = p1['qty']
        qty2 = p2['qty']
        tot1 = p1['totale']
        tot2 = p2['totale']
        
        # Calculate prices (totale / qty)
        prezzo1 = tot1 / qty1 if qty1 > 0 else 0
        prezzo2 = tot2 / qty2 if qty2 > 0 else 0
        
        # Diff: periodo1 - periodo2 (how much more/less in periodo1 vs periodo2)
        diff_qty = qty1 - qty2
        diff_prezzo = prezzo1 - prezzo2
        diff_totale = tot1 - tot2
        
        # Calculate percentage changes (base is periodo2)
        pct_qty = ((qty1 - qty2) / qty2 * 100) if qty2 > 0 else (100 if qty1 > 0 else 0)
        pct_prezzo = ((prezzo1 - prezzo2) / prezzo2 * 100) if prezzo2 > 0 else (100 if prezzo1 > 0 else 0)
        
        confronto.append({
            "prodotto": nome,
            "qty1": round(qty1, 1),
            "qty2": round(qty2, 1),
            "diff_qty": round(diff_qty, 1),
            "pct_qty": round(pct_qty, 1),
            "prezzo1": round(prezzo1, 2),
            "prezzo2": round(prezzo2, 2),
            "diff_prezzo": round(diff_prezzo, 2),
            "pct_prezzo": round(pct_prezzo, 1),
            "totale1": round(tot1, 2),
            "totale2": round(tot2, 2),
            "diff_totale": round(diff_totale, 2)
        })
    
    # Sort by absolute total difference (biggest changes first)
    confronto.sort(key=lambda x: abs(x["diff_totale"]), reverse=True)
    
    return {
        "confronto": confronto,
        "totale_prodotti": len(confronto),
        "periodo1": f"{start1} - {end1}",
        "periodo2": f"{start2} - {end2}"
    }


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
async def generate_ai_report(report_type: str = Query("settimanale", enum=["settimanale", "mensile", "dashboard"])):
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    now = datetime.now()

    if report_type == "settimanale":
        start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        period_name = "Settimana"
    elif report_type == "dashboard":
        # Dashboard report: analisi mese corrente con confronto mese precedente
        month_start = now.replace(day=1).strftime("%Y-%m-%d")
        prev_month = (now.replace(day=1) - timedelta(days=1))
        prev_month_start = prev_month.replace(day=1).strftime("%Y-%m-%d")
        prev_month_end = prev_month.strftime("%Y-%m-%d")
        start_date = month_start
        period_name = "Dashboard"
    else:
        start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        period_name = "Mese"
    end_date = now.strftime("%Y-%m-%d")

    vendite = await db.vendite.find({"data": {"$gte": start_date}}, {"_id": 0}).to_list(10000)
    vendite = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    ordini = await db.ordini.find({"data": {"$gte": start_date}}, {"_id": 0}).to_list(5000)
    clienti = await db.clienti.find({}, {"_id": 0}).to_list(1000)

    fatturato_totale = sum(abs(v.get('totale', 0)) for v in vendite)
    num_vendite = len(vendite)
    
    # Calculate unique orders (same client + same date = 1 order)
    ordini_unici = set()
    for v in vendite:
        cliente = v.get('cliente_nome', '')
        data = v.get('data', '')
        if cliente and data:
            ordini_unici.add((cliente, data))
    num_ordini = len(ordini_unici) if ordini_unici else 1
    media_per_ordine = fatturato_totale / num_ordini if num_ordini > 0 else 0
    
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

    recent_clients = set(v.get('cliente_nome', '') for v in vendite)
    all_historical_clients = set(c.get('nome', '') for c in clienti)
    inactive_clients = list(all_historical_clients - recent_clients)[:10]
    acquisti_totale = sum(abs(o.get('totale', 0)) for o in ordini)

    # For dashboard report, add comparison with previous month
    prev_month_data = ""
    if report_type == "dashboard":
        prev_vendite = await db.vendite.find({"data": {"$gte": prev_month_start, "$lte": prev_month_end}}, {"_id": 0}).to_list(10000)
        prev_vendite = [v for v in prev_vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
        prev_fatturato = sum(abs(v.get('totale', 0)) for v in prev_vendite)
        prev_num_vendite = len(prev_vendite)
        variazione_fatt = ((fatturato_totale - prev_fatturato) / prev_fatturato * 100) if prev_fatturato > 0 else 0
        
        # Get alerts data
        sotto_scorta = await db.prodotti.count_documents({"quantita_minima": {"$gt": 0}, "$expr": {"$lte": ["$quantita", "$quantita_minima"]}})
        
        prev_month_data = f"""
CONFRONTO MESE PRECEDENTE:
- Fatturato mese precedente: €{prev_fatturato:,.2f}
- Variazione: {variazione_fatt:+.1f}%
- Transazioni mese precedente: {prev_num_vendite}

ALERT ATTIVI:
- Prodotti sotto scorta: {sotto_scorta}
- Clienti inattivi: {len(inactive_clients)}
"""

    data_summary = f"""
DATI AZIENDALI - {period_name} dal {start_date} al {end_date}

FATTURATO E VENDITE:
- Fatturato totale: €{fatturato_totale:,.2f}
- Numero ordini (giorni cliente unici): {num_ordini}
- Numero righe vendita: {num_vendite}
- Media per ordine: €{media_per_ordine:,.2f}
{prev_month_data}
TOP 5 PRODOTTI (per fatturato):
{chr(10).join([f"- {p[0]}: €{p[1]:,.2f}" for p in top_products]) if top_products else "- Nessun dato"}

TOP 5 CLIENTI (per spesa):
{chr(10).join([f"- {c[0]}: €{c[1]:,.2f}" for c in top_clients]) if top_clients else "- Nessun dato"}

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

        if report_type == "dashboard":
            prompt_tipo = "DASHBOARD (analisi completa della situazione attuale con confronto mese precedente)"
            sezioni = """Il report deve includere:
1. **Situazione Attuale** - stato dell'attività con confronto mese precedente
2. **Performance** - analisi fatturato, trend, variazioni percentuali
3. **Alert e Criticità** - prodotti sotto scorta, clienti da riattivare
4. **Top Performers** - migliori prodotti e clienti del periodo
5. **Azioni Immediate** - 3-5 azioni prioritarie da eseguire subito"""
        else:
            prompt_tipo = f"{report_type}"
            sezioni = """Il report deve includere:
1. **Sommario Esecutivo** - panoramica rapida dei risultati chiave
2. **Performance Vendite** - analisi del fatturato e trend
3. **Prodotti** - analisi dei best seller e suggerimenti
4. **Clienti** - analisi dei top clienti e strategia per clienti inattivi
5. **Raccomandazioni** - 3-5 azioni concrete"""

        prompt = f"""Genera un report {prompt_tipo} professionale basato sui seguenti dati aziendali.

{data_summary}

{sezioni}

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
                "clienti_inattivi": len(inactive_clients)
            },
            "created_at": now.isoformat()
        }
        await db.ai_reports.insert_one(report)
        report.pop('_id', None)
        return report
    except Exception as e:
        logger.error(f"Error generating AI report: {e}")
        raise HTTPException(status_code=500, detail=f"Errore generazione report: {str(e)}")


@router.post("/ai-reports/export-pdf")
async def export_report_pdf(data: dict):
    from fastapi.responses import Response
    from routes.pdf_helper import FlowPDF, eur, FONT, C_BLUE, C_EMERALD, C_VIOLET, C_AMBER, C_RED, C_SLATE
    try:
        tipo       = str(data.get('tipo','Report')).upper()
        p_inizio   = str(data.get('periodo_inizio',''))
        p_fine     = str(data.get('periodo_fine',''))
        metriche   = data.get('metriche', {})
        created_at = str(data.get('created_at',''))[:10]
        contenuto  = str(data.get('contenuto',''))

        fatturato   = metriche.get('fatturato', 0)
        num_vendite = metriche.get('num_vendite', 0)
        c_inattivi  = metriche.get('clienti_inattivi', 0)
        variazione  = float(metriche.get('variazione_percentuale', 0) or 0)

        pdf = FlowPDF(f"REPORT AI — {tipo}", f"Periodo: {p_inizio}  —  {p_fine}")
        pdf.add_page()

        kpis = [
            ("FATTURATO PERIODO",  eur(fatturato), C_BLUE,   f"{p_inizio} / {p_fine}"),
            ("TRANSAZIONI",        f"{num_vendite:,}",       C_EMERALD, None),
            ("CLIENTI INATTIVI",   f"{c_inattivi}",
             C_AMBER if c_inattivi > 0 else C_EMERALD, "da ricontattare"),
        ]
        if variazione:
            kpis.append(("VARIAZIONE", f"{variazione:+.1f}%",
                          C_EMERALD if variazione >= 0 else C_RED, "vs periodo prec."))
        pdf.kpi_row(kpis)

        pdf.section_title("Considerazioni", C_VIOLET, top_gap=3)
        pdf.ai_text_block(contenuto)

        pdf.ln(6)
        pdf.set_font(FONT,'I',7.5); pdf.set_text_color(*C_SLATE)
        pdf.cell(0,5,f"Report generato il {created_at}  |  Flow Business Analytics  |  Confidenziale",align='C')

        pdf_bytes = pdf.output()
        return Response(bytes(pdf_bytes), media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename=report_{tipo.lower()}.pdf"})
    except Exception as e:
        logger.error(f"Error exporting report PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Errore export PDF: {str(e)}")



@router.post("/ai-chat")
async def ai_chat(data: dict):
    """
    AI Chat with full access to all platform data.
    Can answer questions about products, customers, suppliers, orders, stock, etc.
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    from pydantic import BaseModel
    
    message = data.get('message', '')
    if not message:
        raise HTTPException(status_code=400, detail="Messaggio richiesto")
    
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    now = datetime.now()
    
    # Gather comprehensive data for AI context
    try:
        # Get reference date from latest sale
        latest_sale = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", -1)])
        if latest_sale and latest_sale.get('data'):
            try:
                reference_date = datetime.strptime(latest_sale['data'], "%Y-%m-%d")
            except Exception:
                reference_date = now
        else:
            reference_date = now
        
        ninety_days_ago = (reference_date - timedelta(days=90)).strftime("%Y-%m-%d")
        
        # 1. Products - with stock levels and prices
        prodotti = await db.prodotti.find({}, {"_id": 0}).to_list(5000)
        prodotti_list = []
        low_stock_products = []
        for p in prodotti:
            qty = p.get('quantita', 0)
            min_qty = p.get('quantita_minima', 0)
            prezzo = p.get('prezzo_medio', 0)
            prodotti_list.append({
                'nome': p.get('nome', ''),
                'quantita': qty,
                'quantita_minima': min_qty,
                'prezzo_medio': prezzo,
                'valore_scorte': qty * prezzo if prezzo > 0 else 0
            })
            if min_qty > 0 and qty <= min_qty:
                low_stock_products.append(p.get('nome', ''))
        
        # 2. Top selling products (last 90 days)
        vendite_pipeline = [
            {"$match": {"data": {"$gte": ninety_days_ago}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
            {"$group": {
                "_id": "$prodotto_nome",
                "fatturato": {"$sum": {"$abs": "$totale"}},
                "quantita": {"$sum": {"$abs": "$quantita"}},
                "ordini": {"$sum": 1}
            }},
            {"$sort": {"fatturato": -1}},
            {"$limit": 30}
        ]
        top_vendite = await db.vendite.aggregate(vendite_pipeline).to_list(30)
        
        # 3. Top customers
        clienti_pipeline = [
            {"$match": {"data": {"$gte": ninety_days_ago}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
            {"$group": {
                "_id": "$cliente_nome",
                "fatturato": {"$sum": {"$abs": "$totale"}},
                "ordini": {"$sum": 1}
            }},
            {"$sort": {"fatturato": -1}},
            {"$limit": 20}
        ]
        top_clienti = await db.vendite.aggregate(clienti_pipeline).to_list(20)
        
        # 4. Suppliers with their top products AND recent orders
        fornitori = await db.fornitori.find({}, {"_id": 0, "id": 1, "nome": 1}).to_list(500)
        fornitori_ordini = []
        
        # Get recent orders from suppliers (last 30 days)
        thirty_days_ago = (reference_date - timedelta(days=30)).strftime("%Y-%m-%d")
        recent_ordini = await db.ordini.find(
            {"data": {"$gte": thirty_days_ago}},
            {"_id": 0, "data": 1, "fornitore_nome": 1, "prodotto_nome": 1, "quantita": 1, "totale": 1}
        ).sort("data", -1).to_list(1000)
        
        # Group orders by supplier
        ordini_per_fornitore = {}
        for o in recent_ordini:
            fornitore = o.get('fornitore_nome', '')
            if fornitore:
                if fornitore not in ordini_per_fornitore:
                    ordini_per_fornitore[fornitore] = []
                ordini_per_fornitore[fornitore].append({
                    'data': o.get('data', ''),
                    'prodotto': o.get('prodotto_nome', ''),
                    'qty': abs(o.get('quantita', 0)),
                    'totale': abs(o.get('totale', 0))
                })
        
        # Build detailed supplier orders context
        fornitori_dettaglio = []
        for fornitore, ordini in sorted(ordini_per_fornitore.items(), key=lambda x: sum(o['totale'] for o in x[1]), reverse=True)[:25]:
            prodotti_fornitore = {}
            for o in ordini:
                prod = o['prodotto']
                if prod not in prodotti_fornitore:
                    prodotti_fornitore[prod] = {'qty': 0, 'totale': 0}
                prodotti_fornitore[prod]['qty'] += o['qty']
                prodotti_fornitore[prod]['totale'] += o['totale']
            
            top_prods = sorted(prodotti_fornitore.items(), key=lambda x: x[1]['totale'], reverse=True)[:5]
            prods_str = ', '.join([f"{p[0]} ({p[1]['qty']:.0f}u €{p[1]['totale']:.0f})" for p in top_prods])
            totale_fornitore = sum(p[1]['totale'] for p in top_prods)
            fornitori_dettaglio.append(f"- {fornitore} (€{it_num(totale_fornitore, 0)}): {prods_str}")
            
            # Also add to fornitori_ordini for backward compatibility
            fornitori_ordini.append({
                'fornitore': fornitore,
                'top_prodotti': [{'nome': p[0], 'totale': p[1]['totale'], 'qty': p[1]['qty']} for p in top_prods]
            })
        
        # 5. RECENT SALES - Last 14 days with full details (for specific queries)
        fourteen_days_ago = (reference_date - timedelta(days=14)).strftime("%Y-%m-%d")
        recent_sales = await db.vendite.find(
            {"data": {"$gte": fourteen_days_ago}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}},
            {"_id": 0, "data": 1, "cliente_nome": 1, "prodotto_nome": 1, "quantita": 1, "totale": 1}
        ).sort("data", -1).to_list(500)
        
        # Group recent sales by client
        vendite_per_cliente = {}
        for v in recent_sales:
            cliente = v.get('cliente_nome', '')
            if cliente:
                if cliente not in vendite_per_cliente:
                    vendite_per_cliente[cliente] = []
                vendite_per_cliente[cliente].append({
                    'data': v.get('data', ''),
                    'prodotto': v.get('prodotto_nome', ''),
                    'qty': abs(v.get('quantita', 0)),
                    'totale': abs(v.get('totale', 0))
                })
        
        # Build detailed recent sales context
        recent_sales_context = []
        for cliente, vendite in sorted(vendite_per_cliente.items(), key=lambda x: sum(v['totale'] for v in x[1]), reverse=True)[:25]:
            prodotti_cliente = {}
            for v in vendite:
                prod = v['prodotto']
                if prod not in prodotti_cliente:
                    prodotti_cliente[prod] = {'qty': 0, 'totale': 0}
                prodotti_cliente[prod]['qty'] += v['qty']
                prodotti_cliente[prod]['totale'] += v['totale']
            
            top_prods = sorted(prodotti_cliente.items(), key=lambda x: x[1]['totale'], reverse=True)[:5]
            prods_str = ', '.join([f"{p[0]} ({p[1]['qty']:.0f}u €{p[1]['totale']:.0f})" for p in top_prods])
            totale_cliente = sum(p[1]['totale'] for p in top_prods)
            recent_sales_context.append(f"- {cliente} (€{it_num(totale_cliente, 0)}): {prods_str}")
        
        # 6. Get ALL clients for fuzzy matching
        all_clienti_db = await db.clienti.find({}, {"_id": 0, "nome": 1}).to_list(1000)
        all_clienti_nomi = [c.get('nome', '') for c in all_clienti_db if c.get('nome')]
        
        # 7. Monthly revenue summary
        fatturato_mese = sum(t['fatturato'] for t in top_vendite)
        
        # 8. Current stock value
        valore_totale_magazzino = sum(p['valore_scorte'] for p in prodotti_list)
        
        # Helper function for building fornitore line
        def build_fornitore_line(fo):
            prods = ', '.join([p['nome'] + ' (€' + str(int(p['totale'])) + ')' for p in fo['top_prodotti'][:3]])
            return f"- {fo['fornitore']}: {prods}"
        
        # Build comprehensive context
        context = f"""
DATI AZIENDA ORTOFRUTTICOLA - Aggiornati al {reference_date.strftime("%Y-%m-%d")}

=== RIEPILOGO GENERALE ===
- Fatturato ultimi 90 giorni: €{it_num(fatturato_mese, 2)}
- Valore totale magazzino: €{it_num(valore_totale_magazzino, 2)}
- Prodotti a catalogo: {len(prodotti_list)}
- Prodotti sotto scorta: {len(low_stock_products)}
- Fornitori attivi: {len(fornitori)}
- Clienti attivi (90gg): {len(top_clienti)}

=== TOP 15 PRODOTTI PIU' VENDUTI (90gg) ===
{chr(10).join([f"- {p['_id']}: €{it_num(p['fatturato'], 2)} | {p['quantita']:.0f} unità | {p['ordini']} ordini" for p in top_vendite[:15]])}

=== TOP 10 CLIENTI (90gg) ===
{chr(10).join([f"- {c['_id']}: €{it_num(c['fatturato'], 2)} | {c['ordini']} ordini" for c in top_clienti[:10]])}

=== VENDITE ULTIME 2 SETTIMANE PER CLIENTE (dettaglio prodotti) ===
{chr(10).join(recent_sales_context) if recent_sales_context else "Nessuna vendita nelle ultime 2 settimane"}

=== ACQUISTI DA FORNITORI (ultimo mese - dettaglio prodotti) ===
{chr(10).join(fornitori_dettaglio) if fornitori_dettaglio else "Nessun ordine nell'ultimo mese"}

=== PRODOTTI SOTTO SCORTA (da riordinare) ===
{chr(10).join([f"- {nome}" for nome in low_stock_products[:15]]) if low_stock_products else "Nessun prodotto sotto scorta"}

=== GIACENZA MAGAZZINO (primi 30 per valore) ===
{chr(10).join([f"- {p['nome']}: {p['quantita']:.0f} unità | €{p['prezzo_medio']:.2f}/u | Valore: €{p['valore_scorte']:.2f}" for p in sorted(prodotti_list, key=lambda x: -x['valore_scorte'])[:30] if p['quantita'] > 0])}

=== FORNITORI E LORO PRODOTTI PRINCIPALI ===
{chr(10).join([build_fornitore_line(fo) for fo in fornitori_ordini[:15]])}
"""

        # Add list of all entity names for fuzzy matching
        all_prodotti_names = [p['nome'] for p in prodotti_list]
        all_clienti_names = list(set(all_clienti_nomi + [c['_id'] for c in top_clienti] + list(vendite_per_cliente.keys())))
        # Include ALL suppliers from DB, not just those with recent orders
        all_fornitori_names = list(set([f.get('nome', '') for f in fornitori if f.get('nome')] + list(ordini_per_fornitore.keys())))
        
        entity_lists = f"""
=== LISTA COMPLETA NOMI (per ricerca) ===
PRODOTTI (primi 60): {', '.join(all_prodotti_names[:60])}
TUTTI I CLIENTI (primi 50): {', '.join(sorted(all_clienti_names)[:50])}
TUTTI I FORNITORI: {', '.join(sorted(all_fornitori_names))}
"""

        # Call AI
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="API key LLM non configurata")
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"chat-{uuid.uuid4()}",
            system_message="""Sei un assistente business AI esperto nel settore ortofrutticolo italiano.
Hai accesso completo a tutti i dati dell'azienda: vendite, clienti, fornitori, magazzino, ordini.

REGOLE FONDAMENTALI:
1. Rispondi SEMPRE in italiano
2. USA SOLO I NUMERI DAI DATI FORNITI - non inventare mai cifre
3. Se l'utente scrive un nome in modo impreciso (es. "ortofrutta" invece di "ORTOFRUTTA SRL"), cerca di trovare il match più simile nella lista entità
4. Quando formuli ordini, basa le quantità sulle vendite reali (es. se un prodotto vende 100 unità al mese, suggerisci quantità proporzionate)
5. Includi sempre i riferimenti ai dati concreti quando fai affermazioni
6. Se non trovi un fornitore/cliente/prodotto, elenca quelli disponibili più simili

COME FORMULARE ORDINI:
- Identifica il fornitore (cerca corrispondenza anche parziale del nome)
- Guarda quali prodotti quel fornitore fornisce
- Basa le quantità sulle vendite medie degli ultimi 90 giorni
- Considera la giacenza attuale

FORMATO RISPOSTE:
- Sii conciso ma completo
- Usa elenchi puntati
- Includi sempre numeri reali dai dati"""
        ).with_model("openai", "gpt-4o")
        
        prompt = f"""CONTESTO DATI AZIENDALI:
{context}

{entity_lists}

DOMANDA UTENTE:
{message}

ISTRUZIONI: Rispondi basandoti ESCLUSIVAMENTE sui dati sopra. Se l'utente cerca un nome non esatto, trova il match più vicino dalla lista entità. Se chiede ordini, usa le quantità reali di vendita per suggerire quantità sensate."""

        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return {
            "success": True,
            "response": response,
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        raise HTTPException(status_code=500, detail=f"Errore chat AI: {str(e)}")
