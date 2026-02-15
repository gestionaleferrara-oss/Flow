import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  RefreshCw, 
  ExternalLink, 
  Cloud, 
  Sun, 
  CloudRain, 
  Snowflake,
  Wind,
  Droplets,
  TrendingUp,
  Filter,
  X
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import LoadingSpinner from '@/components/LoadingSpinner';
import { cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Weather code to icon mapping
const weatherIcons = {
  0: { icon: '☀️', name: 'Sereno' },
  1: { icon: '🌤️', name: 'Prevalentemente sereno' },
  2: { icon: '⛅', name: 'Parzialmente nuvoloso' },
  3: { icon: '☁️', name: 'Nuvoloso' },
  45: { icon: '🌫️', name: 'Nebbia' },
  48: { icon: '🌫️', name: 'Nebbia ghiacciata' },
  51: { icon: '🌦️', name: 'Pioggerella' },
  53: { icon: '🌦️', name: 'Pioggerella' },
  55: { icon: '🌧️', name: 'Pioggerella intensa' },
  61: { icon: '🌧️', name: 'Pioggia leggera' },
  63: { icon: '🌧️', name: 'Pioggia' },
  65: { icon: '🌧️', name: 'Pioggia forte' },
  71: { icon: '🌨️', name: 'Neve leggera' },
  73: { icon: '🌨️', name: 'Neve' },
  75: { icon: '❄️', name: 'Neve forte' },
  80: { icon: '⛈️', name: 'Rovescio' },
  81: { icon: '⛈️', name: 'Rovescio forte' },
  82: { icon: '⛈️', name: 'Rovescio violento' },
  95: { icon: '🌩️', name: 'Temporale' },
};

const fallbackImage = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 250' fill='%236c757d'%3E%3Crect width='100%25' height='100%25' fill='%231e293b'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='14' fill='%2364748b'%3EImmagine non disponibile%3C/text%3E%3C/svg%3E";

export default function Notizie() {
  const [notizie, setNotizie] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [meteo, setMeteo] = useState(null);
  const [prezziMercati, setPrezziMercati] = useState([]);
  const [categorie, setCategorie] = useState([]);
  const [selectedCategoria, setSelectedCategoria] = useState('all');
  const [selectedArticle, setSelectedArticle] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

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
      
      // Extract unique categories
      const cats = [...new Set(notizieRes.data.map(n => n.categoria))];
      setCategorie(cats);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const refreshNews = async () => {
    setRefreshing(true);
    try {
      await axios.post(`${API}/notizie/refresh`);
      // Wait a bit for background refresh
      setTimeout(async () => {
        const response = await axios.get(`${API}/notizie`);
        setNotizie(response.data);
        setRefreshing(false);
      }, 3000);
    } catch (error) {
      console.error('Error refreshing news:', error);
      setRefreshing(false);
    }
  };

  const filteredNotizie = selectedCategoria === 'all' 
    ? notizie 
    : notizie.filter(n => n.categoria === selectedCategoria);

  const getWeatherIcon = useCallback((code) => {
    return weatherIcons[code] || { icon: '❓', name: 'Sconosciuto' };
  }, []);

  if (loading) return <LoadingSpinner fullScreen />;

  return (
    <PageWrapper>
      <PageHeader
        title="Notizie di Mercato"
        subtitle="Ultime notizie e prezzi dal mondo dell'ortofrutta"
      >
        <Button 
          onClick={refreshNews} 
          disabled={refreshing}
          data-testid="refresh-news-btn"
          className="bg-white/5 border border-white/10 hover:bg-white/10"
        >
          <RefreshCw className={cn('w-4 h-4 mr-2', refreshing && 'animate-spin')} />
          {refreshing ? 'Aggiornamento...' : 'Aggiorna'}
        </Button>
      </PageHeader>

      {/* Widgets Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Weather Widget */}
        {meteo && meteo.current_weather && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="widget-card"
            data-testid="weather-widget"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-4">
                <span className="text-5xl">
                  {getWeatherIcon(meteo.current_weather.weathercode).icon}
                </span>
                <div>
                  <p className="text-4xl font-bold tracking-tight">
                    {Math.round(meteo.current_weather.temperature)}°
                  </p>
                  <p className="text-sm text-slate-400">
                    {getWeatherIcon(meteo.current_weather.weathercode).name}
                  </p>
                </div>
              </div>
              <div className="text-right text-sm text-slate-500">
                <p className="font-medium text-slate-400">Bologna</p>
                <p>Oggi</p>
              </div>
            </div>
            
            {/* Forecast */}
            {meteo.daily && (
              <div className="flex justify-between pt-4 border-t border-white/5">
                {meteo.daily.time.slice(1, 4).map((date, idx) => {
                  const dayName = new Date(date).toLocaleDateString('it-IT', { weekday: 'short' });
                  return (
                    <div key={date} className="text-center">
                      <p className="text-xs text-slate-500 uppercase">{dayName}</p>
                      <span className="text-2xl my-1 block">
                        {getWeatherIcon(meteo.daily.weathercode[idx + 1]).icon}
                      </span>
                      <p className="text-sm font-medium">
                        {Math.round(meteo.daily.temperature_2m_max[idx + 1])}°
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </motion.div>
        )}

        {/* Market Prices Widget */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="widget-card"
          data-testid="prices-widget"
        >
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-white/5">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            <h3 className="font-semibold text-slate-300">Prezzi Mercati Ingrosso</h3>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {prezziMercati.map((mercato, idx) => (
              <a
                key={mercato.nome}
                href={mercato.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between px-3 py-2.5 rounded-lg 
                  bg-white/[0.03] border border-white/5 hover:bg-white/[0.06] 
                  hover:border-blue-500/30 transition-all duration-300 group"
              >
                <span className="text-sm text-slate-400 group-hover:text-slate-200 transition-colors">
                  {mercato.nome}
                </span>
                <ExternalLink className="w-3.5 h-3.5 text-slate-600 group-hover:text-blue-400 transition-colors" />
              </a>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Category Filters */}
      <div className="flex flex-wrap gap-2 mb-6" data-testid="category-filters">
        <button
          onClick={() => setSelectedCategoria('all')}
          className={cn(
            'px-4 py-2 rounded-full text-sm font-medium transition-all duration-300',
            selectedCategoria === 'all'
              ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
              : 'bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10'
          )}
        >
          Tutte
        </button>
        {categorie.map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategoria(cat)}
            className={cn(
              'px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 capitalize',
              selectedCategoria === cat
                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                : 'bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10'
            )}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* News Grid */}
      {filteredNotizie.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <AnimatePresence mode="popLayout">
            {filteredNotizie.map((notizia, index) => (
              <motion.article
                key={notizia.id || index}
                layout
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: index * 0.05, duration: 0.4 }}
                className="news-card"
                onClick={() => notizia.url && window.open(notizia.url, '_blank')}
                data-testid="news-card"
              >
                <img
                  src={notizia.immagine_url || fallbackImage}
                  alt={notizia.titolo}
                  className="news-card-image"
                  onError={(e) => { e.target.src = fallbackImage; }}
                />
                <div className="news-card-body">
                  <span className="news-card-badge">{notizia.fonte}</span>
                  <h3 className="font-semibold text-slate-200 mb-2 line-clamp-2 leading-snug">
                    {notizia.titolo}
                  </h3>
                  <p className="text-sm text-slate-500 line-clamp-3">
                    {notizia.descrizione || notizia.contenuto}
                  </p>
                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/5">
                    <span className="text-xs text-slate-600 capitalize">{notizia.categoria}</span>
                    {notizia.data_pubblicazione && (
                      <span className="text-xs text-slate-600">
                        {notizia.data_pubblicazione.slice(0, 16)}
                      </span>
                    )}
                  </div>
                </div>
              </motion.article>
            ))}
          </AnimatePresence>
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-state-icon">📰</div>
          <p className="text-slate-400">Nessuna notizia disponibile</p>
          <p className="text-sm text-slate-600 mt-2">
            Clicca su "Aggiorna" per caricare le ultime notizie
          </p>
        </div>
      )}

      {/* Article Modal */}
      <AnimatePresence>
        {selectedArticle && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedArticle(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-slate-900 border border-white/10 rounded-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden"
              onClick={e => e.stopPropagation()}
            >
              <div className="p-6 border-b border-white/10 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-slate-200 line-clamp-1">
                  {selectedArticle.titolo}
                </h2>
                <button
                  onClick={() => setSelectedArticle(null)}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 overflow-y-auto max-h-[60vh]">
                {selectedArticle.immagine_url && (
                  <img
                    src={selectedArticle.immagine_url}
                    alt={selectedArticle.titolo}
                    className="w-full h-64 object-cover rounded-xl mb-6"
                  />
                )}
                <p className="text-slate-400 leading-relaxed">
                  {selectedArticle.descrizione || selectedArticle.contenuto}
                </p>
              </div>
              <div className="p-6 border-t border-white/10 flex justify-between">
                <span className="text-sm text-slate-500">{selectedArticle.fonte}</span>
                {selectedArticle.url && (
                  <a
                    href={selectedArticle.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500/20 text-blue-400 
                      rounded-lg hover:bg-blue-500/30 transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Leggi articolo completo
                  </a>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </PageWrapper>
  );
}
