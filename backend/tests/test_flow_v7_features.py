"""Tests for iteration 7 features:
- Magazzino recalculate-quantities
- Upload pulisci-duplicati
- Dashboard card-detail ordini (media_ordini_giornaliera, no giorni_picco)
- Dashboard card-detail clienti (clienti_in_crescita, no piu_frequenti)
- Forecast PDF with anno_recente/val_recente/anno_precedente/val_precedente
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"


# --- Magazzino recalculate ---
def test_recalculate_quantities():
    r = requests.post(f"{API}/prodotti/recalculate-quantities", timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "prodotti_aggiornati" in data
    assert isinstance(data["prodotti_aggiornati"], int)
    assert data["prodotti_aggiornati"] >= 0


# --- Pulisci duplicati ---
def test_pulisci_duplicati():
    r = requests.post(f"{API}/pulisci-duplicati", timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("success") is True
    assert "vendite_rimossi" in data
    assert "ordini_rimossi" in data
    assert "message" in data


# --- Dashboard card-detail ordini ---
def test_card_detail_ordini_has_media_no_picco():
    r = requests.get(f"{API}/dashboard/card-detail/ordini?periodo=mese", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["tipo"] == "ordini"
    assert "media_ordini_giornaliera" in data
    assert "giorni_attivi" in data
    assert "scontrino_medio" in data
    # Must NOT have peak days key
    assert "giorni_picco" not in data
    assert "picco_giornaliero" not in data
    assert "picco" not in data


# --- Dashboard card-detail clienti ---
def test_card_detail_clienti_has_crescita_no_frequenti():
    r = requests.get(f"{API}/dashboard/card-detail/clienti?periodo=mese", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["tipo"] == "clienti"
    assert "clienti_in_crescita" in data
    assert isinstance(data["clienti_in_crescita"], list)
    # Must NOT contain "piu_frequenti"
    assert "piu_frequenti" not in data
    # If not empty, verify shape
    for c in data["clienti_in_crescita"]:
        assert "nome" in c
        assert "crescita_eur" in c


# --- Forecast generate + export-pdf ---
def test_forecast_generate_and_pdf_has_anno_fields():
    gen = requests.get(
        f"{API}/forecast/generate",
        params={"tipo": "globale", "mese_target": "2026-08", "metrica": "fatturato"},
        timeout=180,
    )
    assert gen.status_code == 200, gen.text
    body = gen.json()
    assert body.get("success") is True
    previsioni = body.get("previsioni", [])
    assert len(previsioni) >= 1
    # Each previsione must contain the new fields
    for p in previsioni:
        assert "anno_recente" in p
        assert "val_recente" in p
        assert "anno_precedente" in p
        assert "val_precedente" in p

    pdf = requests.post(f"{API}/forecast/export-pdf", json=body, timeout=60)
    assert pdf.status_code == 200, pdf.text
    ct = pdf.headers.get("content-type", "")
    assert "application/pdf" in ct
    assert pdf.content[:4] == b"%PDF"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
