import { useState } from 'react';
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
  ChevronRight,
  Sparkles,
  FileText
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
  const location = useLocation();

  return (
    <>
      {/* Mobile menu button */}
      <button
        data-testid="sidebar-toggle"
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-50 lg:hidden p-3 rounded-xl
          bg-white/5 backdrop-blur-xl border border-white/10
          hover:bg-white/10 transition-all duration-300"
      >
        {isOpen ? <X size={22} /> : <Menu size={22} />}
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
          'fixed left-0 top-0 h-full w-[280px] z-50',
          'bg-gradient-to-b from-slate-900/95 via-slate-900/90 to-slate-900/80',
          'backdrop-blur-2xl',
          'border-r border-white/[0.06]',
          'transform transition-transform duration-300 lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Gradient accent line */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-blue-500/50 to-transparent" />
        
        {/* Logo */}
        <div className="h-24 flex items-center px-6 border-b border-white/[0.06]">
          <Link 
            to="/" 
            className="flex items-center gap-4 group" 
            data-testid="logo-link"
          >
            <div className="relative">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 
                flex items-center justify-center shadow-lg shadow-blue-500/25
                group-hover:shadow-blue-500/40 transition-all duration-300">
                <Package className="w-6 h-6 text-white" />
              </div>
              <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full 
                bg-gradient-to-br from-cyan-400 to-blue-500 
                flex items-center justify-center">
                <Sparkles className="w-2.5 h-2.5 text-white" />
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-300 
                bg-clip-text text-transparent">
                Flusso
              </h1>
              <p className="text-[10px] text-slate-500 uppercase tracking-[0.2em] font-medium">
                Gestione Aziendale
              </p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1.5">
          {navigation.map((item, index) => {
            const isActive = location.pathname === item.href;
            const Icon = item.icon;
            
            return (
              <motion.div
                key={item.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <Link
                  to={item.href}
                  data-testid={`nav-${item.name.toLowerCase().replace(/\s/g, '-')}`}
                  onClick={() => setIsOpen(false)}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300',
                    'relative overflow-hidden group',
                    isActive 
                      ? 'bg-gradient-to-r from-blue-500/15 to-blue-500/5 text-blue-400 border border-blue-500/20'
                      : 'hover:bg-white/[0.04] text-slate-400 hover:text-slate-200 border border-transparent'
                  )}
                >
                  {/* Active indicator glow */}
                  {isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 
                      bg-gradient-to-b from-blue-400 to-blue-600 rounded-r-full
                      shadow-[0_0_15px_rgba(59,130,246,0.5)]" />
                  )}
                  
                  <Icon 
                    size={20} 
                    className={cn(
                      'transition-all duration-300 relative z-10',
                      isActive ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-300'
                    )}
                  />
                  <span className={cn(
                    'text-sm font-medium relative z-10',
                    isActive ? 'text-blue-400' : ''
                  )}>
                    {item.name}
                  </span>
                  {item.badge && (
                    <span className="ml-auto px-1.5 py-0.5 text-[10px] font-semibold bg-purple-500/20 text-purple-300 rounded">
                      {item.badge}
                    </span>
                  )}
                  {isActive && !item.badge && (
                    <ChevronRight size={16} className="ml-auto text-blue-400/60" />
                  )}
                </Link>
              </motion.div>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-white/[0.06]">
          <div className="p-4 rounded-xl bg-gradient-to-br from-white/[0.03] to-transparent 
            border border-white/[0.04]">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-700 to-slate-800 
                flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-400">Flusso v2.0</p>
                <p className="text-[10px] text-slate-600">Smart Business</p>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
