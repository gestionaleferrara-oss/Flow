import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
  Search,
  AlertTriangle,
  Calendar,
  Plus,
  Edit2,
  Check,
  X,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import LoadingSpinner from '@/components/LoadingSpinner';
import { cn, formatCurrency, getStatusBadge } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Magazzino() {
  const [prodotti, setProdotti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState(null);
  const [stats, setStats] = useState({ ordinare_count: 0, scadenza_count: 0 });
  const [page, setPage] = useState(1);
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({});
  const perPage = 15;

  useEffect(() => {
    loadProdotti();
    loadStats();
  }, [search, filter, page]);

  const loadProdotti = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (filter) params.append('filter_type', filter);
      params.append('skip', (page - 1) * perPage);
      params.append('limit', perPage);
      
      const response = await axios.get(`${API}/prodotti?${params}`);
      setProdotti(response.data);
    } catch (error) {
      console.error('Error loading prodotti:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await axios.get(`${API}/prodotti/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const handleEdit = (prodotto) => {
    setEditingId(prodotto.id);
    setEditData({ ...prodotto });
  };

  const handleSave = async () => {
    try {
      await axios.put(`${API}/prodotti/${editingId}`, editData);
      setEditingId(null);
      loadProdotti();
      loadStats();
    } catch (error) {
      console.error('Error saving:', error);
    }
  };

  const handleCancel = () => {
    setEditingId(null);
    setEditData({});
  };

  const toggleFilter = (type) => {
    setFilter(filter === type ? null : type);
    setPage(1);
  };

  if (loading) return <LoadingSpinner fullScreen />;

  return (
    <PageWrapper>
      <PageHeader
        title="Magazzino"
        subtitle="Gestione inventario e scorte"
      >
        <Button data-testid="add-product-btn">
          <Plus className="w-4 h-4 mr-2" />
          Aggiungi Prodotto
        </Button>
      </PageHeader>

      {/* Filter Bar */}
      <div className="filter-bar rounded-sm mb-6">
        <div className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Cerca prodotto..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="pl-10"
              data-testid="search-input"
            />
          </div>
        </div>
        
        <button
          onClick={() => toggleFilter('ordinare')}
          data-testid="filter-ordinare"
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-sm transition-all',
            filter === 'ordinare' 
              ? 'bg-amber-500/20 text-amber-500 ring-1 ring-amber-500' 
              : 'bg-card hover:bg-muted'
          )}
        >
          <AlertTriangle className="w-4 h-4" />
          <span className="font-medium">{stats.ordinare_count}</span>
          <span className="text-sm">Da Ordinare</span>
        </button>
        
        <button
          onClick={() => toggleFilter('scadenza')}
          data-testid="filter-scadenza"
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-sm transition-all',
            filter === 'scadenza' 
              ? 'bg-purple-500/20 text-purple-500 ring-1 ring-purple-500' 
              : 'bg-card hover:bg-muted'
          )}
        >
          <Calendar className="w-4 h-4" />
          <span className="font-medium">{stats.scadenza_count}</span>
          <span className="text-sm">In Scadenza</span>
        </button>
      </div>

      {/* Data Table */}
      <div className="bg-card border border-border/50 rounded-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table" data-testid="magazzino-table">
            <thead>
              <tr>
                <th>Prodotto</th>
                <th className="text-right">Q.ta</th>
                <th className="text-right">Kg/pz</th>
                <th>Imballo</th>
                <th className="text-right">Q.ta Min.</th>
                <th className="text-right">Q.ta Rim.</th>
                <th className="text-right">Kg Rim.</th>
                <th className="text-right">Prezzo</th>
                <th className="text-right">Valore</th>
                <th>Scadenza</th>
                <th>Stato</th>
                <th className="w-24"></th>
              </tr>
            </thead>
            <tbody>
              {prodotti.map((p, index) => {
                const isEditing = editingId === p.id;
                const status = getStatusBadge(p.stato);
                
                return (
                  <motion.tr
                    key={p.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: index * 0.02 }}
                    data-testid={`row-${p.id}`}
                  >
                    <td className="font-medium">
                      {isEditing ? (
                        <Input
                          value={editData.nome || ''}
                          onChange={(e) => setEditData({ ...editData, nome: e.target.value })}
                          className="h-8"
                        />
                      ) : (
                        p.nome
                      )}
                    </td>
                    <td className="text-right tabular-nums">
                      {isEditing ? (
                        <Input
                          type="number"
                          value={editData.quantita || 0}
                          onChange={(e) => setEditData({ ...editData, quantita: parseFloat(e.target.value) })}
                          className="h-8 w-20 text-right"
                        />
                      ) : (
                        p.quantita?.toLocaleString('it-IT')
                      )}
                    </td>
                    <td className="text-right tabular-nums">{p.kg_per_pezzo?.toFixed(2)}</td>
                    <td>{p.imballo || '-'}</td>
                    <td className="text-right tabular-nums">
                      {isEditing ? (
                        <Input
                          type="number"
                          value={editData.quantita_minima || 0}
                          onChange={(e) => setEditData({ ...editData, quantita_minima: parseFloat(e.target.value) })}
                          className="h-8 w-20 text-right"
                          data-testid="edit-quantita-minima"
                        />
                      ) : (
                        p.quantita_minima?.toLocaleString('it-IT') || '0'
                      )}
                    </td>
                    <td className="text-right tabular-nums">{p.quantita?.toLocaleString('it-IT')}</td>
                    <td className="text-right tabular-nums">{p.kg_rimanenti?.toFixed(2)}</td>
                    <td className="text-right tabular-nums">{formatCurrency(p.prezzo_medio)}</td>
                    <td className="text-right tabular-nums font-medium">{formatCurrency(p.valore_scorte)}</td>
                    <td>
                      {isEditing ? (
                        <Input
                          type="date"
                          value={editData.scadenza || ''}
                          onChange={(e) => setEditData({ ...editData, scadenza: e.target.value })}
                          className="h-8 w-36"
                          data-testid="edit-scadenza"
                        />
                      ) : (
                        p.scadenza || '-'
                      )}
                    </td>
                    <td>
                      <span className={cn('flex items-center gap-1 text-sm', status.color)}>
                        {status.icon} {status.label}
                      </span>
                    </td>
                    <td>
                      <div className="table-actions justify-end">
                        {isEditing ? (
                          <>
                            <button
                              onClick={handleSave}
                              className="action-btn"
                              data-testid="save-btn"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={handleCancel}
                              className="action-btn delete"
                              data-testid="cancel-btn"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => handleEdit(p)}
                            className="action-btn"
                            data-testid="edit-btn"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {prodotti.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">📦</div>
            <p>Nessun prodotto trovato</p>
            <p className="text-sm">Importa dei dati o aggiungi un nuovo prodotto</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-4">
        <p className="text-sm text-muted-foreground">
          Pagina {page}
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            data-testid="prev-page"
          >
            <ChevronLeft className="w-4 h-4" />
            Precedente
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => p + 1)}
            disabled={prodotti.length < perPage}
            data-testid="next-page"
          >
            Successiva
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </PageWrapper>
  );
}
