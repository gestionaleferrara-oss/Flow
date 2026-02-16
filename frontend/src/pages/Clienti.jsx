import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Search, Plus, Eye, Edit2, Trash2, Save, X, Phone, Mail, FileText, Calendar, Clock } from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PERIODI = [
  { value: 'mese', label: 'Mese Corrente' },
  { value: '3mesi', label: '3 Mesi' },
  { value: '6mesi', label: '6 Mesi' },
  { value: 'anno', label: 'Anno' },
  { value: 'tutto', label: 'Tutto' },
];

export default function Clienti() {
  const [clienti, setClienti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCliente, setSelectedCliente] = useState(null);
  const [analisi, setAnalisi] = useState(null);
  const [loadingAnalisi, setLoadingAnalisi] = useState(false);
  const [periodoAnalisi, setPeriodoAnalisi] = useState('mese');
  const [showModal, setShowModal] = useState(false);
  const [editFields, setEditFields] = useState({
    whatsapp: '',
    email: '',
    note: ''
  });
  const [saving, setSaving] = useState(false);
  const [selectedYear, setSelectedYear] = useState('');
  const [availableYears, setAvailableYears] = useState([]);

  // Read search param from URL on mount
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const searchParam = urlParams.get('search');
    if (searchParam) {
      setSearch(searchParam);
    }
  }, []);

  useEffect(() => {
    loadClienti();
  }, [search, selectedYear]);

  const loadClienti = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (selectedYear) params.append('anno', selectedYear);
      const qs = params.toString() ? `?${params.toString()}` : '';
      const response = await axios.get(`${API}/clienti${qs}`);
      const data = response.data;
      setClienti(data.clienti || []);
      const anni = data.anni_disponibili || [];
      if (anni.length > 0 && availableYears.length === 0) {
        setAvailableYears(anni);
        if (!selectedYear) setSelectedYear(anni[0]);
      }
    } catch (error) {
      console.error('Error loading clienti:', error);
    } finally {
      setLoading(false);
    }
  };

  const viewAnalisi = async (cliente, periodo = 'mese') => {
    setSelectedCliente(cliente);
    setPeriodoAnalisi(periodo);
    setEditFields({
      whatsapp: cliente.whatsapp || '',
      email: cliente.email || '',
      note: cliente.note || ''
    });
    setShowModal(true);
    setLoadingAnalisi(true);
    try {
      const response = await axios.get(`${API}/clienti/${cliente.id}/analisi?periodo=${periodo}`);
      setAnalisi(response.data);
    } catch (error) {
      console.error('Error loading analisi:', error);
    } finally {
      setLoadingAnalisi(false);
    }
  };

  const handlePeriodoChange = (newPeriodo) => {
    setPeriodoAnalisi(newPeriodo);
    if (selectedCliente) {
      viewAnalisi(selectedCliente, newPeriodo);
    }
  };

  const handleSaveClienteDetails = async () => {
    if (!selectedCliente) return;
    setSaving(true);
    try {
      await axios.put(`${API}/clienti/${selectedCliente.id}`, {
        nome: selectedCliente.nome,
        codice: selectedCliente.codice,
        whatsapp: editFields.whatsapp,
        email: editFields.email,
        note: editFields.note
      });
      // Aggiorna la lista clienti
      loadClienti();
      // Aggiorna il cliente selezionato
      setSelectedCliente({
        ...selectedCliente,
        whatsapp: editFields.whatsapp,
        email: editFields.email,
        note: editFields.note
      });
    } catch (error) {
      console.error('Error saving cliente:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Sei sicuro di voler eliminare questo cliente?')) return;
    try {
      await axios.delete(`${API}/clienti/${id}`);
      loadClienti();
    } catch (error) {
      console.error('Error deleting:', error);
    }
  };

  if (loading) return <LoadingSpinner fullScreen />;

  return (
    <PageWrapper>
      <PageHeader
        title="Clienti"
        subtitle="Gestione anagrafica clienti"
      >
        <Button data-testid="add-cliente-btn">
          <Plus className="w-4 h-4 mr-2" />
          Aggiungi Cliente
        </Button>
      </PageHeader>

      {/* Search */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Cerca cliente..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
            data-testid="search-cliente"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-card border border-border/50 rounded-sm overflow-hidden">
        <table className="data-table" data-testid="clienti-table">
          <thead>
            <tr>
              <th>Cliente</th>
              <th>Codice</th>
              <th className="text-right">
                <div className="flex items-center justify-end gap-2">
                  <span>Fatturato</span>
                  {availableYears.length > 0 && (
                    <select
                      value={selectedYear}
                      onChange={(e) => setSelectedYear(e.target.value)}
                      className="bg-slate-800 border border-slate-600 rounded px-2 py-0.5 text-xs font-normal text-slate-300 cursor-pointer hover:border-slate-500 focus:outline-none focus:border-blue-500"
                      data-testid="year-selector"
                    >
                      {availableYears.map(y => (
                        <option key={y} value={y}>{y}</option>
                      ))}
                    </select>
                  )}
                </div>
              </th>
              <th>WhatsApp</th>
              <th>Email</th>
              <th>Note</th>
              <th className="w-32"></th>
            </tr>
          </thead>
          <tbody>
            {clienti.map((cliente, index) => (
              <motion.tr
                key={cliente.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.02 }}
              >
                <td className="font-medium">{cliente.nome}</td>
                <td className="text-muted-foreground">{cliente.codice || '-'}</td>
                <td className="text-right tabular-nums font-medium text-primary">
                  {formatCurrency(cliente.fatturato_totale)}
                </td>
                <td>{cliente.whatsapp || '-'}</td>
                <td>{cliente.email || '-'}</td>
                <td className="text-muted-foreground text-sm truncate max-w-[200px]">
                  {cliente.note || '-'}
                </td>
                <td>
                  <div className="table-actions justify-end">
                    <button
                      onClick={() => viewAnalisi(cliente)}
                      className="action-btn"
                      data-testid="view-analisi"
                      title="Visualizza analisi"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => viewAnalisi(cliente)}
                      className="action-btn"
                      title="Modifica"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(cliente.id)}
                      className="action-btn delete"
                      title="Elimina"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>

        {clienti.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">👤</div>
            <p>Nessun cliente trovato</p>
          </div>
        )}
      </div>

      {/* Analisi Modal con campi editabili */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto" data-testid="analisi-modal">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl uppercase">
              Analisi Cliente: {selectedCliente?.nome}
            </DialogTitle>
          </DialogHeader>
          
          {/* Periodo Selector */}
          <div className="flex items-center gap-2 mb-4 flex-wrap">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Periodo:</span>
            {PERIODI.map(p => (
              <button
                key={p.value}
                onClick={() => handlePeriodoChange(p.value)}
                disabled={loadingAnalisi}
                className={cn(
                  "px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                  periodoAnalisi === p.value 
                    ? "bg-primary text-primary-foreground" 
                    : "bg-muted hover:bg-muted/80 text-muted-foreground"
                )}
              >
                {p.label}
              </button>
            ))}
          </div>
          
          {loadingAnalisi ? (
            <div className="flex items-center justify-center h-40">
              <LoadingSpinner />
            </div>
          ) : analisi ? (
            <div className="space-y-6">
              {/* Statistiche */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 bg-muted rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Totale Speso</p>
                  <p className="font-heading text-xl font-bold text-primary">
                    {formatCurrency(analisi.totaleSpeso)}
                  </p>
                </div>
                <div className="p-3 bg-muted rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Num. Visite</p>
                  <p className="font-heading text-xl font-bold">
                    {analisi.numOrdini}
                  </p>
                </div>
                <div className="p-3 bg-muted rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Ultima Visita</p>
                  <p className="font-heading text-lg font-bold">
                    {analisi.ultimoOrdine}
                  </p>
                </div>
                <div className="p-3 bg-muted rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Media/Visita</p>
                  <p className="font-heading text-xl font-bold">
                    {formatCurrency(analisi.mediaOrdine)}
                  </p>
                </div>
              </div>
              
              {/* Lista Visite */}
              {analisi.listaVisite && analisi.listaVisite.length > 0 && (
                <div className="border border-border rounded-lg overflow-hidden">
                  <div className="px-3 py-2 bg-muted/50 border-b border-border flex items-center gap-2">
                    <Clock className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm font-semibold">Storico Visite</span>
                  </div>
                  <div className="max-h-48 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/30 sticky top-0">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Data</th>
                          <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Totale</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analisi.listaVisite.map((v, i) => (
                          <tr key={i} className="border-t border-border/50 hover:bg-muted/20">
                            <td className="px-3 py-2">{v.data}</td>
                            <td className="px-3 py-2 text-right font-medium text-primary">{formatCurrency(v.totale)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              
              {/* Prodotti Più Acquistati */}
              <div className="p-3 bg-primary/10 rounded-lg">
                <p className="text-xs text-muted-foreground mb-2">Prodotti Più Acquistati</p>
                {analisi.topProdotti && analisi.topProdotti.length > 0 ? (
                  <div className="space-y-1">
                    {analisi.topProdotti.slice(0, 5).map((p, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span className="truncate flex-1 mr-2">{p.nome}</span>
                        <span className="text-primary font-medium">{formatCurrency(p.totale)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Nessun dato</p>
                )}
              </div>

              {/* Campi Editabili */}
              <div className="border-t border-border pt-4">
                <h4 className="font-semibold mb-4 flex items-center gap-2">
                  <Edit2 className="w-4 h-4" />
                  Informazioni di Contatto
                </h4>
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <Phone className="w-4 h-4 text-green-500 shrink-0" />
                    <Input
                      placeholder="WhatsApp (es. +39 123 456 7890)"
                      value={editFields.whatsapp}
                      onChange={(e) => setEditFields({ ...editFields, whatsapp: e.target.value })}
                      className="flex-1"
                      data-testid="edit-whatsapp"
                    />
                  </div>
                  <div className="flex items-center gap-3">
                    <Mail className="w-4 h-4 text-blue-500 shrink-0" />
                    <Input
                      placeholder="Email"
                      type="email"
                      value={editFields.email}
                      onChange={(e) => setEditFields({ ...editFields, email: e.target.value })}
                      className="flex-1"
                      data-testid="edit-email"
                    />
                  </div>
                  <div className="flex items-start gap-3">
                    <FileText className="w-4 h-4 text-amber-500 shrink-0 mt-3" />
                    <Textarea
                      placeholder="Note sul cliente..."
                      value={editFields.note}
                      onChange={(e) => setEditFields({ ...editFields, note: e.target.value })}
                      className="flex-1"
                      rows={3}
                      data-testid="edit-note"
                    />
                  </div>
                  <Button onClick={handleSaveClienteDetails} disabled={saving} className="w-full">
                    <Save className="w-4 h-4 mr-2" />
                    {saving ? 'Salvataggio...' : 'Salva Modifiche'}
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-40 text-muted-foreground">
              Nessun dato disponibile
            </div>
          )}
        </DialogContent>
      </Dialog>
    </PageWrapper>
  );
}
