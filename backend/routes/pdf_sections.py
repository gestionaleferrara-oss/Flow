"""Sezioni narrative e confronto ultimi due esercizi per tutti i PDF."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from database import db
from routes.pdf_helper import C_BLUE, C_NAVY, C_RED, C_SLATE, FONT, clean_text

EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']


def it_num(v, dec=0) -> str:
    """Formato italiano: 1.234,56"""
    s = f"{(v or 0):,.{dec}f}"
    return s.replace(',', '§').replace('.', ',').replace('§', '.')


def it_eur(v, dec=0) -> str:
    return f"\u20ac {it_num(v, dec)}"


def _meno_un_anno(d: datetime) -> datetime:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        return d.replace(year=d.year - 1, day=28)


def periodi_anno_su_anno(start: str, end: str):
    """Il periodo selezionato e lo stesso periodo dell'anno precedente."""
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    f = "%Y-%m-%d"
    return ((_meno_un_anno(s).strftime(f), _meno_un_anno(e).strftime(f)), (start, end))


def periodi_due_esercizi(end: str):
    """Due finestre di 12 mesi: l'ultima che termina a `end` e quella precedente."""
    e = datetime.strptime(end, "%Y-%m-%d")
    a1_start = _meno_un_anno(e) + timedelta(days=1)
    a0_end = a1_start - timedelta(days=1)
    a0_start = _meno_un_anno(a0_end) + timedelta(days=1)
    f = "%Y-%m-%d"
    return ((a0_start.strftime(f), a0_end.strftime(f)), (a1_start.strftime(f), e.strftime(f)))


def label_periodo(start: str, end: str) -> str:
    return f"{start[8:10]}/{start[5:7]}/{start[2:4]} - {end[8:10]}/{end[5:7]}/{end[2:4]}"


def label_esercizio(start: str, end: str) -> str:
    return label_periodo(start, end)


async def kpi_vendite(match_base: Dict, start: str, end: str) -> Dict:
    match = {**match_base, "data": {"$gte": start, "$lte": end},
             "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}
    rows = await db.vendite.aggregate([
        {"$match": match},
        {"$group": {"_id": None,
                    "fatturato": {"$sum": {"$abs": "$totale"}},
                    "quantita": {"$sum": {"$abs": "$quantita"}},
                    "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                    "righe": {"$sum": 1},
                    "prodotti": {"$addToSet": "$prodotto_nome"},
                    "clienti": {"$addToSet": "$cliente_nome"}}},
        {"$project": {"fatturato": 1, "quantita": 1, "costo": 1, "righe": 1,
                      "n_prodotti": {"$size": "$prodotti"}, "n_clienti": {"$size": "$clienti"}}},
    ]).to_list(1)
    d = rows[0] if rows else {}
    fatt = d.get('fatturato', 0) or 0
    costo = d.get('costo', 0) or 0
    qty = d.get('quantita', 0) or 0
    return {
        "start": start, "end": end, "label": label_esercizio(start, end),
        "fatturato": fatt, "quantita": qty, "costo": costo,
        "margine": fatt - costo,
        "margine_pct": ((fatt - costo) / costo * 100) if costo > 0 else None,
        "prezzo_medio": (fatt / qty) if qty else 0,
        "righe": d.get('righe', 0), "n_prodotti": d.get('n_prodotti', 0), "n_clienti": d.get('n_clienti', 0),
    }


async def kpi_acquisti(match_base: Dict, start: str, end: str) -> Dict:
    match = {**match_base, "data": {"$gte": start, "$lte": end}}
    rows = await db.ordini.aggregate([
        {"$match": match},
        {"$group": {"_id": None,
                    "spesa": {"$sum": "$totale"},
                    "quantita": {"$sum": "$quantita"},
                    "qty_v": {"$sum": {"$cond": [{"$and": [{"$gt": ["$totale", 0]}, {"$gt": ["$quantita", 0]}]},
                                                 "$quantita", 0]}},
                    "spesa_v": {"$sum": {"$cond": [{"$and": [{"$gt": ["$totale", 0]}, {"$gt": ["$quantita", 0]}]},
                                                   "$totale", 0]}},
                    "righe": {"$sum": 1},
                    "prodotti": {"$addToSet": "$prodotto_nome"},
                    "fornitori": {"$addToSet": "$fornitore_nome"}}},
        {"$project": {"spesa": 1, "quantita": 1, "righe": 1, "qty_v": 1, "spesa_v": 1,
                      "n_prodotti": {"$size": "$prodotti"}, "n_fornitori": {"$size": "$fornitori"}}},
    ]).to_list(1)
    d = rows[0] if rows else {}
    return {
        "start": start, "end": end, "label": label_esercizio(start, end),
        "spesa": d.get('spesa', 0) or 0, "quantita": d.get('quantita', 0) or 0,
        "prezzo_medio": (d['spesa_v'] / d['qty_v']) if d.get('qty_v') else 0,
        "righe": d.get('righe', 0), "n_prodotti": d.get('n_prodotti', 0),
        "n_fornitori": d.get('n_fornitori', 0),
    }


def var_pct(nuovo, vecchio) -> Optional[float]:
    if not vecchio:
        return None
    return (nuovo - vecchio) / vecchio * 100


def _v(v) -> str:
    return f"{v:+.1f}%".replace('.', ',') if v is not None else 'n.d.'


async def prezzi_in_aumento(match_base: Dict, p0, p1, soglia: float = 5.0, limit: int = 12) -> List[Dict]:
    """Prodotti presenti nei due esercizi con prezzo medio ponderato di acquisto in aumento."""
    async def prezzi(start, end):
        rows = await db.ordini.aggregate([
            {"$match": {**match_base, "data": {"$gte": start, "$lte": end},
                        "quantita": {"$gt": 0}, "totale": {"$gt": 0}}},
            {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": "$quantita"}, "tot": {"$sum": "$totale"}}},
        ]).to_list(20000)
        return {r['_id']: r['tot'] / r['qty'] for r in rows if r['_id'] and r['qty'] > 0}

    vecchi = await prezzi(*p0)
    nuovi = await prezzi(*p1)
    out = []
    for nome, pn in nuovi.items():
        pv = vecchi.get(nome)
        if not pv or pv <= 0:
            continue
        v = (pn - pv) / pv * 100
        if v >= soglia:
            out.append({"prodotto": nome, "prezzo_vecchio": pv, "prezzo_nuovo": pn, "var_pct": v})
    out.sort(key=lambda x: -x['var_pct'])
    return out[:limit]


def concentrazione(valori: List[float], soglia: float = 0.8):
    """Quanti elementi coprono l'80% del totale e peso dei primi 5."""
    tot = sum(valori)
    if tot <= 0:
        return 0, len(valori), 0.0
    ordinati = sorted(valori, reverse=True)
    cum = 0.0
    n = 0
    for v in ordinati:
        cum += v
        n += 1
        if cum / tot >= soglia:
            break
    top5 = sum(ordinati[:5]) / tot * 100
    return n, len(valori), top5


# ═══════════════ BLOCCHI PDF ═══════════════

def blocco_sintesi(pdf, testo: str, titolo: str = "Sintesi"):
    pdf.section_title(titolo, C_BLUE, top_gap=2)
    pdf.set_font(FONT, '', 9)
    pdf.set_text_color(40, 50, 70)
    pdf.set_x(14)
    pdf.multi_cell(182, 5.1, clean_text(testo), align='L')
    pdf.ln(3)


def blocco_considerazioni(pdf, testo: str):
    if not testo:
        return
    pdf.ensure_space(32)
    pdf.section_title("Considerazioni finali", C_NAVY)
    pdf.set_font(FONT, '', 9)
    pdf.set_text_color(40, 50, 70)
    pdf.set_x(14)
    pdf.multi_cell(182, 5.1, clean_text(testo), align='L')
    pdf.ln(2)


def blocco_confronto(pdf, righe: List[List[str]],
                     titolo="Confronto con lo stesso periodo dell'anno precedente"):
    pdf.section_title(titolo, C_SLATE)
    pdf.smart_table(['Indicatore', 'Anno precedente', 'Periodo selezionato', 'Var. %'],
                    [70, 40, 40, 40], righe, aligns=['L', 'R', 'R', 'R'])


def blocco_prezzi_aumento(pdf, prezzi: List[Dict]):
    if not prezzi:
        return
    pdf.section_title("Prezzi di acquisto in aumento rispetto allo stesso periodo dell'anno precedente", C_RED)
    righe = [[clean_text(p['prodotto'])[:48], it_eur(p['prezzo_vecchio'], 2), it_eur(p['prezzo_nuovo'], 2),
              _v(p['var_pct'])] for p in prezzi]
    pdf.smart_table(['Prodotto', 'Prezzo anno prec.', 'Prezzo periodo sel.', 'Var. %'],
                    [76, 38, 38, 38], righe, aligns=['L', 'R', 'R', 'R'])
    pdf.note_text("Prodotti acquistati in entrambi i periodi con prezzo medio ponderato in aumento di almeno il 5%: "
                  "sono i candidati prioritari per una rinegoziazione con il fornitore.")


# ═══════════════ TESTI ═══════════════

def righe_confronto_vendite(a0: Dict, a1: Dict) -> List[List[str]]:
    return [
        ["Fatturato", it_eur(a0['fatturato']), it_eur(a1['fatturato']), _v(var_pct(a1['fatturato'], a0['fatturato']))],
        ["Quantita venduta", it_num(a0['quantita']), it_num(a1['quantita']), _v(var_pct(a1['quantita'], a0['quantita']))],
        ["Costo merce (lotti FIFO)", it_eur(a0['costo']), it_eur(a1['costo']), _v(var_pct(a1['costo'], a0['costo']))],
        ["Margine generato", it_eur(a0['margine']), it_eur(a1['margine']), _v(var_pct(a1['margine'], a0['margine']))],
        ["Margine %", f"{it_num(a0['margine_pct'], 1)}%" if a0['margine_pct'] is not None else 'n.d.',
         f"{it_num(a1['margine_pct'], 1)}%" if a1['margine_pct'] is not None else 'n.d.',
         _v(var_pct(a1['margine_pct'] or 0, a0['margine_pct'] or 0))],
        ["Prezzo medio di vendita", it_eur(a0['prezzo_medio'], 2), it_eur(a1['prezzo_medio'], 2),
         _v(var_pct(a1['prezzo_medio'], a0['prezzo_medio']))],
        ["N. scarichi", it_num(a0['righe']), it_num(a1['righe']), _v(var_pct(a1['righe'], a0['righe']))],
        ["N. prodotti distinti", it_num(a0['n_prodotti']), it_num(a1['n_prodotti']),
         _v(var_pct(a1['n_prodotti'], a0['n_prodotti']))],
        ["N. clienti", it_num(a0['n_clienti']), it_num(a1['n_clienti']), _v(var_pct(a1['n_clienti'], a0['n_clienti']))],
    ]


def righe_confronto_acquisti(a0: Dict, a1: Dict) -> List[List[str]]:
    return [
        ["Spesa acquisti", it_eur(a0['spesa']), it_eur(a1['spesa']), _v(var_pct(a1['spesa'], a0['spesa']))],
        ["Quantita acquistata", it_num(a0['quantita']), it_num(a1['quantita']), _v(var_pct(a1['quantita'], a0['quantita']))],
        ["Prezzo medio di acquisto", it_eur(a0['prezzo_medio'], 2), it_eur(a1['prezzo_medio'], 2),
         _v(var_pct(a1['prezzo_medio'], a0['prezzo_medio']))],
        ["N. documenti/righe", it_num(a0['righe']), it_num(a1['righe']), _v(var_pct(a1['righe'], a0['righe']))],
        ["N. prodotti distinti", it_num(a0['n_prodotti']), it_num(a1['n_prodotti']),
         _v(var_pct(a1['n_prodotti'], a0['n_prodotti']))],
        ["N. fornitori", it_num(a0['n_fornitori']), it_num(a1['n_fornitori']),
         _v(var_pct(a1['n_fornitori'], a0['n_fornitori']))],
    ]


def testo_sintesi_vendite(periodo_label: str, tot: Dict, a0: Dict, a1: Dict,
                          conc, extra: str = "") -> str:
    n80, ntot, top5 = conc
    v_fatt = var_pct(a1['fatturato'], a0['fatturato'])
    v_marg = var_pct(a1['margine'], a0['margine'])
    frasi = [
        f"Nel periodo {periodo_label} il venduto e' stato di {it_eur(tot['fatturato'])} su "
        f"{it_num(tot['quantita'])} pezzi, distribuiti su {it_num(tot['righe'])} scarichi "
        f"verso {it_num(tot.get('n_clienti', 0))} clienti e {it_num(tot.get('n_prodotti', 0))} prodotti distinti.",
        f"Il costo della merce, ricostruito collegando ogni scarico al lotto di acquisto effettivamente consumato "
        f"(metodo FIFO), e' di {it_eur(tot['costo'])}, con un margine di {it_eur(tot['margine'])}"
        + (f" pari al {it_num(tot['margine_pct'], 1)}% sul costo." if tot.get('margine_pct') is not None else "."),
    ]
    if ntot:
        frasi.append(
            f"Il venduto e' concentrato: {n80} prodotti su {ntot} coprono l'80% del fatturato e i primi cinque "
            f"da soli valgono circa il {it_num(top5, 0)}%.")
    if v_fatt is not None:
        direzione = "in crescita" if v_fatt >= 0 else "in calo"
        frasi.append(
            f"Rispetto allo stesso periodo dell'anno precedente ({a0['label']}, {it_eur(a0['fatturato'])} di "
            f"fatturato), il venduto e' {direzione} del {it_num(abs(v_fatt), 1)}%"
            + (f", con un margine {'superiore' if (v_marg or 0) >= 0 else 'inferiore'} del "
               f"{it_num(abs(v_marg), 1)}%." if v_marg is not None else "."))
    if extra:
        frasi.append(extra)
    return " ".join(frasi)


def testo_sintesi_acquisti(periodo_label: str, tot: Dict, a0: Dict, a1: Dict, conc,
                           prezzi: List[Dict], extra: str = "") -> str:
    n80, ntot, top5 = conc
    v_spesa = var_pct(a1['spesa'], a0['spesa'])
    v_qty = var_pct(a1['quantita'], a0['quantita'])
    v_prezzo = var_pct(a1['prezzo_medio'], a0['prezzo_medio'])
    frasi = [
        f"Nel periodo {periodo_label} la spesa di acquisto e' stata di {it_eur(tot['spesa'])} per "
        f"{it_num(tot['quantita'])} pezzi, su {it_num(tot['righe'])} righe di acquisto, "
        f"{it_num(tot.get('n_fornitori', 0))} fornitori e {it_num(tot.get('n_prodotti', 0))} prodotti distinti.",
    ]
    if ntot:
        frasi.append(f"La spesa e' concentrata: {n80} prodotti su {ntot} coprono l'80% del totale e i primi cinque "
                     f"valgono circa il {it_num(top5, 0)}%.")
    if v_spesa is not None:
        direzione = "superiore" if v_spesa >= 0 else "inferiore"
        causa = ""
        if v_qty is not None and v_prezzo is not None:
            if abs(v_qty) > abs(v_prezzo):
                causa = (f" La variazione e' soprattutto un effetto volume ({_v(v_qty)} sulle quantita'), "
                         f"mentre il prezzo medio si muove del {_v(v_prezzo)}.")
            else:
                causa = (f" La variazione e' soprattutto un effetto prezzo ({_v(v_prezzo)} sul prezzo medio), "
                         f"a fronte di quantita' al {_v(v_qty)}.")
        frasi.append(
            f"Rispetto allo stesso periodo dell'anno precedente ({a0['label']}, {it_eur(a0['spesa'])} di spesa), "
            f"la spesa e' {direzione} del {it_num(abs(v_spesa), 1)}%.{causa}")
    if prezzi:
        primi = ", ".join(f"{clean_text(p['prodotto'])[:32]} ({_v(p['var_pct'])})" for p in prezzi[:3])
        frasi.append(f"Gli aumenti di prezzo piu' rilevanti tra i due esercizi riguardano: {primi}.")
    if extra:
        frasi.append(extra)
    return " ".join(frasi)


# ═══════════════ GRAFICI ═══════════════

MESI_IT = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']


def _label_mese(ym: str) -> str:
    try:
        a, m = ym.split('-')
        return f"{MESI_IT[int(m) - 1]} {a[2:]}"
    except (ValueError, IndexError):
        return ym


async def _serie_mensile(coll, match_base: Dict, start: str, end: str, campo: str) -> Dict[str, float]:
    match = {**match_base, "data": {"$gte": start, "$lte": end}}
    if coll == 'vendite':
        match["cliente_nome"] = {"$nin": EXCLUDED_CLIENTS}
        somma = {"$sum": {"$abs": f"${campo}"}}
    else:
        somma = {"$sum": f"${campo}"}
    rows = await db[coll].aggregate([
        {"$match": match},
        {"$group": {"_id": {"$substr": ["$data", 0, 7]}, "tot": somma}},
        {"$sort": {"_id": 1}},
    ]).to_list(500)
    return {r['_id']: r['tot'] or 0 for r in rows if r['_id']}


async def blocco_grafici(pdf, match_base: Dict, start: str, end: str, tipo: str = 'vendite',
                         top: Optional[List] = None, titolo_top: str = ''):
    """Confronto mensile con l'anno precedente + classifica (top = [(nome, valore)])."""
    from routes.pdf_helper import C_AMBER, C_BLUE, C_EMERALD, C_MUTED

    coll = 'ordini' if tipo == 'acquisti' else 'vendite'
    campo = 'totale'
    p0, p1 = periodi_anno_su_anno(start, end)
    attuale = await _serie_mensile(coll, match_base, p1[0], p1[1], campo)
    prec = await _serie_mensile(coll, match_base, p0[0], p0[1], campo)

    if attuale:
        chiavi = sorted(attuale.keys())[-12:]
        # mese equivalente dell'anno precedente
        def anno_prec(ym):
            a, m = ym.split('-')
            return f"{int(a) - 1:04d}-{m}"
        serie_a = [attuale.get(k, 0) for k in chiavi]
        serie_b = [prec.get(anno_prec(k), 0) for k in chiavi]
        pdf.section_title(("Andamento mensile: spesa acquisti" if tipo == 'acquisti'
                           else "Andamento mensile: fatturato") + " vs anno precedente",
                          C_BLUE, top_gap=2)
        pdf.compare_chart([_label_mese(k) for k in chiavi], serie_a, serie_b,
                          legend_a='Periodo selezionato', legend_b='Stesso mese anno prec.',
                          color_a=C_BLUE, color_b=C_MUTED, unit=' \u20ac')
        pdf.chart_caption("Valori in euro. La linea tratteggiata grigia e' lo stesso mese dell'anno precedente.")

    if top:
        pdf.section_title(titolo_top or ("Top fornitori per spesa" if tipo == 'acquisti'
                                         else "Top prodotti per fatturato"),
                          C_EMERALD if tipo == 'vendite' else C_AMBER)
        pdf.bar_ranking(top[:12], color=C_EMERALD if tipo == 'vendite' else C_AMBER, unit=' \u20ac')
