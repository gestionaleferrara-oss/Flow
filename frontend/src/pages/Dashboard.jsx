import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar
} from 'recharts';
import {
  Euro, ShoppingCart, Users, Package, AlertTriangle, ArrowUpRight, Upload,
  BarChart3, TrendingUp, TrendingDown, Search, Box, Sparkles, Lightbulb,
  RefreshCw, Clock, UserX, PackageX, AlertCircle, Minus, X, Filter,
  ArrowDownAZ, Activity, Plus, ChevronRight, Calendar, Eye
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
  const [prodottoStoricoClienti, setProdottoStoricoClienti] = useState(null);
  const [loadingAnalisi, setLoadingAnalisi] = useState(false);
  const [analisiView, setAnalisiView] = useState('vendite');
  const [analisiPeriodo, setAnalisiPeriodo] = useState('1m'); // 1m, 3m, 6m, all
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [alerts, setAlerts] = useState(null);
  const [loadingAlerts, setLoadingAlerts] = useState(false);
  
  // Cliente prodotti search state
  const [showClienteProdottiModal, setShowClienteProdottiModal] = useState(false);
  const [clienteProdotti, setClienteProdotti] = useState(null);
  const [clienteProdottiSearch, setClienteProdottiSearch] = useState('');
  const [loadingClienteProdotti, setLoadingClienteProdotti] = useState(false);
  const [selectedClienteForProdotti, setSelectedClienteForProdotti] = useState(null);

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

  // Card Detail Modal
  const [cardDetail, setCardDetail] = useState(null);
  const [cardDetailType, setCardDetailType] = useState(null);
  const [loadingCardDetail, setLoadingCardDetail] = useState(false);
  
  // Cliente Analisi state
  const [showClienteModal, setShowClienteModal] = useState(false);
  const [selectedCliente, setSelectedCliente] = useState(null);
  const [clienteAnalisi, setClienteAnalisi] = useState(null);
  const [loadingClienteAnalisi, setLoadingClienteAnalisi] = useState(false);
  const [clienteAnalisiPeriodo, setClienteAnalisiPeriodo] = useState('mese');

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

  // Load card detail for popup
  const [cardDetailPeriodo, setCardDetailPeriodo] = useState('mese');
  const [alertPeriodo, setAlertPeriodo] = useState('30gg');
  const [fatturatoPeriodo, setFatturatoPeriodo] = useState('mese');
  const [ordiniPeriodo, setOrdiniPeriodo] = useState('mese');
  const openCardDetail = async (type, periodo) => {
    const pMap = { fatturato: fatturatoPeriodo, ordini: ordiniPeriodo, clienti: cardDetailPeriodo, alert: alertPeriodo };
    const p = periodo || pMap[type];
    setCardDetailType(type);
    setLoadingCardDetail(true);
    try {
      const params = p ? `?periodo=${p}` : '';
      const res = await axios.get(`${API}/dashboard/card-detail/${type}${params}`);
      setCardDetail(res.data);
    } catch (e) { setCardDetail(null); }
    finally { setLoadingCardDetail(false); }
  };

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
    }, 150);
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
    setProdottoStoricoClienti(null);
    try {
      const [venditeRes, acquistiRes, storicoRes] = await Promise.all([
        axios.get(`${API}/prodotti/${encodeURIComponent(prodotto.nome)}/analisi`, { params: { periodo } }),
        axios.get(`${API}/prodotti/${encodeURIComponent(prodotto.nome)}/analisi-acquisti`, { params: { periodo } }),
        axios.get(`${API}/prodotti/${encodeURIComponent(prodotto.nome)}/storico-clienti`)
      ]);
      setProdottoAnalisi(venditeRes.data);
      setProdottoAnalisiAcquisti(acquistiRes.data);
      setProdottoStoricoClienti(storicoRes.data);
    } catch (e) {
      setProdottoAnalisi(null);
      setProdottoAnalisiAcquisti(null);
      setProdottoStoricoClienti(null);
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

  // Cliente Analisi functions
  const viewClienteAnalisi = async (clienteName, periodo = 'mese') => {
    setSelectedCliente({ nome: clienteName });
    setShowClienteModal(true);
    setLoadingClienteAnalisi(true);
    setClienteAnalisiPeriodo(periodo);
    try {
      // First get cliente by name to get ID
      const clientiRes = await axios.get(`${API}/clienti`, { params: { search: clienteName, limit: 1 } });
      const clientiList = clientiRes.data?.clienti || clientiRes.data || [];
      if (clientiList.length > 0) {
        const cliente = clientiList[0];
        setSelectedCliente(cliente);
        const analisiRes = await axios.get(`${API}/clienti/${cliente.id}/analisi`, { params: { periodo } });
        setClienteAnalisi(analisiRes.data);
      }
    } catch (e) {
      setClienteAnalisi(null);
    } finally { setLoadingClienteAnalisi(false); }
  };

  const changeClienteAnalisiPeriodo = async (newPeriodo) => {
    if (!selectedCliente?.id || newPeriodo === clienteAnalisiPeriodo) return;
    setClienteAnalisiPeriodo(newPeriodo);
    setLoadingClienteAnalisi(true);
    try {
      const analisiRes = await axios.get(`${API}/clienti/${selectedCliente.id}/analisi`, { params: { periodo: newPeriodo } });
      setClienteAnalisi(analisiRes.data);
    } catch (e) {
      // Keep existing data
    } finally { setLoadingClienteAnalisi(false); }
  };

  // Search products purchased by a specific customer
  const viewClienteProdotti = async (clienteId, clienteNome, searchTerm = '') => {
    setSelectedClienteForProdotti({ id: clienteId, nome: clienteNome });
    setShowClienteProdottiModal(true);
    setLoadingClienteProdotti(true);
    setClienteProdottiSearch(searchTerm);
    try {
      // Use ID-based endpoint if we have ID, otherwise use name-based endpoint
      const endpoint = clienteId 
        ? `${API}/clienti/${clienteId}/prodotti-acquistati`
        : `${API}/clienti-by-name/${encodeURIComponent(clienteNome)}/prodotti-acquistati`;
      const res = await axios.get(endpoint, { params: { search: searchTerm } });
      setClienteProdotti(res.data);
    } catch (e) {
      setClienteProdotti(null);
    } finally { setLoadingClienteProdotti(false); }
  };

  const searchClienteProdotti = async (searchTerm) => {
    if (!selectedClienteForProdotti?.id && !selectedClienteForProdotti?.nome) return;
    setClienteProdottiSearch(searchTerm);
    setLoadingClienteProdotti(true);
    try {
      const endpoint = selectedClienteForProdotti.id 
        ? `${API}/clienti/${selectedClienteForProdotti.id}/prodotti-acquistati`
        : `${API}/clienti-by-name/${encodeURIComponent(selectedClienteForProdotti.nome)}/prodotti-acquistati`;
      const res = await axios.get(endpoint, { params: { search: searchTerm } });
      setClienteProdotti(res.data);
    } catch (e) {
      // Keep existing
    } finally { setLoadingClienteProdotti(false); }
  };

  const filteredProdotti = searchResults;

  if (loading) return <div className="flex items-center justify-center h-64"><LoadingSpinner /></div>;

  const totalAlerts = (alerts?.prodottiSottoScorta?.length || 0) +
                      (alerts?.clientiInattivi?.length > 0 ? 1 : 0) +
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
        <StatCard label="Fatturato" value={data?.fatturatoMese || 0} format="currency" icon={Euro} gradient="blue" blurred
          onIconClick={() => openCardDetail('fatturato')}
          trend={data?.crescitaPercentuale > 0 ? 'up' : data?.crescitaPercentuale < 0 ? 'down' : 'neutral'}
          trendValue={data?.crescitaPercentuale}
          subtitle={[
            margineData?.margine_medio_pct > 0 ? `Margine: +${margineData.margine_medio_pct.toFixed(1)}% · Profitto: ${formatCurrency(margineData.profitto_totale || 0)}` : null,
            data?.fatturatoMesePrec ? `Mese prec: ${formatCurrency(data.fatturatoMesePrec)}` : null
          ].filter(Boolean).join('\n') || null} />
        <StatCard label="Ordini Mese" value={data?.ordiniMese || 0} icon={ShoppingCart} gradient="emerald" blurred
          onIconClick={() => openCardDetail('ordini')}
          trend={data?.ordiniCrescita > 0 ? 'up' : data?.ordiniCrescita < 0 ? 'down' : 'neutral'}
          trendValue={data?.ordiniCrescita}
          subtitle={data?.ordiniMesePrec ? `Mese prec: ${data.ordiniMesePrec.toLocaleString('it-IT')}` : null} />
        <StatCard label="Clienti Mese" value={data?.nuoviClienti || 0} icon={Users} gradient="cyan" blurred
          onIconClick={() => openCardDetail('clienti')}
          trend={data?.clientiCrescita > 0 ? 'up' : data?.clientiCrescita < 0 ? 'down' : 'neutral'}
          trendValue={data?.clientiCrescita}
          subtitle={data?.clientiMesePrec ? `Mese prec: ${data.clientiMesePrec.toLocaleString('it-IT')}` : null} />
        <StatCard label="Alert" value={totalAlerts} icon={AlertTriangle} gradient="amber" blurred
          onIconClick={() => openCardDetail('alert')}
          subtitle={[
            alerts?.prodottiSottoScorta?.length ? `Sotto scorta: ${alerts.prodottiSottoScorta.length}` : null,
            alerts?.clientiInattivi?.length ? `Clienti inattivi: ${alerts.clientiInattivi.length}` : null,
            alerts?.prodottiInEsaurimento?.length ? `In esaurimento: ${alerts.prodottiInEsaurimento.length}` : null
          ].filter(Boolean).join('\n') || null} />
      </div>

      {/* Main Content Grid - Trends left, Insight right, Quick Links far right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-4">
        {/* Trends Widget - Left */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
          className="lg:col-span-5 rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] overflow-hidden relative"
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
                    className={cn("px-2 py-1 rounded-md text-[10px] font-medium transition-all",
                      trendsPeriodo === p.v ? "bg-emerald-500/20 text-emerald-300 shadow-sm" : "text-slate-500 hover:text-slate-300"
                    )}>{p.l}</button>
                ))}
              </div>
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
          <div className="p-3">
            {trendsVendite?.top_prodotti ? (
              <div className="space-y-1.5">
                {trendsVendite.top_prodotti.slice(0, 5).map((t, idx) => (
                  <div key={t.prodotto} 
                    onClick={() => viewProdottoAnalisi({ nome: t.prodotto })}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04] cursor-pointer hover:bg-white/[0.05] transition-colors">
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

          {/* Popup Modal - Full Trends */}
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
                  </div>
                  <button onClick={() => setShowTrendsPopup(false)} className="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="p-2 max-h-[280px] overflow-y-auto">
                  {trendsVendite?.top_prodotti?.map((t, idx) => (
                    <div key={t.prodotto}
                      onClick={() => { setShowTrendsPopup(false); viewProdottoAnalisi({ nome: t.prodotto }); }}
                      className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-white/[0.04] cursor-pointer transition-colors">
                      <span className="w-5 h-5 rounded-full bg-emerald-500/15 text-emerald-400 text-[10px] font-bold flex items-center justify-center">{idx + 1}</span>
                      <span className="flex-1 text-xs text-slate-300 truncate">{t.prodotto}</span>
                      <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded",
                        t.trend === 'up' ? 'text-emerald-400 bg-emerald-500/10' : t.trend === 'down' ? 'text-red-400 bg-red-500/10' : 'text-slate-400 bg-slate-500/10'
                      )}>{t.variazione_qty_pct > 0 ? '+' : ''}{t.variazione_qty_pct}%</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Sales Insight - Center/Right - Clickable items */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="lg:col-span-5 rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] overflow-hidden"
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
                {salesInsight.insights.slice(0, 4).map((ins) => {
                  const isProduct = ['top_product', 'growth_product', 'velocity', 'best_margin', 'restock_alert'].includes(ins.tipo);
                  const isClient = ['top_client', 'new_client'].includes(ins.tipo);
                  return (
                    <div key={ins.tipo} 
                      onClick={() => {
                        if (isProduct) viewProdottoAnalisi({ nome: ins.valore.replace('...', '') });
                        else if (isClient) viewClienteAnalisi(ins.valore.replace('...', ''));
                      }}
                      data-testid={`insight-item-${ins.tipo}`}
                      className={cn("px-3 py-2.5 rounded-lg border cursor-pointer hover:scale-[1.01] hover:brightness-110 transition-all", insightColors[ins.colore] || insightColors.emerald)}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-base">{ins.icona}</span>
                        <span className="font-semibold text-sm truncate flex-1">{ins.valore}</span>
                        <Eye className="w-3.5 h-3.5 text-white/40" />
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed pl-7">{ins.dettaglio || ins.titolo}</p>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-6">
                <div className="w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center mx-auto mb-3">
                  <Lightbulb className="w-6 h-6 text-amber-500/50" />
                </div>
                <p className="text-sm text-slate-400 mb-1">Analisi in corso...</p>
                <p className="text-xs text-slate-600">Gli insight appariranno quando ci sono dati sufficienti</p>
              </div>
            )}
          </div>
        </motion.div>

        {/* Quick Links - Far Right */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="lg:col-span-2 flex flex-row lg:flex-col gap-2" data-testid="quick-links">
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
                    {p.prezzo_vendita_medio > 0 && <span className="text-emerald-400">Pv. medio: {p.prezzo_vendita_medio.toFixed(2)} €</span>}
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
              <Button variant={analisiView === 'clienti' ? 'default' : 'outline'} size="sm" onClick={() => setAnalisiView('clienti')} data-testid="analisi-clienti-tab" className="gap-1">
                <Users className="w-3 h-3" /> Clienti & Prezzi
              </Button>
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

              {/* NEW: Clienti & Prezzi Tab */}
              {analisiView === 'clienti' && prodottoStoricoClienti && (
                <div className="space-y-4">
                  {/* Margin Summary */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                      <p className="text-[10px] text-emerald-400/70 mb-0.5">Prezzo Vendita Medio</p>
                      <p className="text-lg font-bold text-emerald-400">{formatCurrency(prodottoStoricoClienti.prezzoMedioVendita || 0)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <p className="text-[10px] text-amber-400/70 mb-0.5">Costo Acquisto Medio</p>
                      <p className="text-lg font-bold text-amber-400">{formatCurrency(prodottoStoricoClienti.costoMedioAcquisto || 0)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-violet-500/10 border border-violet-500/20">
                      <p className="text-[10px] text-violet-400/70 mb-0.5">Margine Globale</p>
                      <p className={cn("text-lg font-bold", prodottoStoricoClienti.margineGlobale >= 0 ? "text-violet-400" : "text-red-400")}>
                        {prodottoStoricoClienti.margineGlobale >= 0 ? '+' : ''}{prodottoStoricoClienti.margineGlobale || 0}%
                      </p>
                    </div>
                    <div className="p-3 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                      <p className="text-[10px] text-cyan-400/70 mb-0.5">Clienti Totali</p>
                      <p className="text-lg font-bold text-cyan-400">{prodottoStoricoClienti.clienti?.length || 0}</p>
                    </div>
                  </div>

                  {/* Price History Chart */}
                  {prodottoStoricoClienti.storicoPrezzi?.length > 1 && (
                    <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3">
                      <h4 className="text-xs font-semibold text-white mb-3 flex items-center gap-2">
                        <TrendingUp className="w-3.5 h-3.5 text-emerald-400" /> Storico Prezzi Vendita
                      </h4>
                      <div className="h-[150px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={prodottoStoricoClienti.storicoPrezzi}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                            <XAxis dataKey="mese" stroke="#475569" fontSize={10} tickFormatter={v => v?.slice(-5)} />
                            <YAxis stroke="#475569" fontSize={10} domain={['auto', 'auto']} tickFormatter={v => `€${v.toFixed(2)}`} />
                            <Tooltip 
                              contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                              labelStyle={{ color: '#94a3b8' }}
                              formatter={(v, name) => [formatCurrency(v), name === 'prezzo_medio' ? 'Media' : name === 'prezzo_min' ? 'Min' : 'Max']}
                            />
                            <Line type="monotone" dataKey="prezzo_medio" stroke="#10b981" strokeWidth={2} dot={{ fill: '#10b981', r: 3 }} name="Media" />
                            <Line type="monotone" dataKey="prezzo_min" stroke="#6b7280" strokeWidth={1} strokeDasharray="3 3" dot={false} name="Min" />
                            <Line type="monotone" dataKey="prezzo_max" stroke="#6b7280" strokeWidth={1} strokeDasharray="3 3" dot={false} name="Max" />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}

                  {/* Customers with Last 3 Sales */}
                  {prodottoStoricoClienti.clienti?.length > 0 && (
                    <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3">
                      <h4 className="text-xs font-semibold text-white mb-3 flex items-center gap-2">
                        <Users className="w-3.5 h-3.5 text-cyan-400" /> Ultime Vendite per Cliente
                        <span className="ml-auto text-[10px] text-slate-500">Ultime 3 per cliente</span>
                      </h4>
                      <div className="space-y-3 max-h-[300px] overflow-auto pr-1">
                        {prodottoStoricoClienti.clienti.slice(0, 10).map((cliente, idx) => (
                          <div key={cliente.nome} className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className="w-5 h-5 rounded-full bg-cyan-500/15 text-cyan-400 text-[10px] font-bold flex items-center justify-center">{idx + 1}</span>
                                <span className="text-sm font-medium text-white truncate max-w-[200px]">{cliente.nome}</span>
                                <button
                                  onClick={() => viewClienteProdotti(null, cliente.nome)}
                                  className="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-cyan-400 transition-colors"
                                  title="Cerca prodotti di questo cliente"
                                >
                                  <Search className="w-3 h-3" />
                                </button>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className={cn(
                                  "text-xs font-medium px-1.5 py-0.5 rounded",
                                  cliente.margine_percentuale >= 20 ? "bg-emerald-500/20 text-emerald-400" :
                                  cliente.margine_percentuale >= 0 ? "bg-amber-500/20 text-amber-400" :
                                  "bg-red-500/20 text-red-400"
                                )}>
                                  {cliente.margine_percentuale >= 0 ? '+' : ''}{cliente.margine_percentuale}%
                                </span>
                                <span className="text-xs text-cyan-400 font-medium">{formatCurrency(cliente.totale_venduto)}</span>
                              </div>
                            </div>
                            {/* Last 3 sales */}
                            <div className="space-y-1 pl-7">
                              {cliente.ultime_vendite.map((v, i) => (
                                <div key={i} className="flex items-center justify-between text-[11px]">
                                  <span className="text-slate-500">{formatDate(v.data)}</span>
                                  <span className="text-slate-400">x{v.quantita}</span>
                                  <span className="text-emerald-400 font-medium">{formatCurrency(v.prezzo_unitario)}/u</span>
                                  <span className="text-white">{formatCurrency(v.totale)}</span>
                                </div>
                              ))}
                            </div>
                            <div className="flex items-center justify-between mt-1 pt-1 border-t border-white/[0.04] pl-7">
                              <span className="text-[10px] text-slate-500">{cliente.num_acquisti} acquisti totali</span>
                              <span className="text-[10px] text-slate-400">Media: {formatCurrency(cliente.prezzo_medio)}/u</span>
                            </div>
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

      {/* Client Analysis Modal */}
      <Dialog open={showClienteModal} onOpenChange={setShowClienteModal}>
        <DialogContent className="sm:max-w-3xl max-h-[85vh] overflow-auto" data-testid="cliente-analisi-modal">
          <DialogHeader>
            <DialogTitle>Analisi Cliente: {selectedCliente?.nome}</DialogTitle>
          </DialogHeader>
          
          {/* Period Selector */}
          <div className="flex items-center gap-2 flex-wrap pb-2 border-b border-white/[0.06]">
            <Calendar className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-xs text-slate-500">Periodo:</span>
            {[
              { v: 'mese', l: 'Mese' },
              { v: '3mesi', l: '3 Mesi' },
              { v: '6mesi', l: '6 Mesi' },
              { v: 'anno', l: 'Anno' },
              { v: 'tutto', l: 'Tutto' }
            ].map(p => (
              <button key={p.v} onClick={() => changeClienteAnalisiPeriodo(p.v)}
                disabled={loadingClienteAnalisi}
                data-testid={`cliente-periodo-${p.v}`}
                className={cn("px-2 py-1 rounded-md text-[10px] font-medium transition-all",
                  clienteAnalisiPeriodo === p.v ? "bg-cyan-500/20 text-cyan-300 shadow-sm" : "text-slate-500 hover:text-slate-300"
                )}>{p.l}</button>
            ))}
          </div>

          {loadingClienteAnalisi ? (
            <div className="py-8 text-center"><LoadingSpinner /></div>
          ) : clienteAnalisi ? (
            <div className="space-y-4">
              {/* Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                  <p className="text-[10px] text-slate-500 mb-0.5">Totale Speso</p>
                  <p className="text-lg font-bold text-cyan-400">{formatCurrency(clienteAnalisi.totaleSpeso || 0)}</p>
                </div>
                <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                  <p className="text-[10px] text-slate-500 mb-0.5">Num. Visite</p>
                  <p className="text-lg font-bold text-white">{clienteAnalisi.numOrdini || 0}</p>
                </div>
                <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                  <p className="text-[10px] text-slate-500 mb-0.5">Ultima Visita</p>
                  <p className="text-lg font-bold text-white">{clienteAnalisi.ultimoOrdine || 'N/A'}</p>
                </div>
                <div className="p-3 rounded-lg bg-white/5 border border-white/[0.06]">
                  <p className="text-[10px] text-slate-500 mb-0.5">Media/Visita</p>
                  <p className="text-lg font-bold text-white">{formatCurrency(clienteAnalisi.mediaOrdine || 0)}</p>
                </div>
              </div>

              {/* Visit History */}
              {clienteAnalisi.listaVisite?.length > 0 && (
                <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] overflow-hidden">
                  <div className="px-3 py-2 bg-white/[0.03] border-b border-white/[0.06] flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-xs font-semibold text-white">Storico Visite</span>
                  </div>
                  <div className="max-h-40 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-white/[0.02] sticky top-0">
                        <tr>
                          <th className="px-3 py-2 text-left text-[10px] font-medium text-slate-500">Data</th>
                          <th className="px-3 py-2 text-right text-[10px] font-medium text-slate-500">Totale</th>
                        </tr>
                      </thead>
                      <tbody>
                        {clienteAnalisi.listaVisite.map((v, i) => (
                          <tr key={i} className="border-t border-white/[0.04] hover:bg-white/[0.02]">
                            <td className="px-3 py-2 text-xs text-slate-300">{v.data}</td>
                            <td className="px-3 py-2 text-right text-xs font-medium text-cyan-400">{formatCurrency(v.totale)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Top Products */}
              {clienteAnalisi.topProdotti?.length > 0 && (
                <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3">
                  <h4 className="text-xs font-semibold text-white mb-2 flex items-center gap-2">
                    <Package className="w-3.5 h-3.5 text-cyan-400" /> Prodotti Piu Acquistati
                  </h4>
                  <div className="space-y-1.5">
                    {clienteAnalisi.topProdotti.slice(0, 5).map((p, i) => (
                      <div key={p.nome} className="flex items-center gap-2 text-sm">
                        <span className="w-5 h-5 rounded-full bg-cyan-500/15 text-cyan-400 text-[10px] font-bold flex items-center justify-center">{i + 1}</span>
                        <span className="flex-1 text-slate-300 truncate text-xs">{p.nome}</span>
                        <span className="text-cyan-400 font-medium text-xs">{formatCurrency(p.totale)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="py-8 text-center text-slate-500 text-sm">Nessun dato disponibile</div>
          )}
        </DialogContent>
      </Dialog>

      {/* NEW: Cliente Prodotti Search Modal */}
      <Dialog open={showClienteProdottiModal} onOpenChange={setShowClienteProdottiModal}>
        <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-auto" data-testid="cliente-prodotti-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Users className="w-5 h-5 text-cyan-400" />
              Prodotti di: {selectedClienteForProdotti?.nome || clienteProdotti?.cliente_nome}
            </DialogTitle>
          </DialogHeader>
          
          {/* Search Box */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Cerca prodotto... (es: noci, chandler, howard)"
              value={clienteProdottiSearch}
              onChange={(e) => searchClienteProdotti(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
              data-testid="cliente-prodotti-search"
            />
          </div>

          {loadingClienteProdotti ? (
            <div className="py-8 flex justify-center"><LoadingSpinner /></div>
          ) : clienteProdotti?.prodotti?.length > 0 ? (
            <div className="space-y-2 mt-4">
              <p className="text-xs text-slate-500 mb-2">{clienteProdotti.totale_prodotti} prodotti trovati</p>
              {clienteProdotti.prodotti.map((prod, idx) => (
                <div key={prod.prodotto_nome} className="p-3 rounded-lg bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-medium text-white">{prod.prodotto_nome}</h4>
                    <span className="text-xs text-emerald-400 font-medium">{formatCurrency(prod.totale_acquistato)}</span>
                  </div>
                  
                  {/* Last 3 purchases */}
                  <div className="space-y-1 mb-2">
                    {prod.ultime_3.map((v, i) => (
                      <div key={i} className="flex items-center justify-between text-[11px] bg-white/[0.02] px-2 py-1 rounded">
                        <span className="text-slate-500">{formatDate(v.data)}</span>
                        <span className="text-slate-400">Qty: {v.quantita}</span>
                        <span className="text-cyan-400 font-medium">{formatCurrency(v.prezzo_unitario)}/u</span>
                        <span className="text-white font-medium">{formatCurrency(v.totale)}</span>
                      </div>
                    ))}
                  </div>
                  
                  <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-white/[0.04]">
                    <span>Ultimo acquisto: {formatDate(prod.ultima_data)}</span>
                    <span>{prod.num_acquisti} ordini totali</span>
                    <span>Tot. qty: {prod.quantita_totale}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center">
              <Package className="w-10 h-10 mx-auto text-slate-600 mb-2" />
              <p className="text-slate-500 text-sm">
                {clienteProdottiSearch ? `Nessun prodotto trovato per "${clienteProdottiSearch}"` : 'Nessun prodotto acquistato da questo cliente'}
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>


      {/* Card Detail Modal */}
      <Dialog open={!!cardDetailType} onOpenChange={(open) => { if (!open) { setCardDetailType(null); setCardDetail(null); } }}>
        <DialogContent className={cn("max-h-[85vh] overflow-y-auto overflow-x-hidden", cardDetailType === 'alert' ? "sm:max-w-lg" : "sm:max-w-2xl")} data-testid="card-detail-modal">
          <DialogHeader>
            <DialogTitle>
              {cardDetailType === 'fatturato' && 'Analisi Fatturato'}
              {cardDetailType === 'ordini' && 'Analisi Ordini'}
              {cardDetailType === 'clienti' && 'Analisi Clienti'}
              {cardDetailType === 'alert' && 'Dettaglio Alert'}
            </DialogTitle>
          </DialogHeader>
          {loadingCardDetail ? (
            <div className="py-12 flex justify-center"><LoadingSpinner /></div>
          ) : cardDetail ? (
            <div className="space-y-4">

              {/* FATTURATO detail */}
              {cardDetail.tipo === 'fatturato' && (<>
                <div className="flex items-center gap-2 pb-2 border-b border-white/[0.06]">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  <span className="text-xs text-slate-500">Periodo:</span>
                  {[{v:'mese',l:'Mese corrente'},{v:'mese_prec',l:'Mese prec.'},{v:'30gg',l:'30 giorni'},{v:'90gg',l:'90 giorni'}].map(p => (
                    <button key={p.v} onClick={() => { setFatturatoPeriodo(p.v); openCardDetail('fatturato', p.v); }}
                      className={cn("px-2 py-1 rounded-md text-[10px] font-medium transition-all",
                        fatturatoPeriodo === p.v ? "bg-blue-500/20 text-blue-300" : "text-slate-500 hover:text-slate-300"
                      )}>{p.l}</button>
                  ))}
                </div>
                <div className="h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={cardDetail.giornaliero}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="data" tick={{fontSize: 9, fill: '#94a3b8'}} tickFormatter={v => v?.slice(8)} />
                      <YAxis tick={{fontSize: 9, fill: '#94a3b8'}} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                      <Tooltip contentStyle={{background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12}} formatter={(v) => [`${formatCurrency(v)}`, 'Fatturato']} labelFormatter={l => `Giorno ${l?.slice(8)}`} />
                      <Bar dataKey="totale" fill="#3b82f6" radius={[4,4,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                {cardDetail.settimanale?.length > 0 && (
                  <div className="grid grid-cols-4 gap-2">
                    {cardDetail.settimanale.map(w => (
                      <div key={w.settimana} className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/15 text-center">
                        <p className="text-[10px] text-slate-500">{w.settimana}</p>
                        <p className="text-sm font-bold text-blue-400">{formatCurrency(w.totale)}</p>
                      </div>
                    ))}
                  </div>
                )}
                <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] overflow-hidden">
                  <div className="px-3 py-2 bg-white/[0.03] border-b border-white/[0.06]">
                    <span className="text-xs font-semibold text-white">Top 5 Prodotti per Fatturato</span>
                  </div>
                  {cardDetail.top_prodotti?.map((p, i) => (
                    <div key={p.nome} className="flex items-center gap-2 px-3 py-2 border-t border-white/[0.04] hover:bg-white/[0.02]">
                      <span className="w-5 h-5 rounded-full bg-blue-500/15 text-blue-400 text-[10px] font-bold flex items-center justify-center">{i+1}</span>
                      <span className="flex-1 text-xs text-slate-300 truncate">{p.nome}</span>
                      <span className="text-xs font-medium text-blue-400">{formatCurrency(p.totale)}</span>
                    </div>
                  ))}
                </div>
              </>)}

              {/* ORDINI detail */}
              {cardDetail.tipo === 'ordini' && (<>
                <div className="flex items-center gap-2 pb-2 border-b border-white/[0.06]">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  <span className="text-xs text-slate-500">Periodo:</span>
                  {[{v:'mese',l:'Mese corrente'},{v:'mese_prec',l:'Mese prec.'},{v:'30gg',l:'30 giorni'},{v:'90gg',l:'90 giorni'}].map(p => (
                    <button key={p.v} onClick={() => { setOrdiniPeriodo(p.v); openCardDetail('ordini', p.v); }}
                      className={cn("px-2 py-1 rounded-md text-[10px] font-medium transition-all",
                        ordiniPeriodo === p.v ? "bg-emerald-500/20 text-emerald-300" : "text-slate-500 hover:text-slate-300"
                      )}>{p.l}</button>
                  ))}
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/15 text-center">
                    <p className="text-[10px] text-slate-500">Scontrino Medio</p>
                    <p className="text-lg font-bold text-emerald-400">{formatCurrency(cardDetail.scontrino_medio)}</p>
                  </div>
                  {cardDetail.giorni_picco?.slice(0,2).map(g => (
                    <div key={g.data} className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/15 text-center">
                      <p className="text-[10px] text-slate-500">Picco {g.data?.slice(8)}/{g.data?.slice(5,7)}</p>
                      <p className="text-lg font-bold text-emerald-400">{g.ordini} ordini</p>
                    </div>
                  ))}
                </div>
                <div className="h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={cardDetail.giornaliero}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="data" tick={{fontSize: 9, fill: '#94a3b8'}} tickFormatter={v => v?.slice(8)} />
                      <YAxis tick={{fontSize: 9, fill: '#94a3b8'}} />
                      <Tooltip contentStyle={{background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12}} formatter={(v,n) => [n === 'ordini' ? v : formatCurrency(v), n === 'ordini' ? 'Ordini' : 'Totale']} labelFormatter={l => `Giorno ${l?.slice(8)}`} />
                      <Bar dataKey="ordini" fill="#10b981" radius={[4,4,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] overflow-hidden">
                  <div className="px-3 py-2 bg-white/[0.03] border-b border-white/[0.06]">
                    <span className="text-xs font-semibold text-white">Prodotti Piu Richiesti</span>
                  </div>
                  {cardDetail.top_prodotti_richieste?.map((p, i) => (
                    <div key={p.nome} className="flex items-center gap-2 px-3 py-2 border-t border-white/[0.04] hover:bg-white/[0.02]">
                      <span className="w-5 h-5 rounded-full bg-emerald-500/15 text-emerald-400 text-[10px] font-bold flex items-center justify-center">{i+1}</span>
                      <span className="flex-1 text-xs text-slate-300 truncate">{p.nome}</span>
                      <span className="text-xs font-medium text-emerald-400">{p.richieste} richieste</span>
                    </div>
                  ))}
                </div>
              </>)}

              {/* CLIENTI detail */}
              {cardDetail.tipo === 'clienti' && (<>
                {/* Period Selector */}
                <div className="flex items-center gap-2 pb-2 border-b border-white/[0.06]">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  <span className="text-xs text-slate-500">Periodo:</span>
                  {[{v:'mese',l:'Mese corrente'},{v:'mese_prec',l:'Mese prec.'},{v:'30gg',l:'30 giorni'},{v:'90gg',l:'90 giorni'}].map(p => (
                    <button key={p.v} onClick={() => { setCardDetailPeriodo(p.v); openCardDetail('clienti', p.v); }}
                      className={cn("px-2 py-1 rounded-md text-[10px] font-medium transition-all",
                        cardDetailPeriodo === p.v ? "bg-cyan-500/20 text-cyan-300" : "text-slate-500 hover:text-slate-300"
                      )}>{p.l}</button>
                  ))}
                </div>
                <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] overflow-hidden">
                  <div className="px-3 py-2 bg-white/[0.03] border-b border-white/[0.06] flex items-center gap-2">
                    <Users className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="text-xs font-semibold text-white">Top 5 Clienti per Spesa</span>
                  </div>
                  {cardDetail.top_clienti?.map((c, i) => (
                    <div key={c.nome} className="flex items-center gap-2 px-3 py-2 border-t border-white/[0.04] hover:bg-white/[0.02]">
                      <span className="w-5 h-5 rounded-full bg-cyan-500/15 text-cyan-400 text-[10px] font-bold flex items-center justify-center">{i+1}</span>
                      <span className="flex-1 text-xs text-slate-300 truncate">{c.nome}</span>
                      <span className="text-xs text-slate-500">{c.ordini} ord.</span>
                      <span className="text-xs font-medium text-cyan-400">{formatCurrency(c.totale)}</span>
                    </div>
                  ))}
                </div>
                {cardDetail.nuovi_clienti?.length > 0 && (
                  <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] overflow-hidden">
                    <div className="px-3 py-2 bg-white/[0.03] border-b border-white/[0.06] flex items-center gap-2">
                      <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                      <span className="text-xs font-semibold text-white">Nuovi Clienti nel Periodo</span>
                    </div>
                    {cardDetail.nuovi_clienti.map((c, i) => (
                      <div key={c.nome} className="flex items-center gap-2 px-3 py-2 border-t border-white/[0.04]">
                        <span className="flex-1 text-xs text-slate-300 truncate">{c.nome}</span>
                        <span className="text-[10px] text-slate-500">dal {c.dal}</span>
                        <span className="text-xs font-medium text-blue-400">{formatCurrency(c.totale)}</span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] overflow-hidden">
                  <div className="px-3 py-2 bg-white/[0.03] border-b border-white/[0.06] flex items-center gap-2">
                    <Activity className="w-3.5 h-3.5 text-violet-400" />
                    <span className="text-xs font-semibold text-white">Piu Frequenti</span>
                  </div>
                  {cardDetail.piu_frequenti?.map((c, i) => (
                    <div key={c.nome} className="flex items-center gap-2 px-3 py-2 border-t border-white/[0.04]">
                      <span className="flex-1 text-xs text-slate-300 truncate">{c.nome}</span>
                      <span className="text-xs font-medium text-violet-400">{c.visite} visite</span>
                    </div>
                  ))}
                </div>
              </>)}

              {/* ALERT detail */}
              {cardDetail.tipo === 'alert' && (<>
                {/* Sotto Scorta */}
                {cardDetail.sotto_scorta?.length > 0 && (
                  <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] overflow-hidden">
                    <div className="px-3 py-2 bg-red-500/10 border-b border-white/[0.06] flex items-center gap-2">
                      <PackageX className="w-3.5 h-3.5 text-red-400" />
                      <span className="text-xs font-semibold text-white">Sotto Scorta Minima</span>
                      <span className="ml-auto text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded">{cardDetail.sotto_scorta.length}</span>
                    </div>
                    {cardDetail.sotto_scorta.map(p => (
                      <div key={p.nome} className="flex items-center gap-2 px-3 py-2 border-t border-white/[0.04]">
                        <span className="flex-1 text-xs text-slate-300 truncate">{p.nome}</span>
                        <span className="text-xs text-red-400 font-medium">{p.quantita}</span>
                        <span className="text-[10px] text-slate-500">/ {p.minima} min</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* In Esaurimento */}
                {cardDetail.in_esaurimento?.length > 0 && (
                  <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] overflow-hidden">
                    <div className="px-3 py-2 bg-yellow-500/10 border-b border-white/[0.06] flex items-center gap-2">
                      <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />
                      <span className="text-xs font-semibold text-white">In Esaurimento (vicino al minimo)</span>
                      <span className="ml-auto text-[10px] bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded">{cardDetail.in_esaurimento.length}</span>
                    </div>
                    {cardDetail.in_esaurimento.map(p => (
                      <div key={p.nome} className="flex items-center gap-2 px-3 py-2 border-t border-white/[0.04]">
                        <span className="flex-1 text-xs text-slate-300 truncate">{p.nome}</span>
                        <span className="text-xs text-yellow-400 font-medium">{p.quantita}</span>
                        <span className="text-[10px] text-slate-500">/ {p.minima} min</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* In Scadenza */}
                {cardDetail.in_scadenza?.length > 0 && (
                  <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] overflow-hidden">
                    <div className="px-3 py-2 bg-orange-500/10 border-b border-white/[0.06] flex items-center gap-2">
                      <AlertCircle className="w-3.5 h-3.5 text-orange-400" />
                      <span className="text-xs font-semibold text-white">In Scadenza (30gg)</span>
                      <span className="ml-auto text-[10px] bg-orange-500/20 text-orange-400 px-1.5 py-0.5 rounded">{cardDetail.in_scadenza.length}</span>
                    </div>
                    {cardDetail.in_scadenza.map(p => (
                      <div key={p.nome} className="flex items-center gap-2 px-3 py-2 border-t border-white/[0.04]">
                        <span className="flex-1 text-xs text-slate-300 truncate">{p.nome}</span>
                        <span className="text-xs text-slate-400">{p.quantita} pz</span>
                        <span className="text-xs text-orange-400">{p.scadenza}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Clienti Inattivi con selettore periodo e dettagli */}
                <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] overflow-hidden">
                  <div className="px-3 py-2 bg-amber-500/10 border-b border-white/[0.06]">
                    <div className="flex items-center gap-2 mb-1.5">
                      <UserX className="w-3.5 h-3.5 text-amber-400" />
                      <span className="text-xs font-semibold text-white">Clienti Inattivi</span>
                      {cardDetail.clienti_inattivi?.length > 0 && (
                        <span className="ml-auto text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded">{cardDetail.clienti_inattivi.length}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5">
                      {[{v:'7gg',l:'3-7 gg'},{v:'30gg',l:'7-30 gg'},{v:'60gg',l:'30-60 gg'}].map(p => (
                        <button key={p.v} onClick={() => { setAlertPeriodo(p.v); openCardDetail('alert', p.v); }}
                          className={cn("px-2 py-0.5 rounded text-[10px] font-medium transition-all",
                            alertPeriodo === p.v ? "bg-amber-500/20 text-amber-300" : "text-slate-500 hover:text-slate-300"
                          )}>{p.l}</button>
                      ))}
                    </div>
                  </div>
                  {cardDetail.clienti_inattivi?.length > 0 ? cardDetail.clienti_inattivi.map(c => (
                    <div key={c.nome} className="group px-3 py-2.5 border-t border-white/[0.04] hover:bg-white/[0.04] transition-all">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-slate-200 flex-1 truncate">{c.nome}</span>
                        <span className="text-[10px] text-slate-500">{c.giorni_inattivo}gg</span>
                        <span className="text-xs font-medium text-amber-400">{formatCurrency(c.fatturato_90gg)}</span>
                      </div>
                      <div className="max-h-0 overflow-hidden opacity-0 group-hover:max-h-20 group-hover:opacity-100 transition-all duration-300 ease-out">
                        <div className="flex items-center gap-3 text-[11px] text-white/80 mt-1.5">
                          <span>Ultimo ordine: {c.ultimo_ordine}</span>
                          <span>{c.num_ordini} ordini (90gg)</span>
                        </div>
                        {c.top_prodotti?.length > 0 && (
                          <p className="text-[11px] text-white/60 mt-0.5 truncate">Acquistava: {c.top_prodotti.join(', ')}</p>
                        )}
                      </div>
                    </div>
                  )) : (
                    <p className="px-3 py-4 text-center text-xs text-slate-500">Nessun cliente inattivo in questo periodo</p>
                  )}
                </div>

                {!cardDetail.sotto_scorta?.length && !cardDetail.in_esaurimento?.length && !cardDetail.in_scadenza?.length && !cardDetail.clienti_inattivi?.length && (
                  <p className="text-center py-8 text-sm text-slate-500">Nessun alert attivo</p>
                )}
              </>)}

            </div>
          ) : (
            <p className="text-center py-8 text-sm text-slate-500">Nessun dato disponibile</p>
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
