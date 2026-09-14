from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from typing import Optional
from datetime import datetime, timedelta

from database import db, logger
from routes.pdf_helper import (
    FlowPDF, clean_text,
    C_BLUE, C_EMERALD, C_VIOLET, C_AMBER, C_RED, C_NAVY, C_SLATE
)

router = APIRouter()
EXCLUDED = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']


# ── Color helpers for table cells ──────────────────────────────────
def _margine_color(val):
    try:
        v = float(str(val).replace('%',''))
        if v >= 20: return C_EMERALD
        if v >= 10: return C_AMBER
        return C_RED
    except Exception:
        return C_NAVY

def _trend_color(val):
    try:
        v = float(str(val).replace('%','').replace('+',''))
        if v >= 0: return C_EMERALD
        return C_RED
    except Exception:
        return C_NAVY


# ── Routes ─────────────────────────────────────────────────────────
@router.get("/statistiche/export/pdf")
async def export_statistiche_pdf(
    start_date: Optional[str] = None,
    end_date:   Optional[str] = None,
    tipo: str = "vendite"
):
    now = datetime.now()
    if not start_date:
        start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = now.strftime("%Y-%m-%d")

    query = {"data": {"$gte": start_date, "$lte": end_date}}
    if tipo == "vendite":
        return await _vendite_pdf(query, start_date, end_date)
    elif tipo == "acquisti":
        return await _acquisti_pdf(query, start_date, end_date)
    else:
        raise HTTPException(status_code=400, detail="Tipo non valido")


# ══════════════════════════════════════════════════════════════════
#  VENDITE
# ══════════════════════════════════════════════════════════════════
async def _vendite_pdf(query, start_date, end_date):
    vendite = await db.vendite.find(query, {"_id": 0}).sort("data", 1).to_list(200000)
    vendite = [v for v in vendite
               if v.get('cliente_nome','').upper() not in [c.upper() for c in EXCLUDED]]

    fatturato    = sum(abs(v.get('totale',0)) for v in vendite)
    clienti_set  = set(v.get('cliente_nome','') for v in vendite if v.get('cliente_nome'))
    transazioni  = set()
    for v in vendite:
        transazioni.add((v.get('data',''), v.get('cliente_nome','')))
    num_tx       = len(transazioni)
    scontrino    = fatturato / num_tx if num_tx > 0 else 0

    # Products
    prod = {}
    for v in vendite:
        p = v.get('prodotto_nome','')
        if p:
            if p not in prod:
                prod[p] = {'fat': 0, 'qty': 0}
            prod[p]['fat'] += abs(v.get('totale', 0))
            prod[p]['qty'] += abs(v.get('quantita', 0))

    # Margin
    fat_con_m = 0; sum_m_w = 0; profitto_tot = 0; prod_m = {}
    for nome, d in prod.items():
        if d['qty'] <= 0: continue
        ult = await db.ordini.find_one(
            {"prodotto_nome": nome, "prezzo_unitario": {"$gt": 0}},
            {"_id":0,"prezzo_unitario":1}, sort=[("data",-1)])
        if ult:
            pa = ult.get('prezzo_unitario',0)
            pv = d['fat'] / d['qty']
            if 0 < pa < 500 and pv >= pa*0.2 and pv <= pa*5:
                m = (pv - pa) / pa * 100
                if -50 < m < 200:
                    profit = d['fat'] - pa * d['qty']
                    fat_con_m  += d['fat']
                    sum_m_w    += m * d['fat']
                    profitto_tot += profit
                    prod_m[nome] = {'m': round(m,1), 'p': round(profit,2)}

    margine_medio = sum_m_w / fat_con_m if fat_con_m > 0 else 0

    top_prod = []
    for nome, d in sorted(prod.items(), key=lambda x: x[1]['fat'], reverse=True)[:15]:
        item = [nome, d['fat'], d['qty'],
                f"{prod_m[nome]['m']:.0f}%" if nome in prod_m else 'N/D',
                f"{prod_m[nome]['p']:,.0f}"  if nome in prod_m else 'N/D']
        top_prod.append(item)

    # Clients
    cli_fat   = {}
    cli_dates = {}
    for v in vendite:
        c = v.get('cliente_nome','')
        d = v.get('data','')
        if c:
            cli_fat[c] = cli_fat.get(c,0) + abs(v.get('totale',0))
            if c not in cli_dates: cli_dates[c] = set()
            cli_dates[c].add(d)
    top_cli = [(n, r, len(cli_dates.get(n,[])))
               for n, r in sorted(cli_fat.items(), key=lambda x: x[1], reverse=True)[:15]]

    # Monthly
    mensile = {}
    for v in vendite:
        m = v.get('data','')[:7]
        if m: mensile[m] = mensile.get(m,0) + abs(v.get('totale',0))
    mensile_sorted = sorted(mensile.items())

    # ── Build PDF ─────────────────────────────────────────────────
    n_mesi  = f"{start_date[:7]} / {end_date[:7]}" if start_date[:7] != end_date[:7] else start_date[:7]
    pdf = FlowPDF("REPORT VENDITE", f"Periodo: {start_date}  —  {end_date}")
    pdf.add_page()

    # KPI row 1
    pdf.kpi_row([
        ("FATTURATO TOTALE",  f"EUR {fatturato:,.2f}", C_BLUE,    None),
        ("TRANSAZIONI",       f"{num_tx:,}",            C_EMERALD, f"{len(vendite):,} righe"),
        ("CLIENTI ATTIVI",    f"{len(clienti_set):,}",  C_VIOLET,  None),
        ("SCONTRINO MEDIO",   f"EUR {scontrino:,.2f}",  C_AMBER,   None),
    ])
    # KPI row 2
    if margine_medio > 0:
        pdf.kpi_row([
            ("MARGINE MEDIO",   f"{margine_medio:.1f}%",
             C_EMERALD if margine_medio >= 15 else C_AMBER, "pesato sul fatturato"),
            ("PROFITTO STIMATO", f"EUR {profitto_tot:,.2f}", C_EMERALD,  None),
            ("PRODOTTI VENDUTI", f"{len(prod):,}",            C_BLUE,    None),
            ("COSTO STIMATO",    f"EUR {fatturato-profitto_tot:,.2f}", C_SLATE, None),
        ])

    # Monthly trend (visual chart — no useless % column)
    if mensile_sorted:
        pdf.section_title("Andamento mensile fatturato", C_BLUE, top_gap=3)
        pdf.monthly_chart(mensile_sorted, 'EUR ')

    # Top products
    pdf.section_title("Top 15 Prodotti per fatturato", C_BLUE, top_gap=3)
    cols_p   = ["Prodotto", "Fatturato EUR", "Qty", "Margine", "Profitto EUR"]
    widths_p = [85, 38, 22, 24, 21]
    aligns_p = ['L','R','R','R','R']

    def margine_c(val): return _margine_color(val)
    def default_c(val): return C_NAVY

    pdf.smart_table(
        cols_p, widths_p,
        [[r[0][:32], f"{r[1]:,.2f}", f"{r[2]:,.0f}", r[3], r[4]] for r in top_prod],
        aligns_p,
        col_colors={3: margine_c}
    )

    # Top clients
    pdf.section_title("Top 15 Clienti per fatturato", C_EMERALD, top_gap=3)
    cols_c   = ["Cliente", "Fatturato EUR", "Visite", "% su tot."]
    widths_c = [95, 45, 25, 25]
    aligns_c = ['L','R','C','R']
    rows_c   = []
    for nome, rev, visite in top_cli:
        pct = rev / fatturato * 100 if fatturato > 0 else 0
        rows_c.append([nome[:35], f"{rev:,.2f}", str(visite), f"{pct:.1f}%"])
    pdf.smart_table(cols_c, widths_c, rows_c, aligns_c)

    pdf_bytes = pdf.output()
    fn = f"report_vendite_{start_date}_{end_date}.pdf"
    return Response(bytes(pdf_bytes), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={fn}"})


# ══════════════════════════════════════════════════════════════════
#  ACQUISTI
# ══════════════════════════════════════════════════════════════════
async def _acquisti_pdf(query, start_date, end_date):
    ordini = await db.ordini.find(query, {"_id": 0}).sort("data", 1).to_list(200000)
    speso  = sum(abs(o.get('totale',0)) for o in ordini)
    n_ord  = len(ordini)
    forn_s = set(o.get('fornitore_nome','') for o in ordini if o.get('fornitore_nome'))

    forn = {}
    for o in ordini:
        f = o.get('fornitore_nome','')
        if f:
            if f not in forn: forn[f] = {'tot':0,'n':0}
            forn[f]['tot'] += abs(o.get('totale',0)); forn[f]['n'] += 1
    top_forn = sorted(forn.items(), key=lambda x: x[1]['tot'], reverse=True)[:15]

    prod_acq = {}
    for o in ordini:
        p = o.get('prodotto_nome','')
        if p:
            if p not in prod_acq: prod_acq[p] = {'tot':0,'qty':0}
            prod_acq[p]['tot'] += abs(o.get('totale',0))
            prod_acq[p]['qty'] += abs(o.get('quantita',0))
    top_prod_acq = sorted(prod_acq.items(), key=lambda x: x[1]['tot'], reverse=True)[:15]

    mensile = {}
    for o in ordini:
        m = o.get('data','')[:7]
        if m: mensile[m] = mensile.get(m,0) + abs(o.get('totale',0))
    mensile_sorted = sorted(mensile.items())

    ord_medio = speso / n_ord if n_ord > 0 else 0

    pdf = FlowPDF("REPORT ACQUISTI", f"Periodo: {start_date}  —  {end_date}")
    pdf.add_page()

    pdf.kpi_row([
        ("TOTALE ACQUISTATO", f"EUR {speso:,.2f}",   C_VIOLET, None),
        ("NUMERO ORDINI",     f"{n_ord:,}",            C_BLUE,   None),
        ("FORNITORI ATTIVI",  f"{len(forn_s):,}",      C_EMERALD, None),
        ("ORDINE MEDIO",      f"EUR {ord_medio:,.2f}", C_AMBER,  None),
    ])

    if mensile_sorted:
        pdf.section_title("Andamento mensile acquisti", C_VIOLET, top_gap=3)
        pdf.monthly_chart(mensile_sorted, 'EUR ')

    pdf.section_title("Top 15 Fornitori", C_VIOLET, top_gap=3)
    rows_f = []
    for nome, d in top_forn:
        pct = d['tot'] / speso * 100 if speso > 0 else 0
        rows_f.append([nome[:35], f"{d['tot']:,.2f}", str(d['n']), f"{pct:.1f}%"])
    pdf.smart_table(
        ["Fornitore", "Spesa EUR", "Ordini", "% su tot."],
        [95, 45, 25, 25],
        rows_f, ['L','R','C','R']
    )

    pdf.section_title("Top 15 Prodotti acquistati", C_BLUE, top_gap=3)
    rows_pa = [[n[:38], f"{d['tot']:,.2f}", f"{d['qty']:,.0f}"]
               for n, d in top_prod_acq]
    pdf.smart_table(
        ["Prodotto", "Spesa EUR", "Qty"],
        [120, 45, 25],
        rows_pa, ['L','R','R']
    )

    pdf_bytes = pdf.output()
    fn = f"report_acquisti_{start_date}_{end_date}.pdf"
    return Response(bytes(pdf_bytes), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={fn}"})
