import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Search, Plus, Eye, Edit2, Trash2 } from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Clienti() {
  const [clienti, setClienti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCliente, setSelectedCliente] = useState(null);
  const [analisi, setAnalisi] = useState(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    loadClienti();
  }, [search]);

  const loadClienti = async () => {
    try {
      const params = search ? `?search=${search}` : '';
      const response = await axios.get(`${API}/clienti${params}`);
      setClienti(response.data);
    } catch (error) {
      console.error('Error loading clienti:', error);
    } finally {
      setLoading(false);
    }
  };

  const viewAnalisi = async (cliente) => {
    setSelectedCliente(cliente);
    setShowModal(true);
    try {
      const response = await axios.get(`${API}/clienti/${cliente.id}/analisi`);
      setAnalisi(response.data);
    } catch (error) {
      console.error('Error loading analisi:', error);
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
              <th className="text-right">Fatturato</th>
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

      {/* Analisi Modal */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-lg" data-testid="analisi-modal">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl uppercase">
              Analisi Cliente: {selectedCliente?.nome}
            </DialogTitle>
          </DialogHeader>
          
          {analisi ? (
            <div className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-muted rounded-sm">
                  <p className="text-sm text-muted-foreground mb-1">Speso Ultimo Mese</p>
                  <p className="font-heading text-2xl font-bold text-primary">
                    {formatCurrency(analisi.totaleSpesoMese)}
                  </p>
                </div>
                <div className="p-4 bg-muted rounded-sm">
                  <p className="text-sm text-muted-foreground mb-1">Ordini Ultimo Mese</p>
                  <p className="font-heading text-2xl font-bold">
                    {analisi.ordiniMese}
                  </p>
                </div>
                <div className="p-4 bg-muted rounded-sm">
                  <p className="text-sm text-muted-foreground mb-1">Ultimo Ordine</p>
                  <p className="font-heading text-xl font-bold">
                    {analisi.ultimoOrdine}
                  </p>
                </div>
                <div className="p-4 bg-muted rounded-sm">
                  <p className="text-sm text-muted-foreground mb-1">Media per Ordine</p>
                  <p className="font-heading text-2xl font-bold">
                    {formatCurrency(analisi.mediaOrdine)}
                  </p>
                </div>
              </div>
              <div className="p-4 bg-primary/10 rounded-sm">
                <p className="text-sm text-muted-foreground mb-1">Prodotti Piu Acquistati</p>
                <p className="font-medium text-primary">
                  {analisi.prodottiPiuAcquistati || 'Nessun dato'}
                </p>
              </div>
            </div>
          ) : (
            <LoadingSpinner />
          )}
        </DialogContent>
      </Dialog>
    </PageWrapper>
  );
}
