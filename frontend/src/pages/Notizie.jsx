import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Plus, Calendar, Newspaper } from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatDate } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Notizie() {
  const [notizie, setNotizie] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadNotizie();
  }, []);

  const loadNotizie = async () => {
    try {
      const response = await axios.get(`${API}/notizie`);
      setNotizie(response.data);
    } catch (error) {
      console.error('Error loading notizie:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner fullScreen />;

  return (
    <PageWrapper>
      <PageHeader
        title="Notizie"
        subtitle="News e aggiornamenti aziendali"
      >
        <Button data-testid="add-notizia-btn">
          <Plus className="w-4 h-4 mr-2" />
          Nuova Notizia
        </Button>
      </PageHeader>

      {notizie.length > 0 ? (
        <div className="grid gap-6">
          {notizie.map((notizia, index) => (
            <motion.article
              key={notizia.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-card border border-border/50 rounded-sm p-6 hover:border-primary/30 transition-colors"
            >
              <div className="flex items-start gap-4">
                <div className="p-3 bg-primary/10 rounded-sm">
                  <Newspaper className="w-6 h-6 text-primary" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs uppercase tracking-wider text-primary font-medium px-2 py-1 bg-primary/10 rounded-sm">
                      {notizia.categoria}
                    </span>
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {formatDate(notizia.created_at)}
                    </span>
                  </div>
                  <h2 className="font-heading text-xl font-semibold mb-2">
                    {notizia.titolo}
                  </h2>
                  <p className="text-muted-foreground">
                    {notizia.contenuto}
                  </p>
                </div>
              </div>
            </motion.article>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-state-icon">📰</div>
          <p>Nessuna notizia disponibile</p>
          <p className="text-sm">Aggiungi la prima notizia per iniziare</p>
        </div>
      )}
    </PageWrapper>
  );
}
