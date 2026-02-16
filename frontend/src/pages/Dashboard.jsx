import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import {
  Euro, ShoppingCart, Users, Package, AlertTriangle, ArrowUpRight, Upload,
  BarChart3, TrendingUp, TrendingDown, Search, Box, Sparkles, Lightbulb,
  RefreshCw, Clock, UserX, PackageX, AlertCircle, Minus, X, Filter,
  ArrowDownAZ, Activity, Plus, ChevronRight, Calendar
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import StatCard from '@/components/StatCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { formatCurrency, formatDate, cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [prodotti, setProdotti] = useState([]);
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [prodottoSearch, setProdottoSearch] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [showProdottoModal, setShowProdottoModal] = useState(false);
  const [selectedProdotto, setSelectedProdotto] = useState(null);
  const [prodottoAnalisi, setProdottoAnalisi] = useState(null);
  const [prodottoAnalisiAcquisti, setProdottoAnalisiAcquisti] = useState(null);
  const [loadingAnalisi, setLoadingAnalisi] = useState(false);
  const [analisiView, setAnalisiView] = useState('vendite');
  const [analisiPeriodo, setAnalisiPeriodo] = useState('1m'); // 1m, 3m, 6m, all
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [alerts, setAlerts] = useState(null);
  const [loadingAlerts, setLoadingAlerts] = useState(false);

  // Trends state
  const [trendsVendite, setTrendsVendite] = useState(null);
  const [showTrendsPopup, setShowTrendsPopup] = useState(false);
  const [trendsPeriodo, setTrendsPeriodo] = useState('2w');
  const [trendsOrdinaPer, setTrendsOrdinaPer] = useState('interest');

  // Sales Insight state
  const [salesInsight, setSalesInsight] = useState(null);
  const [insightLoading, setInsightLoading] = useState(false);
  
  // Margine state
  const [margineData, setMargineData] = useState(null);
  
  // AI Floating state
  const [showAiPopup, setShowAiPopup] = useState(false);

  useEffect(() => {
    // Load all data in parallel - non-blocking
    const loadAll = async () => {
      // Critical data first
      axios.get(`${API}/dashboard`).then(r => { setData(r.data); setLoading(false); }).catch(() => setLoading(false));
      
      // Secondary data - non-blocking
      axios.get(`${API}/trends-vendite?limite=5`).then(r => setTrendsVendite(r.data)).catch(() => {});
      axios.get(`${API}/sales-insight`).then(r => setSalesInsight(r.data)).catch(() => {});
      axios.get(`${API}/ai-suggestion`).then(r => setAiSuggestion(r.data)).catch(() => {});
      axios.get(`${API}/alerts`).then(r => setAlerts(r.data)).catch(() => {});
      axios.get(`${API}/margine-vendite`).then(r => setMargineData(r.data)).catch(() => {});
    };
    loadAll();
  }, []);

  const refreshAiSuggestion = async () => {
    setLoadingAi(true);
    try {
      const response = await axios.post(`${API}/ai-suggestion/refresh`);
      setAiSuggestion(response.data);
    } catch (e) {} finally { setLoadingAi(false); }
  };

  const loadTrendsVendite = useCallback(async (periodo, ordinaPer, limit = 20) => {
    try {
      const response = await axios.get(`${API}/trends-vendite`, {
        params: { periodo, ordina_per: ordinaPer, limite: limit }
      });
      setTrendsVendite(response.data);
    } catch (e) {}
  }, []);

  // Server-side search for products
  const searchProdotti = useCallback(async (query) => {
    if (!query || query.trim().length === 0) {
      setSearchResults([]);
      return;
    }
    setSearchLoading(true);
    try {
      const response = await axios.get(`${API}/prodotti/search`, { params: { q: query, limit: 30 } });
      setSearchResults(response.data);
    } catch (e) {
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }, []);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      searchProdotti(prodottoSearch);
    }, 300);
    return () => clearTimeout(timer);
  }, [prodottoSearch, searchProdotti]);

  const viewProdottoAnalisi = async (prodotto, periodo = '1m') => {
    setSelectedProdotto(prodotto);
    setShowSearchModal(false);
    setShowProdottoModal(true);
    setLoadingAnalisi(true);
    setProdottoSearch('');
    setAnalisiView('vendite');
    setAnalisiPeriodo(periodo);
    try {
      const [venditeRes, acquistiRes] = await Promise.all([
        axios.get(`${API}/prodotti/${encodeURIComponent(prodotto.nome)}/analisi`, { params: { periodo } }),
        axios.get(`${API}/prodotti/${encodeURIComponent(prodotto.nome)}/analisi-acquisti`, { params: { periodo } })
      ]);
      setProdottoAnalisi(venditeRes.data);
      setProdottoAnalisiAcquisti(acquistiRes.data);
    } catch (e) {
      setProdottoAnalisi(null);
      setProdottoAnalisiAcquisti(null);
    } finally { setLoadingAnalisi(false); }
  };

  const changeAnalisiPeriodo = async (newPeriodo) => {
    if (!selectedProdotto || newPeriodo === analisiPeriodo) return;
    setAnalisiPeriodo(newPeriodo);
    setLoadingAnalisi(true);
    try {
      const [venditeRes, acquistiRes] = await Promise.all([
        axios.get(`${API}/prodotti/${encodeURIComponent(selectedProdotto.nome)}/analisi`, { params: { periodo: newPeriodo } }),
        axios.get(`${API}/prodotti/${encodeURIComponent(selectedProdotto.nome)}/analisi-acquisti`, { params: { periodo: newPeriodo } })
      ]);
      setProdottoAnalisi(venditeRes.data);
      setProdottoAnalisiAcquisti(acquistiRes.data);
    } catch (e) {
      // Keep existing data on error
    } finally { setLoadingAnalisi(false); }
  };

  const filteredProdotti = searchResults;

  if (loading) return <LoadingSpinner fullScreen />;

  const totalAlerts = (alerts?.prodottiSottoScorta?.length || 0) +
                      (alerts?.clientiInattivi?.length || 0) +
                      (alerts?.prodottiInEsaurimento?.length || 0);

  const insightColors = {
    emerald: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
    cyan: 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400',
    violet: 'bg-violet-500/10 border-violet-500/20 text-violet-400',
    amber: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
    blue: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
    rose: 'bg-rose-500/10 border-rose-500/20 text-rose-400',
    orange: 'bg-orange-500/10 border-orange-500/20 text-orange-400',
  };

  const periodoOptions = [
    { v: '1w', l: '1 Sett.' },
    { v: '2w', l: '2 Sett.' },
    { v: '1m', l: '1 Mese' },
  ];
  const ordinaPerOptions = [
    { v: 'interest', l: 'Interesse' },
    { v: 'qty', l: 'Quantità' },
    { v: 'revenue', l: 'Fatturato' },
  ];

  return (
    <PageWrapper>
      <PageHeader title="Dashboard" subtitle="Panoramica attività">
        <Button variant="outline" onClick={() => setShowSearchModal(true)} className="gap-2 h-9" data-testid="open-search-prodotto">
          <Search className="w-4 h-4" /> <span className="hidden sm:inline">Cerca</span>
        </Button>
      </PageHeader>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <StatCard label="Fatturato" value={data?.fatturatoMese || 0} format="currency" icon={Euro} gradient="blue"
          trend={data?.crescitaPercentuale > 0 ? 'up' : data?.crescitaPercentuale < 0 ? 'down' : 'neutral'}
          trendValue={data?.crescitaPercentuale}
          subtitle={margineData?.margine_medio_pct > 0 
            ? `Margine: +${margineData.margine_medio_pct.toFixed(1)}% · Profitto: ${formatCurrency(margineData.profitto_totale || 0)}`
            : (data?.fatturatoMesePrec ? `Mese prec: ${formatCurrency(data.fatturatoMesePrec)}` : null)} />
        <StatCard label="Ordini Mese" value={data?.ordiniMese || 0} icon={ShoppingCart} gradient="emerald" />
        <StatCard label="Clienti Mese" value={data?.nuoviClienti || 0} icon={Users} gradient="cyan" />
        <StatCard label="Alert" value={totalAlerts} icon={AlertTriangle} gradient="amber" />
      </div>

      {/* Main Content Grid - 2 widgets per row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* Sales Insight - improved text visibility */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
          className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] overflow-hidden"
          data-testid="sales-insight-widget">
          <div className="px-4 py-3 border-b border-white/[0.06] flex items-center gap-2">
            <div className="p-2 rounded-md bg-amber-500/15">
              <Lightbulb className="w-4 h-4 text-amber-400" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold text-white">Sales Insight</h3>
              <p className="text-xs text-slate-500 truncate">{salesInsight?.mese_riferimento || ''}</p>
            </div>
          </div>
          <div className="p-3">
            {insightLoading ? (
              <div className="flex items-center justify-center h-24"><RefreshCw className="w-4 h-4 text-slate-600 animate-spin" /></div>
            ) : salesInsight?.insights?.length > 0 ? (
              <div className="space-y-2">
                {salesInsight.insights.slice(0, 4).map((ins) => (
                  <div key={ins.tipo} className={cn("px-3 py-2.5 rounded-lg border", insightColors[ins.colore] || insightColors.emerald)}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-base">{ins.icona}</span>
                      <span className="font-semibold text-sm truncate flex-1">{ins.valore}</span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed pl-7">{ins.dettaglio || ins.titolo}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center py-4 text-xs text-slate-500">Nessun insight</p>
            )}
          </div>
        </motion.div>
      </div>

      {/* Second Row: Trends + Quick Links - 2 columns aligned */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* Trends Widget */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] overflow-hidden relative"
          data-testid="trends-widget">
          <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-md bg-emerald-500/15">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Trend Prodotti</h3>
                <p className="text-xs text-slate-500">Top 5</p>
              </div>
            </div>
            {/* Visible selectors */}
            <div className="flex items-center gap-2" data-testid="trends-selectors">
              <div className="flex items-center gap-1 bg-white/[0.04] rounded-lg p-0.5">
                <Clock className="w-3.5 h-3.5 text-slate-500 ml-1" />
                {periodoOptions.map(p => (
                  <button key={p.v} onClick={(e) => { e.stopPropagation(); setTrendsPeriodo(p.v); loadTrendsVendite(p.v, trendsOrdinaPer, 5); }}
                    data-testid={`trend-periodo-${p.v}`}
                    className={cn("px-2.5 py-1.5 rounded-md text-xs font-medium transition-all",
                      trendsPeriodo === p.v ? "bg-emerald-500/20 text-emerald-300 shadow-sm" : "text-slate-500 hover:text-slate-300"
                    )}>{p.l}</button>
                ))}
              </div>
              <div className="flex items-center gap-1 bg-white/[0.04] rounded-lg p-0.5">
                <ArrowDownAZ className="w-3.5 h-3.5 text-slate-500 ml-1" />
                {ordinaPerOptions.map(o => (
                  <button key={o.v} onClick={(e) => { e.stopPropagation(); setTrendsOrdinaPer(o.v); loadTrendsVendite(trendsPeriodo, o.v, 5); }}
                    data-testid={`trend-ordina-${o.v}`}
                    className={cn("px-2.5 py-1.5 rounded-md text-xs font-medium transition-all",
                      trendsOrdinaPer === o.v ? "bg-emerald-500/20 text-emerald-300 shadow-sm" : "text-slate-500 hover:text-slate-300"
                    )}>{o.l}</button>
                ))}
              </div>
              {/* Plus button to expand */}
              <button 
                onClick={() => { setShowTrendsPopup(true); loadTrendsVendite(trendsPeriodo, trendsOrdinaPer, 20); }}
                data-testid="trends-expand-btn"
                className="p-2 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 transition-all hover:scale-105"
                title="Mostra top 20"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="p-3">
            {trendsVendite?.top_prodotti ? (
              <div className="space-y-1.5">
                {trendsVendite.top_prodotti.slice(0, 5).map((t, idx) => (
                  <div key={t.prodotto} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold flex items-center justify-center">{idx + 1}</span>
                    <span className="flex-1 text-sm text-slate-300 truncate">{t.prodotto}</span>
                    <span className={cn("text-xs font-semibold px-2 py-1 rounded",
                      t.trend === 'up' ? 'text-emerald-400 bg-emerald-500/10' : t.trend === 'down' ? 'text-red-400 bg-red-500/10' : 'text-slate-400 bg-slate-500/10'
                    )}>{t.variazione_qty_pct > 0 ? '+' : ''}{t.variazione_qty_pct}%</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-24"><RefreshCw className="w-4 h-4 text-slate-600 animate-spin" /></div>
            )}
          </div>

          {/* Popup Modal - Full Trends (with current filters applied) */}
          <AnimatePresence>
            {showTrendsPopup && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="absolute inset-0 z-40 bg-slate-900/98 backdrop-blur-sm rounded-xl border border-emerald-500/20 overflow-hidden"
              >
                <div className="px-3 py-2 border-b border-white/[0.08] flex items-center justify-between bg-emerald-500/5">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-semibold text-white">Top 20 Prodotti</span>
                    <span className="text-[9px] text-slate-500">
                      ({periodoOptions.find(p => p.v === trendsPeriodo)?.l} - {ordinaPerOptions.find(o => o.v === trendsOrdinaPer)?.l})
                    </span>
                  </div>
                  <button 
                    onClick={() => setShowTrendsPopup(false)}
                    className="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                    data-testid="trends-close-btn"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="p-2 max-h-[280px] overflow-auto">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
                    {trendsVendite?.top_prodotti?.slice(0, 20).map((t, idx) => (
                      <div key={t.prodotto} className="flex items-center gap-2 px-2 py-1.5 rounded bg-white/[0.02] border border-white/[0.04]">
                        <span className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 text-[8px] font-bold flex items-center justify-center shrink-0">{idx + 1}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-[10px] text-slate-300 truncate">{t.prodotto}</p>
                          <p className="text-[8px] text-slate-600">&euro;{t.fatturato_2w?.toLocaleString()}</p>
                        </div>
                        <span className={cn("text-[9px] font-medium",
                          t.trend === 'up' ? 'text-emerald-400' : t.trend === 'down' ? 'text-red-400' : 'text-slate-400'
                        )}>{t.variazione_qty_pct > 0 ? '+' : ''}{t.variazione_qty_pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Quick Links - Column layout */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="flex flex-col gap-2" data-testid="quick-links">
          <QuickLink href="/upload" icon={Upload} label="Importa" color="blue" />
          <QuickLink href="/statistiche" icon={BarChart3} label="Statistiche" color="purple" />
          <QuickLink href="/magazzino" icon={Package} label="Magazzino" color="emerald" />
        </motion.div>
      </div>

      {/* Alerts Section */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
        className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] overflow-hidden mb-4">
        <div className="px-4 py-3 border-b border-white/[0.06] flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-400" />
          <span className="text-sm font-semibold text-white">Alert</span>
          {totalAlerts > 0 && <span className="px-2 py-0.5 text-xs bg-amber-500/20 text-amber-300 rounded">{totalAlerts}</span>}
        </div>
        {loadingAlerts ? (
          <div className="p-6 text-center"><RefreshCw className="w-4 h-4 animate-spin mx-auto text-slate-600" /></div>
        ) : totalAlerts === 0 ? (
          <div className="p-6 text-center">
            <Box className="w-8 h-8 mx-auto text-emerald-500/50 mb-1" />
            <p className="text-xs text-emerald-400">Tutto OK</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-white/[0.05]">
            <AlertColumn icon={PackageX} title="Sotto Scorta" items={alerts?.prodottiSottoScorta} color="red" />
            <AlertColumn icon={UserX} title="Clienti Inattivi" items={alerts?.clientiInattivi} color="orange" />
            <AlertColumn icon={Clock} title="In Esaurimento" items={alerts?.prodottiInEsaurimento} color="blue" />
          </div>
        )}
      </motion.div>

      {/* Search Modal */}
      <Dialog open={showSearchModal} onOpenChange={setShowSearchModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader><DialogTitle>Cerca Prodotto</DialogTitle></DialogHeader>
          <Input placeholder="Inizia a digitare per cercare..." value={prodottoSearch} onChange={(e) => setProdottoSearch(e.target.value)} autoFocus data-testid="search-prodotto-input" />
          <div className="max-h-64 overflow-auto space-y-1 mt-2">
            {prodottoSearch.trim().length === 0 ? (
              <p className="text-center py-6 text-sm text-slate-500">Digita almeno un carattere per cercare</p>
            ) : searchLoading ? (
              <div className="flex items-center justify-center py-6">
                <RefreshCw className="w-4 h-4 animate-spin text-slate-500" />
              </div>
            ) : filteredProdotti.length === 0 ? (
              <p className="text-center py-6 text-sm text-slate-500">Nessun prodotto trovato</p>
            ) : (
              filteredProdotti.map((p) => (
                <button key={p.codice || p.nome} onClick={() => viewProdottoAnalisi(p)}
                  data-testid={`search-result-${p.nome}`}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-white/5 transition-colors">
                  <p className="text-sm font-medium text-slate-200 truncate">{p.nome}</p>
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <span>Qty: {p.quantita || 0}</span>
                    {p.ultimo_prezzo_acquisto > 0 && (
                      <span className="text-emerald-400">Costo: €{p.ultimo_prezzo_acquisto?.toFixed(2)}</span>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Product Analysis Modal - Complete Details with Charts */}
      <Dialog open={showProdottoModal} onOpenChange={setShowProdottoModal}>
        <DialogContent className="sm:max-w-3xl max-h-[85vh] overflow-auto">
          <DialogHeader><DialogTitle>{selectedProdotto?.nome}</DialogTitle></DialogHeader>
          
          {/* Period Selector + View Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-white/[0.06]">
            <div className="flex gap-2">
              <Button variant={analisiView === 'vendite' ? 'default' : 'outline'} size="sm" onClick={() => setAnalisiView('vendite')} data-testid="analisi-vendite-tab">Vendite</Button>
              <Button variant={analisiView === 'acquisti' ? 'default' : 'outline'} size="sm" onClick={() => setAnalisiView('acquisti')} data-testid="analisi-acquisti-tab">Acquisti</Button>
            </div>
            <div className="flex items-center gap-1 bg-white/[0.04] rounded-lg p-0.5">
              <Calendar className="w-3 h-3 text-slate-500 ml-1" />
              {[
                { v: '1m', l: 'Mese' },
                { v: '3m', l: '3 Mesi' },
                { v: '6m', l: '6 Mesi' },
                { v: 'all', l: 'Tutto' }
              ].map(p => (
                <button 
                  key={p.v} 
                  onClick={() => changeAnalisiPeriodo(p.v)}
                  disabled={loadingAnalisi}
                  data-testid={`analisi-periodo-${p.v}`}
                  className={cn(
                    "px-2 py-1 rounded-md text-[10px] font-medium transition-all",
                    analisiPeriodo === p.v 
                      ? "bg-blue-500/20 text-blue-300 shadow-sm" 
                      : "text-slate-500 hover:text-slate-300"
                  )}
                >
                  {p.l}
                </button>
              ))}
            </div>
          </div>
          
          {loadingAnalisi ? (
            <div className="py-8 text-center"><LoadingSpinner /></div>
          ) : (
            <div className="space-y-4">
              {analisiView === 'vendite' && prodottoAnalisi && (
                <div className="space-y-4">
                  {/* Period Label */}
                  <p className="text-[10px] text-slate-500 text-right">
                    Periodo: {analisiPeriodo === '1m' ? 'Ultimo mese' : analisiPeriodo === '3m' ? 'Ultimi 3 mesi' : analisiPeriodo === '6m' ? 'Ultimi 6 mesi' : 'Storico completo'}
                  </p>
                  
                  {/* Main Stats Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                      <p className="text-[10px] text-slate-500 mb-0.5">Totale Venduto</p>
                      <p className="text-lg font-bold text-white">{formatCurrency(prodottoAnalisi.totale_venduto || 0)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                      <p className="text-[10px] text-slate-500 mb-0.5">Quantità</p>
                      <p className="text-lg font-bold text-white">{Math.round(prodottoAnalisi.quantita_venduta || 0)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                      <p className="text-[10px] text-slate-500 mb-0.5">Prezzo Medio</p>
                      <p className="text-lg font-bold text-white">{formatCurrency(prodottoAnalisi.prezzo_medio || 0)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                      <p className="text-[10px] text-slate-500 mb-0.5">N. Clienti</p>
                      <p className="text-lg font-bold text-white">{prodottoAnalisi.numero_clienti || 0}</p>
                    </div>
                  </div>
                  
                  {/* Top Clienti */}
                  {prodottoAnalisi.topClienti?.length > 0 && (
                    <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3">
                      <h4 className="text-xs font-semibold text-white mb-2 flex items-center gap-2">
                        <Users className="w-3.5 h-3.5 text-cyan-400" /> Top Clienti
                      </h4>
                      <div className="space-y-1.5">
                        {prodottoAnalisi.topClienti.slice(0, 5).map((c, i) => (
                          <div key={c.nome} className="flex items-center gap-2 text-sm">
                            <span className="w-5 h-5 rounded-full bg-cyan-500/15 text-cyan-400 text-[10px] font-bold flex items-center justify-center">{i + 1}</span>
                            <span className="flex-1 text-slate-300 truncate text-xs">{c.nome}</span>
                            <span className="text-cyan-400 font-medium text-xs">{formatCurrency(c.totale)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Vendite Mensili - Line Chart */}
                  {prodottoAnalisi.venditeMensili?.length > 1 && (
                    <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3">
                      <h4 className="text-xs font-semibold text-white mb-3 flex items-center gap-2">
                        <TrendingUp className="w-3.5 h-3.5 text-violet-400" /> Andamento Vendite
                      </h4>
                      <div className="h-[180px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={prodottoAnalisi.venditeMensili}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                            <XAxis dataKey="mese" stroke="#475569" fontSize={10} tickFormatter={v => v?.slice(-5)} />
                            <YAxis stroke="#475569" fontSize={10} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                            <Tooltip 
                              contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                              labelStyle={{ color: '#94a3b8' }}
                              formatter={(v) => [formatCurrency(v), 'Fatturato']}
                            />
                            <Line type="monotone" dataKey="totale" stroke="#8b5cf6" strokeWidth={2} dot={{ fill: '#8b5cf6', r: 3 }} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {analisiView === 'acquisti' && prodottoAnalisiAcquisti && (
                <div className="space-y-4">
                  {/* Period Label */}
                  <p className="text-[10px] text-slate-500 text-right">
                    Periodo: {analisiPeriodo === '1m' ? 'Ultimo mese' : analisiPeriodo === '3m' ? 'Ultimi 3 mesi' : analisiPeriodo === '6m' ? 'Ultimi 6 mesi' : 'Storico completo'}
                  </p>
                  
                  {/* Main Stats Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                      <p className="text-[10px] text-slate-500 mb-0.5">Totale Acquistato</p>
                      <p className="text-lg font-bold text-white">{formatCurrency(prodottoAnalisiAcquisti.totale_acquistato || 0)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                      <p className="text-[10px] text-slate-500 mb-0.5">Quantità</p>
                      <p className="text-lg font-bold text-white">{Math.round(prodottoAnalisiAcquisti.quantita_acquistata || 0)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                      <p className="text-[10px] text-slate-500 mb-0.5">Costo Medio</p>
                      <p className="text-lg font-bold text-white">{formatCurrency(prodottoAnalisiAcquisti.costo_medio || 0)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                      <p className="text-[10px] text-slate-500 mb-0.5">N. Fornitori</p>
                      <p className="text-lg font-bold text-white">{prodottoAnalisiAcquisti.numero_fornitori || 0}</p>
                    </div>
                  </div>
                  
                  {/* Top Fornitori */}
                  {prodottoAnalisiAcquisti.topFornitori?.length > 0 && (
                    <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3">
                      <h4 className="text-xs font-semibold text-white mb-2 flex items-center gap-2">
                        <Package className="w-3.5 h-3.5 text-orange-400" /> Top Fornitori
                      </h4>
                      <div className="space-y-1.5">
                        {prodottoAnalisiAcquisti.topFornitori.slice(0, 5).map((f, i) => (
                          <div key={f.nome} className="flex items-center gap-2 text-sm">
                            <span className="w-5 h-5 rounded-full bg-orange-500/15 text-orange-400 text-[10px] font-bold flex items-center justify-center">{i + 1}</span>
                            <span className="flex-1 text-slate-300 truncate text-xs">{f.nome}</span>
                            <span className="text-orange-400 font-medium text-xs">{formatCurrency(f.totale)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Acquisti Mensili - Line Chart */}
                  {prodottoAnalisiAcquisti.acquistiMensili?.length > 1 && (
                    <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3">
                      <h4 className="text-xs font-semibold text-white mb-3 flex items-center gap-2">
                        <TrendingUp className="w-3.5 h-3.5 text-amber-400" /> Andamento Acquisti
                      </h4>
                      <div className="h-[180px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={prodottoAnalisiAcquisti.acquistiMensili}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                            <XAxis dataKey="mese" stroke="#475569" fontSize={10} tickFormatter={v => v?.slice(-5)} />
                            <YAxis stroke="#475569" fontSize={10} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                            <Tooltip 
                              contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                              labelStyle={{ color: '#94a3b8' }}
                              formatter={(v) => [formatCurrency(v), 'Spesa']}
                            />
                            <Line type="monotone" dataKey="totale" stroke="#f59e0b" strokeWidth={2} dot={{ fill: '#f59e0b', r: 3 }} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                  
                  {/* Andamento Prezzi - Line Chart */}
                  {prodottoAnalisiAcquisti.variazionePrezzi?.length > 1 && (
                    <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3">
                      <h4 className="text-xs font-semibold text-white mb-3 flex items-center gap-2">
                        <Activity className="w-3.5 h-3.5 text-rose-400" /> Andamento Prezzi
                      </h4>
                      <div className="h-[180px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={prodottoAnalisiAcquisti.variazionePrezzi}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                            <XAxis dataKey="mese" stroke="#475569" fontSize={10} tickFormatter={v => v?.slice(-5)} />
                            <YAxis stroke="#475569" fontSize={10} domain={['auto', 'auto']} tickFormatter={v => `€${v.toFixed(1)}`} />
                            <Tooltip 
                              contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                              labelStyle={{ color: '#94a3b8' }}
                              formatter={(v) => [formatCurrency(v), 'Prezzo Medio']}
                            />
                            <Line type="monotone" dataKey="prezzo_medio" stroke="#f43f5e" strokeWidth={2} dot={{ fill: '#f43f5e', r: 3 }} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* AI Floating Button */}
      <div className="fixed bottom-6 right-6 z-50">
        <AnimatePresence>
          {showAiPopup && (
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.9 }}
              className="absolute bottom-16 right-0 w-80 bg-slate-900/95 backdrop-blur-xl border border-violet-500/30 rounded-xl shadow-2xl shadow-violet-500/20 overflow-hidden"
            >
              <div className="px-4 py-3 border-b border-violet-500/20 bg-violet-500/10 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-violet-400" />
                  <span className="text-sm font-semibold text-white">AI Suggerimento</span>
                </div>
                <button onClick={() => setShowAiPopup(false)} className="p-1 hover:bg-white/10 rounded-lg transition-colors">
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              </div>
              <div className="p-4">
                {aiSuggestion?.suggestion ? (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-1 text-xs font-bold uppercase bg-violet-500/20 text-violet-400 rounded">
                        {aiSuggestion.suggestion.titolo}
                      </span>
                    </div>
                    <p className="text-sm text-slate-300 leading-relaxed">{aiSuggestion.suggestion.messaggio}</p>
                    <div className="flex items-center justify-between pt-2 border-t border-white/10">
                      <span className="text-xs px-2 py-1 bg-violet-500/15 text-violet-300 rounded border border-violet-500/25">
                        {aiSuggestion.suggestion.azione}
                      </span>
                      <Button variant="ghost" size="sm" onClick={refreshAiSuggestion} disabled={loadingAi}
                        className="text-violet-400 hover:text-violet-300 hover:bg-violet-500/10">
                        <RefreshCw className={cn("w-3.5 h-3.5", loadingAi && "animate-spin")} />
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <Sparkles className="w-8 h-8 text-violet-500/40 mx-auto mb-2" />
                    <p className="text-sm text-slate-500">Importa dati per ricevere suggerimenti AI</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Floating AI Button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setShowAiPopup(!showAiPopup)}
          className={cn(
            "w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-all duration-300",
            showAiPopup 
              ? "bg-violet-600 shadow-violet-500/40" 
              : "bg-gradient-to-br from-violet-500 to-violet-700 shadow-violet-500/30 hover:shadow-violet-500/50"
          )}
          data-testid="ai-floating-btn"
        >
          <Sparkles className="w-6 h-6 text-white" />
        </motion.button>
      </div>
    </PageWrapper>
  );
}

// Quick Link - compact on desktop, larger on mobile
function QuickLink({ href, icon: Icon, label, color }) {
  const colors = {
    blue: 'from-blue-500/80 to-blue-600/80 hover:shadow-blue-500/20 border-blue-500/30',
    purple: 'from-purple-500/80 to-purple-600/80 hover:shadow-purple-500/20 border-purple-500/30',
    emerald: 'from-emerald-500/80 to-emerald-600/80 hover:shadow-emerald-500/20 border-emerald-500/30',
  };
  return (
    <Link to={href} className={cn(
      "flex items-center gap-3 flex-1 lg:flex-none",
      "px-4 py-3 md:py-2.5 rounded-xl bg-gradient-to-r border text-white transition-all duration-200 hover:shadow-lg hover:scale-[1.02]",
      colors[color]
    )} data-testid={`quick-link-${label.toLowerCase()}`}>
      <Icon className="w-4 h-4 shrink-0" />
      <span className="text-xs font-semibold">{label}</span>
    </Link>
  );
}

// Alert Column Component
function AlertColumn({ icon: Icon, title, items, color }) {
  const colorClass = { red: 'text-red-400', orange: 'text-orange-400', blue: 'text-blue-400' };
  return (
    <div className="p-2">
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon className={cn("w-3 h-3", colorClass[color])} />
        <span className="text-[10px] font-medium text-slate-400">{title}</span>
        <span className="text-[9px] text-slate-600 ml-auto">{items?.length || 0}</span>
      </div>
      <div className="space-y-0.5 max-h-24 overflow-auto">
        {items?.slice(0, 5).map((item, i) => (
          <div key={i} className="flex items-center justify-between text-[10px] py-1 px-1.5 rounded bg-white/[0.02]">
            <span className="text-slate-400 truncate flex-1 mr-1">{item.nome}</span>
            <span className={cn("font-mono", colorClass[color])}>
              {item.quantita !== undefined ? `${item.quantita}/${item.quantita_minima}` : item.giorni_inattivo ? `${item.giorni_inattivo}g` : `${item.giorni_rimanenti}g`}
            </span>
          </div>
        ))}
        {(!items || items.length === 0) && <p className="text-[9px] text-slate-600 text-center py-1">-</p>}
      </div>
    </div>
  );
}
