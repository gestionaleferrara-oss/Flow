import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, ExternalLink, Wind, Thermometer, MapPin, Clock, ArrowUpRight, FileText, CloudSun } from 'lucide-react';
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
  51: { label: 'Pioggerella', icon: '🌦️', bg: 'from-blue-400/15 to-sky-500/5' },
  61: { label: 'Pioggia', icon: '🌧️', bg: 'from-blue-500/15 to-sky-600/5' },
  71: { label: 'Neve', icon: '🌨️', bg: 'from-cyan-300/15 to-blue-200/5' },
  80: { label: 'Rovescio', icon: '⛈️', bg: 'from-indigo-500/20 to-purple-500/5' },
  95: { label: 'Temporale', icon: '🌩️', bg: 'from-purple-500/20 to-indigo-600/5' },
};
const getW = (code) => weatherMeta[code] || { label: '?', icon: '❓', bg: 'from-slate-500/15 to-slate-600/5' };

const fallbackImg = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 250'%3E%3Crect width='100%25' height='100%25' fill='%23111827'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='12' fill='%23475569'%3ENo Image%3C/text%3E%3C/svg%3E";

export default function Notizie() {
  const [notizie, setNotizie] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [meteo, setMeteo] = useState(null);
  const [prezziMercati, setPrezziMercati] = useState([]);
  const [tickerNews, setTickerNews] = useState([]);
  const [categorie, setCategorie] = useState([]);
  const [selectedCategoria, setSelectedCategoria] = useState('all');

  useEffect(() => {
    const loadAll = async () => {
      const promises = [
        axios.get(`${API}/notizie`).then(r => { setNotizie(r.data); setCategorie([...new Set(r.data.map(n => n.categoria))]); }).catch(() => {}),
        axios.get(`${API}/meteo`).then(r => setMeteo(r.data)).catch(() => {}),
        axios.get(`${API}/prezzi-mercati`).then(r => setPrezziMercati(r.data)).catch(() => {}),
        axios.get(`${API}/ticker-news`).then(r => setTickerNews(r.data)).catch(() => {}),
      ];
      await Promise.allSettled(promises);
      setLoading(false);
    };
    loadAll();
  }, []);

  const refreshNews = async () => {
    setRefreshing(true);
    try {
      await axios.post(`${API}/notizie/refresh`);
      setTimeout(async () => {
        const res = await axios.get(`${API}/notizie`);
        setNotizie(res.data);
        setRefreshing(false);
      }, 2000);
    } catch (e) { setRefreshing(false); }
  };

  const filtered = selectedCategoria === 'all' ? notizie : notizie.filter(n => n.categoria === selectedCategoria);
  
  // Sort by date to ensure most recent article is hero
  const sortedFiltered = [...filtered].sort((a, b) => {
    const dateA = a.data_pubblicazione ? new Date(a.data_pubblicazione) : new Date(0);
    const dateB = b.data_pubblicazione ? new Date(b.data_pubblicazione) : new Date(0);
    return dateB - dateA;
  });
  
  const heroArticle = sortedFiltered[0];
  const restArticles = sortedFiltered.slice(1);

  if (loading) return <LoadingSpinner fullScreen />;

  const cw = meteo?.current_weather;
  const daily = meteo?.daily;
  const w = cw ? getW(cw.weathercode) : null;

  return (
    <PageWrapper>
      <PageHeader title="Notizie & Mercati" subtitle="Settore ortofrutticolo">
        <Button onClick={refreshNews} disabled={refreshing} size="sm" variant="outline" className="h-8">
          <RefreshCw className={cn('w-3.5 h-3.5 mr-1.5', refreshing && 'animate-spin')} />
          <span className="hidden sm:inline">{refreshing ? 'Aggiorno...' : 'Aggiorna'}</span>
        </Button>
      </PageHeader>

      {/* Top Widgets Grid - Responsive */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">

        {/* Meteo Widget */}
        {cw && w && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-white/[0.08] p-3 relative overflow-hidden"
            style={{ background: 'linear-gradient(145deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))' }}>
            <div className={cn('absolute inset-0 bg-gradient-to-br opacity-30', w.bg)} />
            <div className="relative z-10">
              <div className="flex items-center gap-1 mb-2">
                <MapPin className="w-3 h-3 text-cyan-400" />
                <span className="text-[10px] font-medium text-slate-400">Bologna</span>
                <span className="text-[9px] text-slate-600 ml-auto">{new Date().toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric' })}</span>
              </div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-3xl">{w.icon}</span>
                <div>
                  <p className="text-2xl font-bold text-white leading-none">{Math.round(cw.temperature)}°</p>
                  <p className="text-[10px] text-slate-400">{w.label}</p>
                </div>
                <div className="ml-auto text-[9px] text-slate-500 space-y-0.5">
                  <div className="flex items-center gap-1"><Wind className="w-2.5 h-2.5" />{Math.round(cw.windspeed)} km/h</div>
                  {daily && <div className="flex items-center gap-1"><Thermometer className="w-2.5 h-2.5 text-red-400" />{Math.round(daily.temperature_2m_max[0])}°</div>}
                </div>
              </div>
              {daily && (
                <div className="grid grid-cols-5 gap-1">
                  {daily.time.slice(1, 6).map((date, idx) => {
                    const dw = getW(daily.weathercode[idx + 1]);
                    return (
                      <div key={date} className="flex flex-col items-center py-1 rounded bg-white/[0.03]">
                        <p className="text-[7px] uppercase text-slate-600">{new Date(date).toLocaleDateString('it-IT', { weekday: 'short' })}</p>
                        <span className="text-sm">{dw.icon}</span>
                        <span className="text-[8px] text-white font-medium">{Math.round(daily.temperature_2m_max[idx + 1])}°</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Listini Mercato */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
          className="rounded-xl border border-white/[0.08] p-3"
          style={{ background: 'linear-gradient(145deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))' }}>
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-md bg-emerald-500/15">
              <FileText className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-white">Listini Mercato</h3>
              <p className="text-[9px] text-slate-500">Prezzi all'ingrosso</p>
            </div>
          </div>
          <div className="space-y-1">
            {prezziMercati.slice(0, 6).map((m) => (
              <a key={m.nome} href={m.url} target="_blank" rel="noopener noreferrer"
                className="flex items-center justify-between px-2 py-1.5 rounded-lg group bg-white/[0.02] border border-white/[0.04] hover:bg-emerald-500/[0.06] hover:border-emerald-500/15 transition-all">
                <div className="flex items-center gap-1.5">
                  <FileText className="w-3 h-3 text-slate-600 group-hover:text-emerald-400 transition-colors" />
                  <span className="text-[11px] text-slate-400 group-hover:text-slate-200 transition-colors">{m.nome}</span>
                </div>
                <ArrowUpRight className="w-3 h-3 text-slate-600 group-hover:text-emerald-400 transition-all" />
              </a>
            ))}
          </div>
        </motion.div>

        {/* Breaking News Ticker - Today and yesterday's news with LIVE badge */}
        {tickerNews.length > 0 && (() => {
          const today = new Date();
          const todayStr = today.toISOString().split('T')[0];
          const yesterday = new Date(today);
          yesterday.setDate(yesterday.getDate() - 1);
          const yesterdayStr = yesterday.toISOString().split('T')[0];
          
          const recentNews = tickerNews.filter(n => {
            if (!n.data) return false;
            // Parse various date formats
            try {
              const newsDate = new Date(n.data);
              const newsDateStr = newsDate.toISOString().split('T')[0];
              return newsDateStr === todayStr || newsDateStr === yesterdayStr;
            } catch {
              return false;
            }
          });
          
          // Show recent news (today + yesterday) or fallback to latest 6
          const displayNews = recentNews.length > 0 ? recentNews.slice(0, 6) : tickerNews.slice(0, 6);
          const hasRecentNews = recentNews.length > 0;
          
          return (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
              className="rounded-xl border border-white/[0.08] p-3 md:col-span-2 lg:col-span-1"
              style={{ background: 'linear-gradient(145deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))' }}>
              <div className="flex items-center gap-2 mb-2">
                <span className="px-1.5 py-0.5 text-[8px] font-bold uppercase bg-red-500/20 text-red-400 rounded animate-pulse">Live</span>
                <span className="text-xs font-semibold text-white">Breaking News</span>
                {!hasRecentNews && <span className="text-[8px] text-slate-500">(archivio)</span>}
              </div>
              <div className="space-y-1 max-h-[140px] overflow-y-auto pr-1">
                {displayNews.map((n, i) => (
                  <a key={i} href={n.url} target="_blank" rel="noopener noreferrer"
                    className="flex items-start gap-1.5 p-1.5 rounded bg-white/[0.02] border border-white/[0.04] hover:bg-cyan-500/[0.05] transition-all group">
                    <span className="w-1 h-1 rounded-full bg-cyan-500/60 shrink-0 mt-1.5" />
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] text-slate-300 group-hover:text-white line-clamp-2 leading-tight">{n.titolo}</p>
                      <p className="text-[8px] text-slate-600 mt-0.5">{n.fonte}</p>
                    </div>
                  </a>
                ))}
              </div>
            </motion.div>
          );
        })()}
      </div>

      {/* Category Filters - Scrollable on mobile */}
      <div className="flex items-center gap-1.5 mb-4 overflow-x-auto pb-2 -mx-2 px-2 scrollbar-hide">
        <button onClick={() => setSelectedCategoria('all')}
          className={cn('px-3 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-wider whitespace-nowrap transition-all',
            selectedCategoria === 'all'
              ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/25'
              : 'bg-white/[0.04] text-slate-500 border border-white/[0.06] hover:bg-white/[0.08]')}>
          Tutte ({notizie.length})
        </button>
        {categorie.map(cat => (
          <button key={cat} onClick={() => setSelectedCategoria(cat)}
            className={cn('px-3 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-wider whitespace-nowrap transition-all capitalize',
              selectedCategoria === cat
                ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/25'
                : 'bg-white/[0.04] text-slate-500 border border-white/[0.06] hover:bg-white/[0.08]')}>
            {cat}
          </button>
        ))}
      </div>

      {/* Hero Article - Compact */}
      {heroArticle && (
        <motion.article initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="relative mb-4 rounded-xl overflow-hidden cursor-pointer group border border-white/[0.08]"
          onClick={() => heroArticle.url && window.open(heroArticle.url, '_blank')}>
          <div className="flex flex-col sm:flex-row">
            <div className="relative w-full sm:w-48 h-[120px] sm:h-[100px] overflow-hidden shrink-0">
              <img src={heroArticle.immagine_url || fallbackImg} alt={heroArticle.titolo}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                onError={(e) => { e.target.src = fallbackImg; }} loading="lazy" />
            </div>
            <div className="p-3 flex flex-col justify-center flex-1" style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))' }}>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-1.5 py-0.5 text-[8px] font-bold uppercase bg-cyan-500/15 text-cyan-400 rounded">{heroArticle.fonte}</span>
                {heroArticle.data_pubblicazione && (
                  <span className="flex items-center gap-1 text-[8px] text-slate-500">
                    <Clock className="w-2.5 h-2.5" />
                    {new Date(heroArticle.data_pubblicazione).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })}
                  </span>
                )}
              </div>
              <h2 className="text-sm font-bold text-white mb-1 leading-snug line-clamp-2 group-hover:text-cyan-300 transition-colors">
                {heroArticle.titolo}
              </h2>
              <p className="text-[10px] text-slate-400 line-clamp-1 mb-1">{heroArticle.descrizione || heroArticle.contenuto}</p>
              <div className="flex items-center gap-1 text-cyan-400 text-[10px] font-medium">
                <span>Leggi</span><ArrowUpRight className="w-2.5 h-2.5" />
              </div>
            </div>
          </div>
        </motion.article>
      )}

      {/* News Grid - Responsive */}
      {restArticles.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <AnimatePresence mode="popLayout">
            {restArticles.map((notizia, index) => (
              <motion.article key={notizia.id || index} layout
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: index * 0.02, duration: 0.3 }}
                className="group rounded-xl overflow-hidden cursor-pointer border border-white/[0.06] hover:border-white/[0.12] transition-all duration-300"
                style={{ background: 'linear-gradient(145deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01))' }}
                onClick={() => notizia.url && window.open(notizia.url, '_blank')}>
                <div className="relative h-[120px] overflow-hidden">
                  <img src={notizia.immagine_url || fallbackImg} alt={notizia.titolo}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    onError={(e) => { e.target.src = fallbackImg; }} loading="lazy" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
                  <span className="absolute top-2 left-2 px-1.5 py-0.5 text-[8px] font-bold uppercase bg-black/50 backdrop-blur-sm text-white/90 rounded">{notizia.fonte}</span>
                </div>
                <div className="p-3">
                  <h3 className="font-semibold text-xs text-slate-200 mb-1.5 line-clamp-2 leading-snug group-hover:text-white transition-colors">{notizia.titolo}</h3>
                  <p className="text-[10px] text-slate-500 line-clamp-2 mb-2">{notizia.descrizione || notizia.contenuto}</p>
                  <div className="flex items-center justify-between pt-1.5 border-t border-white/[0.05]">
                    <span className="text-[9px] text-slate-600 capitalize">{notizia.categoria}</span>
                    {notizia.data_pubblicazione && (
                      <span className="text-[9px] text-slate-600">{new Date(notizia.data_pubblicazione).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })}</span>
                    )}
                  </div>
                </div>
              </motion.article>
            ))}
          </AnimatePresence>
        </div>
      ) : filtered.length === 0 && (
        <div className="text-center py-12 rounded-xl border border-dashed border-white/10 bg-white/[0.02]">
          <CloudSun className="w-10 h-10 mx-auto text-slate-600 mb-2" />
          <p className="text-sm text-slate-400">Nessuna notizia</p>
          <p className="text-xs text-slate-600 mt-0.5">Clicca Aggiorna per caricare</p>
        </div>
      )}
    </PageWrapper>
  );
}
