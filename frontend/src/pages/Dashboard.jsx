import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
  Euro,
  ShoppingCart,
  Users,
  Package,
  AlertTriangle,
  Calendar,
  ArrowUpRight
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import StatCard from '@/components/StatCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, formatDate } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const response = await axios.get(`${API}/dashboard`);
      setData(response.data);
    } catch (error) {
      console.error('Error loading dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner fullScreen />;

  return (
    <PageWrapper>
      <PageHeader 
        title="Dashboard" 
        subtitle="Panoramica delle attivita aziendali"
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8 animate-stagger">
        <StatCard
          label="Fatturato Mese"
          value={data?.fatturatoMese || 0}
          format="currency"
          icon={Euro}
        />
        <StatCard
          label="Ordini Mese"
          value={data?.ordiniMese || 0}
          icon={ShoppingCart}
        />
        <StatCard
          label="Nuovi Clienti"
          value={data?.nuoviClienti || 0}
          icon={Users}
        />
        <StatCard
          label="Prodotti da Ordinare"
          value={data?.prodottiOrdinare || 0}
          icon={AlertTriangle}
        />
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <QuickLinkCard
          title="Importa Dati CSV"
          description="Carica un file CSV per importare vendite e aggiornare il magazzino"
          href="/upload"
          icon={Package}
        />
        <QuickLinkCard
          title="Visualizza Statistiche"
          description="Analizza le vendite per periodo, prodotto e cliente"
          href="/statistiche"
          icon={Euro}
        />
        <QuickLinkCard
          title="Gestisci Magazzino"
          description="Controlla le scorte e i prodotti da riordinare"
          href="/magazzino"
          icon={Package}
        />
      </div>

      {/* Recent Activity */}
      <div className="bg-card border border-border/50 rounded-sm">
        <div className="p-4 border-b border-border">
          <h2 className="font-heading text-lg font-semibold uppercase tracking-wider">
            Attivita Recenti
          </h2>
        </div>
        <div className="divide-y divide-border/50">
          {data?.attivitaRecenti?.length > 0 ? (
            data.attivitaRecenti.map((item, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="p-4 flex items-center justify-between hover:bg-muted/50"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary/10 rounded-sm flex items-center justify-center">
                    <ShoppingCart className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{item.descrizione}</p>
                    <p className="text-xs text-muted-foreground">{formatDate(item.data)}</p>
                  </div>
                </div>
                <span className="font-mono text-sm text-primary">
                  {formatCurrency(item.valore)}
                </span>
              </motion.div>
            ))
          ) : (
            <div className="p-8 text-center text-muted-foreground">
              <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Nessuna attivita recente</p>
              <p className="text-sm mt-1">Importa dei dati per iniziare</p>
            </div>
          )}
        </div>
      </div>
    </PageWrapper>
  );
}

function QuickLinkCard({ title, description, href, icon: Icon }) {
  return (
    <Link
      to={href}
      data-testid={`quick-link-${title.toLowerCase().replace(/\s/g, '-')}`}
      className="group block p-6 bg-card border border-border/50 rounded-sm hover:border-primary/50 transition-all"
    >
      <div className="flex items-start gap-4">
        <div className="p-3 bg-primary/10 rounded-sm group-hover:bg-primary/20 transition-colors">
          <Icon className="w-6 h-6 text-primary" />
        </div>
        <div className="flex-1">
          <h3 className="font-heading text-lg font-semibold mb-1 group-hover:text-primary transition-colors">
            {title}
          </h3>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
        <ArrowUpRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
      </div>
    </Link>
  );
}
