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
  ChevronRight
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
        className="fixed top-4 left-4 z-50 lg:hidden p-2 bg-card border border-border rounded-sm"
      >
        {isOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setIsOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 h-full w-[280px] bg-card border-r border-border z-50',
          'transform transition-transform duration-300 lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Logo */}
        <div className="h-20 flex items-center px-6 border-b border-border">
          <Link to="/" className="flex items-center gap-3" data-testid="logo-link">
            <div className="w-10 h-10 bg-primary rounded-sm flex items-center justify-center">
              <Package className="w-6 h-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="font-heading text-xl font-bold tracking-tight">GESTIO</h1>
              <p className="text-xs text-muted-foreground">Business Manager</p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            const Icon = item.icon;
            
            return (
              <Link
                key={item.name}
                to={item.href}
                data-testid={`nav-${item.name.toLowerCase().replace(/\s/g, '-')}`}
                onClick={() => setIsOpen(false)}
                className={cn(
                  'flex items-center gap-3 px-4 py-3 rounded-sm transition-all duration-200',
                  'hover:bg-muted group',
                  isActive && 'bg-primary/10 text-primary border-l-2 border-primary'
                )}
              >
                <Icon 
                  size={20} 
                  className={cn(
                    'transition-colors',
                    isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
                  )}
                />
                <span className={cn(
                  'text-sm font-medium',
                  isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
                )}>
                  {item.name}
                </span>
                {isActive && (
                  <ChevronRight size={16} className="ml-auto text-primary" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border">
          <div className="text-xs text-muted-foreground text-center">
            <p>Gestio v1.0</p>
            <p className="mt-1">Data Analytics Hub</p>
          </div>
        </div>
      </aside>
    </>
  );
}
