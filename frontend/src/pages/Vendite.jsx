import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Search, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Trash2, X, AlertTriangle } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, formatDate, cn } from '@/lib/utils';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Vendite() {
  const [venditeGrouped, setVenditeGrouped] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(1);
  const [expandedRows, setExpandedRows] = useState({});
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteMode, setDeleteMode] = useState('period'); // 'period' or 'all'
  const [deleteStart, setDeleteStart] = useState('');
  const [deleteEnd, setDeleteEnd] = useState('');
  const [deleting, setDeleting] = useState(false);
  const perPage = 20;
  const isInitialLoad = useRef(true);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 400);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    loadVendite();
  }, [debouncedSearch, page]);

  const loadVendite = async () => {
    if (isInitialLoad.current) setLoading(true);
    try {
      const params = new URLSearchParams();
      if (debouncedSearch) params.append('search', debouncedSearch);
      params.append('skip', (page - 1) * perPage);
      params.append('limit', 500);
      const response = await axios.get(`${API}/vendite?${params}`);

      const grouped = {};
      response.data.forEach(v => {
        const key = `${v.cliente_nome}_${v.data}`;
        if (!grouped[key]) {
          grouped[key] = { id: key, cliente_nome: v.cliente_nome, data: v.data, prodotti: [], totale: 0 };
        }
        grouped[key].prodotti.push(v);
        grouped[key].totale += Math.abs((v.quantita || 0) * (v.prezzo_unitario || 0));
      });

      setVenditeGrouped(
        Object.values(grouped).sort((a, b) => b.data.localeCompare(a.data)).slice(0, perPage)
      );
    } catch (error) {
      console.error('Error loading vendite:', error);
    } finally {
      setLoading(false);
      isInitialLoad.current = false;
    }
  };

  const toggleExpand = (id) => {
    setExpandedRows(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      const params = new URLSearchParams();
      if (deleteMode === 'all') {
        params.append('delete_all', 'true');
      } else {
        if (deleteStart) params.append('start_date', deleteStart);
        if (deleteEnd) params.append('end_date', deleteEnd);
      }
      const response = await axios.delete(`${API}/vendite/bulk-delete?${params}`);
      toast.success(response.data.message);
      setShowDeleteModal(false);
      setDeleteStart('');
      setDeleteEnd('');
      isInitialLoad.current = true;
      loadVendite();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Errore nella cancellazione');
    } finally {
      setDeleting(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><LoadingSpinner /></div>;

  return (
    <PageWrapper>
      <PageHeader title="Vendite" subtitle="Storico delle vendite registrate">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowDeleteModal(true)}
          className="text-red-400 border-red-500/30 hover:bg-red-500/10"
          data-testid="open-delete-modal"
        >
          <Trash2 className="w-4 h-4 mr-2" />
          Cancella
        </Button>
      </PageHeader>

      {/* Search */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Cerca per cliente o prodotto..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
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
                  <React.Fragment key={gruppo.id}>
                    <tr
                      className={cn("cursor-pointer transition-colors hover:bg-white/5", isExpanded && "bg-blue-500/10")}
                      onClick={() => toggleExpand(gruppo.id)}
                      data-testid={`row-${index}`}
                      style={{ animation: `fadeIn 0.3s ease ${index * 0.02}s both` }}
                    >
                      <td className="text-center">
                        {isExpanded ? <ChevronUp className="w-4 h-4 text-blue-400 inline" /> : <ChevronDown className="w-4 h-4 text-slate-500 inline" />}
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
                    {isExpanded && (
                      <tr>
                        <td colSpan={5} className="p-0">
                          <div className="bg-slate-900/50 border-t border-b border-white/5">
                            <table className="w-full">
                              <thead>
                                <tr className="text-xs text-slate-500 uppercase">
                                  <th className="pl-12 py-2 text-left font-medium">Prodotto</th>
                                  <th className="py-2 text-right font-medium">Quantita</th>
                                  <th className="py-2 text-right font-medium">Prezzo Unit.</th>
                                  <th className="py-2 pr-4 text-right font-medium">Totale</th>
                                </tr>
                              </thead>
                              <tbody>
                                {gruppo.prodotti.map((prod, pIdx) => (
                                  <tr key={pIdx} className="border-t border-white/5 text-sm">
                                    <td className="pl-12 py-2 text-slate-300">{prod.prodotto_nome}</td>
                                    <td className="py-2 text-right tabular-nums text-slate-400">
                                      {Math.abs(prod.quantita || 0).toLocaleString('it-IT')}
                                    </td>
                                    <td className="py-2 text-right tabular-nums text-slate-400">
                                      {formatCurrency(prod.prezzo_unitario)}
                                    </td>
                                    <td className="py-2 pr-4 text-right tabular-nums font-medium text-slate-200">
                                      {formatCurrency(Math.abs((prod.quantita || 0) * (prod.prezzo_unitario || 0)))}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        {venditeGrouped.length === 0 && (
          <div className="empty-state">
            <BarChart3 className="w-12 h-12 mx-auto text-slate-600 mb-3" />
            <p>Nessuna vendita trovata</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-4">
        <p className="text-sm text-muted-foreground">Pagina {page}</p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} data-testid="prev-page-btn">
            <ChevronLeft className="w-4 h-4" /> Precedente
          </Button>
          <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={venditeGrouped.length < perPage} data-testid="next-page-btn">
            Successiva <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Delete Modal */}
      <AnimatePresence>
        {showDeleteModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowDeleteModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-md p-6"
              onClick={(e) => e.stopPropagation()}
              data-testid="delete-modal"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-red-500/20">
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                </div>
                <h2 className="text-lg font-semibold">Cancella Vendite</h2>
                <button onClick={() => setShowDeleteModal(false)} className="ml-auto p-1 hover:bg-slate-800 rounded-lg">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Mode selector */}
              <div className="flex gap-2 mb-4">
                <button
                  onClick={() => setDeleteMode('period')}
                  className={cn(
                    'flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all',
                    deleteMode === 'period'
                      ? 'bg-slate-700 text-white border border-slate-600'
                      : 'bg-slate-800/50 text-slate-400 hover:text-slate-300'
                  )}
                  data-testid="delete-mode-period"
                >
                  Per Periodo
                </button>
                <button
                  onClick={() => setDeleteMode('all')}
                  className={cn(
                    'flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all',
                    deleteMode === 'all'
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                      : 'bg-slate-800/50 text-slate-400 hover:text-slate-300'
                  )}
                  data-testid="delete-mode-all"
                >
                  Tutto
                </button>
              </div>

              {deleteMode === 'period' && (
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Da</label>
                    <Input
                      type="date"
                      value={deleteStart}
                      onChange={(e) => setDeleteStart(e.target.value)}
                      data-testid="delete-start-date"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">A</label>
                    <Input
                      type="date"
                      value={deleteEnd}
                      onChange={(e) => setDeleteEnd(e.target.value)}
                      data-testid="delete-end-date"
                    />
                  </div>
                </div>
              )}

              {deleteMode === 'all' && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg mb-4">
                  <p className="text-sm text-red-400">Attenzione: questa azione eliminera TUTTE le vendite registrate.</p>
                </div>
              )}

              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowDeleteModal(false)}
                >
                  Annulla
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1 bg-red-600 hover:bg-red-700"
                  onClick={handleDelete}
                  disabled={deleting || (deleteMode === 'period' && !deleteStart && !deleteEnd)}
                  data-testid="confirm-delete-btn"
                >
                  {deleting ? 'Eliminando...' : 'Conferma Eliminazione'}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </PageWrapper>
  );
}
