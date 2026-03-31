from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List, Optional
import pandas as pd
import csv
import io

from database import db, logger
from utils import auto_detect_columns, process_csv_row

router = APIRouter()


@router.post("/pulisci-duplicati")
async def pulisci_duplicati():
    """
    Remove duplicate sales and orders from the database.
    Duplicates are identified by: data + cliente/fornitore + prodotto + quantita + totale
    """
    # Clean vendite duplicates
    vendite_pipeline = [
        {"$group": {
            "_id": {
                "data": "$data",
                "cliente_nome": "$cliente_nome",
                "prodotto_nome": "$prodotto_nome",
                "quantita": "$quantita",
                "totale": "$totale"
            },
            "ids": {"$push": "$_id"},
            "count": {"$sum": 1}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]
    
    duplicati_vendite = await db.vendite.aggregate(vendite_pipeline).to_list(100000)
    vendite_rimossi = 0
    
    for dup in duplicati_vendite:
        # Keep the first one, delete the rest
        ids_to_delete = dup['ids'][1:]  # Skip first ID
        if ids_to_delete:
            result = await db.vendite.delete_many({"_id": {"$in": ids_to_delete}})
            vendite_rimossi += result.deleted_count
    
    # Clean ordini duplicates
    ordini_pipeline = [
        {"$group": {
            "_id": {
                "data": "$data",
                "fornitore_nome": "$fornitore_nome",
                "prodotto_nome": "$prodotto_nome",
                "quantita": "$quantita",
                "totale": "$totale"
            },
            "ids": {"$push": "$_id"},
            "count": {"$sum": 1}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]
    
    duplicati_ordini = await db.ordini.aggregate(ordini_pipeline).to_list(100000)
    ordini_rimossi = 0
    
    for dup in duplicati_ordini:
        ids_to_delete = dup['ids'][1:]
        if ids_to_delete:
            result = await db.ordini.delete_many({"_id": {"$in": ids_to_delete}})
            ordini_rimossi += result.deleted_count
    
    return {
        "success": True,
        "vendite_duplicati_rimossi": vendite_rimossi,
        "ordini_duplicati_rimossi": ordini_rimossi,
        "message": f"Rimossi {vendite_rimossi} vendite duplicate e {ordini_rimossi} ordini duplicati"
    }


@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    filename = file.filename.lower()
    if not filename.endswith('.csv') and not filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Il file deve essere in formato CSV o XLSX")

    stats = {
        'new_clienti': 0, 'existing_clienti': 0, 'new_fornitori': 0, 'existing_fornitori': 0,
        'new_prodotti': 0, 'existing_prodotti': 0, 'vendite_created': 0, 'ordini_created': 0,
        'rows_processed': 0, 'rows_skipped': 0, 'columns_detected': {}, 'errors': []
    }

    try:
        content = await file.read()
        rows, headers = _parse_file(content, filename)
        col_mapping = auto_detect_columns(headers)
        stats['columns_detected'] = {k: v for k, v in col_mapping.items() if v is not None}

        await db.vendite.delete_many({})
        await db.ordini.delete_many({})
        await db.prodotti.update_many({}, {"$set": {"quantita": 0}})

        cache = await _build_cache()
        BATCH_SIZE = 500

        for row in rows:
            try:
                await process_csv_row(row, stats, col_mapping, cache)
                stats['rows_processed'] += 1
                if len(cache['vendite_batch']) >= BATCH_SIZE:
                    await db.vendite.insert_many(cache['vendite_batch'])
                    cache['vendite_batch'] = []
                if len(cache['ordini_batch']) >= BATCH_SIZE:
                    await db.ordini.insert_many(cache['ordini_batch'])
                    cache['ordini_batch'] = []
            except Exception as e:
                stats['errors'].append(f"Riga {stats['rows_processed'] + 1}: {str(e)}")

        await _flush_and_update(cache)
        return {"success": True, "message": "File elaborato con successo", "stats": stats}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-multiple")
async def upload_multiple_files(files: List[UploadFile] = File(...), mode: Optional[str] = Form("incremental")):
    total_stats = {
        'new_clienti': 0, 'existing_clienti': 0, 'new_fornitori': 0, 'existing_fornitori': 0,
        'new_prodotti': 0, 'existing_prodotti': 0, 'vendite_created': 0, 'ordini_created': 0,
        'cessioni_created': 0, 'resi_created': 0, 'other_movements': 0,
        'rows_processed': 0, 'files_processed': 0, 'errors': []
    }

    # Only delete if mode is 'full'
    if mode == 'full':
        await db.vendite.delete_many({})
        await db.ordini.delete_many({})
        await db.prodotti.update_many({}, {"$set": {"quantita": 0}})
        cache = await _build_cache()
    else:
        cache = await _build_cache_with_quantities()
    
    BATCH_SIZE = 500

    for file in files:
        filename = file.filename.lower()
        if not filename.endswith('.csv') and not filename.endswith('.xlsx'):
            total_stats['errors'].append(f"File {file.filename}: formato non supportato")
            continue
        try:
            content = await file.read()
            rows, headers = _parse_file(content, filename)
            col_mapping = auto_detect_columns(headers)
            for row in rows:
                try:
                    await process_csv_row(row, total_stats, col_mapping, cache)
                    total_stats['rows_processed'] += 1
                    if len(cache['vendite_batch']) >= BATCH_SIZE:
                        await db.vendite.insert_many(cache['vendite_batch'])
                        cache['vendite_batch'] = []
                    if len(cache['ordini_batch']) >= BATCH_SIZE:
                        await db.ordini.insert_many(cache['ordini_batch'])
                        cache['ordini_batch'] = []
                except Exception as e:
                    total_stats['errors'].append(f"File {file.filename}, riga {total_stats['rows_processed']}: {str(e)}")
            total_stats['files_processed'] += 1
        except Exception as e:
            total_stats['errors'].append(f"File {file.filename}: {str(e)}")

    # Use appropriate flush based on mode
    if mode == 'full':
        await _flush_and_update(cache)
    else:
        await _flush_and_update_incremental(cache)
    return {"success": True, "message": f"Elaborati {total_stats['files_processed']} file con successo", "stats": total_stats}


@router.post("/upload-incremental")
async def upload_incremental(file: UploadFile = File(...)):
    """
    Upload sales/orders incrementally WITHOUT deleting existing data.
    Updates stock quantities incrementally.
    """
    filename = file.filename.lower()
    if not filename.endswith('.csv') and not filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Il file deve essere in formato CSV o XLSX")

    stats = {
        'new_clienti': 0, 'existing_clienti': 0, 'new_fornitori': 0, 'existing_fornitori': 0,
        'new_prodotti': 0, 'existing_prodotti': 0, 'vendite_created': 0, 'ordini_created': 0,
        'rows_processed': 0, 'rows_skipped': 0, 'columns_detected': {}, 'errors': []
    }

    try:
        content = await file.read()
        rows, headers = _parse_file(content, filename)
        col_mapping = auto_detect_columns(headers)
        stats['columns_detected'] = {k: v for k, v in col_mapping.items() if v is not None}

        # Build cache with CURRENT quantities from DB
        cache = await _build_cache_with_quantities()
        BATCH_SIZE = 500

        for row in rows:
            try:
                await process_csv_row(row, stats, col_mapping, cache)
                stats['rows_processed'] += 1
                if len(cache['vendite_batch']) >= BATCH_SIZE:
                    await db.vendite.insert_many(cache['vendite_batch'])
                    cache['vendite_batch'] = []
                if len(cache['ordini_batch']) >= BATCH_SIZE:
                    await db.ordini.insert_many(cache['ordini_batch'])
                    cache['ordini_batch'] = []
            except Exception as e:
                stats['errors'].append(f"Riga {stats['rows_processed'] + 1}: {str(e)}")

        await _flush_and_update_incremental(cache)
        
        return {
            "success": True,
            "message": f"Aggiunti {stats['vendite_created']} vendite, {stats['ordini_created']} ordini. Magazzino aggiornato.",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error in incremental upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _parse_file(content: bytes, filename: str):
    rows = []
    headers = []
    if filename.endswith('.xlsx'):
        df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
        df.columns = [str(c).strip() for c in df.columns]
        unnamed_cols = sum(1 for c in df.columns if 'unnamed' in c.lower())
        if unnamed_cols > len(df.columns) / 2 and len(df) > 0:
            new_headers = [str(v).strip() if pd.notna(v) else f'col_{i}' for i, v in enumerate(df.iloc[0])]
            df.columns = new_headers
            df = df.iloc[1:].reset_index(drop=True)
        headers = list(df.columns)
        for _, row in df.iterrows():
            row_dict = {}
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    row_dict[col] = ''
                elif isinstance(val, (int, float)):
                    row_dict[col] = str(val)
                else:
                    row_dict[col] = str(val).strip()
            rows.append(row_dict)
    else:
        for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise HTTPException(status_code=400, detail="Impossibile decodificare il file")
        first_line = text_content.split('\n')[0]
        delimiter = ';' if ';' in first_line else ','
        csv_reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
        headers = csv_reader.fieldnames or []
        rows = list(csv_reader)
    return rows, headers


async def _build_cache():
    cache = {'clienti': {}, 'fornitori': {}, 'prodotti': {}, 'vendite_batch': [], 'ordini_batch': []}
    existing_clienti = await db.clienti.find({}, {"_id": 0, "id": 1, "nome": 1}).to_list(10000)
    for c in existing_clienti:
        cache['clienti'][c['nome']] = c['id']
    existing_fornitori = await db.fornitori.find({}, {"_id": 0, "id": 1, "nome": 1}).to_list(10000)
    for f in existing_fornitori:
        cache['fornitori'][f['nome']] = f['id']
    existing_prodotti = await db.prodotti.find({}, {"_id": 0, "id": 1, "nome": 1, "prezzo_medio": 1, "quantita": 1}).to_list(10000)
    for p in existing_prodotti:
        cache['prodotti'][p['nome']] = {'id': p['id'], 'prezzo_medio': p.get('prezzo_medio', 0), 'quantita': 0}
    return cache


async def _build_cache_with_quantities():
    """Build cache preserving existing quantities from DB"""
    cache = {'clienti': {}, 'fornitori': {}, 'prodotti': {}, 'vendite_batch': [], 'ordini_batch': [], 'qty_changes': {}}
    existing_clienti = await db.clienti.find({}, {"_id": 0, "id": 1, "nome": 1}).to_list(10000)
    for c in existing_clienti:
        cache['clienti'][c['nome']] = c['id']
    existing_fornitori = await db.fornitori.find({}, {"_id": 0, "id": 1, "nome": 1}).to_list(10000)
    for f in existing_fornitori:
        cache['fornitori'][f['nome']] = f['id']
    existing_prodotti = await db.prodotti.find({}, {"_id": 0, "id": 1, "nome": 1, "prezzo_medio": 1, "quantita": 1}).to_list(10000)
    for p in existing_prodotti:
        # Keep existing quantity, track changes separately
        cache['prodotti'][p['nome']] = {
            'id': p['id'], 
            'prezzo_medio': p.get('prezzo_medio', 0), 
            'quantita': p.get('quantita', 0),
            'qty_change': 0
        }
    return cache


async def _flush_and_update(cache):
    if cache['vendite_batch']:
        await db.vendite.insert_many(cache['vendite_batch'])
    if cache['ordini_batch']:
        await db.ordini.insert_many(cache['ordini_batch'])
    for nome_prodotto, prod_data in cache['prodotti'].items():
        if isinstance(prod_data, dict):
            quantita = max(0, prod_data.get('quantita', 0))  # No negative quantities
            prezzo_medio = prod_data.get('prezzo_medio', 0)
            valore_scorte = quantita * prezzo_medio if prezzo_medio > 0 else 0
            await db.prodotti.update_one(
                {"nome": nome_prodotto},
                {"$set": {
                    "quantita": quantita, 
                    "prezzo_medio": prezzo_medio,
                    "valore_scorte": valore_scorte
                }}
            )


async def _flush_and_update_incremental(cache):
    """Update DB with incremental changes, avoiding duplicates using batch checks"""
    if cache['vendite_batch']:
        # Build set of existing keys first (batch query)
        batch_keys = [
            {"data": v.get("data"), "cliente_nome": v.get("cliente_nome"), 
             "prodotto_nome": v.get("prodotto_nome"), "quantita": v.get("quantita"), "totale": v.get("totale")}
            for v in cache['vendite_batch']
        ]
        
        if batch_keys:
            existing_cursor = db.vendite.find(
                {"$or": batch_keys},
                {"_id": 0, "data": 1, "cliente_nome": 1, "prodotto_nome": 1, "quantita": 1, "totale": 1}
            )
            existing_set = set()
            async for doc in existing_cursor:
                key = (doc.get("data"), doc.get("cliente_nome"), doc.get("prodotto_nome"), 
                       doc.get("quantita"), doc.get("totale"))
                existing_set.add(key)
            
            # Filter out duplicates
            new_vendite = []
            for v in cache['vendite_batch']:
                key = (v.get("data"), v.get("cliente_nome"), v.get("prodotto_nome"), 
                       v.get("quantita"), v.get("totale"))
                if key not in existing_set:
                    new_vendite.append(v)
            
            if new_vendite:
                await db.vendite.insert_many(new_vendite)
            
    if cache['ordini_batch']:
        # Build set of existing keys first (batch query)
        batch_keys = [
            {"data": o.get("data"), "fornitore_nome": o.get("fornitore_nome"),
             "prodotto_nome": o.get("prodotto_nome"), "quantita": o.get("quantita"), "totale": o.get("totale")}
            for o in cache['ordini_batch']
        ]
        
        if batch_keys:
            existing_cursor = db.ordini.find(
                {"$or": batch_keys},
                {"_id": 0, "data": 1, "fornitore_nome": 1, "prodotto_nome": 1, "quantita": 1, "totale": 1}
            )
            existing_set = set()
            async for doc in existing_cursor:
                key = (doc.get("data"), doc.get("fornitore_nome"), doc.get("prodotto_nome"),
                       doc.get("quantita"), doc.get("totale"))
                existing_set.add(key)
            
            # Filter out duplicates
            new_ordini = []
            for o in cache['ordini_batch']:
                key = (o.get("data"), o.get("fornitore_nome"), o.get("prodotto_nome"),
                       o.get("quantita"), o.get("totale"))
                if key not in existing_set:
                    new_ordini.append(o)
            
            if new_ordini:
                await db.ordini.insert_many(new_ordini)
    
    for nome_prodotto, prod_data in cache['prodotti'].items():
        if isinstance(prod_data, dict):
            # Add qty_change to existing quantity
            existing_qty = prod_data.get('quantita', 0)
            qty_change = prod_data.get('qty_change', 0)
            new_qty = max(0, existing_qty + qty_change)
            prezzo_medio = prod_data.get('prezzo_medio', 0)
            valore_scorte = new_qty * prezzo_medio if prezzo_medio > 0 else 0
            
            if qty_change != 0:  # Only update if there was a change
                await db.prodotti.update_one(
                    {"nome": nome_prodotto},
                    {"$set": {
                        "quantita": new_qty,
                        "prezzo_medio": prezzo_medio,
                        "valore_scorte": valore_scorte
                    }}
                )

