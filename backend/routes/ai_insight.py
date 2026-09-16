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
    "Sei il responsabile acquisti e vendite di un'azienda italiana di distribuzione di frutta secca "
    "e ortofrutta. Commenti i dati del foglio che ti viene passato, per il titolare.\n"
    "REGOLE FERREE:\n"
    "- Da 4 a 6 punti, ognuno su una riga che inizia con '- ', massimo 28 parole.\n"
    "- Parla SOLO di: quantita' (pezzi/colli), rotazione e copertura di magazzino, margine e prezzi, "
    "valore degli ordini, frequenza di riordino, concentrazione su pochi articoli o clienti.\n"
    "- Usa esclusivamente i numeri presenti nei dati forniti, citandoli (pezzi, euro, percentuali). "
    "Se un dato non c'e', non parlarne.\n"
    "- Ogni punto = un'osservazione concreta sul foglio + l'azione operativa conseguente "
    "(quanto ordinare, quale prezzo rivedere, cosa non riordinare).\n"
    "- VIETATO: previsioni di mercato, stagionalita' generica, consigli commerciali generici, "
    "marketing, considerazioni su fornitori o clienti non presenti nei dati, ipotesi non verificabili, "
    "preamboli, titoli, grassetti, riferimenti a se stessi o all'intelligenza artificiale.\n"
    "- Tono asciutto e professionale, niente aggettivi enfatici."
)


async def considerazioni(contesto: str, chiave: str = "", extra: str = "") -> str:
    """Testo di considerazioni sui dati passati. Stringa vuota se non disponibile."""
    if not contesto.strip():
        return ""
    h = hashlib.sha256((chiave + extra + contesto).encode()).hexdigest()[:24]
    cached = await db.report_insight.find_one({"_id": h}, {"_id": 0, "testo": 1})
    if cached:
        return cached['testo']

    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        return ""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        system = ISTRUZIONI + ("\nREGOLE AGGIUNTIVE PRIORITARIE:\n" + extra if extra else "")
        chat = (LlmChat(api_key=api_key, session_id=f"insight-{h}", system_message=system)
                .with_model(PROVIDER, MODEL))
        testo = await chat.send_message(UserMessage(text=contesto))
        testo = (testo or "").strip()
        if not testo:
            return ""
        await db.report_insight.replace_one(
            {"_id": h},
            {"_id": h, "testo": testo, "created_at": datetime.now(timezone.utc).isoformat()},
            upsert=True)
        return testo
    except Exception as e:
        logger.warning(f"Considerazioni non disponibili: {e}")
        return ""


async def blocco_considerazioni_ai(pdf, contesto: str, chiave: str = "",
                                   titolo: str = "Considerazioni", extra: str = ""):
    """Aggiunge al PDF la sezione con le considerazioni, se disponibili."""
    from routes.pdf_helper import C_NAVY

    testo = await considerazioni(contesto, chiave, extra)
    if not testo:
        return
    pdf.ensure_space(34)
    pdf.section_title(titolo, C_NAVY)
    pdf.ai_text_block(testo)
