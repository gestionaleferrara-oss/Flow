import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Search, Plus, Edit2, Trash2 } from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Fornitori() {
  const [fornitori, setFornitori] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadFornitori();
  }, [search]);

  const loadFornitori = async () => {
    try {
      const params = search ? `?search=${search}` : '';
      const response = await axios.get(`${API}/fornitori${params}`);
      setFornitori(response.data);
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
              <th className="text-right">Fatturato</th>
              <th>Note</th>
              <th className="w-24"></th>
            </tr>
          </thead>
          <tbody>
            {fornitori.map((fornitore, index) => (
              <motion.tr
                key={fornitore.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.02 }}
              >
                <td className="font-medium">{fornitore.nome}</td>
                <td className="text-muted-foreground">{fornitore.codice || '-'}</td>
                <td className="text-right tabular-nums font-medium text-primary">
                  {formatCurrency(fornitore.fatturato_totale)}
                </td>
                <td className="text-muted-foreground text-sm truncate max-w-[300px]">
                  {fornitore.note || '-'}
                </td>
                <td>
                  <div className="table-actions justify-end">
                    <button
                      className="action-btn"
                      title="Modifica"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(fornitore.id)}
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

        {fornitori.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">🚚</div>
            <p>Nessun fornitore trovato</p>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
