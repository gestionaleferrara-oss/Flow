import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Search, X, FileDown, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const TIPI = [
  { id: 'prodotto', label: 'Prodotto', coll: 'prodotti' },
  { id: 'cliente', label: 'Cliente', coll: 'clienti' },
  { id: 'fornitore', label: 'Fornitore', coll: 'fornitori' },
];
const num = (v) => (v ?? 0).toLocaleString('it-IT');
const dmy = (s) => (s ? s.split('-').reverse().join('/') : '—');

function Kpi({ label, value, color }) {
  return (
    <div className="rounded-xl border border-white/[0.07] bg-black/20 p-3">
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={cn('text-sm font-bold tabular-nums mt-1 truncate', color)}>{value}</div>
    </div>
  );
}

export const PrevisioneRicerca = ({ giorni = 30 }) => {
  const [tipo, setTipo] = useState('prodotto');
  const [q, setQ] = useState('');
  const [opts, setOpts] = useState([]);
  const [cercando, setCercando] = useState(false);
  const [vista, setVista] = useState({ clienti: true, fornitori: true });
  const [open, setOpen] = useState(false);
  const [scelti, setScelti] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const boxRef = useRef(null);

  const coll = TIPI.find((t) => t.id === tipo).coll;

  useEffect(() => {
    const fuori = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', fuori);
    return () => document.removeEventListener('mousedown', fuori);
  }, []);

  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const r = await axios.get(`${API}/analisi/opzioni`, { params: { q, tipo: coll, limit: 15 } });
        setOpts(r.data.nomi || []);
      } catch (e) { setOpts([]); } finally { setCercando(false); }
    }, 250);
    return () => clearTimeout(t);
  }, [q, coll]);

  const qs = (() => {
    const p = new URLSearchParams();
    p.set('tipo', tipo);
    scelti.forEach((n) => p.append('nomi', n));
    p.set('giorni', String(giorni));
    if (tipo === 'prodotto') {
      p.set('vista', vista.clienti && vista.fornitori ? 'entrambi' : vista.fornitori ? 'fornitori' : 'clienti');
    }
    return p.toString();
  })();

  useEffect(() => {
    if (!scelti.length) { setData(null); return; }
    let vivo = true;
    (async () => {
      setLoading(true);
      try {
        const r = await axios.get(`${API}/analisi/previsione?${qs}`);
        if (vivo) setData(r.data);
      } catch (e) { if (vivo) setData(null); } finally { if (vivo) setLoading(false); }
    })();
    return () => { vivo = false; };
  }, [qs, scelti.length]);

  const k = data?.kpi;
  const per = data?.periodo;
  const righe = data?.righe || data?.clienti || [];
  const n = (data?.nomi || []).length;
  const PLUR = { prodotto: 'prodotti', cliente: 'clienti', fornitore: 'fornitori' };
  const etichettaSelezione = n === 1 ? data?.nomi[0] : `${n} ${PLUR[tipo]} selezionati`;

  return (
    <div className="rounded-2xl border border-white/[0.07] bg-white/[0.015] mb-6" data-testid="previsione-ricerca">
      <div className="flex flex-wrap items-center gap-2 px-4 py-3">
        <div className="flex gap-1 p-0.5 rounded-lg bg-white/[0.03] border border-white/[0.06]">
          {TIPI.map((t) => (
            <button key={t.id} onClick={() => { setTipo(t.id); setScelti([]); setQ(''); setOpts([]); }}
              data-testid={`previsione-tipo-${t.id}`}
              className={cn('px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors',
                tipo === t.id ? 'bg-cyan-500/15 text-cyan-300' : 'text-slate-400 hover:text-slate-200')}>
              {t.label}
            </button>
          ))}
        </div>

        <div className="relative flex-1 min-w-[240px]" ref={boxRef}>
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
          <Input value={q} placeholder={`Previsione su un ${tipo}: scrivi per cercare…`}
            onChange={(e) => { setQ(e.target.value); setOpts([]); setCercando(true); setOpen(true); }}
            onFocus={() => setOpen(true)}
            onKeyDown={(e) => { if (e.key === 'Escape') setOpen(false); }}
            ref={inputRef}
            className="h-9 pl-8 text-sm" data-testid="previsione-input" />
          {q && (
            <button onClick={() => { setQ(''); setOpts([]); }} data-testid="previsione-clear"
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded text-slate-500 hover:text-white">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          {open && (opts.length > 0 || cercando) && (
            <div className="absolute z-50 top-full left-0 right-0 mt-1 max-h-72 overflow-auto rounded-lg border border-white/10 bg-[#0b1120] shadow-2xl">
              <div className="flex items-center justify-between px-3 py-1.5 border-b border-white/[0.06] sticky top-0 bg-[#0b1120]">
                <span className="text-[10px] uppercase tracking-wider text-slate-500">
                  Clicca per aggiungere · {scelti.length} selezionati
                </span>
                <button onMouseDown={(e) => { e.preventDefault(); setOpen(false); }}
                  data-testid="previsione-chiudi-lista"
                  className="text-[10px] text-slate-400 hover:text-white px-1.5 py-0.5 rounded hover:bg-white/10">
                  chiudi
                </button>
              </div>
              {cercando && (
                <div className="px-3 py-2 text-xs text-slate-500">Cerco…</div>
              )}
              {opts.map((o, i) => (
                <div key={o} data-testid={`previsione-opzione-${i}`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    setScelti((v) => (v.includes(o) ? v.filter((x) => x !== o) : [...v, o]));
                    inputRef.current?.focus();
                  }}
                  className={cn('flex items-center gap-2 px-3 py-2 text-xs cursor-pointer',
                    scelti.includes(o)
                      ? 'bg-cyan-500/10 text-cyan-200'
                      : 'text-slate-300 hover:bg-white/[0.04] hover:text-slate-100')}>
                  <span className={cn('w-3 h-3 rounded-[3px] border flex items-center justify-center shrink-0',
                    scelti.includes(o) ? 'bg-cyan-500 border-cyan-400' : 'border-white/20')}>
                    {scelti.includes(o) && <Check className="w-2.5 h-2.5 text-[#0b1120]" />}
                  </span>
                  {o}
                </div>
              ))}
            </div>
          )}
        </div>

        {tipo === 'prodotto' && (
          <div className="flex items-center gap-2.5" data-testid="previsione-vista">
            {[{ id: 'clienti', label: 'Clienti' }, { id: 'fornitori', label: 'Fornitori' }].map((v) => (
              <label key={v.id} data-testid={`previsione-vista-${v.id}`}
                className="inline-flex items-center gap-1.5 text-[11px] text-slate-400 hover:text-slate-200 cursor-pointer select-none">
                <input type="checkbox" checked={vista[v.id]}
                  onChange={(e) => setVista((x) => {
                    const next = { ...x, [v.id]: e.target.checked };
                    return next.clienti || next.fornitori ? next : x;
                  })}
                  className="accent-cyan-500 w-3 h-3" />
                {v.label}
              </label>
            ))}
          </div>
        )}

        <span className="text-[11px] text-slate-500 whitespace-nowrap">prossimi {giorni} gg</span>

        {scelti.length > 0 && (
          <Button size="sm" variant="outline" data-testid="previsione-export-pdf"
            onClick={() => window.open(`${API}/analisi/previsione/pdf?${qs}`, '_blank')}>
            <FileDown className="w-3.5 h-3.5 mr-1.5" /> PDF
          </Button>
        )}
      </div>

      {scelti.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-4 pb-3" data-testid="previsione-selezione">
          {scelti.map((n, i) => (
            <span key={n} data-testid={`previsione-chip-${i}`}
              className="inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/25 text-[11px] text-cyan-200">
              {n}
              <button onClick={() => setScelti((v) => v.filter((x) => x !== n))}
                data-testid={`previsione-chip-${i}-remove`}
                className="p-0.5 rounded hover:bg-white/10 text-cyan-300/70 hover:text-white">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
          <button onClick={() => setScelti([])} data-testid="previsione-reset"
            className="text-[11px] text-slate-500 hover:text-slate-300 px-1.5">azzera</button>
        </div>
      )}

      {loading && <div className="px-4 pb-4"><LoadingSpinner /></div>}

      {data && !loading && (
        <div className="border-t border-white/[0.06] p-4 space-y-4" data-testid="previsione-risultato">
          <p className="text-xs text-slate-400" data-testid="previsione-periodi">
            <span className="text-slate-200 font-medium">{etichettaSelezione}</span> · previsione dal {dmy(per.futuro_start)} al{' '}
            {dmy(per.futuro_end)}, calcolata sul venduto dal {dmy(per.storico_start)} al {dmy(per.storico_end)} (anno scorso)
          </p>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {tipo === 'prodotto' && (
              <>
                <Kpi label="Quantità attesa" value={`${num(k.quantita_attesa)} pz`} color="text-cyan-300" />
                <Kpi label="Fatturato atteso" value={formatCurrency(k.fatturato_atteso)} color="text-white" />
                <Kpi label="Margine previsto" value={k.margine_atteso !== null ? `${formatCurrency(k.margine_atteso)} (${k.margine_pct}%)` : '—'} color="text-violet-300" />
                <Kpi label="Da ordinare" value={`${num(k.da_ordinare)} pz · ${formatCurrency(k.valore_ordine)}`} color={k.da_ordinare > 0 ? 'text-amber-300' : 'text-slate-500'} />
                <Kpi label="Giacenza totale" value={`${num(k.giacenza)} pz`} color="text-slate-200" />
                <Kpi label="Clienti attesi" value={`${k.clienti_attesi}`} color="text-emerald-300" />
              </>
            )}
            {tipo === 'cliente' && (
              <>
                <Kpi label="Fatturato atteso" value={formatCurrency(k.fatturato_atteso)} color="text-white" />
                <Kpi label="Margine previsto" value={k.margine_atteso !== null ? `${formatCurrency(k.margine_atteso)} (${k.margine_pct}%)` : '—'} color="text-violet-300" />
                <Kpi label="Referenze attese" value={`${k.referenze}`} color="text-cyan-300" />
                <Kpi label="Da proporre" value={`${k.referenze_da_proporre} · ${formatCurrency(k.valore_da_proporre)}`} color="text-amber-300" />
                <Kpi label="Ultimo ordine" value={dmy(k.ultimo_ordine)} color="text-slate-200" />
                <Kpi label="Giorni dall'ultimo ordine" value={k.giorni_da_ultimo_ordine !== null ? `${k.giorni_da_ultimo_ordine} gg` : '—'} color={k.giorni_da_ultimo_ordine > 45 ? 'text-rose-300' : 'text-slate-200'} />
              </>
            )}
            {tipo === 'fornitore' && (
              <>
                <Kpi label="Valore ordine" value={formatCurrency(k.valore_ordine)} color="text-cyan-300" />
                <Kpi label="Articoli da ordinare" value={`${k.articoli_da_ordinare} di ${k.articoli_trattati}`} color="text-white" />
                <Kpi label="Margine previsto" value={k.margine_previsto ? `${formatCurrency(k.margine_previsto)}${k.margine_pct ? ` (${k.margine_pct}%)` : ''}` : '—'} color="text-violet-300" />
                <Kpi label="Fatturato atteso" value={formatCurrency(k.fatturato_atteso)} color="text-emerald-300" />
                <Kpi label="Spesa ultimi 12 mesi" value={formatCurrency(k.spesa_ultimo_anno)} color="text-slate-200" />
              </>
            )}
          </div>

          {(tipo !== 'prodotto' || vista.clienti) && (
          <div className="rounded-xl border border-white/[0.07] overflow-hidden">
            <div className="px-4 py-2.5 border-b border-white/[0.06]">
              <h4 className="text-sm font-semibold text-white">
                {tipo === 'prodotto' ? `Clienti che lo compreranno (${righe.length})`
                  : tipo === 'cliente' ? `Cosa proporgli (${righe.length} referenze)`
                    : `Ordine consigliato (${righe.length} articoli)`}
              </h4>
            </div>
            <div className="overflow-x-auto max-h-96 overflow-y-auto">
              <table className="w-full text-sm" data-testid="previsione-tabella">
                <thead className="sticky top-0 bg-[#0b1120]">
                  <tr>
                    {(tipo === 'prodotto'
                      ? ['Cliente', 'Qtà attesa', 'Prezzo medio', 'Fatturato', 'Margine', 'Già ordinato', 'Ultimo acq.']
                      : tipo === 'cliente'
                        ? ['Articolo', 'Qtà attesa', 'Prezzo medio', 'Fatturato', 'Margine', 'Già ordinato']
                        : ['Articolo', 'Domanda prev.', 'Giacenza', 'Da ordinare', 'Prezzo acq.', 'Prz. vendita', 'Margine', 'Valore']
                    ).map((c, i) => (
                      <th key={c} className={cn('px-3 py-2 text-[11px] uppercase tracking-wider text-slate-500 whitespace-nowrap',
                        i === 0 ? 'text-left' : 'text-right')}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {righe.map((r, i) => (
                    <tr key={i} className="border-t border-white/[0.04]" data-testid={`previsione-riga-${i}`}>
                      <td className="px-3 py-2 text-slate-200 max-w-[280px] truncate">{r.nome || r.cliente}</td>
                      {tipo === 'fornitore' ? (
                        <>
                          <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{num(r.domanda_prevista)}</td>
                          <td className="px-3 py-2 text-right text-slate-400 tabular-nums">{num(r.giacenza)}</td>
                          <td className="px-3 py-2 text-right text-white font-semibold tabular-nums">{num(r.da_ordinare)}</td>
                          <td className="px-3 py-2 text-right text-slate-300 tabular-nums">€{(r.prezzo_acquisto || 0).toFixed(2)}</td>
                          <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{r.prezzo_vendita_atteso ? `€${r.prezzo_vendita_atteso.toFixed(2)}` : '—'}</td>
                          <td className={cn('px-3 py-2 text-right font-semibold tabular-nums',
                            r.margine_pct === null ? 'text-slate-600' : r.margine_pct >= 20 ? 'text-emerald-400' : r.margine_pct >= 10 ? 'text-amber-400' : 'text-rose-400')}>
                            {r.margine_pct === null ? '—' : `${r.margine_pct}%`}
                          </td>
                          <td className="px-3 py-2 text-right text-cyan-300 font-semibold tabular-nums">{formatCurrency(r.valore)}</td>
                        </>
                      ) : (
                        <>
                          <td className="px-3 py-2 text-right text-white font-semibold tabular-nums">{num(r.quantita_attesa)}</td>
                          <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{r.prezzo_medio ? `€${r.prezzo_medio.toFixed(2)}` : '—'}</td>
                          <td className="px-3 py-2 text-right text-emerald-300 font-semibold tabular-nums">{formatCurrency(r.fatturato_atteso)}</td>
                          <td className={cn('px-3 py-2 text-right font-semibold tabular-nums',
                            r.margine_pct === null || r.margine_pct === undefined ? 'text-slate-600'
                              : r.margine_pct >= 20 ? 'text-emerald-400' : r.margine_pct >= 10 ? 'text-amber-400' : 'text-rose-400')}>
                            {r.margine_pct === null || r.margine_pct === undefined ? '—' : `${r.margine_pct}%`}
                          </td>
                          <td className={cn('px-3 py-2 text-right tabular-nums',
                            r.gia_ordinato > 0 ? 'text-slate-400' : 'text-amber-300 font-medium')}>
                            {r.gia_ordinato > 0 ? `${num(r.gia_ordinato)} pz` : 'da proporre'}
                          </td>
                          {tipo === 'prodotto' && (
                            <td className="px-3 py-2 text-right text-slate-400 tabular-nums">{dmy(r.ultimo_acquisto)}</td>
                          )}
                        </>
                      )}
                    </tr>
                  ))}
                  {righe.length === 0 && (
                    <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500 text-xs">
                      Nessun dato nello stesso periodo dell'anno scorso
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
          )}

          {tipo === 'prodotto' && vista.fornitori && (data.righe_fornitori || []).length > 0 && (
            <div className="rounded-xl border border-white/[0.07] overflow-hidden">
              <div className="px-4 py-2.5 border-b border-white/[0.06]">
                <h4 className="text-sm font-semibold text-white">Fornitori da cui comprarlo ({data.righe_fornitori.length})</h4>
                <p className="text-[11px] text-slate-500 mt-0.5">Ruolo in base agli acquisti degli ultimi 12 mesi e previsione di quanto ordinargli</p>
              </div>
              <div className="overflow-x-auto max-h-80 overflow-y-auto">
                <table className="w-full text-sm" data-testid="previsione-tabella-fornitori">
                  <thead className="sticky top-0 bg-[#0b1120]">
                    <tr>
                      {['Fornitore', 'Ruolo', 'Articoli', 'Prezzo medio', 'Domanda prev.', 'Da ordinare', 'Valore', 'Ultimo acq.'].map((c, i) => (
                        <th key={c} className={cn('px-3 py-2 text-[11px] uppercase tracking-wider text-slate-500 whitespace-nowrap',
                          i === 0 ? 'text-left' : 'text-right')}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.righe_fornitori.map((r, i) => (
                      <tr key={r.nome} className="border-t border-white/[0.04]" data-testid={`previsione-fornitore-riga-${i}`}>
                        <td className="px-3 py-2 text-slate-200 max-w-[220px] truncate">{r.nome}</td>
                        <td className="px-3 py-2 text-right">
                          <span className={cn('text-[10px] font-semibold px-2 py-0.5 rounded-md border whitespace-nowrap',
                            r.ruolo === 'primario' ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                              : r.ruolo === 'secondario' ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                                : 'bg-white/[0.05] text-slate-400 border-white/10')}>
                            {r.ruolo}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right text-slate-400 tabular-nums">{r.prodotti_trattati}</td>
                        <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{r.prezzo_medio ? `€${r.prezzo_medio.toFixed(2)}` : '—'}</td>
                        <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{num(r.domanda_prevista)}</td>
                        <td className="px-3 py-2 text-right text-white font-semibold tabular-nums">{r.da_ordinare > 0 ? num(r.da_ordinare) : '—'}</td>
                        <td className="px-3 py-2 text-right text-cyan-300 font-semibold tabular-nums">{r.valore_ordine > 0 ? formatCurrency(r.valore_ordine) : '—'}</td>
                        <td className="px-3 py-2 text-right text-slate-400 tabular-nums">{dmy(r.ultimo_acquisto)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {tipo === 'prodotto' && (data.righe_prodotti || []).length > 1 && (
            <div className="rounded-xl border border-white/[0.07] overflow-hidden">
              <div className="px-4 py-2.5 border-b border-white/[0.06]">
                <h4 className="text-sm font-semibold text-white">Riepilogo per prodotto ({data.righe_prodotti.length})</h4>
              </div>
              <div className="overflow-x-auto max-h-80 overflow-y-auto">
                <table className="w-full text-sm" data-testid="previsione-tabella-prodotti">
                  <thead className="sticky top-0 bg-[#0b1120]">
                    <tr>
                      {['Prodotto', 'Domanda prev.', 'Giacenza', 'Da ordinare', 'Prezzo acq.', 'Margine', 'Fatturato', 'Fornitore'].map((c, i) => (
                        <th key={c} className={cn('px-3 py-2 text-[11px] uppercase tracking-wider text-slate-500 whitespace-nowrap',
                          i === 0 || i === 7 ? 'text-left' : 'text-right')}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.righe_prodotti.map((r, i) => (
                      <tr key={r.nome} className="border-t border-white/[0.04]" data-testid={`previsione-prodotto-riga-${i}`}>
                        <td className="px-3 py-2 text-slate-200 max-w-[240px] truncate">{r.nome}</td>
                        <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{num(r.domanda_prevista)}</td>
                        <td className="px-3 py-2 text-right text-slate-400 tabular-nums">{num(r.giacenza)}</td>
                        <td className="px-3 py-2 text-right text-white font-semibold tabular-nums">{num(r.da_ordinare)}</td>
                        <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{r.prezzo_acquisto ? `€${r.prezzo_acquisto.toFixed(2)}` : '—'}</td>
                        <td className={cn('px-3 py-2 text-right font-semibold tabular-nums',
                          r.margine_pct === null ? 'text-slate-600' : r.margine_pct >= 20 ? 'text-emerald-400' : r.margine_pct >= 10 ? 'text-amber-400' : 'text-rose-400')}>
                          {r.margine_pct === null ? '—' : `${r.margine_pct}%`}
                        </td>
                        <td className="px-3 py-2 text-right text-emerald-300 tabular-nums">{formatCurrency(r.fatturato_atteso)}</td>
                        <td className="px-3 py-2 text-left text-slate-400 max-w-[160px] truncate">{r.fornitore || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
