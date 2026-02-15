import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export default function PageWrapper({ children, className }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className={cn('page-container', className)}
    >
      {children}
    </motion.div>
  );
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="flex items-center justify-between mb-8">
      <div>
        <h1 className="page-title" data-testid="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {children && <div className="flex gap-3">{children}</div>}
    </div>
  );
}
