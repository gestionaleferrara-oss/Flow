import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  ShoppingCart, TrendingUp, ChevronDown, X as XIcon, Target, Truck, Users,
  Lightbulb, CalendarClock, Trophy,
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const GIORNI = [7, 15, 30, 60, 90];
const num = (v) => (v ?? 0).toLocaleString('it-IT');
const dmy = (s) => (s ? s.split('-').reverse().join('/') : '—');

const AZIONI = {
  'CHIAMA ORA': 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  'CLIENTE FERMO': 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  PROPONI: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
  'IN LINEA': 'bg-white/[0.05] text-slate-400 border-white/10',
};

function DettaglioDrawer({ ctx, giorni, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const r = await axios.get(`${API}/ottimizzazione/piano/articolo`, {
          params: { prodotto: ctx.prodotto, cliente: ctx.cliente || undefined, giorni },
        });
        setData(r.data);
      } catch (e) {
        setData({ spiegazione: 'Non è stato possibile caricare il dettaglio.', tabelle: [] });
      } finally { setLoading(false); }
    })();
  }, [ctx, giorni]);

  return (
    <div className="fixed inset-0 z-[80] flex items-start justify-center p-3 sm:p-6 bg-black/70 backdrop-blur-sm overflow-y-auto"
      onClick={onClose} data-testid="ott-dettaglio-drawer">
      <div onClick={(e) => e.stopPropagation()}
        className="w-full max-w-5xl rounded-2xl border border-white/[0.08] bg-[#0b1120] shadow-2xl my-4">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06] sticky top-0 bg-[#0b1120] rounded-t-2xl z-10">
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-white truncate">{data?.titolo || ctx.titolo}</h3>
            <p className="text-xs text-slate-500">Vendite per cliente</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
            data-testid="ott-dettaglio-close">
            <XIcon className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {loading ? <LoadingSpinner /> : (
            <>
              <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/[0.05] p-4">
                <p className="text-sm text-slate-200 leading-relaxed" data-testid="ott-spiegazione">{data.spiegazione}</p>
                {data.azione && (
                  <p className="mt-3 text-sm text-emerald-300 font-medium flex items-start gap-2">
                    <Target className="w-4 h-4 mt-0.5 shrink-0" /> {data.azione}
                  </p>
                )}
              </div>
              {(data.tabelle || []).map((t, i) => (
                <div key={i} className="rounded-xl border border-white/[0.07] overflow-hidden" data-testid={`ott-tabella-${i}`}>
                  <div className="px-4 py-2.5 border-b border-white/[0.06]">
                    <h4 className="text-sm font-semibold text-white">{t.titolo}</h4>
                  </div>
                  <div className="overflow-x-auto max-h-80 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-[#0b1120]">
                        <tr>
                          {t.colonne.map((c, ci) => (
                            <th key={c} className={cn('px-3 py-2 text-[11px] uppercase tracking-wider text-slate-500 whitespace-nowrap',
                              ci === 0 ? 'text-left' : 'text-right')}>{c}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {t.righe.map((r, ri) => (
                          <tr key={ri} className="border-t border-white/[0.04]">
                            {r.map((cell, ci) => (
                              <td key={ci} className={cn('px-3 py-2 tabular-nums',
                                ci === 0 ? 'text-left text-slate-200 max-w-[260px] truncate' : 'text-right text-slate-300')}>{cell}</td>
                            ))}
                          </tr>
                        ))}
                        {t.righe.length === 0 && (
                          <tr><td colSpan={t.colonne.length} className="px-3 py-5 text-center text-slate-500 text-xs">Nessun dato</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Kpi({ label, value, color }) {
  return (
    <div className="rounded-xl border border-white/[0.07] bg-black/20 p-3">
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={cn('text-lg font-bold tabular-nums mt-1', color)}>{value}</div>
    </div>
  );
}

function OrdineAcquisto({ o, idx, onArticolo }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-white/[0.07] bg-white/[0.015] overflow-hidden" data-testid={`ordine-acquisto-${idx}`}>
      <button onClick={() => setOpen(!open)} data-testid={`ordine-acquisto-${idx}-toggle`}
        className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-white/[0.02] transition-colors">
        <div className="w-9 h-9 rounded-lg border border-cyan-500/20 bg-cyan-500/[0.06] text-cyan-300 flex items-center justify-center shrink-0">
          <Truck className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-white truncate">{o.fornitore}</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            {o.prodotti_n} articoli · margine previsto {o.margine_pct ?? '—'}%
          </p>
        </div>
        <div className="text-right shrink-0">
          <div className="text-base font-bold tabular-nums text-cyan-300">{formatCurrency(o.valore)}</div>
          <div className="text-[11px] text-slate-500">ordine consigliato</div>
        </div>
        <ChevronDown className={cn('w-4 h-4 text-slate-500 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="overflow-x-auto border-t border-white/[0.06]">
          <table className="w-full text-sm">
            <thead>
              <tr>
                {['Articolo', 'Domanda prev.', 'Giacenza', 'Copertura gg', 'Da ordinare', 'Prezzo', 'Prz. vendita', 'Margine', 'Valore'].map((c, i) => (
                  <th key={c} className={cn('px-2 py-2 text-[11px] uppercase tracking-wider text-slate-500 whitespace-nowrap',
                    i === 0 ? 'text-left' : 'text-right')}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {o.articoli.map((a, i) => (
                <tr key={a.prodotto} onClick={() => onArticolo(a)}
                  className="border-t border-white/[0.04] cursor-pointer hover:bg-cyan-500/[0.07] transition-colors"
                  data-testid={`ordine-acquisto-${idx}-row-${i}`}>
                  <td className="px-2 py-2 text-slate-200 max-w-[180px] truncate">{a.prodotto}</td>
                  <td className="px-2 py-2 text-right text-slate-300 tabular-nums">{num(a.domanda_prevista)}</td>
                  <td className="px-2 py-2 text-right text-slate-400 tabular-nums">{num(a.giacenza)}</td>
                  <td className="px-2 py-2 text-right text-slate-400 tabular-nums">{a.copertura_giorni ?? '—'}</td>
                  <td className="px-2 py-2 text-right text-white font-semibold tabular-nums">{num(a.da_ordinare)}</td>
                  <td className="px-2 py-2 text-right text-slate-300 tabular-nums">{a.prezzo_acquisto ? `€${a.prezzo_acquisto.toFixed(2)}` : '—'}</td>
                  <td className="px-2 py-2 text-right text-slate-300 tabular-nums">{a.prezzo_vendita_atteso ? `€${a.prezzo_vendita_atteso.toFixed(2)}` : '—'}</td>
                  <td className={cn('px-2 py-2 text-right font-semibold tabular-nums',
                    a.margine_pct === null ? 'text-slate-600' : a.margine_pct >= 20 ? 'text-emerald-400'
                      : a.margine_pct >= 10 ? 'text-amber-400' : 'text-rose-400')}>
                    {a.margine_pct === null ? '—' : `${a.margine_pct}%`}
                  </td>
                  <td className="px-2 py-2 text-right text-cyan-300 font-semibold tabular-nums">{formatCurrency(a.valore)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ProposteCliente({ o, idx, onArticolo }) {
  const [open, setOpen] = useState(false);
  const [soloDaProporre, setSoloDaProporre] = useState(false);
  const articoli = soloDaProporre ? o.articoli.filter((a) => !a.gia_ordinato) : o.articoli;
  return (
    <div className="rounded-xl border border-white/[0.07] bg-white/[0.015] overflow-hidden" data-testid={`proposta-cliente-${idx}`}>
      <button onClick={() => setOpen(!open)} data-testid={`proposta-cliente-${idx}-toggle`}
        className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-white/[0.02] transition-colors">
        <div className="w-9 h-9 rounded-lg border border-emerald-500/20 bg-emerald-500/[0.06] text-emerald-300 flex items-center justify-center shrink-0">
          <Users className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-white truncate">{o.cliente}</h3>
            <span className={cn('px-2 py-0.5 rounded-md text-[10px] font-semibold border whitespace-nowrap',
              AZIONI[o.azione] || 'bg-white/[0.05] text-slate-400 border-white/10')}>{o.azione}</span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            {o.prodotti_n} referenze attese ·{' '}
            <span className="text-amber-300 font-medium">{o.prodotti_mancanti} da proporre</span>
            {' '}· ultimo ordine {dmy(o.ultimo_ordine)}
          </p>
        </div>
        <div className="text-right shrink-0">
          <div className="text-base font-bold tabular-nums text-emerald-300">{formatCurrency(o.valore_atteso)}</div>
          <div className="text-[11px] text-slate-500">proposta d'ordine</div>
        </div>
        <ChevronDown className={cn('w-4 h-4 text-slate-500 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="border-t border-white/[0.06]">
          <div className="flex items-center gap-3 px-3 py-2 text-[11px] text-slate-400 flex-wrap">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-amber-400/80" /> da proporre (non ancora ordinato)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-slate-600" /> già ordinato
            </span>
            <button onClick={() => setSoloDaProporre(!soloDaProporre)}
              data-testid={`proposta-cliente-${idx}-filtro`}
              className={cn('ml-auto px-2.5 py-1 rounded-md border text-[11px] font-medium transition-colors',
                soloDaProporre ? 'bg-amber-500/15 border-amber-500/30 text-amber-300'
                  : 'bg-white/[0.02] border-white/[0.08] text-slate-400 hover:text-slate-200')}>
              {soloDaProporre ? 'Mostra tutte' : 'Solo da proporre'}
            </button>
          </div>
          <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                {['Articolo', 'Qtà attesa', 'Prezzo', 'Valore'].map((c, i) => (
                  <th key={c} className={cn('px-3 py-2 text-[11px] uppercase tracking-wider text-slate-500 whitespace-nowrap',
                    i === 0 ? 'text-left' : 'text-right')}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {articoli.map((a, i) => (
                <tr key={a.prodotto} onClick={() => onArticolo(a)}
                  className={cn('border-t border-white/[0.04] cursor-pointer transition-colors',
                    a.gia_ordinato ? 'opacity-45 hover:bg-white/[0.03]' : 'bg-amber-500/[0.05] hover:bg-amber-500/[0.12]')}
                  data-testid={`proposta-cliente-${idx}-row-${i}`}>
                  <td className={cn('px-3 py-2 max-w-[300px] truncate border-l-2',
                    a.gia_ordinato ? 'border-l-slate-600 text-slate-400' : 'border-l-amber-400 text-white font-medium')}>
                    {a.prodotto}
                  </td>
                  <td className="px-3 py-2 text-right text-white font-semibold tabular-nums">{num(a.quantita_attesa)}</td>
                  <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{a.prezzo_atteso ? `€${a.prezzo_atteso.toFixed(2)}` : '—'}</td>
                  <td className={cn('px-3 py-2 text-right font-semibold tabular-nums',
                    a.gia_ordinato ? 'text-slate-400' : 'text-amber-300')}>{formatCurrency(a.valore_atteso)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Suggerimenti({ lista, children }) {
  if (!lista?.length && !children) return null;
  return (
    <div className="mt-8" data-testid="suggerimenti">
      <div className="flex items-center gap-2 mb-3">
        <Lightbulb className="w-4 h-4 text-amber-300" />
        <h2 className="text-base font-semibold text-white">Suggerimenti</h2>
      </div>
      <div className="grid gap-3 lg:grid-cols-2 items-start">
        {(lista || []).map((s, i) => (
          <div key={s.id} className="rounded-xl border border-white/[0.07] bg-white/[0.015] overflow-hidden"
            data-testid={`suggerimento-${s.id}`}>
            <div className="px-4 py-3 border-b border-white/[0.06] flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-white">{s.titolo}</h3>
                <p className="text-xs text-slate-400 mt-0.5">{s.descrizione}</p>
              </div>
              <div className="text-sm font-bold text-amber-300 tabular-nums shrink-0">{formatCurrency(s.valore)}</div>
            </div>
            <div className="divide-y divide-white/[0.04] max-h-72 overflow-y-auto">
              {s.voci.map((v, vi) => (
                <div key={vi} className="px-4 py-2 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm text-slate-200 truncate">{v.nome}</div>
                    <div className="text-[11px] text-slate-500 truncate">{v.dettaglio}</div>
                  </div>
                  <div className="text-sm text-slate-300 tabular-nums shrink-0">{formatCurrency(v.valore)}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
        {children}
      </div>
    </div>
  );
}

function TopProdotti({ lista, periodo, onProdotto }) {
  if (!lista?.length) return null;
  const max = lista[0].quantita || 1;
  return (
    <div className="rounded-xl border border-violet-500/20 bg-violet-500/[0.03] overflow-hidden" data-testid="top-prodotti">
      <div className="px-4 py-3 border-b border-white/[0.06] flex items-start gap-2.5">
        <Trophy className="w-4 h-4 text-violet-300 mt-0.5 shrink-0" />
        <div>
          <h2 className="text-sm font-semibold text-white">Prodotti più consumati</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Classifica per quantità venduta dal {dmy(periodo.storico_start)} al {dmy(periodo.storico_end)} (anno scorso)
          </p>
        </div>
      </div>
      <div className="divide-y divide-white/[0.04] max-h-[420px] overflow-y-auto">
        {lista.map((p, i) => (
          <button key={p.prodotto} onClick={() => onProdotto(p)} data-testid={`top-prodotto-${i}`}
            className="w-full text-left px-4 py-2.5 flex items-center gap-3 hover:bg-violet-500/[0.06] transition-colors">
            <span className="w-6 text-xs font-bold text-violet-300/80 tabular-nums shrink-0">{i + 1}</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-slate-200 truncate">{p.prodotto}</div>
              <div className="mt-1 h-1 rounded-full bg-white/[0.06] overflow-hidden">
                <div className="h-full rounded-full bg-violet-400/70" style={{ width: `${(p.quantita / max) * 100}%` }} />
              </div>
            </div>
            <div className="text-right shrink-0">
              <div className="text-sm font-bold text-white tabular-nums">{num(p.quantita)} <span className="text-[10px] font-normal text-slate-500">pz</span></div>
              <div className="text-[11px] text-slate-500 tabular-nums">{formatCurrency(p.fatturato)}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Ottimizzazione() {
  const [tab, setTab] = useState('acquisti');
  const [giorni, setGiorni] = useState(() => Number(localStorage.getItem('flow_piano_giorni')) || 30);
  const [piano, setPiano] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dettaglio, setDettaglio] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/ottimizzazione/piano`, { params: { tipo: tab, giorni } });
      setPiano(r.data);
    } catch (e) { console.error(e); setPiano(null); } finally { setLoading(false); }
  }, [tab, giorni]);

  useEffect(() => { load(); }, [load]);

  const acquisti = tab === 'acquisti';
  const t = piano?.totali || {};
  const per = piano?.periodo;

  return (
    <PageWrapper>
      <PageHeader
        title="Ottimizzazione"
        subtitle="Cosa ordinare e a chi vendere nei prossimi giorni, sulla base del venduto reale dello stesso periodo dell'anno scorso"
      />

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="flex gap-1 p-1 rounded-xl bg-white/[0.03] border border-white/[0.06] w-fit">
          {[{ id: 'acquisti', label: 'Acquisti', icon: ShoppingCart },
            { id: 'vendite', label: 'Vendite', icon: TrendingUp }].map((x) => (
            <button key={x.id} onClick={() => { setTab(x.id); setPiano(null); }}
              data-testid={`ottimizzazione-tab-${x.id}`}
              className={cn('flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                tab === x.id ? 'bg-cyan-500/15 text-cyan-300' : 'text-slate-400 hover:text-slate-200')}>
              <x.icon className="w-4 h-4" /> {x.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5 ml-auto">
          <span className="text-xs text-slate-400 mr-1">Previsione prossimi</span>
          {GIORNI.map((g) => (
            <button key={g} onClick={() => { setGiorni(g); localStorage.setItem('flow_piano_giorni', String(g)); }}
              data-testid={`piano-giorni-${g}`}
              className={cn('px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
                giorni === g ? 'bg-cyan-500/15 border-cyan-500/30 text-cyan-300'
                  : 'bg-white/[0.02] border-white/[0.07] text-slate-400 hover:text-slate-200')}>
              {g} gg
            </button>
          ))}
        </div>
      </div>

      {loading && !piano ? <LoadingSpinner /> : piano && (
        <>
          <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/[0.03] overflow-hidden mb-6" data-testid="piano-azione">
            <div className="px-4 py-3.5 border-b border-white/[0.06] flex items-start gap-2.5">
              <CalendarClock className="w-4 h-4 text-cyan-300 mt-0.5 shrink-0" />
              <div>
                <h2 className="text-sm font-semibold text-white">
                  {acquisti ? 'Ordini da fare' : 'Ordini da proporre'} dal {dmy(per.futuro_start)} al {dmy(per.futuro_end)}
                </h2>
                <p className="text-xs text-slate-400 mt-0.5" data-testid="piano-periodi">
                  Previsione calcolata sul venduto reale dal {dmy(per.storico_start)} al {dmy(per.storico_end)} (stessi giorni dell'anno scorso)
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 p-4">
              {acquisti ? (
                <>
                  <Kpi label="Fornitori da contattare" value={`${t.fornitori || 0}`} color="text-cyan-300" />
                  <Kpi label="Articoli da ordinare" value={`${t.prodotti || 0}`} color="text-emerald-300" />
                  <Kpi label="Valore ordini" value={formatCurrency(t.valore_ordini)} color="text-white" />
                  <Kpi label="Margine previsto" value={formatCurrency(t.margine_previsto)} color="text-violet-300" />
                </>
              ) : (
                <>
                  <Kpi label="Clienti da contattare" value={`${t.da_chiamare || 0} di ${t.clienti || 0}`} color="text-cyan-300" />
                  <Kpi label="Fatturato atteso" value={formatCurrency(t.valore_atteso)} color="text-white" />
                  <Kpi label="Margine previsto" value={formatCurrency(t.margine_previsto)} color="text-violet-300" />
                  <Kpi label="Referenze da proporre" value={formatCurrency(t.valore_mancante)} color="text-amber-300" />
                </>
              )}
            </div>
          </div>

          <div>
            <p className="text-xs text-slate-500 mb-3">
              {acquisti
                ? 'Un blocco per fornitore: ordine completo con tutti gli articoli che si consumano nella finestra. Clicca una riga per lo storico.'
                : `Un blocco per cliente: cosa proporre in base a quanto comprato l'anno scorso. In giallo le referenze che NON ha ancora ordinato negli ultimi ${giorni} giorni (${dmy(per.recenti_start)} → ${dmy(per.recenti_end)}), in grigio quelle già ordinate.`}
            </p>
            <div className="space-y-3">
              {(piano.ordini || []).map((o, i) => acquisti ? (
                <OrdineAcquisto key={o.fornitore} o={o} idx={i}
                  onArticolo={(a) => setDettaglio({ prodotto: a.prodotto, titolo: a.prodotto })} />
              ) : (
                <ProposteCliente key={o.cliente} o={o} idx={i}
                  onArticolo={(a) => setDettaglio({ cliente: o.cliente, prodotto: a.prodotto, titolo: `${a.prodotto} — ${o.cliente}` })} />
              ))}
              {!(piano.ordini || []).length && (
                <div className="rounded-xl border border-white/[0.07] bg-white/[0.015] px-4 py-8 text-center text-sm text-slate-500">
                  Nessuna azione necessaria in questa finestra
                </div>
              )}
            </div>
          </div>

          <Suggerimenti lista={piano.suggerimenti}>
            <TopProdotti lista={piano.top_prodotti} periodo={per}
              onProdotto={(p) => setDettaglio({ prodotto: p.prodotto, titolo: p.prodotto })} />
          </Suggerimenti>
        </>
      )}

      {dettaglio && <DettaglioDrawer ctx={dettaglio} giorni={giorni} onClose={() => setDettaglio(null)} />}
    </PageWrapper>
  );
}
