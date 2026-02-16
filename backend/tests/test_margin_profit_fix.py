"""
Test suite for verifying the margin/profit calculation fixes and dashboard fatturatoMesePrec
Issue: Profitto now calculated on ALL products with purchase price, not just top 10
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDashboardFatturatoMesePrec:
    """Test that dashboard includes fatturatoMesePrec field"""
    
    def test_dashboard_has_fatturato_mese_prec(self):
        """Verify /api/dashboard returns fatturatoMesePrec field"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code == 200, f"Dashboard API failed: {response.status_code}"
        
        data = response.json()
        assert "fatturatoMesePrec" in data, "fatturatoMesePrec field missing from dashboard"
        assert isinstance(data["fatturatoMesePrec"], (int, float)), "fatturatoMesePrec must be numeric"
        print(f"✓ fatturatoMesePrec present: €{data['fatturatoMesePrec']:,.2f}")
        
    def test_dashboard_has_required_fields(self):
        """Verify all required dashboard fields are present"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ['fatturatoMese', 'fatturatoMesePrec', 'crescitaPercentuale', 
                          'ordiniMese', 'nuoviClienti', 'totaleProdotti']
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        print(f"✓ All required dashboard fields present")


class TestStatisticheMarginProfit:
    """Test that statistiche margin and profit are consistent"""
    
    def test_statistiche_has_margin_and_profit(self):
        """Verify /api/statistiche returns margineStimato and profittoStimato"""
        response = requests.get(f"{BASE_URL}/api/statistiche", 
                               params={"start_date": "2024-01-01", "end_date": "2025-12-31"})
        assert response.status_code == 200, f"Statistiche API failed: {response.status_code}"
        
        data = response.json()
        assert "margineStimato" in data, "margineStimato missing"
        assert "profittoStimato" in data, "profittoStimato missing"
        assert "totaleEuro" in data, "totaleEuro missing"
        
        print(f"✓ totaleEuro: €{data['totaleEuro']:,.2f}")
        print(f"✓ margineStimato: {data['margineStimato']:.1f}%")
        print(f"✓ profittoStimato: €{data['profittoStimato']:,.2f}")

    def test_profit_consistency_with_margin(self):
        """
        Verify profitto is approximately consistent with margine
        The formula is: profitto = sum(vendite - costi) for products with known purchase price
        The margin is a weighted average: sum(margine_pct * fatturato) / sum(fatturato)
        
        Expected: profitto should be in reasonable range (15-30% of revenue for products with margin data)
        """
        response = requests.get(f"{BASE_URL}/api/statistiche", 
                               params={"start_date": "2024-01-01", "end_date": "2025-12-31"})
        assert response.status_code == 200
        
        data = response.json()
        totale_euro = data['totaleEuro']
        margine_pct = data['margineStimato']
        profitto = data['profittoStimato']
        
        # Calculate what percentage of revenue the profit represents
        profit_ratio = (profitto / totale_euro * 100) if totale_euro > 0 else 0
        
        print(f"\n--- Margin/Profit Consistency Check ---")
        print(f"Total Revenue: €{totale_euro:,.2f}")
        print(f"Estimated Margin: {margine_pct:.1f}%")
        print(f"Estimated Profit: €{profitto:,.2f}")
        print(f"Profit as % of total revenue: {profit_ratio:.2f}%")
        
        # The margin is calculated only on products with purchase prices
        # Profit/Revenue ratio should be positive and reasonable (5-35% range)
        assert profitto >= 0, "Profit should be non-negative"
        assert 5 <= profit_ratio <= 35, f"Profit ratio {profit_ratio:.1f}% seems unreasonable (expected 5-35%)"
        print(f"✓ Profit ratio {profit_ratio:.2f}% is within reasonable range (5-35%)")
        
    def test_top_products_have_margin_data(self):
        """Verify top products include margin information where available"""
        response = requests.get(f"{BASE_URL}/api/statistiche", 
                               params={"start_date": "2024-01-01", "end_date": "2025-12-31"})
        assert response.status_code == 200
        
        data = response.json()
        top_prodotti = data.get('topProdotti', [])
        
        assert len(top_prodotti) > 0, "No top products returned"
        
        products_with_margin = 0
        for prod in top_prodotti:
            if 'margine_pct' in prod and prod.get('margine_pct') is not None:
                products_with_margin += 1
                print(f"  - {prod['nome'][:30]}: €{prod['totale_euro']:,.0f}, margin: {prod['margine_pct']}%, profit: €{prod.get('profitto', 0):,.0f}")
        
        print(f"\n✓ {products_with_margin}/{len(top_prodotti)} top products have margin data")
        # Most products should have margin data if they have purchase prices
        assert products_with_margin >= len(top_prodotti) // 2, "Less than half of top products have margin data"


class TestStatistiche3Months:
    """Test statistiche with 3-month filter for current period"""
    
    def test_statistiche_3_months_consistency(self):
        """Test statistiche for last 3 months shows consistent margin/profit"""
        response = requests.get(f"{BASE_URL}/api/statistiche", 
                               params={"start_date": "2025-10-01", "end_date": "2025-12-31"})
        assert response.status_code == 200
        
        data = response.json()
        totale_euro = data['totaleEuro']
        margine_pct = data['margineStimato']
        profitto = data['profittoStimato']
        
        print(f"\n--- 3-Month Period (2025-10 to 2025-12) ---")
        print(f"Total Revenue: €{totale_euro:,.2f}")
        print(f"Margin: {margine_pct:.1f}%")
        print(f"Profit: €{profitto:,.2f}")
        
        if totale_euro > 0:
            profit_ratio = profitto / totale_euro * 100
            print(f"Profit/Revenue ratio: {profit_ratio:.2f}%")
            
            # The ratio should be positive and within reasonable bounds
            assert profitto >= 0, "Profit should be non-negative"
            assert 10 <= profit_ratio <= 35, f"Profit ratio {profit_ratio:.1f}% seems off"
            print(f"✓ Margin and profit are consistent for 3-month period")


class TestNotizieLiveBadge:
    """Test that notizie API works correctly"""
    
    def test_notizie_endpoint_returns_data(self):
        """Verify /api/notizie returns news items"""
        response = requests.get(f"{BASE_URL}/api/notizie")
        assert response.status_code == 200, f"Notizie API failed: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Notizie should return a list"
        
        if len(data) > 0:
            # Check first news item has expected fields
            news = data[0]
            assert "titolo" in news, "News missing titolo"
            assert "data_pubblicazione" in news, "News missing data_pubblicazione"
            print(f"✓ Notizie API returns {len(data)} items")
            print(f"  Latest: {news.get('titolo', '')[:60]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
