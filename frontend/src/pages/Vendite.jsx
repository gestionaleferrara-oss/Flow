import { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, ChevronLeft, ChevronRight } from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, formatDate } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Vendite() {
  const [vendite, setVendite] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const perPage = 20;

  useEffect(() => {
    loadVendite();
  }, [search, page]);

  const loadVendite = async () => {
    try {
      const params = new URLSearchParams();
      if (search) {
        params.append('cliente', search);
        params.append('prodotto', search);
      }
      params.append('skip', (page - 1) * perPage);
      params.append('limit', perPage);
      
      const response = await axios.get(`${API}/vendite?${params}`);
      setVendite(response.data);
    } catch (error) {
      console.error('Error loading vendite:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner fullScreen />;

  return (
    <PageWrapper>
      <PageHeader
        title="Vendite"
        subtitle="Storico delle vendite registrate"
      />

      {/* Search */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Cerca per cliente o prodotto..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-10"
            data-testid="search-vendite"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-card border border-border/50 rounded-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table" data-testid="vendite-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Cliente</th>
                <th>Prodotto</th>
                <th className="text-right">Quantita</th>
                <th className="text-right">Prezzo Unit.</th>
                <th className="text-right">Totale</th>
              </tr>
            </thead>
            <tbody>
              {vendite.map((vendita, index) => (
                <tr
                  key={vendita.id}
                  className="animate-fade-in"
                  style={{ animationDelay: `${index * 20}ms` }}
                >
                  <td className="tabular-nums">{formatDate(vendita.data)}</td>
                  <td className="font-medium">{vendita.cliente_nome}</td>
                  <td>{vendita.prodotto_nome}</td>
                  <td className="text-right tabular-nums">{Math.abs(vendita.quantita || 0).toLocaleString('it-IT')}</td>
                  <td className="text-right tabular-nums">{formatCurrency(vendita.prezzo_unitario)}</td>
                  <td className="text-right tabular-nums font-medium text-primary">
                    {formatCurrency(vendita.totale)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {vendite.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">📊</div>
            <p>Nessuna vendita trovata</p>
            <p className="text-sm">Importa dei dati per visualizzare le vendite</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-4">
        <p className="text-sm text-muted-foreground">Pagina {page}</p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            data-testid="prev-page-btn"
          >
            <ChevronLeft className="w-4 h-4" /> Precedente
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => p + 1)}
            disabled={vendite.length < perPage}
            data-testid="next-page-btn"
          >
            Successiva <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </PageWrapper>
  );
}
