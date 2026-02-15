import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Plus, Edit2, Trash2, Eye, X, Check, Package, ChevronDown, Calendar } from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, formatDate, cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Fornitori() {
  const [fornitori, setFornitori] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editNote, setEditNote] = useState('');
  const [savingNote, setSavingNote] = useState(false);
  
  // Year selector
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [availableYears, setAvailableYears] = useState([]);
  
  // Modal per prodotti fornitore
  const [showProdottiModal, setShowProdottiModal] = useState(false);
  const [selectedFornitore, setSelectedFornitore] = useState(null);
  const [fornitoreProdotti, setFornitoreProdotti] = useState(null);
  const [loadingProdotti, setLoadingProdotti] = useState(false);
  const [selectedMese, setSelectedMese] = useState('');

  useEffect(() => {
    loadFornitori();
  }, [search, selectedYear]);

  const loadFornitori = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (selectedYear) params.append('anno', selectedYear);
      const qs = params.toString() ? `?${params.toString()}` : '';
      const response = await axios.get(`${API}/fornitori-with-stats${qs}`);
      setFornitori(response.data.fornitori || []);
      if (response.data.anni_disponibili?.length > 0) {
        setAvailableYears(response.data.anni_disponibili);
      }
    } catch (error) {
      console.error('Error loading fornitori:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Sei sicuro di voler eliminare questo fornitore?')) return;
    try {
      await axios.delete(`${API}/fornitori/${id}`);
      loadFornitori();
    } catch (error) {
      console.error('Error deleting:', error);
    }
  };

  const handleEditNote = (fornitore) => {
    setEditingId(fornitore.id);
    setEditNote(fornitore.note || '');
  };

  const handleSaveNote = async (fornitoreId) => {
    setSavingNote(true);
    try {
      await axios.put(`${API}/fornitori/${fornitoreId}/note`, { note: editNote });
      setEditingId(null);
      loadFornitori();
    } catch (error) {
      console.error('Error saving note:', error);
      alert('Errore nel salvataggio della nota');
    } finally {
      setSavingNote(false);
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditNote('');
  };

  const handleViewProdotti = async (fornitore, mese = '') => {
    setSelectedFornitore(fornitore);
    setShowProdottiModal(true);
    setLoadingProdotti(true);
    setSelectedMese(mese);
    
    try {
      const params = mese ? `?mese=${mese}` : '';
      const response = await axios.get(`${API}/fornitori/${encodeURIComponent(fornitore.nome)}/prodotti${params}`);
      setFornitoreProdotti(response.data);
      // Set the selected month from the response if not already set
      if (!mese && response.data.mese_selezionato) {
        setSelectedMese(response.data.mese_selezionato);
      }
    } catch (error) {
      console.error('Error loading prodotti fornitore:', error);
      setFornitoreProdotti({ prodotti: [], totale_prodotti: 0, totale_speso: 0, mesi_disponibili: [] });
    } finally {
      setLoadingProdotti(false);
    }
  };

  const handleMeseChange = (mese) => {
    if (selectedFornitore) {
      handleViewProdotti(selectedFornitore, mese);
    }
  };

  const closeProdottiModal = () => {
    setShowProdottiModal(false);
    setSelectedFornitore(null);
    setFornitoreProdotti(null);
    setSelectedMese('');
  };

  if (loading) return <LoadingSpinner fullScreen />;

  return (
    <PageWrapper>
      <PageHeader
        title="Fornitori"
        subtitle="Gestione anagrafica fornitori"
      >
        <Button data-testid="add-fornitore-btn">
          <Plus className="w-4 h-4 mr-2" />
          Aggiungi Fornitore
        </Button>
      </PageHeader>

      {/* Search */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Cerca fornitore..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
            data-testid="search-fornitore"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-card border border-border/50 rounded-sm overflow-hidden">
        <table className="data-table" data-testid="fornitori-table">
          <thead>
            <tr>
              <th>Fornitore</th>
              <th>Codice</th>
              <th className="text-right">
                <div className="flex items-center justify-end gap-2">
                  <span>Fatturato</span>
                  <select
                    value={selectedYear}
                    onChange={(e) => setSelectedYear(Number(e.target.value))}
                    className="bg-slate-800 border border-slate-600 rounded px-2 py-0.5 text-xs font-normal text-slate-300 cursor-pointer hover:border-slate-500 focus:outline-none focus:border-blue-500"
                    data-testid="year-selector"
                  >
                    {availableYears.length > 0 ? (
                      availableYears.map(y => (
                        <option key={y} value={y}>{y}</option>
                      ))
                    ) : (
                      <option value={new Date().getFullYear()}>{new Date().getFullYear()}</option>
                    )}
                  </select>
                </div>
              </th>
              <th>Note</th>
              <th className="w-32"></th>
            </tr>
          </thead>
          <tbody>
            {fornitori.map((fornitore, index) => {
              const isEditing = editingId === fornitore.id;
              
              return (
                <motion.tr
                  key={fornitore.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: index * 0.02 }}
                  data-testid={`fornitore-row-${index}`}
                >
                  <td className="font-medium">{fornitore.nome}</td>
                  <td className="text-muted-foreground">{fornitore.codice || '-'}</td>
                  <td className="text-right tabular-nums font-medium text-emerald-400">
                    {formatCurrency(fornitore.fatturato_totale)}
                  </td>
                  <td className="max-w-[300px]">
                    {isEditing ? (
                      <div className="flex items-center gap-2">
                        <Textarea
                          value={editNote}
                          onChange={(e) => setEditNote(e.target.value)}
                          className="h-16 text-sm resize-none"
                          placeholder="Inserisci note..."
                          data-testid="edit-note-input"
                        />
                        <div className="flex flex-col gap-1">
                          <button
                            onClick={() => handleSaveNote(fornitore.id)}
                            disabled={savingNote}
                            className="action-btn"
                            data-testid="save-note-btn"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="action-btn delete"
                            data-testid="cancel-note-btn"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ) : (
                      <span 
                        className="text-muted-foreground text-sm truncate block cursor-pointer hover:text-slate-300"
                        onClick={() => handleEditNote(fornitore)}
                        title="Clicca per modificare"
                      >
                        {fornitore.note || '-'}
                      </span>
                    )}
                  </td>
                  <td>
                    <div className="table-actions justify-end">
                      <button
                        onClick={() => handleViewProdotti(fornitore)}
                        className="action-btn"
                        title="Vedi prodotti"
                        data-testid={`view-prodotti-btn-${index}`}
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleEditNote(fornitore)}
                        className="action-btn"
                        title="Modifica note"
                        data-testid={`edit-note-btn-${index}`}
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(fornitore.id)}
                        className="action-btn delete"
                        title="Elimina"
                        data-testid={`delete-fornitore-btn-${index}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>

        {fornitori.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">
              <Package className="w-8 h-8 text-muted-foreground" />
            </div>
            <p>Nessun fornitore trovato</p>
          </div>
        )}
      </div>

      {/* Modal Prodotti Fornitore */}
      <AnimatePresence>
        {showProdottiModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={closeProdottiModal}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-3xl max-h-[80vh] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
              data-testid="prodotti-modal"
            >
              {/* Modal Header */}
              <div className="p-6 border-b border-slate-700 bg-gradient-to-r from-blue-500/10 to-purple-500/10">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-blue-500/20">
                      <Package className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold">Prodotti da {selectedFornitore?.nome}</h2>
                      <p className="text-sm text-slate-400">
                        Storico acquisti per prodotto
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={closeProdottiModal}
                    className="p-2 rounded-lg hover:bg-slate-800 transition-colors"
                    data-testid="close-modal-btn"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Month Selector */}
                {fornitoreProdotti?.mesi_disponibili?.length > 0 && (
                  <div className="mt-4 flex items-center gap-3">
                    <Calendar className="w-4 h-4 text-slate-400" />
                    <span className="text-sm text-slate-400">Periodo:</span>
                    <select
                      value={selectedMese}
                      onChange={(e) => handleMeseChange(e.target.value)}
                      className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-slate-200 cursor-pointer hover:border-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                      data-testid="month-selector"
                    >
                      {fornitoreProdotti.mesi_disponibili.map(m => (
                        <option key={m.value} value={m.value}>{m.label}</option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Summary Stats */}
                {fornitoreProdotti && (
                  <div className="grid grid-cols-3 gap-4 mt-4">
                    <div className="p-3 bg-white/5 rounded-lg">
                      <p className="text-xs text-slate-400">Prodotti</p>
                      <p className="text-lg font-semibold text-blue-400" data-testid="modal-total-products">
                        {fornitoreProdotti.totale_prodotti}
                      </p>
                    </div>
                    <div className="p-3 bg-white/5 rounded-lg">
                      <p className="text-xs text-slate-400">Totale Speso</p>
                      <p className="text-lg font-semibold text-emerald-400" data-testid="modal-total-spent">
                        {formatCurrency(fornitoreProdotti.totale_speso)}
                      </p>
                    </div>
                    <div className="p-3 bg-white/5 rounded-lg">
                      <p className="text-xs text-slate-400">Mese</p>
                      <p className="text-lg font-semibold text-amber-400" data-testid="modal-month-label">
                        {fornitoreProdotti.mese_riferimento || 'N/A'}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Modal Body */}
              <div className="p-6 overflow-auto max-h-[calc(80vh-260px)]">
                {loadingProdotti ? (
                  <div className="flex items-center justify-center py-12">
                    <LoadingSpinner />
                  </div>
                ) : fornitoreProdotti?.prodotti?.length > 0 ? (
                  <div className="space-y-3">
                    {fornitoreProdotti.prodotti.map((prodotto, index) => (
                      <div
                        key={prodotto.nome}
                        className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50 hover:border-slate-600 transition-colors"
                        data-testid={`prodotto-item-${index}`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-medium text-slate-200">{prodotto.nome}</h3>
                          <span className="text-emerald-400 font-semibold">
                            {formatCurrency(prodotto.totale_speso)}
                          </span>
                        </div>
                        <div className="grid grid-cols-4 gap-4 text-sm">
                          <div>
                            <p className="text-slate-500">Quantita Tot.</p>
                            <p className="text-slate-300">{prodotto.quantita_totale.toLocaleString('it-IT')}</p>
                          </div>
                          <div>
                            <p className="text-slate-500">N. Ordini</p>
                            <p className="text-slate-300">{prodotto.num_ordini}</p>
                          </div>
                          <div>
                            <p className="text-slate-500">Ultimo Prezzo</p>
                            <p className="text-slate-300">{formatCurrency(prodotto.ultimo_prezzo)}</p>
                          </div>
                          <div>
                            <p className="text-slate-500">Ultimo Ordine</p>
                            <p className="text-slate-300">{formatDate(prodotto.ultimo_ordine)}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <Package className="w-12 h-12 mx-auto text-slate-600 mb-3" />
                    <p className="text-slate-400">Nessun prodotto acquistato in questo mese</p>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </PageWrapper>
  );
}
