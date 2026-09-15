import { useState, useEffect } from 'react';
import axios from 'axios';
import { X as XIcon } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const SchedaProdotto = ({ prodotto, giorni = 30, onClose }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let vivo = true;
    (async () => {
      setLoading(true);
      try {
        const r = await axios.get(`${API}/ottimizzazione/piano/articolo`, {
          params: { prodotto, giorni },
        });
        if (vivo) setData(r.data);
      } catch (e) {
        if (vivo) setData({ spiegazione: 'Non è stato possibile caricare la scheda.', tabelle: [] });
      } finally { if (vivo) setLoading(false); }
    })();
    return () => { vivo = false; };
  }, [prodotto, giorni]);

  return (
    <div className="fixed inset-0 z-[90] flex items-start justify-center p-3 sm:p-6 bg-black/70 backdrop-blur-sm overflow-y-auto"
      onClick={onClose} data-testid="scheda-prodotto">
      <div onClick={(e) => e.stopPropagation()}
        className="w-full max-w-5xl rounded-2xl border border-white/[0.08] bg-[#0b1120] shadow-2xl my-4">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06] sticky top-0 bg-[#0b1120] rounded-t-2xl z-10">
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-white truncate">{data?.titolo || prodotto}</h3>
            <p className="text-xs text-slate-500">Scheda prodotto: clienti, andamento mensile e fornitori</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
            data-testid="scheda-prodotto-close">
            <XIcon className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {loading ? <LoadingSpinner /> : (
            <>
              <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/[0.05] p-4">
                <p className="text-sm text-slate-200 leading-relaxed" data-testid="scheda-prodotto-sintesi">
                  {data.spiegazione}
                </p>
              </div>
              {(data.tabelle || []).map((t, i) => (
                <div key={i} className="rounded-xl border border-white/[0.07] overflow-hidden"
                  data-testid={`scheda-prodotto-tabella-${i}`}>
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
                                ci === 0 ? 'text-left text-slate-200 max-w-[260px] truncate' : 'text-right text-slate-300',
                                typeof cell === 'string' && cell.startsWith('-') && cell.endsWith('%') ? 'text-rose-300' : '',
                                typeof cell === 'string' && cell.startsWith('+') && cell.endsWith('%') ? 'text-emerald-300' : '',
                                cell === 'fermo' ? 'text-rose-300' : cell === 'nuovo' ? 'text-cyan-300' : '',
                                cell === 'primario' ? 'text-emerald-300' : '')}>{cell}</td>
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
};
