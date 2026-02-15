import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Search, Plus, ChevronLeft, ChevronRight } from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, formatDate } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Ordini() {
  const [ordini, setOrdini] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const perPage = 20;

  useEffect(() => {
    loadOrdini();
  }, [search, page]);

  const loadOrdini = async () => {
    try {
      const params = new URLSearchParams();
      if (search) {
        params.append('fornitore', search);
        params.append('prodotto', search);
      }
      params.append('skip', (page - 1) * perPage);
      params.append('limit', perPage);
      
      const response = await axios.get(`${API}/ordini?${params}`);
      setOrdini(response.data);
    } catch (error) {
      console.error('Error loading ordini:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner fullScreen />;

  return (
    <PageWrapper>
      <PageHeader
        title="Acquisti"
        subtitle="Storico degli ordini ai fornitori"
      >
        <Button data-testid="add-ordine-btn">
          <Plus className="w-4 h-4 mr-2" />
          Nuovo Acquisto
        </Button>
      </PageHeader>

      {/* Search */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Cerca per fornitore o prodotto..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-10"
            data-testid="search-ordini"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-card border border-border/50 rounded-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table" data-testid="ordini-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Fornitore</th>
                <th>Prodotto</th>
                <th className="text-right">Q.ta</th>
                <th className="text-right">Kg/pz</th>
                <th className="text-right">Tot. Kg</th>
                <th className="text-right">Prezzo</th>
                <th className="text-right">Totale</th>
              </tr>
            </thead>
            <tbody>
              {ordini.map((ordine, index) => (
                <motion.tr
                  key={ordine.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: index * 0.02 }}
                >
                  <td className="tabular-nums">{formatDate(ordine.data)}</td>
                  <td className="font-medium">{ordine.fornitore_nome}</td>
                  <td>{ordine.prodotto_nome}</td>
                  <td className="text-right tabular-nums">{ordine.quantita?.toLocaleString('it-IT')}</td>
                  <td className="text-right tabular-nums">{ordine.kg_per_pezzo?.toFixed(2)}</td>
                  <td className="text-right tabular-nums">{ordine.totale_kg?.toFixed(2)}</td>
                  <td className="text-right tabular-nums">{formatCurrency(ordine.prezzo_unitario)}</td>
                  <td className="text-right tabular-nums font-medium text-primary">
                    {formatCurrency(ordine.totale)}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        {ordini.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">🛒</div>
            <p>Nessun acquisto trovato</p>
            <p className="text-sm">Importa dei dati o aggiungi un nuovo acquisto</p>
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
          >
            <ChevronLeft className="w-4 h-4" /> Precedente
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => p + 1)}
            disabled={ordini.length < perPage}
          >
            Successiva <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </PageWrapper>
  );
}
