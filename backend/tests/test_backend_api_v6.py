"""
Backend API Tests for Flusso App - Testing refactored modular structure
Tests: Dashboard, Clienti, Prodotti, Vendite, Statistiche, PDF Export, Alerts, Sales Insight, Trends
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthAndRoot:
    """Test API root and health"""
    
    def test_api_root(self):
        """Test /api/ returns valid response"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ API root responds: {data['message']}")


class TestDashboard:
    """Dashboard endpoint tests - P0 KPI cards verification"""
    
    def test_dashboard_returns_required_fields(self):
        """Test /api/dashboard returns fatturatoMese, ordiniMese, nuoviClienti"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        # Verify all 4 KPI required fields
        assert "fatturatoMese" in data, "Missing fatturatoMese"
        assert "ordiniMese" in data, "Missing ordiniMese"
        assert "nuoviClienti" in data, "Missing nuoviClienti - this is for Clienti Mese KPI"
        
        # Verify data types
        assert isinstance(data["fatturatoMese"], (int, float)), "fatturatoMese should be numeric"
        assert isinstance(data["ordiniMese"], int), "ordiniMese should be integer"
        assert isinstance(data["nuoviClienti"], int), "nuoviClienti should be integer"
        
        print(f"✓ Dashboard KPIs: Fatturato={data['fatturatoMese']}, Ordini={data['ordiniMese']}, Clienti={data['nuoviClienti']}")
    
    def test_dashboard_has_growth_percentage(self):
        """Test dashboard includes crescitaPercentuale for trend indicator"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        assert "crescitaPercentuale" in data
        assert isinstance(data["crescitaPercentuale"], (int, float))
        print(f"✓ Growth percentage: {data['crescitaPercentuale']}%")


class TestAlerts:
    """Alerts endpoint tests - For Alert KPI card"""
    
    def test_alerts_returns_expected_structure(self):
        """Test /api/alerts returns prodottiSottoScorta and clientiInattivi"""
        response = requests.get(f"{BASE_URL}/api/alerts")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required alert arrays
        assert "prodottiSottoScorta" in data, "Missing prodottiSottoScorta"
        assert "clientiInattivi" in data, "Missing clientiInattivi"
        
        assert isinstance(data["prodottiSottoScorta"], list)
        assert isinstance(data["clientiInattivi"], list)
        
        total_alerts = len(data.get("prodottiSottoScorta", [])) + len(data.get("clientiInattivi", [])) + len(data.get("prodottiInEsaurimento", []))
        print(f"✓ Alerts: {total_alerts} total (SottoScorta={len(data['prodottiSottoScorta'])}, Inattivi={len(data['clientiInattivi'])})")


class TestSalesInsight:
    """Sales Insight tests - P0 insight text visibility verification"""
    
    def test_sales_insight_returns_insights(self):
        """Test /api/sales-insight returns insights array with proper structure"""
        response = requests.get(f"{BASE_URL}/api/sales-insight")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "insights" in data, "Missing insights array"
        assert "mese_riferimento" in data, "Missing mese_riferimento"
        
        if data["insights"]:
            insight = data["insights"][0]
            # Each insight should have text fields that will be visible
            assert "titolo" in insight, "Insight missing titolo"
            assert "valore" in insight, "Insight missing valore"
            assert "dettaglio" in insight, "Insight missing dettaglio - this is the description text"
            assert "colore" in insight, "Insight missing colore"
            print(f"✓ Sales Insight: {len(data['insights'])} insights, Month: {data['mese_riferimento']}")
            print(f"  First insight: {insight['titolo']} - {insight['dettaglio'][:50]}...")
        else:
            print("✓ Sales Insight: No insights (empty data)")


class TestTrendsVendite:
    """Trends Vendite tests - P0 trend selectors verification"""
    
    def test_trends_vendite_default(self):
        """Test /api/trends-vendite returns top_prodotti array"""
        response = requests.get(f"{BASE_URL}/api/trends-vendite?limite=5")
        assert response.status_code == 200
        data = response.json()
        
        assert "top_prodotti" in data, "Missing top_prodotti"
        assert isinstance(data["top_prodotti"], list)
        assert "periodo" in data
        
        print(f"✓ Trends default: {len(data['top_prodotti'])} products, periodo={data['periodo']}")
    
    def test_trends_vendite_periodo_1week(self):
        """Test trends with 1 week periodo selector"""
        response = requests.get(f"{BASE_URL}/api/trends-vendite?periodo=1w&ordina_per=interest&limite=5")
        assert response.status_code == 200
        data = response.json()
        assert data["periodo"] == "1w"
        print(f"✓ Trends 1w: periodo_label={data.get('periodo_label', 'N/A')}")
    
    def test_trends_vendite_periodo_2weeks(self):
        """Test trends with 2 weeks periodo selector"""
        response = requests.get(f"{BASE_URL}/api/trends-vendite?periodo=2w&ordina_per=qty&limite=5")
        assert response.status_code == 200
        data = response.json()
        assert data["periodo"] == "2w"
        print(f"✓ Trends 2w: {len(data['top_prodotti'])} products by qty")
    
    def test_trends_vendite_periodo_1month(self):
        """Test trends with 1 month periodo selector"""
        response = requests.get(f"{BASE_URL}/api/trends-vendite?periodo=1m&ordina_per=revenue&limite=5")
        assert response.status_code == 200
        data = response.json()
        assert data["periodo"] == "1m"
        print(f"✓ Trends 1m: {len(data['top_prodotti'])} products by revenue")


class TestClienti:
    """Clienti module tests"""
    
    def test_get_clienti(self):
        """Test /api/clienti returns array of clients"""
        response = requests.get(f"{BASE_URL}/api/clienti")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Clienti: {len(data)} clients returned")
        
        if data:
            client = data[0]
            assert "nome" in client or "id" in client


class TestProdotti:
    """Prodotti module tests"""
    
    def test_get_prodotti(self):
        """Test /api/prodotti returns array of products"""
        response = requests.get(f"{BASE_URL}/api/prodotti")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Prodotti: {len(data)} products returned")


class TestVendite:
    """Vendite module tests"""
    
    def test_get_vendite(self):
        """Test /api/vendite returns array of sales"""
        response = requests.get(f"{BASE_URL}/api/vendite?limit=20")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Vendite: {len(data)} sales returned")
        
        if data:
            sale = data[0]
            # Verify key fields exist
            assert "data" in sale or "totale" in sale or "cliente_nome" in sale


class TestStatistiche:
    """Statistiche module tests"""
    
    def test_get_statistiche(self):
        """Test /api/statistiche returns proper keys"""
        response = requests.get(f"{BASE_URL}/api/statistiche")
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected keys
        expected_keys = ["totaleEuro", "totaleArticoli", "clientiAttivi", "fatturatoMese", "venditeMensili", "topClienti", "topProdotti"]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"
        
        print(f"✓ Statistiche: totaleEuro={data['totaleEuro']}, clientiAttivi={data['clientiAttivi']}")
    
    def test_get_statistiche_acquisti(self):
        """Test /api/statistiche/acquisti returns purchase statistics"""
        response = requests.get(f"{BASE_URL}/api/statistiche/acquisti")
        assert response.status_code == 200
        data = response.json()
        
        assert "totaleEuro" in data
        assert "fornitoriAttivi" in data
        print(f"✓ Statistiche Acquisti: totaleEuro={data['totaleEuro']}")


class TestPDFExport:
    """PDF Export tests - P2 new feature"""
    
    def test_pdf_export_vendite(self):
        """Test /api/statistiche/export/pdf?tipo=vendite returns valid PDF"""
        response = requests.get(f"{BASE_URL}/api/statistiche/export/pdf?tipo=vendite")
        assert response.status_code == 200
        
        # Verify it's a PDF
        assert response.headers.get("content-type") == "application/pdf", f"Expected PDF, got {response.headers.get('content-type')}"
        
        # Verify PDF magic bytes
        content = response.content
        assert content[:4] == b'%PDF', "Response does not start with PDF magic bytes"
        
        print(f"✓ PDF Export vendite: {len(content)} bytes, valid PDF")
    
    def test_pdf_export_acquisti(self):
        """Test /api/statistiche/export/pdf?tipo=acquisti returns valid PDF"""
        response = requests.get(f"{BASE_URL}/api/statistiche/export/pdf?tipo=acquisti")
        assert response.status_code == 200
        
        assert response.headers.get("content-type") == "application/pdf"
        content = response.content
        assert content[:4] == b'%PDF'
        
        print(f"✓ PDF Export acquisti: {len(content)} bytes, valid PDF")
    
    def test_pdf_export_with_date_range(self):
        """Test PDF export with custom date range"""
        response = requests.get(f"{BASE_URL}/api/statistiche/export/pdf?tipo=vendite&start_date=2024-07-01&end_date=2024-12-31")
        assert response.status_code == 200
        assert response.content[:4] == b'%PDF'
        print(f"✓ PDF Export with dates: {len(response.content)} bytes")


class TestNews:
    """News and Market Prices tests"""
    
    def test_get_notizie(self):
        """Test /api/notizie returns news articles"""
        response = requests.get(f"{BASE_URL}/api/notizie")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Notizie: {len(data)} articles returned")
    
    def test_get_prezzi_mercati(self):
        """Test /api/prezzi-mercati returns market price links"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        if data:
            link = data[0]
            assert "nome" in link
            assert "url" in link
        print(f"✓ Prezzi Mercati: {len(data)} market links")


class TestAISuggestion:
    """AI Suggestion tests"""
    
    def test_get_ai_suggestion(self):
        """Test /api/ai-suggestion returns suggestion"""
        response = requests.get(f"{BASE_URL}/api/ai-suggestion")
        assert response.status_code == 200
        data = response.json()
        
        if "suggestion" in data:
            suggestion = data["suggestion"]
            assert "titolo" in suggestion or "messaggio" in suggestion
            print(f"✓ AI Suggestion: {suggestion.get('titolo', 'N/A')}")
        else:
            print("✓ AI Suggestion: No suggestion available")


class TestFornitori:
    """Fornitori module tests"""
    
    def test_get_fornitori(self):
        """Test /api/fornitori returns array"""
        response = requests.get(f"{BASE_URL}/api/fornitori")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Fornitori: {len(data)} suppliers returned")


class TestOrdini:
    """Ordini module tests"""
    
    def test_get_ordini(self):
        """Test /api/ordini returns array"""
        response = requests.get(f"{BASE_URL}/api/ordini?limit=20")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Ordini: {len(data)} orders returned")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
