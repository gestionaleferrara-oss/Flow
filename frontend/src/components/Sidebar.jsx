import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Home, Upload, Package, Users, Truck, ShoppingCart,
  BarChart3, Newspaper, Sparkles, Zap
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
  const location = useLocation();
  const [hoveredItem, setHoveredItem] = useState(null);
  const [hoverPos, setHoverPos] = useState({ top: 0 });
  const navRefs = useRef({});

  const handleHover = useCallback((name, el) => {
    if (!el) return;
    const rect = el.getBoundingClientRect();
    setHoverPos({ top: rect.top });
    setHoveredItem(name);
  }, []);

  const hoveredData = hoveredItem ? navigation.find(n => n.name === hoveredItem) : null;

  return (
    <>
      <aside
        data-testid="sidebar"
        className="fixed left-0 top-0 h-full z-50 flex flex-col"
        style={{
          width: 76,
          background: 'rgba(8, 12, 24, 0.65)',
          backdropFilter: 'blur(40px)',
          WebkitBackdropFilter: 'blur(40px)',
          borderRight: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        {/* Top glow */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />

        {/* Logo */}
        <Link to="/" className="flex items-center justify-center py-5 group shrink-0" data-testid="logo-link">
          <div className="relative shrink-0">
            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-cyan-500/30 to-blue-600/30 blur-sm group-hover:blur-md transition-all duration-500" />
            <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 group-hover:shadow-cyan-500/40 transition-all duration-500">
              <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
          </div>
        </Link>

        <div className="mx-4 h-px bg-white/[0.04]" />

        {/* Nav icons */}
        <nav className="flex-1 px-2 py-3 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            const isHovered = hoveredItem === item.name;
            const Icon = item.icon;

            return (
              <div
                key={item.name}
                ref={el => navRefs.current[item.name] = el}
                className="relative h-[44px]"
                onMouseEnter={(e) => handleHover(item.name, e.currentTarget)}
                onMouseLeave={() => setHoveredItem(null)}
              >
                <Link
                  to={item.href}
                  data-testid={`nav-${item.name.toLowerCase().replace(/\s/g, '-')}`}
                  className={cn(
                    'flex items-center justify-center w-full h-full rounded-xl transition-colors duration-150',
                    isActive ? 'text-cyan-400' : 'text-slate-500 hover:text-slate-200'
                  )}
                >
                  {isActive && !isHovered && (
                    <motion.div
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-xl bg-white/[0.07] border border-white/[0.08]"
                      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                    />
                  )}
                  {isActive && !isHovered && (
                    <motion.div
                      layoutId="nav-bar"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.7)]"
                      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                    />
                  )}
                  <div className="relative z-10">
                    <Icon size={22} />
                  </div>
                </Link>
              </div>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 shrink-0">
          <div className="h-px bg-white/[0.04] mb-2" />
          <div className="flex items-center justify-center">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          </div>
        </div>
      </aside>

      {/* Overlay espanso — FIXED, fuori dalla sidebar */}
      <AnimatePresence>
        {hoveredData && (
          <motion.div
            key={hoveredData.name}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 600, damping: 26 }}
            className="fixed z-[80] pointer-events-none"
            style={{
              top: hoverPos.top,
              left: 8,
              originX: 0,
              originY: 0.5,
            }}
          >
            <div
              className="flex items-center gap-3 h-[44px] px-4 pr-6 rounded-xl whitespace-nowrap pointer-events-auto
                bg-[#0c1322]/95 border border-cyan-500/20 backdrop-blur-xl"
              style={{
                boxShadow: '0 10px 40px rgba(0,0,0,0.6), 0 0 30px rgba(34,211,238,0.1), inset 0 1px 0 rgba(255,255,255,0.08)',
              }}
            >
              {/* Glow bar */}
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-r-full bg-cyan-400 shadow-[0_0_16px_rgba(34,211,238,0.8)]" />

              <hoveredData.icon size={22} className="text-cyan-400 shrink-0" />

              <motion.span
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.1, delay: 0.02 }}
                className="text-sm font-semibold text-white"
              >
                {hoveredData.name}
              </motion.span>

              {hoveredData.badge && (
                <span className="ml-1 px-1.5 py-0.5 text-[9px] font-bold bg-purple-500/25 text-purple-300 rounded-md border border-purple-500/20">
                  {hoveredData.badge}
                </span>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
