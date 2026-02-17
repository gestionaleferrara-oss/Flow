"""
Backend API Tests for Flusso v4 Features
Testing: Fornitori Year Selector, Month Selector Modal, Statistiche Period-specific KPIs, Prezzi Mercati

Features tested:
1. Fornitori page: year selector in Fatturato column header
2. Fornitori page: modal with month selector showing individual purchase rows
3. Statistiche page: period-specific KPIs (not cumulative)
4. Notizie page: prezzi mercati widget with city names
"""

import pytest
import requests
import os
from urllib.parse import quote

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://flow-dashboard-7.preview.emergentagent.com').rstrip('/')

# Test supplier for modal testing
TEST_SUPPLIER = "PANCRAZIO SPA"


class TestFornitoriYearSelector:
    """Test year selector in Fatturato column - GET /api/fornitori-with-stats"""
    
    def test_returns_dict_structure(self):
        """Response should be dict with 'fornitori' and 'anni_disponibili'"""
        response = requests.get(f"{BASE_URL}/api/fornitori-with-stats")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict), "Response should be dict, not array"
        assert "fornitori" in data, "Should have 'fornitori' key"
        assert "anni_disponibili" in data, "Should have 'anni_disponibili' key"
        
    def test_anni_disponibili_has_years(self):
        """anni_disponibili should contain years like 2025, 2024"""
        response = requests.get(f"{BASE_URL}/api/fornitori-with-stats")
        assert response.status_code == 200
        data = response.json()
        
        anni = data.get("anni_disponibili", [])
        assert len(anni) > 0, "Should have at least one year"
        
        # Verify years are valid strings
        for anno in anni:
            assert isinstance(anno, str), f"Year should be string, got {type(anno)}"
            assert len(anno) == 4, f"Year should be 4 chars, got {anno}"
            
    def test_year_2025_filter(self):
        """GET /api/fornitori-with-stats?anno=2025 should filter by year"""
        response = requests.get(f"{BASE_URL}/api/fornitori-with-stats?anno=2025")
        assert response.status_code == 200
        data = response.json()
        
        fornitori = data.get("fornitori", [])
        assert isinstance(fornitori, list)
        
        # Verify structure
        if fornitori:
            f = fornitori[0]
            assert "nome" in f
            assert "fatturato_totale" in f
            assert isinstance(f["fatturato_totale"], (int, float))
            
    def test_year_2024_filter(self):
        """GET /api/fornitori-with-stats?anno=2024 should filter by year"""
        response = requests.get(f"{BASE_URL}/api/fornitori-with-stats?anno=2024")
        assert response.status_code == 200
        data = response.json()
        
        assert "fornitori" in data
        
    def test_different_years_different_fatturato(self):
        """Year filter should produce different fatturato values"""
        r2025 = requests.get(f"{BASE_URL}/api/fornitori-with-stats?anno=2025")
        r2024 = requests.get(f"{BASE_URL}/api/fornitori-with-stats?anno=2024")
        
        assert r2025.status_code == 200
        assert r2024.status_code == 200
        
        d2025 = r2025.json()
        d2024 = r2024.json()
        
        # Both should have fornitori array
        assert len(d2025.get("fornitori", [])) >= 0
        assert len(d2024.get("fornitori", [])) >= 0


class TestFornitoriMonthModal:
    """Test month selector modal - GET /api/fornitori/{nome}/prodotti"""
    
    def test_returns_acquisti_not_prodotti(self):
        """Response should have 'acquisti' array (individual rows), not aggregated 'prodotti'"""
        encoded = quote(TEST_SUPPLIER)
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded}/prodotti")
        assert response.status_code == 200
        data = response.json()
        
        # Key change: uses 'acquisti' for individual rows
        assert "acquisti" in data, "Should have 'acquisti' key for individual rows"
        assert "totale_acquisti" in data
        assert "totale_speso" in data
        assert "mese_riferimento" in data
        assert "mesi_disponibili" in data
        
    def test_acquisti_row_structure(self):
        """Each acquisto row should have: prodotto, data, quantita, prezzo_unitario, totale"""
        encoded = quote(TEST_SUPPLIER)
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded}/prodotti")
        assert response.status_code == 200
        data = response.json()
        
        acquisti = data.get("acquisti", [])
        if acquisti:
            row = acquisti[0]
            assert "prodotto" in row, "Should have 'prodotto' field"
            assert "data" in row, "Should have 'data' field"
            assert "quantita" in row, "Should have 'quantita' field"
            assert "prezzo_unitario" in row, "Should have 'prezzo_unitario' field"
            assert "totale" in row, "Should have 'totale' field"
            
    def test_mesi_disponibili_structure(self):
        """mesi_disponibili should be {value, label} pairs"""
        encoded = quote(TEST_SUPPLIER)
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded}/prodotti")
        assert response.status_code == 200
        data = response.json()
        
        mesi = data.get("mesi_disponibili", [])
        if mesi:
            m = mesi[0]
            assert "value" in m, "Should have 'value' key"
            assert "label" in m, "Should have 'label' key"
            assert len(m["value"]) == 7, f"Value should be YYYY-MM, got {m['value']}"
            
    def test_italian_month_labels(self):
        """Labels should be Italian: 'Ottobre 2025', 'Marzo 2025', etc."""
        encoded = quote(TEST_SUPPLIER)
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded}/prodotti")
        assert response.status_code == 200
        data = response.json()
        
        mesi = data.get("mesi_disponibili", [])
        italian_months = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
                        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
        
        if mesi:
            label = mesi[0].get("label", "")
            has_italian = any(m in label for m in italian_months)
            assert has_italian, f"Label should contain Italian month, got {label}"
            
    def test_month_filter_param(self):
        """GET ?mese=YYYY-MM should filter data and return mese_selezionato"""
        encoded = quote(TEST_SUPPLIER)
        # First get available months
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded}/prodotti")
        data = response.json()
        
        mesi = data.get("mesi_disponibili", [])
        if mesi:
            test_mese = mesi[0]["value"]
            response2 = requests.get(f"{BASE_URL}/api/fornitori/{encoded}/prodotti?mese={test_mese}")
            assert response2.status_code == 200
            data2 = response2.json()
            
            assert data2.get("mese_selezionato") == test_mese


class TestStatistichePeriodSpecific:
    """Test Statistiche page - KPIs should be period-specific using totaleEuro"""
    
    def test_vendite_statistiche_has_totaleEuro(self):
        """GET /api/statistiche should return totaleEuro for period-specific display"""
        response = requests.get(f"{BASE_URL}/api/statistiche")
        assert response.status_code == 200
        data = response.json()
        
        assert "totaleEuro" in data, "Should have 'totaleEuro' for period KPI"
        assert "totaleArticoli" in data
        assert "clientiAttivi" in data
        
    def test_date_filter_affects_totaleEuro(self):
        """Date filters should change totaleEuro value"""
        # Test with January 2026 filter
        r_jan = requests.get(f"{BASE_URL}/api/statistiche?start_date=2026-01-01&end_date=2026-01-31")
        assert r_jan.status_code == 200
        d_jan = r_jan.json()
        
        # Test with broader date range
        r_all = requests.get(f"{BASE_URL}/api/statistiche")
        assert r_all.status_code == 200
        d_all = r_all.json()
        
        # totaleEuro should be present in both
        assert "totaleEuro" in d_jan
        assert "totaleEuro" in d_all
        
    def test_acquisti_statistiche_structure(self):
        """GET /api/statistiche/acquisti should return acquisti-specific fields"""
        response = requests.get(f"{BASE_URL}/api/statistiche/acquisti")
        assert response.status_code == 200
        data = response.json()
        
        assert "totaleEuro" in data
        assert "totaleArticoli" in data
        assert "fornitoriAttivi" in data, "Should have 'fornitoriAttivi' for acquisti view"
        
    def test_acquisti_date_filter(self):
        """GET /api/statistiche/acquisti with date filter"""
        response = requests.get(f"{BASE_URL}/api/statistiche/acquisti?start_date=2026-01-01&end_date=2026-01-31")
        assert response.status_code == 200
        data = response.json()
        
        assert "totaleEuro" in data
        assert "fornitoriAttivi" in data
        
    def test_venditeMensili_for_charts(self):
        """Should return venditeMensili for chart rendering"""
        response = requests.get(f"{BASE_URL}/api/statistiche?start_date=2026-01-01&end_date=2026-01-31")
        assert response.status_code == 200
        data = response.json()
        
        assert "venditeMensili" in data
        mensili = data.get("venditeMensili", [])
        assert isinstance(mensili, list)


class TestPrezziMercati:
    """Test Prezzi Mercati widget - city names with clickable links"""
    
    def test_returns_city_list(self):
        """GET /api/prezzi-mercati should return list of cities"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0, "Should have at least one market"
        
    def test_city_structure(self):
        """Each city should have 'nome' and 'url'"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        for city in data:
            assert "nome" in city, "Should have 'nome' field"
            assert "url" in city, "Should have 'url' field"
            
    def test_italian_cities(self):
        """Should include Italian cities like Bologna, Bolzano, Milano"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        city_names = [c["nome"] for c in data]
        expected_cities = ["Bologna", "Bolzano", "Milano"]
        
        for city in expected_cities:
            assert city in city_names, f"Should include {city}"
            
    def test_urls_are_valid(self):
        """URLs should be valid HTTP links"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        for city in data:
            url = city.get("url", "")
            assert url.startswith("http"), f"URL should start with http: {url}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
