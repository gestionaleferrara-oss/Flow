"""Iteration 9 tests - PDF exports, piano acquisti (rotazione/riordino/fornitore primario), scheda articolo."""
import os
import pytest
import requests
from urllib.parse import quote

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE, "REACT_APP_BACKEND_URL missing"

TIMEOUT = 60

# ---- Analisi PDF ----
class TestAnalisiPDF:
    def _check_pdf(self, r):
        assert r.status_code == 200, f"{r.status_code}: {r.text[:200]}"
        ct = r.headers.get("content-type", "")
        assert "application/pdf" in ct, f"content-type={ct}"
        assert len(r.content) > 20_000, f"pdf size {len(r.content)} too small"
        assert r.content[:4] == b"%PDF", "not a PDF"

    def test_analisi_vendite(self):
        r = requests.get(f"{BASE}/api/analisi/export/pdf",
                         params={"tipo":"vendite","start_date":"2026-06-01","end_date":"2026-08-31"},
                         timeout=TIMEOUT)
        self._check_pdf(r)

    def test_analisi_acquisti(self):
        r = requests.get(f"{BASE}/api/analisi/export/pdf",
                         params={"tipo":"acquisti","start_date":"2026-06-01","end_date":"2026-08-31"},
                         timeout=TIMEOUT)
        self._check_pdf(r)

    def test_rendiconto(self):
        r = requests.get(f"{BASE}/api/analisi/export/rendiconto",
                         params={"start_date":"2026-06-01","end_date":"2026-08-31"},
                         timeout=TIMEOUT)
        self._check_pdf(r)

    def test_listino_prodotto(self):
        r = requests.get(f"{BASE}/api/analisi/export/listino",
                         params={"prodotto":"PISTACCHIO TOST. KG. 2 USA",
                                 "start_date":"2026-06-01","end_date":"2026-08-31"},
                         timeout=TIMEOUT)
        self._check_pdf(r)

    def test_listino_cliente(self):
        r = requests.get(f"{BASE}/api/analisi/export/listino",
                         params={"cliente":"NUOVA ORTOFRUTTICOLA MODENESE S.R.L.",
                                 "start_date":"2026-06-01","end_date":"2026-08-31"},
                         timeout=TIMEOUT)
        self._check_pdf(r)

    def test_previsione_pdf(self):
        r = requests.get(f"{BASE}/api/analisi/previsione/pdf",
                         params={"tipo":"prodotto","nomi":"PISTACCHIO TOST. KG. 2 USA","giorni":30},
                         timeout=TIMEOUT)
        self._check_pdf(r)


# ---- Piano ottimizzazione ----
class TestPianoPDF:
    def _check_pdf(self, r):
        assert r.status_code == 200, f"{r.status_code}: {r.text[:200]}"
        assert "application/pdf" in r.headers.get("content-type","")
        assert len(r.content) > 20_000
        assert r.content[:4] == b"%PDF"

    def test_piano_pdf_acquisti(self):
        r = requests.get(f"{BASE}/api/ottimizzazione/piano/pdf",
                         params={"tipo":"acquisti","giorni":30}, timeout=TIMEOUT)
        self._check_pdf(r)

    def test_piano_pdf_vendite(self):
        r = requests.get(f"{BASE}/api/ottimizzazione/piano/pdf",
                         params={"tipo":"vendite","giorni":30}, timeout=TIMEOUT)
        self._check_pdf(r)

    def test_piano_pdf_singolo_fornitore(self):
        r0 = requests.get(f"{BASE}/api/ottimizzazione/piano",
                          params={"tipo":"acquisti","giorni":30}, timeout=TIMEOUT)
        assert r0.status_code == 200
        d = r0.json()
        sch = d.get("ordini") or []
        assert sch, f"no ordini: {list(d.keys())}"
        nome = sch[0].get("fornitore")
        r = requests.get(f"{BASE}/api/ottimizzazione/piano/pdf",
                         params={"tipo":"acquisti","giorni":30,"nome":nome},
                         timeout=TIMEOUT)
        self._check_pdf(r)


class TestPianoAcquistiFields:
    def test_piano_has_rotazione_riordino_ruolo(self):
        r = requests.get(f"{BASE}/api/ottimizzazione/piano",
                         params={"tipo":"acquisti","giorni":30}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        schede = d.get("ordini") or []
        assert schede
        articoli = schede[0].get("articoli") or []
        assert articoli
        a = articoli[0]
        for k in ["rotazione","riordino_giorni","ordini_ultimo_anno","ruolo_fornitore","quota_fornitore_pct"]:
            assert k in a, f"missing field {k}; got {list(a.keys())}"
        assert a["rotazione"] in ["bassa","media","alta",None]

    def test_noci_sgusciate_prezzo_primario(self):
        r = requests.get(f"{BASE}/api/ottimizzazione/piano",
                         params={"tipo":"acquisti","giorni":30}, timeout=TIMEOUT)
        d = r.json()
        for s in d.get("ordini",[]):
            for a in s.get("articoli",[]):
                if a.get("prodotto") == "NOCI SGUSCIATE CILE  KG.1 X 10":
                    forn = s["fornitore"]
                    prezzo = a["prezzo_acquisto"]
                    print(f"NOCI: forn={forn} prezzo={prezzo} ruolo={a['ruolo_fornitore']} quota={a['quota_fornitore_pct']}")
                    assert "SACCHETTI" in forn.upper(), f"expected SACCHETTI, got {forn}"
                    assert 12.5 <= prezzo <= 13.5, f"expected ~12.87, got {prezzo}"
                    return
        pytest.fail("NOCI SGUSCIATE CILE  KG.1 X 10 not found")


class TestSchedaArticolo:
    def test_dettaglio_articolo(self):
        r = requests.get(f"{BASE}/api/ottimizzazione/piano/articolo",
                         params={"prodotto":"NOCI SGUSCIATE CILE  KG.1 X 10","giorni":30},
                         timeout=TIMEOUT)
        assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
        d = r.json()
        assert "spiegazione" in d and d["spiegazione"]
        tabs = d.get("tabelle") or []
        assert len(tabs) >= 3, f"expected >=3 tables, got {len(tabs)}"
        titoli = " || ".join((t.get("titolo") or "").lower() for t in tabs)
        assert "client" in titoli, f"missing clienti table: {titoli}"
        assert "mensil" in titoli or "andamento" in titoli, f"missing mensile: {titoli}"
        assert "fornit" in titoli, f"missing fornitori: {titoli}"
