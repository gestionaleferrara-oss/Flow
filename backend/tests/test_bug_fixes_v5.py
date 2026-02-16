"""
Bug Fix Verification Tests for Flusso v5
Testing:
1. Sales data import - vendite classified correctly with 2024 data
2. Sales totals are positive (not negative)
3. Statistiche charts show correct data
4. Pie chart tooltip functionality (isAnimationActive=false)
5. Clienti Inattivi shows days of inactivity calculated from latest DB date
6. In Esaurimento shows products with giorni_rimanenti
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestVenditeBugFix:
    """Test that vendite are correctly classified and have 2024 data with positive totals"""
    
    def test_vendite_endpoint_returns_data(self):
        """Verify /api/vendite returns data"""
        response = requests.get(f"{BASE_URL}/api/vendite?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Vendite should have data"
        print(f"Found {len(data)} vendite records")
    
    def test_vendite_have_2024_data(self):
        """Bug fix: Verify 2024 data is present (was missing before fix)"""
        response = requests.get(f"{BASE_URL}/api/vendite?limit=100")
        assert response.status_code == 200
        data = response.json()
        
        # Check for 2024 dates
        dates_2024 = [v for v in data if v.get('data', '').startswith('2024')]
        assert len(dates_2024) > 0, "Should have 2024 data after bug fix"
        print(f"Found {len(dates_2024)} records with 2024 dates")
        
        # Verify specific months are present
        months = set(v.get('data', '')[:7] for v in dates_2024)
        print(f"2024 months found: {sorted(months)}")
        assert any('2024-12' in m for m in months), "Should have December 2024 data"
    
    def test_vendite_totals_are_positive(self):
        """Bug fix: Verify totals are positive (not negative after abs() fix)"""
        response = requests.get(f"{BASE_URL}/api/vendite?limit=50")
        assert response.status_code == 200
        data = response.json()
        
        # All totals should be >= 0
        negative_totals = [v for v in data if v.get('totale', 0) < 0]
        assert len(negative_totals) == 0, f"Found {len(negative_totals)} negative totals"
        
        # Verify we have actual positive values
        positive_totals = [v for v in data if v.get('totale', 0) > 0]
        assert len(positive_totals) > 0, "Should have positive totals"
        print(f"All {len(data)} records have non-negative totals")
    
    def test_vendite_have_correct_movimento(self):
        """Verify vendite have Movimento='Scarico' and Causale='VENDITA'"""
        response = requests.get(f"{BASE_URL}/api/vendite?limit=50")
        assert response.status_code == 200
        data = response.json()
        
        # Check movimento and causale
        for v in data[:10]:
            movimento = v.get('movimento', '').lower()
            causale = v.get('causale', '').upper()
            if movimento:
                assert movimento == 'scarico', f"Expected Scarico, got {movimento}"
            if causale:
                assert 'VENDITA' in causale or 'VEN' in causale, f"Expected VENDITA, got {causale}"


class TestStatisticheBugFix:
    """Test that statistiche show correct chart data"""
    
    def test_statistiche_returns_data(self):
        """Verify /api/statistiche returns data structure"""
        response = requests.get(f"{BASE_URL}/api/statistiche")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert 'totaleEuro' in data
        assert 'totaleArticoli' in data
        assert 'venditeMensili' in data
        assert 'topClienti' in data
        assert 'topProdotti' in data
        print(f"TotaleEuro: {data['totaleEuro']}")
    
    def test_statistiche_totale_positive(self):
        """Bug fix: Verify totaleEuro is positive"""
        response = requests.get(f"{BASE_URL}/api/statistiche")
        assert response.status_code == 200
        data = response.json()
        
        # totaleEuro should be positive
        assert data['totaleEuro'] >= 0, "totaleEuro should be non-negative"
        assert data['totaleEuro'] > 0, "totaleEuro should be positive with data"
        print(f"TotaleEuro is positive: {data['totaleEuro']}")
    
    def test_statistiche_monthly_data_has_2024(self):
        """Bug fix: Verify monthly data includes 2024"""
        response = requests.get(f"{BASE_URL}/api/statistiche")
        assert response.status_code == 200
        data = response.json()
        
        monthly = data.get('venditeMensili', [])
        assert len(monthly) > 0, "Should have monthly data"
        
        # Check for 2024 months
        months_2024 = [m for m in monthly if m.get('data', '').startswith('2024')]
        assert len(months_2024) > 0, "Should have 2024 monthly data"
        print(f"Found {len(months_2024)} months of 2024 data: {[m['data'] for m in months_2024]}")
    
    def test_statistiche_top_clienti_data(self):
        """Verify topClienti has proper structure for pie chart"""
        response = requests.get(f"{BASE_URL}/api/statistiche")
        assert response.status_code == 200
        data = response.json()
        
        top_clienti = data.get('topClienti', [])
        assert len(top_clienti) > 0, "Should have top clienti data"
        
        # Each entry should have nome and spesa
        for cliente in top_clienti[:5]:
            assert 'nome' in cliente, "Cliente should have nome"
            assert 'spesa' in cliente, "Cliente should have spesa"
            assert cliente['spesa'] > 0, "Spesa should be positive"
        
        print(f"Top 3 clienti: {[(c['nome'][:30], c['spesa']) for c in top_clienti[:3]]}")


class TestClientiInattiviBugFix:
    """Test that clienti inattivi shows days calculated from latest DB date"""
    
    def test_alerts_returns_clienti_inattivi(self):
        """Verify /api/alerts returns clientiInattivi"""
        response = requests.get(f"{BASE_URL}/api/alerts")
        assert response.status_code == 200
        data = response.json()
        
        assert 'clientiInattivi' in data
        print(f"Found {len(data['clientiInattivi'])} inactive clients")
    
    def test_clienti_inattivi_has_giorni_inattivo(self):
        """Bug fix: Verify clientiInattivi entries have giorni_inattivo field"""
        response = requests.get(f"{BASE_URL}/api/alerts")
        assert response.status_code == 200
        data = response.json()
        
        clienti = data.get('clientiInattivi', [])
        if len(clienti) > 0:
            for cliente in clienti[:5]:
                assert 'nome' in cliente, "Should have nome"
                assert 'giorni_inattivo' in cliente, "Should have giorni_inattivo"
                assert cliente['giorni_inattivo'] > 0, "giorni_inattivo should be > 0"
                print(f"Cliente {cliente['nome'][:30]}: {cliente['giorni_inattivo']}gg")
        else:
            print("No inactive clients (all are active)")
    
    def test_clienti_inattivi_days_calculated_from_db_date(self):
        """Bug fix: Days should be calculated from most recent DB date, not datetime.now()"""
        response = requests.get(f"{BASE_URL}/api/alerts")
        assert response.status_code == 200
        data = response.json()
        
        clienti = data.get('clientiInattivi', [])
        if len(clienti) > 0:
            # If DB has 2024-12-31 as latest, days should be < 100 for recent inactive clients
            # Not hundreds/thousands if calculated from current date
            for cliente in clienti:
                giorni = cliente.get('giorni_inattivo', 0)
                # Should be reasonable (< 100 days) since data is from late 2024
                # and reference should be from DB date not current (2026)
                assert giorni < 100, f"Days should be calculated from DB date, got {giorni}"
            print("PASS: Days calculated from latest DB date (not datetime.now())")


class TestInEsaurimentoBugFix:
    """Test that prodotti in esaurimento shows giorni_rimanenti"""
    
    def test_alerts_returns_prodotti_in_esaurimento(self):
        """Verify /api/alerts returns prodottiInEsaurimento"""
        response = requests.get(f"{BASE_URL}/api/alerts")
        assert response.status_code == 200
        data = response.json()
        
        assert 'prodottiInEsaurimento' in data
        print(f"Found {len(data['prodottiInEsaurimento'])} products running low")
    
    def test_prodotti_in_esaurimento_has_giorni_rimanenti(self):
        """Verify prodottiInEsaurimento entries have giorni_rimanenti field"""
        response = requests.get(f"{BASE_URL}/api/alerts")
        assert response.status_code == 200
        data = response.json()
        
        prodotti = data.get('prodottiInEsaurimento', [])
        if len(prodotti) > 0:
            for prod in prodotti[:5]:
                assert 'nome' in prod, "Should have nome"
                assert 'giorni_rimanenti' in prod, "Should have giorni_rimanenti"
                assert prod['giorni_rimanenti'] >= 0, "giorni_rimanenti should be >= 0"
                print(f"Prodotto {prod['nome'][:30]}: {prod['giorni_rimanenti']}gg rimanenti")
        else:
            print("No products running low")


class TestPieChartTooltipFix:
    """Test data structure for pie chart tooltip (isAnimationActive=false fix)"""
    
    def test_top_clienti_structure_for_pie(self):
        """Verify topClienti has correct structure for pie chart"""
        response = requests.get(f"{BASE_URL}/api/statistiche")
        assert response.status_code == 200
        data = response.json()
        
        top_clienti = data.get('topClienti', [])
        assert len(top_clienti) > 0, "Should have topClienti"
        
        # Structure should support Pie chart with nome as nameKey and spesa as dataKey
        cliente = top_clienti[0]
        assert 'nome' in cliente, "Need nome for nameKey"
        assert 'spesa' in cliente, "Need spesa for dataKey"
        
        # Values should be valid for chart rendering
        assert isinstance(cliente['nome'], str)
        assert isinstance(cliente['spesa'], (int, float))
        assert cliente['spesa'] > 0
        print("PASS: Data structure supports pie chart with tooltip")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
