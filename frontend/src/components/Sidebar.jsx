import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
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
  const [expanded, setExpanded] = useState(false);
  const location = useLocation();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  return (
    <motion.aside
      data-testid="sidebar"
      onMouseEnter={() => setExpanded(true)}
      onMouseLeave={() => setExpanded(false)}
      animate={{ width: expanded ? 230 : 68 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="fixed left-0 top-0 h-full z-50 flex flex-col overflow-hidden"
      style={{
        background: 'rgba(8, 12, 24, 0.65)',
        backdropFilter: 'blur(40px)',
        WebkitBackdropFilter: 'blur(40px)',
        borderRight: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      {/* Top glow line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />

      {/* Logo */}
      <Link to="/" className="flex items-center gap-3 px-4 py-5 group shrink-0" data-testid="logo-link">
        <motion.div
          animate={{ scale: expanded ? 1 : 0.95 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          className="relative shrink-0"
        >
          <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-cyan-500/30 to-blue-600/30 blur-sm 
            group-hover:blur-md transition-all duration-500" />
          <div className="relative w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 
            flex items-center justify-center shadow-lg shadow-cyan-500/20
            group-hover:shadow-cyan-500/40 transition-all duration-500">
            <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
          </div>
        </motion.div>
        <motion.div
          animate={{ opacity: expanded ? 1 : 0, x: expanded ? 0 : -8 }}
          transition={{ duration: 0.15, delay: expanded ? 0.05 : 0 }}
          className="overflow-hidden whitespace-nowrap"
        >
          <h1 className="text-base font-bold tracking-tight text-white leading-none">Flusso</h1>
          <p className="text-[9px] text-slate-500 uppercase tracking-[0.2em] font-medium mt-0.5">Business Hub</p>
        </motion.div>
      </Link>

      <div className="mx-3 h-px bg-white/[0.04]" />

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto overflow-x-hidden">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              to={item.href}
              data-testid={`nav-${item.name.toLowerCase().replace(/\s/g, '-')}`}
              className={cn(
                'relative flex items-center gap-3 rounded-lg transition-all duration-200 group/item',
                expanded ? 'px-3 py-2.5' : 'px-0 py-2.5 justify-center',
                isActive
                  ? 'text-cyan-400'
                  : 'text-slate-500 hover:text-slate-200'
              )}
            >
              {/* Background */}
              {isActive && (
                <motion.div
                  layoutId="nav-active"
                  className="absolute inset-0 rounded-lg bg-white/[0.07] border border-white/[0.08]"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}

              {/* Left indicator */}
              {isActive && (
                <motion.div
                  layoutId="nav-bar"
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-cyan-400 
                    shadow-[0_0_12px_rgba(34,211,238,0.7)]"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}

              {/* Icon with zoom on hover */}
              <motion.div
                className="relative z-10 shrink-0"
                whileHover={{ scale: 1.2 }}
                transition={{ type: 'spring', stiffness: 500, damping: 20 }}
              >
                <Icon size={18} className={cn(isActive ? 'text-cyan-400' : 'group-hover/item:text-slate-200')} />
              </motion.div>

              {/* Text slides in */}
              <motion.span
                animate={{
                  opacity: expanded ? 1 : 0,
                  x: expanded ? 0 : -10,
                  width: expanded ? 'auto' : 0,
                }}
                transition={{ duration: 0.15, delay: expanded ? 0.03 : 0 }}
                className="relative z-10 text-[13px] font-medium whitespace-nowrap overflow-hidden"
              >
                {item.name}
              </motion.span>

              {/* Badge */}
              {item.badge && expanded && (
                <motion.span
                  initial={{ opacity: 0, scale: 0.5 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.1 }}
                  className="ml-auto relative z-10 px-1.5 py-0.5 text-[9px] font-bold bg-purple-500/25 
                    text-purple-300 rounded-md border border-purple-500/20"
                >
                  {item.badge}
                </motion.span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 shrink-0">
        <div className="h-px bg-white/[0.04] mb-2" />
        <div className={cn('flex items-center', expanded ? 'justify-between px-1' : 'justify-center')}>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
            <motion.span
              animate={{ opacity: expanded ? 1 : 0, width: expanded ? 'auto' : 0 }}
              transition={{ duration: 0.15 }}
              className="text-[9px] text-emerald-500/70 whitespace-nowrap overflow-hidden"
            >
              Online
            </motion.span>
          </div>
          {expanded && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-[9px] text-slate-600"
            >
              {time.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}
            </motion.p>
          )}
        </div>
      </div>
    </motion.aside>
  );
}
