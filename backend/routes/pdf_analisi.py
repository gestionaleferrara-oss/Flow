"""PDF della pagina Analisi + Rendiconto vendite (provvigione sul margine)."""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from database import db
from routes.analisi import (EXCLUDED_CLIENTS, analisi_acquisti, analisi_vendite_prodotti,
                            esclusi_filter, resolve_period)
from routes.pdf_helper import (C_AMBER, C_BLUE, C_EMERALD, C_NAVY, C_RED, C_SLATE, C_VIOLET,
                               FlowPDF, clean_text)
from routes.pdf_sections import (blocco_confronto, blocco_considerazioni, blocco_prezzi_aumento,
                                 blocco_sintesi, concentrazione, kpi_acquisti, kpi_vendite,
                                 periodi_anno_su_anno, prezzi_in_aumento, righe_confronto_acquisti,
                                 righe_confronto_vendite, testo_sintesi_acquisti, testo_sintesi_vendite, it_eur)

router = APIRouter()
logger = logging.getLogger(__name__)

PROVVIGIONE_DEFAULT = 3.0


def _eur(v) -> str:
    return f"{(v or 0):,.2f}"


def _short(text, n):
    t = clean_text(text or '')
    return t if len(t) <= n else t[:n - 1] + '.'


def _dm(data: Optional[str]) -> str:
    if not data or len(data) < 10:
        return '-'
    return f"{data[8:10]}/{data[5:7]}/{data[2:4]}"


def _margin_color(val):
    try:
        v = float(str(val).replace('%', ''))
    except Exception:
        return C_NAVY
    if v >= 20:
        return C_EMERALD
    if v >= 8:
        return C_AMBER
    return C_RED


# ═════════════════ RENDICONTO VENDITE (provvigione) ═════════════════

@router.get("/analisi/export/rendiconto")
async def export_rendiconto(
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    provvigione_pct: float = PROVVIGIONE_DEFAULT, dettaglio: bool = False,
    max_righe: int = 2500, max_prodotti: int = 40, max_lotti: int = 40, max_clienti: int = 25
):
    """Rendiconto del venduto con costi reali dei lotti (FIFO) e provvigione sul margine."""
    try:
        start, end, _, _ = await resolve_period(start_date, end_date)
        excl = await esclusi_filter()
        match = {"data": {"$gte": start, "$lte": end},
                 "cliente_nome": {"$nin": EXCLUDED_CLIENTS}, **excl}

        righe = await db.vendite.find(
            match,
            {"_id": 0, "data": 1, "cliente_nome": 1, "prodotto_nome": 1, "quantita": 1,
             "totale": 1, "costo_fifo": 1, "costo_unitario_fifo": 1, "lotto_id": 1,
             "fifo_tracciato": 1}
        ).sort([("data", 1)]).to_list(200000)

        if not righe:
            raise HTTPException(status_code=404, detail="Nessuna vendita nel periodo selezionato")

        tot_fatt = tot_qty = tot_costo = 0.0
        prodotti, clienti, lotti_uso = {}, {}, {}
        qty_tracciata = 0.0

        for r in righe:
            qty = abs(r.get('quantita', 0) or 0)
            fatt = abs(r.get('totale', 0) or 0)
            costo = r.get('costo_fifo', 0) or 0
            tot_fatt += fatt
            tot_qty += qty
            tot_costo += costo
            if r.get('fifo_tracciato'):
                qty_tracciata += qty

            p = prodotti.setdefault(r.get('prodotto_nome', ''), {"qty": 0.0, "fatt": 0.0, "costo": 0.0, "righe": 0})
            p['qty'] += qty; p['fatt'] += fatt; p['costo'] += costo; p['righe'] += 1

            c = clienti.setdefault(r.get('cliente_nome', ''), {"qty": 0.0, "fatt": 0.0, "costo": 0.0})
            c['qty'] += qty; c['fatt'] += fatt; c['costo'] += costo

            lid = r.get('lotto_id')
            if lid:
                lo = lotti_uso.setdefault(lid, {"qty": 0.0, "fatt": 0.0, "costo": 0.0})
                lo['qty'] += qty; lo['fatt'] += fatt; lo['costo'] += costo

        margine = tot_fatt - tot_costo
        margine_pct = (margine / tot_costo * 100) if tot_costo > 0 else 0
        provvigione = margine * provvigione_pct / 100
        copertura = (qty_tracciata / tot_qty * 100) if tot_qty > 0 else 0

        lotti_docs = await db.lotti.find({"lotto_id": {"$in": list(lotti_uso.keys())}}, {"_id": 0}).to_list(50000)
        lotti_map = {d['lotto_id']: d for d in lotti_docs}

        periodo_label = f"{_dm(start)} - {_dm(end)}"
        pdf = FlowPDF("RENDICONTO VENDITE", f"Periodo: {periodo_label}  |  Costi reali dei lotti (FIFO)")
        pdf.add_page()

        pdf.kpi_row([
            ("FATTURATO VENDUTO", f"EUR {_eur(tot_fatt)}", C_BLUE, f"{len(righe):,} scarichi"),
            ("COSTO MERCE (LOTTI)", f"EUR {_eur(tot_costo)}", C_SLATE, f"{tot_qty:,.0f} pezzi"),
            ("MARGINE GENERATO", f"EUR {_eur(margine)}", C_EMERALD, f"{margine_pct:.1f}% sul costo"),
            ("PROVVIGIONE DOVUTA", f"EUR {_eur(provvigione)}", C_VIOLET, f"{provvigione_pct:g}% del margine"),
        ])
        pdf.kpi_row([
            ("PRODOTTI VENDUTI", f"{len(prodotti)}", C_BLUE, None),
            ("CLIENTI SERVITI", f"{len(clienti)}", C_BLUE, None),
            ("LOTTI UTILIZZATI", f"{len(lotti_uso)}", C_AMBER, None),
            ("COPERTURA LOTTI REALI", f"{copertura:.0f}%", C_EMERALD if copertura >= 80 else C_AMBER,
             "resto a costo stimato"),
        ])

        # ── Sintesi narrativa + confronto ultimi due esercizi ──
        p0, p1 = periodi_anno_su_anno(start, end)
        a0 = await kpi_vendite(excl, *p0)
        a1 = await kpi_vendite(excl, *p1)
        tot = {"fatturato": tot_fatt, "quantita": tot_qty, "costo": tot_costo, "margine": margine,
               "margine_pct": margine_pct, "righe": len(righe), "n_clienti": len(clienti),
               "n_prodotti": len(prodotti)}
        conc = concentrazione([d['fatt'] for d in prodotti.values()])
        extra = (f"La provvigione calcolata al {provvigione_pct:g}% del margine generato ammonta a "
                 f"{it_eur(provvigione, 2)}.")
        blocco_sintesi(pdf, testo_sintesi_vendite(periodo_label, tot, a0, a1, conc, extra))
        blocco_confronto(pdf, righe_confronto_vendite(a0, a1))

        # ── Riepilogo per prodotto (ordinato per margine, dal piu' alto) ──
        pdf.section_title("Riepilogo per prodotto (ordinato per margine %)", C_BLUE, top_gap=2)
        prod_sorted = sorted(prodotti.items(),
                             key=lambda x: -((x[1]['fatt'] - x[1]['costo']) / x[1]['costo'] * 100
                                             if x[1]['costo'] > 0 else -9999))
        rows = []
        for nome, d in prod_sorted[:max_prodotti]:
            marg = d['fatt'] - d['costo']
            rows.append([
                _short(nome, 44), f"{d['qty']:,.0f}",
                _eur(d['fatt'] / d['qty']) if d['qty'] else '-',
                _eur(d['costo'] / d['qty']) if (d['costo'] and d['qty']) else '-',
                _eur(d['fatt']), _eur(marg),
                f"{marg / d['costo'] * 100:.1f}%" if d['costo'] > 0 else '-',
            ])
        resto = prod_sorted[max_prodotti:]
        if resto:
            r_qty = sum(d['qty'] for _, d in resto)
            r_fatt = sum(d['fatt'] for _, d in resto)
            r_costo = sum(d['costo'] for _, d in resto)
            rows.append([f"Altri {len(resto)} prodotti", f"{r_qty:,.0f}", '-', '-',
                         _eur(r_fatt), _eur(r_fatt - r_costo),
                         f"{(r_fatt - r_costo) / r_costo * 100:.1f}%" if r_costo > 0 else '-'])
        pdf.smart_table(
            ['Prodotto', 'Qta', 'Prz. vendita', 'Costo/u', 'Fatturato', 'Margine', 'Marg. %'],
            [70, 16, 22, 22, 26, 22, 12], rows,
            aligns=['L', 'R', 'R', 'R', 'R', 'R', 'R'], col_colors={6: _margin_color})

        # ── Lotti utilizzati ──
        pdf.section_title("Lotti di acquisto utilizzati per il venduto", C_AMBER)
        lotti_sorted = sorted(lotti_uso.items(), key=lambda x: -(x[1]['fatt'] - x[1]['costo']))
        lrows = []
        for lid, u in lotti_sorted[:max_lotti]:
            lot = lotti_map.get(lid, {})
            marg = u['fatt'] - u['costo']
            lrows.append([
                _short(lot.get('prodotto', '-'), 30),
                _dm(lot.get('data_acquisto')),
                _short(lot.get('fornitore', '-'), 24),
                _eur(lot.get('prezzo_acquisto', 0)) + ('*' if lot.get('prezzo_stimato') else ''),
                f"{u['qty']:,.0f}", _eur(u['fatt']), _eur(marg),
                f"{marg / u['costo'] * 100:.1f}%" if u['costo'] > 0 else '-',
                _dm(lot.get('data_esaurimento')) if lot.get('data_esaurimento') else 'in corso',
            ])
        resto_l = lotti_sorted[max_lotti:]
        if resto_l:
            r_qty = sum(u['qty'] for _, u in resto_l)
            r_fatt = sum(u['fatt'] for _, u in resto_l)
            r_costo = sum(u['costo'] for _, u in resto_l)
            lrows.append([f"Altri {len(resto_l)} lotti", '-', '-', '-', f"{r_qty:,.0f}",
                          _eur(r_fatt), _eur(r_fatt - r_costo),
                          f"{(r_fatt - r_costo) / r_costo * 100:.1f}%" if r_costo > 0 else '-', '-'])
        pdf.smart_table(
            ['Prodotto', 'Acquisto', 'Fornitore', 'Prz. acq.', 'Qta scar.', 'Ricavo', 'Margine', 'Marg. %', 'Esaurito'],
            [44, 16, 38, 17, 17, 20, 18, 14, 16], lrows,
            aligns=['L', 'C', 'L', 'R', 'R', 'R', 'R', 'R', 'C'], col_colors={7: _margin_color})
        pdf.note_text("Ogni scarico e' collegato al lotto di acquisto effettivamente consumato (metodo FIFO: primo "
                      "entrato, primo uscito). La colonna 'Esaurito' indica la data in cui il lotto e' finito e le "
                      "vendite sono passate al lotto successivo. (*) prezzo di acquisto stimato: la riga di acquisto "
                      "originale non riportava il prezzo.")

        # ── Clienti ──
        pdf.section_title("Venduto per cliente", C_VIOLET)
        cli_sorted = sorted(clienti.items(), key=lambda x: -(x[1]['fatt'] - x[1]['costo']))
        crows = []
        for nome, d in cli_sorted[:max_clienti]:
            marg = d['fatt'] - d['costo']
            crows.append([
                _short(nome, 52), f"{d['qty']:,.0f}", _eur(d['fatt']), _eur(d['costo']), _eur(marg),
                f"{marg / d['costo'] * 100:.1f}%" if d['costo'] > 0 else '-',
            ])
        resto_c = cli_sorted[max_clienti:]
        if resto_c:
            r_qty = sum(d['qty'] for _, d in resto_c)
            r_fatt = sum(d['fatt'] for _, d in resto_c)
            r_costo = sum(d['costo'] for _, d in resto_c)
            crows.append([f"Altri {len(resto_c)} clienti", f"{r_qty:,.0f}", _eur(r_fatt), _eur(r_costo),
                          _eur(r_fatt - r_costo),
                          f"{(r_fatt - r_costo) / r_costo * 100:.1f}%" if r_costo > 0 else '-'])
        pdf.smart_table(['Cliente', 'Qta', 'Fatturato', 'Costo lotti', 'Margine', 'Marg. %'],
                        [78, 20, 26, 24, 24, 18], crows,
                        aligns=['L', 'R', 'R', 'R', 'R', 'R'], col_colors={5: _margin_color})

        # ── Dettaglio analitico ──
        if dettaglio:
            pdf.add_page()
            pdf.section_title(f"Dettaglio analitico degli scarichi ({min(len(righe), max_righe):,} righe)", C_NAVY, top_gap=0)
            drows = []
            for r in righe[:max_righe]:
                qty = abs(r.get('quantita', 0) or 0)
                fatt = abs(r.get('totale', 0) or 0)
                costo = r.get('costo_fifo', 0) or 0
                lot = lotti_map.get(r.get('lotto_id'), {})
                drows.append([
                    _dm(r.get('data')), _short(r.get('cliente_nome', ''), 32),
                    _short(r.get('prodotto_nome', ''), 34), f"{qty:,.0f}",
                    _eur(fatt / qty) if qty else '-',
                    _eur(costo / qty) if (costo and qty) else '-',
                    _eur(fatt - costo),
                    f"{(fatt - costo) / costo * 100:.0f}%" if costo > 0 else '-',
                    _dm(lot.get('data_acquisto')) if lot else '-',
                ])
            pdf.smart_table(
                ['Data', 'Cliente', 'Prodotto', 'Qta', 'Prz. vend.', 'Costo/u', 'Margine', 'M%', 'Lotto'],
                [15, 46, 48, 12, 17, 16, 18, 10, 15], drows, row_h=5,
                aligns=['C', 'L', 'L', 'R', 'R', 'R', 'R', 'R', 'C'], col_colors={7: _margin_color})
            if len(righe) > max_righe:
                pdf.note_text(f"Elencate le prime {max_righe:,} righe su {len(righe):,} totali del periodo.")

        # ── Attestazione ──
        pdf.ensure_space(40)
        pdf.section_title("Riepilogo finale", C_EMERALD)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(40, 50, 70)
        testo = (
            f"Nel periodo {periodo_label} sono stati registrati {len(righe):,} scarichi di vendita per "
            f"{tot_qty:,.0f} pezzi, corrispondenti a un fatturato di EUR {_eur(tot_fatt)}. "
            f"Il costo della merce, ricostruito collegando ogni scarico al relativo lotto di acquisto "
            f"(metodo FIFO), e' pari a EUR {_eur(tot_costo)}, con un margine generato di "
            f"EUR {_eur(margine)} ({margine_pct:.1f}% sul costo). "
            f"La provvigione calcolata al {provvigione_pct:g}% del margine generato e' pari a "
            f"EUR {_eur(provvigione)}."
        )
        pdf.multi_cell(190, 5, clean_text(testo))
        pdf.ln(4)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*C_VIOLET)
        pdf.cell(0, 7, clean_text(f"PROVVIGIONE DOVUTA: EUR {_eur(provvigione)}"), ln=True)

        out = pdf.output()
        fname = f"rendiconto_{start}_{end}.pdf"
        return Response(bytes(out), media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename={fname}"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore export rendiconto: {e}")
        raise HTTPException(status_code=500, detail=f"Errore generazione PDF: {str(e)}")


@router.get("/analisi/export/rendiconto-acquisti")
async def export_rendiconto_acquisti(
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    fornitore: Optional[str] = None, prodotto: Optional[str] = None,
    provvigione_pct: float = PROVVIGIONE_DEFAULT,
    max_fornitori: int = 30, max_lotti: int = 60
):
    """Rendiconto dal lato acquisti: per ogni lotto acquistato nel periodo mostra quanto e'
    stato venduto, il ricavo, il margine reale e i giorni di smaltimento."""
    try:
        start, end, _, _ = await resolve_period(start_date, end_date)
        query = {"data_acquisto": {"$gte": start, "$lte": end}}
        if fornitore:
            query["fornitore"] = {"$regex": fornitore, "$options": "i"}
        if prodotto:
            query["prodotto"] = {"$regex": prodotto, "$options": "i"}
        lotti = await db.lotti.find(query, {"_id": 0}).sort([("data_acquisto", 1)]).to_list(50000)
        if not lotti:
            raise HTTPException(status_code=404, detail="Nessun lotto acquistato nel periodo selezionato")

        def giorni(lot):
            if not lot.get('data_esaurimento'):
                return None
            try:
                d1 = datetime.strptime(lot['data_acquisto'], "%Y-%m-%d")
                d2 = datetime.strptime(lot['data_esaurimento'], "%Y-%m-%d")
                return (d2 - d1).days
            except Exception:
                return None

        tot_spesa = tot_qty = tot_venduta = tot_ricavo = tot_costo_venduto = tot_residuo = 0.0
        fornitori = {}
        esauriti = 0
        giorni_list = []
        for lot in lotti:
            qta = lot.get('quantita', 0) or 0
            prezzo = lot.get('prezzo_acquisto', 0) or 0
            venduta = lot.get('quantita_venduta', 0) or 0
            ricavo = lot.get('ricavo', 0) or 0
            costo_venduto = venduta * prezzo
            tot_spesa += qta * prezzo
            tot_qty += qta
            tot_venduta += venduta
            tot_ricavo += ricavo
            tot_costo_venduto += costo_venduto
            tot_residuo += (lot.get('residuo', 0) or 0) * prezzo
            if lot.get('data_esaurimento'):
                esauriti += 1
                g = giorni(lot)
                if g is not None:
                    giorni_list.append(g)
            f = fornitori.setdefault(lot.get('fornitore', '-'),
                                     {"lotti": 0, "qta": 0.0, "spesa": 0.0, "venduta": 0.0,
                                      "ricavo": 0.0, "costo_venduto": 0.0, "residuo": 0.0})
            f['lotti'] += 1; f['qta'] += qta; f['spesa'] += qta * prezzo
            f['venduta'] += venduta; f['ricavo'] += ricavo; f['costo_venduto'] += costo_venduto
            f['residuo'] += (lot.get('residuo', 0) or 0) * prezzo

        margine = tot_ricavo - tot_costo_venduto
        margine_pct = (margine / tot_costo_venduto * 100) if tot_costo_venduto > 0 else 0
        provvigione = margine * provvigione_pct / 100
        smaltimento = (sum(giorni_list) / len(giorni_list)) if giorni_list else None

        periodo_label = f"{_dm(start)} - {_dm(end)}"
        filtri = []
        if fornitore:
            filtri.append(f"Fornitore: {fornitore}")
        if prodotto:
            filtri.append(f"Prodotto: {prodotto}")
        sub = f"Lotti acquistati dal {periodo_label}  |  Resa reale del venduto (FIFO)"
        if filtri:
            sub += "  |  " + "  ".join(filtri)
        pdf = FlowPDF("RENDICONTO ACQUISTI E LOTTI", sub)
        pdf.add_page()
        pdf.kpi_row([
            ("SPESA ACQUISTI", f"EUR {_eur(tot_spesa)}", C_AMBER, f"{len(lotti)} lotti"),
            ("VENDUTO DAI LOTTI", f"EUR {_eur(tot_ricavo)}", C_BLUE,
             f"{tot_venduta:,.0f} di {tot_qty:,.0f} pezzi"),
            ("MARGINE GENERATO", f"EUR {_eur(margine)}", C_EMERALD, f"{margine_pct:.1f}% sul costo"),
            ("PROVVIGIONE DOVUTA", f"EUR {_eur(provvigione)}", C_VIOLET, f"{provvigione_pct:g}% del margine"),
        ])
        pdf.kpi_row([
            ("FORNITORI", f"{len(fornitori)}", C_BLUE, None),
            ("LOTTI ESAURITI", f"{esauriti}/{len(lotti)}", C_EMERALD, "completamente venduti"),
            ("GIACENZA RESIDUA", f"EUR {_eur(tot_residuo)}", C_AMBER, "a costo di acquisto"),
            ("SMALTIMENTO MEDIO", f"{smaltimento:.0f} giorni" if smaltimento is not None else "-",
             C_SLATE, "dall'acquisto all'esaurimento"),
        ])

        # ── Sintesi narrativa + confronto ultimi due esercizi + prezzi in aumento ──
        ord_match = {}
        if fornitore:
            ord_match["fornitore_nome"] = {"$regex": fornitore, "$options": "i"}
        if prodotto:
            ord_match["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}
        p0, p1 = periodi_anno_su_anno(start, end)
        a0 = await kpi_acquisti(ord_match, *p0)
        a1 = await kpi_acquisti(ord_match, *p1)
        prezzi_su = await prezzi_in_aumento(ord_match, p0, p1)
        prod_spese = {}
        for lot in lotti:
            prod_spese[lot.get('prodotto', '-')] = prod_spese.get(lot.get('prodotto', '-'), 0) + \
                (lot.get('quantita', 0) or 0) * (lot.get('prezzo_acquisto', 0) or 0)
        tot_acq = {"spesa": tot_spesa, "quantita": tot_qty, "righe": len(lotti),
                   "n_fornitori": len(fornitori), "n_prodotti": len(prod_spese)}
        extra = (f"Dei {len(lotti)} lotti acquistati nel periodo, {esauriti} risultano completamente venduti"
                 + (f" con un tempo medio di smaltimento di {smaltimento:.0f} giorni" if smaltimento is not None else "")
                 + f"; il venduto di questi lotti ha generato un margine di {it_eur(margine, 2)} "
                   f"({margine_pct:.1f}% sul costo), su cui la provvigione al {provvigione_pct:g}% "
                   f"vale {it_eur(provvigione, 2)}.")
        blocco_sintesi(pdf, testo_sintesi_acquisti(periodo_label, tot_acq, a0, a1,
                                                   concentrazione(list(prod_spese.values())),
                                                   prezzi_su, extra))
        blocco_confronto(pdf, righe_confronto_acquisti(a0, a1))
        blocco_prezzi_aumento(pdf, prezzi_su)

        pdf.section_title("Resa per fornitore", C_AMBER, top_gap=2)
        f_sorted = sorted(fornitori.items(),
                          key=lambda x: -((x[1]['ricavo'] - x[1]['costo_venduto']) / x[1]['costo_venduto'] * 100
                                          if x[1]['costo_venduto'] > 0 else -9999))
        frows = []
        for nome, d in f_sorted[:max_fornitori]:
            marg = d['ricavo'] - d['costo_venduto']
            frows.append([
                _short(nome, 40), f"{d['lotti']}", f"{d['qta']:,.0f}",
                _eur(d['spesa'] / d['qta']) if d['qta'] else '-',
                f"{d['venduta']:,.0f}",
                _eur(d['ricavo'] / d['venduta']) if d['venduta'] else '-',
                _eur(d['ricavo']), _eur(marg),
                f"{marg / d['costo_venduto'] * 100:.1f}%" if d['costo_venduto'] > 0 else '-',
            ])
        pdf.smart_table(['Fornitore', 'Lotti', 'Qta acq.', 'Prz. acq.', 'Qta vend.', 'Prz. vend.', 'Ricavo', 'Margine', 'Marg. %'],
                        [62, 11, 17, 17, 17, 17, 20, 18, 11], frows,
                        aligns=['L', 'R', 'R', 'R', 'R', 'R', 'R', 'R', 'R'], col_colors={8: _margin_color})
        pdf.note_text("Prz. acq. = spesa / quantita acquistata nel periodo. Prz. vend. = ricavo / quantita venduta "
                      "dei lotti. Il ricavo e il margine si riferiscono a tutto il venduto di quei lotti, anche se "
                      "avvenuto dopo la fine del periodo.")

        pdf.section_title("Lotti acquistati (ordinati per margine %)", C_BLUE)
        l_sorted = sorted(lotti, key=lambda lot: -(lot['margine_pct'] if lot.get('margine_pct') is not None else -9999))
        lrows = []
        for lot in l_sorted[:max_lotti]:
            g = giorni(lot)
            lrows.append([
                _short(lot.get('prodotto', '-'), 30), _dm(lot.get('data_acquisto')),
                _short(lot.get('fornitore', '-'), 20), f"{lot.get('quantita', 0):,.0f}",
                _eur(lot.get('prezzo_acquisto', 0)) + ('*' if lot.get('prezzo_stimato') else ''),
                f"{lot.get('quantita_venduta', 0):,.0f}",
                _eur(lot.get('prezzo_vendita_medio')) if lot.get('prezzo_vendita_medio') else '-',
                f"{lot['margine_pct']:.1f}%" if lot.get('margine_pct') is not None else '-',
                _dm(lot.get('data_esaurimento')) if lot.get('data_esaurimento') else 'in corso',
                f"{g}gg" if g is not None else '-',
            ])
        pdf.smart_table(
            ['Prodotto', 'Acquisto', 'Fornitore', 'Qta', 'Prz. acq.', 'Qta vend.', 'Prz. vend.', 'Marg. %', 'Esaurito', 'Giorni'],
            [42, 15, 32, 14, 17, 15, 17, 14, 15, 12], lrows,
            aligns=['L', 'C', 'L', 'R', 'R', 'R', 'R', 'R', 'C', 'R'], col_colors={7: _margin_color})
        pdf.note_text("Ogni lotto e' una riga di acquisto; le quantita' vendute e il ricavo derivano dal collegamento "
                      "FIFO con le vendite. 'Giorni' = tempo di smaltimento dall'acquisto all'esaurimento. "
                      "(*) prezzo di acquisto stimato perche' assente nella riga originale.")

        pdf.ensure_space(40)
        pdf.section_title("Riepilogo finale", C_EMERALD)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(40, 50, 70)
        testo = (
            f"Nel periodo {periodo_label} sono stati acquistati {len(lotti)} lotti per {tot_qty:,.0f} pezzi, "
            f"con una spesa di EUR {_eur(tot_spesa)}. Di questi risultano venduti {tot_venduta:,.0f} pezzi, "
            f"che hanno generato un ricavo di EUR {_eur(tot_ricavo)} a fronte di un costo merce di "
            f"EUR {_eur(tot_costo_venduto)}, per un margine di EUR {_eur(margine)} ({margine_pct:.1f}%). "
            f"La provvigione al {provvigione_pct:g}% del margine generato e' pari a EUR {_eur(provvigione)}. "
            f"Rimane una giacenza residua di EUR {_eur(tot_residuo)} valorizzata al costo di acquisto."
        )
        pdf.multi_cell(190, 5, clean_text(testo))
        pdf.ln(4)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*C_VIOLET)
        pdf.cell(0, 7, clean_text(f"PROVVIGIONE DOVUTA: EUR {_eur(provvigione)}"), ln=True)

        out = pdf.output()
        return Response(bytes(out), media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename=rendiconto_acquisti_{start}_{end}.pdf"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore export rendiconto acquisti: {e}")
        raise HTTPException(status_code=500, detail=f"Errore generazione PDF: {str(e)}")


# ═════════════════ PDF ANALISI (vendite / acquisti) ═════════════════

@router.get("/analisi/export/pdf")
async def export_analisi_pdf(
    tipo: str = "vendite", start_date: Optional[str] = None, end_date: Optional[str] = None,
    fornitore: Optional[str] = None, prodotto: Optional[str] = None, limit: int = 60
):
    try:
        if tipo == "acquisti":
            data = await analisi_acquisti(start_date, end_date, fornitore, prodotto, 500)
            per = data['periodo']
            k = data['kpi']
            filtri = []
            if fornitore:
                filtri.append(f"Fornitore: {fornitore}")
            if prodotto:
                filtri.append(f"Prodotto: {prodotto}")
            sub = f"Periodo: {_dm(per['start'])} - {_dm(per['end'])}"
            if filtri:
                sub += "  |  " + "  ".join(filtri)
            pdf = FlowPDF("ANALISI ACQUISTI FORNITORI", sub)
            pdf.add_page()
            pdf.kpi_row([
                ("SPESA ACQUISTI", f"EUR {_eur(k['spesa'])}", C_AMBER,
                 f"prec. EUR {_eur(k['spesa_prec'])}"),
                ("VARIAZIONE", f"{k['var_pct']:+.1f}%" if k['var_pct'] is not None else "-",
                 C_EMERALD if (k['var_pct'] or 0) >= 0 else C_RED,
                 f"vs {_dm(per['prev_start'])}-{_dm(per['prev_end'])}"),
                ("FORNITORI", f"{k['n_fornitori']}", C_BLUE, f"{k['n_prodotti']} prodotti"),
                ("RESI A FORNITORE", f"EUR {_eur(k['resi'])}", C_VIOLET, None),
            ])

            ord_match = {}
            if fornitore:
                ord_match["fornitore_nome"] = {"$regex": fornitore, "$options": "i"}
            if prodotto:
                ord_match["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}
            p0, p1 = periodi_anno_su_anno(per['start'], per['end'])
            a0 = await kpi_acquisti(ord_match, *p0)
            a1 = await kpi_acquisti(ord_match, *p1)
            prezzi_su = await prezzi_in_aumento(ord_match, p0, p1)
            tot_acq = {"spesa": k['spesa'], "quantita": k['quantita'],
                       "righe": sum(f.get('righe', 0) for f in data['fornitori']),
                       "n_fornitori": k['n_fornitori'], "n_prodotti": k['n_prodotti']}
            blocco_sintesi(pdf, testo_sintesi_acquisti(
                f"{_dm(per['start'])} - {_dm(per['end'])}", tot_acq, a0, a1,
                concentrazione([p['spesa'] for p in data['prodotti']]), prezzi_su))
            blocco_confronto(pdf, righe_confronto_acquisti(a0, a1))
            blocco_prezzi_aumento(pdf, prezzi_su)

            pdf.section_title("Acquisti per fornitore", C_AMBER, top_gap=2)
            rows = [[_short(f['fornitore'], 46), _eur(f['spesa']), f"{f['quantita']:,.0f}",                     _eur(f['prezzo_medio']),
                     _eur(f['prezzo_vendita']) if f.get('prezzo_vendita') else '-',
                     f"{f['margine_pct']:.1f}%" if f.get('margine_pct') is not None else '-',
                     f"{f['var_pct']:+.1f}%" if f['var_pct'] is not None else '-']
                    for f in data['fornitori'][:limit]]
            pdf.smart_table(['Fornitore', 'Spesa', 'Qta', 'Prz. acq.', 'Prz. vend.', 'Marg. %', 'Var. %'],
                            [68, 26, 20, 22, 22, 16, 16], rows,
                            aligns=['L', 'R', 'R', 'R', 'R', 'R', 'R'], col_colors={5: _margin_color})

            # prezzo medio di vendita degli stessi prodotti nel periodo (per confronto/margine)
            nomi_prod = [p['prodotto'] for p in data['prodotti'][:limit]]
            vend_map = {}
            if nomi_prod:
                vrows = await db.vendite.aggregate([
                    {"$match": {"prodotto_nome": {"$in": nomi_prod}, "data": {"$gte": per['start'], "$lte": per['end']},
                                "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
                    {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": {"$abs": "$quantita"}},
                                "fatt": {"$sum": {"$abs": "$totale"}},
                                "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}}}}
                ]).to_list(5000)
                vend_map = {v['_id']: v for v in vrows}

            pdf.section_title("Prodotti acquistati e prezzo di vendita nel periodo", C_BLUE)
            prows = []
            for p in data['prodotti'][:limit]:
                v = vend_map.get(p['prodotto'], {})
                pv = (v.get('fatt', 0) / v['qty']) if v.get('qty') else 0
                costo = v.get('costo', 0) or 0
                marg = ((v.get('fatt', 0) - costo) / costo * 100) if costo > 0 else None
                prows.append([
                    _short(p['prodotto'], 46), _eur(p['spesa']), f"{p['quantita']:,.0f}",
                    _eur(p['prezzo_medio']), _eur(pv) if pv else '-',
                    f"{v['qty']:,.0f}" if v.get('qty') else '-',
                    f"{marg:.1f}%" if marg is not None else '-',
                    f"{p['n_fornitori']}",
                ])
            pdf.smart_table(['Prodotto', 'Spesa acq.', 'Qta acq.', 'Prz. acq.', 'Prz. vendita', 'Qta vend.', 'Marg. %', 'Forn.'],
                            [64, 24, 19, 19, 22, 19, 13, 10], prows,
                            aligns=['L', 'R', 'R', 'R', 'R', 'R', 'R', 'R'], col_colors={6: _margin_color})
            pdf.note_text("Prz. acq. = spesa / quantita acquistata (media ponderata del periodo). Prz. vendita = "
                          "fatturato / quantita venduta dello stesso prodotto nel periodo. Margine calcolato sul "
                          "costo reale dei lotti venduti (FIFO).")

            if data['trend']:
                pdf.section_title("Spesa mensile", C_VIOLET)
                pdf.monthly_chart([(t['mese'], t['spesa']) for t in data['trend']])

            fname = f"analisi_acquisti_{per['start']}_{per['end']}.pdf"
        else:
            data = await analisi_vendite_prodotti(start_date, end_date, prodotto, 500)
            per = data['periodo']
            k = data['kpi']
            pdf = FlowPDF("ANALISI VENDITE PER PRODOTTO",
                          f"Periodo: {_dm(per['start'])} - {_dm(per['end'])}  |  Margini da lotti FIFO")
            pdf.add_page()
            pdf.kpi_row([
                ("FATTURATO", f"EUR {_eur(k['fatturato'])}", C_BLUE, f"prec. EUR {_eur(k['fatturato_prec'])}"),
                ("VARIAZIONE", f"{k['var_pct']:+.1f}%" if k['var_pct'] is not None else "-",
                 C_EMERALD if (k['var_pct'] or 0) >= 0 else C_RED,
                 f"vs {_dm(per['prev_start'])}-{_dm(per['prev_end'])}"),
                ("MARGINE MEDIO", f"{k['margine_medio_pct']:.1f}%" if k['margine_medio_pct'] is not None else "-",
                 C_EMERALD, "costo reale lotti"),
                ("PROFITTO STIMATO", f"EUR {_eur(k['profitto_stimato'])}", C_VIOLET,
                 f"{k['n_prodotti']} prodotti"),
            ])

            excl_v = await esclusi_filter()
            p0, p1 = periodi_anno_su_anno(per['start'], per['end'])
            a0 = await kpi_vendite(excl_v, *p0)
            a1 = await kpi_vendite(excl_v, *p1)
            tot_v = {"fatturato": k['fatturato'], "quantita": k['quantita'],
                     "costo": (k['fatturato'] - (k['profitto_stimato'] or 0)),
                     "margine": k['profitto_stimato'] or 0, "margine_pct": k['margine_medio_pct'],
                     "righe": sum(p['righe'] for p in data['prodotti']),
                     "n_prodotti": k['n_prodotti'],
                     "n_clienti": max((p['n_clienti'] for p in data['prodotti']), default=0)}
            blocco_sintesi(pdf, testo_sintesi_vendite(
                f"{_dm(per['start'])} - {_dm(per['end'])}", tot_v, a0, a1,
                concentrazione([p['fatturato'] for p in data['prodotti']])))
            blocco_confronto(pdf, righe_confronto_vendite(a0, a1))

            pdf.section_title("Vendite per prodotto (ordinate per margine %)", C_BLUE, top_gap=2)
            prodotti_ord = sorted(data['prodotti'],
                                  key=lambda p: -(p['margine_pct'] if p['margine_pct'] is not None else -9999))
            rows = [[_short(p['prodotto'], 44), f"{p['quantita']:,.0f}", _eur(p['prezzo_medio']),
                     _eur(p['costo_unitario']) if p['costo_unitario'] else '-',
                     _eur(p['fatturato']),
                     f"{p['margine_pct']:.1f}%" if p['margine_pct'] is not None else '-',
                     f"{p['var_fatturato_pct']:+.1f}%" if p['var_fatturato_pct'] is not None else '-']
                    for p in prodotti_ord[:limit]]
            pdf.smart_table(['Prodotto', 'Qta', 'Prz. vendita', 'Costo/u', 'Fatturato', 'Marg. %', 'Var. %'],
                            [66, 16, 24, 22, 28, 18, 16], rows,
                            aligns=['L', 'R', 'R', 'R', 'R', 'R', 'R'], col_colors={5: _margin_color})
            pdf.note_text("Il costo unitario e' il costo reale del lotto di acquisto consumato dalle vendite del "
                          "periodo (metodo FIFO). Margine = (fatturato - costo lotti) / costo lotti * 100.")
            fname = f"analisi_vendite_{per['start']}_{per['end']}.pdf"

        out = pdf.output()
        return Response(bytes(out), media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename={fname}"})
    except Exception as e:
        logger.error(f"Errore export analisi PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Errore generazione PDF: {str(e)}")


@router.get("/analisi/export/listino")
async def export_listino(
    cliente: Optional[str] = None, prodotto: Optional[str] = None,
    start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 120,
    ordina: str = "quantita"
):
    """Listino personale: per CLIENTE (i prodotti e i suoi prezzi) o, all'inverso,
    per PRODOTTO (i clienti e il prezzo che ognuno paga)."""
    try:
        if not cliente and not prodotto:
            raise HTTPException(status_code=400, detail="Indica un cliente oppure un prodotto")
        start, end, _, _ = await resolve_period(start_date, end_date)
        excl = await esclusi_filter()

        per_cliente = bool(cliente)
        match = {"data": {"$gte": start, "$lte": end}, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}, **excl}
        if per_cliente:
            match["cliente_nome"] = {"$regex": cliente, "$options": "i"}
            group_field = "$prodotto_nome"
            titolo = "LISTINO CLIENTE"
            intestazione = _short(cliente, 60)
            col_label = "Prodotto"
        else:
            match["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}
            group_field = "$cliente_nome"
            titolo = "LISTINO PER PRODOTTO"
            intestazione = _short(prodotto, 60)
            col_label = "Cliente"

        pipeline = [
            {"$match": match},
            {"$sort": {"data": 1}},
            {"$group": {
                "_id": group_field,
                "qty": {"$sum": {"$abs": "$quantita"}},
                "fatt": {"$sum": {"$abs": "$totale"}},
                "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                "ultimo_prezzo": {"$last": "$prezzo_unitario"},
                "ultima_data": {"$last": "$data"},
                "righe": {"$sum": 1},
            }},
        ]
        rows_agg = [r for r in await db.vendite.aggregate(pipeline).to_list(20000) if r['_id']]
        if not rows_agg:
            raise HTTPException(status_code=404, detail="Nessuna vendita trovata per i filtri indicati")

        tot_fatt = sum(r['fatt'] for r in rows_agg)
        tot_qty = sum(r['qty'] for r in rows_agg)
        tot_costo = sum(r['costo'] for r in rows_agg)
        margine = tot_fatt - tot_costo

        # ordinamento richiesto: quantita (default), margine % o prezzo applicato
        def key(r):
            if ordina == 'margine':
                return -((r['fatt'] - r['costo']) / r['costo'] * 100) if r['costo'] > 0 else 9999
            if ordina == 'prezzo':
                return -(r['fatt'] / r['qty']) if r['qty'] else 0
            return -r['qty']
        rows_agg.sort(key=key)

        ordine_label = {"margine": "margine %", "prezzo": "prezzo applicato"}.get(ordina, "quantita")
        pdf = FlowPDF(titolo, f"{intestazione}  |  Periodo: {_dm(start)} - {_dm(end)}")
        pdf.add_page()
        pdf.kpi_row([
            ("FATTURATO PERIODO", f"EUR {_eur(tot_fatt)}", C_BLUE, f"{len(rows_agg)} voci"),
            ("QUANTITA", f"{tot_qty:,.0f}", C_VIOLET, "pezzi"),
            ("COSTO LOTTI (FIFO)", f"EUR {_eur(tot_costo)}", C_SLATE, None),
            ("MARGINE", f"EUR {_eur(margine)}", C_EMERALD,
             f"{margine / tot_costo * 100:.1f}% sul costo" if tot_costo > 0 else None),
        ])

        # ── Sintesi narrativa + confronto ultimi due esercizi ──
        base_match = {**excl}
        if per_cliente:
            base_match["cliente_nome"] = {"$regex": cliente, "$options": "i"}
        else:
            base_match["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}
        p0, p1 = periodi_anno_su_anno(start, end)
        a0 = await kpi_vendite(base_match, *p0)
        a1 = await kpi_vendite(base_match, *p1)
        tot_l = {"fatturato": tot_fatt, "quantita": tot_qty, "costo": tot_costo, "margine": margine,
                 "margine_pct": (margine / tot_costo * 100) if tot_costo > 0 else None,
                 "righe": sum(r['righe'] for r in rows_agg),
                 "n_prodotti": len(rows_agg) if per_cliente else 1,
                 "n_clienti": 1 if per_cliente else len(rows_agg)}
        extra = ("Il listino e' ordinato per " + ordine_label + " e riporta, per ogni voce, il prezzo medio "
                 "ponderato applicato, l'ultimo prezzo praticato e il margine reale calcolato sul costo del "
                 "lotto venduto.")
        blocco_sintesi(pdf, testo_sintesi_vendite(f"{_dm(start)} - {_dm(end)}", tot_l, a0, a1,
                                                  concentrazione([r['fatt'] for r in rows_agg]), extra))
        blocco_confronto(pdf, righe_confronto_vendite(a0, a1))

        pdf.section_title(
            (f"Prodotti acquistati dal cliente (ordinati per {ordine_label})" if per_cliente
             else f"Clienti che acquistano il prodotto (ordinati per {ordine_label})"), C_BLUE, top_gap=2)
        table_rows = []
        for r in rows_agg[:limit]:
            marg = r['fatt'] - r['costo']
            table_rows.append([
                _short(r['_id'], 50), f"{r['qty']:,.0f}",
                _eur(r['fatt'] / r['qty']) if r['qty'] else '-',
                _eur(r.get('ultimo_prezzo', 0)),
                _eur(r['costo'] / r['qty']) if (r['costo'] and r['qty']) else '-',
                _eur(r['fatt']),
                f"{marg / r['costo'] * 100:.1f}%" if r['costo'] > 0 else '-',
                _dm(r.get('ultima_data')),
            ])
        pdf.smart_table(
            [col_label, 'Qta', 'Prz. medio', 'Ultimo prz.', 'Costo/u', 'Fatturato', 'Marg. %', 'Ultima vendita'],
            [66, 15, 20, 20, 19, 24, 14, 22], table_rows,
            aligns=['L', 'R', 'R', 'R', 'R', 'R', 'R', 'C'], col_colors={6: _margin_color})
        pdf.note_text("Prezzo medio = fatturato / quantita del periodo (media ponderata). Costo/u = costo reale del "
                      "lotto di acquisto consumato (FIFO). Margine = (fatturato - costo lotti) / costo lotti * 100.")

        out = pdf.output()
        base = (cliente or prodotto or 'listino').replace(' ', '_')[:30]
        return Response(bytes(out), media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename=listino_{base}_{start}_{end}.pdf"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore export listino: {e}")
        raise HTTPException(status_code=500, detail=f"Errore generazione PDF: {str(e)}")


@router.get("/analisi/provvigione")
async def get_provvigione():
    doc = await db.settings.find_one({"key": "provvigione"}, {"_id": 0})
    return {"percentuale": doc.get('percentuale', PROVVIGIONE_DEFAULT) if doc else PROVVIGIONE_DEFAULT,
            "base": "margine"}


@router.put("/analisi/provvigione")
async def set_provvigione(data: dict):
    pct = float(data.get('percentuale', PROVVIGIONE_DEFAULT))
    await db.settings.update_one({"key": "provvigione"},
                                 {"$set": {"key": "provvigione", "percentuale": pct,
                                           "aggiornato": datetime.now().isoformat()}}, upsert=True)
    return {"success": True, "percentuale": pct}
