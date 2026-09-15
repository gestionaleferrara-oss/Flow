"""Considerazioni narrative generate sui dati del report, con cache su Mongo."""
import hashlib
import logging
import os
from datetime import datetime, timezone

from database import db

logger = logging.getLogger(__name__)

PROVIDER = "anthropic"
MODEL = "claude-sonnet-4-6"

ISTRUZIONI = (
    "Sei l'analista interno di un'azienda italiana di distribuzione ortofrutta e frutta secca. "
    "Ricevi i dati di un report e scrivi le considerazioni finali per il titolare.\n"
    "REGOLE:\n"
    "- Italiano, tono professionale e diretto, prima persona plurale o impersonale.\n"
    "- Da 4 a 6 punti, ognuno su una riga che inizia con '- '.\n"
    "- Ogni punto deve citare numeri concreti presi dai dati e dire cosa fare.\n"
    "- Vietato: preamboli, titoli, formule tipo 'in conclusione', riferimenti all'intelligenza "
    "artificiale, all'assistente o al fatto che stai analizzando dei dati.\n"
    "- Niente markdown oltre al trattino iniziale, niente grassetti.\n"
    "- Massimo 30 parole per punto."
)


async def considerazioni(contesto: str, chiave: str = "") -> str:
    """Testo di considerazioni sui dati passati. Stringa vuota se non disponibile."""
    if not contesto.strip():
        return ""
    h = hashlib.sha256((chiave + contesto).encode()).hexdigest()[:24]
    cached = await db.report_insight.find_one({"_id": h}, {"_id": 0, "testo": 1})
    if cached:
        return cached['testo']

    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        return ""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = (LlmChat(api_key=api_key, session_id=f"insight-{h}", system_message=ISTRUZIONI)
                .with_model(PROVIDER, MODEL))
        testo = await chat.send_message(UserMessage(text=contesto))
        testo = (testo or "").strip()
        if not testo:
            return ""
        await db.report_insight.insert_one({
            "_id": h, "testo": testo, "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return testo
    except Exception as e:
        logger.warning(f"Considerazioni non disponibili: {e}")
        return ""


async def blocco_considerazioni_ai(pdf, contesto: str, chiave: str = "",
                                   titolo: str = "Considerazioni"):
    """Aggiunge al PDF la sezione con le considerazioni, se disponibili."""
    from routes.pdf_helper import C_NAVY

    testo = await considerazioni(contesto, chiave)
    if not testo:
        return
    pdf.ensure_space(34)
    pdf.section_title(titolo, C_NAVY)
    pdf.ai_text_block(testo)
