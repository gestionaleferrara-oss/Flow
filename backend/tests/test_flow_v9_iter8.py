"""Iteration 8 - Focused tests for previsione alignment, unita', PDFs and confronto."""
import os
import io
import re
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

PRODUCTS = [
    "NOCI CILE CHANDLER 34/36 X 10",
    "PISTACCHIO SGUSCIATO KG. 1 X 10",
    "PISTACCHIO GRANELLA KG.1 X 10",
    "PISTACCHIO TOST. KG. 2 USA",
    "LUPINI 250 X 24",
]


def _get(path, **params):
    r = requests.get(f"{BASE}{path}", params=params, timeout=90)
    return r


# ---------- Alignment previsione vs ottimizzazione ----------
def _piano_map(giorni):
    r = _get("/api/ottimizzazione/piano", tipo="acquisti", giorni=giorni, limit=100)
    assert r.status_code == 200, r.text
    out = {}
    for o in r.json().get("ordini", []):
        for a in o.get("articoli", []):
            out[a.get("prodotto")] = a.get("domanda_prevista")
    return out


@pytest.mark.parametrize("giorni", [30, 107])
@pytest.mark.parametrize("prod", PRODUCTS)
def test_alignment_previsione_vs_piano(giorni, prod):
    piano = _piano_map(giorni)
    if prod not in piano:
        pytest.skip(f"{prod} not in piano for giorni={giorni}")
    r = _get("/api/analisi/previsione", tipo="prodotto", nomi=prod, giorni=giorni)
    assert r.status_code == 200, r.text
    righe = r.json().get("righe_prodotti", [])
    if not righe:
        pytest.skip(f"{prod} no righe_prodotti giorni={giorni}")
    an = next((x for x in righe if x["nome"] == prod), None)
    assert an is not None
    diff = abs(an["domanda_prevista"] - piano[prod])
    assert diff <= 0.2, f"{prod} giorni={giorni}: analisi={an['domanda_prevista']} piano={piano[prod]}"


# ---------- Unita' esposta ----------
KG_ITEMS = ["NOCI CILE CHANDLER 34/36 X 10", "PISTACCHIO SGUSCIATO KG. 1 X 10", "PISTACCHIO TOST. KG. 2 USA"]
PZ_ITEMS = ["LUPINI 250 X 24"]


@pytest.mark.parametrize("prod", KG_ITEMS)
def test_unita_kg(prod):
    r = _get("/api/analisi/previsione", tipo="prodotto", nomi=prod, giorni=30)
    assert r.status_code == 200
    j = r.json()
    for rig in j.get("righe_prodotti", []):
        if rig["nome"] == prod:
            assert rig.get("unita") == "kg", f"{prod} unita={rig.get('unita')}"
    assert j.get("kpi", {}).get("unita") == "kg"


@pytest.mark.parametrize("prod", PZ_ITEMS)
def test_unita_pz(prod):
    r = _get("/api/analisi/previsione", tipo="prodotto", nomi=prod, giorni=30)
    assert r.status_code == 200
    j = r.json()
    for rig in j.get("righe_prodotti", []):
        if rig["nome"] == prod:
            assert rig.get("unita") == "pz", f"{prod} unita={rig.get('unita')}"
    assert j.get("kpi", {}).get("unita") == "pz"


def test_unita_mista_none():
    # kg + pz mix
    r = requests.get(
        f"{BASE}/api/analisi/previsione",
        params=[("tipo", "prodotto"), ("nomi", "NOCI CILE CHANDLER 34/36 X 10"), ("nomi", "LUPINI 250 X 24"), ("giorni", 30)],
        timeout=60,
    )
    assert r.status_code == 200
    kpi_unita = r.json().get("kpi", {}).get("unita")
    assert kpi_unita is None, f"expected None got {kpi_unita}"


# ---------- Coerenza totali ----------
@pytest.mark.parametrize("prod", ["NOCI CILE CHANDLER 34/36 X 10", "PISTACCHIO SGUSCIATO KG. 1 X 10"])
def test_coerenza_totali(prod):
    r = _get("/api/analisi/previsione", tipo="prodotto", nomi=prod, giorni=30)
    assert r.status_code == 200
    j = r.json()
    sum_prod_q = sum(x["domanda_prevista"] for x in j.get("righe_prodotti", []))
    sum_client_q = sum(x.get("quantita_attesa", 0) for x in j.get("righe", []))
    kpi_q = j.get("kpi", {}).get("quantita_attesa", 0)
    assert abs(sum_prod_q - kpi_q) <= 0.5, f"prod_sum={sum_prod_q} kpi={kpi_q}"
    assert abs(sum_client_q - kpi_q) <= 0.5, f"client_sum={sum_client_q} kpi={kpi_q}"

    sum_prod_f = sum(x.get("fatturato_atteso", 0) for x in j.get("righe_prodotti", []))
    sum_cli_f = sum(x.get("fatturato_atteso", 0) for x in j.get("righe", []))
    kpi_f = j.get("kpi", {}).get("fatturato_atteso", 0)
    assert abs(sum_prod_f - kpi_f) <= 0.5
    assert abs(sum_cli_f - kpi_f) <= 0.5


# ---------- PDF previsione ----------
def _extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader  # type: ignore
    reader = PdfReader(io.BytesIO(content))
    return "\n".join(p.extract_text() or "" for p in reader.pages)


@pytest.mark.parametrize("params,title,forbidden", [
    ({"tipo": "prodotto", "nomi": "NOCI CILE CHANDLER 34/36 X 10", "vista": "clienti"}, "REPORT PRODOTTI",
     ["Giacenza", "Da ordinare", "Compra piu spesso", "Ultimo acq", "Flow Business Analytics"]),
    ({"tipo": "prodotto", "nomi": "NOCI CILE CHANDLER 34/36 X 10", "vista": "fornitori"}, "REPORT PRODOTTI", []),
    ({"tipo": "prodotto", "nomi": "NOCI CILE CHANDLER 34/36 X 10", "vista": "entrambi"}, "REPORT PRODOTTI", []),
])
def test_pdf_previsione_prodotti(params, title, forbidden):
    r = _get("/api/analisi/previsione/pdf", **params, giorni=30)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
    text = _extract_pdf_text(r.content)
    assert title in text, f"missing title {title}"
    for f in forbidden:
        assert f not in text, f"forbidden text present: {f}"
    # 70/30 mention (intro)
    if params.get("vista") == "clienti":
        assert "70" in text and "30" in text, "intro 70/30 missing"


def test_pdf_previsione_cliente():
    # pick any client
    stats = _get("/api/analisi/previsione", tipo="cliente", giorni=30)
    if stats.status_code != 200:
        pytest.skip("no cliente previsione")
    # Try with an existing client name
    j = stats.json()
    nomi = None
    for r in j.get("righe", [])[:5]:
        nomi = r.get("nome") or r.get("cliente")
        if nomi:
            break
    if not nomi:
        pytest.skip("no clients")
    r = _get("/api/analisi/previsione/pdf", tipo="cliente", nomi=nomi, giorni=30)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
    text = _extract_pdf_text(r.content)
    assert "REPORT CLIENTE" in text


def test_pdf_previsione_fornitore():
    stats = _get("/api/analisi/previsione", tipo="fornitore", giorni=30)
    if stats.status_code != 200:
        pytest.skip()
    nomi = None
    for r in stats.json().get("righe", [])[:5]:
        nomi = r.get("nome") or r.get("fornitore")
        if nomi:
            break
    if not nomi:
        pytest.skip()
    r = _get("/api/analisi/previsione/pdf", tipo="fornitore", nomi=nomi, giorni=30)
    assert r.status_code == 200
    text = _extract_pdf_text(r.content)
    assert "REPORT FORNITORE" in text


# ---------- PDF piano ----------
def test_pdf_piano_acquisti():
    r = _get("/api/ottimizzazione/piano/pdf", tipo="acquisti", giorni=30, nome="MADI VENTURA SPA")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
    text = _extract_pdf_text(r.content)
    # column headers required
    for c in ["Articolo", "Domanda prev", "Riordino", "Lotto", "Prezzo acq", "Prezzo vend", "Marg", "Valore"]:
        assert c in text, f"header missing: {c}"


def test_pdf_piano_vendite():
    r = _get("/api/ottimizzazione/piano/pdf", tipo="vendite", giorni=30, limit=2)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_piano_valore_domanda_equals_qty_prezzo():
    r = _get("/api/ottimizzazione/piano", tipo="acquisti", giorni=30, limit=100)
    assert r.status_code == 200
    fails = []
    for o in r.json().get("ordini", [])[:10]:
        for a in o.get("articoli", []):
            expected = round((a.get("domanda_prevista") or 0) * (a.get("prezzo_acquisto") or 0), 2)
            v = a.get("valore_domanda")
            if v is None:
                continue
            if abs(v - expected) > 1:
                fails.append((a.get("prodotto"), v, expected))
    assert not fails, f"mismatches: {fails[:5]}"


# ---------- PDF statistiche + confronto ----------
def test_pdf_statistiche_confronto():
    r = _get(
        "/api/statistiche/export/pdf",
        tipo="vendite",
        cmp1_start="2026-01-01", cmp1_end="2026-03-31",
        cmp2_start="2025-01-01", cmp2_end="2025-03-31",
    )
    assert r.status_code == 200, r.text
    text = _extract_pdf_text(r.content)
    assert "CONFRONTO VENDITE" in text.upper()


def test_pdf_statistiche_normale_con_filtro_prodotto():
    r = _get("/api/statistiche/export/pdf", tipo="vendite", prodotto="PISTACCHIO")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


# ---------- Confronta periodi ----------
def test_confronta_periodi_cronologia():
    r1 = _get("/api/confronta-periodi",
              start1="2026-09-01", end1="2026-09-15",
              start2="2025-09-01", end2="2025-09-15")
    r2 = _get("/api/confronta-periodi",
              start1="2025-09-01", end1="2025-09-15",
              start2="2026-09-01", end2="2026-09-15")
    assert r1.status_code == 200 and r2.status_code == 200
    j1 = r1.json(); j2 = r2.json()
    # periodo_recente
    assert j1.get("periodo_recente") in (1, 2)
    assert j2.get("periodo_recente") in (1, 2)
    # Map by prodotto and compare signs
    def by_prod(j):
        out = {}
        for r in j.get("prodotti", []) or j.get("righe", []) or []:
            out[r.get("prodotto") or r.get("nome")] = r
        return out
    m1, m2 = by_prod(j1), by_prod(j2)
    common = set(m1) & set(m2)
    assert common, f"no common products (j1 keys sample={list(m1)[:3]})"
    diffs = []
    for k in list(common)[:20]:
        a = m1[k].get("diff_qty")
        b = m2[k].get("diff_qty")
        if a is None or b is None:
            continue
        # signs should be equal (both recent - old)
        if (a > 0) != (b > 0) and a != 0 and b != 0:
            diffs.append((k, a, b))
    assert not diffs, f"sign flips: {diffs[:3]}"


# ---------- Regression PDF Analisi (was 500) ----------
@pytest.mark.parametrize("tipo", ["vendite", "acquisti"])
def test_pdf_analisi_export(tipo):
    r = _get("/api/analisi/export/pdf", tipo=tipo)
    assert r.status_code == 200, r.text[:200]
    assert r.content[:4] == b"%PDF"
