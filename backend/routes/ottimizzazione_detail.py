"""Drill-down delle opportunita' di ottimizzazione: spiegazione + prove a supporto."""
from statistics import median
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException

from database import db
from routes.analisi import EXCLUDED_CLIENTS, resolve_period
from routes.pdf_sections import periodi_anno_su_anno

router = APIRouter()


def _eur(v) -> str:
    return f"{(v or 0):,.2f}".replace(',', '§').replace('.', ',').replace('§', '.') + " €"


def _q(v) -> str:
    return f"{(v or 0):,.0f}".replace(',', '.')


def T(titolo: str, colonne: List[str], righe: List[List]) -> Dict:
    return {"titolo": titolo, "colonne": colonne, "righe": righe}


async def acquisti_prodotto(nome: str, start: str, end: str) -> List[Dict]:
    return await db.ordini.find(
        {"prodotto_nome": nome, "data": {"$gte": start, "$lte": end}, "quantita": {"$gt": 0},
         "totale": {"$gt": 0}},
        {"_id": 0, "data": 1, "fornitore_nome": 1, "quantita": 1, "totale": 1, "prezzo_unitario": 1}
    ).sort([("data", -1)]).to_list(400)


async def serie_mensile_prodotto(nome: str) -> List[Dict]:
    vend = await db.vendite.aggregate([
        {"$match": {"prodotto_nome": nome, "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
        {"$group": {"_id": {"$substr": ["$data", 0, 7]}, "qty": {"$sum": {"$abs": "$quantita"}},
                    "fatt": {"$sum": {"$abs": "$totale"}}, "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}}}},
        {"$sort": {"_id": 1}},
    ]).to_list(400)
    acq = await db.ordini.aggregate([
        {"$match": {"prodotto_nome": nome, "quantita": {"$gt": 0}, "totale": {"$gt": 0}}},
        {"$group": {"_id": {"$substr": ["$data", 0, 7]}, "qty": {"$sum": "$quantita"}, "tot": {"$sum": "$totale"}}},
    ]).to_list(400)
    amap = {a['_id']: a for a in acq}
    out = []
    for v in vend[-15:]:
        a = amap.get(v['_id'], {})
        out.append({
            "mese": v['_id'], "qty": v['qty'], "fatt": v['fatt'],
            "prezzo_vendita": v['fatt'] / v['qty'] if v['qty'] else 0,
            "costo": v['costo'] / v['qty'] if (v['costo'] and v['qty']) else 0,
            "prezzo_acquisto": (a.get('tot', 0) / a['qty']) if a.get('qty') else 0,
            "margine": ((v['fatt'] - v['costo']) / v['costo'] * 100) if v['costo'] else None,
        })
    return out


@router.get("/ottimizzazione/dettaglio")
async def ottimizzazione_dettaglio(
    modulo: str, prodotto: Optional[str] = None, cliente: Optional[str] = None,
    fornitore: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None
):
    start, end, _, _ = await resolve_period(start_date, end_date)
    (ly_start, ly_end), _ = periodi_anno_su_anno(start, end)
    tabelle: List[Dict] = []
    spiegazione = ""
    azione = ""
    titolo = prodotto or cliente or fornitore or modulo

    # ─────────── MODULI ACQUISTI ───────────
    if modulo in ("cambio_fornitore", "sconto_quantita", "prezzi_aumento", "rotazione", "margine_basso"):
        if not prodotto:
            raise HTTPException(status_code=400, detail="Prodotto richiesto")
        righe = await acquisti_prodotto(prodotto, start, end)
        per_f: Dict[str, Dict] = {}
        for r in righe:
            f = per_f.setdefault(r['fornitore_nome'], {"qty": 0.0, "spesa": 0.0, "righe": 0, "ultima": r['data']})
            f['qty'] += r['quantita']; f['spesa'] += r.get('totale', 0) or 0; f['righe'] += 1

        if modulo == "cambio_fornitore":
            prezzi = {f: d['spesa'] / d['qty'] for f, d in per_f.items() if d['qty'] > 0}
            if prezzi:
                best = min(prezzi, key=prezzi.get)
                qty_tot = sum(d['qty'] for d in per_f.values())
                spesa_tot = sum(d['spesa'] for d in per_f.values())
                risparmio = sum((prezzi[f] - prezzi[best]) * per_f[f]['qty'] for f in prezzi)
                spiegazione = (
                    f"Nel periodo hai comprato {_q(qty_tot)} pezzi di {prodotto} da {len(per_f)} fornitori diversi, "
                    f"spendendo {_eur(spesa_tot)} (prezzo medio {_eur(spesa_tot / qty_tot)}). "
                    f"Il fornitore piu' conveniente e' {best} a {_eur(prezzi[best])}: se tutta la quantita' fosse "
                    f"stata acquistata da lui avresti speso {_eur(prezzi[best] * qty_tot)}, "
                    f"con un risparmio di {_eur(risparmio)}. Le tabelle sotto mostrano il prezzo di ogni fornitore "
                    f"e ogni singolo acquisto, cosi' puoi verificare formato, date e quantita' prima di spostare "
                    f"gli ordini o usare il confronto come leva in trattativa."
                )
                azione = (f"Chiedi a {max(prezzi, key=prezzi.get)} di allinearsi a {_eur(prezzi[best])} "
                          f"oppure sposta i volumi su {best}.")
                tabelle.append(T("Prezzo per fornitore nel periodo",
                                 ["Fornitore", "Qtà", "Spesa", "Prezzo medio", "Acquisti", "Differenza vs migliore"],
                                 [[f, _q(d['qty']), _eur(d['spesa']), _eur(prezzi[f]), d['righe'],
                                   _eur((prezzi[f] - prezzi[best]) * d['qty'])]
                                  for f, d in sorted(per_f.items(), key=lambda x: prezzi.get(x[0], 0))]))

        elif modulo == "sconto_quantita":
            qty_list = [r['quantita'] for r in righe]
            if qty_list:
                med = median(qty_list)
                pic = [r for r in righe if r['quantita'] <= med]
                gra = [r for r in righe if r['quantita'] > med]
                qp = sum(r['quantita'] for r in pic) or 1
                sp = sum(r.get('totale', 0) for r in pic)
                qg = sum(r['quantita'] for r in gra) or 1
                sg = sum(r.get('totale', 0) for r in gra)
                spiegazione = (
                    f"Su {len(righe)} acquisti di {prodotto} nel periodo, negli ordini fino a {_q(med)} pezzi hai "
                    f"pagato in media {_eur(sp / qp)}, mentre negli ordini piu' grandi hai pagato {_eur(sg / qg)} "
                    f"({(sp / qp - sg / qg) / (sp / qp) * 100:.1f}% in meno). Significa che il fornitore ti riconosce "
                    f"gia' uno sconto sul volume: consolidando gli ordini piccoli in meno consegne piu' grandi "
                    f"puoi ottenere lo stesso prezzo su tutta la quantita'. L'elenco degli acquisti sotto mostra "
                    f"data, fornitore, quantita' e prezzo di ogni riga."
                )
                azione = (f"Raggruppa gli ordini piccoli e chiedi il prezzo di {_eur(sg / qg)} su tutte le "
                          f"consegne, oppure un ordine programmato a scaglioni.")

        elif modulo == "prezzi_aumento":
            ly = await db.ordini.aggregate([
                {"$match": {"prodotto_nome": prodotto, "data": {"$gte": ly_start, "$lte": ly_end},
                            "quantita": {"$gt": 0}, "totale": {"$gt": 0}}},
                {"$group": {"_id": "$fornitore_nome", "qty": {"$sum": "$quantita"}, "tot": {"$sum": "$totale"}}},
            ]).to_list(200)
            qty_ora = sum(d['qty'] for d in per_f.values()) or 1
            spesa_ora = sum(d['spesa'] for d in per_f.values())
            p_ora = spesa_ora / qty_ora
            qty_ly = sum(r['qty'] for r in ly) or 1
            p_ly = sum(r['tot'] for r in ly) / qty_ly if ly else 0
            if p_ly:
                spiegazione = (
                    f"Il prezzo di acquisto di {prodotto} e' passato da {_eur(p_ly)} nello stesso periodo "
                    f"dell'anno scorso a {_eur(p_ora)} di oggi (+{(p_ora - p_ly) / p_ly * 100:.1f}%). "
                    f"Sulle {_q(qty_ora)} unita' acquistate nel periodo l'aumento ti costa "
                    f"{_eur((p_ora - p_ly) * qty_ora)}. Sotto trovi il confronto per fornitore e l'andamento "
                    f"mensile del prezzo di acquisto e di vendita, per capire se l'aumento e' stato ribaltato "
                    f"sul prezzo di vendita o se si e' mangiato il margine."
                )
                azione = (f"Porta in trattativa il confronto anno su anno e chiedi il rientro verso {_eur(p_ly)}, "
                          f"oppure adegua il prezzo di vendita.")
                lym = {r['_id']: r for r in ly}
                tabelle.append(T("Confronto prezzi per fornitore (anno precedente vs periodo)",
                                 ["Fornitore", "Prezzo anno prec.", "Prezzo attuale", "Var. %", "Qtà attuale"],
                                 [[f, _eur(lym[f]['tot'] / lym[f]['qty']) if f in lym and lym[f]['qty'] else '—',
                                   _eur(d['spesa'] / d['qty']) if d['qty'] else '—',
                                   (f"{((d['spesa'] / d['qty']) / (lym[f]['tot'] / lym[f]['qty']) - 1) * 100:+.1f}%"
                                    if f in lym and lym[f]['qty'] and d['qty'] else '—'),
                                   _q(d['qty'])] for f, d in per_f.items()]))

        elif modulo == "rotazione":
            lotti = await db.lotti.find({"prodotto": prodotto}, {"_id": 0}).sort([("data_acquisto", -1)]).to_list(60)
            giorni = [l for l in lotti if l.get('data_esaurimento')]
            media_g = (sum((__import__('datetime').datetime.strptime(l['data_esaurimento'], "%Y-%m-%d")
                            - __import__('datetime').datetime.strptime(l['data_acquisto'], "%Y-%m-%d")).days
                           for l in giorni) / len(giorni)) if giorni else None
            residuo = sum((l.get('residuo', 0) or 0) * (l.get('prezzo_acquisto', 0) or 0) for l in lotti)
            spiegazione = (
                f"{prodotto}: i lotti acquistati si esauriscono in media in "
                f"{media_g:.0f} giorni. " if media_g is not None else f"{prodotto}: nessun lotto ancora esaurito. "
            ) + (
                f"Al momento restano {_eur(residuo)} di merce non venduta valorizzata al costo di acquisto. "
                f"Confrontando la quantita' media per ordine con il consumo reale ottieni la quantita' da ordinare "
                f"per coprire il periodo desiderato senza immobilizzare capitale. Sotto trovi lotto per lotto quanto "
                f"hai comprato, quanto hai venduto e in quanti giorni."
            )
            azione = "Riduci la quantita' per ordine e aumenta la frequenza, oppure spingi le vendite dei lotti fermi."
            tabelle.append(T("Lotti del prodotto",
                             ["Acquisto", "Fornitore", "Qtà", "Costo/u", "Venduto", "Residuo", "Esaurito il", "Margine %"],
                             [[l['data_acquisto'], l.get('fornitore', '—'), _q(l.get('quantita')),
                               _eur(l.get('prezzo_acquisto')), _q(l.get('quantita_venduta')), _q(l.get('residuo')),
                               l.get('data_esaurimento') or 'in corso',
                               f"{l['margine_pct']}%" if l.get('margine_pct') is not None else '—'] for l in lotti]))

        elif modulo == "margine_basso":
            v = await db.vendite.aggregate([
                {"$match": {"prodotto_nome": prodotto, "data": {"$gte": start, "$lte": end},
                            "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
                {"$group": {"_id": "$cliente_nome", "qty": {"$sum": {"$abs": "$quantita"}},
                            "fatt": {"$sum": {"$abs": "$totale"}},
                            "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}}}},
                {"$sort": {"fatt": -1}},
            ]).to_list(200)
            qty = sum(r['qty'] for r in v) or 1
            fatt = sum(r['fatt'] for r in v)
            costo = sum(r['costo'] for r in v)
            spiegazione = (
                f"{prodotto} viene venduto a {_eur(fatt / qty)} di media ma ti costa {_eur(costo / qty)} "
                f"(costo reale del lotto): il margine e' del "
                f"{((fatt - costo) / costo * 100) if costo else 0:.1f}%, sotto la soglia di sicurezza. "
                f"Nel periodo hai movimentato {_q(qty)} pezzi per {_eur(fatt)}. Hai due leve: comprare meglio "
                f"(costo target {_eur((fatt / qty) / 1.15)} per arrivare al 15%) oppure alzare il prezzo ai clienti "
                f"che pagano meno, che trovi elencati qui sotto."
            )
            azione = "Rinegozia l'acquisto o ritocca il prezzo ai clienti sotto media."
            tabelle.append(T("Clienti che comprano questo prodotto",
                             ["Cliente", "Qtà", "Prezzo medio", "Fatturato", "Margine %"],
                             [[r['_id'], _q(r['qty']), _eur(r['fatt'] / r['qty']) if r['qty'] else '—',
                               _eur(r['fatt']),
                               f"{(r['fatt'] - r['costo']) / r['costo'] * 100:.1f}%" if r['costo'] else '—']
                              for r in v]))

        if modulo in ("cambio_fornitore", "sconto_quantita", "prezzi_aumento"):
            tabelle.append(T("Acquisti del periodo (riga per riga)",
                             ["Data", "Fornitore", "Qtà", "Prezzo", "Totale"],
                             [[r['data'], r['fornitore_nome'], _q(r['quantita']),
                               _eur((r.get('totale', 0) / r['quantita']) if r['quantita'] else 0),
                               _eur(r.get('totale'))] for r in righe[:60]]))
        serie = await serie_mensile_prodotto(prodotto)
        if serie:
            tabelle.append(T("Andamento mensile (ultimi mesi)",
                             ["Mese", "Qtà venduta", "Prezzo vendita", "Costo lotto", "Prezzo acquisto", "Margine %"],
                             [[s['mese'], _q(s['qty']), _eur(s['prezzo_vendita']), _eur(s['costo']),
                               _eur(s['prezzo_acquisto']),
                               f"{s['margine']:.1f}%" if s['margine'] is not None else '—'] for s in serie]))

    # ─────────── MODULO CONSOLIDAMENTO ───────────
    elif modulo == "consolidamento":
        if not fornitore:
            raise HTTPException(status_code=400, detail="Fornitore richiesto")
        cat = set(await db.ordini.distinct("prodotto_nome", {"fornitore_nome": fornitore}))
        righe = await db.ordini.find(
            {"data": {"$gte": start, "$lte": end}, "quantita": {"$gt": 0}, "totale": {"$gt": 0}},
            {"_id": 0, "prodotto_nome": 1, "fornitore_nome": 1, "quantita": 1, "totale": 1}).to_list(200000)
        altrove: Dict[str, Dict] = {}
        spesa_sua = 0.0
        for r in righe:
            if r['fornitore_nome'] == fornitore:
                spesa_sua += r['totale']
                continue
            if r['prodotto_nome'] in cat:
                d = altrove.setdefault(r['prodotto_nome'], {"qty": 0.0, "spesa": 0.0, "forn": {}})
                d['qty'] += r['quantita']; d['spesa'] += r['totale']
                d['forn'][r['fornitore_nome']] = d['forn'].get(r['fornitore_nome'], 0) + r['totale']
        spostabile = sum(d['spesa'] for d in altrove.values())
        prezzi_suoi = await db.ordini.aggregate([
            {"$match": {"fornitore_nome": fornitore, "prodotto_nome": {"$in": list(altrove.keys())},
                        "quantita": {"$gt": 0}, "totale": {"$gt": 0}}},
            {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": "$quantita"}, "tot": {"$sum": "$totale"},
                        "ultima": {"$max": "$data"}}},
        ]).to_list(5000)
        pmap = {p['_id']: p for p in prezzi_suoi}
        spiegazione = (
            f"Nel periodo hai speso {_eur(spesa_sua)} con {fornitore}. Nello stesso periodo hai comprato da altri "
            f"fornitori {len(altrove)} prodotti che {fornitore} tratta gia', per un totale di {_eur(spostabile)}. "
            f"Spostando anche solo una parte di questi volumi porteresti il suo giro a "
            f"{_eur(spesa_sua + spostabile)} (+{(spostabile / spesa_sua * 100) if spesa_sua else 0:.0f}%): "
            f"un argomento concreto per ottenere uno sconto sull'intero listino. Nella tabella trovi, per ogni "
            f"prodotto, quanto spendi altrove e a che prezzo lo ha venduto lui in passato: sposta solo dove e' "
            f"davvero competitivo."
        )
        azione = (f"Presenta a {fornitore} il volume aggiuntivo di {_eur(spostabile)} e chiedi uno sconto a scaglioni.")
        tabelle.append(T("Prodotti comprati altrove che questo fornitore tratta",
                         ["Prodotto", "Spesa altrove", "Qtà", "Fornitori attuali", "Suo prezzo storico", "Ultimo acquisto da lui"],
                         [[p, _eur(d['spesa']), _q(d['qty']), ", ".join(d['forn'].keys()),
                           _eur(pmap[p]['tot'] / pmap[p]['qty']) if p in pmap and pmap[p]['qty'] else '—',
                           pmap[p]['ultima'] if p in pmap else '—']
                          for p, d in sorted(altrove.items(), key=lambda x: -x[1]['spesa'])[:40]]))

    # ─────────── MODULI VENDITE ───────────
    elif modulo in ("sotto_prezzo", "sconto_quantita_vendita", "margine_calo"):
        if not prodotto:
            raise HTTPException(status_code=400, detail="Prodotto richiesto")
        clienti = await db.vendite.aggregate([
            {"$match": {"prodotto_nome": prodotto, "data": {"$gte": start, "$lte": end},
                        "cliente_nome": {"$nin": EXCLUDED_CLIENTS}}},
            {"$group": {"_id": "$cliente_nome", "qty": {"$sum": {"$abs": "$quantita"}},
                        "fatt": {"$sum": {"$abs": "$totale"}},
                        "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}},
                        "giorni": {"$addToSet": "$data"}}},
            {"$project": {"qty": 1, "fatt": 1, "costo": 1, "ordini": {"$size": "$giorni"}}},
        ]).to_list(500)
        prezzi = [c['fatt'] / c['qty'] for c in clienti if c['qty']]
        med = median(prezzi) if prezzi else 0
        mio = next((c for c in clienti if c['_id'] == cliente), None) if cliente else None

        if modulo == "sotto_prezzo" and mio:
            p_cli = mio['fatt'] / mio['qty'] if mio['qty'] else 0
            spiegazione = (
                f"{cliente} paga {prodotto} {_eur(p_cli)}, mentre la mediana degli altri "
                f"{len(clienti) - 1} clienti e' {_eur(med)} ({(med - p_cli) / med * 100:.1f}% in piu'). "
                f"Nel periodo ha comprato {_q(mio['qty'])} pezzi in {mio['ordini']} ordini per {_eur(mio['fatt'])}: "
                f"allineando il prezzo alla mediana recupereresti {_eur((med - p_cli) * mio['qty'])}, "
                f"con un margine che passerebbe dal "
                f"{((mio['fatt'] - mio['costo']) / mio['costo'] * 100) if mio['costo'] else 0:.1f}% al "
                f"{((med * mio['qty'] - mio['costo']) / mio['costo'] * 100) if mio['costo'] else 0:.1f}%. "
                f"Nella classifica sotto vedi cosa pagano tutti gli altri: usala per giustificare il ritocco."
            )
            azione = f"Proponi a {cliente} il passaggio a {_eur(med)}, anche graduale."
        elif modulo == "sconto_quantita_vendita" and mio:
            q_ord = mio['qty'] / mio['ordini'] if mio['ordini'] else mio['qty']
            med_ord = median([(c['qty'] / c['ordini']) if c['ordini'] else c['qty'] for c in clienti])
            spiegazione = (
                f"{cliente} compra {prodotto} spesso ma in piccole quantita': {mio['ordini']} ordini nel periodo, "
                f"in media {_q(q_ord)} pezzi per volta, contro una mediana di mercato di {_q(med_ord)}. "
                f"Portandolo verso la quantita' mediana su ogni ordine il venduto crescerebbe di circa "
                f"{_eur((med_ord - q_ord) * mio['ordini'] * (med or 0))} nel periodo. "
                f"Essendo gia' un cliente fidelizzato sul prodotto, un prezzo dedicato sul lotto piu' grande "
                f"e' la leva piu' semplice. Sotto trovi tutti i suoi acquisti del prodotto."
            )
            azione = f"Offri a {cliente} un prezzo dedicato sul lotto da {_q(med_ord)} pezzi."
            righe_v = await db.vendite.find(
                {"prodotto_nome": prodotto, "cliente_nome": cliente, "data": {"$gte": start, "$lte": end}},
                {"_id": 0, "data": 1, "quantita": 1, "totale": 1}).sort([("data", -1)]).to_list(100)
            tabelle.append(T(f"Acquisti di {cliente}", ["Data", "Qtà", "Prezzo", "Totale"],
                             [[r['data'], _q(abs(r['quantita'])),
                               _eur(abs(r.get('totale', 0)) / abs(r['quantita']) if r['quantita'] else 0),
                               _eur(abs(r.get('totale', 0)))] for r in righe_v]))
        elif modulo == "margine_calo":
            spiegazione = (
                f"Il margine di {prodotto} e' peggiorato rispetto allo stesso periodo dell'anno scorso. "
                f"Nella tabella mensile qui sotto puoi vedere esattamente quando il costo del lotto e' salito e se "
                f"il prezzo di vendita lo ha seguito: se la linea del costo sale e quella del prezzo resta piatta, "
                f"il margine e' stato eroso. Nella classifica dei clienti vedi a chi stai applicando i prezzi piu' "
                f"bassi: sono i primi su cui intervenire per riportare il margine ai livelli precedenti."
            )
            azione = "Adegua il prezzo di vendita al nuovo costo, partendo dai clienti sotto la mediana."

        if prezzi:
            tabelle.append(T("Prezzo applicato a ogni cliente (dal piu' alto)",
                             ["Cliente", "Prezzo", "vs mediana", "Qtà", "Ordini", "Fatturato", "Margine %"],
                             [[c['_id'], _eur(c['fatt'] / c['qty']),
                               f"{((c['fatt'] / c['qty']) / med - 1) * 100:+.1f}%" if med else '—',
                               _q(c['qty']), c['ordini'], _eur(c['fatt']),
                               f"{(c['fatt'] - c['costo']) / c['costo'] * 100:.1f}%" if c['costo'] else '—']
                              for c in sorted(clienti, key=lambda x: -(x['fatt'] / x['qty'] if x['qty'] else 0))]))
        serie = await serie_mensile_prodotto(prodotto)
        if serie:
            tabelle.append(T("Andamento mensile (prezzo di vendita e costo del lotto)",
                             ["Mese", "Qtà", "Prezzo vendita", "Costo lotto", "Prezzo acquisto", "Margine %"],
                             [[s['mese'], _q(s['qty']), _eur(s['prezzo_vendita']), _eur(s['costo']),
                               _eur(s['prezzo_acquisto']),
                               f"{s['margine']:.1f}%" if s['margine'] is not None else '—'] for s in serie]))

    elif modulo in ("clienti_calo", "clienti_margine_basso"):
        if not cliente:
            raise HTTPException(status_code=400, detail="Cliente richiesto")

        async def agg(s, e):
            rows = await db.vendite.aggregate([
                {"$match": {"cliente_nome": cliente, "data": {"$gte": s, "$lte": e}}},
                {"$group": {"_id": "$prodotto_nome", "qty": {"$sum": {"$abs": "$quantita"}},
                            "fatt": {"$sum": {"$abs": "$totale"}},
                            "costo": {"$sum": {"$ifNull": ["$costo_fifo", 0]}}}},
            ]).to_list(2000)
            return {r['_id']: r for r in rows if r['_id']}

        ora = await agg(start, end)
        prima = await agg(ly_start, ly_end)
        f_ora = sum(r['fatt'] for r in ora.values())
        f_prima = sum(r['fatt'] for r in prima.values())
        costo_ora = sum(r['costo'] for r in ora.values())

        if modulo == "clienti_calo":
            persi = [(p, r['fatt']) for p, r in prima.items() if p not in ora]
            persi.sort(key=lambda x: -x[1])
            calati = [(p, prima[p]['fatt'], r['fatt']) for p, r in ora.items()
                      if p in prima and r['fatt'] < prima[p]['fatt'] * 0.8]
            calati.sort(key=lambda x: -(x[1] - x[2]))
            spiegazione = (
                f"{cliente} nel periodo ha comprato per {_eur(f_ora)} contro {_eur(f_prima)} dello stesso periodo "
                f"dell'anno scorso: {_eur(f_prima - f_ora)} in meno "
                f"({((f_ora - f_prima) / f_prima * 100) if f_prima else 0:.1f}%). "
                f"Ha smesso di comprare {len(persi)} prodotti (i primi valgono "
                f"{_eur(sum(v for _, v in persi[:5]))}) e ne ha ridotti altri {len(calati)}. "
                f"Sapere esattamente quali referenze sono uscite dal suo ordine ti permette di ripartire da quelle: "
                f"spesso e' un problema di prezzo su un singolo articolo o di un concorrente entrato su una linea."
            )
            azione = (f"Richiama {cliente} proponendo i prodotti persi, partendo da "
                      f"{persi[0][0] if persi else 'quelli a maggior valore'}.")
            tabelle.append(T("Prodotti che ha smesso di comprare",
                             ["Prodotto", "Fatturato anno prec.", "Qtà anno prec."],
                             [[p, _eur(v), _q(prima[p]['qty'])] for p, v in persi[:25]]))
            tabelle.append(T("Prodotti in forte calo",
                             ["Prodotto", "Anno prec.", "Periodo sel.", "Differenza"],
                             [[p, _eur(a), _eur(b), _eur(a - b)] for p, a, b in calati[:25]]))
        else:
            marg = ((f_ora - costo_ora) / costo_ora * 100) if costo_ora else 0
            spiegazione = (
                f"{cliente} vale {_eur(f_ora)} di fatturato nel periodo ma con un margine del {marg:.1f}%: "
                f"la merce che gli hai venduto ti e' costata {_eur(costo_ora)} (costo reale dei lotti). "
                f"Il problema non e' il cliente in se', ma il mix: nella tabella sotto trovi i prodotti che gli "
                f"vendi con il margine piu' basso, ed e' su quei pochi articoli che conviene ritoccare il prezzo "
                f"o proporre un'alternativa piu' redditizia, senza toccare il resto del listino."
            )
            azione = "Ritocca il prezzo sui 3-5 prodotti a margine peggiore o sostituiscili con alternative migliori."

        prodotti_rows = sorted(ora.items(),
                               key=lambda x: ((x[1]['fatt'] - x[1]['costo']) / x[1]['costo'] * 100
                                              if x[1]['costo'] else 9999))
        tabelle.append(T("Prodotti acquistati dal cliente nel periodo",
                         ["Prodotto", "Qtà", "Prezzo medio", "Fatturato", "Costo lotti", "Margine %", "Anno prec."],
                         [[p, _q(r['qty']), _eur(r['fatt'] / r['qty']) if r['qty'] else '—', _eur(r['fatt']),
                           _eur(r['costo']),
                           f"{(r['fatt'] - r['costo']) / r['costo'] * 100:.1f}%" if r['costo'] else '—',
                           _eur(prima[p]['fatt']) if p in prima else '—'] for p, r in prodotti_rows[:40]]))
    else:
        raise HTTPException(status_code=400, detail=f"Modulo '{modulo}' non riconosciuto")

    return {
        "modulo": modulo, "titolo": titolo,
        "periodo": {"start": start, "end": end, "ly_start": ly_start, "ly_end": ly_end},
        "spiegazione": spiegazione, "azione": azione, "tabelle": tabelle,
    }
