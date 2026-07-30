import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Search, X, EyeOff, Check } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function ExclusionDialog({ open, onOpenChange, onSaved }) {
  const [allProducts, setAllProducts] = useState([]);
  const [excluded, setExcluded] = useState(new Set());
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    Promise.all([
      axios.get(`${API}/statistiche/lists`),
      axios.get(`${API}/esclusioni`),
    ]).then(([listsRes, exclRes]) => {
      const prods = (listsRes.data?.prodotti || []).filter(Boolean).sort((a, b) => a.localeCompare(b));
      setAllProducts(prods);
      setExcluded(new Set(exclRes.data?.nomi || []));
    }).catch(() => {
      toast.error('Errore nel caricamento dei prodotti');
    }).finally(() => setLoading(false));
  }, [open]);

  const filtered = useMemo(() => {
    if (!filter.trim()) return allProducts;
    const f = filter.trim().toLowerCase();
    return allProducts.filter(p => p.toLowerCase().includes(f));
  }, [allProducts, filter]);

  const allFilteredSelected = filtered.length > 0 && filtered.every(p => excluded.has(p));

  const toggle = (name) => {
    setExcluded(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  };

  const toggleAllFiltered = () => {
    setExcluded(prev => {
      const next = new Set(prev);
      if (allFilteredSelected) {
        filtered.forEach(p => next.delete(p));
      } else {
        filtered.forEach(p => next.add(p));
      }
      return next;
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const nomi = Array.from(excluded);
      await axios.put(`${API}/esclusioni`, { nomi });
      toast.success(`${nomi.length} articoli esclusi dai calcoli`);
      onOpenChange(false);
      onSaved && onSaved(nomi);
    } catch (e) {
      toast.error('Errore nel salvataggio delle esclusioni');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" data-testid="exclusion-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <EyeOff className="w-4 h-4 text-amber-400" /> Escludi articoli dai calcoli
          </DialogTitle>
          <DialogDescription>
            Gli articoli selezionati restano visibili in grigio nel Magazzino ma vengono esclusi da tutte le statistiche, dashboard e previsioni.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Filtra per nome, lettera o simbolo..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="pl-10"
              data-testid="exclusion-filter-input"
            />
          </div>

          <div className="flex items-center justify-between text-xs">
            <button
              onClick={toggleAllFiltered}
              className="flex items-center gap-2 text-slate-300 hover:text-white transition-colors"
              data-testid="exclusion-select-all"
            >
              <span className={cn(
                "w-4 h-4 rounded border flex items-center justify-center",
                allFilteredSelected ? "bg-amber-500 border-amber-500" : "border-slate-500"
              )}>
                {allFilteredSelected && <Check className="w-3 h-3 text-black" />}
              </span>
              {allFilteredSelected ? 'Deseleziona tutti' : 'Seleziona tutti'} ({filtered.length})
            </button>
            <span className="text-amber-400 font-medium" data-testid="exclusion-count">
              {excluded.size} esclusi
            </span>
          </div>

          <ScrollArea className="h-64 rounded-lg border border-border/50">
            {loading ? (
              <div className="p-4 text-center text-sm text-slate-500">Caricamento...</div>
            ) : filtered.length === 0 ? (
              <div className="p-4 text-center text-sm text-slate-500">Nessun articolo trovato</div>
            ) : (
              <div className="divide-y divide-white/[0.04]">
                {filtered.map((name) => {
                  const isOn = excluded.has(name);
                  return (
                    <label
                      key={name}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-white/[0.03] transition-colors",
                        isOn && "bg-amber-500/5"
                      )}
                      data-testid={`exclusion-item-${name}`}
                    >
                      <Checkbox checked={isOn} onCheckedChange={() => toggle(name)} />
                      <span className={cn("text-sm truncate", isOn ? "text-amber-400" : "text-slate-300")}>{name}</span>
                    </label>
                  );
                })}
              </div>
            )}
          </ScrollArea>
        </div>

        <div className="flex justify-end gap-2 mt-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="exclusion-cancel-btn">
            <X className="w-4 h-4 mr-1" /> Annulla
          </Button>
          <Button onClick={handleSave} disabled={saving} data-testid="exclusion-save-btn">
            <Check className="w-4 h-4 mr-1" /> {saving ? 'Salvataggio...' : 'Salva esclusioni'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
