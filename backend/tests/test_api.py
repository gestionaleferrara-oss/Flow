"""
Backend API Tests for Magazzino CSV Pro
Tests: Dashboard, CSV Upload, Statistiche, Notizie, Magazzino, Clienti, Fornitori, Prodotti
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://magazzino-csv-pro.preview.emergentagent.com"


class TestHealthCheck:
    """Basic API health tests"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Gestio API" in data["message"]
        print("✓ API root endpoint working")


class TestDashboard:
    """Dashboard API tests"""
    
    def test_get_dashboard(self):
        """Test dashboard overview endpoint"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected keys
        expected_keys = ['fatturatoMese', 'ordiniMese', 'nuoviClienti', 
                        'prodottiOrdinare', 'prodottiScadenza', 'attivitaRecenti']
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"
        
        # Data type assertions
        assert isinstance(data['fatturatoMese'], (int, float))
        assert isinstance(data['ordiniMese'], int)
        assert isinstance(data['attivitaRecenti'], list)
        print(f"✓ Dashboard data: fatturato={data['fatturatoMese']}, ordini={data['ordiniMese']}")


class TestCSVUpload:
    """CSV Upload API tests"""
    
    def test_upload_csv_success(self):
        """Test CSV upload with valid file"""
        csv_path = "/tmp/sales_small.csv"
        
        if not os.path.exists(csv_path):
            pytest.skip("Test CSV file not found")
        
        with open(csv_path, 'rb') as f:
            files = {'file': ('sales_small.csv', f, 'text/csv')}
            response = requests.post(f"{BASE_URL}/api/upload-csv", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get('success') == True
        assert 'stats' in data
        stats = data['stats']
        
        # Verify auto-detected columns
        assert 'columns_detected' in stats
        print(f"✓ CSV upload successful: {stats.get('rows_processed', 0)} rows processed")
        print(f"  Columns detected: {stats.get('columns_detected', {})}")
        print(f"  Vendite created: {stats.get('vendite_created', 0)}")
        print(f"  Ordini created: {stats.get('ordini_created', 0)}")
    
    def test_upload_invalid_file(self):
        """Test CSV upload with non-CSV file"""
        files = {'file': ('test.txt', b'not a csv file', 'text/plain')}
        response = requests.post(f"{BASE_URL}/api/upload-csv", files=files)
        
        # Should reject non-CSV files
        assert response.status_code == 400
        print("✓ Invalid file upload correctly rejected")


class TestStatistiche:
    """Statistiche API tests"""
    
    def test_get_statistiche(self):
        """Test basic statistiche endpoint"""
        response = requests.get(f"{BASE_URL}/api/statistiche")
        assert response.status_code == 200
        data = response.json()
        
        expected_keys = ['totaleEuro', 'totaleArticoli', 'clientiAttivi',
                        'fatturatoMese', 'venditeMensili', 'topClienti', 'topProdotti']
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"
        
        print(f"✓ Statistiche: totale={data['totaleEuro']}€, clienti={data['clientiAttivi']}")
    
    def test_statistiche_with_filters(self):
        """Test statistiche with date filters"""
        params = {
            'start_date': '2025-01-01',
            'end_date': '2025-12-31'
        }
        response = requests.get(f"{BASE_URL}/api/statistiche", params=params)
        assert response.status_code == 200
        data = response.json()
        assert 'totaleEuro' in data
        print(f"✓ Statistiche with date filter working")
    
    def test_get_statistiche_lists(self):
        """Test statistiche filter lists endpoint"""
        response = requests.get(f"{BASE_URL}/api/statistiche/lists")
        assert response.status_code == 200
        data = response.json()
        
        assert 'prodotti' in data
        assert 'clienti' in data
        assert isinstance(data['prodotti'], list)
        assert isinstance(data['clienti'], list)
        print(f"✓ Lists: {len(data['prodotti'])} prodotti, {len(data['clienti'])} clienti")


class TestNotizie:
    """Notizie (News) API tests"""
    
    def test_get_notizie(self):
        """Test get news endpoint"""
        response = requests.get(f"{BASE_URL}/api/notizie")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Notizie: {len(data)} articles found")
    
    def test_refresh_notizie(self):
        """Test refresh news endpoint"""
        response = requests.post(f"{BASE_URL}/api/notizie/refresh")
        assert response.status_code == 200
        data = response.json()
        assert 'message' in data
        print(f"✓ Notizie refresh triggered")
    
    def test_get_prezzi_mercati(self):
        """Test market prices links endpoint"""
        response = requests.get(f"{BASE_URL}/api/prezzi-mercati")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify structure
        for mercato in data:
            assert 'nome' in mercato
            assert 'url' in mercato
        print(f"✓ Prezzi mercati: {len(data)} markets available")


class TestMeteo:
    """Weather API tests"""
    
    def test_get_meteo_default(self):
        """Test weather endpoint with default location (Bologna)"""
        response = requests.get(f"{BASE_URL}/api/meteo")
        assert response.status_code == 200
        data = response.json()
        
        # Should have current_weather if API is working
        if 'error' not in data:
            assert 'current_weather' in data
            assert 'temperature' in data['current_weather']
            print(f"✓ Meteo: {data['current_weather']['temperature']}°C")
        else:
            print(f"⚠ Meteo API returned error: {data.get('error')}")


class TestMagazzino:
    """Magazzino (Products/Inventory) API tests"""
    
    def test_get_prodotti(self):
        """Test get products endpoint"""
        response = requests.get(f"{BASE_URL}/api/prodotti")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Prodotti: {len(data)} products found")
        
        if len(data) > 0:
            # Verify product structure
            p = data[0]
            expected_keys = ['id', 'nome', 'quantita', 'prezzo_medio']
            for key in expected_keys:
                assert key in p, f"Missing key: {key}"
    
    def test_get_prodotti_with_search(self):
        """Test products search"""
        response = requests.get(f"{BASE_URL}/api/prodotti", params={'search': 'fagioli'})
        assert response.status_code == 200
        print(f"✓ Product search working")
    
    def test_get_prodotti_stats(self):
        """Test product stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/prodotti/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert 'ordinare_count' in data
        assert 'scadenza_count' in data
        assert 'total' in data
        print(f"✓ Prodotti stats: total={data['total']}, ordinare={data['ordinare_count']}")
    
    def test_get_prodotti_filter_ordinare(self):
        """Test products filter - Da Ordinare"""
        response = requests.get(f"{BASE_URL}/api/prodotti", params={'filter_type': 'ordinare'})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Filter 'ordinare': {len(data)} products")
    
    def test_get_prodotti_filter_scadenza(self):
        """Test products filter - In Scadenza"""
        response = requests.get(f"{BASE_URL}/api/prodotti", params={'filter_type': 'scadenza'})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Filter 'scadenza': {len(data)} products")


class TestClienti:
    """Clienti CRUD API tests"""
    
    @pytest.fixture
    def test_cliente_id(self):
        """Create a test client for subsequent tests"""
        data = {"nome": "TEST_Cliente_PyTest", "codice": "TEST001"}
        response = requests.post(f"{BASE_URL}/api/clienti", json=data)
        if response.status_code == 200:
            return response.json().get('id')
        return None
    
    def test_get_clienti(self):
        """Test get clients endpoint"""
        response = requests.get(f"{BASE_URL}/api/clienti")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Clienti: {len(data)} clients found")
    
    def test_create_cliente(self):
        """Test create client"""
        data = {"nome": "TEST_NuovoCliente", "codice": "TEST999", "email": "test@test.com"}
        response = requests.post(f"{BASE_URL}/api/clienti", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result.get('nome') == data['nome']
        assert 'id' in result
        print(f"✓ Cliente created: {result.get('id')}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/clienti/{result['id']}")
    
    def test_get_clienti_search(self):
        """Test client search"""
        response = requests.get(f"{BASE_URL}/api/clienti", params={'search': 'fruit'})
        assert response.status_code == 200
        print(f"✓ Client search working")


class TestFornitori:
    """Fornitori CRUD API tests"""
    
    def test_get_fornitori(self):
        """Test get suppliers endpoint"""
        response = requests.get(f"{BASE_URL}/api/fornitori")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Fornitori: {len(data)} suppliers found")
    
    def test_create_fornitore(self):
        """Test create supplier"""
        data = {"nome": "TEST_NuovoFornitore", "codice": "TESTF001"}
        response = requests.post(f"{BASE_URL}/api/fornitori", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result.get('nome') == data['nome']
        assert 'id' in result
        print(f"✓ Fornitore created: {result.get('id')}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/fornitori/{result['id']}")


class TestVendite:
    """Vendite (Sales) API tests"""
    
    def test_get_vendite(self):
        """Test get sales endpoint"""
        response = requests.get(f"{BASE_URL}/api/vendite")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Vendite: {len(data)} sales found")
    
    def test_get_vendite_count(self):
        """Test vendite count endpoint"""
        response = requests.get(f"{BASE_URL}/api/vendite/count")
        assert response.status_code == 200
        data = response.json()
        assert 'count' in data
        print(f"✓ Vendite count: {data['count']}")
    
    def test_get_vendite_with_filters(self):
        """Test vendite with filters"""
        params = {
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
            'limit': 10
        }
        response = requests.get(f"{BASE_URL}/api/vendite", params=params)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Vendite filter working")


class TestOrdini:
    """Ordini (Orders/Purchases) API tests"""
    
    def test_get_ordini(self):
        """Test get orders endpoint"""
        response = requests.get(f"{BASE_URL}/api/ordini")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Ordini: {len(data)} orders found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
