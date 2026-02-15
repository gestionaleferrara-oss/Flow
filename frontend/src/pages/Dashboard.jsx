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
  ArrowUpRight,
  Upload,
  BarChart3,
  TrendingUp,
  TrendingDown
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import StatCard from '@/components/StatCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, formatDate, cn } from '@/lib/utils';

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
        subtitle="Panoramica delle attività aziendali"
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8 animate-stagger">
        <StatCard
          label="Fatturato Mese"
          value={data?.fatturatoMese || 0}
          format="currency"
          icon={Euro}
          gradient="blue"
          trend={data?.crescitaPercentuale > 0 ? 'up' : data?.crescitaPercentuale < 0 ? 'down' : 'neutral'}
          trendValue={data?.crescitaPercentuale}
          subtitle={data?.fatturatoMesePrec > 0 ? `Mese prec: ${formatCurrency(data.fatturatoMesePrec)}` : null}
        />
        <StatCard
          label="Ordini Mese"
          value={data?.ordiniMese || 0}
          icon={ShoppingCart}
          gradient="emerald"
        />
        <StatCard
          label="Nuovi Clienti"
          value={data?.nuoviClienti || 0}
          icon={Users}
          gradient="cyan"
        />
        <StatCard
          label="Da Riordinare"
          value={data?.prodottiOrdinare || 0}
          icon={AlertTriangle}
          gradient="amber"
        />
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-8">
        <QuickLinkCard
          title="Importa Dati"
          description="Carica un file CSV o XLSX per importare vendite e aggiornare il magazzino"
          href="/upload"
          icon={Upload}
          gradient="from-blue-500 to-blue-600"
        />
        <QuickLinkCard
          title="Visualizza Statistiche"
          description="Analizza le vendite per periodo, prodotto e cliente"
          href="/statistiche"
          icon={BarChart3}
          gradient="from-purple-500 to-purple-600"
        />
        <QuickLinkCard
          title="Gestisci Magazzino"
          description="Controlla le scorte e i prodotti da riordinare"
          href="/magazzino"
          icon={Package}
          gradient="from-emerald-500 to-emerald-600"
        />
      </div>

      {/* Recent Activity */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-card overflow-hidden"
      >
        <div className="p-5 border-b border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10">
              <TrendingUp className="w-5 h-5 text-blue-400" />
            </div>
            <h2 className="font-semibold text-lg">Attività Recenti</h2>
          </div>
          <Link 
            to="/vendite" 
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            Vedi tutte
          </Link>
        </div>
        <div className="divide-y divide-white/5">
          {data?.attivitaRecenti?.length > 0 ? (
            data.attivitaRecenti.map((item, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 + index * 0.05 }}
                className="p-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-blue-500/10 
                    flex items-center justify-center border border-blue-500/20">
                    <ShoppingCart className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-200">{item.descrizione}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{formatDate(item.data)}</p>
                  </div>
                </div>
                <span className="font-mono text-sm font-semibold text-emerald-400">
                  {formatCurrency(item.valore)}
                </span>
              </motion.div>
            ))
          ) : (
            <div className="p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-800/50 
                flex items-center justify-center">
                <Calendar className="w-8 h-8 text-slate-600" />
              </div>
              <p className="text-slate-400 font-medium">Nessuna attività recente</p>
              <p className="text-sm text-slate-600 mt-1">
                Importa dei dati per iniziare
              </p>
              <Link
                to="/upload"
                className="inline-flex items-center gap-2 mt-4 px-4 py-2 
                  bg-blue-500/10 text-blue-400 rounded-lg hover:bg-blue-500/20 transition-colors"
              >
                <Upload className="w-4 h-4" />
                Importa Dati
              </Link>
            </div>
          )}
        </div>
      </motion.div>
    </PageWrapper>
  );
}

function QuickLinkCard({ title, description, href, icon: Icon, gradient }) {
  return (
    <Link
      to={href}
      data-testid={`quick-link-${title.toLowerCase().replace(/\s/g, '-')}`}
      className="group block p-6 glass-card hover:border-blue-500/30 transition-all duration-500"
    >
      <div className="flex items-start gap-4">
        <div className={cn(
          'p-3 rounded-xl bg-gradient-to-br shadow-lg transition-all duration-300',
          gradient,
          'group-hover:scale-110 group-hover:shadow-xl'
        )}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-lg text-slate-200 mb-1 
            group-hover:text-white transition-colors">
            {title}
          </h3>
          <p className="text-sm text-slate-500 line-clamp-2">{description}</p>
        </div>
        <ArrowUpRight className="w-5 h-5 text-slate-600 group-hover:text-blue-400 
          transform group-hover:translate-x-1 group-hover:-translate-y-1 transition-all" />
      </div>
    </Link>
  );
}
