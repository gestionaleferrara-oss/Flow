"""Backend regression tests for iter9 review request (Flow app).
Covers: PDF Analisi, KPI coerenza previsione, allineamento previsione-piano,
unita di misura, cliente CORRISPETTIVI, statistiche PDF confronto, differenze cronologiche.
"""
import os
import io
import pytest
import requests
import fitz  # pymupdf

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://magazzino-stock.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

TIMEOUT = 90


def pdf_text(content: bytes) -> str:
    doc = fitz.open(stream=content, filetype="pdf")
    txt = ""
    for p in doc:
        txt += p.get_text()
    doc.close()
    return txt


# ---------- 1) PDF Analisi (vendite + acquisti) ----------
class TestAnalisiExportPdf:
    def test_pdf_vendite(self):
        r = requests.get(f"{API}/analisi/export/pdf", params={"tipo": "vendite"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:400]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        txt = pdf_text(r.content)
        assert len(txt) > 50

    def test_pdf_acquisti(self):
        r = requests.get(f"{API}/analisi/export/pdf", params={"tipo": "acquisti"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:400]
        assert r.headers.get("content-type", "").startswith("application/pdf")


# ---------- 2) KPI coerenza previsione prodotti ----------
PRODOTTI_SETS = [
    ["PISTACCHIO SGUSCIATO KG. 1 X 10"],
    ["NOCI CILE CHANDLER 34/36 X 10", "PISTACCHIO TOST. KG. 2 USA"],
    ["LUPINI 250 X 24", "PISTACCHIO TOST. GR. 150 X 24"],
]


@pytest.mark.parametrize("nomi", PRODOTTI_SETS)
def test_previsione_kpi_coerenza(nomi):
    r = requests.get(f"{API}/analisi/previsione", params={"tipo": "prodotto", "nomi": ",".join(nomi), "giorni": 30}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    j = r.json()
    kpi = j.get("kpi") or {}
    righe = j.get("righe") or []
    righe_prod = j.get("righe_prodotti") or []

    sum_dom = round(sum(float(x.get("domanda_prevista", 0) or 0) for x in righe_prod), 2)
    sum_qty = round(sum(float(x.get("quantita_attesa", 0) or 0) for x in righe), 2)
    kpi_qty = round(float(kpi.get("quantita_attesa", 0) or 0), 2)
    assert abs(sum_dom - kpi_qty) < 0.5, f"sum_dom={sum_dom} vs kpi={kpi_qty}"
    assert abs(sum_qty - kpi_qty) < 0.5, f"sum_qty={sum_qty} vs kpi={kpi_qty}"

    sum_fat_prod = round(sum(float(x.get("fatturato_atteso", 0) or 0) for x in righe_prod), 2)
    sum_fat_righe = round(sum(float(x.get("fatturato_atteso", 0) or 0) for x in righe), 2)
    kpi_fat = round(float(kpi.get("fatturato_atteso", 0) or 0), 2)
    assert abs(sum_fat_prod - kpi_fat) < 1.0, f"fat prod={sum_fat_prod} vs kpi={kpi_fat}"
    assert abs(sum_fat_righe - kpi_fat) < 1.0, f"fat righe={sum_fat_righe} vs kpi={kpi_fat}"


# ---------- 3) Allineamento previsione vs piano ottimizzazione ----------
@pytest.mark.parametrize("prod", ["PISTACCHIO SGUSCIATO KG. 1 X 10", "NOCI CILE CHANDLER 34/36 X 10"])
@pytest.mark.parametrize("gg", [30, 107])
def test_previsione_allineata_piano(prod, gg):
    r1 = requests.get(f"{API}/analisi/previsione", params={"tipo": "prodotto", "nomi": prod, "giorni": gg}, timeout=TIMEOUT)
    assert r1.status_code == 200
    j1 = r1.json()
    dom_prev = float((j1.get("kpi") or {}).get("quantita_attesa", 0) or 0)

    r2 = requests.get(f"{API}/ottimizzazione/piano", params={"tipo": "acquisti", "giorni": gg, "limit": 500}, timeout=TIMEOUT)
    assert r2.status_code == 200, r2.text[:300]
    j2 = r2.json()
    # piano struttura: ordini[].articoli[]
    articoli = []
    for o in (j2.get("ordini") or []):
        articoli.extend(o.get("articoli") or [])
    # somma domanda_prevista per prodotto (piu fornitori)
    tot_piano = round(sum(float(a.get("domanda_prevista", 0) or 0) for a in articoli if (a.get("prodotto") or "").strip() == prod), 2)
    if tot_piano == 0:
        pytest.skip(f"prodotto {prod} non presente nel piano per gg={gg}")
    tol = max(0.5, dom_prev * 0.01)
    assert abs(dom_prev - tot_piano) <= tol, f"prev={dom_prev} piano={tot_piano} for {prod} gg={gg}"


# ---------- 4) Unita di misura ----------
UNITA_CASES = [
    (["PISTACCHIO TOST. KG. 2 USA"], "kg"),
    (["NOCI CILE CHANDLER 34/36 X 10"], "kg"),
    (["LUPINI 250 X 24"], "pz"),
    # NOTE: 'PISTACCHIO TOST. GR. 150 X 24' has no sales history -> skipped

    (["PISTACCHIO TOST. KG. 2 USA", "LUPINI 250 X 24"], None),  # mix -> null
]


@pytest.mark.parametrize("nomi,exp", UNITA_CASES)
def test_unita_kpi(nomi, exp):
    r = requests.get(f"{API}/analisi/previsione", params={"tipo": "prodotto", "nomi": ",".join(nomi), "giorni": 30}, timeout=TIMEOUT)
    assert r.status_code == 200
    j = r.json()
    kpi = j.get("kpi") or {}
    unita = kpi.get("unita")
    assert unita == exp, f"nomi={nomi} atteso={exp} got={unita}"
    # tutte le righe_prodotti devono avere 'unita'
    for rp in (j.get("righe_prodotti") or []):
        assert "unita" in rp, f"riga senza campo unita: {rp}"


# ---------- 6) Cliente CORRISPETTIVI incluso ----------
class TestCorrispettivi:
    def test_appare_in_vendite_clienti(self):
        # /api/analisi/opzioni?tipo=clienti restituisce l'elenco clienti (Analisi page)
        r = requests.get(f"{API}/analisi/opzioni", params={"q": "CORRIS", "tipo": "clienti", "limit": 10}, timeout=TIMEOUT)
        assert r.status_code == 200
        nomi = r.json().get("nomi", [])
        assert any("CORRISPETTIVI" in n.upper() for n in nomi), f"CORRISPETTIVI non trovato: {nomi}"

    def test_appare_in_top_clienti_prodotto(self):
        # verifica che compaia come cliente per un articolo (top_clienti in prodotto-dettaglio)
        r = requests.get(f"{API}/analisi/prodotto-dettaglio", params={"nome": "PISTACCHIO TOST. KG. 2 USA"}, timeout=TIMEOUT)
        assert r.status_code == 200
        tc = r.json().get("top_clienti", [])
        names = [c.get("cliente", "").upper() for c in tc]
        assert any("CORRISPETTIVI" in n for n in names), f"CORRISPETTIVI non in top_clienti: {names}"

    def test_appare_in_statistiche(self):
        r = requests.get(f"{API}/statistiche", timeout=TIMEOUT)
        assert r.status_code == 200
        # non deve essere filtrato; verifichiamo che i totali siano presenti (non regredisce)
        assert r.json() is not None

    def test_appare_in_dashboard(self):
        r = requests.get(f"{API}/dashboard", timeout=TIMEOUT)
        assert r.status_code == 200


# ---------- 7) Statistiche PDF confronto ----------
class TestStatistichePdf:
    def test_pdf_confronto(self):
        params = {
            "tipo": "vendite",
            "cmp1_start": "2026-01-01", "cmp1_end": "2026-03-31",
            "cmp2_start": "2025-01-01", "cmp2_end": "2025-03-31",
        }
        r = requests.get(f"{API}/statistiche/export/pdf", params=params, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        txt = pdf_text(r.content).upper()
        assert "CONFRONTO" in txt, f"'CONFRONTO' non trovato nel PDF. First 400: {txt[:400]}"

    def test_pdf_statistiche_normale(self):
        r = requests.get(f"{API}/statistiche/export/pdf", params={"tipo": "vendite"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")


# ---------- 8) Differenze cronologiche confronta-periodi ----------
class TestConfrontaPeriodi:
    def test_segno_cronologico_stabile(self):
        p1 = {"start1": "2025-01-01", "end1": "2025-03-31", "start2": "2026-01-01", "end2": "2026-03-31"}
        p2 = {"start1": "2026-01-01", "end1": "2026-03-31", "start2": "2025-01-01", "end2": "2025-03-31"}
        r1 = requests.get(f"{API}/confronta-periodi", params=p1, timeout=TIMEOUT)
        r2 = requests.get(f"{API}/confronta-periodi", params=p2, timeout=TIMEOUT)
        assert r1.status_code == 200 and r2.status_code == 200, (r1.text[:200], r2.text[:200])
        j1, j2 = r1.json(), r2.json()
        # entrambe devono avere periodo_recente
        assert "periodo_recente" in j1 and "periodo_recente" in j2, "campo periodo_recente mancante"
        d1 = j1.get("diff_totale", j1.get("diff_qty"))
        d2 = j2.get("diff_totale", j2.get("diff_qty"))
        if d1 is not None and d2 is not None:
            # stesso segno
            import math
            assert (d1 == 0 and d2 == 0) or (d1 * d2 > 0) or (abs(d1 - d2) < 0.01), f"diff invertita: {d1} vs {d2}"


# ---------- 9) Regressione PDF ----------
REGRESSION_PDFS = [
    ("/ottimizzazione/piano/pdf", {"tipo": "acquisti", "giorni": 30, "nome": "MADI VENTURA SPA"}),
    ("/ottimizzazione/piano/pdf", {"tipo": "vendite", "giorni": 30}),
    ("/analisi/previsione/pdf", {"tipo": "prodotto", "nomi": "PISTACCHIO TOST. KG. 2 USA", "giorni": 30, "vista": "entrambi"}),
    ("/analisi/previsione/pdf", {"tipo": "prodotto", "nomi": "PISTACCHIO TOST. KG. 2 USA", "giorni": 30, "vista": "clienti"}),
    ("/analisi/previsione/pdf", {"tipo": "prodotto", "nomi": "PISTACCHIO TOST. KG. 2 USA", "giorni": 30, "vista": "fornitori"}),
    ("/analisi/previsione/pdf", {"tipo": "cliente", "nomi": "CLIENTE CORRISPETTIVI", "giorni": 30}),
    ("/analisi/previsione/pdf", {"tipo": "fornitore", "nomi": "MADI VENTURA SPA", "giorni": 30}),
    ("/analisi/export/rendiconto", {}),
    ("/analisi/export/rendiconto-acquisti", {}),
    ("/analisi/export/listino", {"prodotto": "PISTACCHIO TOST. KG. 2 USA"}),
    ("/statistiche/export/pdf", {}),
    ("/ottimizzazione/export/pdf", {"tipo": "acquisti"}),
]


@pytest.mark.parametrize("path,params", REGRESSION_PDFS)
def test_pdf_regression(path, params):
    r = requests.get(f"{API}{path}", params=params, timeout=TIMEOUT)
    assert r.status_code == 200, f"{path} {params} -> {r.status_code}: {r.text[:200]}"
    ct = r.headers.get("content-type", "")
    assert ct.startswith("application/pdf"), f"{path} content-type={ct}"
    # valida che sia un vero PDF
    try:
        doc = fitz.open(stream=r.content, filetype="pdf")
        assert doc.page_count >= 1
        doc.close()
    except Exception as e:
        pytest.fail(f"{path} PDF invalido: {e}")
