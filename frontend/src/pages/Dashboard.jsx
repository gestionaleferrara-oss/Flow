import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Euro, ShoppingCart, Users, Package, AlertTriangle, ArrowUpRight, Upload,
  BarChart3, TrendingUp, TrendingDown, Search, Box, Sparkles, Lightbulb,
  RefreshCw, Clock, UserX, PackageX, AlertCircle, Minus, X, Filter,
  ArrowDownAZ, Activity, Plus, ChevronRight
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
    } catch (e) {
      setProdottoAnalisi(null);
      setProdottoAnalisiAcquisti(null);
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
          trendValue={data?.crescitaPercentuale} />
        <StatCard label="Ordini Mese" value={data?.ordiniMese || 0} icon={ShoppingCart} gradient="emerald" />
        <StatCard label="Clienti Mese" value={data?.nuoviClienti || 0} icon={Users} gradient="cyan" />
        <StatCard label="Alert" value={totalAlerts} icon={AlertTriangle} gradient="amber" />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-4">
        {/* AI Suggestion - Compact inline style */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
          className="lg:col-span-8 rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] overflow-hidden">
          <div className="px-3 py-2 flex items-center gap-3">
            <div className="p-1.5 rounded-md bg-violet-500/15 shrink-0">
              <Sparkles className="w-3.5 h-3.5 text-violet-400" />
            </div>
            <div className="flex-1 min-w-0">
              {aiSuggestion?.suggestion ? (
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] font-semibold text-violet-400 uppercase tracking-wide">{aiSuggestion.suggestion.titolo}</span>
                  <span className="text-xs text-slate-300 truncate">{aiSuggestion.suggestion.messaggio}</span>
                  <span className="text-[9px] px-1.5 py-0.5 bg-violet-500/10 text-violet-300 rounded border border-violet-500/20 shrink-0">{aiSuggestion.suggestion.azione}</span>
                </div>
              ) : (
                <span className="text-xs text-slate-500">Importa dati per suggerimenti AI</span>
              )}
            </div>
            <Button variant="ghost" size="sm" onClick={refreshAiSuggestion} disabled={loadingAi}
              className="text-violet-400 hover:text-violet-300 hover:bg-violet-500/10 h-7 px-2 shrink-0">
              <RefreshCw className={cn("w-3 h-3", loadingAi && "animate-spin")} />
            </Button>
          </div>
        </motion.div>

        {/* Sales Insight - improved text visibility */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="lg:col-span-4 rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] overflow-hidden"
          data-testid="sales-insight-widget">
          <div className="px-3 py-2.5 border-b border-white/[0.06] flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-amber-500/15">
              <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-xs font-semibold text-white">Sales Insight</h3>
              <p className="text-[9px] text-slate-500 truncate">{salesInsight?.mese_riferimento || ''}</p>
            </div>
          </div>
          <div className="p-2">
            {insightLoading ? (
              <div className="flex items-center justify-center h-24"><RefreshCw className="w-4 h-4 text-slate-600 animate-spin" /></div>
            ) : salesInsight?.insights?.length > 0 ? (
              <div className="space-y-1.5">
                {salesInsight.insights.slice(0, 4).map((ins) => (
                  <div key={ins.tipo} className={cn("px-2.5 py-2 rounded-lg border", insightColors[ins.colore] || insightColors.emerald)}>
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm">{ins.icona}</span>
                      <span className="font-semibold text-xs truncate flex-1">{ins.valore}</span>
                    </div>
                    <p className="text-[11px] text-slate-300 leading-relaxed pl-6">{ins.dettaglio || ins.titolo}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center py-4 text-[10px] text-slate-500">Nessun insight</p>
            )}
          </div>
        </motion.div>
      </div>

      {/* Second Row: Trends + Quick Links */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-4">
        {/* Trends Widget - no hover on widget, only plus button */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="lg:col-span-8 rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] overflow-hidden relative"
          data-testid="trends-widget">
          <div className="px-3 py-2.5 border-b border-white/[0.06] flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-emerald-500/15">
                <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-xs font-semibold text-white">Trend Prodotti</h3>
                <p className="text-[9px] text-slate-500">Top 5</p>
              </div>
            </div>
            {/* Visible selectors */}
            <div className="flex items-center gap-2" data-testid="trends-selectors">
              <div className="flex items-center gap-1 bg-white/[0.04] rounded-lg p-0.5">
                <Clock className="w-3 h-3 text-slate-500 ml-1" />
                {periodoOptions.map(p => (
                  <button key={p.v} onClick={(e) => { e.stopPropagation(); setTrendsPeriodo(p.v); loadTrendsVendite(p.v, trendsOrdinaPer, 5); }}
                    data-testid={`trend-periodo-${p.v}`}
                    className={cn("px-2 py-1 rounded-md text-[10px] font-medium transition-all",
                      trendsPeriodo === p.v ? "bg-emerald-500/20 text-emerald-300 shadow-sm" : "text-slate-500 hover:text-slate-300"
                    )}>{p.l}</button>
                ))}
              </div>
              <div className="flex items-center gap-1 bg-white/[0.04] rounded-lg p-0.5">
                <ArrowDownAZ className="w-3 h-3 text-slate-500 ml-1" />
                {ordinaPerOptions.map(o => (
                  <button key={o.v} onClick={(e) => { e.stopPropagation(); setTrendsOrdinaPer(o.v); loadTrendsVendite(trendsPeriodo, o.v, 5); }}
                    data-testid={`trend-ordina-${o.v}`}
                    className={cn("px-2 py-1 rounded-md text-[10px] font-medium transition-all",
                      trendsOrdinaPer === o.v ? "bg-emerald-500/20 text-emerald-300 shadow-sm" : "text-slate-500 hover:text-slate-300"
                    )}>{o.l}</button>
                ))}
              </div>
              {/* Plus button to expand */}
              <button 
                onClick={() => { setShowTrendsPopup(true); loadTrendsVendite(trendsPeriodo, trendsOrdinaPer, 20); }}
                data-testid="trends-expand-btn"
                className="p-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 transition-all hover:scale-105"
                title="Mostra top 20"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
          <div className="p-2">
            {trendsVendite?.top_prodotti ? (
              <div className="space-y-1">
                {trendsVendite.top_prodotti.slice(0, 5).map((t, idx) => (
                  <div key={t.prodotto} className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-white/[0.02] border border-white/[0.04]">
                    <span className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 text-[9px] font-bold flex items-center justify-center">{idx + 1}</span>
                    <span className="flex-1 text-[11px] text-slate-300 truncate">{t.prodotto}</span>
                    <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded",
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

        {/* Quick Links - Compact on desktop, larger on mobile */}
        <div className="lg:col-span-4 flex lg:flex-col gap-2" data-testid="quick-links">
          <QuickLink href="/upload" icon={Upload} label="Importa" color="blue" />
          <QuickLink href="/statistiche" icon={BarChart3} label="Statistiche" color="purple" />
          <QuickLink href="/magazzino" icon={Package} label="Magazzino" color="emerald" />
        </div>
      </div>

      {/* Alerts Section */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
        className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] overflow-hidden">
        <div className="px-3 py-2 border-b border-white/[0.06] flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-400" />
          <span className="text-xs font-semibold text-white">Alert</span>
          {totalAlerts > 0 && <span className="px-1.5 py-0.5 text-[9px] bg-amber-500/20 text-amber-300 rounded">{totalAlerts}</span>}
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

      {/* Product Analysis Modal - Complete Details */}
      <Dialog open={showProdottoModal} onOpenChange={setShowProdottoModal}>
        <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-auto">
          <DialogHeader><DialogTitle>{selectedProdotto?.nome}</DialogTitle></DialogHeader>
          {loadingAnalisi ? (
            <div className="py-8 text-center"><LoadingSpinner /></div>
          ) : (
            <div className="space-y-4">
              <div className="flex gap-2">
                <Button variant={analisiView === 'vendite' ? 'default' : 'outline'} size="sm" onClick={() => setAnalisiView('vendite')} data-testid="analisi-vendite-tab">Vendite</Button>
                <Button variant={analisiView === 'acquisti' ? 'default' : 'outline'} size="sm" onClick={() => setAnalisiView('acquisti')} data-testid="analisi-acquisti-tab">Acquisti</Button>
              </div>
              
              {analisiView === 'vendite' && prodottoAnalisi && (
                <div className="space-y-4">
                  {/* Main Stats Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                      <p className="text-[10px] text-slate-500 mb-0.5">Totale Venduto</p>
                      <p className="text-lg font-bold text-white">{formatCurrency(prodottoAnalisi.totale_venduto || 0)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                      <p className="text-[10px] text-slate-500 mb-0.5">Quantità Venduta</p>
                      <p className="text-lg font-bold text-white">{prodottoAnalisi.quantita_venduta || 0}</p>
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
                  
                  {/* Secondary Stats */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/10">
                      <p className="text-[10px] text-blue-400 mb-0.5">Media Mensile (Fatturato)</p>
                      <p className="text-base font-semibold text-white">{formatCurrency(prodottoAnalisi.fatturatoMensile || 0)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                      <p className="text-[10px] text-emerald-400 mb-0.5">Media Mensile (Quantità)</p>
                      <p className="text-base font-semibold text-white">{prodottoAnalisi.mediaMensile || 0}</p>
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
                  
                  {/* Vendite Mensili */}
                  {prodottoAnalisi.venditeMensili?.length > 0 && (
                    <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3">
                      <h4 className="text-xs font-semibold text-white mb-2 flex items-center gap-2">
                        <BarChart3 className="w-3.5 h-3.5 text-violet-400" /> Storico Mensile
                      </h4>
                      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                        {prodottoAnalisi.venditeMensili.slice(-8).map((m) => (
                          <div key={m.mese} className="p-2 rounded bg-violet-500/5 border border-violet-500/10 text-center">
                            <p className="text-[9px] text-slate-500">{m.mese}</p>
                            <p className="text-xs font-semibold text-violet-300">{formatCurrency(m.totale)}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {analisiView === 'acquisti' && prodottoAnalisiAcquisti && (
                <div className="space-y-4">
                  {/* Main Stats Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                      <p className="text-[10px] text-slate-500 mb-0.5">Totale Acquistato</p>
                      <p className="text-lg font-bold text-white">{formatCurrency(prodottoAnalisiAcquisti.totale_acquistato || 0)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                      <p className="text-[10px] text-slate-500 mb-0.5">Quantità Acquistata</p>
                      <p className="text-lg font-bold text-white">{prodottoAnalisiAcquisti.quantita_acquistata || 0}</p>
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
                  
                  {/* Secondary Stats */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg bg-orange-500/5 border border-orange-500/10">
                      <p className="text-[10px] text-orange-400 mb-0.5">Media Mensile (Spesa)</p>
                      <p className="text-base font-semibold text-white">{formatCurrency(prodottoAnalisiAcquisti.spesoMensile || 0)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/10">
                      <p className="text-[10px] text-amber-400 mb-0.5">Media Mensile (Quantità)</p>
                      <p className="text-base font-semibold text-white">{prodottoAnalisiAcquisti.mediaMensile || 0}</p>
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
                  
                  {/* Acquisti Mensili */}
                  {prodottoAnalisiAcquisti.acquistiMensili?.length > 0 && (
                    <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3">
                      <h4 className="text-xs font-semibold text-white mb-2 flex items-center gap-2">
                        <BarChart3 className="w-3.5 h-3.5 text-amber-400" /> Storico Mensile
                      </h4>
                      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                        {prodottoAnalisiAcquisti.acquistiMensili.slice(-8).map((m) => (
                          <div key={m.mese} className="p-2 rounded bg-amber-500/5 border border-amber-500/10 text-center">
                            <p className="text-[9px] text-slate-500">{m.mese}</p>
                            <p className="text-xs font-semibold text-amber-300">{formatCurrency(m.totale)}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Variazione Prezzi */}
                  {prodottoAnalisiAcquisti.variazionePrezzi?.length > 0 && (
                    <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3">
                      <h4 className="text-xs font-semibold text-white mb-2 flex items-center gap-2">
                        <Activity className="w-3.5 h-3.5 text-rose-400" /> Andamento Prezzi
                      </h4>
                      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                        {prodottoAnalisiAcquisti.variazionePrezzi.slice(-8).map((p) => (
                          <div key={p.mese} className="p-2 rounded bg-rose-500/5 border border-rose-500/10 text-center">
                            <p className="text-[9px] text-slate-500">{p.mese}</p>
                            <p className="text-xs font-semibold text-rose-300">{formatCurrency(p.prezzo_medio)}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
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
