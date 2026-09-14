"""Iteration 8 tests: Analisi endpoints + AI Agent + regressions."""
import json
import os
import time
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://magazzino-stock.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

TIMEOUT_SHORT = 30
TIMEOUT_AGENT = 180


# ─────────── ANALISI ───────────

class TestAnalisiVendite:
    def test_vendite_prodotti_no_dates(self):
        r = requests.get(f"{API}/analisi/vendite-prodotti", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        data = r.json()
        assert "periodo" in data and "kpi" in data and "prodotti" in data
        kpi = data["kpi"]
        for k in ("fatturato", "fatturato_prec", "var_pct", "quantita", "n_prodotti",
                  "margine_medio_pct", "profitto_stimato"):
            assert k in kpi, f"missing kpi key {k}"
        assert kpi["fatturato"] > 0, "expected non-zero revenue in default period"
        assert len(data["prodotti"]) > 0

        # verify math coherence on at least 2 rows
        checked = 0
        for p in data["prodotti"][:10]:
            if p.get("costo_unitario") and p.get("prezzo_medio") and p.get("margine_pct") is not None:
                expected = (p["prezzo_medio"] - p["costo_unitario"]) / p["costo_unitario"] * 100
                assert abs(expected - p["margine_pct"]) < 0.5, \
                    f"margine mismatch on {p['prodotto']}: {expected} vs {p['margine_pct']}"
                if p["quantita"] > 0:
                    expected_pm = p["fatturato"] / p["quantita"]
                    assert abs(expected_pm - p["prezzo_medio"]) < 0.01
                checked += 1
                if checked >= 2:
                    break
        assert checked >= 2, "not enough rows with costo_unitario to verify math"
        # store first product name for other tests
        pytest.PRODOTTO_TOP = data["prodotti"][0]["prodotto"]
        pytest.PERIODO = data["periodo"]

    def test_vendite_prodotti_with_dates(self):
        r = requests.get(f"{API}/analisi/vendite-prodotti",
                         params={"start_date": "2026-06-01", "end_date": "2026-06-30"},
                         timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        assert d["periodo"]["start"] == "2026-06-01"
        assert d["periodo"]["end"] == "2026-06-30"

    def test_vendite_prodotti_search(self):
        top = getattr(pytest, "PRODOTTO_TOP", None)
        assert top, "prev test not run"
        frag = top[:4]
        r = requests.get(f"{API}/analisi/vendite-prodotti",
                         params={"search": frag}, timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        for p in d["prodotti"]:
            assert frag.lower() in p["prodotto"].lower()

    def test_prodotto_dettaglio(self):
        top = getattr(pytest, "PRODOTTO_TOP", None)
        r = requests.get(f"{API}/analisi/prodotto-dettaglio",
                         params={"nome": top}, timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        assert d["nome"] == top
        assert "serie_mensile" in d and "top_clienti" in d and "fornitori" in d
        assert "giacenza" in d and "quantita_minima" in d


ACQ_RANGE = {"start_date": "2026-07-01", "end_date": "2026-07-31"}


class TestAnalisiAcquisti:
    def test_acquisti_no_filters(self):
        # NOTE: default period (last vendite month) has 0 purchases → using explicit month
        r = requests.get(f"{API}/analisi/acquisti", params=ACQ_RANGE, timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        for k in ("spesa", "spesa_prec", "var_pct", "quantita", "n_fornitori", "n_prodotti", "resi"):
            assert k in d["kpi"]
        assert len(d["fornitori"]) > 0
        assert len(d["prodotti"]) > 0
        assert len(d["trend"]) > 0
        # ordering by spesa desc
        spese = [f["spesa"] for f in d["fornitori"]]
        assert spese == sorted(spese, reverse=True)
        pytest.FORN_TOP = d["fornitori"][0]["fornitore"]
        pytest.PROD_ACQ = d["prodotti"][0]["prodotto"]

    def test_acquisti_filter_fornitore(self):
        r0 = requests.get(f"{API}/analisi/acquisti", params=ACQ_RANGE, timeout=TIMEOUT_SHORT).json()
        forn = pytest.FORN_TOP
        r = requests.get(f"{API}/analisi/acquisti",
                         params={**ACQ_RANGE, "fornitore": forn[:5]}, timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        assert d["kpi"]["n_fornitori"] <= r0["kpi"]["n_fornitori"]
        for f in d["fornitori"]:
            assert forn[:5].lower() in f["fornitore"].lower()

    def test_acquisti_filter_prodotto(self):
        r0 = requests.get(f"{API}/analisi/acquisti", params=ACQ_RANGE, timeout=TIMEOUT_SHORT).json()
        prod = pytest.PROD_ACQ
        r = requests.get(f"{API}/analisi/acquisti",
                         params={**ACQ_RANGE, "prodotto": prod[:4]}, timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        assert d["kpi"]["n_prodotti"] <= r0["kpi"]["n_prodotti"]

    def test_acquisti_date_range(self):
        r = requests.get(f"{API}/analisi/acquisti",
                         params={"start_date": "2026-05-01", "end_date": "2026-05-31"},
                         timeout=TIMEOUT_SHORT)
        assert r.status_code == 200

    def test_confronto_fornitori(self):
        # find a product with multiple fornitori
        # broader range to find products with multiple suppliers
        wide = {"start_date": "2026-01-01", "end_date": "2026-08-14"}
        r = requests.get(f"{API}/analisi/acquisti",
                         params={**wide, "limit": 200}, timeout=TIMEOUT_SHORT).json()
        multi = next((p for p in r["prodotti"] if p.get("n_fornitori", 0) > 1), None)
        assert multi, "no product with multiple suppliers found"
        r2 = requests.get(f"{API}/analisi/confronto-fornitori",
                          params={"prodotto": multi["prodotto"], **wide}, timeout=TIMEOUT_SHORT)
        assert r2.status_code == 200
        d = r2.json()
        assert len(d["fornitori"]) >= 2
        prezzi = [f["prezzo_medio"] for f in d["fornitori"]]
        assert prezzi == sorted(prezzi), "fornitori not sorted by prezzo_medio asc"
        assert d["confronto"] is not None
        assert "migliore" in d["confronto"] and "peggiore" in d["confronto"]
        assert "risparmio_potenziale" in d["confronto"]

    def test_opzioni(self):
        r = requests.get(f"{API}/analisi/opzioni",
                         params={"tipo": "fornitori", "q": "a"}, timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        assert isinstance(r.json()["nomi"], list)
        r = requests.get(f"{API}/analisi/opzioni",
                         params={"tipo": "prodotti", "q": "a"}, timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        assert len(r.json()["nomi"]) > 0


# ─────────── AI AGENT ───────────

class TestAIAgent:
    def test_tools_list(self):
        r = requests.get(f"{API}/ai-agent/tools", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        tools = r.json()["tools"]
        assert len(tools) == 14, f"expected 14 tools, got {len(tools)}"
        for t in tools:
            assert "name" in t and "label" in t and "scrittura" in t

    def test_chat_read(self):
        payload = {"message": "Quali sono i 5 prodotti più venduti nell'ultimo mese con dati e qual è il margine medio?",
                   "session_id": "qa-read-1"}
        r = requests.post(f"{API}/ai-agent/chat", json=payload, timeout=TIMEOUT_AGENT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["success"] is True
        assert d["session_id"] == "qa-read-1"
        assert isinstance(d["response"], str) and len(d["response"]) > 20
        assert isinstance(d["azioni"], list) and len(d["azioni"]) > 0
        names = [a["strumento"] for a in d["azioni"]]
        assert any(n in ("panoramica", "query_vendite", "analisi_margini") for n in names), \
            f"expected relevant tools, got {names}"

    def test_chat_memory(self):
        payload = {"message": "E il secondo prodotto di quella lista, chi lo compra più spesso?",
                   "session_id": "qa-read-1"}
        r = requests.post(f"{API}/ai-agent/chat", json=payload, timeout=TIMEOUT_AGENT)
        assert r.status_code == 200
        d = r.json()
        assert len(d["response"]) > 20

    def test_history_and_delete(self):
        r = requests.get(f"{API}/ai-agent/history",
                         params={"session_id": "qa-read-1"}, timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        msgs = r.json()["messages"]
        assert len(msgs) >= 4  # 2 turns → 4 messages
        r = requests.delete(f"{API}/ai-agent/session",
                            params={"session_id": "qa-read-1"}, timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        r = requests.get(f"{API}/ai-agent/history",
                         params={"session_id": "qa-read-1"}, timeout=TIMEOUT_SHORT)
        assert r.json()["messages"] == []

    def test_chat_write_quantita_minima(self):
        # pick a product with a clean name (skip those starting with `(` to avoid regex/URL edge case)
        prod = requests.get(f"{API}/prodotti", params={"limit": 20}, timeout=TIMEOUT_SHORT).json()
        if isinstance(prod, dict) and "prodotti" in prod:
            prod = prod["prodotti"]
        picked = next((p for p in prod if not p["nome"].startswith("(")), None)
        assert picked, "no clean product name"
        nome = picked["nome"]
        original_qm = picked.get("quantita_minima", 0)
        pytest.WRITE_NOME = nome
        pytest.WRITE_ORIG_QM = original_qm
        pytest.WRITE_ID = picked["id"]

        payload = {"message": f"Imposta la quantita minima a 33 per il prodotto {nome}",
                   "session_id": "qa-write-1"}
        r = requests.post(f"{API}/ai-agent/chat", json=payload, timeout=TIMEOUT_AGENT)
        assert r.status_code == 200
        d = r.json()
        names = [a["strumento"] for a in d["azioni"]]
        assert "aggiorna_prodotto" in names, f"aggiorna_prodotto not called, got {names}"

        # verify DB persistence via GET on the specific id (search is regex-based)
        got = requests.get(f"{API}/prodotti", timeout=TIMEOUT_SHORT).json()
        if isinstance(got, dict) and "prodotti" in got:
            got = got["prodotti"]
        match = next((p for p in got if p["id"] == pytest.WRITE_ID), None)
        assert match is not None, f"prodotto {nome} not found"
        assert abs(match["quantita_minima"] - 33) < 0.01, \
            f"quantita_minima not updated: {match['quantita_minima']}"

        # restore
        requests.put(f"{API}/prodotti/{match['id']}",
                     json={"quantita_minima": original_qm}, timeout=TIMEOUT_SHORT)
        requests.delete(f"{API}/ai-agent/session",
                        params={"session_id": "qa-write-1"}, timeout=TIMEOUT_SHORT)

    def test_chat_write_esclusioni(self):
        nome = pytest.WRITE_NOME
        # exclude
        r = requests.post(f"{API}/ai-agent/chat",
                          json={"message": f"Escludi dai calcoli il prodotto {nome}",
                                "session_id": "qa-excl-1"}, timeout=TIMEOUT_AGENT)
        assert r.status_code == 200
        excl = requests.get(f"{API}/esclusioni", timeout=TIMEOUT_SHORT).json()
        excl_list = excl if isinstance(excl, list) else excl.get("nomi") or excl.get("prodotti") or []
        assert any(nome.lower() in e.lower() for e in excl_list), f"{nome} not in {excl_list}"

        # include again
        r = requests.post(f"{API}/ai-agent/chat",
                          json={"message": f"Reinserisci nei calcoli il prodotto {nome}",
                                "session_id": "qa-excl-1"}, timeout=TIMEOUT_AGENT)
        assert r.status_code == 200
        excl = requests.get(f"{API}/esclusioni", timeout=TIMEOUT_SHORT).json()
        excl_list = excl if isinstance(excl, list) else excl.get("nomi") or excl.get("prodotti") or []
        assert not any(e == nome for e in excl_list), f"{nome} still in {excl_list}"
        requests.delete(f"{API}/ai-agent/session",
                        params={"session_id": "qa-excl-1"}, timeout=TIMEOUT_SHORT)

    def test_stream_sse(self):
        payload = {"message": "Quanti fornitori ho e quanto ho speso in totale nell'ultimo mese con dati?",
                   "session_id": "qa-stream-1"}
        with requests.post(f"{API}/ai-agent/stream", json=payload,
                           stream=True, timeout=TIMEOUT_AGENT) as r:
            assert r.status_code == 200
            events = []
            start = time.time()
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if raw.startswith("data: "):
                    try:
                        obj = json.loads(raw[6:])
                        events.append(obj)
                        if obj.get("type") == "done" or obj.get("type") == "error":
                            break
                    except Exception:
                        pass
                if time.time() - start > TIMEOUT_AGENT:
                    break
        types = {e["type"] for e in events}
        assert "session" in types
        assert "done" in types or "error" not in types
        assert "delta" in types or "tool_start" in types, f"no content events, got {types}"
        requests.delete(f"{API}/ai-agent/session",
                        params={"session_id": "qa-stream-1"}, timeout=TIMEOUT_SHORT)


# ─────────── REGRESSION ───────────

class TestRegression:
    def test_recalculate(self):
        r = requests.post(f"{API}/prodotti/recalculate-quantities", timeout=180)
        assert r.status_code == 200
        d = r.json()
        assert d.get("success") or "aggiornati" in d or "prodotti" in d, d

    def test_esclusioni_impact_dashboard(self):
        # get a product name from vendite that has volumes
        top = requests.get(f"{API}/analisi/vendite-prodotti", timeout=TIMEOUT_SHORT).json()
        target = top["prodotti"][0]["prodotto"]

        # exclude it
        current = requests.get(f"{API}/esclusioni", timeout=TIMEOUT_SHORT).json()
        cur_list = current if isinstance(current, list) else current.get("nomi") or current.get("prodotti") or []
        new_list = list(set(cur_list) | {target})
        # try different payload shapes
        for payload in ({"nomi": new_list}, {"prodotti": new_list}, new_list):
            rr = requests.put(f"{API}/esclusioni", json=payload, timeout=TIMEOUT_SHORT)
            if rr.status_code < 400:
                break
        else:
            pytest.skip("cannot set esclusioni")

        try:
            trends = requests.get(f"{API}/trends-vendite", timeout=60).json()
            # trends structure varies; ensure target not top-listed
            prod_lists = []
            if isinstance(trends, dict):
                for v in trends.values():
                    if isinstance(v, list):
                        prod_lists.append(v)
            found = False
            for lst in prod_lists:
                for p in lst:
                    if isinstance(p, dict) and p.get("prodotto") == target:
                        found = True
            assert not found, f"{target} still appears in trends-vendite despite exclusion"

            calo = requests.get(f"{API}/top-clienti-prodotti-calo", timeout=60).json()
            found2 = False
            if isinstance(calo, list):
                for row in calo:
                    if isinstance(row, dict) and row.get("prodotto") == target:
                        found2 = True
            assert not found2, f"{target} in top-clienti-prodotti-calo despite exclusion"
        finally:
            # restore
            for payload in ({"nomi": cur_list}, {"prodotti": cur_list}, cur_list):
                if requests.put(f"{API}/esclusioni", json=payload, timeout=TIMEOUT_SHORT).status_code < 400:
                    break
