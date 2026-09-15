"""Backend tests for iteration 9: piano d'azione + previsione multi-selezione + PDF senza confronto storico."""
import os
import re
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://magazzino-stock.preview.emergentagent.com").rstrip("/")
# For long PDF endpoints we can also use localhost if needed, but public URL should be fine with timeout
API = f"{BASE}/api"
TO = 90  # seconds - PDF generation with LLM insights can be slow


# ─────────── /ottimizzazione/piano ───────────

@pytest.mark.parametrize("tipo,giorni", [("acquisti", 30), ("vendite", 30), ("acquisti", 45), ("acquisti", 7)])
def test_piano_struttura(tipo, giorni):
    r = requests.get(f"{API}/ottimizzazione/piano", params={"tipo": tipo, "giorni": giorni}, timeout=TO)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tipo"] == tipo
    per = d["periodo"]
    assert per["giorni"] == giorni
    # Verify finestra: futuro_start = oggi, futuro_end = oggi+giorni-1 (in giorni); storico = -365
    from datetime import datetime, timedelta
    fs = datetime.strptime(per["futuro_start"], "%Y-%m-%d")
    fe = datetime.strptime(per["futuro_end"], "%Y-%m-%d")
    assert (fe - fs).days == giorni - 1
    ls = datetime.strptime(per["storico_start"], "%Y-%m-%d")
    assert (fs - ls).days == 365
    assert "totali" in d
    assert "ordini" in d and isinstance(d["ordini"], list)
    assert "suggerimenti" in d
    assert "top_prodotti" in d
    # No 'risparmio' anywhere in the payload
    assert "risparmio" not in str(d).lower() or "risparmio_potenziale" not in str(d)


def test_piano_no_risparmio_key():
    for tipo in ("acquisti", "vendite"):
        r = requests.get(f"{API}/ottimizzazione/piano", params={"tipo": tipo, "giorni": 30}, timeout=TO)
        assert r.status_code == 200
        # deep scan for a bare 'risparmio' key
        def scan(x):
            if isinstance(x, dict):
                assert "risparmio" not in x, f"trovato campo 'risparmio' in {list(x.keys())}"
                for v in x.values(): scan(v)
            elif isinstance(x, list):
                for v in x: scan(v)
        scan(r.json())


# ─────────── /ottimizzazione/piano/pdf ───────────

def _pdf_ok(r):
    assert r.status_code == 200, r.text[:400]
    assert r.headers.get("content-type", "").startswith("application/pdf"), r.headers
    assert len(r.content) > 10_000, f"pdf troppo piccolo: {len(r.content)}"
    assert r.content[:4] == b"%PDF"
    return r.content


@pytest.mark.parametrize("tipo", ["acquisti", "vendite"])
def test_piano_pdf(tipo):
    r = requests.get(f"{API}/ottimizzazione/piano/pdf", params={"tipo": tipo, "giorni": 30}, timeout=TO)
    body = _pdf_ok(r)
    # PDF should NOT contain "Come leggere il piano"
    assert b"Come leggere il piano" not in body


def test_piano_pdf_scheda_fornitore():
    # get real fornitore name
    r = requests.get(f"{API}/ottimizzazione/piano", params={"tipo": "acquisti", "giorni": 30}, timeout=TO)
    ordini = r.json()["ordini"]
    assert ordini, "no ordini available"
    nome = ordini[0]["fornitore"]
    r2 = requests.get(f"{API}/ottimizzazione/piano/pdf",
                      params={"tipo": "acquisti", "giorni": 30, "nome": nome}, timeout=TO)
    _pdf_ok(r2)


def test_piano_pdf_scheda_cliente():
    r = requests.get(f"{API}/ottimizzazione/piano", params={"tipo": "vendite", "giorni": 30}, timeout=TO)
    ordini = r.json()["ordini"]
    assert ordini
    nome = ordini[0]["cliente"]
    r2 = requests.get(f"{API}/ottimizzazione/piano/pdf",
                      params={"tipo": "vendite", "giorni": 30, "nome": nome}, timeout=TO)
    _pdf_ok(r2)


def test_piano_pdf_scheda_404():
    r = requests.get(f"{API}/ottimizzazione/piano/pdf",
                     params={"tipo": "acquisti", "giorni": 30, "nome": "NON_ESISTE_XYZ_123"}, timeout=TO)
    assert r.status_code == 404


# ─────────── /analisi/previsione (multi) ───────────

def test_previsione_prodotto_multi():
    # find two prodotti with data
    opt = requests.get(f"{API}/analisi/opzioni", params={"tipo": "prodotti", "q": "PISTACCHIO"}, timeout=30).json()
    nomi = opt["nomi"][:2] if opt["nomi"] else []
    if len(nomi) < 1:
        pytest.skip("no prodotto disponibile")
    # nomi repeated param
    params = [("tipo", "prodotto"), ("giorni", "30")]
    for n in nomi: params.append(("nomi", n))
    r = requests.get(f"{API}/analisi/previsione", params=params, timeout=TO)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tipo"] == "prodotto"
    assert "kpi" in d and "righe" in d and "righe_prodotti" in d and "righe_fornitori" in d
    for f in d["righe_fornitori"]:
        assert f.get("ruolo") in ("primario", "secondario", "occasionale"), f
        assert "scarto_dal_migliore_pct" not in f
        assert "migliore_su" not in f


def test_previsione_cliente():
    r = requests.get(f"{API}/analisi/previsione",
                     params=[("tipo", "cliente"), ("giorni", "30"),
                             ("nomi", "NUOVA ORTOFRUTTICOLA MODENESE S.R.L.")],
                     timeout=TO)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tipo"] == "cliente"
    assert "kpi" in d and "righe" in d


def test_previsione_fornitore():
    r = requests.get(f"{API}/analisi/previsione",
                     params=[("tipo", "fornitore"), ("giorni", "30"),
                             ("nomi", "MADI VENTURA SPA")],
                     timeout=TO)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tipo"] == "fornitore"
    assert "kpi" in d and "righe" in d


# ─────────── /analisi/previsione/pdf ───────────

def test_previsione_pdf_prodotto_viste():
    opt = requests.get(f"{API}/analisi/opzioni", params={"tipo": "prodotti", "q": "PISTACCHIO"}, timeout=30).json()
    nomi = opt["nomi"][:1]
    if not nomi:
        pytest.skip("no prodotto")
    for vista in ("entrambi", "clienti", "fornitori"):
        params = [("tipo", "prodotto"), ("giorni", "30"), ("vista", vista)] + [("nomi", n) for n in nomi]
        r = requests.get(f"{API}/analisi/previsione/pdf", params=params, timeout=TO)
        _pdf_ok(r)


def test_previsione_pdf_cliente():
    r = requests.get(f"{API}/analisi/previsione/pdf",
                     params=[("tipo", "cliente"), ("giorni", "30"),
                             ("nomi", "NUOVA ORTOFRUTTICOLA MODENESE S.R.L.")], timeout=TO)
    _pdf_ok(r)


def test_previsione_pdf_fornitore():
    r = requests.get(f"{API}/analisi/previsione/pdf",
                     params=[("tipo", "fornitore"), ("giorni", "30"),
                             ("nomi", "MADI VENTURA SPA")], timeout=TO)
    _pdf_ok(r)


# ─────────── Export PDF esistenti ───────────

def test_export_pdf_vendite():
    r = requests.get(f"{API}/analisi/export/pdf",
                     params={"tipo": "vendite", "start_date": "2026-06-01", "end_date": "2026-08-31"},
                     timeout=TO)
    body = _pdf_ok(r)
    # Deve non contenere confronti anno precedente
    text_marks = [b"Var. %", b"VARIAZIONE", b"confronto", b"CONFRONTO", b"Confronto", b"Anno precedente"]
    found = [m for m in text_marks if m in body]
    assert not found, f"trovati marcatori confronto: {found}"


def test_export_pdf_acquisti():
    r = requests.get(f"{API}/analisi/export/pdf",
                     params={"tipo": "acquisti", "start_date": "2026-06-01", "end_date": "2026-08-31"},
                     timeout=TO)
    _pdf_ok(r)


def test_export_rendiconto():
    r = requests.get(f"{API}/analisi/export/rendiconto", timeout=TO)
    _pdf_ok(r)


def test_export_listino():
    # need a valid prodotto
    opt = requests.get(f"{API}/analisi/opzioni", params={"tipo": "prodotti", "q": "PISTACCHIO"}, timeout=30).json()
    nomi = opt["nomi"][:1]
    if not nomi:
        pytest.skip("no prodotto")
    r = requests.get(f"{API}/analisi/export/listino", params={"prodotto": nomi[0]}, timeout=TO)
    _pdf_ok(r)


def test_export_statistiche_pdf():
    r = requests.get(f"{API}/statistiche/export/pdf", timeout=TO)
    _pdf_ok(r)


def test_export_ottimizzazione_pdf():
    r = requests.get(f"{API}/ottimizzazione/export/pdf", params={"tipo": "acquisti"}, timeout=TO)
    _pdf_ok(r)
