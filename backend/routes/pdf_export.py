from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from typing import Optional
from datetime import datetime, timedelta

from database import db, logger
from routes.pdf_helper import (
    FlowPDF, clean_text,
    C_BLUE, C_EMERALD, C_VIOLET, C_AMBER, C_RED, C_NAVY, C_SLATE, C_LIGHT, C_WHITE
)

router = APIRouter()

EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']


@router.get("/statistiche/export/pdf")
async def export_statistiche_pdf(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tipo: str = "vendite"
):
    now = datetime.now()
    if not start_date:
        start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = now.strftime("%Y-%m-%d")

    query = {"data": {"$gte": start_date, "$lte": end_date}}

    if tipo == "vendite":
        return await _export_vendite_pdf(query, start_date, end_date)
    elif tipo == "acquisti":
        return await _export_acquisti_pdf(query, start_date, end_date)
    else:
        raise HTTPException(status_code=400, detail="Tipo non valido")


async def _export_vendite_pdf(query, start_date, end_date):
    vendite = await db.vendite.find(query, {"_id": 0}).sort("data", -1).to_list(100000)
    vendite = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]

    fatturato = sum(abs(v.get('totale', 0)) for v in vendite)
    num_righe = len(vendite)
    clienti_set = set(v.get('cliente_nome', '') for v in vendite if v.get('cliente_nome'))

    # Unique transactions
    transazioni_uniche = set()
    for v in vendite:
        transazioni_uniche.add((v.get('data', ''), v.get('cliente_nome', '')))
    num_transazioni = len(transazioni_uniche)
    scontrino_medio = fatturato / num_transazioni if num_transazioni > 0 else 0

    # Products aggregation
    prod_data = {}
    for v in vendite:
        p = v.get('prodotto_nome', '')
        if not p:
            continue
        if p not in prod_data:
            prod_data[p] = {'fatturato': 0, 'qty': 0}
        prod_data[p]['fatturato'] += abs(v.get('totale', 0))
        prod_data[p]['qty'] += abs(v.get('quantita', 0))

    # Margin calculation (weighted average)
    totale_fatturato_con_margine = 0
    somma_margini_ponderati = 0
    totale_profitto = 0
    prodotti_margine_data = {}

    for nome, dati in prod_data.items():
        if dati['qty'] <= 0:
            continue
        ultimo_ordine = await db.ordini.find_one(
            {"prodotto_nome": nome, "prezzo_unitario": {"$gt": 0}},
            {"_id": 0, "prezzo_unitario": 1},
            sort=[("data", -1)]
        )
        if ultimo_ordine:
            prezzo_acquisto = ultimo_ordine.get('prezzo_unitario', 0)
            prezzo_vendita = dati['fatturato'] / dati['qty']
            if prezzo_acquisto > 0 and prezzo_acquisto < 500:
                if prezzo_vendita <= prezzo_acquisto * 5 and prezzo_vendita >= prezzo_acquisto * 0.2:
                    costo_totale = prezzo_acquisto * dati['qty']
                    profitto = dati['fatturato'] - costo_totale
                    margine = ((prezzo_vendita - prezzo_acquisto) / prezzo_acquisto) * 100
                    if -50 < margine < 200:
                        totale_fatturato_con_margine += dati['fatturato']
                        somma_margini_ponderati += margine * dati['fatturato']
                        totale_profitto += profitto
                        prodotti_margine_data[nome] = {
                            'margine': round(margine, 1),
                            'profitto': round(profitto, 2)
                        }

    margine_medio = (somma_margini_ponderati / totale_fatturato_con_margine) if totale_fatturato_con_margine > 0 else 0

    top_prod = []
    for nome, dati in sorted(prod_data.items(), key=lambda x: x[1]['fatturato'], reverse=True)[:15]:
        item = {'nome': nome, 'fatturato': dati['fatturato'], 'qty': dati['qty'], 'margine': None, 'profitto': None}
        if nome in prodotti_margine_data:
            item['margine'] = prodotti_margine_data[nome]['margine']
            item['profitto'] = prodotti_margine_data[nome]['profitto']
        top_prod.append(item)

    # Clients
    cli_rev = {}
    cli_ordini_cnt = {}
    for v in vendite:
        c = v.get('cliente_nome', '')
        if c:
            cli_rev[c] = cli_rev.get(c, 0) + abs(v.get('totale', 0))
            key = (c, v.get('data', ''))
            cli_ordini_cnt[c] = cli_ordini_cnt.get(c, 0)
    # Count unique dates per client
    cli_dates = {}
    for v in vendite:
        c = v.get('cliente_nome', '')
        d = v.get('data', '')
        if c:
            if c not in cli_dates:
                cli_dates[c] = set()
            cli_dates[c].add(d)
    top_cli = [(n, r, len(cli_dates.get(n, []))) for n, r in sorted(cli_rev.items(), key=lambda x: x[1], reverse=True)[:15]]

    # Monthly breakdown
    mensile = {}
    for v in vendite:
        m = v.get('data', '')[:7]
        if m:
            mensile[m] = mensile.get(m, 0) + abs(v.get('totale', 0))
    mensile_sorted = sorted(mensile.items())

    # ─── Build PDF ────────────────────────────────────────────────
    subtitle = f"Periodo: {start_date}  -  {end_date}"
    pdf = FlowPDF("REPORT VENDITE", subtitle)
    pdf.add_page()

    # KPI row 1
    pdf.kpi_row_4([
        ("FATTURATO TOTALE", f"EUR {fatturato:,.2f}", C_BLUE, None),
        ("TRANSAZIONI", f"{num_transazioni:,}", C_EMERALD, f"{num_righe} righe"),
        ("CLIENTI ATTIVI", f"{len(clienti_set):,}", C_VIOLET, None),
        ("SCONTRINO MEDIO", f"EUR {scontrino_medio:,.2f}", C_AMBER, None),
    ])
    # KPI row 2 (margin)
    if margine_medio > 0:
        pdf.kpi_row_4([
            ("MARGINE MEDIO", f"{margine_medio:.1f}%", C_EMERALD if margine_medio > 15 else C_AMBER, "pesato sul fatturato"),
            ("PROFITTO STIMATO", f"EUR {totale_profitto:,.2f}", C_EMERALD, None),
            ("PRODOTTI VENDUTI", f"{len(prod_data):,}", C_BLUE, None),
            ("COSTO STIMATO", f"EUR {fatturato - totale_profitto:,.2f}", C_SLATE, None),
        ])

    # Monthly trend
    if mensile_sorted:
        pdf.section_title("ANDAMENTO MENSILE", C_BLUE)
        cols = ["Mese", "Fatturato (EUR)", "% sul Totale"]
        widths = [50, 90, 50]
        pdf.table_header(cols, widths)
        for i, (m, v) in enumerate(mensile_sorted):
            pct = (v / fatturato * 100) if fatturato > 0 else 0
            pdf.table_row([m, f"{v:,.2f}", f"{pct:.1f}%"], widths, ['L', 'R', 'R'], alt=i % 2 == 1)
        pdf.ln(4)

    # Top products table
    pdf.section_title("TOP 15 PRODOTTI", C_BLUE)
    cols = ["#", "Prodotto", "Fatturato EUR", "Qty", "Margine", "Profitto EUR"]
    widths = [8, 72, 38, 22, 25, 25]
    pdf.table_header(cols, widths)
    for i, item in enumerate(top_prod):
        margine_str = f"{item['margine']:.0f}%" if item['margine'] is not None else "N/D"
        profitto_str = f"{item['profitto']:,.0f}" if item['profitto'] is not None else "N/D"
        pdf.table_row(
            [str(i+1), item['nome'][:26], f"{item['fatturato']:,.2f}", f"{item['qty']:,.0f}", margine_str, profitto_str],
            widths, ['C', 'L', 'R', 'R', 'R', 'R'], alt=i % 2 == 1
        )
    pdf.ln(4)

    # Top clients table
    pdf.section_title("TOP 15 CLIENTI", C_EMERALD)
    cols = ["#", "Cliente", "Fatturato EUR", "Visite", "% Fatturato"]
    widths = [8, 90, 45, 25, 22]
    pdf.table_header(cols, widths)
    for i, (nome, rev, visite) in enumerate(top_cli):
        pct = (rev / fatturato * 100) if fatturato > 0 else 0
        pdf.table_row(
            [str(i+1), nome[:30], f"{rev:,.2f}", str(visite), f"{pct:.1f}%"],
            widths, ['C', 'L', 'R', 'C', 'R'], alt=i % 2 == 1
        )

    pdf_bytes = pdf.output()
    filename = f"report_vendite_{start_date}_{end_date}.pdf"
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


async def _export_acquisti_pdf(query, start_date, end_date):
    ordini = await db.ordini.find(query, {"_id": 0}).sort("data", -1).to_list(100000)
    totale_speso = sum(abs(o.get('totale', 0)) for o in ordini)
    num_ordini = len(ordini)
    fornitori_set = set(o.get('fornitore_nome', '') for o in ordini if o.get('fornitore_nome'))

    # Suppliers
    forn_data = {}
    for o in ordini:
        f = o.get('fornitore_nome', '')
        if f:
            if f not in forn_data:
                forn_data[f] = {'totale': 0, 'ordini': 0}
            forn_data[f]['totale'] += abs(o.get('totale', 0))
            forn_data[f]['ordini'] += 1
    top_forn = sorted(forn_data.items(), key=lambda x: x[1]['totale'], reverse=True)[:15]

    # Products
    prod_data = {}
    for o in ordini:
        p = o.get('prodotto_nome', '')
        if p:
            if p not in prod_data:
                prod_data[p] = {'totale': 0, 'qty': 0}
            prod_data[p]['totale'] += abs(o.get('totale', 0))
            prod_data[p]['qty'] += abs(o.get('quantita', 0))
    top_prod = sorted(prod_data.items(), key=lambda x: x[1]['totale'], reverse=True)[:15]

    # Monthly
    mensile = {}
    for o in ordini:
        m = o.get('data', '')[:7]
        if m:
            mensile[m] = mensile.get(m, 0) + abs(o.get('totale', 0))
    mensile_sorted = sorted(mensile.items())

    order_medio = totale_speso / num_ordini if num_ordini > 0 else 0

    # ─── Build PDF ────────────────────────────────────────────────
    subtitle = f"Periodo: {start_date}  -  {end_date}"
    pdf = FlowPDF("REPORT ACQUISTI", subtitle)
    pdf.add_page()

    pdf.kpi_row_4([
        ("TOTALE ACQUISTATO", f"EUR {totale_speso:,.2f}", C_VIOLET, None),
        ("NUMERO ORDINI", f"{num_ordini:,}", C_BLUE, None),
        ("FORNITORI ATTIVI", f"{len(fornitori_set):,}", C_EMERALD, None),
        ("ORDINE MEDIO", f"EUR {order_medio:,.2f}", C_AMBER, None),
    ])

    # Monthly
    if mensile_sorted:
        pdf.section_title("ANDAMENTO MENSILE ACQUISTI", C_VIOLET)
        cols = ["Mese", "Spesa (EUR)", "% sul Totale"]
        widths = [50, 90, 50]
        pdf.table_header(cols, widths)
        for i, (m, v) in enumerate(mensile_sorted):
            pct = (v / totale_speso * 100) if totale_speso > 0 else 0
            pdf.table_row([m, f"{v:,.2f}", f"{pct:.1f}%"], widths, ['L', 'R', 'R'], alt=i % 2 == 1)
        pdf.ln(4)

    # Top fornitori
    pdf.section_title("TOP 15 FORNITORI", C_VIOLET)
    cols = ["#", "Fornitore", "Spesa EUR", "Ordini", "% Totale"]
    widths = [8, 90, 45, 22, 25]
    pdf.table_header(cols, widths)
    for i, (nome, dati) in enumerate(top_forn):
        pct = (dati['totale'] / totale_speso * 100) if totale_speso > 0 else 0
        pdf.table_row(
            [str(i+1), nome[:30], f"{dati['totale']:,.2f}", str(dati['ordini']), f"{pct:.1f}%"],
            widths, ['C', 'L', 'R', 'C', 'R'], alt=i % 2 == 1
        )
    pdf.ln(4)

    # Top prodotti acquistati
    pdf.section_title("TOP 15 PRODOTTI ACQUISTATI", C_BLUE)
    cols = ["#", "Prodotto", "Spesa EUR", "Qty"]
    widths = [8, 110, 45, 27]
    pdf.table_header(cols, widths)
    for i, (nome, dati) in enumerate(top_prod):
        pdf.table_row(
            [str(i+1), nome[:35], f"{dati['totale']:,.2f}", f"{dati['qty']:,.0f}"],
            widths, ['C', 'L', 'R', 'R'], alt=i % 2 == 1
        )

    pdf_bytes = pdf.output()
    filename = f"report_acquisti_{start_date}_{end_date}.pdf"
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
