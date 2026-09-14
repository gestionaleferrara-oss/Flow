import { useState, useEffect, Fragment } from 'react';
import axios from 'axios';
import { ChevronRight, Loader2, Package } from 'lucide-react';
import { formatCurrency, cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const margineClass = (v) => v === null || v === undefined
  ? 'text-slate-600'
  : v >= 20 ? 'text-emerald-400' : v >= 8 ? 'text-amber-400' : 'text-rose-400';

const num = (v) => (v ?? 0).toLocaleString('it-IT');
const eur = (v) => (v === null || v === undefined ? '—' : `€${v.toFixed(2)}`);

/** Lotti FIFO di un prodotto: clic su un lotto -> vendite collegate */
export const LottiPanel = ({ prodotto, lotti: lottiProp, titolo = 'Lotti di acquisto (FIFO)' }) => {
  const [lotti, setLotti] = useState(lottiProp || null);
  const [loading, setLoading] = useState(!lottiProp);
  const [selected, setSelected] = useState(null);
  const [vendite, setVendite] = useState(null);
  const [venditeLoading, setVenditeLoading] = useState(false);

  useEffect(() => {
    if (lottiProp) { setLotti(lottiProp); return; }
    let alive = true;
    (async () => {
      setLoading(true);
      try {
        const r = await axios.get(`${API}/fifo/lotti`, { params: { prodotto, limit: 100 } });
        if (alive) setLotti(r.data.lotti || []);
      } catch (e) { if (alive) setLotti([]); } finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [prodotto, lottiProp]);

  const apriLotto = async (lot) => {
    if (selected === lot.lotto_id) { setSelected(null); setVendite(null); return; }
    setSelected(lot.lotto_id);
    setVenditeLoading(true);
    setVendite(null);
    try {
      const r = await axios.get(`${API}/fifo/lotto/vendite`, { params: { lotto_id: lot.lotto_id } });
      setVendite(r.data);
    } catch (e) { setVendite({ vendite: [], totali: {} }); } finally { setVenditeLoading(false); }
  };

  return (
    <div className="rounded-xl border border-white/[0.07] overflow-hidden" data-testid="lotti-panel">
      <div className="px-4 py-2.5 border-b border-white/[0.06] flex items-center justify-between">
        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
          <Package className="w-4 h-4 text-amber-300" /> {titolo}
        </h4>
        <span className="text-[11px] text-slate-500">clicca un lotto per vedere le vendite collegate</span>
      </div>

      {loading ? (
        <div className="p-6 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-slate-500" /></div>
      ) : (
        <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
          <table className="w-full text-sm" data-testid="lotti-table">
            <thead className="sticky top-0 bg-[#0b1120] z-10">
              <tr>
                {['Acquisto', 'Fornitore', 'Qtà', 'Costo/u', 'Venduto', 'Residuo', 'Esaurito il', 'Prz. vendita', 'Margine'].map((c, i) => (
                  <th key={c} className={cn('px-3 py-2 text-[11px] uppercase tracking-wider text-slate-500 whitespace-nowrap',
                    i <= 1 ? 'text-left' : 'text-right')}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(lotti || []).map((l) => (
                <Fragment key={l.lotto_id}>
                  <tr
                    key={l.lotto_id}
                    onClick={() => apriLotto(l)}                    className={cn('border-t border-white/[0.04] cursor-pointer transition-colors',
                      selected === l.lotto_id ? 'bg-amber-500/[0.09]' : 'hover:bg-amber-500/[0.06]')}
                    data-testid={`lotto-row-${l.lotto_id}`}
                  >
                    <td className="px-3 py-2 text-slate-200 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1">
                        <ChevronRight className={cn('w-3 h-3 transition-transform', selected === l.lotto_id && 'rotate-90')} />
                        {l.data_acquisto}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-300 max-w-[200px] truncate">{l.fornitore || '—'}</td>
                    <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{num(l.quantita)}</td>
                    <td className="px-3 py-2 text-right text-slate-300 tabular-nums">
                      {eur(l.prezzo_acquisto)}{l.prezzo_stimato && <span className="text-amber-400" title="prezzo stimato">*</span>}
                    </td>
                    <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{num(l.quantita_venduta)}</td>
                    <td className="px-3 py-2 text-right text-slate-400 tabular-nums">{num(l.residuo)}</td>
                    <td className="px-3 py-2 text-right text-slate-400 whitespace-nowrap">{l.data_esaurimento || 'in corso'}</td>
                    <td className="px-3 py-2 text-right text-slate-300 tabular-nums">{eur(l.prezzo_vendita_medio)}</td>
                    <td className={cn('px-3 py-2 text-right font-semibold tabular-nums', margineClass(l.margine_pct))}>
                      {l.margine_pct === null || l.margine_pct === undefined ? '—' : `${l.margine_pct}%`}
                    </td>
                  </tr>
                  {selected === l.lotto_id && (
                    <tr key={`${l.lotto_id}-det`} className="bg-black/30">
                      <td colSpan={9} className="px-3 py-3">
                        {venditeLoading ? (
                          <div className="flex items-center gap-2 text-xs text-slate-400">
                            <Loader2 className="w-3.5 h-3.5 animate-spin" /> carico le vendite del lotto...                          </div>
                        ) : (
                          <div data-testid="lotto-vendite">
                            <div className="flex flex-wrap gap-4 text-xs text-slate-400 mb-2">
                              <span>Vendite: <b className="text-slate-200">{vendite?.totali?.n_vendite ?? 0}</b></span>
                              <span>Qtà: <b className="text-slate-200">{num(vendite?.totali?.quantita)}</b></span>
                              <span>Ricavo: <b className="text-slate-200">{formatCurrency(vendite?.totali?.fatturato || 0)}</b></span>
                              <span>Margine: <b className={margineClass(vendite?.totali?.margine_pct)}>
                                {formatCurrency(vendite?.totali?.margine || 0)}
                                {vendite?.totali?.margine_pct !== null && vendite?.totali?.margine_pct !== undefined
                                  ? ` (${vendite.totali.margine_pct}%)` : ''}
                              </b></span>
                            </div>
                            <table className="w-full text-xs">
                              <thead>
                                <tr className="text-slate-500">
                                  {['Data', 'Cliente', 'Qtà', 'Prz. vendita', 'Costo/u', 'Margine %'].map((c, i) => (
                                    <th key={c} className={cn('px-2 py-1 font-medium', i <= 1 ? 'text-left' : 'text-right')}>{c}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {(vendite?.vendite || []).map((v, i) => (
                                  <tr key={i} className="border-t border-white/[0.04]">
                                    <td className="px-2 py-1 text-slate-300 whitespace-nowrap">{v.data}</td>
                                    <td className="px-2 py-1 text-slate-300 max-w-[220px] truncate">{v.cliente}</td>
                                    <td className="px-2 py-1 text-right text-slate-300 tabular-nums">{num(v.quantita)}</td>
                                    <td className="px-2 py-1 text-right text-slate-300 tabular-nums">{eur(v.prezzo_vendita)}</td>
                                    <td className="px-2 py-1 text-right text-slate-400 tabular-nums">{eur(v.costo_unitario)}</td>
                                    <td className={cn('px-2 py-1 text-right font-semibold tabular-nums', margineClass(v.margine_pct))}>
                                      {v.margine_pct === null ? '—' : `${v.margine_pct}%`}
                                    </td>
                                  </tr>
                                ))}
                                {(vendite?.vendite || []).length === 0 && (
                                  <tr><td colSpan={6} className="px-2 py-3 text-center text-slate-500">
                                    Nessuna vendita collegata a questo lotto
                                  </td></tr>
                                )}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {(lotti || []).length === 0 && (
                <tr><td colSpan={9} className="px-3 py-6 text-center text-slate-500 text-xs">
                  Nessun lotto di acquisto per questo prodotto
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default LottiPanel;
