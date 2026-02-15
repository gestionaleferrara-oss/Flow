"""
Backend API Tests for Agro Stats V2 Application
Tests for: Dashboard, Statistiche, Notizie, Prezzi Mercati, Meteo, Vendite, Clienti, Fornitori, Prodotti
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAPIRoot:
    """Test API root and health endpoints"""
    
    def test_api_root(self):
        """Test API root returns welcome message"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Gestio" in data["message"]


class TestDashboard:
    """Test dashboard endpoint"""
    
    def test_dashboard_returns_kpi_data(self):
        """Dashboard should return KPI cards data: Fatturato, Ordini, Nuovi Clienti, Da Riordinare"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required KPI fields exist
        assert "fatturatoMese" in data
        assert "ordiniMese" in data
        assert "nuoviClienti" in data
        assert "prodottiOrdinare" in data
        
        # Verify values are non-negative
        assert data["fatturatoMese"] >= 0
        assert data["ordiniMese"] >= 0
        assert data["nuoviClienti"] >= 0
        assert data["prodottiOrdinare"] >= 0


class TestStatistiche:
    """Test statistiche endpoint - focuses on topProdotti returning totale_euro field"""
    
    def test_statistiche_returns_data(self):
        """Statistiche endpoint should return sales data"""
        response = requests.get(f"{BASE_URL}/api/statistiche")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields exist
        assert "totaleEuro" in data
        assert "totaleArticoli" in data
        assert "clientiAttivi" in data
        assert "fatturatoMese" in data
        assert "topProdotti" in data
        assert "topClienti" in data
        
    def test_top_prodotti_has_totale_euro_field(self):
        """topProdotti should have totale_euro field (not quantita) for revenue-based ranking"""
        response = requests.get(f"{BASE_URL}/api/statistiche")
        assert response.status_code == 200
        data = response.json()
        
        top_prodotti = data.get("topProdotti", [])
        if len(top_prodotti) > 0:
            # Verify totale_euro field exists (not quantita)
            first_product = top_prodotti[0]
            assert "totale_euro" in first_product, "topProdotti should have 'totale_euro' field"
            assert "nome" in first_product
            
            # Verify totale_euro is positive (absolute value used)
            assert first_product["totale_euro"] >= 0, "totale_euro should be non-negative"
            
    def test_statistiche_all_values_positive(self):
        """All statistiche values should be positive (abs applied)"""
        response = requests.get(f"{BASE_URL}/api/statistiche")
        assert response.status_code == 200
        data = response.json()
        
        assert data["totaleEuro"] >= 0, "totaleEuro should be positive"
        assert data["totaleArticoli"] >= 0, "totaleArticoli should be positive"
        assert data["fatturatoMese"] >= 0, "fatturatoMese should be positive"
        
    def test_statistiche_filters_work(self):
        """Test filters: prodotto, cliente, start_date, end_date"""
        # Test date filter
        response = requests.get(f"{BASE_URL}/api/statistiche?start_date=2025-01-01&end_date=2025-12-31")
        assert response.status_code == 200
        
        # Test prodotto filter
        response = requests.get(f"{BASE_URL}/api/statistiche?prodotto=test")
        assert response.status_code == 200


class TestNotizie:
    """Test notizie endpoint - should return news from correct sources"""
    
    def test_notizie_returns_list(self):
        """Notizie endpoint should return a list of news articles"""
        response = requests.get(f"{BASE_URL}/api/notizie")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_notizie_sources_are_correct(self):
        """News should come from FreshPlaza, Corriere Ortofrutticolo, FreshPoint Magazine only"""
        response = requests.get(f"{BASE_URL}/api/notizie")
        assert response.status_code == 200
        data = response.json()
        
        allowed_sources = ["FreshPlaza", "Corriere Ortofrutticolo", "FreshPoint Magazine"]
        invalid_sources = ["ANSA", "Il Sole 24 Ore", "Reuters"]
        
        if len(data) > 0:
            sources_found = set(n.get("fonte", "") for n in data)
            
            # Verify at least some allowed sources present
            assert len(sources_found.intersection(allowed_sources)) > 0, f"Should have news from ortofrutta sources, found: {sources_found}"
            
            # Verify no invalid sources
            for invalid in invalid_sources:
                assert invalid not in sources_found, f"Should NOT have news from {invalid}"
                
    def test_notizia_has_required_fields(self):
        """Each news item should have titolo, fonte, categoria fields"""
        response = requests.get(f"{BASE_URL}/api/notizie")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            news_item = data[0]
            assert "titolo" in news_item
            assert "fonte" in news_item
            assert "categoria" in news_item


class TestPrezziMercati:
    """Test prezzi-mercati endpoint - should return dynamic market prices from FreshPlaza"""
    
    def test_prezzi_mercati_returns_list(self):
        """Prezzi mercati should return a list of market price links"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Should return at least one market"
        
    def test_prezzi_mercati_has_nome_and_url(self):
        """Each market should have nome (city name) and url"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            market = data[0]
            assert "nome" in market, "Market should have 'nome' field"
            assert "url" in market, "Market should have 'url' field"
            assert len(market["nome"]) > 0
            assert market["url"].startswith("http")
            
    def test_prezzi_mercati_has_italian_cities(self):
        """Markets should be Italian cities"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            city_names = [m.get("nome", "") for m in data]
            # Check if at least one Italian city is present
            italian_cities = ["Bologna", "Milano", "Roma", "Torino", "Verona", "Cesena", "Bolzano"]
            found_italian = any(city in city_names for city in italian_cities)
            assert found_italian, f"Should have Italian cities, found: {city_names}"


class TestMeteo:
    """Test meteo endpoint - should return weather for Bologna"""
    
    def test_meteo_returns_data(self):
        """Meteo endpoint should return weather data"""
        response = requests.get(f"{BASE_URL}/api/meteo")
        assert response.status_code == 200
        data = response.json()
        
        # Verify weather data structure
        assert "current_weather" in data or "error" in data
        
    def test_meteo_has_current_weather(self):
        """Weather response should include current weather"""
        response = requests.get(f"{BASE_URL}/api/meteo")
        assert response.status_code == 200
        data = response.json()
        
        if "current_weather" in data:
            current = data["current_weather"]
            assert "temperature" in current
            assert "weathercode" in current


class TestVendite:
    """Test vendite endpoint"""
    
    def test_vendite_returns_list(self):
        """Vendite endpoint should return a list"""
        response = requests.get(f"{BASE_URL}/api/vendite?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_vendite_has_required_fields(self):
        """Each vendita should have data, cliente_nome, prodotto_nome, totale"""
        response = requests.get(f"{BASE_URL}/api/vendite?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            vendita = data[0]
            assert "data" in vendita
            assert "cliente_nome" in vendita
            assert "prodotto_nome" in vendita
            assert "totale" in vendita


class TestClienti:
    """Test clienti endpoint"""
    
    def test_clienti_returns_list(self):
        """Clienti endpoint should return a list"""
        response = requests.get(f"{BASE_URL}/api/clienti?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_clienti_search_works(self):
        """Search parameter should filter results"""
        response = requests.get(f"{BASE_URL}/api/clienti?search=test&limit=10")
        assert response.status_code == 200


class TestFornitori:
    """Test fornitori endpoint"""
    
    def test_fornitori_returns_list(self):
        """Fornitori endpoint should return a list"""
        response = requests.get(f"{BASE_URL}/api/fornitori?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestProdotti:
    """Test prodotti (magazzino) endpoint"""
    
    def test_prodotti_returns_list(self):
        """Prodotti endpoint should return a list"""
        response = requests.get(f"{BASE_URL}/api/prodotti?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_prodotti_stats(self):
        """Prodotti stats should return ordinare_count and scadenza_count"""
        response = requests.get(f"{BASE_URL}/api/prodotti/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "ordinare_count" in data
        assert "scadenza_count" in data
        assert "total" in data


class TestStatisticheLists:
    """Test statistiche/lists endpoint for filter dropdowns"""
    
    def test_statistiche_lists_returns_prodotti_and_clienti(self):
        """Should return lists of prodotti and clienti for filter dropdowns"""
        response = requests.get(f"{BASE_URL}/api/statistiche/lists")
        assert response.status_code == 200
        data = response.json()
        
        assert "prodotti" in data
        assert "clienti" in data
        assert isinstance(data["prodotti"], list)
        assert isinstance(data["clienti"], list)


class TestUploadCSV:
    """Test CSV upload endpoint accepts both CSV and XLSX"""
    
    def test_upload_rejects_invalid_files(self):
        """Upload should reject non-CSV/XLSX files"""
        # Create a fake .txt file
        files = {"file": ("test.txt", b"test content", "text/plain")}
        response = requests.post(f"{BASE_URL}/api/upload-csv", files=files)
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
