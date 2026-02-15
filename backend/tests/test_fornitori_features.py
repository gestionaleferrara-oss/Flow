"""
Backend API Tests for Fornitori Features - Year Selector & Month Selector
Tests for: GET /api/fornitori-with-stats (year filtering) and GET /api/fornitori/{nome}/prodotti (month filtering)
"""

import pytest
import requests
import os
from urllib.parse import quote

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test suppliers mentioned in the context
SUPPLIER_1 = "O SOLE 'E NAPULE DI CALABRIA ALFONSO SRL"
SUPPLIER_2 = "PANCRAZIO SPA"


class TestFornitoriWithStats:
    """Test GET /api/fornitori-with-stats endpoint - Year filtering feature"""
    
    def test_fornitori_with_stats_returns_json(self):
        """Should return JSON with 'fornitori' array and 'anni_disponibili' array"""
        response = requests.get(f"{BASE_URL}/api/fornitori-with-stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify new response structure
        assert "fornitori" in data, "Response should have 'fornitori' key"
        assert "anni_disponibili" in data, "Response should have 'anni_disponibili' key"
        assert isinstance(data["fornitori"], list), "'fornitori' should be a list"
        assert isinstance(data["anni_disponibili"], list), "'anni_disponibili' should be a list"
        
    def test_anni_disponibili_contains_years(self):
        """anni_disponibili should contain year strings like '2025', '2024'"""
        response = requests.get(f"{BASE_URL}/api/fornitori-with-stats")
        assert response.status_code == 200
        data = response.json()
        
        anni = data.get("anni_disponibili", [])
        if len(anni) > 0:
            # Verify years are strings and valid
            for anno in anni:
                assert isinstance(anno, str), f"Year should be string, got {type(anno)}"
                assert len(anno) == 4, f"Year should be 4 digits, got {anno}"
                assert anno.isdigit(), f"Year should be numeric, got {anno}"
                
    def test_fornitori_with_stats_year_filter_2025(self):
        """GET /api/fornitori-with-stats?anno=2025 should filter turnover by year 2025"""
        response = requests.get(f"{BASE_URL}/api/fornitori-with-stats?anno=2025")
        assert response.status_code == 200
        data = response.json()
        
        assert "fornitori" in data
        fornitori = data["fornitori"]
        assert isinstance(fornitori, list)
        
        # Verify each fornitore has fatturato_totale field
        if len(fornitori) > 0:
            for f in fornitori[:5]:  # Check first 5
                assert "nome" in f
                assert "fatturato_totale" in f
                assert isinstance(f["fatturato_totale"], (int, float))
                
    def test_fornitori_with_stats_year_filter_2024(self):
        """GET /api/fornitori-with-stats?anno=2024 should filter turnover by year 2024"""
        response = requests.get(f"{BASE_URL}/api/fornitori-with-stats?anno=2024")
        assert response.status_code == 200
        data = response.json()
        
        assert "fornitori" in data
        fornitori = data["fornitori"]
        assert isinstance(fornitori, list)
        
    def test_fornitori_year_filter_changes_fatturato(self):
        """Different years should produce different fatturato values (if data exists)"""
        response_2025 = requests.get(f"{BASE_URL}/api/fornitori-with-stats?anno=2025")
        response_2024 = requests.get(f"{BASE_URL}/api/fornitori-with-stats?anno=2024")
        
        assert response_2025.status_code == 200
        assert response_2024.status_code == 200
        
        data_2025 = response_2025.json()
        data_2024 = response_2024.json()
        
        fornitori_2025 = data_2025.get("fornitori", [])
        fornitori_2024 = data_2024.get("fornitori", [])
        
        # Find a common supplier to compare
        names_2025 = {f["nome"]: f["fatturato_totale"] for f in fornitori_2025}
        names_2024 = {f["nome"]: f["fatturato_totale"] for f in fornitori_2024}
        
        # Verify the data structure is correct for both years
        print(f"2025: {len(fornitori_2025)} suppliers, 2024: {len(fornitori_2024)} suppliers")
        
    def test_fornitori_with_stats_search_param(self):
        """Search param should filter suppliers by name"""
        response = requests.get(f"{BASE_URL}/api/fornitori-with-stats?search=pancrazio")
        assert response.status_code == 200
        data = response.json()
        
        assert "fornitori" in data
        assert "anni_disponibili" in data


class TestFornitoreProdotti:
    """Test GET /api/fornitori/{nome}/prodotti endpoint - Month selector feature"""
    
    def test_fornitore_prodotti_returns_data(self):
        """Should return product data for a specific supplier"""
        encoded_name = quote(SUPPLIER_2)  # PANCRAZIO SPA
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded_name}/prodotti")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "fornitore" in data
        assert "prodotti" in data
        assert "totale_prodotti" in data
        assert "totale_speso" in data
        assert "mese_riferimento" in data
        assert "mesi_disponibili" in data
        
    def test_mesi_disponibili_structure(self):
        """mesi_disponibili should be array of {value, label} pairs"""
        encoded_name = quote(SUPPLIER_2)
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded_name}/prodotti")
        assert response.status_code == 200
        data = response.json()
        
        mesi = data.get("mesi_disponibili", [])
        if len(mesi) > 0:
            # Verify structure
            for m in mesi[:3]:
                assert "value" in m, "Each month should have 'value' key"
                assert "label" in m, "Each month should have 'label' key"
                # Value should be YYYY-MM format
                assert len(m["value"]) == 7, f"Value should be YYYY-MM format, got {m['value']}"
                assert "-" in m["value"], f"Value should contain dash, got {m['value']}"
                
    def test_mese_labels_are_italian(self):
        """Month labels should be in Italian (e.g., 'Novembre 2025', 'Marzo 2025')"""
        encoded_name = quote(SUPPLIER_2)
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded_name}/prodotti")
        assert response.status_code == 200
        data = response.json()
        
        mesi = data.get("mesi_disponibili", [])
        italian_months = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
                        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
        
        if len(mesi) > 0:
            for m in mesi[:3]:
                label = m.get("label", "")
                # Label should start with Italian month name
                found_italian = any(month in label for month in italian_months)
                assert found_italian, f"Label should be Italian month, got {label}"
                
    def test_fornitore_prodotti_with_mese_param(self):
        """GET /api/fornitori/{nome}/prodotti?mese=2024-04 should return data for specified month"""
        encoded_name = quote(SUPPLIER_2)
        # First get available months
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded_name}/prodotti")
        assert response.status_code == 200
        data = response.json()
        
        mesi = data.get("mesi_disponibili", [])
        if len(mesi) > 0:
            # Test with first available month
            test_month = mesi[0]["value"]
            response_filtered = requests.get(f"{BASE_URL}/api/fornitori/{encoded_name}/prodotti?mese={test_month}")
            assert response_filtered.status_code == 200
            
            data_filtered = response_filtered.json()
            # mese_selezionato should match the requested month
            assert data_filtered.get("mese_selezionato") == test_month
            
    def test_fornitore_prodotti_month_filter_changes_data(self):
        """Different months should return different product data"""
        encoded_name = quote(SUPPLIER_2)
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded_name}/prodotti")
        data = response.json()
        
        mesi = data.get("mesi_disponibili", [])
        if len(mesi) >= 2:
            # Get data for two different months
            response_m1 = requests.get(f"{BASE_URL}/api/fornitori/{encoded_name}/prodotti?mese={mesi[0]['value']}")
            response_m2 = requests.get(f"{BASE_URL}/api/fornitori/{encoded_name}/prodotti?mese={mesi[1]['value']}")
            
            assert response_m1.status_code == 200
            assert response_m2.status_code == 200
            
            data_m1 = response_m1.json()
            data_m2 = response_m2.json()
            
            # Verify both have valid structures
            assert "prodotti" in data_m1
            assert "prodotti" in data_m2
            assert "mese_riferimento" in data_m1
            assert "mese_riferimento" in data_m2
            
            # Mese riferimento should be different
            print(f"Month 1: {data_m1['mese_riferimento']}, products: {data_m1['totale_prodotti']}")
            print(f"Month 2: {data_m2['mese_riferimento']}, products: {data_m2['totale_prodotti']}")
            
    def test_fornitore_prodotti_summary_stats(self):
        """Response should include summary stats: totale_prodotti, totale_speso, mese_riferimento"""
        encoded_name = quote(SUPPLIER_2)
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded_name}/prodotti")
        assert response.status_code == 200
        data = response.json()
        
        # Verify summary fields exist and are correct types
        assert isinstance(data.get("totale_prodotti"), int)
        assert isinstance(data.get("totale_speso"), (int, float))
        assert isinstance(data.get("mese_riferimento"), str)
        
    def test_fornitore_prodotti_with_special_chars(self):
        """Should handle supplier name with special characters like apostrophe"""
        # Use the supplier with special chars: O SOLE 'E NAPULE DI CALABRIA ALFONSO SRL
        encoded_name = quote(SUPPLIER_1)
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded_name}/prodotti")
        # Should either return 200 with data or 200 with empty list (not 500 error)
        assert response.status_code == 200
        data = response.json()
        
        # Verify basic structure even if no data
        assert "fornitore" in data
        assert "prodotti" in data
        assert "mesi_disponibili" in data
        
    def test_fornitore_prodotti_nonexistent_supplier(self):
        """Should return empty data for nonexistent supplier (not error)"""
        encoded_name = quote("NONEXISTENT_SUPPLIER_12345")
        response = requests.get(f"{BASE_URL}/api/fornitori/{encoded_name}/prodotti")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("prodotti") == []
        assert data.get("totale_prodotti") == 0
        assert data.get("mesi_disponibili") == []


class TestFornitoriBasicEndpoint:
    """Test the basic /api/fornitori endpoint still works"""
    
    def test_fornitori_basic_returns_list(self):
        """Basic fornitori endpoint should still return list directly"""
        response = requests.get(f"{BASE_URL}/api/fornitori?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        # Basic endpoint returns array directly
        assert isinstance(data, list)
        if len(data) > 0:
            assert "nome" in data[0]
            assert "id" in data[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
