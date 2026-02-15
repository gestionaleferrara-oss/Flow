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
  Sector,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import {
  Euro,
  Package,
  Users,
  TrendingUp,
  TrendingDown,
  Filter,
  Calendar,
  RefreshCw
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import StatCard from '@/components/StatCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

export default function Statistiche() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    prodotto: '',
    cliente: '',
    startDate: '',
    endDate: ''
  });
  const [lists, setLists] = useState({ prodotti: [], clienti: [] });
  const [showSuggestions, setShowSuggestions] = useState({ prodotto: false, cliente: false });
  const [activePieIndex, setActivePieIndex] = useState(-1);

  useEffect(() => {
    loadLists();
    loadStatistiche();
  }, []);

  const loadLists = async () => {
    try {
      const response = await axios.get(`${API}/statistiche/lists`);
      setLists(response.data);
    } catch (error) {
      console.error('Error loading lists:', error);
    }
  };

  const loadStatistiche = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.prodotto) params.append('prodotto', filters.prodotto);
      if (filters.cliente) params.append('cliente', filters.cliente);
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      
      const response = await axios.get(`${API}/statistiche?${params}`);
      setData(response.data);
    } catch (error) {
      console.error('Error loading statistiche:', error);
    } finally {
      setLoading(false);
    }
  };

  const applyPreset = (preset) => {
    const now = new Date();
    let startDate, endDate;

    switch (preset) {
      case 'last30':
        startDate = new Date(now.setDate(now.getDate() - 30));
        endDate = new Date();
        break;
      case 'currentMonth':
        startDate = new Date(now.getFullYear(), now.getMonth(), 1);
        endDate = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        break;
      case 'lastMonth':
        startDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        endDate = new Date(now.getFullYear(), now.getMonth(), 0);
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
    setFilters({ prodotto: '', cliente: '', startDate: '', endDate: '' });
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      loadStatistiche();
    }, 500);
    return () => clearTimeout(timer);
  }, [filters]);

  if (loading && !data) return <LoadingSpinner fullScreen />;

  return (
    <PageWrapper>
      <PageHeader
        title="Statistiche"
        subtitle="Analisi dettagliate delle vendite"
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

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          label="Totale Vendite"
          value={data?.totaleEuro || 0}
          format="currency"
          icon={Euro}
        />
        <StatCard
          label="Fatturato Mese"
          value={data?.fatturatoMese || 0}
          format="currency"
          icon={Euro}
          trend={data?.diffPercentuale > 0 ? 'up' : data?.diffPercentuale < 0 ? 'down' : 'neutral'}
          trendValue={data?.diffPercentuale}
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

      {/* Filters */}
      <div className="bg-muted p-4 rounded-sm mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium uppercase tracking-wider">Filtri</span>
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
              <div className="absolute top-full left-0 right-0 bg-card border border-border rounded-sm mt-1 max-h-48 overflow-auto z-10">
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

          {/* Cliente */}
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
              <div className="absolute top-full left-0 right-0 bg-card border border-border rounded-sm mt-1 max-h-48 overflow-auto z-10">
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

          {/* Date Range */}
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

        {/* Preset Buttons */}
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
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Pulisci Filtri
          </Button>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monthly Sales Chart */}
        <div className="bg-card border border-border/50 p-6 rounded-sm">
          <h3 className="font-heading text-lg font-semibold uppercase mb-4">Andamento Vendite Mensili</h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
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
                  contentStyle={{ background: '#0A0A0A', border: '1px solid #27272A' }}
                  formatter={(value) => [formatCurrency(value), 'Vendite']}
                />
                <Area
                  type="monotone"
                  dataKey="totale"
                  stroke="#3B82F6"
                  fillOpacity={1}
                  fill="url(#colorVendite)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Clienti Chart */}
        <div className="bg-card border border-border/50 p-6 rounded-sm">
          <h3 className="font-heading text-lg font-semibold uppercase mb-4">Top Clienti</h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data?.topClienti || []}
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  dataKey="spesa"
                  nameKey="nome"
                  label={({ cx, cy, midAngle, innerRadius, outerRadius, nome, percent }) => {
                    const RADIAN = Math.PI / 180;
                    const radius = outerRadius + 20;
                    const x = cx + radius * Math.cos(-midAngle * RADIAN);
                    const y = cy + radius * Math.sin(-midAngle * RADIAN);
                    return (
                      <text x={x} y={y} fill="#e2e8f0" fontSize={12} fontWeight={500}
                        textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central">
                        {`${nome?.slice(0,12)} (${(percent*100).toFixed(0)}%)`}
                      </text>
                    );
                  }}
                  labelLine={false}
                  activeShape={({ cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill, nome, spesa }) => {
                    return (
                      <g>
                        <text x={cx} y={cy - 10} textAnchor="middle" fill="#f1f5f9" fontSize={14} fontWeight={600}>
                          {nome?.slice(0, 18)}
                        </text>
                        <text x={cx} y={cy + 12} textAnchor="middle" fill="#94a3b8" fontSize={12}>
                          {formatCurrency(spesa)}
                        </text>
                        <Sector cx={cx} cy={cy} innerRadius={innerRadius} outerRadius={outerRadius + 6}
                          startAngle={startAngle} endAngle={endAngle} fill={fill} />
                      </g>
                    );
                  }}
                  activeIndex={activePieIndex}
                  onMouseEnter={(_, index) => setActivePieIndex(index)}
                  onMouseLeave={() => setActivePieIndex(-1)}
                >
                  {(data?.topClienti || []).map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#0A0A0A', border: '1px solid #27272A' }}
                  formatter={(value) => formatCurrency(value)}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Prodotti Chart - by Euro */}
        <div className="bg-card border border-border/50 p-6 rounded-sm lg:col-span-2">
          <h3 className="font-heading text-lg font-semibold uppercase mb-4">Top Prodotti per Fatturato</h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.topProdotti || []} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
                <XAxis type="number" stroke="#71717A" fontSize={12} tickFormatter={(v) => `€${(v/1000).toFixed(0)}k`} />
                <YAxis 
                  type="category" 
                  dataKey="nome" 
                  stroke="#71717A" 
                  fontSize={12}
                  width={150}
                  tickFormatter={(v) => v?.length > 20 ? v.slice(0, 20) + '...' : v}
                />
                <Tooltip
                  contentStyle={{ background: '#0A0A0A', border: '1px solid #27272A' }}
                  formatter={(value) => [formatCurrency(value), 'Fatturato']}
                />
                <Bar dataKey="totale_euro" fill="#10B981" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
