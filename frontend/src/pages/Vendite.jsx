import { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, ChevronLeft, ChevronRight, ChevronDown, ChevronUp } from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, formatDate, cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Vendite() {
  const [venditeGrouped, setVenditeGrouped] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [expandedRows, setExpandedRows] = useState({});
  const perPage = 20;

  useEffect(() => {
    loadVendite();
  }, [search, page]);

  const loadVendite = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) {
        params.append('search', search);
      }
      params.append('skip', (page - 1) * perPage);
      params.append('limit', 500); // Get more to group properly
      
      const response = await axios.get(`${API}/vendite?${params}`);
      
      // Group vendite by cliente + data
      const grouped = {};
      response.data.forEach(v => {
        const key = `${v.cliente_nome}_${v.data}`;
        if (!grouped[key]) {
          grouped[key] = {
            id: key,
            cliente_nome: v.cliente_nome,
            data: v.data,
            prodotti: [],
            totale: 0
          };
        }
        grouped[key].prodotti.push(v);
        grouped[key].totale += Math.abs(v.totale || (v.quantita * v.prezzo_unitario) || 0);
      });
      
      // Convert to array and sort by date desc
      const groupedArray = Object.values(grouped)
        .sort((a, b) => b.data.localeCompare(a.data))
        .slice(0, perPage);
      
      setVenditeGrouped(groupedArray);
    } catch (error) {
      console.error('Error loading vendite:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (id) => {
    setExpandedRows(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
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
      <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table" data-testid="vendite-table">
            <thead>
              <tr>
                <th className="w-12"></th>
                <th>Data</th>
                <th>Cliente</th>
                <th className="text-right">N. Prodotti</th>
                <th className="text-right">Totale Giorno</th>
              </tr>
            </thead>
            <tbody>
              {venditeGrouped.map((gruppo, index) => {
                const isExpanded = expandedRows[gruppo.id];
                return (
                  <>
                    <tr
                      key={gruppo.id}
                      className={cn(
                        "cursor-pointer transition-colors hover:bg-white/5",
                        isExpanded && "bg-blue-500/10"
                      )}
                      onClick={() => toggleExpand(gruppo.id)}
                      data-testid={`row-${index}`}
                    >
                      <td className="text-center">
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-blue-400 inline" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-slate-500 inline" />
                        )}
                      </td>
                      <td className="tabular-nums">{formatDate(gruppo.data)}</td>
                      <td className="font-medium">{gruppo.cliente_nome}</td>
                      <td className="text-right">
                        <span className="px-2 py-1 bg-slate-700/50 rounded-full text-xs">
                          {gruppo.prodotti.length} {gruppo.prodotti.length === 1 ? 'prodotto' : 'prodotti'}
                        </span>
                      </td>
                      <td className="text-right tabular-nums font-semibold text-emerald-400">
                        {formatCurrency(gruppo.totale)}
                      </td>
                    </tr>
                    
                    {/* Expanded row with product details */}
                    {isExpanded && (
                      <tr key={`${gruppo.id}-details`}>
                        <td colSpan={5} className="p-0">
                          <div className="bg-slate-900/50 border-t border-b border-white/5">
                            <table className="w-full">
                              <thead>
                                <tr className="text-xs text-slate-500 uppercase">
                                  <th className="pl-12 py-2 text-left font-medium">Prodotto</th>
                                  <th className="py-2 text-right font-medium">Quantità</th>
                                  <th className="py-2 text-right font-medium">Prezzo Unit.</th>
                                  <th className="py-2 pr-4 text-right font-medium">Totale</th>
                                </tr>
                              </thead>
                              <tbody>
                                {gruppo.prodotti.map((prod, pIdx) => (
                                  <tr 
                                    key={pIdx} 
                                    className="border-t border-white/5 text-sm"
                                  >
                                    <td className="pl-12 py-2 text-slate-300">{prod.prodotto_nome}</td>
                                    <td className="py-2 text-right tabular-nums text-slate-400">
                                      {Math.abs(prod.quantita || 0).toLocaleString('it-IT')}
                                    </td>
                                    <td className="py-2 text-right tabular-nums text-slate-400">
                                      {formatCurrency(prod.prezzo_unitario)}
                                    </td>
                                    <td className="py-2 pr-4 text-right tabular-nums font-medium text-slate-200">
                                      {formatCurrency(
                                        (prod.quantita && prod.prezzo_unitario)
                                          ? Math.abs(prod.quantita * prod.prezzo_unitario)
                                          : Math.abs(prod.totale)
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>

        {venditeGrouped.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">📊</div>
            <p>Nessuna vendita trovata</p>
            <p className="text-sm">Importa dei dati per visualizzare le vendite</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-4">
        <p className="text-sm text-muted-foreground">
          Pagina {page} - Clicca su una riga per espandere e vedere i dettagli
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
            disabled={venditeGrouped.length < perPage}
            data-testid="next-page-btn"
          >
            Successiva <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </PageWrapper>
  );
}
