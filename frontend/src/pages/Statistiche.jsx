import { useState, useEffect } from 'react';
import axios from 'axios';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line
} from 'recharts';
import {
  Euro, Package, Users, Calendar, RefreshCw, Truck,
  Download, Filter, X, TrendingUp
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import StatCard from '@/components/StatCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, cn } from '@/lib/utils';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#84CC16'];

// Autocomplete component - extracted to prevent re-creation on parent re-render
function FilterAutocomplete({ placeholder, value, field, suggestions, filters, setFilters }) {
  const [isOpen, setIsOpen] = useState(false);
  const filtered = suggestions.filter(s => s.toLowerCase().includes((value || '').toLowerCase())).slice(0, 10);
  
  return (
    <div className="relative">
      <Input
        placeholder={placeholder}
        value={value}
        onChange={(e) => {
          setFilters({ ...filters, [field]: e.target.value });
          setIsOpen(true);
        }}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setTimeout(() => setIsOpen(false), 250)}
        className="h-8 text-sm"
        data-testid={`filter-${field}`}
      />
      {isOpen && value && filtered.length > 0 && (
        <div className="absolute top-full left-0 right-0 bg-slate-800 border border-slate-700 rounded-lg mt-1 max-h-48 overflow-auto z-50 shadow-xl">
          {filtered.map((s, i) => (
            <div 
              key={i} 
              className="px-3 py-2 hover:bg-slate-700 cursor-pointer text-xs text-slate-200"
              onMouseDown={(e) => {
                e.preventDefault();
                setFilters({ ...filters, [field]: s });
                setIsOpen(false);
              }}
            >
              {s}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Statistiche() {
  const [data, setData] = useState(null);
  const [dataAcquisti, setDataAcquisti] = useState(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('vendite');
  const [filters, setFilters] = useState({ prodotto: '', cliente: '', fornitore: '', startDate: '', endDate: '' });
  const [lists, setLists] = useState({ prodotti: [], clienti: [], fornitori: [] });
  const [showSuggestions, setShowSuggestions] = useState({});
  const [showFilters, setShowFilters] = useState(false);
  const [activePreset, setActivePreset] = useState(null);
  
  // Month comparison state - separate month and year
  const [showCompare, setShowCompare] = useState(false);
  const [compareData, setCompareData] = useState(null);
  const [compare1Month, setCompare1Month] = useState('');
  const [compare1Year, setCompare1Year] = useState('');
  const [compare2Month, setCompare2Month] = useState('');
  const [compare2Year, setCompare2Year] = useState('');
  const [loadingCompare, setLoadingCompare] = useState(false);

  const hasActiveFilters = filters.prodotto || filters.cliente || filters.fornitore || filters.startDate || filters.endDate;

  useEffect(() => { loadLists(); }, []);

  useEffect(() => {
    const timer = setTimeout(() => loadStatistiche(), 400);
    return () => clearTimeout(timer);
  }, [filters]);

  const loadLists = async () => {
    try {
      const [v, a] = await Promise.all([
        axios.get(`${API}/statistiche/lists`),
        axios.get(`${API}/statistiche/acquisti/lists`)
      ]);
      setLists({ prodotti: v.data.prodotti, clienti: v.data.clienti, fornitori: a.data.fornitori });
    } catch (e) { console.error(e); }
  };

  const loadStatistiche = async () => {
    setLoading(true);
    try {
      const p = new URLSearchParams();
      if (filters.prodotto) p.append('prodotto', filters.prodotto);
      if (filters.startDate) p.append('start_date', filters.startDate);
      if (filters.endDate) p.append('end_date', filters.endDate);
      const pv = new URLSearchParams(p);
      if (filters.cliente) pv.append('cliente', filters.cliente);
      const pa = new URLSearchParams(p);
      if (filters.fornitore) pa.append('fornitore', filters.fornitore);
      const [vr, ar] = await Promise.all([
        axios.get(`${API}/statistiche?${pv}`),
        axios.get(`${API}/statistiche/acquisti?${pa}`)
      ]);
      setData(vr.data);
      setDataAcquisti(ar.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };

  const applyPreset = (preset) => {
    setActivePreset(preset);
    const today = new Date();
    let s, e;
    switch (preset) {
      case 'last30':
        e = new Date(today); s = new Date(today); s.setDate(s.getDate() - 30); break;
      case 'currentMonth':
        s = new Date(today.getFullYear(), today.getMonth(), 1);
        e = new Date(today.getFullYear(), today.getMonth() + 1, 0); break;
      case 'lastMonth':
        s = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        e = new Date(today.getFullYear(), today.getMonth(), 0); break;
      case 'last3Months':
        e = new Date(today); s = new Date(today); s.setMonth(s.getMonth() - 3); break;
      default: return;
    }
    setFilters({ ...filters, startDate: s.toISOString().split('T')[0], endDate: e.toISOString().split('T')[0] });
  };

  const clearFilters = () => {
    setFilters({ prodotto: '', cliente: '', fornitore: '', startDate: '', endDate: '' });
    setActivePreset(null);
  };

  const handleExport = async (formato) => {
    try {
      const p = new URLSearchParams();
      p.append('formato', formato);
      p.append('tipo', viewMode === 'vendite' ? 'vendite' : 'acquisti');
      if (filters.prodotto) p.append('prodotto', filters.prodotto);
      if (filters.cliente) p.append('cliente', filters.cliente);
      if (filters.fornitore) p.append('fornitore', filters.fornitore);
      if (filters.startDate) p.append('start_date', filters.startDate);
      if (filters.endDate) p.append('end_date', filters.endDate);
      
      const url = `${API}/statistiche/export?${p}`;
      const a = document.createElement('a');
      a.href = url;
      a.download = `flow_${viewMode}.${formato === 'excel' ? 'xlsx' : 'csv'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      toast.success(`Export ${formato.toUpperCase()} avviato`);
    } catch (e) {
      toast.error('Errore nell\'export');
    }
  };

  const handlePdfExport = async () => {
    try {
      const p = new URLSearchParams();
      p.append('tipo', viewMode === 'vendite' ? 'vendite' : 'acquisti');
      if (filters.startDate) p.append('start_date', filters.startDate);
      if (filters.endDate) p.append('end_date', filters.endDate);
      const url = `${API}/statistiche/export/pdf?${p}`;
      window.open(url, '_blank');
      toast.success('PDF generato');
    } catch (e) {
      toast.error('Errore nella generazione PDF');
    }
  };

  // Month and year options for comparison
  const monthOptions = [
    { value: '01', label: 'Gen' }, { value: '02', label: 'Feb' }, { value: '03', label: 'Mar' },
    { value: '04', label: 'Apr' }, { value: '05', label: 'Mag' }, { value: '06', label: 'Giu' },
    { value: '07', label: 'Lug' }, { value: '08', label: 'Ago' }, { value: '09', label: 'Set' },
    { value: '10', label: 'Ott' }, { value: '11', label: 'Nov' }, { value: '12', label: 'Dic' }
  ];
  const currentYear = new Date().getFullYear();
  const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i); // Last 5 years

  // Load comparison data
  const loadCompareData = async () => {
    if (!compare1Month || !compare1Year || !compare2Month || !compare2Year) {
      toast.error('Seleziona mese e anno per entrambi i periodi');
      return;
    }
    setLoadingCompare(true);
    try {
      const y1 = parseInt(compare1Year);
      const m1 = parseInt(compare1Month);
      const y2 = parseInt(compare2Year);
      const m2 = parseInt(compare2Month);
      
      const start1 = `${y1}-${compare1Month}-01`;
      const end1 = new Date(y1, m1, 0).toISOString().split('T')[0];
      const start2 = `${y2}-${compare2Month}-01`;
      const end2 = new Date(y2, m2, 0).toISOString().split('T')[0];

      const endpoint = viewMode === 'vendite' ? 'statistiche' : 'statistiche/acquisti';
      const [res1, res2] = await Promise.all([
        axios.get(`${API}/${endpoint}?start_date=${start1}&end_date=${end1}`),
        axios.get(`${API}/${endpoint}?start_date=${start2}&end_date=${end2}`)
      ]);

      const monthLabels = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic'];
      setCompareData({
        mese1: { label: `${monthLabels[m1 - 1]} ${y1}`, data: res1.data },
        mese2: { label: `${monthLabels[m2 - 1]} ${y2}`, data: res2.data }
      });
    } catch (e) {
      console.error(e);
      toast.error('Errore nel caricamento dati confronto');
    } finally {
      setLoadingCompare(false);
    }
  };

  if (loading && !data) return <div className="flex items-center justify-center h-64"><LoadingSpinner /></div>;

  const presets = [
    { key: 'last30', label: '30gg' },
    { key: 'currentMonth', label: 'Questo mese' },
    { key: 'lastMonth', label: 'Mese prec.' },
    { key: 'last3Months', label: '3 mesi' },
  ];

  return (
    <PageWrapper>
      <PageHeader
        title="Statistiche"
        subtitle={viewMode === 'vendite' ? "Analisi vendite" : "Analisi acquisti"}
      >
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => handlePdfExport()} className="bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20" data-testid="export-pdf">
            <Download className="w-4 h-4 mr-1" /> PDF
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleExport('csv')} data-testid="export-csv">
            <Download className="w-4 h-4 mr-1" /> CSV
          </Button>
          <Button variant="outline" size="sm" onClick={loadStatistiche} data-testid="refresh-stats">
            <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
          </Button>
        </div>
      </PageHeader>

      {/* Mode Switch + Compact Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        {/* View switch */}
        <div className="flex p-1 bg-slate-800/60 rounded-lg">
          <button
            onClick={() => setViewMode('vendite')}
            className={cn(
              "flex items-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-medium transition-all",
              viewMode === 'vendite'
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : "text-slate-400 hover:text-slate-300"
            )}
            data-testid="switch-vendite"
          >
            <Users className="w-3.5 h-3.5" /> Vendite
          </button>
          <button
            onClick={() => setViewMode('acquisti')}
            className={cn(
              "flex items-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-medium transition-all",
              viewMode === 'acquisti'
                ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                : "text-slate-400 hover:text-slate-300"
            )}
            data-testid="switch-acquisti"
          >
            <Truck className="w-3.5 h-3.5" /> Acquisti
          </button>
        </div>

        {/* Divider */}
        <div className="w-px h-6 bg-slate-700" />

        {/* Preset buttons - inline */}
        {presets.map(p => (
          <button
            key={p.key}
            onClick={() => { applyPreset(p.key); setShowCompare(false); }}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              activePreset === p.key && !showCompare
                ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                : "bg-slate-800/40 text-slate-400 hover:text-slate-300 hover:bg-slate-800/80 border border-transparent"
            )}
          >
            {p.label}
          </button>
        ))}
        
        {/* Compare months button */}
        <button
          onClick={() => { setShowCompare(!showCompare); setActivePreset(null); setCompareData(null); }}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
            showCompare
              ? "bg-violet-500/20 text-violet-400 border border-violet-500/30"
              : "bg-slate-800/40 text-slate-400 hover:text-slate-300 hover:bg-slate-800/80 border border-transparent"
          )}
          data-testid="compare-months-btn"
        >
          <TrendingUp className="w-3.5 h-3.5" />
          Confronta
        </button>

        {/* Divider */}
        <div className="w-px h-6 bg-slate-700" />

        {/* Expand filters toggle */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
            showFilters || hasActiveFilters
              ? "bg-slate-700 text-white"
              : "bg-slate-800/40 text-slate-400 hover:text-slate-300"
          )}
        >
          <Filter className="w-3.5 h-3.5" />
          Filtri
          {hasActiveFilters && (
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
          )}
        </button>

        {hasActiveFilters && (
          <button onClick={clearFilters} className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1">
            <X className="w-3 h-3" /> Reset
          </button>
        )}
      </div>

      {/* Expanded filters panel */}
      {showFilters && (
        <div className="flex flex-wrap items-end gap-3 mb-6 p-3 bg-slate-800/30 rounded-lg border border-slate-700/50 overflow-visible">
          <div className="w-44 relative z-20">
            <FilterAutocomplete placeholder="Prodotto" value={filters.prodotto} field="prodotto" suggestions={lists.prodotti} filters={filters} setFilters={setFilters} />
          </div>
          {viewMode === 'vendite' ? (
            <div className="w-44 relative z-10">
              <FilterAutocomplete placeholder="Cliente" value={filters.cliente} field="cliente" suggestions={lists.clienti} filters={filters} setFilters={setFilters} />
            </div>
          ) : (
            <div className="w-44 relative z-10">
              <FilterAutocomplete placeholder="Fornitore" value={filters.fornitore} field="fornitore" suggestions={lists.fornitori || []} filters={filters} setFilters={setFilters} />
            </div>
          )}
          <div className="w-36">
            <Input type="date" value={filters.startDate} onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
              className="h-8 text-sm" data-testid="filter-start-date" />
          </div>
          <div className="w-36">
            <Input type="date" value={filters.endDate} onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
              className="h-8 text-sm" data-testid="filter-end-date" />
          </div>
        </div>
      )}

      {/* Month comparison panel */}
      {showCompare && (
        <div className="mb-6 p-4 bg-violet-500/5 rounded-xl border border-violet-500/20">
          <div className="flex flex-wrap items-center gap-3 mb-4">
            {/* Period 1 */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-violet-400 font-medium">Periodo 1:</span>
              <select
                value={compare1Month}
                onChange={(e) => setCompare1Month(e.target.value)}
                className="h-8 w-20 px-2 rounded-md bg-slate-700 border border-slate-500 text-xs text-white"
                data-testid="compare-month-1"
              >
                <option value="">Mese</option>
                <option value="01">Gennaio</option>
                <option value="02">Febbraio</option>
                <option value="03">Marzo</option>
                <option value="04">Aprile</option>
                <option value="05">Maggio</option>
                <option value="06">Giugno</option>
                <option value="07">Luglio</option>
                <option value="08">Agosto</option>
                <option value="09">Settembre</option>
                <option value="10">Ottobre</option>
                <option value="11">Novembre</option>
                <option value="12">Dicembre</option>
              </select>
              <select
                value={compare1Year}
                onChange={(e) => setCompare1Year(e.target.value)}
                className="h-8 w-20 px-2 rounded-md bg-slate-700 border border-slate-500 text-xs text-white"
                data-testid="compare-year-1"
              >
                <option value="">Anno</option>
                <option value="2026">2026</option>
                <option value="2025">2025</option>
                <option value="2024">2024</option>
                <option value="2023">2023</option>
                <option value="2022">2022</option>
              </select>
            </div>

            <span className="text-slate-500 text-sm font-medium">vs</span>

            {/* Period 2 */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-cyan-400 font-medium">Periodo 2:</span>
              <select
                value={compare2Month}
                onChange={(e) => setCompare2Month(e.target.value)}
                className="h-8 w-20 px-2 rounded-md bg-slate-700 border border-slate-500 text-xs text-white"
                data-testid="compare-month-2"
              >
                <option value="">Mese</option>
                <option value="01">Gennaio</option>
                <option value="02">Febbraio</option>
                <option value="03">Marzo</option>
                <option value="04">Aprile</option>
                <option value="05">Maggio</option>
                <option value="06">Giugno</option>
                <option value="07">Luglio</option>
                <option value="08">Agosto</option>
                <option value="09">Settembre</option>
                <option value="10">Ottobre</option>
                <option value="11">Novembre</option>
                <option value="12">Dicembre</option>
              </select>
              <select
                value={compare2Year}
                onChange={(e) => setCompare2Year(e.target.value)}
                className="h-8 w-20 px-2 rounded-md bg-slate-700 border border-slate-500 text-xs text-white"
                data-testid="compare-year-2"
              >
                <option value="">Anno</option>
                <option value="2026">2026</option>
                <option value="2025">2025</option>
                <option value="2024">2024</option>
                <option value="2023">2023</option>
                <option value="2022">2022</option>
              </select>
            </div>

            <Button 
              onClick={loadCompareData}
              disabled={loadingCompare || !compare1Month || !compare1Year || !compare2Month || !compare2Year}
              size="sm"
              className="bg-violet-500 hover:bg-violet-600 text-white h-8 px-4"
              data-testid="compare-load-btn"
            >
              {loadingCompare ? <RefreshCw className="w-3 h-3 animate-spin" /> : 'Confronta'}
            </Button>
          </div>
          
          {/* Comparison results */}
          {compareData && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Month 1 card */}
              <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
                <h4 className="text-sm font-semibold text-violet-400 mb-3">{compareData.mese1.label}</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">Fatturato</span>
                    <span className="text-sm font-semibold text-white">{formatCurrency(compareData.mese1.data.totaleEuro || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">Articoli</span>
                    <span className="text-sm text-slate-300">{(compareData.mese1.data.totaleArticoli || 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">{viewMode === 'vendite' ? 'Clienti' : 'Fornitori'}</span>
                    <span className="text-sm text-slate-300">{viewMode === 'vendite' ? compareData.mese1.data.clientiAttivi || 0 : compareData.mese1.data.fornitoriAttivi || 0}</span>
                  </div>
                </div>
              </div>
              
              {/* Month 2 card */}
              <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
                <h4 className="text-sm font-semibold text-cyan-400 mb-3">{compareData.mese2.label}</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">Fatturato</span>
                    <span className="text-sm font-semibold text-white">{formatCurrency(compareData.mese2.data.totaleEuro || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">Articoli</span>
                    <span className="text-sm text-slate-300">{(compareData.mese2.data.totaleArticoli || 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-slate-400">{viewMode === 'vendite' ? 'Clienti' : 'Fornitori'}</span>
                    <span className="text-sm text-slate-300">{viewMode === 'vendite' ? compareData.mese2.data.clientiAttivi || 0 : compareData.mese2.data.fornitoriAttivi || 0}</span>
                  </div>
                </div>
              </div>
              
              {/* Difference card */}
              <div className="md:col-span-2 p-4 bg-gradient-to-r from-violet-500/10 to-cyan-500/10 rounded-lg border border-violet-500/20">
                <h4 className="text-sm font-semibold text-white mb-3">Variazione</h4>
                <div className="grid grid-cols-3 gap-4">
                  {(() => {
                    const fatt1 = compareData.mese1.data.totaleEuro || 0;
                    const fatt2 = compareData.mese2.data.totaleEuro || 0;
                    const diffFatt = fatt2 - fatt1;
                    const pctFatt = fatt1 > 0 ? ((fatt2 - fatt1) / fatt1 * 100) : 0;
                    
                    const art1 = compareData.mese1.data.totaleArticoli || 0;
                    const art2 = compareData.mese2.data.totaleArticoli || 0;
                    const diffArt = art2 - art1;
                    const pctArt = art1 > 0 ? ((art2 - art1) / art1 * 100) : 0;
                    
                    const cli1 = viewMode === 'vendite' ? (compareData.mese1.data.clientiAttivi || 0) : (compareData.mese1.data.fornitoriAttivi || 0);
                    const cli2 = viewMode === 'vendite' ? (compareData.mese2.data.clientiAttivi || 0) : (compareData.mese2.data.fornitoriAttivi || 0);
                    const diffCli = cli2 - cli1;
                    const pctCli = cli1 > 0 ? ((cli2 - cli1) / cli1 * 100) : 0;
                    
                    return (
                      <>
                        <div className="text-center">
                          <div className="text-xs text-slate-400 mb-1">Fatturato</div>
                          <div className={cn("text-lg font-bold", diffFatt >= 0 ? "text-emerald-400" : "text-red-400")}>
                            {diffFatt >= 0 ? '+' : ''}{formatCurrency(diffFatt)}
                          </div>
                          <div className={cn("text-xs", pctFatt >= 0 ? "text-emerald-400" : "text-red-400")}>
                            ({pctFatt >= 0 ? '+' : ''}{pctFatt.toFixed(1)}%)
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-slate-400 mb-1">Articoli</div>
                          <div className={cn("text-lg font-bold", diffArt >= 0 ? "text-emerald-400" : "text-red-400")}>
                            {diffArt >= 0 ? '+' : ''}{diffArt.toLocaleString()}
                          </div>
                          <div className={cn("text-xs", pctArt >= 0 ? "text-emerald-400" : "text-red-400")}>
                            ({pctArt >= 0 ? '+' : ''}{pctArt.toFixed(1)}%)
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-slate-400 mb-1">{viewMode === 'vendite' ? 'Clienti' : 'Fornitori'}</div>
                          <div className={cn("text-lg font-bold", diffCli >= 0 ? "text-emerald-400" : "text-red-400")}>
                            {diffCli >= 0 ? '+' : ''}{diffCli}
                          </div>
                          <div className={cn("text-xs", pctCli >= 0 ? "text-emerald-400" : "text-red-400")}>
                            ({pctCli >= 0 ? '+' : ''}{pctCli.toFixed(1)}%)
                          </div>
                        </div>
                      </>
                    );
                  })()}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* KPI Cards - solo con filtri attivi */}
      {hasActiveFilters && (
        viewMode === 'vendite' ? (
          <div className="space-y-3 mb-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6" data-testid="kpi-cards-vendite">
              <StatCard label="Fatturato Periodo" value={data?.totaleEuro || 0} format="currency" icon={Euro} />
              <StatCard label="Articoli Venduti" value={data?.totaleArticoli || 0} icon={Package} />
              <StatCard label="Clienti Attivi" value={data?.clientiAttivi || 0} icon={Users} />
            </div>
            {/* Margine Banner */}
            {data?.margineStimato > 0 && (
              <div className="flex items-center gap-4 px-4 py-2 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs text-slate-400">Margine Stimato:</span>
                  <span className="text-sm font-semibold text-emerald-400">+{data.margineStimato.toFixed(1)}%</span>
                </div>
                <div className="text-xs text-slate-500">
                  Profitto: <span className="text-emerald-400 font-medium">{formatCurrency(data.profittoStimato || 0)}</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8" data-testid="kpi-cards-acquisti">
            <StatCard label="Speso Periodo" value={dataAcquisti?.totaleEuro || 0} format="currency" icon={Euro} />
            <StatCard label="Articoli Acquistati" value={dataAcquisti?.totaleArticoli || 0} icon={Package} />
            <StatCard label="Fornitori Attivi" value={dataAcquisti?.fornitoriAttivi || 0} icon={Truck} />
          </div>
        )
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {viewMode === 'vendite' ? (
          <>
            <ChartCard title="Andamento Vendite Mensili">
              <TimeChart data={data?.venditeMensili} color="#3B82F6" label="Vendite" gradientId="gVendite" />
            </ChartCard>
            <ChartCard title="Top Clienti">
              <PieChartCard data={data?.topClienti} />
            </ChartCard>
            <ChartCard title="Top Prodotti per Fatturato">
              <HBarChart data={data?.topProdotti} color="#10B981" label="Fatturato" showMargin={true} />
            </ChartCard>
          </>
        ) : (
          <>
            <ChartCard title="Andamento Acquisti Mensili">
              <TimeChart data={dataAcquisti?.acquistiMensili} color="#3B82F6" label="Acquisti" gradientId="gAcquisti" />
            </ChartCard>
            <ChartCard title="Top Fornitori">
              <PieChartCard data={dataAcquisti?.topFornitori} />
            </ChartCard>
            <ChartCard title="Top Prodotti Acquistati">
              <HBarChart data={dataAcquisti?.topProdotti} color="#3B82F6" label="Speso" />
            </ChartCard>
          </>
        )}
      </div>
    </PageWrapper>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="bg-card border border-border/50 p-5 rounded-xl">
      <h3 className="font-heading text-sm font-semibold uppercase tracking-wider text-slate-400 mb-4">{title}</h3>
      <div className="h-[280px]">{children}</div>
    </div>
  );
}

function TimeChart({ data, color, label, gradientId }) {
  const d = data || [];
  return (
    <ResponsiveContainer width="100%" height="100%">
      {d.length > 1 ? (
        <AreaChart data={d}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="data" stroke="#475569" fontSize={11} />
          <YAxis stroke="#475569" fontSize={11} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
          <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: 8 }}
            formatter={v => [formatCurrency(v), label]} />
          <Area type="monotone" dataKey="totale" stroke={color} fillOpacity={1} fill={`url(#${gradientId})`} />
        </AreaChart>
      ) : (
        <BarChart data={d}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="data" stroke="#475569" fontSize={11} />
          <YAxis stroke="#475569" fontSize={11} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
          <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: 8 }}
            formatter={v => [formatCurrency(v), label]} />
          <Bar dataKey="totale" fill={color} radius={[4, 4, 0, 0]} />
        </BarChart>
      )}
    </ResponsiveContainer>
  );
}

function PieChartCard({ data }) {
  const d = data || [];
  if (!d.length) return <div className="flex items-center justify-center h-full text-slate-500 text-sm">Nessun dato</div>;
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie data={d} cx="50%" cy="50%" outerRadius={100} innerRadius={40} dataKey="spesa" nameKey="nome"
          isAnimationActive={false}
          label={({ percent }) => percent > 0.03 ? `${(percent * 100).toFixed(0)}%` : ''}
          labelLine={{ stroke: '#475569', strokeWidth: 1 }}>
          {d.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Pie>
        <Tooltip 
          contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
          itemStyle={{ color: '#fff' }}
          labelStyle={{ color: '#94a3b8' }}
          formatter={(v, _, props) => [formatCurrency(v), props.payload.nome]} 
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

function HBarChart({ data, color, label, showMargin = false }) {
  const d = data || [];
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={d} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis type="number" stroke="#475569" fontSize={11} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
        <YAxis type="category" dataKey="nome" stroke="#475569" fontSize={10} width={110}
          tickFormatter={v => v?.length > 14 ? v.slice(0, 14) + '..' : v} />
        <Tooltip 
          contentStyle={{ background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: 8 }}
          formatter={(value, name, props) => {
            const result = [[formatCurrency(value), label]];
            if (showMargin && props.payload.margine_pct !== undefined) {
              result.push([`${props.payload.margine_pct > 0 ? '+' : ''}${props.payload.margine_pct}%`, 'Margine']);
            }
            if (showMargin && props.payload.profitto !== undefined) {
              result.push([formatCurrency(props.payload.profitto), 'Profitto']);
            }
            return result;
          }}
        />
        <Bar dataKey="totale_euro" fill={color} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
