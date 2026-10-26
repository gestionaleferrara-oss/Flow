import { useState } from 'react';
import axios from 'axios';
import { Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const iso = (d) => {
  const z = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
  return z.toISOString().slice(0, 10);
};

const PERIODI = [
  { id: 'tutto', label: 'Tutto' },
  { id: 'mese', label: 'Mese in corso' },
  { id: 'mese_prec', label: 'Mese precedente' },
  { id: '3mesi', label: 'Ultimi 3 mesi' },
  { id: 'anno', label: 'Anno in corso' },
  { id: 'custom', label: 'Personalizzato' },
];

const TIPI = [
  { id: 'entrambi', label: 'Vendite + Acquisti' },
  { id: 'vendite', label: 'Solo vendite' },
  { id: 'acquisti', label: 'Solo acquisti' },
];

function intervallo(periodo, da, a) {
  const oggi = new Date();
  const y = oggi.getFullYear();
  const m = oggi.getMonth();
  switch (periodo) {
    case 'mese':
      return [iso(new Date(y, m, 1)), iso(oggi)];
    case 'mese_prec':
      return [iso(new Date(y, m - 1, 1)), iso(new Date(y, m, 0))];
    case '3mesi':
      return [iso(new Date(y, m - 3, oggi.getDate())), iso(oggi)];
    case 'anno':
      return [iso(new Date(y, 0, 1)), iso(oggi)];
    case 'custom':
      return [da || null, a || null];
    default:
      return [null, null];
  }
}

function Pill({ active, onClick, children, testId }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testId}
      className={cn(
        'px-3 py-1.5 rounded-lg text-sm font-medium transition-all border',
        active
          ? 'bg-primary/20 text-primary border-primary/40'
          : 'bg-muted/30 text-muted-foreground border-transparent hover:bg-muted/50'
      )}
    >
      {children}
    </button>
  );
}

export default function ExportDati() {
  const [periodo, setPeriodo] = useState('tutto');
  const [tipo, setTipo] = useState('entrambi');
  const [formato, setFormato] = useState('xlsx');
  const [da, setDa] = useState('');
  const [a, setA] = useState('');
  const [scaricando, setScaricando] = useState(false);

  const csvNonDisponibile = formato === 'csv' && tipo === 'entrambi';

  const scarica = async () => {
    const [start, end] = intervallo(periodo, da, a);
    if (periodo === 'custom' && !start && !end) {
      toast.error('Scegli almeno una data');
      return;
    }
    if (start && end && start > end) {
      toast.error('La data di inizio è successiva alla data di fine');
      return;
    }
    const params = { tipo, formato };
    if (start) params.start_date = start;
    if (end) params.end_date = end;

    setScaricando(true);
    try {
      const res = await axios.get(`${API}/export/movimenti`, { params, responseType: 'blob' });
      const disp = res.headers['content-disposition'] || '';
      const match = disp.match(/filename="?([^"]+)"?/);
      const nome = match ? match[1] : `flow_${tipo}.${formato}`;
      const url = URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = nome;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast.success('Download avviato');
    } catch (err) {
      let msg = 'Errore durante il download';
      try {
        const testo = await err.response?.data?.text();
        msg = JSON.parse(testo).detail || msg;
      } catch (_) { /* risposta non JSON */ }
      toast.error(msg);
    } finally {
      setScaricando(false);
    }
  };

  return (
    <div className="mt-8 p-6 bg-card border border-border/50 rounded-sm" data-testid="export-dati">
      <div className="flex items-center gap-2 mb-1">
        <Download className="w-5 h-5 text-primary" />
        <h3 className="font-heading text-lg font-semibold uppercase">Scarica dati</h3>
      </div>
      <p className="text-sm text-muted-foreground mb-5">
        Esporta vendite e acquisti del periodo scelto in un file Excel o CSV.
      </p>

      <div className="space-y-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Periodo</p>
          <div className="flex flex-wrap gap-2">
            {PERIODI.map((p) => (
              <Pill key={p.id} active={periodo === p.id} onClick={() => setPeriodo(p.id)} testId={`export-periodo-${p.id}`}>
                {p.label}
              </Pill>
            ))}
          </div>
          {periodo === 'custom' && (
            <div className="flex flex-wrap items-center gap-3 mt-3">
              <label className="text-sm text-muted-foreground flex items-center gap-2">
                Dal
                <input
                  type="date"
                  value={da}
                  onChange={(e) => setDa(e.target.value)}
                  className="bg-muted/30 border border-border/50 rounded-md px-2 py-1 text-sm text-foreground"
                  data-testid="export-da"
                />
              </label>
              <label className="text-sm text-muted-foreground flex items-center gap-2">
                al
                <input
                  type="date"
                  value={a}
                  onChange={(e) => setA(e.target.value)}
                  className="bg-muted/30 border border-border/50 rounded-md px-2 py-1 text-sm text-foreground"
                  data-testid="export-a"
                />
              </label>
            </div>
          )}
        </div>

        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Dati</p>
          <div className="flex flex-wrap gap-2">
            {TIPI.map((t) => (
              <Pill key={t.id} active={tipo === t.id} onClick={() => setTipo(t.id)} testId={`export-tipo-${t.id}`}>
                {t.label}
              </Pill>
            ))}
          </div>
        </div>

        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Formato</p>
          <div className="flex flex-wrap gap-2">
            <Pill active={formato === 'xlsx'} onClick={() => setFormato('xlsx')} testId="export-formato-xlsx">Excel</Pill>
            <Pill active={formato === 'csv'} onClick={() => setFormato('csv')} testId="export-formato-csv">CSV</Pill>
          </div>
          {csvNonDisponibile && (
            <p className="text-xs text-amber-400 mt-2">
              Il CSV contiene un solo tipo di dati: scegli “Solo vendite” o “Solo acquisti”, oppure usa Excel (un foglio per ciascuno).
            </p>
          )}
        </div>

        <div className="flex justify-end pt-2">
          <Button
            onClick={scarica}
            disabled={scaricando || csvNonDisponibile}
            className="gap-2 uppercase tracking-wider"
            data-testid="export-scarica-btn"
          >
            <Download className={cn('w-4 h-4', scaricando && 'animate-pulse')} />
            {scaricando ? 'Preparazione...' : 'Scarica'}
          </Button>
        </div>
      </div>
    </div>
  );
}
