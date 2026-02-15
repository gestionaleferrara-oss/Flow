import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RefreshCw, ExternalLink, X, Wind, Droplets, Thermometer,
  MapPin, Clock, ArrowUpRight, FileText, CloudSun
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import LoadingSpinner from '@/components/LoadingSpinner';
import { cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const weatherMeta = {
  0: { label: 'Sereno', icon: '☀️', gradient: 'from-amber-500/20 via-orange-500/10 to-yellow-500/5' },
  1: { label: 'Prevalentemente sereno', icon: '🌤️', gradient: 'from-amber-500/15 via-sky-500/10 to-blue-500/5' },
  2: { label: 'Parzialmente nuvoloso', icon: '⛅', gradient: 'from-sky-500/15 via-slate-500/10 to-blue-500/5' },
  3: { label: 'Nuvoloso', icon: '☁️', gradient: 'from-slate-500/20 via-gray-500/10 to-slate-600/5' },
  45: { label: 'Nebbia', icon: '🌫️', gradient: 'from-gray-400/20 via-slate-500/10 to-gray-600/5' },
  48: { label: 'Nebbia ghiacciata', icon: '🌫️', gradient: 'from-cyan-400/20 via-slate-500/10 to-gray-600/5' },
  51: { label: 'Pioggerella', icon: '🌦️', gradient: 'from-blue-400/20 via-sky-500/10 to-slate-500/5' },
  53: { label: 'Pioggerella', icon: '🌦️', gradient: 'from-blue-400/20 via-sky-500/10 to-slate-500/5' },
  55: { label: 'Pioggerella intensa', icon: '🌧️', gradient: 'from-blue-500/25 via-indigo-500/10 to-slate-500/5' },
  61: { label: 'Pioggia leggera', icon: '🌧️', gradient: 'from-blue-500/20 via-sky-600/10 to-slate-500/5' },
  63: { label: 'Pioggia', icon: '🌧️', gradient: 'from-blue-600/25 via-indigo-500/10 to-slate-600/5' },
  65: { label: 'Pioggia forte', icon: '🌧️', gradient: 'from-indigo-500/25 via-blue-600/10 to-slate-700/5' },
  71: { label: 'Neve leggera', icon: '🌨️', gradient: 'from-cyan-300/20 via-blue-200/10 to-white/5' },
  73: { label: 'Neve', icon: '🌨️', gradient: 'from-cyan-300/25 via-blue-200/10 to-white/5' },
  75: { label: 'Neve forte', icon: '❄️', gradient: 'from-cyan-200/25 via-blue-100/10 to-white/5' },
  80: { label: 'Rovescio', icon: '⛈️', gradient: 'from-indigo-500/25 via-purple-500/10 to-slate-600/5' },
  81: { label: 'Rovescio forte', icon: '⛈️', gradient: 'from-indigo-600/25 via-purple-600/10 to-slate-700/5' },
  82: { label: 'Rovescio violento', icon: '⛈️', gradient: 'from-purple-600/25 via-indigo-600/10 to-slate-800/5' },
  95: { label: 'Temporale', icon: '🌩️', gradient: 'from-purple-500/25 via-indigo-600/10 to-slate-800/5' },
};

const getWeather = (code) => weatherMeta[code] || { label: 'Sconosciuto', icon: '❓', gradient: 'from-slate-500/20 to-slate-600/5' };

const fallbackImg = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 250'%3E%3Crect width='100%25' height='100%25' fill='%23111827'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='13' fill='%23475569'%3EImmagine non disponibile%3C/text%3E%3C/svg%3E";

export default function Notizie() {
  const [notizie, setNotizie] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [meteo, setMeteo] = useState(null);
  const [prezziMercati, setPrezziMercati] = useState([]);
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
      const cats = [...new Set(notizieRes.data.map(n => n.categoria))];
      setCategorie(cats);
    } catch (error) { console.error(error); } finally { setLoading(false); }
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
    } catch (error) { setRefreshing(false); }
  };

  const filtered = selectedCategoria === 'all' ? notizie : notizie.filter(n => n.categoria === selectedCategoria);
  const heroArticle = filtered[0];
  const restArticles = filtered.slice(1);

  if (loading) return <LoadingSpinner fullScreen />;

  const cw = meteo?.current_weather;
  const daily = meteo?.daily;
  const w = cw ? getWeather(cw.weathercode) : null;

  return (
    <PageWrapper>
      <PageHeader title="Notizie & Mercati" subtitle="Il polso del settore ortofrutticolo">
        <Button
          onClick={refreshNews}
          disabled={refreshing}
          data-testid="refresh-news-btn"
          className="bg-white/10 border border-white/20 hover:bg-white/20 text-white hover:text-white"
        >
          <RefreshCw className={cn('w-4 h-4 mr-2', refreshing && 'animate-spin')} />
          {refreshing ? 'Aggiornamento...' : 'Aggiorna'}
        </Button>
      </PageHeader>

      {/* === TOP SECTION: Meteo + Mercati === */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5 mb-8">

        {/* METEO CARD — 3 colonne */}
        {cw && w && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              'lg:col-span-3 relative rounded-2xl overflow-hidden border border-white/[0.08]',
              'bg-gradient-to-br', w.gradient
            )}
            style={{
              background: 'linear-gradient(145deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%)',
              backdropFilter: 'blur(20px)',
            }}
            data-testid="weather-widget"
          >
            {/* Background gradient overlay */}
            <div className={cn('absolute inset-0 bg-gradient-to-br opacity-60', w.gradient)} />

            <div className="relative z-10 p-6">
              {/* Header */}
              <div className="flex items-center gap-2 mb-5">
                <MapPin className="w-4 h-4 text-cyan-400" />
                <span className="text-sm font-medium text-slate-300">Bologna, Italia</span>
                <span className="text-xs text-slate-500 ml-auto">
                  {new Date().toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })}
                </span>
              </div>

              {/* Main temp + icon */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-end gap-4">
                  <span className="text-7xl leading-none">{w.icon}</span>
                  <div>
                    <p className="text-5xl font-extrabold tracking-tight text-white leading-none">
                      {Math.round(cw.temperature)}°
                    </p>
                    <p className="text-sm text-slate-400 mt-1 font-medium">{w.label}</p>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2 text-sm text-slate-400">
                    <Wind className="w-4 h-4 text-sky-400" />
                    <span>{Math.round(cw.windspeed)} km/h</span>
                  </div>
                  {daily && (
                    <>
                      <div className="flex items-center gap-2 text-sm text-slate-400">
                        <Thermometer className="w-4 h-4 text-red-400" />
                        <span>Max {Math.round(daily.temperature_2m_max[0])}°</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-slate-400">
                        <Thermometer className="w-4 h-4 text-blue-400" />
                        <span>Min {Math.round(daily.temperature_2m_min[0])}°</span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* 7-day forecast strip */}
              {daily && (
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {daily.time.slice(1, 7).map((date, idx) => {
                    const dw = getWeather(daily.weathercode[idx + 1]);
                    const dayName = new Date(date).toLocaleDateString('it-IT', { weekday: 'short' });
                    return (
                      <div
                        key={date}
                        className="flex-1 min-w-[72px] flex flex-col items-center py-2.5 px-2 rounded-xl
                          bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.08] transition-colors"
                      >
                        <p className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">{dayName}</p>
                        <span className="text-xl my-1.5">{dw.icon}</span>
                        <div className="flex items-center gap-1 text-xs">
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

        {/* MERCATI CARD — 2 colonne */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2 rounded-2xl overflow-hidden border border-white/[0.08] p-5"
          style={{
            background: 'linear-gradient(145deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%)',
            backdropFilter: 'blur(20px)',
          }}
          data-testid="prices-widget"
        >
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center">
              <FileText className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Listini Mercato</h3>
              <p className="text-[11px] text-slate-500">Prezzi ingrosso aggiornati</p>
            </div>
          </div>

          <div className="space-y-2">
            {prezziMercati.map((mercato, idx) => (
              <motion.a
                key={mercato.nome}
                href={mercato.url}
                target="_blank"
                rel="noopener noreferrer"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 + idx * 0.03 }}
                className="flex items-center justify-between px-3.5 py-2.5 rounded-xl group
                  bg-white/[0.03] border border-white/[0.05]
                  hover:bg-emerald-500/[0.08] hover:border-emerald-500/20 transition-all duration-300"
              >
                <div className="flex items-center gap-2.5">
                  <MapPin className="w-3.5 h-3.5 text-slate-600 group-hover:text-emerald-400 transition-colors" />
                  <span className="text-sm text-slate-400 group-hover:text-slate-200 transition-colors font-medium">
                    {mercato.nome}
                  </span>
                </div>
                <ArrowUpRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-emerald-400 transition-all
                  group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </motion.a>
            ))}
          </div>
        </motion.div>
      </div>

      {/* === CATEGORY FILTERS === */}
      <div className="flex flex-wrap items-center gap-2 mb-6" data-testid="category-filters">
        <button
          onClick={() => setSelectedCategoria('all')}
          className={cn(
            'px-4 py-2 rounded-full text-xs font-semibold uppercase tracking-wider transition-all duration-300',
            selectedCategoria === 'all'
              ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/25 shadow-sm shadow-cyan-500/10'
              : 'bg-white/[0.04] text-slate-500 border border-white/[0.06] hover:bg-white/[0.08] hover:text-slate-300'
          )}
        >
          Tutte ({notizie.length})
        </button>
        {categorie.map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategoria(cat)}
            className={cn(
              'px-4 py-2 rounded-full text-xs font-semibold uppercase tracking-wider transition-all duration-300 capitalize',
              selectedCategoria === cat
                ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/25 shadow-sm shadow-cyan-500/10'
                : 'bg-white/[0.04] text-slate-500 border border-white/[0.06] hover:bg-white/[0.08] hover:text-slate-300'
            )}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* === HERO ARTICLE === */}
      {heroArticle && (
        <motion.article
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="relative mb-8 rounded-2xl overflow-hidden cursor-pointer group border border-white/[0.08]"
          onClick={() => heroArticle.url && window.open(heroArticle.url, '_blank')}
          data-testid="hero-news-card"
        >
          <div className="grid grid-cols-1 lg:grid-cols-2">
            <div className="relative h-[240px] lg:h-auto overflow-hidden">
              <img
                src={heroArticle.immagine_url || fallbackImg}
                alt={heroArticle.titolo}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                onError={(e) => { e.target.src = fallbackImg; }}
              />
              <div className="absolute inset-0 bg-gradient-to-r from-black/50 via-transparent to-transparent lg:hidden" />
            </div>
            <div className="p-6 lg:p-8 flex flex-col justify-center"
              style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)' }}
            >
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
              <motion.article
                key={notizia.id || index}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: index * 0.04, duration: 0.4 }}
                className="group rounded-2xl overflow-hidden cursor-pointer border border-white/[0.06]
                  hover:border-white/[0.15] transition-all duration-500 hover:-translate-y-1"
                style={{
                  background: 'linear-gradient(145deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)',
                }}
                onClick={() => notizia.url && window.open(notizia.url, '_blank')}
                data-testid="news-card"
              >
                <div className="relative h-[180px] overflow-hidden">
                  <img
                    src={notizia.immagine_url || fallbackImg}
                    alt={notizia.titolo}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                    onError={(e) => { e.target.src = fallbackImg; }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                  <span className="absolute top-3 left-3 px-2 py-1 text-[9px] font-bold uppercase tracking-wider
                    bg-black/50 backdrop-blur-md text-white/90 rounded-lg border border-white/10">
                    {notizia.fonte}
                  </span>
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
