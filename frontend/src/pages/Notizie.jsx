import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RefreshCw, ExternalLink, Wind, Thermometer,
  MapPin, Clock, ArrowUpRight, FileText, CloudSun,
  TrendingUp, TrendingDown, Minus, Search as SearchIcon
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import LoadingSpinner from '@/components/LoadingSpinner';
import { cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const weatherMeta = {
  0: { label: 'Sereno', icon: '☀️', bg: 'from-amber-500/15 to-orange-500/5' },
  1: { label: 'Prev. sereno', icon: '🌤️', bg: 'from-amber-500/10 to-sky-500/5' },
  2: { label: 'Parz. nuvoloso', icon: '⛅', bg: 'from-sky-500/10 to-slate-500/5' },
  3: { label: 'Nuvoloso', icon: '☁️', bg: 'from-slate-500/15 to-gray-500/5' },
  45: { label: 'Nebbia', icon: '🌫️', bg: 'from-gray-400/15 to-slate-500/5' },
  48: { label: 'Nebbia', icon: '🌫️', bg: 'from-cyan-400/15 to-gray-500/5' },
  51: { label: 'Pioggerella', icon: '🌦️', bg: 'from-blue-400/15 to-sky-500/5' },
  53: { label: 'Pioggerella', icon: '🌦️', bg: 'from-blue-400/15 to-sky-500/5' },
  55: { label: 'Pioggia', icon: '🌧️', bg: 'from-blue-500/20 to-indigo-500/5' },
  61: { label: 'Pioggia', icon: '🌧️', bg: 'from-blue-500/15 to-sky-600/5' },
  63: { label: 'Pioggia', icon: '🌧️', bg: 'from-blue-600/20 to-indigo-500/5' },
  65: { label: 'Pioggia forte', icon: '🌧️', bg: 'from-indigo-500/20 to-slate-700/5' },
  71: { label: 'Neve', icon: '🌨️', bg: 'from-cyan-300/15 to-blue-200/5' },
  73: { label: 'Neve', icon: '🌨️', bg: 'from-cyan-300/20 to-blue-200/5' },
  75: { label: 'Neve forte', icon: '❄️', bg: 'from-cyan-200/20 to-white/5' },
  80: { label: 'Rovescio', icon: '⛈️', bg: 'from-indigo-500/20 to-purple-500/5' },
  81: { label: 'Rovescio', icon: '⛈️', bg: 'from-indigo-600/20 to-purple-600/5' },
  82: { label: 'Rovescio', icon: '⛈️', bg: 'from-purple-600/20 to-slate-800/5' },
  95: { label: 'Temporale', icon: '🌩️', bg: 'from-purple-500/20 to-indigo-600/5' },
};
const getW = (code) => weatherMeta[code] || { label: '?', icon: '❓', bg: 'from-slate-500/15 to-slate-600/5' };

const fallbackImg = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 250'%3E%3Crect width='100%25' height='100%25' fill='%23111827'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='13' fill='%23475569'%3EImmagine non disponibile%3C/text%3E%3C/svg%3E";

// Mini sparkline SVG
function Sparkline({ data, color }) {
  if (!data || data.length < 2) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 80, h = 28;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(' ');
  return (
    <svg width={w} height={h} className="shrink-0">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Notizie() {
  const [notizie, setNotizie] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [meteo, setMeteo] = useState(null);
  const [prezziMercati, setPrezziMercati] = useState([]);
  const [trends, setTrends] = useState([]);
  const [trendsLoading, setTrendsLoading] = useState(true);
  const [categorie, setCategorie] = useState([]);
  const [selectedCategoria, setSelectedCategoria] = useState('all');

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [notizieRes, meteoRes, prezziRes] = await Promise.all([
        axios.get(`${API}/notizie`),
        axios.get(`${API}/meteo`),
        axios.get(`${API}/prezzi-mercati`)
      ]);
      setNotizie(notizieRes.data);
      setMeteo(meteoRes.data);
      setPrezziMercati(prezziRes.data);
      setCategorie([...new Set(notizieRes.data.map(n => n.categoria))]);
    } catch (e) { console.error(e); } finally { setLoading(false); }

    // Load trends separately (slower)
    try {
      const trendsRes = await axios.get(`${API}/trends-frutta-secca`);
      setTrends(trendsRes.data);
    } catch (e) { console.error(e); } finally { setTrendsLoading(false); }
  };

  const refreshNews = async () => {
    setRefreshing(true);
    try {
      await axios.post(`${API}/notizie/refresh`);
      setTimeout(async () => {
        const response = await axios.get(`${API}/notizie`);
        setNotizie(response.data);
        setRefreshing(false);
      }, 3000);
    } catch (e) { setRefreshing(false); }
  };

  const filtered = selectedCategoria === 'all' ? notizie : notizie.filter(n => n.categoria === selectedCategoria);
  const heroArticle = filtered[0];
  const restArticles = filtered.slice(1);

  if (loading) return <LoadingSpinner fullScreen />;

  const cw = meteo?.current_weather;
  const daily = meteo?.daily;
  const w = cw ? getW(cw.weathercode) : null;

  return (
    <PageWrapper>
      <PageHeader title="Notizie & Mercati" subtitle="Il polso del settore ortofrutticolo">
        <Button onClick={refreshNews} disabled={refreshing} data-testid="refresh-news-btn"
          className="bg-white/10 border border-white/20 hover:bg-white/20 text-white hover:text-white">
          <RefreshCw className={cn('w-4 h-4 mr-2', refreshing && 'animate-spin')} />
          {refreshing ? 'Aggiornamento...' : 'Aggiorna'}
        </Button>
      </PageHeader>

      {/* === TOP: 3 widget in riga === */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8 items-start">

        {/* 1. METEO + TICKER */}
        <div className="flex flex-col gap-4">
          {cw && w && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-2xl overflow-hidden border border-white/[0.08] p-5 relative"
              style={{ background: 'linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01))', backdropFilter: 'blur(20px)' }}
              data-testid="weather-widget"
            >
              <div className={cn('absolute inset-0 rounded-2xl bg-gradient-to-br opacity-40', w.bg)} />
              <div className="relative z-10">
                <div className="flex items-center gap-1.5 mb-2">
                  <MapPin className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="text-xs font-medium text-slate-400">Bologna</span>
                  <span className="text-[10px] text-slate-600 ml-auto">
                    {new Date().toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' })}
                  </span>
                </div>

                <div className="flex items-center gap-3 mb-3">
                  <span className="text-4xl">{w.icon}</span>
                  <div>
                    <p className="text-3xl font-extrabold tracking-tight text-white leading-none">{Math.round(cw.temperature)}°</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">{w.label}</p>
                  </div>
                  <div className="ml-auto flex flex-col gap-0.5 text-[11px] text-slate-500">
                    <div className="flex items-center gap-1.5"><Wind className="w-3 h-3 text-sky-400" />{Math.round(cw.windspeed)} km/h</div>
                    {daily && <>
                      <div className="flex items-center gap-1.5"><Thermometer className="w-3 h-3 text-red-400" />Max {Math.round(daily.temperature_2m_max[0])}°</div>
                      <div className="flex items-center gap-1.5"><Thermometer className="w-3 h-3 text-blue-400" />Min {Math.round(daily.temperature_2m_min[0])}°</div>
                    </>}
                  </div>
                </div>

                {daily && (
                  <div className="grid grid-cols-6 gap-1">
                    {daily.time.slice(1, 7).map((date, idx) => {
                      const dw = getW(daily.weathercode[idx + 1]);
                      return (
                        <div key={date} className="flex flex-col items-center py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.05]">
                          <p className="text-[8px] uppercase font-semibold text-slate-600 tracking-wider">
                            {new Date(date).toLocaleDateString('it-IT', { weekday: 'short' })}
                          </p>
                          <span className="text-base my-0.5">{dw.icon}</span>
                          <div className="flex gap-0.5 text-[9px]">
                            <span className="font-semibold text-white">{Math.round(daily.temperature_2m_max[idx + 1])}°</span>
                            <span className="text-slate-500">{Math.round(daily.temperature_2m_min[idx + 1])}°</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* TICKER NOTIZIE FLASH */}
          {notizie.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="rounded-xl overflow-hidden border border-white/[0.08] relative"
              style={{ background: 'linear-gradient(145deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))' }}
              data-testid="news-ticker"
            >
              <div className="flex items-center gap-2 px-3 py-2">
                <span className="shrink-0 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider bg-red-500/20 text-red-400 rounded border border-red-500/20 animate-pulse">
                  Live
                </span>
                <div className="overflow-hidden flex-1 relative">
                  <div className="absolute left-0 top-0 bottom-0 w-6 bg-gradient-to-r from-[#0d1117] to-transparent z-10" />
                  <div className="absolute right-0 top-0 bottom-0 w-6 bg-gradient-to-l from-[#0d1117] to-transparent z-10" />
                  <div className="ticker-scroll flex items-center gap-6 whitespace-nowrap">
                    {notizie.slice(0, 10).map((n, i) => (
                      <a key={i} href={n.url} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-[11px] text-slate-400 hover:text-cyan-400 transition-colors shrink-0">
                        <span className="w-1 h-1 rounded-full bg-cyan-500/60 shrink-0" />
                        <span className="font-medium">{n.titolo}</span>
                      </a>
                    ))}
                    {/* Duplicato per loop continuo */}
                    {notizie.slice(0, 10).map((n, i) => (
                      <a key={`dup-${i}`} href={n.url} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-[11px] text-slate-400 hover:text-cyan-400 transition-colors shrink-0">
                        <span className="w-1 h-1 rounded-full bg-cyan-500/60 shrink-0" />
                        <span className="font-medium">{n.titolo}</span>
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </div>

        {/* 2. LISTINI MERCATO */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08 }}
          className="rounded-2xl overflow-hidden border border-white/[0.08] p-5"
          style={{ background: 'linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01))', backdropFilter: 'blur(20px)' }}
          data-testid="prices-widget"
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="w-7 h-7 rounded-lg bg-emerald-500/15 flex items-center justify-center">
              <FileText className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-white">Listini Mercato</h3>
              <p className="text-[10px] text-slate-500">Prezzi ingrosso</p>
            </div>
          </div>
          <div className="space-y-1.5">
            {prezziMercati.map((m, idx) => (
              <motion.a key={m.nome} href={m.url} target="_blank" rel="noopener noreferrer"
                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.12 + idx * 0.03 }}
                className="flex items-center justify-between px-3 py-2 rounded-lg group
                  bg-white/[0.03] border border-white/[0.04] hover:bg-emerald-500/[0.06] hover:border-emerald-500/15 transition-all duration-300">
                <div className="flex items-center gap-2">
                  <MapPin className="w-3 h-3 text-slate-600 group-hover:text-emerald-400 transition-colors" />
                  <span className="text-xs text-slate-400 group-hover:text-slate-200 transition-colors font-medium">{m.nome}</span>
                </div>
                <ArrowUpRight className="w-3 h-3 text-slate-600 group-hover:text-emerald-400 transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </motion.a>
            ))}
          </div>
        </motion.div>

        {/* 3. TRENDS FRUTTA SECCA */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.16 }}
          className="rounded-2xl overflow-hidden border border-white/[0.08] p-5"
          style={{ background: 'linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01))', backdropFilter: 'blur(20px)' }}
          data-testid="trends-widget"
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="w-7 h-7 rounded-lg bg-violet-500/15 flex items-center justify-center">
              <SearchIcon className="w-3.5 h-3.5 text-violet-400" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-white">Trend Frutta Secca</h3>
              <p className="text-[10px] text-slate-500">Google Trends Italia — ultimi 3 mesi</p>
            </div>
          </div>

          {trendsLoading ? (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="w-5 h-5 text-slate-600 animate-spin" />
            </div>
          ) : trends.length > 0 ? (
            <div className="space-y-2">
              {trends.map((t, idx) => (
                <motion.div key={t.keyword}
                  initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 + idx * 0.04 }}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.04]
                    hover:bg-white/[0.06] transition-all duration-300"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-200">{t.keyword}</span>
                      <span className={cn(
                        'flex items-center gap-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded-md',
                        t.trend === 'up' && 'text-emerald-400 bg-emerald-500/10',
                        t.trend === 'down' && 'text-red-400 bg-red-500/10',
                        t.trend === 'stable' && 'text-slate-400 bg-slate-500/10'
                      )}>
                        {t.trend === 'up' && <TrendingUp className="w-2.5 h-2.5" />}
                        {t.trend === 'down' && <TrendingDown className="w-2.5 h-2.5" />}
                        {t.trend === 'stable' && <Minus className="w-2.5 h-2.5" />}
                        {t.change_pct > 0 ? '+' : ''}{t.change_pct}%
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-600 mt-0.5">Interesse: {t.current_interest}/100</p>
                  </div>
                  <Sparkline
                    data={t.sparkline}
                    color={t.trend === 'up' ? '#34d399' : t.trend === 'down' ? '#f87171' : '#94a3b8'}
                  />
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-32 text-xs text-slate-500">Dati non disponibili</div>
          )}
        </motion.div>
      </div>

      {/* === CATEGORY FILTERS === */}
      <div className="flex flex-wrap items-center gap-2 mb-6" data-testid="category-filters">
        <button onClick={() => setSelectedCategoria('all')}
          className={cn('px-4 py-2 rounded-full text-xs font-semibold uppercase tracking-wider transition-all duration-300',
            selectedCategoria === 'all'
              ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/25 shadow-sm shadow-cyan-500/10'
              : 'bg-white/[0.04] text-slate-500 border border-white/[0.06] hover:bg-white/[0.08] hover:text-slate-300')}>
          Tutte ({notizie.length})
        </button>
        {categorie.map(cat => (
          <button key={cat} onClick={() => setSelectedCategoria(cat)}
            className={cn('px-4 py-2 rounded-full text-xs font-semibold uppercase tracking-wider transition-all duration-300 capitalize',
              selectedCategoria === cat
                ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/25 shadow-sm shadow-cyan-500/10'
                : 'bg-white/[0.04] text-slate-500 border border-white/[0.06] hover:bg-white/[0.08] hover:text-slate-300')}>
            {cat}
          </button>
        ))}
      </div>

      {/* === HERO ARTICLE === */}
      {heroArticle && (
        <motion.article initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="relative mb-8 rounded-2xl overflow-hidden cursor-pointer group border border-white/[0.08]"
          onClick={() => heroArticle.url && window.open(heroArticle.url, '_blank')}
          data-testid="hero-news-card">
          <div className="grid grid-cols-1 lg:grid-cols-2">
            <div className="relative h-[220px] lg:h-auto overflow-hidden">
              <img src={heroArticle.immagine_url || fallbackImg} alt={heroArticle.titolo}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                onError={(e) => { e.target.src = fallbackImg; }} />
            </div>
            <div className="p-6 lg:p-8 flex flex-col justify-center"
              style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))' }}>
              <div className="flex items-center gap-2 mb-3">
                <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider bg-cyan-500/15 text-cyan-400 rounded-lg border border-cyan-500/20">
                  {heroArticle.fonte}
                </span>
                {heroArticle.data_pubblicazione && (
                  <span className="flex items-center gap-1 text-[11px] text-slate-500">
                    <Clock className="w-3 h-3" />
                    {new Date(heroArticle.data_pubblicazione).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })}
                  </span>
                )}
              </div>
              <h2 className="text-xl lg:text-2xl font-bold text-white mb-3 leading-snug line-clamp-3 group-hover:text-cyan-300 transition-colors duration-300">
                {heroArticle.titolo}
              </h2>
              <p className="text-sm text-slate-400 leading-relaxed line-clamp-3 mb-4">
                {heroArticle.descrizione || heroArticle.contenuto}
              </p>
              <div className="flex items-center gap-2 text-cyan-400 text-sm font-medium group-hover:gap-3 transition-all duration-300">
                <span>Leggi articolo</span>
                <ArrowUpRight className="w-4 h-4" />
              </div>
            </div>
          </div>
        </motion.article>
      )}

      {/* === NEWS GRID === */}
      {restArticles.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <AnimatePresence mode="popLayout">
            {restArticles.map((notizia, index) => (
              <motion.article key={notizia.id || index} layout
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: index * 0.04, duration: 0.4 }}
                className="group rounded-2xl overflow-hidden cursor-pointer border border-white/[0.06]
                  hover:border-white/[0.15] transition-all duration-500 hover:-translate-y-1"
                style={{ background: 'linear-gradient(145deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))' }}
                onClick={() => notizia.url && window.open(notizia.url, '_blank')}
                data-testid="news-card">
                <div className="relative h-[170px] overflow-hidden">
                  <img src={notizia.immagine_url || fallbackImg} alt={notizia.titolo}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                    onError={(e) => { e.target.src = fallbackImg; }} />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                  <span className="absolute top-3 left-3 px-2 py-1 text-[9px] font-bold uppercase tracking-wider
                    bg-black/50 backdrop-blur-md text-white/90 rounded-lg border border-white/10">{notizia.fonte}</span>
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-sm text-slate-200 mb-2 line-clamp-2 leading-snug group-hover:text-white transition-colors">
                    {notizia.titolo}
                  </h3>
                  <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed mb-3">
                    {notizia.descrizione || notizia.contenuto}
                  </p>
                  <div className="flex items-center justify-between pt-3 border-t border-white/[0.05]">
                    <span className="text-[10px] text-slate-600 capitalize font-medium">{notizia.categoria}</span>
                    {notizia.data_pubblicazione && (
                      <span className="text-[10px] text-slate-600">
                        {new Date(notizia.data_pubblicazione).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })}
                      </span>
                    )}
                  </div>
                </div>
              </motion.article>
            ))}
          </AnimatePresence>
        </div>
      ) : filtered.length === 0 && (
        <div className="text-center py-16 rounded-2xl border border-dashed border-white/10 bg-white/[0.02]">
          <CloudSun className="w-12 h-12 mx-auto text-slate-600 mb-3" />
          <p className="text-slate-400 font-medium">Nessuna notizia disponibile</p>
          <p className="text-sm text-slate-600 mt-1">Clicca su "Aggiorna" per caricare le ultime notizie</p>
        </div>
      )}
    </PageWrapper>
  );
}
