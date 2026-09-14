"""PDF del report scritto dall'AI in chat: testo + KPI + tabelle passate dall'assistente."""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from database import db
from routes.pdf_helper import FlowPDF, clean_text, C_BLUE, C_EMERALD, C_VIOLET, C_AMBER

router = APIRouter()

COLORI = [C_BLUE, C_EMERALD, C_VIOLET, C_AMBER]


async def salva_report(titolo: str, sottotitolo: str, testo: str,
                       kpi: Optional[List[Dict]] = None,
                       tabelle: Optional[List[Dict]] = None,
                       note: str = "") -> str:
    rid = uuid.uuid4().hex[:12]
    await db.ai_report_pdf.insert_one({
        "report_id": rid, "titolo": titolo, "sottotitolo": sottotitolo, "testo": testo,
        "kpi": kpi or [], "tabelle": tabelle or [], "note": note,
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

    if doc.get('testo'):
        pdf.section_title("Analisi")
        pdf.ai_text_block(doc['testo'])

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

    if doc.get('note'):
        pdf.note_text(doc['note'])

    out = pdf.output(dest='S')
    nome = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in doc['titolo'])[:60] or "report_ai"
    return Response(bytes(out), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nome}.pdf"'})
