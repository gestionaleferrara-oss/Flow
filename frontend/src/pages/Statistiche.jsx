import { useState, useEffect } from 'react';
import axios from 'axios';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line
} from 'recharts';
import {
  Euro, Package, Users, Calendar, RefreshCw, Truck,
  Download, Filter, X
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
      a.download = `flusso_${viewMode}.${formato === 'excel' ? 'xlsx' : 'csv'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      toast.success(`Export ${formato.toUpperCase()} avviato`);
    } catch (e) {
      toast.error('Errore nell\'export');
    }
  };

  const Autocomplete = ({ placeholder, value, field, suggestions }) => (
    <div className="relative">
      <Input
        placeholder={placeholder}
        value={value}
        onChange={(e) => setFilters({ ...filters, [field]: e.target.value })}
        onFocus={() => setShowSuggestions({ [field]: true })}
        onBlur={() => setTimeout(() => setShowSuggestions({}), 200)}
        className="h-8 text-sm"
        data-testid={`filter-${field}`}
      />
      {showSuggestions[field] && value && (
        <div className="absolute top-full left-0 right-0 bg-slate-800 border border-slate-700 rounded-lg mt-1 max-h-40 overflow-auto z-20">
          {suggestions.filter(s => s.toLowerCase().includes(value.toLowerCase())).slice(0, 8).map((s, i) => (
            <div key={i} className="px-3 py-1.5 hover:bg-slate-700 cursor-pointer text-xs"
              onClick={() => setFilters({ ...filters, [field]: s })}>{s}</div>
          ))}
        </div>
      )}
    </div>
  );

  if (loading && !data) return <LoadingSpinner fullScreen />;

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
            onClick={() => applyPreset(p.key)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              activePreset === p.key
                ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                : "bg-slate-800/40 text-slate-400 hover:text-slate-300 hover:bg-slate-800/80 border border-transparent"
            )}
          >
            {p.label}
          </button>
        ))}

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
        <div className="flex flex-wrap items-end gap-3 mb-6 p-3 bg-slate-800/30 rounded-lg border border-slate-700/50">
          <div className="w-44">
            <Autocomplete placeholder="Prodotto" value={filters.prodotto} field="prodotto" suggestions={lists.prodotti} />
          </div>
          {viewMode === 'vendite' ? (
            <div className="w-44">
              <Autocomplete placeholder="Cliente" value={filters.cliente} field="cliente" suggestions={lists.clienti} />
            </div>
          ) : (
            <div className="w-44">
              <Autocomplete placeholder="Fornitore" value={filters.fornitore} field="fornitore" suggestions={lists.fornitori || []} />
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

      {/* KPI Cards - solo con filtri attivi */}
      {hasActiveFilters && (
        viewMode === 'vendite' ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8" data-testid="kpi-cards-vendite">
            <StatCard label="Fatturato Periodo" value={data?.totaleEuro || 0} format="currency" icon={Euro} />
            <StatCard label="Articoli Venduti" value={data?.totaleArticoli || 0} icon={Package} />
            <StatCard label="Clienti Attivi" value={data?.clientiAttivi || 0} icon={Users} />
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
              <HBarChart data={data?.topProdotti} color="#10B981" label="Fatturato" />
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

function HBarChart({ data, color, label }) {
  const d = data || [];
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={d} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis type="number" stroke="#475569" fontSize={11} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
        <YAxis type="category" dataKey="nome" stroke="#475569" fontSize={10} width={110}
          tickFormatter={v => v?.length > 14 ? v.slice(0, 14) + '..' : v} />
        <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: 8 }}
          formatter={v => [formatCurrency(v), label]} />
        <Bar dataKey="totale_euro" fill={color} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
