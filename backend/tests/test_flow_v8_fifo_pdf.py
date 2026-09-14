"""Iteration 8 tests: FIFO endpoints, PDF exports, margine FIFO usage, AI agent generate_pdf link."""
import os
import time
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("/app/frontend/.env"))
BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://magazzino-stock.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
TIMEOUT = 60
TIMEOUT_AGENT = 180

PROD_PINOLI = "PINOLI ITALIA KG. 1 X 10"
PROD_NOCI = "NOCI USA CHANDLER 34+ X 10"
PROD_NOCI_SG = "NOCI SGUSCIATE CILE  KG.1 X 10"  # double space in name
CLIENTE = "GREMENTIERI ALDO SAS"


# ─────────── FIFO ───────────

class TestFifo:
    def test_stato(self):
        r = requests.get(f"{API}/fifo/stato", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "copertura_pct" in d
        # requirement: 100 %
        assert d["copertura_pct"] == 100, f"copertura_pct={d['copertura_pct']} expected 100"

    def test_lotti_noci(self):
        r = requests.get(f"{API}/fifo/lotti", params={"prodotto": PROD_NOCI}, timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        lotti = d.get("lotti") or d
        if isinstance(lotti, dict):
            lotti = lotti.get("lotti") or []
        assert isinstance(lotti, list) and len(lotti) > 0, f"no lotti for {PROD_NOCI}: {d}"
        for lot in lotti:
            pa = lot.get("prezzo_acquisto")
            assert pa is not None and pa > 0, f"lotto with non-positive prezzo_acquisto: {lot}"
            if lot.get("prezzo_stimato"):
                assert isinstance(lot["prezzo_stimato"], bool)

    def test_rebuild_prodotto(self):
        t0 = time.time()
        r = requests.post(f"{API}/fifo/rebuild", params={"prodotto": PROD_PINOLI}, timeout=90)
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text
        d = r.json()
        # metadata expected
        assert isinstance(d, dict)
        assert elapsed < 60, f"rebuild too slow: {elapsed}s"


# ─────────── MARGINE VENDITE FIFO ───────────

class TestMargineVendite:
    def test_margine_uses_fifo(self):
        r = requests.get(f"{API}/margine-vendite", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        metodo = d.get("metodo", "")
        assert "FIFO" in str(metodo).upper(), f"metodo missing FIFO: {metodo}"
        assert "margine_medio_pct" in d
        assert "top_margini" in d and isinstance(d["top_margini"], list)
        assert "worst_margini" in d and isinstance(d["worst_margini"], list)

    def test_regression_sales_insight(self):
        r = requests.get(f"{API}/sales-insight", timeout=TIMEOUT)
        assert r.status_code == 200

    def test_regression_dashboard(self):
        r = requests.get(f"{API}/dashboard", timeout=TIMEOUT)
        assert r.status_code == 200


# ─────────── PRODOTTO DETTAGLIO enrichment ───────────

class TestProdottoDettaglio:
    def test_dettaglio_pinoli(self):
        r = requests.get(f"{API}/analisi/prodotto-dettaglio",
                         params={"nome": PROD_PINOLI}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "serie_mensile" in d and isinstance(d["serie_mensile"], list)
        if d["serie_mensile"]:
            m = d["serie_mensile"][0]
            # required fields
            assert "costo_lotti" in m or "costo_fifo" in m, f"missing costo_lotti in {m.keys()}"
            assert "margine_pct" in m
        assert "lotti" in d and isinstance(d["lotti"], list)
        if d["lotti"]:
            lot = d["lotti"][0]
            for k in ("data_acquisto", "fornitore", "prezzo_acquisto",
                      "quantita_venduta", "residuo"):
                assert k in lot, f"missing {k} in lotto {lot}"
        assert "top_clienti" in d
        if d["top_clienti"]:
            tc = d["top_clienti"][0]
            for k in ("quantita", "prezzo_medio", "costo_unitario", "margine_pct"):
                assert k in tc, f"missing {k} in top_clienti {tc}"
        assert "fornitori" in d


# ─────────── PDF EXPORTS ───────────

class TestPdfExports:
    def _assert_pdf(self, r, min_size=3000):
        assert r.status_code == 200, f"{r.status_code}: {r.text[:200]}"
        ct = r.headers.get("content-type", "")
        assert "application/pdf" in ct, f"wrong content-type: {ct}"
        assert r.content[:4] == b"%PDF", f"not PDF header: {r.content[:20]}"
        assert len(r.content) > min_size, f"pdf too small: {len(r.content)} bytes"

    def test_rendiconto_no_detail(self):
        r = requests.get(f"{API}/analisi/export/rendiconto",
                         params={"start_date": "2026-07-01", "end_date": "2026-07-31"},
                         timeout=TIMEOUT)
        self._assert_pdf(r)
        self.size_no_detail = len(r.content)

    def test_rendiconto_with_detail(self):
        r = requests.get(f"{API}/analisi/export/rendiconto",
                         params={"start_date": "2026-07-01", "end_date": "2026-07-31",
                                 "dettaglio": "true"},
                         timeout=TIMEOUT)
        self._assert_pdf(r)

    def test_pdf_vendite(self):
        r = requests.get(f"{API}/analisi/export/pdf",
                         params={"tipo": "vendite"}, timeout=TIMEOUT)
        self._assert_pdf(r)

    def test_pdf_acquisti(self):
        r = requests.get(f"{API}/analisi/export/pdf",
                         params={"tipo": "acquisti",
                                 "start_date": "2026-06-01",
                                 "end_date": "2026-07-31"}, timeout=TIMEOUT)
        self._assert_pdf(r)

    def test_listino_cliente(self):
        r = requests.get(f"{API}/analisi/export/listino",
                         params={"cliente": CLIENTE,
                                 "start_date": "2026-06-01",
                                 "end_date": "2026-07-31"}, timeout=TIMEOUT)
        self._assert_pdf(r)

    def test_listino_prodotto(self):
        r = requests.get(f"{API}/analisi/export/listino",
                         params={"prodotto": PROD_PINOLI,
                                 "start_date": "2026-06-01",
                                 "end_date": "2026-07-31"}, timeout=TIMEOUT)
        self._assert_pdf(r)

    def test_listino_missing_params_400(self):
        r = requests.get(f"{API}/analisi/export/listino",
                         params={"start_date": "2026-06-01",
                                 "end_date": "2026-07-31"}, timeout=TIMEOUT)
        assert r.status_code == 400, f"expected 400 got {r.status_code}"

    def test_rendiconto_empty_period_404(self):
        r = requests.get(f"{API}/analisi/export/rendiconto",
                         params={"start_date": "2030-01-01",
                                 "end_date": "2030-01-31"}, timeout=TIMEOUT)
        assert r.status_code == 404, f"expected 404 got {r.status_code}: {r.text[:200]}"


# ─────────── AI AGENT generate_pdf link ───────────

class TestAgentPdfLink:
    def test_agent_generates_relative_link(self):
        payload = {"message": "preparami il rendiconto pdf di luglio 2026",
                   "session_id": "qa-pdf-1"}
        r = requests.post(f"{API}/ai-agent/chat", json=payload, timeout=TIMEOUT_AGENT)
        assert r.status_code == 200, r.text
        d = r.json()
        resp = d.get("response", "")
        # must contain markdown link that starts with /api/analisi/export/rendiconto
        assert "/api/analisi/export/rendiconto" in resp, \
            f"no rendiconto link found in agent response: {resp[:400]}"
        # must NOT invent a domain
        bad_domains = ["example.com", "yourdomain", "http://localhost", "https://localhost"]
        for bd in bad_domains:
            assert bd not in resp, f"agent invented domain {bd}"
        # cleanup
        requests.delete(f"{API}/ai-agent/session",
                        params={"session_id": "qa-pdf-1"}, timeout=TIMEOUT)


# ─────────── CONFRONTO FORNITORI extra ordering ───────────

class TestConfrontoFornitoriOrder:
    def test_ordering_lowest_price_first(self):
        # find product with multiple suppliers
        wide = {"start_date": "2026-01-01", "end_date": "2026-08-31", "limit": 200}
        r = requests.get(f"{API}/analisi/acquisti", params=wide, timeout=TIMEOUT).json()
        multi = next((p for p in r["prodotti"] if p.get("n_fornitori", 0) > 1), None)
        if not multi:
            pytest.skip("no product with multiple suppliers")
        r2 = requests.get(f"{API}/analisi/confronto-fornitori",
                          params={"prodotto": multi["prodotto"], **wide}, timeout=TIMEOUT).json()
        prezzi = [f["prezzo_medio"] for f in r2["fornitori"]]
        assert prezzi == sorted(prezzi), f"not sorted asc: {prezzi}"
        assert "risparmio_potenziale" in r2["confronto"]
