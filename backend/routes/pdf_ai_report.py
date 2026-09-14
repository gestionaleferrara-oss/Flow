"""PDF del report scritto dall'AI in chat: KPI, grafici, tabelle e note finali."""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from database import db
from routes.pdf_helper import (C_AMBER, C_BLUE, C_EMERALD, C_SLATE, C_VIOLET,
                               FlowPDF, clean_text, it_num)

router = APIRouter()

COLORI = [C_BLUE, C_EMERALD, C_VIOLET, C_AMBER, C_SLATE]


async def salva_report(titolo: str, sottotitolo: str, testo: str,
                       kpi: Optional[List[Dict]] = None,
                       tabelle: Optional[List[Dict]] = None,
                       note: str = "",
                       grafici: Optional[List[Dict]] = None) -> str:
    rid = uuid.uuid4().hex[:12]
    await db.ai_report_pdf.insert_one({
        "report_id": rid, "titolo": titolo, "sottotitolo": sottotitolo, "testo": testo,
        "kpi": kpi or [], "tabelle": tabelle or [], "grafici": grafici or [], "note": note,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return rid


@router.get("/ai/reports")
async def lista_report(limit: int = 50):
    docs = await db.ai_report_pdf.find(
        {}, {"_id": 0, "report_id": 1, "titolo": 1, "sottotitolo": 1, "created_at": 1, "tabelle": 1}
    ).sort([("created_at", -1)]).to_list(min(limit, 200))
    return {"reports": [{
        "report_id": d['report_id'], "titolo": d.get('titolo') or 'Report',
        "sottotitolo": d.get('sottotitolo') or '', "created_at": d.get('created_at'),
        "tabelle": len(d.get('tabelle') or []),
        "url": f"/api/ai/report/{d['report_id']}.pdf",
    } for d in docs]}


@router.delete("/ai/reports/{report_id}")
async def elimina_report(report_id: str):
    res = await db.ai_report_pdf.delete_one({"report_id": report_id})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Report non trovato")
    return {"success": True}


def _numeri(vals) -> List[float]:
    out = []
    for v in (vals or []):
        try:
            out.append(float(str(v).replace('.', '').replace(',', '.').replace('€', '').strip()))
        except (TypeError, ValueError):
            out.append(0.0)
    return out


def _grafico_come_tabella(pdf, g: Dict, idx: int):
    """I grafici non sono piu' disegnati: i dati vengono resi come tabella."""
    etichette = [clean_text(str(e)) for e in (g.get('etichette') or [])]
    valori = _numeri(g.get('valori'))
    valori2 = _numeri(g.get('valori2'))
    if not etichette or not valori:
        return
    colore = COLORI[idx % len(COLORI)]
    pdf.section_title(g.get('titolo') or 'Dettaglio', colore)
    unita = clean_text(g.get('unita') or '').strip()
    simbolo = '\u20ac' if unita.upper() in ('EUR', 'EURO', '\u20ac') else ''

    def fmt(v):
        return f"{simbolo} {it_num(v)}".strip() if simbolo else it_num(v)

    if valori2:
        cols = ['Voce', g.get('legenda') or 'Periodo', g.get('legenda2') or 'Anno precedente', 'Var. %']
        righe = []
        for i, e in enumerate(etichette):
            a = valori[i] if i < len(valori) else 0
            b = valori2[i] if i < len(valori2) else 0
            var = f"{(a - b) / b * 100:+.1f}%".replace('.', ',') if b else '-'
            righe.append([e, fmt(a), fmt(b), var])
        pdf.smart_table(cols, [76, 40, 40, 24], righe, aligns=['L', 'R', 'R', 'R'])
    else:
        righe = [[e, fmt(valori[i] if i < len(valori) else 0)] for i, e in enumerate(etichette)]
        pdf.smart_table(['Voce', g.get('legenda') or 'Valore'], [120, 60], righe, aligns=['L', 'R'])

    if g.get('nota'):
        pdf.note_text(g['nota'])


@router.get("/ai/report/{report_id}.pdf")
async def ai_report_pdf(report_id: str):
    doc = await db.ai_report_pdf.find_one({"report_id": report_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Report non trovato")

    pdf = FlowPDF(report_title=doc['titolo'][:70] or "Report AI",
                  subtitle=doc.get('sottotitolo') or "")
    pdf.add_page()

    kpi = doc.get('kpi') or []
    if kpi:
        pdf.kpi_row([(clean_text(k.get('label', ''))[:30], clean_text(k.get('valore', '')),
                      COLORI[i % 4], clean_text(k.get('nota')) if k.get('nota') else None)
                     for i, k in enumerate(kpi[:4])])

    for i, g in enumerate(doc.get('grafici') or []):
        _grafico_come_tabella(pdf, g, i)

    for t in (doc.get('tabelle') or []):
        colonne = [clean_text(c) for c in (t.get('colonne') or [])]
        righe = [[('' if c is None else clean_text(c)) for c in r] for r in (t.get('righe') or [])]
        if not colonne or not righe:
            continue
        pdf.section_title(t.get('titolo') or "Dettaglio")
        prima = 190 - 22 * (len(colonne) - 1)
        prima = max(prima, 45)
        resto = (190 - prima) / max(len(colonne) - 1, 1)
        widths = [prima] + [resto] * (len(colonne) - 1)
        aligns = ['L'] + ['R'] * (len(colonne) - 1)
        pdf.smart_table(colonne, widths, righe, aligns)
        if t.get('nota'):
            pdf.note_text(t['nota'])

    if doc.get('testo'):
        pdf.section_title("Lettura dei dati e raccomandazioni", C_SLATE)
        pdf.ai_text_block(doc['testo'])

    if doc.get('note'):
        pdf.note_text(doc['note'])

    out = pdf.output(dest='S')
    nome = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in doc['titolo'])[:60] or "report_ai"
    return Response(bytes(out), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nome}.pdf"'})
