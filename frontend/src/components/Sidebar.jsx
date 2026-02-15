import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Home,
  Upload,
  Package,
  Users,
  Truck,
  ShoppingCart,
  BarChart3,
  Newspaper,
  Menu,
  X,
  Sparkles,
  ChevronRight,
  Zap
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Importa Dati', href: '/upload', icon: Upload },
  { name: 'Magazzino', href: '/magazzino', icon: Package },
  { name: 'Vendite', href: '/vendite', icon: BarChart3 },
  { name: 'Clienti', href: '/clienti', icon: Users },
  { name: 'Fornitori', href: '/fornitori', icon: Truck },
  { name: 'Acquisti', href: '/ordini', icon: ShoppingCart },
  { name: 'Statistiche', href: '/statistiche', icon: BarChart3 },
  { name: 'Report AI', href: '/report-ai', icon: Sparkles, badge: 'AI' },
  { name: 'Notizie', href: '/notizie', icon: Newspaper },
];

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(false);
  const [hoveredIdx, setHoveredIdx] = useState(null);
  const location = useLocation();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  return (
    <>
      {/* Mobile toggle */}
      <button
        data-testid="sidebar-toggle"
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-50 lg:hidden p-3 rounded-xl
          bg-white/5 backdrop-blur-xl border border-white/10
          hover:bg-white/10 transition-all duration-300"
      >
        {isOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
            onClick={() => setIsOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 h-full w-[220px] z-50 flex flex-col',
          'transition-transform duration-300 lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        style={{
          background: 'rgba(8, 12, 24, 0.55)',
          backdropFilter: 'blur(40px)',
          WebkitBackdropFilter: 'blur(40px)',
          borderRight: '1px solid rgba(255,255,255,0.05)'
        }}
      >
        {/* Top accent line */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />

        {/* Logo */}
        <Link
          to="/"
          className="flex items-center gap-3 px-5 py-5 group"
          data-testid="logo-link"
          onClick={() => setIsOpen(false)}
        >
          <div className="relative w-9 h-9 flex items-center justify-center">
            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-cyan-500/30 to-blue-600/30 
              blur-sm group-hover:blur-md transition-all duration-500" />
            <div className="relative w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 
              flex items-center justify-center shadow-lg shadow-cyan-500/20
              group-hover:shadow-cyan-500/40 transition-all duration-500">
              <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
          </div>
          <div className="overflow-hidden">
            <h1 className="text-lg font-bold tracking-tight text-white leading-none">
              Flusso
            </h1>
            <p className="text-[9px] text-slate-500 uppercase tracking-[0.25em] font-medium mt-0.5">
              Business Hub
            </p>
          </div>
        </Link>

        {/* Divider */}
        <div className="mx-4 h-px bg-white/[0.04]" />

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {navigation.map((item, index) => {
            const isActive = location.pathname === item.href;
            const Icon = item.icon;
            const isHovered = hoveredIdx === index;

            return (
              <Link
                key={item.name}
                to={item.href}
                data-testid={`nav-${item.name.toLowerCase().replace(/\s/g, '-')}`}
                onClick={() => setIsOpen(false)}
                onMouseEnter={() => setHoveredIdx(index)}
                onMouseLeave={() => setHoveredIdx(null)}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 relative text-[13px] font-medium',
                  isActive
                    ? 'text-cyan-400'
                    : 'text-slate-500 hover:text-slate-200'
                )}
              >
                {/* Active/Hover background */}
                {(isActive || isHovered) && (
                  <motion.div
                    layoutId="sidebar-bg"
                    className={cn(
                      'absolute inset-0 rounded-lg',
                      isActive
                        ? 'bg-white/[0.06] border border-white/[0.08]'
                        : 'bg-white/[0.03]'
                    )}
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}

                {/* Active left bar */}
                {isActive && (
                  <motion.div
                    layoutId="sidebar-indicator"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.6)]"
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}

                <Icon
                  size={17}
                  className={cn(
                    'relative z-10 transition-colors duration-200',
                    isActive ? 'text-cyan-400' : ''
                  )}
                />
                <span className="relative z-10">{item.name}</span>

                {item.badge && (
                  <span className="ml-auto relative z-10 px-1.5 py-0.5 text-[9px] font-bold bg-purple-500/25 text-purple-300 rounded-md border border-purple-500/20">
                    {item.badge}
                  </span>
                )}
                {isActive && !item.badge && (
                  <ChevronRight size={14} className="ml-auto relative z-10 text-cyan-400/40" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4">
          <div className="h-px bg-white/[0.04] mb-3" />
          <div className="flex items-center justify-between px-1">
            <div>
              <p className="text-[10px] font-medium text-slate-500">Flusso v2.1</p>
              <p className="text-[9px] text-slate-600">{time.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}</p>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[9px] text-emerald-500/70">Online</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
