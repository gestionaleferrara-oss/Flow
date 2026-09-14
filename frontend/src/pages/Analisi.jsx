import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import {
  Package, Truck, ArrowUpRight, ArrowDownRight, X, ChevronUp, ChevronDown,
  Search, Euro, Percent, TrendingDown, Scale, FileDown, FileText,
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import LoadingSpinner from '@/components/LoadingSpinner';
import { LottiPanel } from '@/components/LottiPanel';
import { formatCurrency, cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PRESETS = [
  { id: 'auto', label: 'Ultimo mese con dati' },
  { id: 'currentMonth', label: 'Questo mese' },
  { id: 'lastMonth', label: 'Mese prec.' },
  { id: 'last30', label: '30 giorni' },
  { id: 'last90', label: '90 giorni' },
  { id: 'year', label: 'Anno corrente' },
];

const iso = (d) => d.toISOString().split('T')[0];

function presetRange(id) {
  const t = new Date();
  switch (id) {
    case 'auto':
      return ['', ''];
    case 'currentMonth':
      return [iso(new Date(t.getFullYear(), t.getMonth(), 1)), iso(t)];
    case 'lastMonth':
      return [iso(new Date(t.getFullYear(), t.getMonth() - 1, 1)), iso(new Date(t.getFullYear(), t.getMonth(), 0))];
    case 'last30': {
      const s = new Date(t); s.setDate(s.getDate() - 30); return [iso(s), iso(t)];
    }
    case 'last90': {
      const s = new Date(t); s.setDate(s.getDate() - 90); return [iso(s), iso(t)];
    }
    case 'year':
      return [iso(new Date(t.getFullYear(), 0, 1)), iso(t)];
    default:
      return ['', ''];
  }
}

function Delta({ value, testid }) {
  if (value === null || value === undefined) return <span className="text-slate-600">—</span>;
  const up = value >= 0;
  return (
    <span
      className={cn('inline-flex items-center gap-0.5 font-semibold tabular-nums',
        up ? 'text-emerald-400' : 'text-rose-400')}
      data-testid={testid}
    >
      {up ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
      {up ? '+' : ''}{value.toFixed(1)}%
    </span>
  );
}

function Kpi({ label, value, sub, accent = 'cyan', icon: Icon, testid }) {
  const colors = {
    cyan: 'text-cyan-300 border-cyan-500/20 bg-cyan-500/[0.06]',
    emerald: 'text-emerald-300 border-emerald-500/20 bg-emerald-500/[0.06]',
    amber: 'text-amber-300 border-amber-500/20 bg-amber-500/[0.06]',
    violet: 'text-violet-300 border-violet-500/20 bg-violet-500/[0.06]',
  }[accent];
  return (
    <div className={cn('rounded-xl border p-4', colors)} data-testid={testid}>
      <div className="flex items-center gap-2 mb-2">
        {Icon && <Icon className="w-3.5 h-3.5 opacity-70" />}
        <span className="text-[11px] uppercase tracking-wider opacity-70">{label}</span>
      </div>
      <div className="text-xl font-bold text-white tabular-nums">{value}</div>
      {sub && <div className="text-xs mt-1 opacity-80">{sub}</div>}
    </div>
  );
}

function SortHeader({ label, field, sort, setSort, align = 'right' }) {
  const active = sort.field === field;
  return (
    <th
      onClick={() => setSort({ field, dir: active && sort.dir === 'desc' ? 'asc' : 'desc' })}
      className={cn('px-3 py-2.5 text-[11px] uppercase tracking-wider cursor-pointer select-none whitespace-nowrap',
        align === 'right' ? 'text-right' : 'text-left',
        active ? 'text-cyan-300' : 'text-slate-500 hover:text-slate-300')}
      data-testid={`sort-${field}`}
    >
      <span className="inline-flex items-center gap-1">
        {align === 'right' && active && (sort.dir === 'desc' ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />)}
        {label}
        {align === 'left' && active && (sort.dir === 'desc' ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />)}
      </span>
    </th>
  );
}

function Autocomplete({ placeholder, value, onChange, tipo, testid }) {
  const [open, setOpen] = useState(false);
  const [opts, setOpts] = useState([]);

  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const r = await axios.get(`${API}/analisi/opzioni`, { params: { q: value || '', tipo } });
        setOpts(r.data.nomi || []);
      } catch (e) { /* ignora */ }
    }, 250);
    return () => clearTimeout(t);
  }, [value, tipo]);

  return (
    <div className="relative">
      <Input
        value={value}
        placeholder={placeholder}
        onChange={(e) => { onChange(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 200)}
        className="h-9 text-sm"
        data-testid={testid}
      />
      {open && opts.length > 0 && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 max-h-56 overflow-auto rounded-lg border border-white/10 bg-[#0b1120] shadow-2xl">
          {opts.map((o) => (
            <div
              key={o}
              onMouseDown={(e) => { e.preventDefault(); onChange(o); setOpen(false); }}
              className="px-3 py-2 text-xs text-slate-300 hover:bg-cyan-500/10 hover:text-cyan-200 cursor-pointer"
            >
              {o}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ───────────────────────── TAB VENDITE ─────────────────────────

function VenditeProdotti({ range, setPreset, preset, setRange }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState({ field: 'fatturato', dir: 'desc' });
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/analisi/vendite-prodotti`, {
        params: { start_date: range[0] || undefined, end_date: range[1] || undefined, search: search || undefined },
      });
      setData(r.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, [range, search]);

  useEffect(() => { const t = setTimeout(load, 300); return () => clearTimeout(t); }, [load]);

  const openDetail = async (nome) => {
    setDetailLoading(true);
    setDetail({ nome });
    try {
      const r = await axios.get(`${API}/analisi/prodotto-dettaglio`, {
        params: { nome, start_date: range[0] || undefined, end_date: range[1] || undefined },
      });
      setDetail(r.data);
    } catch (e) { console.error(e); } finally { setDetailLoading(false); }
  };

  const rows = [...(data?.prodotti || [])].sort((a, b) => {
    const va = a[sort.field], vb = b[sort.field];
    if (typeof va === 'string') return sort.dir === 'desc' ? vb.localeCompare(va) : va.localeCompare(vb);
    const na = va ?? -Infinity, nb = vb ?? -Infinity;
    return sort.dir === 'desc' ? nb - na : na - nb;
  });

  return (
    <div className="space-y-5">
      <PeriodBar range={range} setRange={setRange} preset={preset} setPreset={setPreset}>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative w-full sm:w-56">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Cerca prodotto..."
              className="h-9 pl-9 text-sm"
              data-testid="analisi-vendite-search"
            />
          </div>
          <ExportBar range={range} tipo="vendite" filtri={{ prodotto: search }} />
        </div>
      </PeriodBar>

      {loading && !data ? <LoadingSpinner /> : data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <Kpi label="Fatturato periodo" value={formatCurrency(data.kpi.fatturato)} icon={Euro} accent="cyan"
              testid="kpi-fatturato"
              sub={<span>
                {data.periodo.prev_start} → {data.periodo.prev_end}: {formatCurrency(data.kpi.fatturato_prec)} <Delta value={data.kpi.var_pct} />
              </span>} />
            <Kpi label="Quantità venduta" value={data.kpi.quantita.toLocaleString('it-IT')} icon={Package} accent="violet" testid="kpi-quantita" />
            <Kpi label="Prodotti venduti" value={data.kpi.n_prodotti} icon={Scale} accent="violet" testid="kpi-prodotti" />
            <Kpi label="Margine medio" value={data.kpi.margine_medio_pct !== null ? `${data.kpi.margine_medio_pct}%` : '—'} icon={Percent} accent="emerald" testid="kpi-margine"
              sub="costo reale FIFO" />
            <Kpi label="Profitto stimato" value={data.kpi.profitto_stimato !== null ? formatCurrency(data.kpi.profitto_stimato) : '—'} icon={Euro} accent="emerald" testid="kpi-profitto" />
          </div>

          <div className="rounded-xl border border-white/[0.07] overflow-hidden bg-white/[0.015]">
            <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">Vendite per prodotto</h3>
              <span className="text-xs text-slate-500">
                {data.periodo.start} → {data.periodo.end} · confronto {data.periodo.prev_start} → {data.periodo.prev_end} · costi da lotti FIFO
              </span>
            </div>
            <div className="overflow-x-auto max-h-[560px] overflow-y-auto">
              <table className="w-full text-sm" data-testid="analisi-vendite-table">
                <thead className="sticky top-0 bg-[#0b1120] z-10">
                  <tr>
                    <SortHeader label="Prodotto" field="prodotto" sort={sort} setSort={setSort} align="left" />
                    <SortHeader label="Qtà" field="quantita" sort={sort} setSort={setSort} />
                    <SortHeader label="Fatturato" field="fatturato" sort={sort} setSort={setSort} />
                    <SortHeader label="Prezzo medio" field="prezzo_medio" sort={sort} setSort={setSort} />
                    <SortHeader label="Costo reale" field="costo_unitario" sort={sort} setSort={setSort} />
                    <SortHeader label="Margine FIFO" field="margine_pct" sort={sort} setSort={setSort} />
                    <SortHeader label="Clienti" field="n_clienti" sort={sort} setSort={setSort} />
                    <SortHeader label="Var. vs prec." field="var_fatturato_pct" sort={sort} setSort={setSort} />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr
                      key={r.prodotto}
                      onClick={() => openDetail(r.prodotto)}
                      className="border-t border-white/[0.04] hover:bg-cyan-500/[0.06] cursor-pointer transition-colors"
                      data-testid={`vendite-row-${r.prodotto}`}
                    >
                      <td className="px-3 py-2.5 text-slate-200 max-w-[280px] truncate">{r.prodotto}</td>
                      <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">{r.quantita.toLocaleString('it-IT')}</td>
                      <td className="px-3 py-2.5 text-right text-white font-semibold tabular-nums">{formatCurrency(r.fatturato)}</td>
                      <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">€{r.prezzo_medio.toFixed(2)}</td>
                      <td className="px-3 py-2.5 text-right text-slate-400 tabular-nums">{r.costo_unitario ? `€${r.costo_unitario.toFixed(2)}` : '—'}</td>
                      <td className={cn('px-3 py-2.5 text-right font-semibold tabular-nums',
                        r.margine_pct === null ? 'text-slate-600'
                          : r.margine_pct >= 20 ? 'text-emerald-400' : r.margine_pct >= 8 ? 'text-amber-400' : 'text-rose-400')}>
                        {r.margine_pct === null ? '—' : `${r.margine_pct}%`}
                      </td>
                      <td className="px-3 py-2.5 text-right text-slate-400 tabular-nums">{r.n_clienti}</td>
                      <td className="px-3 py-2.5 text-right"><Delta value={r.var_fatturato_pct} /></td>
                    </tr>
                  ))}
                  {rows.length === 0 && (
                    <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-500 text-sm">Nessuna vendita nel periodo selezionato</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {detail && (
        <DetailDrawer title={detail.nome} onClose={() => setDetail(null)} testid="prodotto-detail-drawer">
          {detailLoading || !detail.serie_mensile ? <LoadingSpinner /> : (
            <div className="space-y-5">
              <div className="flex justify-end">
                <Button
                  variant="outline" size="sm"
                  onClick={() => {
                    const p = new URLSearchParams({ prodotto: detail.nome });
                    if (range[0]) p.append('start_date', range[0]);
                    if (range[1]) p.append('end_date', range[1]);
                    window.open(`${API}/analisi/export/listino?${p}`, '_blank');
                  }}
                  data-testid="export-listino-prodotto"
                >
                  <FileDown className="w-4 h-4 mr-2" /> Listino clienti di questo prodotto (PDF)
                </Button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Kpi label="Giacenza" value={detail.giacenza?.toLocaleString('it-IT') ?? '0'} accent="violet" />
                <Kpi label="Qtà minima" value={detail.quantita_minima?.toLocaleString('it-IT') ?? '0'} accent="amber" />
                <Kpi label="Clienti nel periodo" value={detail.top_clienti.length} accent="cyan" />
                <Kpi label="Fornitori nel periodo" value={detail.fornitori.length} accent="emerald" />
              </div>

              <div className="rounded-xl border border-white/[0.07] p-4">
                <h4 className="text-sm font-semibold text-white mb-3">Andamento mensile (ultimi 24 mesi)</h4>
                <ResponsiveContainer width="100%" height={260}>
                  <ComposedChart data={detail.serie_mensile}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="mese" stroke="#64748b" fontSize={11} />
                    <YAxis yAxisId="l" stroke="#64748b" fontSize={11} />
                    <YAxis yAxisId="r" orientation="right" stroke="#64748b" fontSize={11} />
                    <Tooltip contentStyle={{ background: '#0b1120', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 12 }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar yAxisId="l" dataKey="fatturato" name="Fatturato €" fill="#22d3ee" radius={[4, 4, 0, 0]} />
                    <Line yAxisId="r" dataKey="prezzo_vendita" name="Prezzo vendita €" stroke="#34d399" strokeWidth={2} dot={false} />
                    <Line yAxisId="r" dataKey="prezzo_acquisto" name="Prezzo acquisto €" stroke="#fbbf24" strokeWidth={2} dot={false} />
                    <Line yAxisId="r" dataKey="costo_lotti" name="Costo lotto venduto €" stroke="#f472b6" strokeWidth={2} strokeDasharray="4 3" dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              <div className="space-y-4">
                <MiniTable
                  title="Top clienti nel periodo"
                  cols={['Cliente', 'Qtà', 'Prezzo vendita', 'Fatturato', 'Costo lotto', 'Margine']}
                  rows={detail.top_clienti.map((c) => [
                    c.cliente,
                    c.quantita.toLocaleString('it-IT'),
                    `€${c.prezzo_medio.toFixed(2)}`,
                    formatCurrency(c.fatturato),
                    c.costo_unitario ? `€${c.costo_unitario.toFixed(2)}` : '—',
                    c.margine_pct === null || c.margine_pct === undefined ? '—' : `${c.margine_pct}%`,
                  ])}
                  testid="detail-top-clienti"
                />
                <MiniTable
                  title="Fornitori del prodotto"
                  cols={['Fornitore', 'Qtà', 'Prezzo medio']}
                  rows={detail.fornitori.map((f) => [f.fornitore, f.quantita.toLocaleString('it-IT'), `€${f.prezzo_medio.toFixed(2)}`])}
                  testid="detail-fornitori"
                />
              </div>

              <LottiPanel prodotto={detail.nome} lotti={detail.lotti || []} />
            </div>
          )}
        </DetailDrawer>
      )}
    </div>
  );
}

// ───────────────────────── TAB ACQUISTI ─────────────────────────

function AcquistiFornitori({ range, setRange, preset, setPreset }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fornitore, setFornitore] = useState('');
  const [prodotto, setProdotto] = useState('');
  const [sortF, setSortF] = useState({ field: 'spesa', dir: 'desc' });
  const [sortP, setSortP] = useState({ field: 'spesa', dir: 'desc' });
  const [confronto, setConfronto] = useState(null);
  const [confrontoLoading, setConfrontoLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/analisi/acquisti`, {
        params: {
          start_date: range[0] || undefined, end_date: range[1] || undefined,
          fornitore: fornitore || undefined, prodotto: prodotto || undefined,
        },
      });
      setData(r.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, [range, fornitore, prodotto]);

  useEffect(() => { const t = setTimeout(load, 300); return () => clearTimeout(t); }, [load]);

  const openConfronto = async (nome) => {
    setConfrontoLoading(true);
    setConfronto({ prodotto: nome });
    try {
      const r = await axios.get(`${API}/analisi/confronto-fornitori`, {
        params: { prodotto: nome, start_date: range[0] || undefined, end_date: range[1] || undefined },
      });
      setConfronto(r.data);
    } catch (e) { console.error(e); } finally { setConfrontoLoading(false); }
  };

  const sortRows = (rows, sort) => [...rows].sort((a, b) => {
    const va = a[sort.field], vb = b[sort.field];
    if (typeof va === 'string') return sort.dir === 'desc' ? vb.localeCompare(va) : va.localeCompare(vb);
    const na = va ?? -Infinity, nb = vb ?? -Infinity;
    return sort.dir === 'desc' ? nb - na : na - nb;
  });

  return (
    <div className="space-y-5">
      <PeriodBar range={range} setRange={setRange} preset={preset} setPreset={setPreset}>
        <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
          <div className="w-full sm:w-56"><Autocomplete placeholder="Filtra fornitore..." value={fornitore} onChange={setFornitore} tipo="fornitori" testid="analisi-filtro-fornitore" /></div>
          <div className="w-full sm:w-56"><Autocomplete placeholder="Filtra prodotto..." value={prodotto} onChange={setProdotto} tipo="prodotti" testid="analisi-filtro-prodotto" /></div>
          {(fornitore || prodotto) && (
            <Button variant="ghost" size="sm" onClick={() => { setFornitore(''); setProdotto(''); }} data-testid="analisi-clear-filtri">
              <X className="w-4 h-4" />
            </Button>
          )}
          <ExportBar range={range} tipo="acquisti" filtri={{ fornitore, prodotto }} />
        </div>
      </PeriodBar>

      {loading && !data ? <LoadingSpinner /> : data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <Kpi label="Spesa acquisti" value={formatCurrency(data.kpi.spesa)} icon={Euro} accent="amber" testid="kpi-spesa"
              sub={<span>
                {data.periodo.prev_start} → {data.periodo.prev_end}: {formatCurrency(data.kpi.spesa_prec)} <Delta value={data.kpi.var_pct} />
              </span>} />
            <Kpi label="Quantità acquistata" value={data.kpi.quantita.toLocaleString('it-IT')} icon={Package} accent="violet" testid="kpi-qty-acquisti" />
            <Kpi label="Fornitori" value={data.kpi.n_fornitori} icon={Truck} accent="cyan" testid="kpi-n-fornitori" />
            <Kpi label="Prodotti acquistati" value={data.kpi.n_prodotti} icon={Scale} accent="cyan" testid="kpi-n-prodotti-acq" />
            <Kpi label="Resi a fornitore" value={formatCurrency(data.kpi.resi)} icon={TrendingDown} accent="emerald" testid="kpi-resi" />
          </div>

          {data.trend.length > 1 && (
            <div className="rounded-xl border border-white/[0.07] p-4 bg-white/[0.015]">
              <h3 className="text-sm font-semibold text-white mb-3">Spesa mensile</h3>
              <ResponsiveContainer width="100%" height={200}>
                <ComposedChart data={data.trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="mese" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip contentStyle={{ background: '#0b1120', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 12 }} />
                  <Bar dataKey="spesa" name="Spesa €" fill="#fbbf24" radius={[4, 4, 0, 0]} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="grid xl:grid-cols-2 gap-4">
            <div className="rounded-xl border border-white/[0.07] overflow-hidden bg-white/[0.015]">
              <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">Acquisti per fornitore</h3>
                <span className="text-[11px] text-slate-500">{data.periodo.start} → {data.periodo.end}</span>
              </div>
              <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
                <table className="w-full text-sm" data-testid="analisi-fornitori-table">
                  <thead className="sticky top-0 bg-[#0b1120] z-10">
                    <tr>
                      <SortHeader label="Fornitore" field="fornitore" sort={sortF} setSort={setSortF} align="left" />
                      <SortHeader label="Spesa" field="spesa" sort={sortF} setSort={setSortF} />
                      <SortHeader label="Qtà" field="quantita" sort={sortF} setSort={setSortF} />
                      <SortHeader label="Prodotti" field="n_prodotti" sort={sortF} setSort={setSortF} />
                      <SortHeader label="Prz. vend." field="prezzo_vendita" sort={sortF} setSort={setSortF} />
                      <SortHeader label="Margine %" field="margine_pct" sort={sortF} setSort={setSortF} />
                      <SortHeader label="Var." field="var_pct" sort={sortF} setSort={setSortF} />
                    </tr>
                  </thead>
                  <tbody>
                    {sortRows(data.fornitori, sortF).map((f) => (
                      <tr key={f.fornitore}
                        onClick={() => setFornitore(f.fornitore)}
                        className="border-t border-white/[0.04] hover:bg-amber-500/[0.06] cursor-pointer transition-colors"
                        data-testid={`fornitore-row-${f.fornitore}`}>
                        <td className="px-3 py-2.5 text-slate-200 max-w-[240px] truncate">{f.fornitore}</td>
                        <td className="px-3 py-2.5 text-right text-white font-semibold tabular-nums">{formatCurrency(f.spesa)}</td>
                        <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">{f.quantita.toLocaleString('it-IT')}</td>
                        <td className="px-3 py-2.5 text-right text-slate-400 tabular-nums">{f.n_prodotti}</td>
                        <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">{f.prezzo_vendita ? `€${f.prezzo_vendita.toFixed(2)}` : '—'}</td>
                        <td className={cn('px-3 py-2.5 text-right font-semibold tabular-nums',
                          f.margine_pct === null ? 'text-slate-600'
                            : f.margine_pct >= 20 ? 'text-emerald-400' : f.margine_pct >= 8 ? 'text-amber-400' : 'text-rose-400')}>
                          {f.margine_pct === null ? '—' : `${f.margine_pct}%`}
                        </td>
                        <td className="px-3 py-2.5 text-right"><Delta value={f.var_pct} /></td>
                      </tr>
                    ))}
                    {data.fornitori.length === 0 && (
                      <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-500 text-sm">Nessun acquisto nel periodo</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="rounded-xl border border-white/[0.07] overflow-hidden bg-white/[0.015]">
              <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">Prodotti acquistati</h3>
                <span className="text-[11px] text-slate-500">clicca per confrontare i fornitori</span>
              </div>
              <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
                <table className="w-full text-sm" data-testid="analisi-prodotti-acquistati-table">
                  <thead className="sticky top-0 bg-[#0b1120] z-10">
                    <tr>
                      <SortHeader label="Prodotto" field="prodotto" sort={sortP} setSort={setSortP} align="left" />
                      <SortHeader label="Spesa" field="spesa" sort={sortP} setSort={setSortP} />
                      <SortHeader label="Qtà" field="quantita" sort={sortP} setSort={setSortP} />
                      <SortHeader label="Prezzo medio" field="prezzo_medio" sort={sortP} setSort={setSortP} />
                      <SortHeader label="Prz. vend." field="prezzo_vendita" sort={sortP} setSort={setSortP} />
                      <SortHeader label="Margine %" field="margine_pct" sort={sortP} setSort={setSortP} />
                      <SortHeader label="Forn." field="n_fornitori" sort={sortP} setSort={setSortP} />
                    </tr>
                  </thead>
                  <tbody>
                    {sortRows(data.prodotti, sortP).map((p) => (
                      <tr key={p.prodotto}
                        onClick={() => openConfronto(p.prodotto)}
                        className="border-t border-white/[0.04] hover:bg-cyan-500/[0.06] cursor-pointer transition-colors"
                        data-testid={`prodotto-acq-row-${p.prodotto}`}>
                        <td className="px-3 py-2.5 text-slate-200 max-w-[240px] truncate">{p.prodotto}</td>
                        <td className="px-3 py-2.5 text-right text-white font-semibold tabular-nums">{formatCurrency(p.spesa)}</td>
                        <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">{p.quantita.toLocaleString('it-IT')}</td>
                        <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">€{p.prezzo_medio.toFixed(2)}</td>
                        <td className="px-3 py-2.5 text-right text-slate-300 tabular-nums">{p.prezzo_vendita ? `€${p.prezzo_vendita.toFixed(2)}` : '—'}</td>
                        <td className={cn('px-3 py-2.5 text-right font-semibold tabular-nums',
                          p.margine_pct === null ? 'text-slate-600'
                            : p.margine_pct >= 20 ? 'text-emerald-400' : p.margine_pct >= 8 ? 'text-amber-400' : 'text-rose-400')}>
                          {p.margine_pct === null ? '—' : `${p.margine_pct}%`}
                        </td>
                        <td className="px-3 py-2.5 text-right text-slate-400 tabular-nums">{p.n_fornitori}</td>
                      </tr>
                    ))}
                    {data.prodotti.length === 0 && (
                      <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-500 text-sm">Nessun acquisto nel periodo</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}

      {confronto && (
        <DetailDrawer title={`Confronto fornitori — ${confronto.prodotto}`} onClose={() => setConfronto(null)} testid="confronto-fornitori-drawer">
          {confrontoLoading || !confronto.fornitori ? <LoadingSpinner /> : (
            <div className="space-y-5">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <Kpi label="Prezzo vendita medio" value={`€${confronto.prezzo_vendita_medio.toFixed(2)}`} accent="emerald" />
                <Kpi label="Fornitori nel periodo" value={confronto.fornitori.length} accent="cyan" />
                {confronto.confronto && (
                  <Kpi label="Risparmio potenziale" value={formatCurrency(confronto.confronto.risparmio_potenziale)} accent="amber"
                    sub={`comprando tutto da ${confronto.confronto.migliore}`} />
                )}
              </div>
              <MiniTable
                title="Prezzi per fornitore (dal più conveniente)"
                cols={['Fornitore', 'Prezzo medio', 'Ultimo prezzo', 'Qtà', 'Spesa', 'Ultimo acquisto']}
                rows={confronto.fornitori.map((f) => [
                  f.fornitore, `€${f.prezzo_medio.toFixed(2)}`, `€${f.ultimo_prezzo.toFixed(2)}`,
                  f.quantita.toLocaleString('it-IT'), formatCurrency(f.spesa), f.ultima_data,
                ])}
                testid="confronto-fornitori-table"
              />
              {confronto.fornitori.length === 0 && (
                <p className="text-sm text-slate-500">Nessun acquisto di questo prodotto nel periodo selezionato.</p>
              )}
              <LottiPanel prodotto={confronto.prodotto} titolo="Lotti di acquisto del prodotto (FIFO)" />
            </div>
          )}
        </DetailDrawer>
      )}
    </div>
  );
}

// ───────────────────────── SHARED UI ─────────────────────────

function ExportBar({ range, tipo, filtri = {} }) {
  const [pct, setPct] = useState(() => localStorage.getItem('flow_provvigione') || '3');
  const [dettaglio, setDettaglio] = useState(false);
  const [clienteListino, setClienteListino] = useState('');
  const [prodottoListino, setProdottoListino] = useState('');
  const [ordinaMargine, setOrdinaMargine] = useState(false);

  const qs = (extra = {}, useFiltri = true) => {
    const p = new URLSearchParams();
    if (range[0]) p.append('start_date', range[0]);
    if (range[1]) p.append('end_date', range[1]);
    if (useFiltri) Object.entries(filtri).forEach(([k, v]) => { if (v) p.append(k, v); });
    Object.entries(extra).forEach(([k, v]) => p.append(k, v));
    return p.toString();
  };

  const scarica = (path, extra, useFiltri = true) => window.open(`${API}${path}?${qs(extra, useFiltri)}`, '_blank');

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        variant="outline" size="sm"
        onClick={() => scarica('/analisi/export/pdf', { tipo })}
        data-testid={`export-pdf-${tipo}`}
      >
        <FileDown className="w-4 h-4 mr-2" /> Esporta PDF
      </Button>
      {tipo === 'vendite' && (
        <div className="flex items-center gap-2 pl-2 border-l border-white/[0.08]">
          <div className="flex items-center gap-1">
            <Input
              type="number" step="0.1" min="0" max="100" value={pct}
              onChange={(e) => { setPct(e.target.value); localStorage.setItem('flow_provvigione', e.target.value); }}
              className="h-9 w-16 text-xs text-center"
              data-testid="provvigione-input"
            />
            <span className="text-xs text-slate-400">% sul margine</span>
          </div>
          <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox" checked={dettaglio} onChange={(e) => setDettaglio(e.target.checked)}
              className="accent-violet-500" data-testid="rendiconto-dettaglio-toggle"
            />
            dettaglio righe
          </label>
          <Button
            size="sm"
            className="bg-violet-600 hover:bg-violet-500"
            onClick={() => scarica('/analisi/export/rendiconto', { provvigione_pct: pct || 3, dettaglio })}
            data-testid="export-rendiconto"
          >
            <FileText className="w-4 h-4 mr-2" /> Rendiconto vendite
          </Button>
          <div className="flex items-center gap-1 pl-2 border-l border-white/[0.08]">
            <div className="w-44">
              <Autocomplete
                placeholder="Listino per cliente..."
                value={clienteListino}
                onChange={setClienteListino}
                tipo="clienti"
                testid="listino-cliente-input"
              />
            </div>
            <Button
              variant="outline" size="sm"
              disabled={!clienteListino}
              onClick={() => scarica('/analisi/export/listino', { cliente: clienteListino, ordina: 'quantita' }, false)}
              data-testid="export-listino-cliente"
            >
              <FileDown className="w-4 h-4 mr-1" /> Listino
            </Button>
          </div>
          <div className="flex items-center gap-1 pl-2 border-l border-white/[0.08]">
            <div className="w-44">
              <Autocomplete
                placeholder="Listino per prodotto..."
                value={prodottoListino}
                onChange={setProdottoListino}
                tipo="prodotti"
                testid="listino-prodotto-input"
              />
            </div>
            <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer select-none">
              <input
                type="checkbox" checked={ordinaMargine} onChange={(e) => setOrdinaMargine(e.target.checked)}
                className="accent-violet-500" data-testid="listino-ordina-margine"
              />
              per margine
            </label>
            <Button
              variant="outline" size="sm"
              disabled={!prodottoListino}
              onClick={() => scarica('/analisi/export/listino', {
                prodotto: prodottoListino, ordina: ordinaMargine ? 'margine' : 'quantita',
              }, false)}
              data-testid="export-listino-prodotto-bar"
            >
              <FileDown className="w-4 h-4 mr-1" /> Listino
            </Button>
          </div>
        </div>
      )}
      {tipo === 'acquisti' && (
        <div className="flex items-center gap-2 pl-2 border-l border-white/[0.08]">
          <div className="flex items-center gap-1">
            <Input
              type="number" step="0.1" min="0" max="100" value={pct}
              onChange={(e) => { setPct(e.target.value); localStorage.setItem('flow_provvigione', e.target.value); }}
              className="h-9 w-16 text-xs text-center"
              data-testid="provvigione-input-acquisti"
            />
            <span className="text-xs text-slate-400">% sul margine</span>
          </div>
          <Button
            size="sm"
            className="bg-violet-600 hover:bg-violet-500"
            onClick={() => scarica('/analisi/export/rendiconto-acquisti', { provvigione_pct: pct || 3 })}
            data-testid="export-rendiconto-acquisti"
          >
            <FileText className="w-4 h-4 mr-2" /> Rendiconto acquisti
          </Button>
        </div>
      )}
    </div>
  );
}

function PeriodBar({ range, setRange, preset, setPreset, children }) {
  return (
    <div className="rounded-xl border border-white/[0.07] bg-white/[0.015] p-3 flex flex-col lg:flex-row lg:items-center gap-3 justify-between">
      <div className="flex flex-wrap items-center gap-2">
        {PRESETS.map((p) => (
          <button
            key={p.id}
            onClick={() => { setPreset(p.id); setRange(presetRange(p.id)); }}
            data-testid={`preset-${p.id}`}
            className={cn('px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
              preset === p.id
                ? 'bg-cyan-500/15 border-cyan-500/30 text-cyan-300'
                : 'bg-white/[0.02] border-white/[0.07] text-slate-400 hover:text-slate-200')}
          >
            {p.label}
          </button>
        ))}
        <div className="flex items-center gap-1.5 ml-1">
          <Input type="date" value={range[0]} onChange={(e) => { setPreset(null); setRange([e.target.value, range[1]]); }}
            className="h-9 w-[135px] text-xs" data-testid="analisi-start-date" />
          <span className="text-slate-600 text-xs">→</span>
          <Input type="date" value={range[1]} onChange={(e) => { setPreset(null); setRange([range[0], e.target.value]); }}
            className="h-9 w-[135px] text-xs" data-testid="analisi-end-date" />
        </div>
      </div>
      {children}
    </div>
  );
}

function MiniTable({ title, cols, rows, testid }) {
  return (
    <div className="rounded-xl border border-white/[0.07] overflow-hidden">
      <div className="px-4 py-2.5 border-b border-white/[0.06]">
        <h4 className="text-sm font-semibold text-white">{title}</h4>
      </div>
      <div className="overflow-x-auto max-h-80 overflow-y-auto">
        <table className="w-full text-sm" data-testid={testid}>
          <thead className="sticky top-0 bg-[#0b1120]">
            <tr>
              {cols.map((c, i) => (
                <th key={c} className={cn('px-3 py-2 text-[11px] uppercase tracking-wider text-slate-500 whitespace-nowrap',
                  i === 0 ? 'text-left' : 'text-right')}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, ri) => (
              <tr key={ri} className="border-t border-white/[0.04]">
                {r.map((cell, ci) => (
                  <td key={ci} className={cn('px-3 py-2 tabular-nums',
                    ci === 0 ? 'text-left text-slate-200 max-w-[240px] truncate' : 'text-right text-slate-300')}>{cell}</td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={cols.length} className="px-3 py-6 text-center text-slate-500 text-xs">Nessun dato</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DetailDrawer({ title, children, onClose, testid }) {
  return (
    <div className="fixed inset-0 z-[80] flex items-start justify-center p-3 sm:p-6 bg-black/70 backdrop-blur-sm overflow-y-auto"
      onClick={onClose} data-testid={testid}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-5xl rounded-2xl border border-white/[0.08] bg-[#0b1120] shadow-2xl my-4"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06] sticky top-0 bg-[#0b1120] rounded-t-2xl z-10">
          <h3 className="text-base font-semibold text-white pr-6 truncate">{title}</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
            data-testid="drawer-close">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

// ───────────────────────── PAGE ─────────────────────────

export default function Analisi() {
  const [tab, setTab] = useState('vendite');
  const [preset, setPreset] = useState('auto');
  const [range, setRange] = useState(presetRange('auto'));

  return (
    <PageWrapper>
      <PageHeader title="Analisi" subtitle="Vendite per prodotto e acquisti dai fornitori, con confronto sul periodo precedente" />

      <div className="flex gap-1 mb-5 p-1 rounded-xl bg-white/[0.03] border border-white/[0.06] w-fit">
        {[
          { id: 'vendite', label: 'Vendite prodotti', icon: Package },
          { id: 'acquisti', label: 'Acquisti fornitori', icon: Truck },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            data-testid={`analisi-tab-${t.id}`}
            className={cn('flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              tab === t.id ? 'bg-cyan-500/15 text-cyan-300' : 'text-slate-400 hover:text-slate-200')}
          >
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {tab === 'vendite'
        ? <VenditeProdotti range={range} setRange={setRange} preset={preset} setPreset={setPreset} />
        : <AcquistiFornitori range={range} setRange={setRange} preset={preset} setPreset={setPreset} />}    </PageWrapper>
  );
}
