from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from typing import Optional
from datetime import datetime, timedelta
from fpdf import FPDF

from database import db

router = APIRouter()


class FlussoReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 58, 95)
        self.cell(0, 10, "Flusso - Report Statistiche", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_draw_color(0, 180, 216)
        self.set_line_width(0.6)
        self.line(10, 18, 200, 18)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Pagina {self.page_no()} - Generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="C")

    def section_title(self, text):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(30, 58, 95)
        self.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 180, 216)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 100, self.get_y())
        self.ln(3)

    def kpi_row(self, label, value):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(80, 80, 80)
        self.cell(70, 7, label, new_x="RIGHT")
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(30, 58, 95)
        self.cell(0, 7, str(value), new_x="LMARGIN", new_y="NEXT")

    def table_header(self, cols, widths):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(30, 58, 95)
        self.set_text_color(255, 255, 255)
        for col, w in zip(cols, widths):
            self.cell(w, 7, col, border=1, fill=True, align="C")
        self.ln()

    def table_row(self, values, widths, aligns=None):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(50, 50, 50)
        self.set_fill_color(245, 247, 250)
        fill = self.page_break_trigger and False
        for i, (val, w) in enumerate(zip(values, widths)):
            a = (aligns[i] if aligns else "L")
            self.cell(w, 6, str(val)[:30], border=1, align=a)
        self.ln()


@router.get("/statistiche/export/pdf")
async def export_statistiche_pdf(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tipo: str = "vendite"
):
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    now = datetime.now()

    if not start_date:
        start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = now.strftime("%Y-%m-%d")

    query = {"data": {"$gte": start_date, "$lte": end_date}}

    if tipo == "vendite":
        vendite = await db.vendite.find(query, {"_id": 0}).sort("data", -1).to_list(100000)
        vendite = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]

        fatturato = sum(abs(v.get('totale', 0)) for v in vendite)
        num_vendite = len(vendite)
        clienti_set = set(v.get('cliente_nome', '') for v in vendite if v.get('cliente_nome'))

        # Top prodotti with margin calculation using WEIGHTED average
        prod_data = {}
        for v in vendite:
            p = v.get('prodotto_nome', '')
            if p not in prod_data:
                prod_data[p] = {'fatturato': 0, 'qty': 0}
            prod_data[p]['fatturato'] += abs(v.get('totale', 0))
            prod_data[p]['qty'] += abs(v.get('quantita', 0))
        
        # Get purchase prices and calculate margins
        top_prod_with_margin = []
        totale_fatturato_con_margine = 0
        somma_margini_ponderati = 0
        totale_profitto = 0
        
        for nome, dati in sorted(prod_data.items(), key=lambda x: x[1]['fatturato'], reverse=True)[:10]:
            item = {'nome': nome, 'fatturato': dati['fatturato'], 'margine': None, 'profitto': None}
            
            # Get last purchase price
            ultimo_ordine = await db.ordini.find_one(
                {"prodotto_nome": nome, "prezzo_unitario": {"$gt": 0}},
                {"_id": 0, "prezzo_unitario": 1},
                sort=[("data", -1)]
            )
            if ultimo_ordine and dati['qty'] > 0:
                prezzo_acquisto = ultimo_ordine.get('prezzo_unitario', 0)
                # Weighted average: total revenue / total quantity
                prezzo_vendita = dati['fatturato'] / dati['qty']
                
                # Filter out anomalous prices
                if prezzo_acquisto > 0 and prezzo_acquisto < 500:
                    # Skip if sale price is unreasonably different from purchase price
                    if prezzo_vendita <= prezzo_acquisto * 5 and prezzo_vendita >= prezzo_acquisto * 0.2:
                        costo_totale = prezzo_acquisto * dati['qty']
                        profitto = dati['fatturato'] - costo_totale
                        margine = ((prezzo_vendita - prezzo_acquisto) / prezzo_acquisto) * 100
                        
                        # Only include reasonable margins (-50% to +200%)
                        if -50 < margine < 200:
                            item['margine'] = round(margine, 1)
                            item['profitto'] = round(profitto, 2)
                            
                            # Accumulate for weighted average margin calculation
                            totale_fatturato_con_margine += dati['fatturato']
                            somma_margini_ponderati += margine * dati['fatturato']
                            totale_profitto += profitto
            
            top_prod_with_margin.append(item)
        
        # Calculate weighted average margin: sum(margine * fatturato) / sum(fatturato)
        margine_medio = (somma_margini_ponderati / totale_fatturato_con_margine) if totale_fatturato_con_margine > 0 else 0

        # Top clienti
        cli_rev = {}
        for v in vendite:
            c = v.get('cliente_nome', '')
            if c:
                cli_rev[c] = cli_rev.get(c, 0) + abs(v.get('totale', 0))
        top_cli = sorted(cli_rev.items(), key=lambda x: x[1], reverse=True)[:10]

        pdf = FlussoReport()
        pdf.add_page()
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 7, f"Periodo: {start_date} - {end_date}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(5)

        pdf.section_title("Riepilogo Vendite")
        pdf.kpi_row("Fatturato Totale:", f"EUR {fatturato:,.2f}")
        pdf.kpi_row("Numero Transazioni:", f"{num_vendite:,}")
        pdf.kpi_row("Clienti Unici:", f"{len(clienti_set)}")
        pdf.kpi_row("Scontrino Medio:", f"EUR {fatturato / num_vendite:,.2f}" if num_vendite > 0 else "N/A")
        if margine_medio > 0:
            pdf.kpi_row("Margine Medio Stimato:", f"{margine_medio:.1f}%")
            pdf.kpi_row("Profitto Stimato:", f"EUR {totale_profitto:,.2f}")
        pdf.ln(5)

        pdf.section_title("Top 10 Prodotti (con Margine)")
        pdf.table_header(["#", "Prodotto", "Fatturato", "Margine", "Profitto"], [8, 80, 40, 30, 32])
        for i, item in enumerate(top_prod_with_margin):
            margine_str = f"{item['margine']:.0f}%" if item['margine'] is not None else "N/A"
            profitto_str = f"EUR {item['profitto']:,.0f}" if item['profitto'] is not None else "N/A"
            pdf.table_row(
                [str(i + 1), item['nome'][:25], f"EUR {item['fatturato']:,.0f}", margine_str, profitto_str],
                [8, 80, 40, 30, 32], ["C", "L", "R", "R", "R"]
            )
        pdf.ln(5)

        pdf.section_title("Top 10 Clienti")
        pdf.table_header(["#", "Cliente", "Spesa"], [10, 120, 60])
        for i, (nome, rev) in enumerate(top_cli):
            pdf.table_row([str(i + 1), nome[:30], f"EUR {rev:,.2f}"], [10, 120, 60], ["C", "L", "R"])

    elif tipo == "acquisti":
        ordini = await db.ordini.find(query, {"_id": 0}).sort("data", -1).to_list(100000)
        totale_speso = sum(abs(o.get('totale', 0)) for o in ordini)
        num_ordini = len(ordini)
        fornitori_set = set(o.get('fornitore_nome', '') for o in ordini if o.get('fornitore_nome'))

        forn_rev = {}
        for o in ordini:
            f = o.get('fornitore_nome', '')
            if f:
                forn_rev[f] = forn_rev.get(f, 0) + abs(o.get('totale', 0))
        top_forn = sorted(forn_rev.items(), key=lambda x: x[1], reverse=True)[:10]

        prod_rev = {}
        for o in ordini:
            p = o.get('prodotto_nome', '')
            prod_rev[p] = prod_rev.get(p, 0) + abs(o.get('totale', 0))
        top_prod = sorted(prod_rev.items(), key=lambda x: x[1], reverse=True)[:10]

        pdf = FlussoReport()
        pdf.add_page()
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 7, f"Periodo: {start_date} - {end_date}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(5)

        pdf.section_title("Riepilogo Acquisti")
        pdf.kpi_row("Totale Acquisti:", f"EUR {totale_speso:,.2f}")
        pdf.kpi_row("Numero Ordini:", f"{num_ordini:,}")
        pdf.kpi_row("Fornitori Unici:", f"{len(fornitori_set)}")
        pdf.ln(5)

        pdf.section_title("Top 10 Fornitori")
        pdf.table_header(["#", "Fornitore", "Spesa"], [10, 120, 60])
        for i, (nome, rev) in enumerate(top_forn):
            pdf.table_row([str(i + 1), nome[:30], f"EUR {rev:,.2f}"], [10, 120, 60], ["C", "L", "R"])
        pdf.ln(5)

        pdf.section_title("Top 10 Prodotti Acquistati")
        pdf.table_header(["#", "Prodotto", "Spesa"], [10, 120, 60])
        for i, (nome, rev) in enumerate(top_prod):
            pdf.table_row([str(i + 1), nome[:30], f"EUR {rev:,.2f}"], [10, 120, 60], ["C", "L", "R"])

    else:
        raise HTTPException(status_code=400, detail="Tipo non valido. Usa 'vendite' o 'acquisti'")

    pdf_bytes = pdf.output()
    filename = f"report_{tipo}_{start_date}_{end_date}.pdf"
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
