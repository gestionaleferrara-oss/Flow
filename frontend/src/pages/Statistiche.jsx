import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line
} from 'recharts';
import {
  Euro,
  Package,
  Users,
  Filter,
  Calendar,
  RefreshCw,
  Truck
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import StatCard from '@/components/StatCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#84CC16'];

export default function Statistiche() {
  const [data, setData] = useState(null);
  const [dataAcquisti, setDataAcquisti] = useState(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('vendite');
  const [filters, setFilters] = useState({
    prodotto: '',
    cliente: '',
    fornitore: '',
    startDate: '',
    endDate: ''
  });
  const [lists, setLists] = useState({ prodotti: [], clienti: [], fornitori: [] });
  const [showSuggestions, setShowSuggestions] = useState({ prodotto: false, cliente: false, fornitore: false });
  const [clientiTrend, setClientiTrend] = useState([]);
  const [fornitoriTrend, setFornitoriTrend] = useState([]);

  const hasActiveFilters = filters.prodotto || filters.cliente || filters.fornitore || filters.startDate || filters.endDate;

  useEffect(() => {
    loadLists();
    loadClientiTrend();
    loadFornitoriTrend();
  }, []);

  // Debounced filter loading
  useEffect(() => {
    const timer = setTimeout(() => {
      loadStatistiche();
    }, 400);
    return () => clearTimeout(timer);
  }, [filters]);

  const loadLists = async () => {
    try {
      const [venditeRes, acquistiRes] = await Promise.all([
        axios.get(`${API}/statistiche/lists`),
        axios.get(`${API}/statistiche/acquisti/lists`)
      ]);
      setLists({
        prodotti: venditeRes.data.prodotti,
        clienti: venditeRes.data.clienti,
        fornitori: acquistiRes.data.fornitori
      });
    } catch (error) {
      console.error('Error loading lists:', error);
    }
  };

  const loadStatistiche = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.prodotto) params.append('prodotto', filters.prodotto);
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      
      const paramsVendite = new URLSearchParams(params);
      if (filters.cliente) paramsVendite.append('cliente', filters.cliente);
      
      const paramsAcquisti = new URLSearchParams(params);
      if (filters.fornitore) paramsAcquisti.append('fornitore', filters.fornitore);
      
      const [venditeRes, acquistiRes] = await Promise.all([
        axios.get(`${API}/statistiche?${paramsVendite}`),
        axios.get(`${API}/statistiche/acquisti?${paramsAcquisti}`)
      ]);
      
      setData(venditeRes.data);
      setDataAcquisti(acquistiRes.data);
    } catch (error) {
      console.error('Error loading statistiche:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadClientiTrend = async () => {
    try {
      const response = await axios.get(`${API}/statistiche/clienti-trend`);
      setClientiTrend(response.data);
    } catch (error) {
      console.error('Error loading clienti trend:', error);
    }
  };

  const loadFornitoriTrend = async () => {
    try {
      const response = await axios.get(`${API}/statistiche/fornitori-trend`);
      setFornitoriTrend(response.data);
    } catch (error) {
      console.error('Error loading fornitori trend:', error);
    }
  };

  const applyPreset = (preset) => {
    const today = new Date();
    let startDate, endDate;

    switch (preset) {
      case 'last30':
        endDate = new Date(today);
        startDate = new Date(today);
        startDate.setDate(startDate.getDate() - 30);
        break;
      case 'currentMonth':
        startDate = new Date(today.getFullYear(), today.getMonth(), 1);
        endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        break;
      case 'lastMonth':
        startDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        endDate = new Date(today.getFullYear(), today.getMonth(), 0);
        break;
      case 'last3Months':
        endDate = new Date(today);
        startDate = new Date(today);
        startDate.setMonth(startDate.getMonth() - 3);
        break;
      default:
        return;
    }

    setFilters({
      ...filters,
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0]
    });
  };

  const clearFilters = () => {
    setFilters({ prodotto: '', cliente: '', fornitore: '', startDate: '', endDate: '' });
  };

  if (loading && !data) return <LoadingSpinner fullScreen />;

  // Determine which period label to show
  const getPeriodLabel = () => {
    if (filters.startDate && filters.endDate) {
      return `${filters.startDate} - ${filters.endDate}`;
    }
    if (filters.startDate) return `Dal ${filters.startDate}`;
    if (filters.endDate) return `Fino al ${filters.endDate}`;
    return 'Tutto il periodo';
  };

  return (
    <PageWrapper>
      <PageHeader
        title="Statistiche"
        subtitle={viewMode === 'vendite' ? "Analisi dettagliate delle vendite" : "Analisi dettagliate degli acquisti"}
      >
        <Button
          variant="outline"
          onClick={loadStatistiche}
          data-testid="refresh-stats"
        >
          <RefreshCw className={cn('w-4 h-4 mr-2', loading && 'animate-spin')} />
          Aggiorna
        </Button>
      </PageHeader>

      {/* Switch Vendite/Acquisti */}
      <div className="flex p-1.5 bg-slate-800/50 rounded-xl mb-6 max-w-md">
        <button
          onClick={() => setViewMode('vendite')}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all",
            viewMode === 'vendite' 
              ? "bg-emerald-500/20 text-emerald-400 shadow-sm border border-emerald-500/30" 
              : "text-slate-400 hover:text-slate-300 hover:bg-slate-700/50"
          )}
          data-testid="switch-vendite"
        >
          <Users className="w-4 h-4" />
          Vendite / Clienti
        </button>
        <button
          onClick={() => setViewMode('acquisti')}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all",
            viewMode === 'acquisti' 
              ? "bg-blue-500/20 text-blue-400 shadow-sm border border-blue-500/30" 
              : "text-slate-400 hover:text-slate-300 hover:bg-slate-700/50"
          )}
          data-testid="switch-acquisti"
        >
          <Truck className="w-4 h-4" />
          Acquisti / Fornitori
        </button>
      </div>

      {/* Filters FIRST - so user always sets period */}
      <div className="bg-muted p-4 rounded-lg mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium uppercase tracking-wider">Filtri</span>
          {hasActiveFilters && (
            <span className="ml-2 px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded-full">
              Attivi
            </span>
          )}
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          {/* Prodotto */}
          <div className="relative">
            <Input
              placeholder="Prodotto"
              value={filters.prodotto}
              onChange={(e) => setFilters({ ...filters, prodotto: e.target.value })}
              onFocus={() => setShowSuggestions({ ...showSuggestions, prodotto: true })}
              onBlur={() => setTimeout(() => setShowSuggestions({ ...showSuggestions, prodotto: false }), 200)}
              data-testid="filter-prodotto"
            />
            {showSuggestions.prodotto && filters.prodotto && (
              <div className="absolute top-full left-0 right-0 bg-card border border-border rounded-lg mt-1 max-h-48 overflow-auto z-10">
                {lists.prodotti
                  .filter(p => p.toLowerCase().includes(filters.prodotto.toLowerCase()))
                  .slice(0, 10)
                  .map((p, i) => (
                    <div
                      key={i}
                      className="px-3 py-2 hover:bg-muted cursor-pointer text-sm"
                      onClick={() => setFilters({ ...filters, prodotto: p })}
                    >
                      {p}
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* Cliente or Fornitore */}
          {viewMode === 'vendite' ? (
            <div className="relative">
              <Input
                placeholder="Cliente"
                value={filters.cliente}
                onChange={(e) => setFilters({ ...filters, cliente: e.target.value })}
                onFocus={() => setShowSuggestions({ ...showSuggestions, cliente: true })}
                onBlur={() => setTimeout(() => setShowSuggestions({ ...showSuggestions, cliente: false }), 200)}
                data-testid="filter-cliente"
              />
              {showSuggestions.cliente && filters.cliente && (
                <div className="absolute top-full left-0 right-0 bg-card border border-border rounded-lg mt-1 max-h-48 overflow-auto z-10">
                  {lists.clienti
                    .filter(c => c.toLowerCase().includes(filters.cliente.toLowerCase()))
                    .slice(0, 10)
                    .map((c, i) => (
                      <div
                        key={i}
                        className="px-3 py-2 hover:bg-muted cursor-pointer text-sm"
                        onClick={() => setFilters({ ...filters, cliente: c })}
                      >
                        {c}
                      </div>
                    ))}
                </div>
              )}
            </div>
          ) : (
            <div className="relative">
              <Input
                placeholder="Fornitore"
                value={filters.fornitore}
                onChange={(e) => setFilters({ ...filters, fornitore: e.target.value })}
                onFocus={() => setShowSuggestions({ ...showSuggestions, fornitore: true })}
                onBlur={() => setTimeout(() => setShowSuggestions({ ...showSuggestions, fornitore: false }), 200)}
                data-testid="filter-fornitore"
              />
              {showSuggestions.fornitore && filters.fornitore && (
                <div className="absolute top-full left-0 right-0 bg-card border border-border rounded-lg mt-1 max-h-48 overflow-auto z-10">
                  {(lists.fornitori || [])
                    .filter(f => f.toLowerCase().includes(filters.fornitore.toLowerCase()))
                    .slice(0, 10)
                    .map((f, i) => (
                      <div
                        key={i}
                        className="px-3 py-2 hover:bg-muted cursor-pointer text-sm"
                        onClick={() => setFilters({ ...filters, fornitore: f })}
                      >
                        {f}
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}

          <Input
            type="date"
            value={filters.startDate}
            onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
            data-testid="filter-start-date"
          />
          <Input
            type="date"
            value={filters.endDate}
            onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
            data-testid="filter-end-date"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => applyPreset('last30')}>
            <Calendar className="w-4 h-4 mr-2" />
            Ultimi 30 giorni
          </Button>
          <Button variant="outline" size="sm" onClick={() => applyPreset('currentMonth')}>
            Mese Corrente
          </Button>
          <Button variant="outline" size="sm" onClick={() => applyPreset('lastMonth')}>
            Mese Precedente
          </Button>
          <Button variant="outline" size="sm" onClick={() => applyPreset('last3Months')}>
            Ultimi 3 Mesi
          </Button>
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              Pulisci Filtri
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards - Period-specific, NO cumulative totals */}
      {viewMode === 'vendite' ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatCard
            label="Fatturato Periodo"
            value={data?.totaleEuro || 0}
            format="currency"
            icon={Euro}
            subtitle={hasActiveFilters ? getPeriodLabel() : null}
          />
          <StatCard
            label="Articoli Venduti"
            value={data?.totaleArticoli || 0}
            icon={Package}
          />
          <StatCard
            label="Clienti Attivi"
            value={data?.clientiAttivi || 0}
            icon={Users}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatCard
            label="Speso Periodo"
            value={dataAcquisti?.totaleEuro || 0}
            format="currency"
            icon={Euro}
            subtitle={hasActiveFilters ? getPeriodLabel() : null}
          />
          <StatCard
            label="Articoli Acquistati"
            value={dataAcquisti?.totaleArticoli || 0}
            icon={Package}
          />
          <StatCard
            label="Fornitori Attivi"
            value={dataAcquisti?.fornitoriAttivi || 0}
            icon={Truck}
          />
        </div>
      )}

      {/* Charts */}
      {viewMode === 'vendite' ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Monthly Sales Chart */}
          <div className="bg-card border border-border/50 p-6 rounded-xl">
            <h3 className="font-heading text-lg font-semibold uppercase mb-4">Andamento Vendite Mensili</h3>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                {(data?.venditeMensili || []).length > 1 ? (
                  <AreaChart data={data?.venditeMensili || []}>
                    <defs>
                      <linearGradient id="colorVendite" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
                    <XAxis dataKey="data" stroke="#71717A" fontSize={12} />
                    <YAxis stroke="#71717A" fontSize={12} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                    <Tooltip
                      contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', color: '#ffffff', borderRadius: '8px' }}
                      formatter={(value) => [formatCurrency(value), 'Vendite']}
                    />
                    <Area type="monotone" dataKey="totale" stroke="#3B82F6" fillOpacity={1} fill="url(#colorVendite)" />
                  </AreaChart>
                ) : (
                  <BarChart data={data?.venditeMensili || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
                    <XAxis dataKey="data" stroke="#71717A" fontSize={12} />
                    <YAxis stroke="#71717A" fontSize={12} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                    <Tooltip
                      contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', color: '#ffffff', borderRadius: '8px' }}
                      formatter={(value) => [formatCurrency(value), 'Vendite']}
                    />
                    <Bar dataKey="totale" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top Clienti Pie Chart */}
          <div className="bg-card border border-border/50 p-6 rounded-xl">
            <h3 className="font-heading text-lg font-semibold uppercase mb-4">Top Clienti</h3>
            <div className="h-[300px]">
              {(data?.topClienti || []).length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data?.topClienti || []}
                      cx="50%"
                      cy="50%"
                      outerRadius={110}
                      innerRadius={45}
                      dataKey="spesa"
                      nameKey="nome"
                      label={({ percent }) => percent > 0.03 ? `${(percent * 100).toFixed(0)}%` : ''}
                      labelLine={{ stroke: '#64748b', strokeWidth: 1 }}
                    >
                      {(data?.topClienti || []).map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', color: '#ffffff', borderRadius: '8px' }}
                      formatter={(value, name, props) => [formatCurrency(value), props.payload.nome]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500">Nessun dato disponibile</div>
              )}
            </div>
          </div>

          {/* Clienti Trend */}
          <div className="bg-card border border-border/50 p-6 rounded-xl">
            <h3 className="font-heading text-lg font-semibold uppercase mb-4">Trend Clienti Attivi (Ultimi 7 giorni)</h3>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={clientiTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
                  <XAxis dataKey="giorno" stroke="#71717A" fontSize={11} />
                  <YAxis stroke="#71717A" fontSize={12} />
                  <Tooltip
                    contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', color: '#ffffff', borderRadius: '8px' }}
                    formatter={(value) => [value, 'Clienti']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="clienti" 
                    stroke="#8B5CF6" 
                    strokeWidth={3}
                    dot={{ fill: '#8B5CF6', r: 5 }}
                    activeDot={{ r: 8, fill: '#8B5CF6' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top Prodotti */}
          <div className="bg-card border border-border/50 p-6 rounded-xl">
            <h3 className="font-heading text-lg font-semibold uppercase mb-4">Top Prodotti per Fatturato</h3>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.topProdotti || []} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
                  <XAxis type="number" stroke="#71717A" fontSize={12} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                  <YAxis 
                    type="category" 
                    dataKey="nome" 
                    stroke="#71717A" 
                    fontSize={11}
                    width={120}
                    tickFormatter={(v) => v?.length > 15 ? v.slice(0, 15) + '...' : v}
                  />
                  <Tooltip
                    contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', color: '#ffffff', borderRadius: '8px' }}
                    formatter={(value) => [formatCurrency(value), 'Fatturato']}
                  />
                  <Bar dataKey="totale_euro" fill="#10B981" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ) : (
        /* Acquisti Charts */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Monthly Purchases Chart */}
          <div className="bg-card border border-border/50 p-6 rounded-xl">
            <h3 className="font-heading text-lg font-semibold uppercase mb-4">Andamento Acquisti Mensili</h3>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                {(dataAcquisti?.acquistiMensili || []).length > 1 ? (
                  <AreaChart data={dataAcquisti?.acquistiMensili || []}>
                    <defs>
                      <linearGradient id="colorAcquisti" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
                    <XAxis dataKey="data" stroke="#71717A" fontSize={12} />
                    <YAxis stroke="#71717A" fontSize={12} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                    <Tooltip
                      contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', color: '#ffffff', borderRadius: '8px' }}
                      formatter={(value) => [formatCurrency(value), 'Acquisti']}
                    />
                    <Area type="monotone" dataKey="totale" stroke="#3B82F6" fillOpacity={1} fill="url(#colorAcquisti)" />
                  </AreaChart>
                ) : (
                  <BarChart data={dataAcquisti?.acquistiMensili || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
                    <XAxis dataKey="data" stroke="#71717A" fontSize={12} />
                    <YAxis stroke="#71717A" fontSize={12} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                    <Tooltip
                      contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', color: '#ffffff', borderRadius: '8px' }}
                      formatter={(value) => [formatCurrency(value), 'Acquisti']}
                    />
                    <Bar dataKey="totale" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top Fornitori Pie Chart */}
          <div className="bg-card border border-border/50 p-6 rounded-xl">
            <h3 className="font-heading text-lg font-semibold uppercase mb-4">Top Fornitori</h3>
            <div className="h-[300px]">
              {(dataAcquisti?.topFornitori || []).length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={dataAcquisti?.topFornitori || []}
                      cx="50%"
                      cy="50%"
                      outerRadius={110}
                      innerRadius={45}
                      dataKey="spesa"
                      nameKey="nome"
                      label={({ percent }) => percent > 0.03 ? `${(percent * 100).toFixed(0)}%` : ''}
                      labelLine={{ stroke: '#64748b', strokeWidth: 1 }}
                    >
                      {(dataAcquisti?.topFornitori || []).map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', color: '#ffffff', borderRadius: '8px' }}
                      formatter={(value, name, props) => [formatCurrency(value), props.payload.nome]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500">Nessun dato disponibile</div>
              )}
            </div>
          </div>

          {/* Fornitori Trend */}
          <div className="bg-card border border-border/50 p-6 rounded-xl">
            <h3 className="font-heading text-lg font-semibold uppercase mb-4">Trend Fornitori Attivi (Ultimi 7 giorni)</h3>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={fornitoriTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
                  <XAxis dataKey="giorno" stroke="#71717A" fontSize={11} />
                  <YAxis stroke="#71717A" fontSize={12} />
                  <Tooltip
                    contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', color: '#ffffff', borderRadius: '8px' }}
                    formatter={(value) => [value, 'Fornitori']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="fornitori" 
                    stroke="#3B82F6" 
                    strokeWidth={3}
                    dot={{ fill: '#3B82F6', r: 5 }}
                    activeDot={{ r: 8, fill: '#3B82F6' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top Prodotti Acquistati */}
          <div className="bg-card border border-border/50 p-6 rounded-xl">
            <h3 className="font-heading text-lg font-semibold uppercase mb-4">Top Prodotti Acquistati</h3>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dataAcquisti?.topProdotti || []} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
                  <XAxis type="number" stroke="#71717A" fontSize={12} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                  <YAxis 
                    type="category" 
                    dataKey="nome" 
                    stroke="#71717A" 
                    fontSize={11}
                    width={120}
                    tickFormatter={(v) => v?.length > 15 ? v.slice(0, 15) + '...' : v}
                  />
                  <Tooltip
                    contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', color: '#ffffff', borderRadius: '8px' }}
                    formatter={(value) => [formatCurrency(value), 'Speso']}
                  />
                  <Bar dataKey="totale_euro" fill="#3B82F6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </PageWrapper>
  );
}
