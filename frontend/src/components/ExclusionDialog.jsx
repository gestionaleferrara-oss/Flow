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
  const [showOnlyExcluded, setShowOnlyExcluded] = useState(false);

  useEffect(() => {
    if (!open) return;
    setShowOnlyExcluded(false);
    setFilter('');
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
    let list = allProducts;
    if (showOnlyExcluded) list = list.filter(p => excluded.has(p));
    if (filter.trim()) {
      const f = filter.trim().toLowerCase();
      list = list.filter(p => p.toLowerCase().includes(f));
    }
    return list;
  }, [allProducts, filter, showOnlyExcluded, excluded]);

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
      <DialogContent className="max-w-lg w-[calc(100vw-2rem)] overflow-hidden" data-testid="exclusion-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <EyeOff className="w-4 h-4 text-amber-400" /> Escludi articoli dai calcoli
          </DialogTitle>
          <DialogDescription>
            Gli articoli selezionati restano visibili in grigio nel Magazzino ma vengono esclusi da tutte le statistiche, dashboard e previsioni.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 min-w-0">
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            <Input
              placeholder="Filtra per nome, lettera o simbolo..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="pl-10 w-full"
              data-testid="exclusion-filter-input"
            />
          </div>

          <div className="flex items-center justify-between gap-2 text-xs">
            <button
              onClick={toggleAllFiltered}
              className="flex items-center gap-2 text-slate-300 hover:text-white transition-colors min-w-0"
              data-testid="exclusion-select-all"
            >
              <span className={cn(
                "w-4 h-4 shrink-0 rounded border flex items-center justify-center",
                allFilteredSelected ? "bg-amber-500 border-amber-500" : "border-slate-500"
              )}>
                {allFilteredSelected && <Check className="w-3 h-3 text-black" />}
              </span>
              <span className="truncate">{allFilteredSelected ? 'Deseleziona tutti' : 'Seleziona tutti'} ({filtered.length})</span>
            </button>
            <button
              onClick={() => setShowOnlyExcluded(v => !v)}
              disabled={excluded.size === 0}
              className={cn(
                "shrink-0 font-medium px-2 py-1 rounded-md transition-colors border",
                showOnlyExcluded
                  ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                  : "text-amber-400 border-transparent hover:bg-amber-500/10 disabled:opacity-40 disabled:cursor-not-allowed"
              )}
              data-testid="exclusion-count"
              title="Mostra solo gli articoli esclusi per deselezionarli"
            >
              {excluded.size} esclusi{showOnlyExcluded ? ' • mostra tutti' : ''}
            </button>
          </div>

          <ScrollArea className="h-64 w-full rounded-lg border border-border/50">
            {loading ? (
              <div className="p-4 text-center text-sm text-slate-500">Caricamento...</div>
            ) : filtered.length === 0 ? (
              <div className="p-4 text-center text-sm text-slate-500">
                {showOnlyExcluded ? 'Nessun articolo escluso' : 'Nessun articolo trovato'}
              </div>
            ) : (
              <div className="divide-y divide-white/[0.04]">
                {filtered.map((name) => {
                  const isOn = excluded.has(name);
                  return (
                    <label
                      key={name}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-white/[0.03] transition-colors min-w-0",
                        isOn && "bg-amber-500/5"
                      )}
                      data-testid={`exclusion-item-${name}`}
                    >
                      <Checkbox className="shrink-0" checked={isOn} onCheckedChange={() => toggle(name)} />
                      <span className={cn("text-sm truncate min-w-0", isOn ? "text-amber-400" : "text-slate-300")}>{name}</span>
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
