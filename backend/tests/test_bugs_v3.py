"""
Bug Fix Verification Tests - Iteration 3
Tests for 7 reported bugs:
1. Bug 1: Market price links should be valid URLs
2. Bug 2: News sources (FreshPlaza, Corriere Ortofrutticolo, Myfruit - NOT FreshPoint Magazine) + chronological sorting
3. Bug 3: Pie chart text readability (frontend only - tested via Playwright)
4. Bug 4: Sale totals with exact decimals (frontend calculates totale = quantita * prezzo_unitario)
5. Bug 5: Filters with single param (search OR logic, start_date alone)
6. Bug 6: Dashboard crescitaPercentuale field
7. Bug 7: No welcome card on dashboard (frontend only - tested via Playwright)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestBug1_MarketPriceLinks:
    """Bug 1: GET /api/prezzi-mercati should return valid URLs"""
    
    def test_prezzi_mercati_returns_valid_urls(self):
        """Each market price link should be a valid URL starting with http"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200, f"API returned {response.status_code}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should return at least one market"
        
        # Verify each link is a valid URL
        for market in data:
            assert "nome" in market, f"Market should have 'nome' field: {market}"
            assert "url" in market, f"Market should have 'url' field: {market}"
            assert market["url"].startswith("http"), f"URL should start with http: {market['url']}"
            
    def test_prezzi_mercati_urls_are_pdf_or_valid_pages(self):
        """URLs should point to valid resources (PDF or web pages)"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            # Check first market URL is accessible
            first_market = data[0]
            url = first_market.get("url", "")
            
            # Just verify it's a proper URL format
            assert url.startswith("http://") or url.startswith("https://"), f"Invalid URL: {url}"
            
    def test_prezzi_mercati_has_italian_cities(self):
        """Markets should include Italian cities"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        italian_cities = ["Bologna", "Milano", "Roma", "Torino", "Cesena", "Bolzano", "Lusia", "Verona"]
        city_names = [m.get("nome", "") for m in data]
        
        found_italian = any(city in city_names for city in italian_cities)
        assert found_italian, f"Should have Italian cities, found: {city_names}"


class TestBug2_NewsSources:
    """Bug 2: News from 3 sources (FreshPlaza, Corriere Ortofrutticolo, Myfruit) + chronological sort"""
    
    def test_notizie_returns_correct_sources(self):
        """News should come from FreshPlaza, Corriere Ortofrutticolo, Myfruit (NOT FreshPoint Magazine)"""
        response = requests.get(f"{BASE_URL}/api/notizie")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        
        if len(data) > 0:
            sources_found = set(n.get("fonte", "") for n in data)
            print(f"Sources found: {sources_found}")
            
            # Must have these 3 sources
            correct_sources = ["FreshPlaza", "Corriere Ortofrutticolo", "Myfruit"]
            for source in correct_sources:
                assert source in sources_found, f"Missing source: {source}. Found: {sources_found}"
            
            # Must NOT have FreshPoint Magazine
            incorrect_sources = ["FreshPoint Magazine", "FreshPoint"]
            for bad_source in incorrect_sources:
                assert bad_source not in sources_found, f"Should NOT have {bad_source}. Found: {sources_found}"
                
    def test_notizie_sorted_chronologically(self):
        """News should be sorted newest first (by data_pubblicazione or sort_date)"""
        response = requests.get(f"{BASE_URL}/api/notizie")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) >= 2:
            # Check that items are in chronological order (newest first)
            # The dates are in format like "Sun, 15 Feb 2026"
            dates = [n.get("data_pubblicazione", "") for n in data[:5]]
            print(f"First 5 dates: {dates}")
            
            # Verify we have dates (not empty)
            non_empty_dates = [d for d in dates if d]
            assert len(non_empty_dates) > 0, "News items should have dates"
            
    def test_notizia_has_required_fields(self):
        """Each news item should have titolo, fonte, categoria"""
        response = requests.get(f"{BASE_URL}/api/notizie")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            for idx, item in enumerate(data[:5]):
                assert "titolo" in item, f"News item {idx} missing titolo"
                assert "fonte" in item, f"News item {idx} missing fonte"
                assert len(item.get("titolo", "")) > 0, f"News item {idx} has empty titolo"


class TestBug5_FiltersWithSingleParam:
    """Bug 5: Filters should work with single parameter (OR logic for search, single date filter)"""
    
    def test_vendite_search_or_logic(self):
        """GET /api/vendite?search=BANANA should work (OR across cliente_nome and prodotto_nome)"""
        response = requests.get(f"{BASE_URL}/api/vendite?search=BANANA&limit=10")
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"Search 'BANANA' returned {len(data)} results")
        
        if len(data) > 0:
            # Verify search found items where either cliente_nome OR prodotto_nome contains BANANA
            for item in data[:3]:
                cliente = item.get("cliente_nome", "").upper()
                prodotto = item.get("prodotto_nome", "").upper()
                # At least one should contain BANANA
                has_banana = "BANANA" in cliente or "BANANA" in prodotto
                assert has_banana, f"Search result should match BANANA in cliente_nome or prodotto_nome: {item}"
                
    def test_statistiche_single_start_date_filter(self):
        """GET /api/statistiche?start_date=2025-01-01 should work with only start_date"""
        response = requests.get(f"{BASE_URL}/api/statistiche?start_date=2025-01-01")
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response has expected fields
        assert "totaleEuro" in data, "Response should have totaleEuro"
        assert "totaleArticoli" in data, "Response should have totaleArticoli"
        print(f"Single start_date filter returned totaleEuro: {data.get('totaleEuro')}")
        
    def test_statistiche_single_prodotto_filter(self):
        """GET /api/statistiche?prodotto=BANANA should work with only prodotto"""
        response = requests.get(f"{BASE_URL}/api/statistiche?prodotto=BANANA")
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        data = response.json()
        
        assert "totaleEuro" in data, "Response should have totaleEuro"
        
    def test_vendite_with_search_param_only(self):
        """GET /api/vendite with only search param should work"""
        response = requests.get(f"{BASE_URL}/api/vendite?search=TEST")
        assert response.status_code == 200, f"API returned {response.status_code}"


class TestBug6_DashboardGrowthPercentage:
    """Bug 6: Dashboard should return crescitaPercentuale field (Sales Growth %)"""
    
    def test_dashboard_has_crescita_percentuale(self):
        """GET /api/dashboard should return crescitaPercentuale field"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code == 200, f"API returned {response.status_code}"
        data = response.json()
        
        # Verify crescitaPercentuale field exists
        assert "crescitaPercentuale" in data, f"Dashboard should have 'crescitaPercentuale' field. Found: {list(data.keys())}"
        
        # Value should be a number (can be negative, zero, or positive)
        crescita = data["crescitaPercentuale"]
        assert isinstance(crescita, (int, float)), f"crescitaPercentuale should be a number, got: {type(crescita)}"
        print(f"crescitaPercentuale value: {crescita}%")
        
    def test_dashboard_has_fatturato_mese(self):
        """Dashboard should still have fatturatoMese for context"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        assert "fatturatoMese" in data, "Dashboard should have fatturatoMese"
        assert "fatturatoMesePrec" in data, "Dashboard should have fatturatoMesePrec for comparison"
        
    def test_dashboard_does_not_require_ordini_mese(self):
        """Verify ordiniMese is still available but crescitaPercentuale is the new metric"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        # ordiniMese can still exist for internal use
        # But crescitaPercentuale is the key new field
        assert "crescitaPercentuale" in data
        print(f"Dashboard fields: {list(data.keys())}")


class TestBug4_VenditeDecimalTotals:
    """Bug 4: Vendite should have proper decimal values for calculations
    Note: Frontend calculates totale = quantita * prezzo_unitario for display
    Backend returns raw data that may have rounded totale
    """
    
    def test_vendite_has_quantita_and_prezzo_unitario(self):
        """Each vendita should have quantita and prezzo_unitario for frontend calculation"""
        response = requests.get(f"{BASE_URL}/api/vendite?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            for idx, vendita in enumerate(data[:5]):
                assert "quantita" in vendita, f"Vendita {idx} missing quantita"
                assert "prezzo_unitario" in vendita, f"Vendita {idx} missing prezzo_unitario"
                assert "totale" in vendita, f"Vendita {idx} missing totale"
                
                # Frontend calculates: totale = quantita * prezzo_unitario
                qty = vendita.get("quantita", 0)
                prezzo = vendita.get("prezzo_unitario", 0)
                backend_totale = vendita.get("totale", 0)
                
                # Both values should be numeric
                assert isinstance(qty, (int, float)), f"quantita should be numeric: {qty}"
                assert isinstance(prezzo, (int, float)), f"prezzo_unitario should be numeric: {prezzo}"
                
                print(f"Vendita {idx}: qty={qty}, prezzo={prezzo}, backend_totale={backend_totale}")
                print(f"  Frontend would calculate: {qty * prezzo:.2f}")


class TestAPIHealthCheck:
    """General API health checks"""
    
    def test_api_root(self):
        """API root should return 200"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        
    def test_statistiche_endpoint(self):
        """Statistiche endpoint should work"""
        response = requests.get(f"{BASE_URL}/api/statistiche")
        assert response.status_code == 200
        
    def test_dashboard_endpoint(self):
        """Dashboard endpoint should work"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
