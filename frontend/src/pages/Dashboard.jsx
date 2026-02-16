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
  AlertCircle,
  Truck,
  Minus,
  ChevronDown,
  ChevronUp,
  Filter
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
  const [prodottoAnalisiAcquisti, setProdottoAnalisiAcquisti] = useState(null);
  const [loadingAnalisi, setLoadingAnalisi] = useState(false);
  const [analisiView, setAnalisiView] = useState('vendite');
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [alerts, setAlerts] = useState(null);
  const [loadingAlerts, setLoadingAlerts] = useState(true);
  
  // Trends state
  const [trendsVendite, setTrendsVendite] = useState(null);
  const [trendsExpanded, setTrendsExpanded] = useState(false);
  const [trendsPeriodo, setTrendsPeriodo] = useState('2w');
  const [trendsOrdinaPer, setTrendsOrdinaPer] = useState('interest');
  
  // Sales Insight state
  const [salesInsight, setSalesInsight] = useState(null);
  const [insightLoading, setInsightLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
    loadProdotti();
    loadAiSuggestion();
    loadAlerts();
    loadTrendsVendite();
    loadSalesInsight();
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

  const loadTrendsVendite = async (periodo = trendsPeriodo, ordinaPer = trendsOrdinaPer, limit = trendsExpanded ? 20 : 5) => {
    try {
      const response = await axios.get(`${API}/trends-vendite`, {
        params: { periodo, ordina_per: ordinaPer, limit }
      });
      setTrendsVendite(response.data);
    } catch (error) {
      console.error('Error loading trends:', error);
    }
  };

  const loadSalesInsight = async () => {
    setInsightLoading(true);
    try {
      const response = await axios.get(`${API}/sales-insight`);
      setSalesInsight(response.data);
    } catch (error) {
      console.error('Error loading sales insight:', error);
    } finally {
      setInsightLoading(false);
    }
  };

  const viewProdottoAnalisi = async (prodotto) => {
    setSelectedProdotto(prodotto);
    setShowSearchModal(false);
    setShowProdottoModal(true);
    setLoadingAnalisi(true);
    setProdottoSearch('');
    setAnalisiView('vendite');
    
    try {
      const [venditeRes, acquistiRes] = await Promise.all([
        axios.get(`${API}/prodotti/${encodeURIComponent(prodotto.nome)}/analisi`),
        axios.get(`${API}/prodotti/${encodeURIComponent(prodotto.nome)}/analisi-acquisti`)
      ]);
      setProdottoAnalisi(venditeRes.data);
      setProdottoAnalisiAcquisti(acquistiRes.data);
    } catch (error) {
      console.error('Error loading prodotto analisi:', error);
      setProdottoAnalisi(null);
      setProdottoAnalisiAcquisti(null);
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

  // Color map for insights
  const insightColorMap = {
    emerald: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', text: 'text-emerald-400', icon: 'text-emerald-400' },
    cyan: { bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', text: 'text-cyan-400', icon: 'text-cyan-400' },
    violet: { bg: 'bg-violet-500/10', border: 'border-violet-500/20', text: 'text-violet-400', icon: 'text-violet-400' },
    amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/20', text: 'text-amber-400', icon: 'text-amber-400' },
    blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/20', text: 'text-blue-400', icon: 'text-blue-400' },
    rose: { bg: 'bg-rose-500/10', border: 'border-rose-500/20', text: 'text-rose-400', icon: 'text-rose-400' },
    orange: { bg: 'bg-orange-500/10', border: 'border-orange-500/20', text: 'text-orange-400', icon: 'text-orange-400' },
  };

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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
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

      {/* Main Grid: AI + Insights + Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        
        {/* AI Suggestion Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2"
        >
          <div className="h-full relative overflow-hidden rounded-2xl bg-gradient-to-br from-violet-500/10 via-purple-500/5 to-fuchsia-500/10 border border-purple-500/20">
            <div className="absolute top-0 right-0 w-48 h-48 bg-purple-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
            
            <div className="relative p-5">
              <div className="flex items-start gap-4">
                <div className="p-2.5 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-purple-500/25">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-white">Suggerimento AI</h3>
                      <span className="px-2 py-0.5 text-[10px] bg-purple-500/20 text-purple-300 rounded-full">AI</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={refreshAiSuggestion}
                      disabled={loadingAi}
                      className="text-purple-300 hover:text-purple-200 hover:bg-purple-500/20 h-7 px-2"
                      data-testid="refresh-ai-btn"
                    >
                      <RefreshCw className={cn("w-3.5 h-3.5 mr-1", loadingAi && "animate-spin")} />
                      <span className="text-xs">Nuovo</span>
                    </Button>
                  </div>
                  
                  {loadingAi ? (
                    <div className="flex items-center gap-2 text-slate-400 text-sm">
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Analisi in corso...</span>
                    </div>
                  ) : aiSuggestion?.suggestion ? (
                    <>
                      <div className="flex items-center gap-2 mb-1.5">
                        <Lightbulb className="w-4 h-4 text-amber-400" />
                        <span className="text-sm font-medium text-purple-300">{aiSuggestion.suggestion.titolo}</span>
                      </div>
                      <p className="text-slate-300 text-sm leading-relaxed mb-2">
                        {aiSuggestion.suggestion.messaggio}
                      </p>
                      <span className="inline-block px-2.5 py-1 text-xs bg-white/5 text-purple-300 rounded-lg border border-purple-500/20">
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

        {/* Sales Insight Widget - Hover to expand details */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="rounded-2xl overflow-hidden border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01]"
          data-testid="sales-insight-widget"
        >
          <div className="p-4 border-b border-white/[0.06]">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-amber-500/15">
                <Lightbulb className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Sales Insight</h3>
                <p className="text-[10px] text-slate-500">{salesInsight?.mese_riferimento || 'Caricamento...'}</p>
              </div>
            </div>
          </div>

          <div className="p-3">
            {insightLoading ? (
              <div className="flex items-center justify-center h-32">
                <RefreshCw className="w-5 h-5 text-slate-600 animate-spin" />
              </div>
            ) : salesInsight?.insights?.length > 0 ? (
              <div className="space-y-1.5">
                {salesInsight.insights.slice(0, 5).map((insight) => {
                  const colors = insightColorMap[insight.colore] || insightColorMap.emerald;
                  return (
                    <div
                      key={insight.tipo}
                      className={cn(
                        "group relative flex items-center gap-2.5 px-3 py-2 rounded-lg border transition-all duration-200 cursor-default",
                        colors.bg, colors.border
                      )}
                    >
                      <span className="text-sm shrink-0">{insight.icona}</span>
                      <div className="flex-1 min-w-0">
                        <p className={cn("text-xs font-semibold truncate", colors.text)}>{insight.valore}</p>
                        <p className="text-[9px] text-slate-600 truncate">{insight.titolo}</p>
                      </div>
                      {/* Hover tooltip with details */}
                      <div className="absolute left-0 right-0 -bottom-1 translate-y-full opacity-0 group-hover:opacity-100 pointer-events-none z-20 transition-opacity duration-200">
                        <div className="mx-2 p-2.5 rounded-lg bg-slate-900/95 border border-white/10 shadow-xl backdrop-blur-sm">
                          <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-0.5">{insight.titolo}</p>
                          <p className={cn("text-xs font-semibold", colors.text)}>{insight.valore}</p>
                          <p className="text-[10px] text-slate-500 mt-1">{insight.dettaglio}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-6">
                <p className="text-xs text-slate-500">Nessun insight</p>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Second Row: Trends + Quick Links */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-6">
        
        {/* Trends Widget - Expandable */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={cn(
            "rounded-2xl overflow-hidden border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] transition-all duration-300",
            trendsExpanded && "lg:col-span-2"
          )}
          data-testid="trends-widget"
        >
          <div className="p-4 border-b border-white/[0.06] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-emerald-500/15">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Trend Prodotti</h3>
                <p className="text-[10px] text-slate-500">Top {trendsExpanded ? '20' : '5'} • {trendsVendite?.periodo_label || '2 settimane'}</p>
              </div>
            </div>
            <button
              onClick={() => {
                const newExpanded = !trendsExpanded;
                setTrendsExpanded(newExpanded);
                loadTrendsVendite(trendsPeriodo, trendsOrdinaPer, newExpanded ? 20 : 5);
              }}
              className="flex items-center gap-1 px-2 py-1 rounded-lg bg-white/[0.05] border border-white/[0.08] text-[10px] text-slate-400 hover:bg-white/[0.1] hover:text-white transition-all"
              data-testid="expand-trends-btn"
            >
              {trendsExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {trendsExpanded ? 'Riduci' : 'Espandi'}
            </button>
          </div>

          {/* Filters - only when expanded */}
          {trendsExpanded && (
            <div className="px-4 py-3 border-b border-white/[0.04] bg-white/[0.01]">
              <div className="flex flex-wrap gap-4">
                <div>
                  <span className="text-[9px] text-slate-600 uppercase tracking-wide block mb-1.5">Periodo</span>
                  <div className="flex gap-1">
                    {[{ v: '1w', l: '1S' }, { v: '2w', l: '2S' }, { v: '1m', l: '1M' }, { v: '3m', l: '3M' }].map(p => (
                      <button
                        key={p.v}
                        onClick={() => { setTrendsPeriodo(p.v); loadTrendsVendite(p.v, trendsOrdinaPer, 20); }}
                        className={cn(
                          'px-2 py-1 rounded text-[10px] font-medium transition-all',
                          trendsPeriodo === p.v
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : 'bg-white/[0.04] text-slate-500 border border-white/[0.06] hover:bg-white/[0.08]'
                        )}
                      >{p.l}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="text-[9px] text-slate-600 uppercase tracking-wide block mb-1.5">Ordina</span>
                  <div className="flex gap-1">
                    {[{ v: 'interest', l: 'Rilevanza' }, { v: 'fatturato', l: '€' }, { v: 'var_positiva', l: '↑' }, { v: 'var_negativa', l: '↓' }].map(o => (
                      <button
                        key={o.v}
                        onClick={() => { setTrendsOrdinaPer(o.v); loadTrendsVendite(trendsPeriodo, o.v, 20); }}
                        className={cn(
                          'px-2 py-1 rounded text-[10px] font-medium transition-all',
                          trendsOrdinaPer === o.v
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                            : 'bg-white/[0.04] text-slate-500 border border-white/[0.06] hover:bg-white/[0.08]'
                        )}
                      >{o.l}</button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className={cn("p-3", trendsExpanded && "max-h-[400px] overflow-auto")}>
            {trendsVendite?.top_prodotti ? (
              <div className={cn("space-y-1.5", trendsExpanded && "grid grid-cols-1 lg:grid-cols-2 gap-2 space-y-0")}>
                {trendsVendite.top_prodotti.map((t, idx) => (
                  <div
                    key={t.prodotto}
                    className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:bg-emerald-500/[0.04] transition-colors"
                  >
                    <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-slate-200 truncate">{t.prodotto}</p>
                      <p className="text-[10px] text-slate-600">€{t.fatturato_2w?.toLocaleString()} • {t.quantita_2w?.toLocaleString()} pz</p>
                    </div>
                    <div className={cn(
                      'flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold',
                      t.trend === 'up' && 'text-emerald-400 bg-emerald-500/10',
                      t.trend === 'down' && 'text-red-400 bg-red-500/10',
                      t.trend === 'stable' && 'text-slate-400 bg-slate-500/10'
                    )}>
                      {t.trend === 'up' && <TrendingUp className="w-3 h-3" />}
                      {t.trend === 'down' && <TrendingDown className="w-3 h-3" />}
                      {t.trend === 'stable' && <Minus className="w-3 h-3" />}
                      {t.variazione_qty_pct > 0 ? '+' : ''}{t.variazione_qty_pct}%
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-32">
                <RefreshCw className="w-5 h-5 text-slate-600 animate-spin" />
              </div>
            )}
          </div>
        </motion.div>

        {/* Quick Links - shrinks when trends expanded */}
        <div className={cn("space-y-3", trendsExpanded && "lg:col-span-1")}>
          <QuickLinkCard
            title="Importa Dati"
            description="Carica CSV o XLSX"
            href="/upload"
            icon={Upload}
            gradient="from-blue-500 to-blue-600"
          />
          <QuickLinkCard
            title="Statistiche"
            description="Analizza vendite"
            href="/statistiche"
            icon={BarChart3}
            gradient="from-purple-500 to-purple-600"
          />
          <QuickLinkCard
            title="Magazzino"
            description="Gestisci scorte"
            href="/magazzino"
            icon={Package}
            gradient="from-emerald-500 to-emerald-600"
          />
        </div>
      </div>

      {/* Alert Gestione */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="rounded-2xl overflow-hidden border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01]"
      >
        <div className="p-4 border-b border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-amber-500/10">
              <AlertCircle className="w-4 h-4 text-amber-400" />
            </div>
            <h2 className="font-semibold text-white">Centro Alert</h2>
            {totalAlerts > 0 && (
              <span className="px-2 py-0.5 text-[10px] bg-amber-500/20 text-amber-300 rounded-full">
                {totalAlerts}
              </span>
            )}
          </div>
        </div>
        
        {loadingAlerts ? (
          <div className="p-8 text-center">
            <LoadingSpinner />
          </div>
        ) : totalAlerts === 0 ? (
          <div className="p-10 text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-emerald-500/10 flex items-center justify-center">
              <Box className="w-6 h-6 text-emerald-500" />
            </div>
            <p className="text-emerald-400 font-medium text-sm">Tutto sotto controllo!</p>
            <p className="text-xs text-slate-500 mt-1">Nessun alert attivo</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 divide-y lg:divide-y-0 lg:divide-x divide-white/[0.05]">
            {/* Prodotti Sotto Scorta */}
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <PackageX className="w-4 h-4 text-red-400" />
                <span className="text-xs font-medium text-slate-300">Sotto Scorta</span>
                <span className="ml-auto text-[10px] text-slate-500">{alerts?.prodottiSottoScorta?.length || 0}</span>
              </div>
              <div className="space-y-1.5 max-h-40 overflow-auto">
                {alerts?.prodottiSottoScorta?.map((p, i) => (
                  <div key={i} className="flex items-center justify-between text-xs py-1.5 px-2 rounded bg-white/[0.02] hover:bg-white/[0.04]">
                    <span className="text-slate-400 truncate flex-1 mr-2">{p.nome}</span>
                    <span className={cn("font-mono text-[10px]", p.urgenza === 'alta' ? "text-red-400" : "text-amber-400")}>
                      {p.quantita}/{p.quantita_minima}
                    </span>
                  </div>
                ))}
                {(!alerts?.prodottiSottoScorta || alerts.prodottiSottoScorta.length === 0) && (
                  <p className="text-[10px] text-slate-600 text-center py-2">Nessuno</p>
                )}
              </div>
            </div>

            {/* Clienti Inattivi */}
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <UserX className="w-4 h-4 text-orange-400" />
                <span className="text-xs font-medium text-slate-300">Clienti Inattivi</span>
                <span className="ml-auto text-[10px] text-slate-500">{alerts?.clientiInattivi?.length || 0}</span>
              </div>
              <div className="space-y-1.5 max-h-40 overflow-auto">
                {alerts?.clientiInattivi?.map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-xs py-1.5 px-2 rounded bg-white/[0.02] hover:bg-white/[0.04]">
                    <span className="text-slate-400 truncate flex-1 mr-2">{c.nome}</span>
                    <span className="text-[10px] text-slate-500">{c.giorni_inattivo}gg</span>
                  </div>
                ))}
                {(!alerts?.clientiInattivi || alerts.clientiInattivi.length === 0) && (
                  <p className="text-[10px] text-slate-600 text-center py-2">Tutti attivi</p>
                )}
              </div>
            </div>

            {/* Prodotti In Esaurimento */}
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="w-4 h-4 text-blue-400" />
                <span className="text-xs font-medium text-slate-300">In Esaurimento</span>
                <span className="ml-auto text-[10px] text-slate-500">{alerts?.prodottiInEsaurimento?.length || 0}</span>
              </div>
              <div className="space-y-1.5 max-h-40 overflow-auto">
                {alerts?.prodottiInEsaurimento?.map((p, i) => (
                  <div key={i} className="flex items-center justify-between text-xs py-1.5 px-2 rounded bg-white/[0.02] hover:bg-white/[0.04]">
                    <span className="text-slate-400 truncate flex-1 mr-2">{p.nome}</span>
                    <span className={cn("font-mono text-[10px]", p.giorni_rimanenti <= 7 ? "text-red-400" : "text-blue-400")}>
                      {p.giorni_rimanenti}gg
                    </span>
                  </div>
                ))}
                {(!alerts?.prodottiInEsaurimento || alerts.prodottiInEsaurimento.length === 0) && (
                  <p className="text-[10px] text-slate-600 text-center py-2">Nessuno</p>
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
          
          {/* Switch Vendite/Acquisti */}
          <div className="flex p-1 bg-slate-800 rounded-lg mt-2">
            <button
              onClick={() => setAnalisiView('vendite')}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-all",
                analisiView === 'vendite' 
                  ? "bg-emerald-500/20 text-emerald-400 shadow-sm" 
                  : "text-slate-400 hover:text-slate-300"
              )}
              data-testid="switch-vendite"
            >
              <Users className="w-4 h-4" />
              Vendite / Clienti
            </button>
            <button
              onClick={() => setAnalisiView('acquisti')}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-all",
                analisiView === 'acquisti' 
                  ? "bg-blue-500/20 text-blue-400 shadow-sm" 
                  : "text-slate-400 hover:text-slate-300"
              )}
              data-testid="switch-acquisti"
            >
              <Truck className="w-4 h-4" />
              Acquisti / Fornitori
            </button>
          </div>
          
          {loadingAnalisi ? (
            <LoadingSpinner />
          ) : analisiView === 'vendite' ? (
            // Vista Vendite/Clienti
            prodottoAnalisi ? (
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
                
                <div className="p-4 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                  <p className="text-sm text-muted-foreground mb-1">Clienti Principali</p>
                  <p className="font-medium text-emerald-400">
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
            )
          ) : (
            // Vista Acquisti/Fornitori
            prodottoAnalisiAcquisti ? (
              <div className="space-y-4 mt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-muted rounded-lg">
                    <p className="text-sm text-muted-foreground mb-1">Speso Mensile</p>
                    <p className="font-heading text-2xl font-bold text-blue-400">
                      {formatCurrency(prodottoAnalisiAcquisti.spesoMensile || 0)}
                    </p>
                    <p className="text-xs text-muted-foreground">media 6 mesi</p>
                  </div>
                  <div className="p-4 bg-muted rounded-lg">
                    <p className="text-sm text-muted-foreground mb-1">Prezzo Medio Acquisto</p>
                    <p className="font-heading text-2xl font-bold text-amber-400">
                      {formatCurrency(prodottoAnalisiAcquisti.prezzoMedioAcquisto || 0)}
                    </p>
                  </div>
                  <div className="p-4 bg-muted rounded-lg">
                    <p className="text-sm text-muted-foreground mb-1">Trend Acquisti</p>
                    <div className="flex items-center gap-2">
                      {(prodottoAnalisiAcquisti.trendPercentuale || 0) >= 0 ? (
                        <TrendingUp className="w-5 h-5 text-blue-400" />
                      ) : (
                        <TrendingDown className="w-5 h-5 text-emerald-400" />
                      )}
                      <p className={cn(
                        "font-heading text-2xl font-bold",
                        (prodottoAnalisiAcquisti.trendPercentuale || 0) >= 0 ? "text-blue-400" : "text-emerald-400"
                      )}>
                        {prodottoAnalisiAcquisti.trendPercentuale > 0 ? '+' : ''}{prodottoAnalisiAcquisti.trendPercentuale || 0}%
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground">vs mese prec.</p>
                  </div>
                  <div className="p-4 bg-muted rounded-lg">
                    <p className="text-sm text-muted-foreground mb-1">Fornitori Unici</p>
                    <p className="font-heading text-2xl font-bold text-purple-400">
                      {prodottoAnalisiAcquisti.fornitoriUnici || 0}
                    </p>
                  </div>
                </div>
                
                <div className="p-4 bg-blue-500/10 rounded-lg border border-blue-500/20">
                  <p className="text-sm text-muted-foreground mb-1">Fornitori Principali</p>
                  <p className="font-medium text-blue-400">
                    {prodottoAnalisiAcquisti.fornitoriPrincipali || 'Nessun dato'}
                  </p>
                </div>

                {/* Info acquisti */}
                <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                  <p className="text-sm text-muted-foreground mb-2">Storico Acquisti</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-xs text-slate-500">Ordini Ultimo Mese</span>
                      <p className="font-mono font-bold text-lg text-blue-400">
                        {prodottoAnalisiAcquisti.ordiniUltimoMese || 0}
                      </p>
                      <span className="text-xs text-slate-500">
                        {prodottoAnalisiAcquisti.meseRiferimento || ''}
                      </span>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500">Ultimo Acquisto</span>
                      <p className="font-mono text-slate-300">
                        {formatDate(prodottoAnalisiAcquisti.ultimoAcquisto)}
                      </p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500">Acquisto Medio/Mese</span>
                      <p className="font-mono text-slate-300">
                        {prodottoAnalisiAcquisti.mediaMensile?.toLocaleString('it-IT') || 0}
                      </p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500">Quantità Attuale</span>
                      <p className={cn(
                        "font-mono font-bold text-lg",
                        (selectedProdotto?.quantita || 0) <= 0 ? "text-red-400" : "text-emerald-400"
                      )}>
                        {selectedProdotto?.quantita?.toLocaleString('it-IT') || 0}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Nessun dato di acquisto per questo prodotto
              </div>
            )
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
      className="group block p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-blue-500/30 hover:bg-white/[0.05] transition-all duration-300"
    >
      <div className="flex items-center gap-3">
        <div className={cn(
          'p-2.5 rounded-lg bg-gradient-to-br shadow-lg transition-all duration-300',
          gradient,
          'group-hover:scale-105'
        )}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-sm text-slate-200 group-hover:text-white transition-colors">
            {title}
          </h3>
          <p className="text-[11px] text-slate-500 truncate">{description}</p>
        </div>
        <ArrowUpRight className="w-4 h-4 text-slate-600 group-hover:text-blue-400 
          transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all shrink-0" />
      </div>
    </Link>
  );
}
