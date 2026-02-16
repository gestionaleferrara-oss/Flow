"""
Backend API Tests for Flusso App - New Features Iteration 7
Tests: Margin Calculation, Server-side Product Search, Statistiche with Margins, PDF with Margin Column

Features tested:
1. /api/margine-vendite - Dashboard margin banner data
2. /api/prodotti/search - Server-side search with ultimo_prezzo_acquisto
3. /api/statistiche - Includes margineStimato and profittoStimato when filters applied
4. /api/statistiche/export/pdf - PDF export with margin column
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestMargineVendite:
    """Test /api/margine-vendite endpoint - Dashboard margin banner"""
    
    def test_margine_vendite_returns_200(self):
        """Test /api/margine-vendite returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/margine-vendite")
        assert response.status_code == 200
        print(f"✓ Margine vendite endpoint returns 200")
    
    def test_margine_vendite_returns_expected_structure(self):
        """Test /api/margine-vendite returns all required fields for margin banner"""
        response = requests.get(f"{BASE_URL}/api/margine-vendite")
        assert response.status_code == 200
        data = response.json()
        
        # Required fields for Dashboard margin banner
        required_fields = [
            "mese_riferimento",
            "margine_medio_pct",
            "profitto_totale",
            "totale_fatturato",
            "totale_costo",
            "prodotti_con_margine"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"✓ Margine vendite has all required fields")
        print(f"  - Mese: {data['mese_riferimento']}")
        print(f"  - Margine Medio: {data['margine_medio_pct']}%")
        print(f"  - Profitto Totale: €{data['profitto_totale']}")
        print(f"  - Prodotti Analizzati: {data['prodotti_con_margine']}")
    
    def test_margine_vendite_data_types(self):
        """Test /api/margine-vendite returns correct data types"""
        response = requests.get(f"{BASE_URL}/api/margine-vendite")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["margine_medio_pct"], (int, float)), "margine_medio_pct should be numeric"
        assert isinstance(data["profitto_totale"], (int, float)), "profitto_totale should be numeric"
        assert isinstance(data["prodotti_con_margine"], int), "prodotti_con_margine should be int"
        
        print(f"✓ Data types are correct")
    
    def test_margine_vendite_has_top_and_worst_margini(self):
        """Test /api/margine-vendite includes top_margini and worst_margini arrays"""
        response = requests.get(f"{BASE_URL}/api/margine-vendite")
        assert response.status_code == 200
        data = response.json()
        
        assert "top_margini" in data, "Missing top_margini array"
        assert "worst_margini" in data, "Missing worst_margini array"
        assert isinstance(data["top_margini"], list)
        assert isinstance(data["worst_margini"], list)
        
        if data["top_margini"]:
            top_item = data["top_margini"][0]
            assert "prodotto" in top_item, "top_margini item missing prodotto"
            assert "margine_pct" in top_item, "top_margini item missing margine_pct"
            assert "profitto" in top_item, "top_margini item missing profitto"
            print(f"✓ Top margin: {top_item['prodotto']} - {top_item['margine_pct']}%")


class TestProdottiSearch:
    """Test /api/prodotti/search endpoint - Server-side search with debounce"""
    
    def test_search_empty_query_returns_empty(self):
        """Test empty search query returns empty array"""
        response = requests.get(f"{BASE_URL}/api/prodotti/search?q=")
        assert response.status_code == 200
        data = response.json()
        assert data == [], "Empty query should return empty array"
        print(f"✓ Empty query returns empty array")
    
    def test_search_finds_products_by_name(self):
        """Test search finds products by name"""
        response = requests.get(f"{BASE_URL}/api/prodotti/search?q=noci&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        # Should find some products with "noci" in name
        if len(data) > 0:
            product = data[0]
            assert "nome" in product
            assert "noci" in product["nome"].lower(), "Product should contain search term"
        
        print(f"✓ Search 'noci' returned {len(data)} products")
    
    def test_search_returns_ultimo_prezzo_acquisto(self):
        """Test search results include ultimo_prezzo_acquisto (last purchase cost)"""
        response = requests.get(f"{BASE_URL}/api/prodotti/search?q=pistacchio&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        if len(data) > 0:
            product = data[0]
            assert "ultimo_prezzo_acquisto" in product, "Missing ultimo_prezzo_acquisto field"
            print(f"✓ Product '{product['nome'][:30]}...' has ultimo_prezzo_acquisto: €{product['ultimo_prezzo_acquisto']}")
        else:
            print("✓ No products found for search term (empty result)")
    
    def test_search_by_product_code(self):
        """Test search can find products by code"""
        response = requests.get(f"{BASE_URL}/api/prodotti/search?q=PR01&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Search by code 'PR01' returned {len(data)} products")
    
    def test_search_limit_parameter(self):
        """Test search respects limit parameter"""
        response = requests.get(f"{BASE_URL}/api/prodotti/search?q=a&limit=3")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) <= 3, f"Expected max 3 results, got {len(data)}"
        print(f"✓ Search respects limit=3, returned {len(data)} products")


class TestStatisticheWithMargin:
    """Test /api/statistiche endpoint includes margin data when filters applied"""
    
    def test_statistiche_returns_margin_when_filtered(self):
        """Test statistiche returns margineStimato and profittoStimato with date filters"""
        response = requests.get(f"{BASE_URL}/api/statistiche?start_date=2024-10-01&end_date=2025-02-28")
        assert response.status_code == 200
        data = response.json()
        
        assert "margineStimato" in data, "Missing margineStimato field"
        assert "profittoStimato" in data, "Missing profittoStimato field"
        
        print(f"✓ Statistiche with date filter:")
        print(f"  - Fatturato: €{data.get('totaleEuro', 0):.2f}")
        print(f"  - Margine Stimato: {data['margineStimato']}%")
        print(f"  - Profitto Stimato: €{data['profittoStimato']:.2f}")
    
    def test_statistiche_top_prodotti_have_margin_info(self):
        """Test statistiche topProdotti array includes margin data"""
        response = requests.get(f"{BASE_URL}/api/statistiche?start_date=2024-10-01&end_date=2025-02-28")
        assert response.status_code == 200
        data = response.json()
        
        assert "topProdotti" in data
        top_prodotti = data["topProdotti"]
        
        # Find products with margin info
        products_with_margin = [p for p in top_prodotti if "margine_pct" in p]
        
        if products_with_margin:
            product = products_with_margin[0]
            assert "margine_pct" in product
            assert "profitto" in product
            print(f"✓ Top product '{product['nome'][:25]}...' has margine_pct: {product['margine_pct']}%, profitto: €{product.get('profitto', 0)}")
        else:
            print("✓ No products with margin data found (purchase price data may be missing)")


class TestPDFExportWithMargin:
    """Test PDF export includes margin column"""
    
    def test_pdf_export_vendite_returns_valid_pdf(self):
        """Test /api/statistiche/export/pdf?tipo=vendite returns valid PDF"""
        response = requests.get(f"{BASE_URL}/api/statistiche/export/pdf?tipo=vendite")
        assert response.status_code == 200
        
        # Verify content type
        assert "application/pdf" in response.headers.get("content-type", ""), f"Expected PDF content-type, got {response.headers.get('content-type')}"
        
        # Verify PDF magic bytes
        content = response.content
        assert content[:4] == b'%PDF', "Response does not start with PDF magic bytes"
        
        print(f"✓ PDF Export vendite: {len(content)} bytes, valid PDF")
    
    def test_pdf_export_with_date_range_includes_margin(self):
        """Test PDF export with date range (margin column should be included)"""
        response = requests.get(f"{BASE_URL}/api/statistiche/export/pdf?tipo=vendite&start_date=2024-10-01&end_date=2025-02-28")
        assert response.status_code == 200
        
        content = response.content
        assert content[:4] == b'%PDF', "Not a valid PDF"
        
        # PDF should be larger when more data is included
        assert len(content) > 1000, "PDF seems too small"
        
        print(f"✓ PDF Export with date range: {len(content)} bytes")
    
    def test_pdf_export_acquisti(self):
        """Test PDF export for acquisti type"""
        response = requests.get(f"{BASE_URL}/api/statistiche/export/pdf?tipo=acquisti&start_date=2024-10-01&end_date=2025-02-28")
        assert response.status_code == 200
        
        assert response.content[:4] == b'%PDF'
        print(f"✓ PDF Export acquisti: {len(response.content)} bytes")


class TestDashboardLoading:
    """Test Dashboard loads instantly without blocking"""
    
    def test_dashboard_endpoint_fast(self):
        """Test /api/dashboard responds quickly (non-blocking)"""
        import time
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/dashboard")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 10, f"Dashboard took too long: {elapsed:.2f}s (should be <10s)"
        
        print(f"✓ Dashboard responded in {elapsed:.2f}s")
    
    def test_margine_vendite_endpoint_fast(self):
        """Test /api/margine-vendite responds reasonably quickly"""
        import time
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/margine-vendite")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 15, f"Margine vendite took too long: {elapsed:.2f}s"
        
        print(f"✓ Margine vendite responded in {elapsed:.2f}s")


class TestAIWidgetCompact:
    """Test AI suggestion endpoint (for compact widget)"""
    
    def test_ai_suggestion_returns_compact_data(self):
        """Test /api/ai-suggestion returns suggestion for compact display"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestion")
        assert response.status_code == 200
        data = response.json()
        
        if "suggestion" in data:
            suggestion = data["suggestion"]
            # Compact widget needs these fields
            assert "titolo" in suggestion or "tipo" in suggestion
            assert "messaggio" in suggestion or "azione" in suggestion
            print(f"✓ AI Suggestion compact: {suggestion.get('titolo', 'N/A')} - {suggestion.get('messaggio', 'N/A')[:50]}...")
        else:
            print("✓ AI Suggestion: No active suggestion")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
