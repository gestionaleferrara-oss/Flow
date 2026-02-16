import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { 
  Sparkles, Search, Calendar, TrendingUp, Package, Users, 
  RefreshCw, RotateCcw, FileDown, Target, Lightbulb
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Forecast() {
  const [tipo, setTipo] = useState('prodotto'); // 'prodotto' or 'cliente'
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [meseTarget, setMeseTarget] = useState('');
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);

  // Set default target month to next month
  useEffect(() => {
    const now = new Date();
    const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    const formatted = `${nextMonth.getFullYear()}-${String(nextMonth.getMonth() + 1).padStart(2, '0')}`;
    setMeseTarget(formatted);
  }, []);

  // Reset everything
  const handleReset = () => {
    setSelectedEntity(null);
    setForecast(null);
    setError(null);
    setSearch('');
    setSearchResults([]);
    // Reset to next month
    const now = new Date();
    const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    setMeseTarget(`${nextMonth.getFullYear()}-${String(nextMonth.getMonth() + 1).padStart(2, '0')}`);
  };

  // Export PDF
  const handleExportPdf = async () => {
    if (!forecast) return;
    setExporting(true);
    try {
      const response = await axios.post(`${API}/forecast/export-pdf`, forecast, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `forecast_${forecast.nome.replace(/\s+/g, '_')}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Export error:', e);
    } finally {
      setExporting(false);
    }
  };

  // Search for products or clients
  const searchEntities = useCallback(async (query) => {
    if (!query || query.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    setSearchLoading(true);
    try {
      const endpoint = tipo === 'prodotto' ? 'forecast/prodotti' : 'forecast/clienti';
      const response = await axios.get(`${API}/${endpoint}`, { params: { search: query } });
      setSearchResults(response.data);
    } catch (e) {
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }, [tipo]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      searchEntities(search);
    }, 200);
    return () => clearTimeout(timer);
  }, [search, searchEntities]);

  // Reset when changing type
  useEffect(() => {
    setSearch('');
    setSearchResults([]);
    setSelectedEntity(null);
    setForecast(null);
    setError(null);
  }, [tipo]);

  const selectEntity = (entity) => {
    setSelectedEntity(entity);
    setSearch('');
    setSearchResults([]);
    setForecast(null);
    setError(null);
  };

  const generateForecast = async () => {
    if (!selectedEntity || !meseTarget) return;
    
    setLoading(true);
    setError(null);
    setForecast(null);
    
    try {
      const response = await axios.get(`${API}/forecast/generate`, {
        params: {
          tipo,
          nome: selectedEntity.nome,
          mese_target: meseTarget
        }
      });
      
      if (response.data.success) {
        setForecast(response.data);
      } else {
        setError(response.data.error || 'Errore nella generazione della previsione');
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Errore nella generazione della previsione');
    } finally {
      setLoading(false);
    }
  };

  const getMeseLabel = (meseStr) => {
    if (!meseStr) return '';
    const mesi = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic'];
    const [year, month] = meseStr.split('-');
    return `${mesi[parseInt(month) - 1]} ${year.slice(2)}`;
  };

  return (
    <PageWrapper>
      <PageHeader 
        title="Forecast AI" 
        subtitle="Previsioni vendite con intelligenza artificiale"
      />

      {/* Selection Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Step 1: Select Type */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold flex items-center justify-center">1</div>
            <span className="text-sm font-medium text-white">Seleziona Tipo</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setTipo('prodotto')}
              data-testid="tipo-prodotto"
              className={cn(
                "flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                tipo === 'prodotto' 
                  ? "bg-blue-500/20 text-blue-400 border border-blue-500/30" 
                  : "bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:bg-white/[0.06]"
              )}
            >
              <Package className="w-4 h-4" />
              Prodotto
            </button>
            <button
              onClick={() => setTipo('cliente')}
              data-testid="tipo-cliente"
              className={cn(
                "flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                tipo === 'cliente' 
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30" 
                  : "bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:bg-white/[0.06]"
              )}
            >
              <Users className="w-4 h-4" />
              Cliente
            </button>
          </div>
        </motion.div>

        {/* Step 2: Search & Select */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="w-6 h-6 rounded-full bg-purple-500/20 text-purple-400 text-xs font-bold flex items-center justify-center">2</div>
            <span className="text-sm font-medium text-white">
              {selectedEntity ? `Selezionato: ${selectedEntity.nome}` : `Cerca ${tipo === 'prodotto' ? 'Prodotto' : 'Cliente'}`}
            </span>
          </div>
          
          {selectedEntity ? (
            <div className="flex items-center gap-2">
              <div className={cn(
                "flex-1 px-3 py-2 rounded-lg text-sm",
                tipo === 'prodotto' ? "bg-blue-500/10 text-blue-300 border border-blue-500/20" : "bg-cyan-500/10 text-cyan-300 border border-cyan-500/20"
              )}>
                {selectedEntity.nome}
              </div>
              <button 
                onClick={() => { setSelectedEntity(null); setForecast(null); }}
                className="px-2 py-2 rounded-lg bg-white/[0.05] text-slate-400 hover:text-white hover:bg-white/[0.1] transition-all"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input
                placeholder={`Cerca ${tipo === 'prodotto' ? 'prodotto' : 'cliente'}...`}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
                data-testid="search-entity"
              />
              {/* Dropdown results */}
              {(searchResults.length > 0 || searchLoading) && (
                <div className="absolute top-full left-0 right-0 mt-1 max-h-48 overflow-auto rounded-lg border border-white/[0.08] bg-slate-900/95 backdrop-blur-lg z-20">
                  {searchLoading ? (
                    <div className="p-3 text-center">
                      <RefreshCw className="w-4 h-4 animate-spin mx-auto text-slate-500" />
                    </div>
                  ) : (
                    searchResults.map((item) => (
                      <button
                        key={item.nome}
                        onClick={() => selectEntity(item)}
                        className="w-full text-left px-3 py-2 hover:bg-white/[0.05] transition-colors border-b border-white/[0.04] last:border-b-0"
                      >
                        <p className="text-sm text-white truncate">{item.nome}</p>
                        {item.fatturato_storico && (
                          <p className="text-xs text-slate-500">Storico: {formatCurrency(item.fatturato_storico)}</p>
                        )}
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          )}
        </motion.div>

        {/* Step 3: Select Month & Generate */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold flex items-center justify-center">3</div>
            <span className="text-sm font-medium text-white">Mese Target</span>
          </div>
          <div className="flex gap-2">
            <input
              type="month"
              value={meseTarget}
              onChange={(e) => setMeseTarget(e.target.value)}
              className="flex-1 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-emerald-500/50"
              data-testid="mese-target"
            />
            <Button 
              onClick={generateForecast}
              disabled={!selectedEntity || !meseTarget || loading}
              className="gap-2"
              data-testid="generate-forecast"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              Genera
            </Button>
          </div>
        </motion.div>
      </div>

      {/* Error Display */}
      {error && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
        >
          {error}
        </motion.div>
      )}

      {/* Loading State */}
      {loading && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center justify-center py-16"
        >
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500/20 to-blue-500/20 flex items-center justify-center mb-4">
            <Sparkles className="w-8 h-8 text-purple-400 animate-pulse" />
          </div>
          <p className="text-white font-medium mb-1">Generazione in corso...</p>
          <p className="text-sm text-slate-500">L'AI sta analizzando i dati storici</p>
        </motion.div>
      )}

      {/* Forecast Results */}
      {forecast && !loading && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {/* Header with actions */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className={cn(
                "p-2 rounded-lg",
                tipo === 'prodotto' ? "bg-blue-500/15 text-blue-400" : "bg-cyan-500/15 text-cyan-400"
              )}>
                {tipo === 'prodotto' ? <Package className="w-5 h-5" /> : <Users className="w-5 h-5" />}
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">{forecast.nome}</h2>
                <p className="text-xs text-slate-500">
                  Previsione per <span className="text-emerald-400 font-medium">{forecast.mese_target_nome}</span>
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportPdf}
                disabled={exporting}
                className="gap-2"
                data-testid="export-pdf"
              >
                {exporting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />}
                PDF
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleReset}
                className="gap-2"
                data-testid="reset-forecast"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Historical Chart */}
            <div className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-4">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-4 h-4 text-violet-400" />
                <span className="text-sm font-medium text-white">Storico Vendite</span>
              </div>
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={forecast.storico}>
                    <defs>
                      <linearGradient id="colorFatturato" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis 
                      dataKey="mese" 
                      tick={{ fontSize: 10, fill: '#64748b' }} 
                      tickFormatter={getMeseLabel}
                    />
                    <YAxis 
                      tick={{ fontSize: 10, fill: '#64748b' }} 
                      tickFormatter={(v) => `€${(v/1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                      labelFormatter={getMeseLabel}
                      formatter={(v) => [formatCurrency(v), 'Fatturato']}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="fatturato" 
                      stroke="#8b5cf6" 
                      strokeWidth={2}
                      fill="url(#colorFatturato)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2">
                <div className="p-2 rounded-lg bg-white/[0.03] text-center">
                  <p className="text-[10px] text-slate-500">Totale Periodo</p>
                  <p className="text-sm font-semibold text-white">{formatCurrency(forecast.statistiche.totale_periodo)}</p>
                </div>
                <div className="p-2 rounded-lg bg-white/[0.03] text-center">
                  <p className="text-[10px] text-slate-500">Media Mensile</p>
                  <p className="text-sm font-semibold text-violet-400">{formatCurrency(forecast.statistiche.media_mensile)}</p>
                </div>
                <div className="p-2 rounded-lg bg-white/[0.03] text-center">
                  <p className="text-[10px] text-slate-500">Mesi Dati</p>
                  <p className="text-sm font-semibold text-white">{forecast.statistiche.num_mesi_dati}</p>
                </div>
              </div>
            </div>

            {/* AI Forecast */}
            <div className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-4">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <span className="text-sm font-medium text-white">Previsione AI</span>
                <span className="ml-auto text-[10px] text-slate-500">{forecast.mese_target_nome}</span>
              </div>
              <div className="prose prose-invert prose-sm max-w-none text-slate-300 overflow-auto max-h-[350px]">
                <ReactMarkdown
                  components={{
                    h1: ({ children }) => <h3 className="text-base font-semibold text-white mt-3 mb-2">{children}</h3>,
                    h2: ({ children }) => <h4 className="text-sm font-semibold text-white mt-3 mb-1.5">{children}</h4>,
                    h3: ({ children }) => <h5 className="text-sm font-medium text-slate-200 mt-2 mb-1">{children}</h5>,
                    p: ({ children }) => <p className="text-sm text-slate-400 mb-2 leading-relaxed">{children}</p>,
                    strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
                    ul: ({ children }) => <ul className="list-disc list-inside space-y-1 my-2">{children}</ul>,
                    li: ({ children }) => <li className="text-sm text-slate-400">{children}</li>,
                  }}
                >
                  {forecast.previsione_ai}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Empty State */}
      {!forecast && !loading && !error && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center justify-center py-16 text-center"
        >
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-500/10 to-blue-500/10 flex items-center justify-center mb-4">
            <Target className="w-10 h-10 text-purple-400/50" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">Previsioni Intelligenti</h3>
          <p className="text-sm text-slate-500 max-w-md">
            Seleziona un prodotto o cliente e un mese target per generare una previsione 
            di vendita basata sull'analisi AI dei dati storici.
          </p>
          <div className="flex items-center gap-4 mt-6 text-xs text-slate-600">
            <div className="flex items-center gap-1.5">
              <Package className="w-3.5 h-3.5" />
              <span>Analisi per prodotto</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5" />
              <span>Analisi per cliente</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Lightbulb className="w-3.5 h-3.5" />
              <span>Suggerimenti AI</span>
            </div>
          </div>
        </motion.div>
      )}
    </PageWrapper>
  );
}
