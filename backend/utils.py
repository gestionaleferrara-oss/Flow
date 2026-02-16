from datetime import datetime
import re
import csv
import io

from database import db
from models import Cliente, Fornitore, Prodotto, Vendita, Ordine


def parse_italian_date(date_str: str) -> str:
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    date_str = str(date_str).strip()
    if ' ' in date_str and ':' in date_str:
        try:
            parsed = datetime.strptime(date_str.split(' ')[0], "%Y-%m-%d")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass
    formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d.%m.%Y", "%Y/%m/%d", "%d %m %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now().strftime("%Y-%m-%d")


def parse_float(value: str) -> float:
    if not value:
        return 0.0
    value = str(value).strip()
    value = re.sub(r'[€\s\x80]', '', value)
    if not value or value == '-':
        return 0.0
    if ',' in value and '.' in value:
        value = value.replace('.', '').replace(',', '.')
    elif ',' in value:
        value = value.replace(',', '.')
    elif '.' in value:
        parts = value.split('.')
        if len(parts) == 2 and len(parts[1]) == 3 and parts[1].isdigit():
            value = value.replace('.', '')
    try:
        return float(value)
    except ValueError:
        return 0.0


def serialize_doc(doc: dict) -> dict:
    if '_id' in doc:
        del doc['_id']
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc


def auto_detect_columns(headers: list) -> dict:
    mapping = {
        'movimento': None, 'data': None, 'codice_cliente_fornitore': None,
        'nome_cliente_fornitore': None, 'codice_prodotto': None, 'nome_prodotto': None,
        'quantita': None, 'importo_unitario': None, 'importo_totale': None, 'causale': None
    }
    for i, header in enumerate(headers):
        h = header.lower().strip()
        if 'movimento' in h or 'tipo' in h:
            mapping['movimento'] = header
        elif h == 'data' or 'data' in h:
            mapping['data'] = header
        elif 'codice cl' in h or 'cod. cl' in h or 'cod cl' in h:
            mapping['codice_cliente_fornitore'] = header
        elif 'decodifica cl' in h or 'nome cl' in h or 'cliente' in h:
            mapping['nome_cliente_fornitore'] = header
        elif h == 'codice' or (('codice' in h or 'cod' in h) and 'cl' not in h and 'fo' not in h):
            mapping['codice_prodotto'] = header
        elif h == 'decodifica' or ('decodifica' in h and 'cl' not in h and 'fo' not in h):
            mapping['nome_prodotto'] = header
        elif 'quantit' in h or 'qty' in h or 'qta' in h:
            mapping['quantita'] = header
        elif 'importo unitario' in h or 'prezzo' in h or 'prezzo unitario' in h or 'unit' in h:
            mapping['importo_unitario'] = header
        elif 'importo totale' in h or 'totale' in h:
            mapping['importo_totale'] = header
        elif 'causale' in h:
            mapping['causale'] = header
    return mapping


async def process_csv_row(row: dict, stats: dict, col_mapping: dict, cache: dict):
    movimento = row.get(col_mapping['movimento'] or 'Movimento', '').strip()
    data = parse_italian_date(row.get(col_mapping['data'] or 'Data', ''))
    codice_cliente_fornitore = row.get(col_mapping['codice_cliente_fornitore'] or 'Codice Cl./Fo.', '').strip()
    nome_cliente_fornitore = row.get(col_mapping['nome_cliente_fornitore'] or 'Decodifica Cl./Fo.', '').strip()
    codice_prodotto = row.get(col_mapping['codice_prodotto'] or 'Codice', '').strip()
    nome_prodotto = row.get(col_mapping['nome_prodotto'] or 'Decodifica', '').strip()

    quantita_val = '0'
    for key in row.keys():
        if 'quantit' in key.lower() or 'qty' in key.lower():
            quantita_val = row[key]
            break
    if col_mapping['quantita']:
        quantita_val = row.get(col_mapping['quantita'], quantita_val)
    quantita = parse_float(quantita_val)

    importo_unitario = parse_float(row.get(col_mapping['importo_unitario'] or 'Importo Unitario', '0'))
    importo_totale = parse_float(row.get(col_mapping['importo_totale'] or 'Importo Totale', '0'))
    causale = row.get(col_mapping['causale'] or 'Causale', '').strip().upper()

    if not nome_prodotto and not nome_cliente_fornitore:
        return

    movimento_upper = movimento.upper()
    is_vendita = movimento_upper == 'SCARICO' and ('VEN' in causale or causale == 'VENDITA')
    is_acquisto = movimento_upper == 'CARICO' and ('ACQ' in causale or 'C/ACQUISTO' in causale)
    is_rettifica = 'RETTIFIC' in causale
    is_cessione = 'CESSIONE' in causale or 'OMAGGIO' in causale or 'CAMPIONE' in causale
    is_reso = 'RESO' in causale
    is_trasferimento = 'TRASFERIMENTO' in causale
    is_vuotati = 'VUOTATI' in causale
    is_commissione = 'COMMISSIONE' in causale

    quantita = abs(quantita)
    importo_totale = abs(importo_totale)
    importo_unitario = abs(importo_unitario)
    qty_change = quantita if movimento_upper == 'CARICO' else -quantita
    if is_reso and 'ACQUISTI' in causale:
        qty_change = -quantita

    if is_vendita and nome_cliente_fornitore:
        if nome_cliente_fornitore not in cache['clienti']:
            cliente = Cliente(nome=nome_cliente_fornitore, codice=codice_cliente_fornitore)
            await db.clienti.insert_one(serialize_doc(cliente.model_dump()))
            cache['clienti'][nome_cliente_fornitore] = cliente.id
            stats['new_clienti'] += 1
        else:
            stats['existing_clienti'] += 1
        cliente_id = cache['clienti'][nome_cliente_fornitore]
        vendita = Vendita(
            data=data, cliente_id=cliente_id, cliente_nome=nome_cliente_fornitore,
            prodotto_nome=nome_prodotto, quantita=quantita,
            prezzo_unitario=importo_unitario, totale=importo_totale, movimento=movimento, causale=causale
        )
        cache['vendite_batch'].append(serialize_doc(vendita.model_dump()))
        stats['vendite_created'] += 1

    elif is_acquisto and nome_cliente_fornitore:
        if nome_cliente_fornitore not in cache['fornitori']:
            fornitore = Fornitore(nome=nome_cliente_fornitore, codice=codice_cliente_fornitore)
            await db.fornitori.insert_one(serialize_doc(fornitore.model_dump()))
            cache['fornitori'][nome_cliente_fornitore] = fornitore.id
            stats['new_fornitori'] += 1
        else:
            stats['existing_fornitori'] += 1
        fornitore_id = cache['fornitori'][nome_cliente_fornitore]
        ordine = Ordine(
            data=data, fornitore_id=fornitore_id, fornitore_nome=nome_cliente_fornitore,
            prodotto_nome=nome_prodotto, quantita=quantita,
            prezzo_unitario=importo_unitario, totale=importo_totale
        )
        cache['ordini_batch'].append(serialize_doc(ordine.model_dump()))
        stats['ordini_created'] += 1

    elif is_cessione and nome_cliente_fornitore:
        if nome_cliente_fornitore not in cache['clienti']:
            cliente = Cliente(nome=nome_cliente_fornitore, codice=codice_cliente_fornitore)
            await db.clienti.insert_one(serialize_doc(cliente.model_dump()))
            cache['clienti'][nome_cliente_fornitore] = cliente.id
            stats['new_clienti'] += 1
        cliente_id = cache['clienti'].get(nome_cliente_fornitore)
        vendita = Vendita(
            data=data, cliente_id=cliente_id, cliente_nome=nome_cliente_fornitore,
            prodotto_nome=nome_prodotto, quantita=quantita,
            prezzo_unitario=0, totale=0, movimento=movimento, causale=causale
        )
        cache['vendite_batch'].append(serialize_doc(vendita.model_dump()))
        stats['cessioni_created'] = stats.get('cessioni_created', 0) + 1

    elif is_reso and nome_cliente_fornitore:
        if nome_cliente_fornitore not in cache['fornitori']:
            fornitore = Fornitore(nome=nome_cliente_fornitore, codice=codice_cliente_fornitore)
            await db.fornitori.insert_one(serialize_doc(fornitore.model_dump()))
            cache['fornitori'][nome_cliente_fornitore] = fornitore.id
            stats['new_fornitori'] += 1
        fornitore_id = cache['fornitori'].get(nome_cliente_fornitore)
        ordine = Ordine(
            data=data, fornitore_id=fornitore_id, fornitore_nome=nome_cliente_fornitore,
            prodotto_nome=nome_prodotto, quantita=-quantita,
            prezzo_unitario=importo_unitario, totale=-importo_totale
        )
        cache['ordini_batch'].append(serialize_doc(ordine.model_dump()))
        stats['resi_created'] = stats.get('resi_created', 0) + 1
    else:
        stats['other_movements'] = stats.get('other_movements', 0) + 1

    if nome_prodotto:
        if nome_prodotto not in cache['prodotti']:
            prodotto = Prodotto(nome=nome_prodotto, codice=codice_prodotto, prezzo_medio=importo_unitario, quantita=qty_change)
            await db.prodotti.insert_one(serialize_doc(prodotto.model_dump()))
            cache['prodotti'][nome_prodotto] = {'id': prodotto.id, 'prezzo_medio': importo_unitario, 'quantita': qty_change}
            stats['new_prodotti'] += 1
        else:
            cache['prodotti'][nome_prodotto]['quantita'] = cache['prodotti'][nome_prodotto].get('quantita', 0) + qty_change
            if is_acquisto and importo_unitario > 0:
                cache['prodotti'][nome_prodotto]['prezzo_medio'] = importo_unitario
            stats['existing_prodotti'] += 1
