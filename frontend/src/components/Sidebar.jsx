import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Home, Upload, Package, Users, Truck, ShoppingCart,
  BarChart3, Newspaper, Sparkles, Zap, X
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Importa Dati', href: '/upload', icon: Upload },
  { name: 'Forecast', href: '/forecast', icon: Sparkles, badge: 'AI' },
  { name: 'Magazzino', href: '/magazzino', icon: Package },
  { name: 'Vendite', href: '/vendite', icon: BarChart3 },
  { name: 'Clienti', href: '/clienti', icon: Users },
  { name: 'Fornitori', href: '/fornitori', icon: Truck },
  { name: 'Acquisti', href: '/ordini', icon: ShoppingCart },
  { name: 'Statistiche', href: '/statistiche', icon: BarChart3 },
  { name: 'Report AI', href: '/report-ai', icon: Sparkles, badge: 'AI' },
  { name: 'Notizie', href: '/notizie', icon: Newspaper },
];

// Prefetch map for instant navigation
const prefetchMap = {
  '/': () => import('@/pages/Dashboard'),
  '/upload': () => import('@/pages/UploadCSV'),
  '/magazzino': () => import('@/pages/Magazzino'),
  '/vendite': () => import('@/pages/Vendite'),
  '/clienti': () => import('@/pages/Clienti'),
  '/fornitori': () => import('@/pages/Fornitori'),
  '/ordini': () => import('@/pages/Ordini'),
  '/statistiche': () => import('@/pages/Statistiche'),
  '/report-ai': () => import('@/pages/ReportAI'),
  '/notizie': () => import('@/pages/Notizie'),
};
const prefetched = new Set();

export default function Sidebar({ mobileOpen, onMobileClose }) {
  const location = useLocation();
  const [hoveredItem, setHoveredItem] = useState(null);
  const [hoverPos, setHoverPos] = useState({ top: 0 });
  const leaveTimer = useRef(null);

  const enterItem = useCallback((name, el, href) => {
    clearTimeout(leaveTimer.current);
    const rect = el.getBoundingClientRect();
    setHoverPos({ top: rect.top });
    setHoveredItem(name);
    // Prefetch page chunk on hover
    if (href && !prefetched.has(href) && prefetchMap[href]) {
      prefetched.add(href);
      prefetchMap[href]();
    }
  }, []);

  const leaveItem = useCallback(() => {
    leaveTimer.current = setTimeout(() => setHoveredItem(null), 80);
  }, []);

  const keepHover = useCallback(() => {
    clearTimeout(leaveTimer.current);
  }, []);

  useEffect(() => () => clearTimeout(leaveTimer.current), []);

  // Close mobile sidebar on route change
  useEffect(() => {
    if (mobileOpen && onMobileClose) onMobileClose();
  }, [location.pathname]);

  const hoveredData = hoveredItem ? navigation.find(n => n.name === hoveredItem) : null;
  const HoveredIcon = hoveredData?.icon;

  return (
    <>
      {/* Mobile backdrop overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[45] lg:hidden"
            onClick={onMobileClose}
            data-testid="sidebar-overlay"
          />
        )}
      </AnimatePresence>

      <aside
        data-testid="sidebar"
        className={cn(
          "fixed left-0 top-0 h-full z-50 flex flex-col transition-transform duration-300 ease-out",
          "lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
        style={{
          width: 76,
          background: 'rgba(8, 12, 24, 0.65)',
          backdropFilter: 'blur(40px)',
          WebkitBackdropFilter: 'blur(40px)',
          borderRight: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />

        {/* Logo + Close on mobile */}
        <div className="flex items-center justify-center py-5 shrink-0 relative">
          <Link to="/" className="group" data-testid="logo-link">
            <div className="relative shrink-0">
              <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-cyan-500/30 to-blue-600/30 blur-sm group-hover:blur-md transition-all duration-500" />
              <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 group-hover:shadow-cyan-500/40 transition-all duration-500">
                <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
              </div>
            </div>
          </Link>
          {/* Mobile close button */}
          <button
            onClick={onMobileClose}
            className="absolute right-1 top-3 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 lg:hidden"
            data-testid="sidebar-close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="mx-4 h-px bg-white/[0.04]" />

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            const isHovered = hoveredItem === item.name;
            const Icon = item.icon;

            return (
              <div
                key={item.name}
                className="relative h-[44px]"
                onMouseEnter={(e) => enterItem(item.name, e.currentTarget, item.href)}
                onMouseLeave={leaveItem}
              >
                <Link
                  to={item.href}
                  data-testid={`nav-${item.name.toLowerCase().replace(/\s/g, '-')}`}
                  className={cn(
                    'flex items-center justify-center w-full h-full rounded-xl transition-colors duration-150',
                    isHovered ? 'text-cyan-400' : isActive ? 'text-cyan-400' : 'text-slate-500 hover:text-slate-200'
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

        <div className="px-4 py-3 shrink-0">
          <div className="h-px bg-white/[0.04] mb-2" />
          <div className="flex items-center justify-center">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          </div>
        </div>
      </aside>

      {/* Popup espanso — fixed position, fuori dal flusso sidebar */}
      <AnimatePresence>
        {hoveredData && HoveredIcon && (
          <motion.div
            key={hoveredData.name}
            initial={{ scale: 0.75, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.75, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 650, damping: 28 }}
            className="fixed z-[100] hidden lg:block"
            style={{
              top: hoverPos.top,
              left: 10,
              transformOrigin: 'left center',
            }}
            onMouseEnter={keepHover}
            onMouseLeave={leaveItem}
          >
            <Link
              to={hoveredData.href}
              className="flex items-center gap-3 h-[44px] px-4 pr-6 rounded-xl whitespace-nowrap
                bg-[#0b1120] border border-cyan-500/25 backdrop-blur-xl"
              style={{
                boxShadow: '0 12px 48px rgba(0,0,0,0.7), 0 0 32px rgba(34,211,238,0.12), inset 0 1px 0 rgba(255,255,255,0.08)',
              }}
            >
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-r-full bg-cyan-400 shadow-[0_0_16px_rgba(34,211,238,0.9)]" />
              <HoveredIcon size={22} className="text-cyan-400 shrink-0" />
              <motion.span
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.1, delay: 0.03 }}
                className="text-sm font-semibold text-white"
              >
                {hoveredData.name}
              </motion.span>
              {hoveredData.badge && (
                <span className="ml-1 px-1.5 py-0.5 text-[9px] font-bold bg-purple-500/25 text-purple-300 rounded-md border border-purple-500/20">
                  {hoveredData.badge}
                </span>
              )}
            </Link>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
