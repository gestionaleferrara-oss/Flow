"""Tests for iteration 9 v2 (PDF listino, ottimizzazione piano, previsione con fornitore primario)."""
import os
import requests
import pytest
from urllib.parse import urlencode

def _get_base_url():
    url = os.environ.get('REACT_APP_BACKEND_URL')
    if not url:
        # fallback to frontend/.env
        with open('/app/frontend/.env') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    url = line.split('=', 1)[1].strip()
                    break
    return url.rstrip('/')

BASE_URL = _get_base_url()
TIMEOUT = 60

NOCI = "NOCI SGUSCIATE CILE  KG.1 X 10"
PIST = "PISTACCHIO TOST. KG. 2 USA"
CLIENTE = "NUOVA ORTOFRUTTICOLA MODENESE S.R.L."
FORN = "MADI VENTURA SPA"


# ---------- BUG PRINCIPALE: Listino PDF ----------
class TestListinoPDF:
    def test_listino_per_prodotto_ok(self):
        # Listino per PRODOTTO con date
        params = {"prodotto": PIST, "start_date": "2026-01-01", "end_date": "2026-09-14"}
        r = requests.get(f"{BASE_URL}/api/analisi/export/listino", params=params, timeout=TIMEOUT)
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:300]}"
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_listino_per_cliente_ok(self):
        params = {"cliente": CLIENTE, "start_date": "2026-01-01", "end_date": "2026-09-14"}
        r = requests.get(f"{BASE_URL}/api/analisi/export/listino", params=params, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_listino_prodotto_senza_date_periodo_automatico(self):
        # Il frontend può omettere start/end (modalità automatica)
        params = {"prodotto": PIST}
        r = requests.get(f"{BASE_URL}/api/analisi/export/listino", params=params, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF"

    def test_listino_prodotto_partial_match(self):
        # 'PISTACCHIO' come regex parziale
        params = {"prodotto": "PISTACCHIO"}
        r = requests.get(f"{BASE_URL}/api/analisi/export/listino", params=params, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF"

    def test_listino_no_match_404(self):
        params = {"prodotto": "zzzz_nonexistent"}
        r = requests.get(f"{BASE_URL}/api/analisi/export/listino", params=params, timeout=TIMEOUT)
        assert r.status_code == 404


# ---------- Previsione: fornitore primario ----------
class TestPrevisioneFornitorePrimario:
    def test_previsione_prodotti_multi(self):
        params = [("tipo", "prodotto"), ("nomi", NOCI), ("nomi", PIST), ("giorni", "30")]
        r = requests.get(f"{BASE_URL}/api/analisi/previsione", params=params, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "righe_prodotti" in data
        righe = data["righe_prodotti"]
        assert len(righe) >= 1
        # Verifica presenza campo fornitore
        noci_row = next((r for r in righe if "NOCI" in r.get("nome", "")), None)
        assert noci_row is not None
        assert "fornitore" in noci_row
        # Deve essere quello primario (SACCHETTI) e non un fornitore occasionale
        print(f"NOCI fornitore={noci_row.get('fornitore')} prezzo={noci_row.get('prezzo_acquisto')}")
        assert "SACCHETTI" in noci_row["fornitore"], f"Fornitore primario atteso SACCHETTI, ricevuto {noci_row['fornitore']}"
        assert abs(noci_row["prezzo_acquisto"] - 12.863) < 0.5


# ---------- Piano ottimizzazione con rotazione/riordino ----------
class TestPianoOttimizzazione:
    def test_piano_acquisti_has_rotazione_riordino(self):
        r = requests.get(f"{BASE_URL}/api/ottimizzazione/piano",
                         params={"tipo": "acquisti", "giorni": 30, "limit": 3}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        # Verifica struttura: schede fornitore con articoli aventi rotazione + riordino_giorni
        found = False
        schede = data.get("schede") or data.get("ordini") or data.get("proposte") or []
        # Estrai articoli
        for sc in schede:
            articoli = sc.get("articoli") or sc.get("items") or []
            for a in articoli:
                if "rotazione" in a and "riordino_giorni" in a:
                    found = True
                    break
            if found:
                break
        assert found, f"rotazione/riordino non trovati nel piano. keys top-level: {list(data.keys())}"

    def test_piano_pdf_acquisti(self):
        r = requests.get(f"{BASE_URL}/api/ottimizzazione/piano/pdf",
                         params={"tipo": "acquisti", "giorni": 30, "limit": 3}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_piano_pdf_singola_scheda(self):
        r = requests.get(f"{BASE_URL}/api/ottimizzazione/piano/pdf",
                         params={"tipo": "acquisti", "giorni": 30, "limit": 3, "nome": FORN},
                         timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF"

    def test_piano_pdf_vendite(self):
        r = requests.get(f"{BASE_URL}/api/ottimizzazione/piano/pdf",
                         params={"tipo": "vendite", "giorni": 30, "limit": 3}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF"


# ---------- Dettaglio articolo (scheda prodotto) ----------
class TestSchedaProdotto:
    def test_dettaglio_articolo(self):
        r = requests.get(f"{BASE_URL}/api/ottimizzazione/piano/articolo",
                         params={"prodotto": PIST, "giorni": 30}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "titolo" in data and "tabelle" in data
        tabelle = data["tabelle"]
        assert len(tabelle) == 3, f"attese 3 tabelle, trovate {len(tabelle)}"
        titoli = " | ".join(t.get("titolo", "") for t in tabelle)
        assert "Client" in titoli
        assert "mensile" in titoli.lower() or "andamento" in titoli.lower()
        assert "Fornitori" in titoli or "fornitor" in titoli.lower()
        # verifica colonne prima tabella (clienti YoY)
        cols0 = tabelle[0].get("colonne", [])
        assert any("Var" in c for c in cols0), f"manca colonna Var % in {cols0}"


# ---------- Considerazioni AI nel PDF analisi ----------
class TestExportAnalisiPDF:
    def test_export_vendite_pdf_200(self):
        r = requests.get(f"{BASE_URL}/api/analisi/export/pdf",
                         params={"tipo": "vendite", "start_date": "2026-06-01", "end_date": "2026-08-31"},
                         timeout=90)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF"


# ---------- Regressione previsione cliente/fornitore + PDF ----------
class TestPrevisioneCFPdf:
    def test_previsione_cliente(self):
        r = requests.get(f"{BASE_URL}/api/analisi/previsione",
                         params={"tipo": "cliente", "nomi": CLIENTE, "giorni": 30}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]

    def test_previsione_fornitore(self):
        r = requests.get(f"{BASE_URL}/api/analisi/previsione",
                         params={"tipo": "fornitore", "nomi": FORN, "giorni": 30}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text[:300]

    def test_previsione_pdf_cliente(self):
        r = requests.get(f"{BASE_URL}/api/analisi/previsione/pdf",
                         params={"tipo": "cliente", "nomi": CLIENTE, "giorni": 30}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF"

    def test_previsione_pdf_fornitore(self):
        r = requests.get(f"{BASE_URL}/api/analisi/previsione/pdf",
                         params={"tipo": "fornitore", "nomi": FORN, "giorni": 30}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF"
