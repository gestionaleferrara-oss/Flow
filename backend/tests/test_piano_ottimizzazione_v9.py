"""Test per la nuova pagina Ottimizzazione (piano acquisti/vendite basato su finestra N giorni)."""
import os
from datetime import datetime, timedelta

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://magazzino-stock.preview.emergentagent.com').rstrip('/')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']


@pytest.fixture(scope="module")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


def _iso(d):
    return d.strftime("%Y-%m-%d")


# --- Test periodo/finestra ---

@pytest.mark.parametrize("giorni", [7, 30, 90])
def test_periodo_finestra(giorni):
    r = requests.get(f"{BASE_URL}/api/ottimizzazione/piano", params={"tipo": "acquisti", "giorni": giorni}, timeout=60)
    assert r.status_code == 200, r.text
    p = r.json()['periodo']
    oggi = datetime.now()
    exp_fs = _iso(oggi)
    exp_fe = _iso(oggi + timedelta(days=giorni - 1))
    exp_ly_fs = _iso(oggi - timedelta(days=365))
    exp_ly_fe = _iso(oggi + timedelta(days=giorni - 1) - timedelta(days=365))
    assert p['futuro_start'] == exp_fs, f"futuro_start expected {exp_fs} got {p['futuro_start']}"
    assert p['futuro_end'] == exp_fe
    assert p['storico_start'] == exp_ly_fs
    assert p['storico_end'] == exp_ly_fe
    assert p['giorni'] == giorni


# --- Test acquisti: matematica ---

def test_acquisti_math_da_ordinare(db):
    r = requests.get(f"{BASE_URL}/api/ottimizzazione/piano", params={"tipo": "acquisti", "giorni": 30}, timeout=60)
    assert r.status_code == 200
    body = r.json()
    ordini = body['ordini']
    assert len(ordini) > 0, "Ci si aspetta almeno un ordine di acquisto"
    p = body['periodo']

    # Prendi qualche articolo campione (primo ordine, primi 3 articoli)
    campioni = []
    for o in ordini[:3]:
        for a in o['articoli'][:2]:
            campioni.append((o['fornitore'], a))
    assert campioni

    prodotti_map = {p['nome']: p.get('quantita', 0) or 0 for p in db.prodotti.find({}, {"_id": 0, "nome": 1, "quantita": 1})}

    for forn, a in campioni:
        nome = a['prodotto']
        # domanda_prevista = sum abs(quantita) vendite dell'anno scorso in finestra
        pipeline = [
            {"$match": {"prodotto_nome": nome, "cliente_nome": {"$nin": EXCLUDED_CLIENTS},
                        "data": {"$gte": p['storico_start'], "$lte": p['storico_end']}}},
            {"$group": {"_id": None, "qty": {"$sum": {"$abs": "$quantita"}}}}
        ]
        row = list(db.vendite.aggregate(pipeline))
        atteso = row[0]['qty'] if row else 0
        assert abs(a['domanda_prevista'] - atteso) <= 0.5, f"{nome}: domanda_prevista={a['domanda_prevista']} atteso~{atteso}"

        # da_ordinare = max(domanda - giacenza, 0), sempre > 0 in un ordine
        giac = prodotti_map.get(nome, 0)
        exp_da_ord = max(atteso - giac, 0)
        assert abs(a['da_ordinare'] - exp_da_ord) <= 0.5, f"{nome}: da_ordinare={a['da_ordinare']} atteso {exp_da_ord}"
        assert a['da_ordinare'] > 0, f"{nome}: da_ordinare deve essere > 0 negli ordini"

        # valore = prezzo_acquisto * da_ordinare
        if a['prezzo_acquisto']:
            exp_val = a['prezzo_acquisto'] * a['da_ordinare']
            assert abs(a['valore'] - exp_val) <= max(exp_val * 0.02, 1), f"{nome}: valore={a['valore']} atteso {exp_val}"

    # Totale ordine.valore == somma articoli.valore (arrotondato)
    for o in ordini[:5]:
        somma = sum(x['valore'] for x in o['articoli'])
        assert abs(o['valore'] - somma) <= max(somma * 0.02, 1), f"{o['fornitore']}: valore ordine {o['valore']} != somma {somma}"

    # Totali
    tot = body['totali']
    assert tot['fornitori'] == len(ordini)
    assert abs(tot['valore_ordini'] - sum(o['valore'] for o in ordini)) <= 1


def test_acquisti_best_fornitore(db):
    """Il fornitore consigliato deve essere il più conveniente (media ponderata su ultimi 365gg)."""
    r = requests.get(f"{BASE_URL}/api/ottimizzazione/piano", params={"tipo": "acquisti", "giorni": 30}, timeout=60)
    body = r.json()
    oggi = datetime.now()
    anno_start = _iso(oggi - timedelta(days=365))
    oggi_s = _iso(oggi)

    campioni = []
    for o in body['ordini']:
        if o['fornitore'] == "Fornitore da individuare":
            continue
        for a in o['articoli'][:1]:
            campioni.append((o['fornitore'], a['prodotto']))
        if len(campioni) >= 3:
            break

    for forn_atteso, nome in campioni:
        rows = list(db.ordini.aggregate([
            {"$match": {"prodotto_nome": nome, "data": {"$gte": anno_start, "$lte": oggi_s},
                        "quantita": {"$gt": 0}, "totale": {"$gt": 0}}},
            {"$group": {"_id": "$fornitore_nome", "q": {"$sum": "$quantita"}, "t": {"$sum": "$totale"}}}
        ]))
        prezzi = {r['_id']: r['t'] / r['q'] for r in rows if r['q'] > 0}
        if not prezzi:
            continue
        best = min(prezzi, key=prezzi.get)
        assert forn_atteso == best, f"{nome}: consigliato {forn_atteso}, atteso {best} (prezzi={prezzi})"


def test_acquisti_fornitore_ignoto_block():
    """Articoli senza storico fornitore vanno in 'Fornitore da individuare' (se esistono)."""
    r = requests.get(f"{BASE_URL}/api/ottimizzazione/piano", params={"tipo": "acquisti", "giorni": 90}, timeout=60)
    body = r.json()
    forns = [o['fornitore'] for o in body['ordini']]
    # Non forziamo la presenza, ma se c'è deve avere articoli
    for o in body['ordini']:
        if o['fornitore'] == "Fornitore da individuare":
            assert len(o['articoli']) > 0


# --- Test vendite ---

def test_vendite_struttura_e_gia_ordinato(db):
    r = requests.get(f"{BASE_URL}/api/ottimizzazione/piano", params={"tipo": "vendite", "giorni": 30}, timeout=60)
    assert r.status_code == 200
    body = r.json()
    assert body['tipo'] == 'vendite'
    ordini = body['ordini']
    assert len(ordini) > 0
    p = body['periodo']

    # Pick a client with articoli and verifica quantita_attesa
    ord0 = ordini[0]
    assert 'articoli' in ord0
    assert ord0['azione'] in ('CHIAMA ORA', 'CLIENTE FERMO', 'PROPONI', 'IN LINEA')

    cliente = ord0['cliente']
    art = ord0['articoli'][0]
    nome_p = art['prodotto']
    pipeline = [
        {"$match": {"cliente_nome": cliente, "prodotto_nome": nome_p,
                    "data": {"$gte": p['storico_start'], "$lte": p['storico_end']}}},
        {"$group": {"_id": None, "qty": {"$sum": {"$abs": "$quantita"}},
                    "fatt": {"$sum": {"$abs": "$totale"}}}}
    ]
    row = list(db.vendite.aggregate(pipeline))
    exp_qty = row[0]['qty'] if row else 0
    exp_fatt = row[0]['fatt'] if row else 0
    assert abs(art['quantita_attesa'] - exp_qty) <= 0.5
    assert abs(art['valore_atteso'] - exp_fatt) <= 1

    # gia_ordinato: true solo se cliente ha comprato quel prodotto in ultimi 60gg
    oggi = datetime.now()
    recente_start = _iso(oggi - timedelta(days=60))
    oggi_s = _iso(oggi)
    row_r = list(db.vendite.aggregate([
        {"$match": {"cliente_nome": cliente, "prodotto_nome": nome_p,
                    "data": {"$gte": recente_start, "$lte": oggi_s}}},
        {"$group": {"_id": None, "q": {"$sum": {"$abs": "$quantita"}}}}
    ]))
    ha_comprato = bool(row_r) and row_r[0]['q'] > 0
    assert art['gia_ordinato'] == ha_comprato, f"{cliente}/{nome_p}: gia_ordinato={art['gia_ordinato']} atteso {ha_comprato}"


def test_vendite_cliente_fermo(db):
    r = requests.get(f"{BASE_URL}/api/ottimizzazione/piano", params={"tipo": "vendite", "giorni": 30}, timeout=60)
    body = r.json()
    oggi = datetime.now()
    for prop in body['ordini']:
        if prop['azione'] == 'CLIENTE FERMO':
            gg = prop['giorni_da_ultimo_ordine']
            assert gg is not None and gg > 45, f"{prop['cliente']}: azione CLIENTE FERMO ma gg={gg}"


# --- Suggerimenti ---

@pytest.mark.parametrize("tipo", ["acquisti", "vendite"])
def test_suggerimenti_presenti(tipo):
    r = requests.get(f"{BASE_URL}/api/ottimizzazione/piano", params={"tipo": tipo, "giorni": 30}, timeout=60)
    body = r.json()
    sug = body.get('suggerimenti', [])
    assert isinstance(sug, list)
    assert len(sug) > 0, f"Nessun suggerimento per {tipo}"
    for s in sug:
        assert s.get('id') and s.get('titolo') and s.get('descrizione')
        assert s.get('voci') and len(s['voci']) > 0
        assert 'valore' in s
        # valore = somma coerente delle voci
        somma = sum(v.get('valore', 0) for v in s['voci'])
        assert abs(s['valore'] - somma) <= max(abs(somma) * 0.05, 5), f"{s['id']}: valore {s['valore']} != somma voci {somma}"
