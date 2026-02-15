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
  ArrowUpRight,
  Upload,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Search,
  Box,
  Sparkles,
  Lightbulb,
  RefreshCw,
  Clock,
  UserX,
  PackageX,
  AlertCircle
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import StatCard from '@/components/StatCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { formatCurrency, formatDate, cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [prodotti, setProdotti] = useState([]);
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [prodottoSearch, setProdottoSearch] = useState('');
  const [showProdottoModal, setShowProdottoModal] = useState(false);
  const [selectedProdotto, setSelectedProdotto] = useState(null);
  const [prodottoAnalisi, setProdottoAnalisi] = useState(null);
  const [loadingAnalisi, setLoadingAnalisi] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [alerts, setAlerts] = useState(null);
  const [loadingAlerts, setLoadingAlerts] = useState(true);

  useEffect(() => {
    loadDashboard();
    loadProdotti();
    loadAiSuggestion();
    loadAlerts();
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

  const loadProdotti = async () => {
    try {
      const response = await axios.get(`${API}/prodotti?limit=1000`);
      setProdotti(response.data);
    } catch (error) {
      console.error('Error loading prodotti:', error);
    }
  };

  const loadAiSuggestion = async () => {
    setLoadingAi(true);
    try {
      const response = await axios.get(`${API}/ai-suggestion`);
      setAiSuggestion(response.data);
    } catch (error) {
      console.error('Error loading AI suggestion:', error);
    } finally {
      setLoadingAi(false);
    }
  };

  const refreshAiSuggestion = async () => {
    setLoadingAi(true);
    try {
      const response = await axios.post(`${API}/ai-suggestion/refresh`);
      setAiSuggestion(response.data);
    } catch (error) {
      console.error('Error refreshing AI suggestion:', error);
    } finally {
      setLoadingAi(false);
    }
  };

  const loadAlerts = async () => {
    setLoadingAlerts(true);
    try {
      const response = await axios.get(`${API}/alerts`);
      setAlerts(response.data);
    } catch (error) {
      console.error('Error loading alerts:', error);
    } finally {
      setLoadingAlerts(false);
    }
  };

  const viewProdottoAnalisi = async (prodotto) => {
    setSelectedProdotto(prodotto);
    setShowSearchModal(false);
    setShowProdottoModal(true);
    setLoadingAnalisi(true);
    setProdottoSearch('');
    try {
      const response = await axios.get(`${API}/prodotti/${encodeURIComponent(prodotto.nome)}/analisi`);
      setProdottoAnalisi(response.data);
    } catch (error) {
      console.error('Error loading prodotto analisi:', error);
      setProdottoAnalisi(null);
    } finally {
      setLoadingAnalisi(false);
    }
  };

  const filteredProdotti = prodotti.filter(p => 
    p.nome.toLowerCase().includes(prodottoSearch.toLowerCase())
  ).slice(0, 12);

  if (loading) return <LoadingSpinner fullScreen />;

  const totalAlerts = (alerts?.prodottiSottoScorta?.length || 0) + 
                      (alerts?.clientiInattivi?.length || 0) + 
                      (alerts?.prodottiInEsaurimento?.length || 0);

  return (
    <PageWrapper>
      <PageHeader 
        title="Dashboard" 
        subtitle="Panoramica delle attività aziendali"
      >
        <Button
          variant="outline"
          onClick={() => setShowSearchModal(true)}
          className="gap-2"
          data-testid="open-search-prodotto"
        >
          <Search className="w-4 h-4" />
          Cerca Prodotto
        </Button>
      </PageHeader>

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
          label="Alert Attivi"
          value={totalAlerts}
          icon={AlertTriangle}
          gradient="amber"
        />
      </div>

      {/* AI Suggestion Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="mb-8"
      >
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-violet-500/10 via-purple-500/5 to-fuchsia-500/10 border border-purple-500/20">
          <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-violet-500/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />
          
          <div className="relative p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-purple-500/25">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-lg text-white">Suggerimento AI</h3>
                    <span className="px-2 py-0.5 text-xs bg-purple-500/20 text-purple-300 rounded-full">AI</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={refreshAiSuggestion}
                    disabled={loadingAi}
                    className="text-purple-300 hover:text-purple-200 hover:bg-purple-500/20"
                    data-testid="refresh-ai-btn"
                  >
                    <RefreshCw className={cn("w-4 h-4 mr-1", loadingAi && "animate-spin")} />
                    Nuovo
                  </Button>
                </div>
                
                {loadingAi ? (
                  <div className="flex items-center gap-2 text-slate-400">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Analisi in corso...</span>
                  </div>
                ) : aiSuggestion?.suggestion ? (
                  <>
                    <div className="flex items-center gap-2 mb-2">
                      <Lightbulb className="w-4 h-4 text-amber-400" />
                      <span className="text-sm font-medium text-purple-300">{aiSuggestion.suggestion.titolo}</span>
                    </div>
                    <p className="text-slate-300 text-sm leading-relaxed mb-3">
                      {aiSuggestion.suggestion.messaggio}
                    </p>
                    <span className="inline-block px-3 py-1.5 text-xs bg-white/5 text-purple-300 rounded-lg border border-purple-500/20">
                      {aiSuggestion.suggestion.azione}
                    </span>
                  </>
                ) : (
                  <p className="text-slate-400 text-sm">
                    Importa più dati per ricevere suggerimenti personalizzati
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-8">
        <QuickLinkCard
          title="Importa Dati"
          description="Carica un file CSV o XLSX per importare vendite"
          href="/upload"
          icon={Upload}
          gradient="from-blue-500 to-blue-600"
        />
        <QuickLinkCard
          title="Visualizza Statistiche"
          description="Analizza le vendite per periodo e cliente"
          href="/statistiche"
          icon={BarChart3}
          gradient="from-purple-500 to-purple-600"
        />
        <QuickLinkCard
          title="Gestisci Magazzino"
          description="Controlla le scorte e i prodotti"
          href="/magazzino"
          icon={Package}
          gradient="from-emerald-500 to-emerald-600"
        />
      </div>

      {/* Alert Gestione */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-card overflow-hidden"
      >
        <div className="p-5 border-b border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/10">
              <AlertCircle className="w-5 h-5 text-amber-400" />
            </div>
            <h2 className="font-semibold text-lg">Centro Alert</h2>
            {totalAlerts > 0 && (
              <span className="px-2 py-0.5 text-xs bg-amber-500/20 text-amber-300 rounded-full">
                {totalAlerts} alert
              </span>
            )}
          </div>
        </div>
        
        {loadingAlerts ? (
          <div className="p-8 text-center">
            <LoadingSpinner />
          </div>
        ) : totalAlerts === 0 ? (
          <div className="p-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
              <Box className="w-8 h-8 text-emerald-500" />
            </div>
            <p className="text-emerald-400 font-medium">Tutto sotto controllo!</p>
            <p className="text-sm text-slate-500 mt-1">Nessun alert attivo</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 divide-y lg:divide-y-0 lg:divide-x divide-white/5">
            {/* Prodotti Sotto Scorta */}
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <PackageX className="w-4 h-4 text-red-400" />
                <span className="text-sm font-medium text-slate-300">Sotto Scorta</span>
                <span className="ml-auto text-xs text-slate-500">{alerts?.prodottiSottoScorta?.length || 0}</span>
              </div>
              <div className="space-y-2 max-h-48 overflow-auto">
                {alerts?.prodottiSottoScorta?.map((p, i) => (
                  <div key={i} className="flex items-center justify-between text-sm py-1.5 px-2 rounded bg-white/[0.02] hover:bg-white/[0.04]">
                    <span className="text-slate-400 truncate flex-1 mr-2">{p.nome}</span>
                    <span className={cn(
                      "font-mono text-xs",
                      p.urgenza === 'alta' ? "text-red-400" : "text-amber-400"
                    )}>
                      {p.quantita}/{p.quantita_minima}
                    </span>
                  </div>
                ))}
                {(!alerts?.prodottiSottoScorta || alerts.prodottiSottoScorta.length === 0) && (
                  <p className="text-xs text-slate-600 text-center py-2">Nessun prodotto sotto scorta</p>
                )}
              </div>
            </div>

            {/* Clienti Inattivi */}
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <UserX className="w-4 h-4 text-orange-400" />
                <span className="text-sm font-medium text-slate-300">Clienti Inattivi</span>
                <span className="ml-auto text-xs text-slate-500">{alerts?.clientiInattivi?.length || 0}</span>
              </div>
              <div className="space-y-2 max-h-48 overflow-auto">
                {alerts?.clientiInattivi?.map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-sm py-1.5 px-2 rounded bg-white/[0.02] hover:bg-white/[0.04]">
                    <div className="truncate flex-1 mr-2">
                      <span className="text-slate-400">{c.nome}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-xs text-slate-500">{c.giorni_inattivo}gg</span>
                    </div>
                  </div>
                ))}
                {(!alerts?.clientiInattivi || alerts.clientiInattivi.length === 0) && (
                  <p className="text-xs text-slate-600 text-center py-2">Tutti i clienti attivi</p>
                )}
              </div>
            </div>

            {/* Prodotti In Esaurimento */}
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="w-4 h-4 text-blue-400" />
                <span className="text-sm font-medium text-slate-300">In Esaurimento</span>
                <span className="ml-auto text-xs text-slate-500">{alerts?.prodottiInEsaurimento?.length || 0}</span>
              </div>
              <div className="space-y-2 max-h-48 overflow-auto">
                {alerts?.prodottiInEsaurimento?.map((p, i) => (
                  <div key={i} className="flex items-center justify-between text-sm py-1.5 px-2 rounded bg-white/[0.02] hover:bg-white/[0.04]">
                    <span className="text-slate-400 truncate flex-1 mr-2">{p.nome}</span>
                    <span className={cn(
                      "font-mono text-xs",
                      p.giorni_rimanenti <= 7 ? "text-red-400" : "text-blue-400"
                    )}>
                      {p.giorni_rimanenti}gg
                    </span>
                  </div>
                ))}
                {(!alerts?.prodottiInEsaurimento || alerts.prodottiInEsaurimento.length === 0) && (
                  <p className="text-xs text-slate-600 text-center py-2">Nessun prodotto in esaurimento</p>
                )}
              </div>
            </div>
          </div>
        )}
      </motion.div>

      {/* Modal Ricerca Prodotti */}
      <Dialog open={showSearchModal} onOpenChange={setShowSearchModal}>
        <DialogContent className="max-w-xl" data-testid="search-prodotto-modal">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl uppercase flex items-center gap-3">
              <Box className="w-5 h-5 text-emerald-500" />
              Cerca Prodotto
            </DialogTitle>
          </DialogHeader>
          
          <div className="mt-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Digita il nome del prodotto..."
                value={prodottoSearch}
                onChange={(e) => setProdottoSearch(e.target.value)}
                className="pl-10 h-12 text-base"
                autoFocus
                data-testid="search-prodotto-input"
              />
            </div>
            
            <div className="mt-4 max-h-[400px] overflow-auto">
              {prodottoSearch ? (
                filteredProdotti.length > 0 ? (
                  <div className="space-y-1">
                    {filteredProdotti.map((p, i) => (
                      <button
                        key={p.id || i}
                        className="w-full px-4 py-3 hover:bg-muted rounded-lg cursor-pointer text-left flex items-center justify-between transition-colors"
                        onClick={() => viewProdottoAnalisi(p)}
                        data-testid={`prodotto-result-${i}`}
                      >
                        <div className="flex items-center gap-3">
                          <Package className="w-5 h-5 text-emerald-500" />
                          <span className="font-medium">{p.nome}</span>
                        </div>
                        <div className="text-right">
                          <span className={cn(
                            "text-sm font-mono",
                            (p.quantita || 0) <= 0 ? "text-red-400" : "text-slate-400"
                          )}>
                            Qtà: {p.quantita?.toLocaleString('it-IT') || 0}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    Nessun prodotto trovato per "{prodottoSearch}"
                  </div>
                )
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Inizia a digitare per cercare...</p>
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Modal Analisi Prodotto */}
      <Dialog open={showProdottoModal} onOpenChange={setShowProdottoModal}>
        <DialogContent className="max-w-lg" data-testid="prodotto-analisi-modal">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl uppercase flex items-center gap-3">
              <Package className="w-5 h-5 text-emerald-500" />
              {selectedProdotto?.nome}
            </DialogTitle>
          </DialogHeader>
          
          {loadingAnalisi ? (
            <LoadingSpinner />
          ) : prodottoAnalisi ? (
            <div className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground mb-1">Fatturato Mensile</p>
                  <p className="font-heading text-2xl font-bold text-emerald-400">
                    {formatCurrency(prodottoAnalisi.fatturatoMensile || 0)}
                  </p>
                  <p className="text-xs text-muted-foreground">media 6 mesi</p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground mb-1">Prezzo Medio Vendita</p>
                  <p className="font-heading text-2xl font-bold text-blue-400">
                    {formatCurrency(prodottoAnalisi.prezzoMedioVendita || 0)}
                  </p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground mb-1">Trend Vendite</p>
                  <div className="flex items-center gap-2">
                    {(prodottoAnalisi.trendPercentuale || 0) >= 0 ? (
                      <TrendingUp className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <TrendingDown className="w-5 h-5 text-red-400" />
                    )}
                    <p className={cn(
                      "font-heading text-2xl font-bold",
                      (prodottoAnalisi.trendPercentuale || 0) >= 0 ? "text-emerald-400" : "text-red-400"
                    )}>
                      {prodottoAnalisi.trendPercentuale > 0 ? '+' : ''}{prodottoAnalisi.trendPercentuale || 0}%
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground">vs mese prec.</p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground mb-1">Clienti Unici</p>
                  <p className="font-heading text-2xl font-bold text-purple-400">
                    {prodottoAnalisi.clientiUnici || 0}
                  </p>
                </div>
              </div>
              
              <div className="p-4 bg-primary/10 rounded-lg">
                <p className="text-sm text-muted-foreground mb-1">Clienti Principali</p>
                <p className="font-medium text-primary">
                  {prodottoAnalisi.clientiPrincipali || 'Nessun dato'}
                </p>
              </div>

              {/* Info prodotto */}
              <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                <p className="text-sm text-muted-foreground mb-2">Stato Magazzino</p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-slate-500">Quantità</span>
                    <p className={cn(
                      "font-mono font-bold text-lg",
                      (selectedProdotto?.quantita || 0) <= 0 ? "text-red-400" : "text-emerald-400"
                    )}>
                      {selectedProdotto?.quantita?.toLocaleString('it-IT') || 0}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">Giorni Rimanenti</span>
                    <p className={cn(
                      "font-mono font-bold text-lg",
                      typeof prodottoAnalisi.giorniEsaurimento === 'number' && prodottoAnalisi.giorniEsaurimento < 14 
                        ? "text-red-400" 
                        : "text-blue-400"
                    )}>
                      {prodottoAnalisi.giorniEsaurimento || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">Vendita Media/Mese</span>
                    <p className="font-mono text-slate-300">
                      {prodottoAnalisi.mediaMensile?.toLocaleString('it-IT') || 0}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">Ultima Vendita</span>
                    <p className="font-mono text-slate-300">
                      {formatDate(prodottoAnalisi.ultimaVendita)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              Nessun dato di vendita per questo prodotto
            </div>
          )}
        </DialogContent>
      </Dialog>
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
