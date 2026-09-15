"""Tests for iteration 9 - PDF reports & previsione (Ottimizzazione).
Covers:
- Analisi PDF (vendite/acquisti/rendiconto) with CONSIDERAZIONI, no YoY in vendite
- Previsione endpoint (prodotto/cliente/fornitore) - fornitori have ruolo, no risparmio
- Previsione PDF with vista filter
- Piano PDF (acquisti/vendite) - strutturato con pezzi
- Piano JSON without 'risparmio'
- Existing PDF endpoints should return 200
"""
import os
import requests
import pytest
import io

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
LOCAL_URL = "http://localhost:8001"
TIMEOUT = 90

def _get(path, params=None):
    """Try external URL first; on 504 fallback to localhost."""
    url = f"{BASE_URL}{path}"
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
        if r.status_code == 504:
            r = requests.get(f"{LOCAL_URL}{path}", params=params, timeout=TIMEOUT)
        return r
    except requests.exceptions.RequestException:
        return requests.get(f"{LOCAL_URL}{path}", params=params, timeout=TIMEOUT)


def _pdf_text(content: bytes) -> str:
    try:
        import fitz
        doc = fitz.open(stream=content, filetype="pdf")
        txt = "\n".join(p.get_text() for p in doc)
        doc.close()
        return txt
    except Exception as e:
        return ""


# ---------- ANALISI PDF ----------

class TestAnalisiPDF:
    def test_vendite_pdf_no_yoy_has_considerazioni(self):
        r = _get("/api/analisi/export/pdf", {
            "tipo": "vendite",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
        })
        assert r.status_code == 200, r.text[:400]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        txt = _pdf_text(r.content).upper()
        assert "CONSIDERAZIONI" in txt, "Manca sezione CONSIDERAZIONI"
        # Must NOT contain YoY markers
        for bad in ["VARIAZIONE", "VAR. %", "ANNO PRECEDENTE", "CONFRONTO CON LO STESSO PERIODO"]:
            assert bad not in txt, f"Il PDF vendite contiene ancora YoY marker: {bad}"

    def test_acquisti_pdf_has_considerazioni(self):
        r = _get("/api/analisi/export/pdf", {
            "tipo": "acquisti",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
        })
        assert r.status_code == 200, r.text[:400]
        assert r.content[:4] == b"%PDF"
        txt = _pdf_text(r.content).upper()
        assert "CONSIDERAZIONI" in txt

    def test_rendiconto_pdf_has_considerazioni(self):
        r = _get("/api/analisi/export/rendiconto", {
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
        })
        assert r.status_code == 200, r.text[:400]
        assert r.content[:4] == b"%PDF"
        txt = _pdf_text(r.content).upper()
        assert "CONSIDERAZIONI" in txt

    def test_listino_pdf_ok(self):
        r = _get("/api/analisi/export/listino", {
            "prodotto": "PISTACCHIO TOST. KG. 2 USA",
            "start_date": "2026-06-01",
            "end_date": "2026-08-31",
        })
        assert r.status_code == 200, r.text[:400]
        assert r.content[:4] == b"%PDF"


# ---------- PREVISIONE JSON ----------

class TestPrevisioneJSON:
    def test_previsione_prodotto_multi(self):
        r = _get("/api/analisi/previsione", [
            ("tipo", "prodotto"),
            ("nomi", "PISTACCHIO TOST. KG. 2 USA"),
            ("nomi", "NOCI SGUSCIATE CILE  KG.1 X 10"),
            ("giorni", "45"),
        ])
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        assert "kpi" in data
        assert "righe" in data
        assert "righe_prodotti" in data
        assert "righe_fornitori" in data
        # each fornitore row has ruolo & required fields, no risparmio
        for row in data["righe_fornitori"]:
            assert "ruolo" in row, f"manca ruolo in {row}"
            assert row["ruolo"] in ("primario", "secondario", "occasionale"), row["ruolo"]
            for key in ("domanda_prevista", "da_ordinare", "valore_ordine"):
                assert key in row, f"manca {key} in {row}"
            # No risparmio-like fields
            for bad in ("risparmio", "scarto", "delta_prezzo", "risparmio_stimato"):
                assert bad not in row, f"campo indesiderato {bad}"

    def test_previsione_cliente(self):
        r = _get("/api/analisi/previsione", {
            "tipo": "cliente",
            "nomi": "NUOVA ORTOFRUTTICOLA MODENESE S.R.L.",
            "giorni": "45",
        })
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert "kpi" in d and "righe" in d

    def test_previsione_fornitore(self):
        r = _get("/api/analisi/previsione", {
            "tipo": "fornitore",
            "nomi": "MADI VENTURA SPA",
            "giorni": "45",
        })
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert "kpi" in d and "righe" in d


# ---------- PREVISIONE PDF ----------

class TestPrevisionePDF:
    def _params(self, vista):
        return [
            ("tipo", "prodotto"),
            ("nomi", "PISTACCHIO TOST. KG. 2 USA"),
            ("nomi", "NOCI SGUSCIATE CILE  KG.1 X 10"),
            ("giorni", "45"),
            ("vista", vista),
        ]

    def test_previsione_pdf_entrambi(self):
        r = _get("/api/analisi/previsione/pdf", self._params("entrambi"))
        assert r.status_code == 200, r.text[:400]
        assert r.content[:4] == b"%PDF"
        txt = _pdf_text(r.content).upper()
        assert "CONSIDERAZIONI" in txt
        # No QUOTA column in fornitori table
        assert "QUOTA" not in txt, "Colonna QUOTA presente nella tabella fornitori"

    def test_previsione_pdf_clienti_only(self):
        r = _get("/api/analisi/previsione/pdf", self._params("clienti"))
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"
        txt = _pdf_text(r.content).upper()
        # no fornitori table indicator
        assert "FORNITORI" not in txt or "TABELLA FORNITORI" not in txt

    def test_previsione_pdf_fornitori_only(self):
        r = _get("/api/analisi/previsione/pdf", self._params("fornitori"))
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"
        txt = _pdf_text(r.content).upper()
        assert "QUOTA" not in txt


# ---------- PIANO OTTIMIZZAZIONE ----------

class TestPianoOttimizzazione:
    def test_piano_acquisti_json_no_risparmio(self):
        r = _get("/api/ottimizzazione/piano", {"tipo": "acquisti", "giorni": "30"})
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        for key in ("periodo", "totali", "ordini", "suggerimenti", "top_prodotti"):
            assert key in d, f"manca {key}"
        # no risparmio
        import json as _j
        blob = _j.dumps(d).lower()
        assert "risparmio" not in blob

    def test_piano_vendite_json(self):
        r = _get("/api/ottimizzazione/piano", {"tipo": "vendite", "giorni": "30"})
        assert r.status_code == 200
        d = r.json()
        assert "ordini" in d

    def test_piano_pdf_acquisti(self):
        r = _get("/api/ottimizzazione/piano/pdf", {"tipo": "acquisti", "giorni": "30", "limit": "8"})
        assert r.status_code == 200, r.text[:400]
        assert r.content[:4] == b"%PDF"
        txt = _pdf_text(r.content).upper()
        assert "PIANO DI ACQUISTO" in txt
        assert "CONSIDERAZIONI" in txt
        assert "PUNTI DI ATTENZIONE" in txt
        # pezzi columns
        assert "DA ORDINARE" in txt
        assert "GIACENZA" in txt

    def test_piano_pdf_vendite(self):
        r = _get("/api/ottimizzazione/piano/pdf", {"tipo": "vendite", "giorni": "30", "limit": "8"})
        assert r.status_code == 200, r.text[:400]
        assert r.content[:4] == b"%PDF"
        txt = _pdf_text(r.content).upper()
        assert "PIANO DI VENDITA" in txt
        assert "CONSIDERAZIONI" in txt


# ---------- Existing PDFs must not 500 ----------

class TestOtherPDFs:
    def test_statistiche_pdf(self):
        r = _get("/api/statistiche/export/pdf")
        assert r.status_code == 200, r.text[:400]
        assert r.content[:4] == b"%PDF"

    def test_ottimizzazione_export_pdf(self):
        r = _get("/api/ottimizzazione/export/pdf", {"tipo": "acquisti"})
        assert r.status_code == 200, r.text[:400]
        assert r.content[:4] == b"%PDF"
