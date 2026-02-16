"""
Test new features implemented:
1. GET /api/sales-insight - Dynamic sales insights
2. GET /api/trends-vendite - Trends with parameters (periodo, ordina_per, limit)
3. GET /api/prezzi-mercati - Market price links (6 links to ISMEA and CCIAA)

Testing Agent: T1 - Iteration 6
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSalesInsight:
    """Test /api/sales-insight endpoint"""
    
    def test_sales_insight_returns_200(self):
        """Should return 200 status"""
        response = requests.get(f"{BASE_URL}/api/sales-insight")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ GET /api/sales-insight returns 200")
    
    def test_sales_insight_response_structure(self):
        """Should return proper structure with mese_riferimento and insights"""
        response = requests.get(f"{BASE_URL}/api/sales-insight")
        assert response.status_code == 200
        data = response.json()
        
        # Check required top-level fields
        assert "mese_riferimento" in data, "Missing mese_riferimento field"
        assert "insights" in data, "Missing insights field"
        assert isinstance(data["insights"], list), "insights should be a list"
        print(f"✓ Response has mese_riferimento: {data['mese_riferimento']}")
        print(f"✓ Response has {len(data['insights'])} insights")
    
    def test_sales_insight_fields(self):
        """Each insight should have: tipo, icona, titolo, valore, dettaglio, colore"""
        response = requests.get(f"{BASE_URL}/api/sales-insight")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["tipo", "icona", "titolo", "valore", "dettaglio", "colore"]
        
        if data["insights"]:
            for i, insight in enumerate(data["insights"]):
                for field in required_fields:
                    assert field in insight, f"Insight {i} missing field: {field}"
                print(f"  ✓ Insight {insight['tipo']}: {insight['titolo']} = {insight['valore']}")
        
        print(f"✓ All insights have required fields: {required_fields}")


class TestTrendsVendite:
    """Test /api/trends-vendite endpoint with parameters"""
    
    def test_trends_vendite_default(self):
        """Should work with default parameters"""
        response = requests.get(f"{BASE_URL}/api/trends-vendite")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "top_prodotti" in data, "Missing top_prodotti field"
        assert "periodo" in data, "Missing periodo field"
        assert "periodo_label" in data, "Missing periodo_label field"
        print(f"✓ GET /api/trends-vendite returns 200 with {len(data.get('top_prodotti', []))} products")
    
    def test_trends_vendite_with_periodo_2w(self):
        """Should accept periodo=2w parameter"""
        response = requests.get(f"{BASE_URL}/api/trends-vendite", params={
            "periodo": "2w",
            "ordina_per": "interest",
            "limit": 5
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("periodo") == "2w", f"Expected periodo=2w, got {data.get('periodo')}"
        assert "periodo_attuale" in data, "Missing periodo_attuale"
        assert "periodo_precedente" in data, "Missing periodo_precedente"
        print(f"✓ periodo=2w works: {data.get('periodo_label')}")
        print(f"  Period: {data.get('periodo_attuale')} vs {data.get('periodo_precedente')}")
    
    def test_trends_vendite_with_periodo_1m(self):
        """Should accept periodo=1m parameter"""
        response = requests.get(f"{BASE_URL}/api/trends-vendite", params={
            "periodo": "1m",
            "ordina_per": "fatturato",
            "limit": 20
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("periodo") == "1m", f"Expected periodo=1m, got {data.get('periodo')}"
        assert len(data.get("top_prodotti", [])) <= 20, "Should respect limit=20"
        print(f"✓ periodo=1m works: {len(data.get('top_prodotti', []))} products returned")
    
    def test_trends_vendite_ordina_per_fatturato(self):
        """Should sort by fatturato when ordina_per=fatturato"""
        response = requests.get(f"{BASE_URL}/api/trends-vendite", params={
            "ordina_per": "fatturato",
            "limit": 10
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("ordina_per") == "fatturato", f"Expected ordina_per=fatturato"
        
        # Verify sorting - each product should have >= fatturato than next
        products = data.get("top_prodotti", [])
        if len(products) > 1:
            for i in range(len(products) - 1):
                assert products[i]["fatturato_2w"] >= products[i+1]["fatturato_2w"], \
                    f"Products not sorted by fatturato at index {i}"
        print(f"✓ ordina_per=fatturato works - products sorted by revenue")
    
    def test_trends_vendite_limit_5(self):
        """Should return max 5 items when limit=5"""
        response = requests.get(f"{BASE_URL}/api/trends-vendite", params={"limit": 5})
        assert response.status_code == 200
        data = response.json()
        
        assert len(data.get("top_prodotti", [])) <= 5, "Should return max 5 products"
        print(f"✓ limit=5 returns {len(data.get('top_prodotti', []))} products")
    
    def test_trends_vendite_limit_20(self):
        """Should return max 20 items when limit=20 (expanded mode)"""
        response = requests.get(f"{BASE_URL}/api/trends-vendite", params={"limit": 20})
        assert response.status_code == 200
        data = response.json()
        
        # Should respect limit but not exceed total products
        total = data.get("totale_prodotti", 0)
        returned = len(data.get("top_prodotti", []))
        assert returned <= 20, f"Should return max 20 products, got {returned}"
        assert returned <= total, f"Returned {returned} but total is {total}"
        print(f"✓ limit=20 returns {returned} products (total: {total})")
    
    def test_trends_vendite_product_fields(self):
        """Each product should have required fields"""
        response = requests.get(f"{BASE_URL}/api/trends-vendite", params={"limit": 5})
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "prodotto", "quantita_2w", "fatturato_2w",
            "variazione_qty_pct", "variazione_fatturato_pct",
            "quota_fatturato_pct", "trend"
        ]
        
        for product in data.get("top_prodotti", []):
            for field in required_fields:
                assert field in product, f"Missing field {field} in product"
        
        print(f"✓ All products have required fields")


class TestPrezziMercati:
    """Test /api/prezzi-mercati endpoint - market price links"""
    
    def test_prezzi_mercati_returns_200(self):
        """Should return 200 status"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ GET /api/prezzi-mercati returns 200")
    
    def test_prezzi_mercati_returns_6_links(self):
        """Should return exactly 6 market price links"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) == 6, f"Expected 6 links, got {len(data)}"
        print(f"✓ Returns exactly 6 market price links")
    
    def test_prezzi_mercati_link_structure(self):
        """Each link should have nome and url fields"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        for i, link in enumerate(data):
            assert "nome" in link, f"Link {i} missing 'nome' field"
            assert "url" in link, f"Link {i} missing 'url' field"
            assert link["url"].startswith("http"), f"Link {i} URL should start with http"
            print(f"  ✓ {link['nome']}: {link['url'][:50]}...")
        
        print(f"✓ All links have nome and url fields")
    
    def test_prezzi_mercati_ismea_links(self):
        """Should include ISMEA links"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        ismea_links = [l for l in data if "ISMEA" in l.get("nome", "").upper()]
        assert len(ismea_links) >= 2, f"Expected at least 2 ISMEA links, got {len(ismea_links)}"
        
        for link in ismea_links:
            assert "ismeamercati.it" in link["url"], f"ISMEA link should point to ismeamercati.it"
        
        print(f"✓ Found {len(ismea_links)} ISMEA links")
    
    def test_prezzi_mercati_cciaa_links(self):
        """Should include CCIAA (Camera di Commercio) links"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        cciaa_links = [l for l in data if "CCIAA" in l.get("nome", "").upper()]
        assert len(cciaa_links) >= 4, f"Expected at least 4 CCIAA links, got {len(cciaa_links)}"
        
        for link in cciaa_links:
            assert "camcom" in link["url"], f"CCIAA link should point to camcom domain"
        
        print(f"✓ Found {len(cciaa_links)} CCIAA links")


class TestHealthAndBasicEndpoints:
    """Basic health checks"""
    
    def test_api_root(self):
        """Should return 200 for API root"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        print(f"✓ API root is accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
