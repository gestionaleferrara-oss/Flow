import { useState, useEffect } from 'react';
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

function NavItem({ item, isActive, hoveredItem, setHoveredItem }) {
  const Icon = item.icon;
  const isHovered = hoveredItem === item.name;

  return (
    <div
      className="relative h-[44px]"
      onMouseEnter={() => setHoveredItem(item.name)}
      onMouseLeave={() => setHoveredItem(null)}
    >
      {/* Icona statica sempre visibile */}
      <Link
        to={item.href}
        data-testid={`nav-${item.name.toLowerCase().replace(/\s/g, '-')}`}
        className={cn(
          'relative flex items-center justify-center w-full h-full rounded-xl transition-colors duration-150',
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

      {/* Overlay espanso - posizionato assoluto, esce dalla sidebar */}
      <AnimatePresence>
        {isHovered && (
          <motion.div
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.85, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 600, damping: 28 }}
            className="absolute top-0 left-0 z-[70] pointer-events-auto"
            style={{ originX: 0, originY: 0.5 }}
          >
            <Link
              to={item.href}
              className="flex items-center gap-3 h-[44px] px-4 pr-5 rounded-xl whitespace-nowrap
                bg-[#0d1424]/95 border border-cyan-500/20 backdrop-blur-xl"
              style={{
                boxShadow: '0 10px 40px rgba(0,0,0,0.6), 0 0 24px rgba(34,211,238,0.12), inset 0 1px 0 rgba(255,255,255,0.08)',
              }}
            >
              {/* Glow bar a sinistra */}
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-r-full bg-cyan-400 shadow-[0_0_16px_rgba(34,211,238,0.8)]" />

              <div className="text-cyan-400">
                <Icon size={22} />
              </div>
              <motion.span
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.1, delay: 0.03 }}
                className="text-sm font-semibold text-white"
              >
                {item.name}
              </motion.span>
              {item.badge && (
                <span className="ml-1 px-1.5 py-0.5 text-[9px] font-bold bg-purple-500/25 text-purple-300 rounded-md border border-purple-500/20">
                  {item.badge}
                </span>
              )}
            </Link>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Sidebar() {
  const location = useLocation();
  const [hoveredItem, setHoveredItem] = useState(null);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  return (
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
      {/* Top glow line */}
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

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-1 overflow-y-auto">
        {navigation.map((item) => (
          <NavItem
            key={item.name}
            item={item}
            isActive={location.pathname === item.href}
            hoveredItem={hoveredItem}
            setHoveredItem={setHoveredItem}
          />
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 shrink-0">
        <div className="h-px bg-white/[0.04] mb-2" />
        <div className="flex items-center justify-center">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        </div>
      </div>
    </aside>
  );
}
