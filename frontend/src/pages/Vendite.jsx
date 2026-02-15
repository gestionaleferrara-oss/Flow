import { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, ChevronLeft, ChevronRight, Database } from 'lucide-react';
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
  const [totalCount, setTotalCount] = useState(0);
  const perPage = 20;

  useEffect(() => {
    loadVendite();
    loadTotalCount();
  }, [search, page]);

  const loadVendite = async () => {
    try {
      const params = new URLSearchParams();
      if (search) {
        params.append('search', search);
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

  const loadTotalCount = async () => {
    try {
      const response = await axios.get(`${API}/vendite/count`);
      setTotalCount(response.data.count);
    } catch (error) {
      console.error('Error loading count:', error);
    }
  };

  if (loading) return <LoadingSpinner fullScreen />;

  const totalPages = Math.ceil(totalCount / perPage);
  const startRecord = (page - 1) * perPage + 1;
  const endRecord = Math.min(page * perPage, totalCount);

  return (
    <PageWrapper>
      <PageHeader
        title="Vendite"
        subtitle="Storico delle vendite registrate"
      />

      {/* Total Records Counter */}
      <div className="mb-6 flex items-center gap-4">
        <div className="flex items-center gap-3 px-4 py-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
          <Database className="w-5 h-5 text-emerald-400" />
          <div>
            <span className="text-emerald-400 font-semibold text-lg">{totalCount.toLocaleString('it-IT')}</span>
            <span className="text-slate-400 text-sm ml-2">record totali nel database</span>
          </div>
        </div>
      </div>

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
      <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
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
                    {formatCurrency(
                      (vendita.quantita && vendita.prezzo_unitario)
                        ? vendita.quantita * vendita.prezzo_unitario
                        : vendita.totale
                    )}
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

      {/* Pagination with detailed info */}
      <div className="flex items-center justify-between mt-4">
        <p className="text-sm text-muted-foreground">
          {totalCount > 0 ? (
            <>
              Mostrando <span className="font-medium text-slate-300">{startRecord}</span> - <span className="font-medium text-slate-300">{endRecord}</span> di <span className="font-medium text-emerald-400">{totalCount.toLocaleString('it-IT')}</span> record
              {totalPages > 1 && <span className="ml-2">(Pagina {page} di {totalPages})</span>}
            </>
          ) : (
            'Nessun record'
          )}
        </p>
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
            disabled={vendite.length < perPage || page >= totalPages}
            data-testid="next-page-btn"
          >
            Successiva <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </PageWrapper>
  );
}
