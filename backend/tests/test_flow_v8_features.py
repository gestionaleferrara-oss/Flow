"""Backend tests for iteration 8 features:
1. Ordini Mese card == popup Ordini Totali (unique cliente+data)
2. Exclusion GET/PUT + effect on statistiche
3. Prodotti sort: quantita 0 last
4. Dashboard clienti card returns clienti_in_crescita + clienti_in_calo
5. Global forecast previsioni_prodotti (top 10) + PDF
"""
import os
import time
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    yield s
    # Cleanup: ensure exclusions reset
    try:
        s.put(f"{BASE}/esclusioni", json={"nomi": []}, timeout=30)
    except Exception:
        pass


# ---------- BUG FIX: ordiniMese == popup ordini totali ----------
def test_ordini_mese_matches_popup(client):
    d = client.get(f"{BASE}/dashboard", timeout=60).json()
    ordini_mese = d.get("ordiniMese")
    pop = client.get(f"{BASE}/dashboard/card-detail/ordini?periodo=mese", timeout=60).json()
    ordini_totali = pop.get("num_visite_totali") or pop.get("ordiniTotali") or pop.get("ordini_totali")
    assert ordini_mese is not None, f"ordiniMese missing: {d.keys()}"
    assert ordini_totali is not None, f"popup value missing: {pop.keys()}"
    assert ordini_mese == ordini_totali, f"MISMATCH: card={ordini_mese} popup={ordini_totali}"


# ---------- Exclusion API ----------
def test_esclusioni_get_empty_initial(client):
    r = client.get(f"{BASE}/esclusioni", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "nomi" in data and isinstance(data["nomi"], list)
    assert "count" in data


def test_esclusioni_put_and_effect_on_statistiche(client):
    # Get baseline statistiche
    stats0 = client.get(f"{BASE}/statistiche", timeout=60).json()
    totale0 = stats0.get("totaleEuro") or stats0.get("totale_euro") or stats0.get("totale") or 0
    top_products = stats0.get("topProdotti") or stats0.get("top_prodotti") or []
    assert top_products, f"no top products: {list(stats0.keys())[:10]}"
    top_name = top_products[0].get("nome") or top_products[0].get("prodotto")
    assert top_name

    # Exclude top product
    r = client.put(f"{BASE}/esclusioni", json={"nomi": [top_name]}, timeout=30)
    assert r.status_code == 200
    assert r.json().get("count") == 1

    # Verify GET returns it
    g = client.get(f"{BASE}/esclusioni", timeout=30).json()
    assert top_name in g["nomi"]

    # Verify stats total dropped
    stats1 = client.get(f"{BASE}/statistiche", timeout=60).json()
    totale1 = stats1.get("totaleEuro") or stats1.get("totale_euro") or stats1.get("totale") or 0
    assert totale1 < totale0, f"totale not reduced: {totale0} -> {totale1}"

    top1 = stats1.get("topProdotti") or stats1.get("top_prodotti") or []
    new_top = top1[0].get("nome") or top1[0].get("prodotto") if top1 else None
    assert new_top != top_name, f"top product should have changed after excl: {new_top}"

    # Cleanup
    r2 = client.put(f"{BASE}/esclusioni", json={"nomi": []}, timeout=30)
    assert r2.status_code == 200
    assert r2.json().get("count") == 0


# ---------- Prodotti sort: zero-qty last ----------
def test_prodotti_zero_qty_sorted_last(client):
    r = client.get(f"{BASE}/prodotti?limit=200&sort_by=nome&sort_order=1", timeout=60)
    assert r.status_code == 200
    items = r.json()
    if isinstance(items, dict):
        items = items.get("items") or items.get("prodotti") or []
    qtys = []
    for p in items:
        q = p.get("quantita") if isinstance(p, dict) else None
        if q is None:
            q = p.get("giacenza", 0) if isinstance(p, dict) else 0
        qtys.append(q or 0)
    # After first zero, all subsequent must also be zero
    seen_zero = False
    for q in qtys:
        if q == 0:
            seen_zero = True
        elif seen_zero and q > 0:
            pytest.fail(f"Found positive qty after zero. Sequence: {qtys}")


# ---------- Clienti card has crescita + calo, no nuovi ----------
def test_clienti_card_detail_has_crescita_and_calo(client):
    r = client.get(f"{BASE}/dashboard/card-detail/clienti", timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert "clienti_in_crescita" in d, f"missing clienti_in_crescita: {list(d.keys())}"
    assert "clienti_in_calo" in d, f"missing clienti_in_calo: {list(d.keys())}"
    # top clienti should exist too
    assert any(k in d for k in ("top_clienti", "topClienti", "clienti"))


# ---------- Global forecast previsioni_prodotti ----------
def test_global_forecast_previsioni_prodotti(client):
    r = client.get(f"{BASE}/forecast/generate?tipo=globale&mese_target=2026-08&metrica=fatturato", timeout=90)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    prods = data.get("previsioni_prodotti") or []
    assert len(prods) == 10, f"expected 10 got {len(prods)}"
    required = {"prodotto", "anno_recente", "val_recente", "anno_precedente", "val_precedente", "previsione", "trend"}
    missing = required - set(prods[0].keys())
    assert not missing, f"missing keys: {missing} in {prods[0]}"

    # PDF export
    r2 = client.post(f"{BASE}/forecast/export-pdf", json=data, timeout=60)
    assert r2.status_code == 200
    assert r2.content[:4] == b"%PDF", f"not PDF: {r2.content[:20]}"
    assert len(r2.content) > 1000
