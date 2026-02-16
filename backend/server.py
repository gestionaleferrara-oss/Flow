from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import csv
import io
import re
import httpx
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import asyncio
import pandas as pd

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# ======================= RSS NEWS SOURCES =======================
RSS_SOURCES = [
    {"name": "FreshPlaza", "url": "https://www.freshplaza.it/rss.xml", "categoria": "ortofrutta"},
    {"name": "Corriere Ortofrutticolo", "url": "https://www.corriereortofrutticolo.it/feed/", "categoria": "ortofrutta"},
]

# Myfruit.it does not have RSS; we scrape HTML instead
MYFRUIT_NEWS_URL = "https://www.myfruit.it/news-page/1"

# ======================= MARKET PRICE LINKS =======================
# These are dynamically scraped from FreshPlaza; this is the fallback cache
_market_price_cache = {"links": [], "last_updated": None}


# ======================= MODELS =======================

class BaseModelConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Cliente(BaseModelConfig):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    codice: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    note: Optional[str] = None
    fatturato_totale: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClienteCreate(BaseModel):
    nome: str
    codice: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    note: Optional[str] = None


class Fornitore(BaseModelConfig):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    codice: Optional[str] = None
    fatturato_totale: float = 0.0
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FornitoreCreate(BaseModel):
    nome: str
    codice: Optional[str] = None
    note: Optional[str] = None


class Prodotto(BaseModelConfig):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    codice: Optional[str] = None
    quantita: float = 0.0
    kg_per_pezzo: float = 0.0
    imballo: Optional[str] = None
    prezzo_medio: float = 0.0
    valore_scorte: float = 0.0
    scadenza: Optional[str] = None
    quantita_minima: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProdottoCreate(BaseModel):
    nome: str
    codice: Optional[str] = None
    quantita: float = 0.0
    kg_per_pezzo: float = 0.0
    imballo: Optional[str] = None
    prezzo_medio: float = 0.0
    scadenza: Optional[str] = None
    quantita_minima: float = 0.0


class Vendita(BaseModelConfig):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data: str
    cliente_id: Optional[str] = None
    cliente_nome: str
    prodotto_id: Optional[str] = None
    prodotto_nome: str
    quantita: float = 0.0
    prezzo_unitario: float = 0.0
    totale: float = 0.0
    movimento: Optional[str] = None
    causale: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Ordine(BaseModelConfig):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data: str
    fornitore_id: Optional[str] = None
    fornitore_nome: str
    prodotto_id: Optional[str] = None
    prodotto_nome: str
    quantita: float = 0.0
    kg_per_pezzo: float = 0.0
    totale_kg: float = 0.0
    prezzo_unitario: float = 0.0
    totale: float = 0.0
    data_inizio: Optional[str] = None
    data_fine: Optional[str] = None
    giorni_durata: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrdineCreate(BaseModel):
    fornitore_nome: str
    prodotto_nome: str
    quantita: float
    kg_per_pezzo: float
    prezzo_unitario: float
    data_inizio: Optional[str] = None
    data_fine: Optional[str] = None


class Notizia(BaseModelConfig):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    titolo: str
    descrizione: Optional[str] = None
    contenuto: Optional[str] = None
    url: Optional[str] = None
    immagine_url: Optional[str] = None
    fonte: str = "Sistema"
    categoria: str = "generale"
    data_pubblicazione: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotiziaCreate(BaseModel):
    titolo: str
    descrizione: Optional[str] = None
    contenuto: Optional[str] = None
    url: Optional[str] = None
    immagine_url: Optional[str] = None
    fonte: str = "Sistema"
    categoria: str = "generale"


class PrezzoMercato(BaseModel):
    nome: str
    url: str


# ======================= UTILITY FUNCTIONS =======================

def parse_italian_date(date_str: str) -> str:
    """Parse various date formats and return YYYY-MM-DD"""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    
    date_str = str(date_str).strip()
    
    # Handle pandas Timestamp strings like "2025-07-01 00:00:00"
    if ' ' in date_str and ':' in date_str:
        try:
            parsed = datetime.strptime(date_str.split(' ')[0], "%Y-%m-%d")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # Try various formats
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", 
        "%d.%m.%Y", "%Y/%m/%d", "%d %m %Y"
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return datetime.now().strftime("%Y-%m-%d")


def parse_float(value: str) -> float:
    """Parse string to float, handling Italian number format with thousand separators"""
    if not value:
        return 0.0
    
    value = str(value).strip()
    
    # Remove currency symbols (€, \x80 which is € in Windows-1252) and extra spaces
    value = re.sub(r'[€\s\x80]', '', value)
    
    # Check for empty string after cleaning
    if not value or value == '-':
        return 0.0
    
    # Handle Italian format:
    # - Comma (,) is decimal separator
    # - Period (.) is thousand separator
    # Examples: "4.497,50" -> 4497.50, "1,05" -> 1.05, "-13" -> -13
    
    # If we have both comma and period, period is thousand separator
    if ',' in value and '.' in value:
        # Remove thousand separators (periods) first, then replace comma with period
        value = value.replace('.', '').replace(',', '.')
    elif ',' in value:
        # Only comma present - it's the decimal separator
        value = value.replace(',', '.')
    # If only period is present, need to check if it's thousand or decimal
    elif '.' in value:
        # Count digits after the period
        parts = value.split('.')
        if len(parts) == 2:
            # If 3 digits after period, likely thousand separator (e.g., "4.497")
            if len(parts[1]) == 3 and parts[1].isdigit():
                value = value.replace('.', '')
            # Otherwise keep as decimal (e.g., "1.05")
    
    try:
        return float(value)
    except ValueError:
        return 0.0


def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document for JSON serialization"""
    if '_id' in doc:
        del doc['_id']
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc


# ======================= CSV PROCESSING =======================

def auto_detect_columns(headers: list) -> dict:
    """Auto-detect CSV columns by matching common patterns"""
    mapping = {
        'movimento': None,
        'data': None,
        'codice_cliente_fornitore': None,
        'nome_cliente_fornitore': None,
        'codice_prodotto': None,
        'nome_prodotto': None,
        'quantita': None,
        'importo_unitario': None,
        'importo_totale': None,
        'causale': None
    }
    
    for i, header in enumerate(headers):
        h = header.lower().strip()
        
        # Movimento
        if 'movimento' in h or 'tipo' in h:
            mapping['movimento'] = header
        # Data
        elif h == 'data' or 'data' in h:
            mapping['data'] = header
        # Codice Cliente/Fornitore
        elif 'codice cl' in h or 'cod. cl' in h or 'cod cl' in h:
            mapping['codice_cliente_fornitore'] = header
        # Nome Cliente/Fornitore
        elif 'decodifica cl' in h or 'nome cl' in h or 'cliente' in h:
            mapping['nome_cliente_fornitore'] = header
        # Codice Prodotto
        elif h == 'codice' or (('codice' in h or 'cod' in h) and 'cl' not in h and 'fo' not in h):
            mapping['codice_prodotto'] = header
        # Nome Prodotto / Decodifica
        elif h == 'decodifica' or ('decodifica' in h and 'cl' not in h and 'fo' not in h):
            mapping['nome_prodotto'] = header
        # Quantita - handles encoding issues with à
        elif 'quantit' in h or 'qty' in h or 'qta' in h:
            mapping['quantita'] = header
        # Importo Unitario (PREZZO)
        elif 'importo unitario' in h or 'prezzo' in h or 'prezzo unitario' in h or 'unit' in h:
            mapping['importo_unitario'] = header
        # Importo Totale (TOTALE PAGATO)
        elif 'importo totale' in h or 'totale' in h:
            mapping['importo_totale'] = header
        # Causale
        elif 'causale' in h:
            mapping['causale'] = header
    
    return mapping


async def process_csv_row(row: dict, stats: dict, col_mapping: dict, cache: dict):
    """Process a single CSV row and update database"""
    
    # Use auto-detected column mapping
    movimento = row.get(col_mapping['movimento'] or 'Movimento', '').strip()
    data = parse_italian_date(row.get(col_mapping['data'] or 'Data', ''))
    codice_cliente_fornitore = row.get(col_mapping['codice_cliente_fornitore'] or 'Codice Cl./Fo.', '').strip()
    nome_cliente_fornitore = row.get(col_mapping['nome_cliente_fornitore'] or 'Decodifica Cl./Fo.', '').strip()
    codice_prodotto = row.get(col_mapping['codice_prodotto'] or 'Codice', '').strip()
    nome_prodotto = row.get(col_mapping['nome_prodotto'] or 'Decodifica', '').strip()
    
    # Auto-detect quantity column (handles encoding issues)
    quantita_val = '0'
    for key in row.keys():
        if 'quantit' in key.lower() or 'qty' in key.lower():
            quantita_val = row[key]
            break
    if col_mapping['quantita']:
        quantita_val = row.get(col_mapping['quantita'], quantita_val)
    quantita = parse_float(quantita_val)
    
    # Auto-detect price and total columns
    importo_unitario = parse_float(row.get(col_mapping['importo_unitario'] or 'Importo Unitario', '0'))
    importo_totale = parse_float(row.get(col_mapping['importo_totale'] or 'Importo Totale', '0'))
    
    causale = row.get(col_mapping['causale'] or 'Causale', '').strip().upper()
    
    # Skip empty rows
    if not nome_prodotto and not nome_cliente_fornitore:
        return
    
    # Determine transaction type based on Movimento AND Causale
    movimento_upper = movimento.upper()
    
    # VENDITA: Scarico + VENDITA
    is_vendita = movimento_upper == 'SCARICO' and ('VEN' in causale or causale == 'VENDITA')
    
    # ACQUISTO: Carico + C/ACQUISTO
    is_acquisto = movimento_upper == 'CARICO' and ('ACQ' in causale or 'C/ACQUISTO' in causale)
    
    # RETTIFICA: any with RETTIFICHE or RETTIFICA
    is_rettifica = 'RETTIFIC' in causale
    
    # CESSIONE/OMAGGIO: CESSIONE GRATUITA, CAMPIONE OMAGGIO
    is_cessione = 'CESSIONE' in causale or 'OMAGGIO' in causale or 'CAMPIONE' in causale
    
    # RESO: RESO SU ACQUISTI, RESO C/REFRIGERAZIONE
    is_reso = 'RESO' in causale
    
    # TRASFERIMENTO: TRASFERIMENTO INT.
    is_trasferimento = 'TRASFERIMENTO' in causale
    
    # VUOTATI: contenitori vuotati
    is_vuotati = 'VUOTATI' in causale
    
    # COMMISSIONE: C/COMMISSIONE
    is_commissione = 'COMMISSIONE' in causale
    
    # Keep original sign for quantity tracking, but use abs for display
    raw_quantita = quantita
    raw_totale = importo_totale
    
    # For SCARICO movements, quantities are negative in the file
    quantita = abs(quantita)
    importo_totale = abs(importo_totale)
    importo_unitario = abs(importo_unitario)
    
    # Determine quantity change for inventory
    # CARICO adds, SCARICO subtracts
    qty_change = quantita if movimento_upper == 'CARICO' else -quantita
    
    # Special handling for RESO SU ACQUISTI (return to supplier = inventory decreases)
    if is_reso and 'ACQUISTI' in causale:
        qty_change = -quantita  # Returns reduce inventory
    
    # VENDITA -> create sale record
    if is_vendita and nome_cliente_fornitore:
        # Check in-memory cache - no DB query needed since we pre-loaded
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
    
    # Handle CESSIONI/OMAGGI as sales with 0 value (for tracking)
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
    
    # Handle RESI as negative orders (returns to supplier)
    elif is_reso and nome_cliente_fornitore:
        if nome_cliente_fornitore not in cache['fornitori']:
            fornitore = Fornitore(nome=nome_cliente_fornitore, codice=codice_cliente_fornitore)
            await db.fornitori.insert_one(serialize_doc(fornitore.model_dump()))
            cache['fornitori'][nome_cliente_fornitore] = fornitore.id
            stats['new_fornitori'] += 1
        
        fornitore_id = cache['fornitori'].get(nome_cliente_fornitore)
        # Resi are recorded as negative totals
        ordine = Ordine(
            data=data, fornitore_id=fornitore_id, fornitore_nome=nome_cliente_fornitore,
            prodotto_nome=nome_prodotto, quantita=-quantita,
            prezzo_unitario=importo_unitario, totale=-importo_totale
        )
        cache['ordini_batch'].append(serialize_doc(ordine.model_dump()))
        stats['resi_created'] = stats.get('resi_created', 0) + 1
    
    # Track other movements for statistics but don't create sales/orders
    else:
        stats['other_movements'] = stats.get('other_movements', 0) + 1
    
    # Create/update prodotto with quantity tracking
    # Use the qty_change calculated earlier which already accounts for special cases
    if nome_prodotto:
        if nome_prodotto not in cache['prodotti']:
            # New product - set initial quantity based on movement type
            prodotto = Prodotto(nome=nome_prodotto, codice=codice_prodotto, prezzo_medio=importo_unitario, quantita=qty_change)
            await db.prodotti.insert_one(serialize_doc(prodotto.model_dump()))
            cache['prodotti'][nome_prodotto] = {'id': prodotto.id, 'prezzo_medio': importo_unitario, 'quantita': qty_change}
            stats['new_prodotti'] += 1
        else:
            # Product exists - track quantity change in cache, batch update later
            cache['prodotti'][nome_prodotto]['quantita'] = cache['prodotti'][nome_prodotto].get('quantita', 0) + qty_change
            if is_acquisto and importo_unitario > 0:
                cache['prodotti'][nome_prodotto]['prezzo_medio'] = importo_unitario
            stats['existing_prodotti'] += 1


# ======================= API ENDPOINTS =======================

@api_router.get("/")
async def root():
    return {"message": "Gestio API v1.0"}


# ----- CSV/XLSX Upload -----
@api_router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload and process CSV or XLSX file"""
    
    filename = file.filename.lower()
    if not filename.endswith('.csv') and not filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Il file deve essere in formato CSV o XLSX")
    
    stats = {
        'new_clienti': 0,
        'existing_clienti': 0,
        'new_fornitori': 0,
        'existing_fornitori': 0,
        'new_prodotti': 0,
        'existing_prodotti': 0,
        'vendite_created': 0,
        'ordini_created': 0,
        'rows_processed': 0,
        'rows_skipped': 0,
        'columns_detected': {},
        'errors': []
    }
    
    try:
        content = await file.read()
        rows = []
        headers = []
        
        if filename.endswith('.xlsx'):
            # Parse XLSX with pandas
            df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
            df.columns = [str(c).strip() for c in df.columns]
            
            # Check if first row contains actual headers (common with XLSX exports)
            # If columns are "Unnamed:" it means the real headers are in the first data row
            unnamed_cols = sum(1 for c in df.columns if 'unnamed' in c.lower())
            if unnamed_cols > len(df.columns) / 2 and len(df) > 0:
                # Use first row as headers
                new_headers = [str(v).strip() if pd.notna(v) else f'col_{i}' for i, v in enumerate(df.iloc[0])]
                df.columns = new_headers
                df = df.iloc[1:].reset_index(drop=True)
            
            headers = list(df.columns)
            rows = []
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
            # Parse CSV with encoding detection
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    text_content = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise HTTPException(status_code=400, detail="Impossibile decodificare il file")
            
            # Detect delimiter
            first_line = text_content.split('\n')[0]
            delimiter = ';' if ';' in first_line else ','
            
            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
            headers = csv_reader.fieldnames or []
            rows = list(csv_reader)
        
        # Auto-detect columns from headers
        col_mapping = auto_detect_columns(headers)
        stats['columns_detected'] = {k: v for k, v in col_mapping.items() if v is not None}
        
        # IMPORTANT: Clear existing vendite and ordini to prevent duplicates
        # This is a full re-import approach - each upload replaces all data
        await db.vendite.delete_many({})
        await db.ordini.delete_many({})
        
        # Reset product quantities to 0 before recalculating from file
        await db.prodotti.update_many({}, {"$set": {"quantita": 0}})
        
        # In-memory cache for batch processing
        cache = {
            'clienti': {},
            'fornitori': {},
            'prodotti': {},
            'vendite_batch': [],
            'ordini_batch': []
        }
        
        BATCH_SIZE = 500
        
        # Pre-load existing data into cache for faster processing
        existing_clienti = await db.clienti.find({}, {"_id": 0, "id": 1, "nome": 1}).to_list(10000)
        for c in existing_clienti:
            cache['clienti'][c['nome']] = c['id']
        
        existing_fornitori = await db.fornitori.find({}, {"_id": 0, "id": 1, "nome": 1}).to_list(10000)
        for f in existing_fornitori:
            cache['fornitori'][f['nome']] = f['id']
        
        existing_prodotti = await db.prodotti.find({}, {"_id": 0, "id": 1, "nome": 1, "prezzo_medio": 1, "quantita": 1}).to_list(10000)
        for p in existing_prodotti:
            cache['prodotti'][p['nome']] = {'id': p['id'], 'prezzo_medio': p.get('prezzo_medio', 0), 'quantita': 0}
        
        for row in rows:
            try:
                await process_csv_row(row, stats, col_mapping, cache)
                stats['rows_processed'] += 1
                
                # Flush batches periodically
                if len(cache['vendite_batch']) >= BATCH_SIZE:
                    await db.vendite.insert_many(cache['vendite_batch'])
                    cache['vendite_batch'] = []
                if len(cache['ordini_batch']) >= BATCH_SIZE:
                    await db.ordini.insert_many(cache['ordini_batch'])
                    cache['ordini_batch'] = []
                    
            except Exception as e:
                stats['errors'].append(f"Riga {stats['rows_processed'] + 1}: {str(e)}")
        
        # Flush remaining batches
        if cache['vendite_batch']:
            await db.vendite.insert_many(cache['vendite_batch'])
            cache['vendite_batch'] = []
        if cache['ordini_batch']:
            await db.ordini.insert_many(cache['ordini_batch'])
            cache['ordini_batch'] = []
        
        # Batch update product quantities
        for nome_prodotto, prod_data in cache['prodotti'].items():
            if isinstance(prod_data, dict):
                await db.prodotti.update_one(
                    {"nome": nome_prodotto},
                    {"$set": {"quantita": prod_data.get('quantita', 0), "prezzo_medio": prod_data.get('prezzo_medio', 0)}}
                )
        
        return {
            "success": True,
            "message": "File elaborato con successo",
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/upload-multiple")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    """Upload and process multiple CSV/XLSX files at once, merging all data"""
    
    total_stats = {
        'new_clienti': 0,
        'existing_clienti': 0,
        'new_fornitori': 0,
        'existing_fornitori': 0,
        'new_prodotti': 0,
        'existing_prodotti': 0,
        'vendite_created': 0,
        'ordini_created': 0,
        'cessioni_created': 0,
        'resi_created': 0,
        'other_movements': 0,
        'rows_processed': 0,
        'files_processed': 0,
        'errors': []
    }
    
    # Clear all existing data ONCE before processing all files
    await db.vendite.delete_many({})
    await db.ordini.delete_many({})
    await db.prodotti.update_many({}, {"$set": {"quantita": 0}})
    
    # Global cache shared across all files
    cache = {
        'clienti': {},
        'fornitori': {},
        'prodotti': {},
        'vendite_batch': [],
        'ordini_batch': []
    }
    
    BATCH_SIZE = 500
    
    # Pre-load existing data into cache for faster processing
    existing_clienti = await db.clienti.find({}, {"_id": 0, "id": 1, "nome": 1}).to_list(10000)
    for c in existing_clienti:
        cache['clienti'][c['nome']] = c['id']
    
    existing_fornitori = await db.fornitori.find({}, {"_id": 0, "id": 1, "nome": 1}).to_list(10000)
    for f in existing_fornitori:
        cache['fornitori'][f['nome']] = f['id']
    
    existing_prodotti = await db.prodotti.find({}, {"_id": 0, "id": 1, "nome": 1, "prezzo_medio": 1, "quantita": 1}).to_list(10000)
    for p in existing_prodotti:
        cache['prodotti'][p['nome']] = {'id': p['id'], 'prezzo_medio': p.get('prezzo_medio', 0), 'quantita': 0}
    
    for file in files:
        filename = file.filename.lower()
        if not filename.endswith('.csv') and not filename.endswith('.xlsx'):
            total_stats['errors'].append(f"File {file.filename}: formato non supportato")
            continue
        
        try:
            content = await file.read()
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
                    total_stats['errors'].append(f"File {file.filename}: impossibile decodificare")
                    continue
                
                first_line = text_content.split('\n')[0]
                delimiter = ';' if ';' in first_line else ','
                
                csv_reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
                headers = csv_reader.fieldnames or []
                rows = list(csv_reader)
            
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
    
    # Flush remaining batches
    if cache['vendite_batch']:
        await db.vendite.insert_many(cache['vendite_batch'])
    if cache['ordini_batch']:
        await db.ordini.insert_many(cache['ordini_batch'])
    
    # Batch update product quantities
    for nome_prodotto, prod_data in cache['prodotti'].items():
        if isinstance(prod_data, dict):
            await db.prodotti.update_one(
                {"nome": nome_prodotto},
                {"$set": {"quantita": prod_data.get('quantita', 0), "prezzo_medio": prod_data.get('prezzo_medio', 0)}}
            )
    
    return {
        "success": True,
        "message": f"Elaborati {total_stats['files_processed']} file con successo",
        "stats": total_stats
    }


# ----- Clienti -----
@api_router.get("/clienti", response_model=List[Cliente])
async def get_clienti(
    search: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    query = {}
    if search:
        query["nome"] = {"$regex": search, "$options": "i"}
    
    clienti = await db.clienti.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return clienti


@api_router.post("/clienti", response_model=Cliente)
async def create_cliente(data: ClienteCreate):
    cliente = Cliente(**data.model_dump())
    doc = serialize_doc(cliente.model_dump())
    await db.clienti.insert_one(doc)
    return cliente


@api_router.get("/clienti/{cliente_id}")
async def get_cliente(cliente_id: str):
    cliente = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    return cliente


@api_router.put("/clienti/{cliente_id}")
async def update_cliente(cliente_id: str, data: ClienteCreate):
    result = await db.clienti.update_one(
        {"id": cliente_id},
        {"$set": data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    return {"success": True}


@api_router.delete("/clienti/{cliente_id}")
async def delete_cliente(cliente_id: str):
    result = await db.clienti.delete_one({"id": cliente_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    return {"success": True}


@api_router.get("/clienti/{cliente_id}/analisi")
async def get_cliente_analisi(cliente_id: str):
    """Get detailed analysis for a cliente"""
    cliente = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    # Get sales for this cliente
    vendite = await db.vendite.find({"cliente_id": cliente_id}, {"_id": 0}).to_list(1000)
    
    # Calculate stats
    now = datetime.now()
    last_month = now - timedelta(days=30)
    last_month_str = last_month.strftime("%Y-%m-%d")
    
    totale_mese = sum(v.get('totale', 0) for v in vendite if v.get('data', '') >= last_month_str)
    ordini_mese = len([v for v in vendite if v.get('data', '') >= last_month_str])
    ultimo_ordine = max([v.get('data', '') for v in vendite], default='N/A')
    media_ordine = totale_mese / ordini_mese if ordini_mese > 0 else 0
    
    # Top products
    prodotti_count = {}
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        prodotti_count[prod] = prodotti_count.get(prod, 0) + v.get('quantita', 0)
    
    top_prodotti = sorted(prodotti_count.items(), key=lambda x: x[1], reverse=True)[:3]
    prodotti_str = ', '.join([p[0] for p in top_prodotti]) if top_prodotti else 'Nessuno'
    
    return {
        "totaleSpesoMese": totale_mese,
        "ordiniMese": ordini_mese,
        "ultimoOrdine": ultimo_ordine,
        "mediaOrdine": media_ordine,
        "prodottiPiuAcquistati": prodotti_str
    }


# ----- Fornitori -----
@api_router.get("/fornitori", response_model=List[Fornitore])
async def get_fornitori(
    search: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    query = {}
    if search:
        query["nome"] = {"$regex": search, "$options": "i"}
    
    fornitori = await db.fornitori.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return fornitori


@api_router.post("/fornitori", response_model=Fornitore)
async def create_fornitore(data: FornitoreCreate):
    fornitore = Fornitore(**data.model_dump())
    doc = serialize_doc(fornitore.model_dump())
    await db.fornitori.insert_one(doc)
    return fornitore


@api_router.put("/fornitori/{fornitore_id}")
async def update_fornitore(fornitore_id: str, data: FornitoreCreate):
    result = await db.fornitori.update_one(
        {"id": fornitore_id},
        {"$set": data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    return {"success": True}


@api_router.delete("/fornitori/{fornitore_id}")
async def delete_fornitore(fornitore_id: str):
    result = await db.fornitori.delete_one({"id": fornitore_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    return {"success": True}


@api_router.get("/fornitori-with-stats")
async def get_fornitori_with_stats(
    search: Optional[str] = None,
    anno: Optional[int] = None,
    limit: int = 100,
    skip: int = 0
):
    """Get fornitori with calculated fatturato from ordini, filterable by year"""
    query = {}
    if search:
        query["nome"] = {"$regex": search, "$options": "i"}
    
    fornitori = await db.fornitori.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    
    # Filter ordini by year if specified
    ordini_query = {}
    if anno:
        ordini_query["data"] = {"$gte": f"{anno}-01-01", "$lte": f"{anno}-12-31"}
    
    ordini = await db.ordini.find(ordini_query, {"_id": 0, "fornitore_nome": 1, "totale": 1, "prezzo_unitario": 1, "quantita": 1}).to_list(100000)
    
    # Calculate fatturato per fornitore (using prezzo * quantità for accuracy)
    fatturato_map = {}
    for o in ordini:
        fornitore_nome = o.get('fornitore_nome', '')
        totale = abs(o.get('quantita', 0) * o.get('prezzo_unitario', 0))
        fatturato_map[fornitore_nome] = fatturato_map.get(fornitore_nome, 0) + totale
    
    # Add calculated fatturato to each fornitore
    for f in fornitori:
        f['fatturato_totale'] = round(fatturato_map.get(f.get('nome', ''), 0), 2)
    
    # Get available years from all ordini
    all_dates = await db.ordini.distinct("data")
    anni_disponibili = sorted(set(d[:4] for d in all_dates if d and len(d) >= 4), reverse=True)
    
    return {"fornitori": fornitori, "anni_disponibili": anni_disponibili}


@api_router.put("/fornitori/{fornitore_id}/note")
async def update_fornitore_note(fornitore_id: str, data: Dict[str, Any]):
    """Update only the note field of a fornitore"""
    result = await db.fornitori.update_one(
        {"id": fornitore_id},
        {"$set": {"note": data.get("note", "")}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Fornitore non trovato")
    return {"success": True}


@api_router.get("/fornitori/{fornitore_nome}/prodotti")
async def get_fornitore_prodotti(fornitore_nome: str, mese: Optional[str] = None):
    """Get all products purchased from a specific fornitore - con selezione mese"""
    from urllib.parse import unquote
    fornitore_nome = unquote(fornitore_nome)
    
    # Get all ordini for this fornitore
    ordini = await db.ordini.find(
        {"fornitore_nome": fornitore_nome}, 
        {"_id": 0, "prodotto_nome": 1, "quantita": 1, "prezzo_unitario": 1, "totale": 1, "data": 1}
    ).to_list(10000)
    
    if not ordini:
        return {
            "fornitore": fornitore_nome,
            "acquisti": [],
            "totale_acquisti": 0,
            "totale_speso": 0,
            "mese_riferimento": "N/A",
            "mesi_disponibili": []
        }
    
    # Trova tutti i mesi disponibili
    mesi_con_ordini = {}
    for o in ordini:
        data = o.get('data', '')[:7]  # YYYY-MM
        if data:
            if data not in mesi_con_ordini:
                mesi_con_ordini[data] = []
            mesi_con_ordini[data].append(o)
    
    # Crea lista mesi disponibili ordinata (più recente prima)
    mesi_it = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
              'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
    
    mesi_disponibili = []
    for m in sorted(mesi_con_ordini.keys(), reverse=True):
        try:
            mese_dt = datetime.strptime(m, "%Y-%m")
            label = f"{mesi_it[mese_dt.month - 1]} {mese_dt.year}"
            mesi_disponibili.append({"value": m, "label": label})
        except:
            mesi_disponibili.append({"value": m, "label": m})
    
    # Determina quale mese usare
    if mese and mese in mesi_con_ordini:
        mese_selezionato = mese
    else:
        # Usa l'ultimo mese disponibile
        mese_selezionato = sorted(mesi_con_ordini.keys(), reverse=True)[0] if mesi_con_ordini else None
    
    if not mese_selezionato:
        return {
            "fornitore": fornitore_nome,
            "acquisti": [],
            "totale_acquisti": 0,
            "totale_speso": 0,
            "mese_riferimento": "N/A",
            "mesi_disponibili": mesi_disponibili
        }
    
    # Trova label del mese selezionato
    try:
        mese_dt = datetime.strptime(mese_selezionato, "%Y-%m")
        mese_riferimento = f"{mesi_it[mese_dt.month - 1]} {mese_dt.year}"
    except:
        mese_riferimento = mese_selezionato
    
    ordini_mese = mesi_con_ordini[mese_selezionato]
    
    # Return individual order lines (not aggregated)
    acquisti_list = []
    for o in ordini_mese:
        quantita = abs(o.get('quantita', 0))
        prezzo = o.get('prezzo_unitario', 0)
        totale = round(quantita * prezzo, 2)
        acquisti_list.append({
            "prodotto": o.get('prodotto_nome', ''),
            "data": o.get('data', ''),
            "quantita": quantita,
            "prezzo_unitario": prezzo,
            "totale": totale
        })
    
    # Sort by date descending, then by product name
    acquisti_list.sort(key=lambda x: (-x['totale'], x['prodotto']))
    
    totale_speso = sum(a['totale'] for a in acquisti_list)
    
    return {
        "fornitore": fornitore_nome,
        "acquisti": acquisti_list,
        "totale_acquisti": len(acquisti_list),
        "totale_speso": round(totale_speso, 2),
        "mese_riferimento": mese_riferimento,
        "mese_selezionato": mese_selezionato,
        "mesi_disponibili": mesi_disponibili
    }


# ----- Prodotti (Magazzino) -----
@api_router.get("/prodotti", response_model=List[Prodotto])
async def get_prodotti(
    search: Optional[str] = None,
    filter_type: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    query = {}
    if search:
        query["nome"] = {"$regex": search, "$options": "i"}
    
    if filter_type == "ordinare":
        query["$expr"] = {"$and": [
            {"$gt": ["$quantita", 0]},
            {"$lte": ["$quantita", "$quantita_minima"]}
        ]}
    elif filter_type == "scadenza":
        today = datetime.now().strftime("%Y-%m-%d")
        thirty_days = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        query["scadenza"] = {"$lte": thirty_days, "$gte": today}
    
    prodotti = await db.prodotti.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    
    # Calculate derived fields and clamp negatives
    for p in prodotti:
        quantita = max(0, p.get('quantita', 0))
        p['quantita'] = quantita
        prezzo = p.get('prezzo_medio', 0)
        minima = p.get('quantita_minima', 0)
        
        p['valore_scorte'] = quantita * prezzo
        
        if quantita <= 0:
            p['stato'] = 'non_disponibile'
        elif minima > 0 and quantita <= minima:
            p['stato'] = 'ordinare'
        else:
            p['stato'] = 'disponibile'
    
    return prodotti


@api_router.get("/prodotti/stats")
async def get_prodotti_stats():
    """Get inventory statistics"""
    prodotti = await db.prodotti.find({}, {"_id": 0}).to_list(10000)
    
    ordinare_count = 0
    scadenza_count = 0
    today = datetime.now()
    thirty_days = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    
    for p in prodotti:
        quantita = p.get('quantita', 0)
        minima = p.get('quantita_minima', 0)
        scadenza = p.get('scadenza', '')
        
        if quantita > 0 and minima > 0 and quantita <= minima:
            ordinare_count += 1
        
        if scadenza and scadenza <= thirty_days:
            scadenza_count += 1
    
    return {
        "ordinare_count": ordinare_count,
        "scadenza_count": scadenza_count,
        "total": len(prodotti)
    }


@api_router.post("/prodotti", response_model=Prodotto)
async def create_prodotto(data: ProdottoCreate):
    prodotto = Prodotto(**data.model_dump())
    doc = serialize_doc(prodotto.model_dump())
    await db.prodotti.insert_one(doc)
    return prodotto


@api_router.put("/prodotti/{prodotto_id}")
async def update_prodotto(prodotto_id: str, data: Dict[str, Any]):
    # Clamp quantity to 0 minimum if being set
    if 'quantita' in data and data['quantita'] is not None:
        data['quantita'] = max(0, float(data['quantita']))
    result = await db.prodotti.update_one(
        {"id": prodotto_id},
        {"$set": data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    return {"success": True}


@api_router.delete("/prodotti/{prodotto_id}")
async def delete_prodotto(prodotto_id: str):
    result = await db.prodotti.delete_one({"id": prodotto_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    return {"success": True}


@api_router.post("/prodotti/recalculate-quantities")
async def recalculate_quantities():
    """Recalculate all product quantities from sales/orders data"""
    
    # Get all vendite (SCARICO = vendita, decreases stock)
    vendite = await db.vendite.find({}, {"_id": 0, "prodotto_nome": 1, "quantita": 1}).to_list(100000)
    
    # Get all ordini (CARICO = acquisto, increases stock)
    ordini = await db.ordini.find({}, {"_id": 0, "prodotto_nome": 1, "quantita": 1}).to_list(100000)
    
    # Calculate net quantities per product
    # CARICO (ordini) adds, SCARICO (vendite) subtracts
    product_quantities = {}
    
    for o in ordini:
        prod = o.get('prodotto_nome', '')
        qty = abs(o.get('quantita', 0))
        product_quantities[prod] = product_quantities.get(prod, 0) + qty
    
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        qty = abs(v.get('quantita', 0))
        product_quantities[prod] = product_quantities.get(prod, 0) - qty
    
    # Update all products
    updated = 0
    for prod_name, qty in product_quantities.items():
        result = await db.prodotti.update_one(
            {"nome": prod_name},
            {"$set": {"quantita": qty}}
        )
        if result.modified_count > 0:
            updated += 1
    
    return {
        "success": True,
        "products_updated": updated,
        "total_products_calculated": len(product_quantities)
    }


@api_router.get("/prodotti/{prodotto_nome:path}/analisi")
async def get_prodotto_analisi(prodotto_nome: str):
    """Get detailed analysis for a prodotto"""
    # Decode URL-encoded product name (handle slashes in names)
    from urllib.parse import unquote
    prodotto_nome = unquote(prodotto_nome)
    vendite = await db.vendite.find({"prodotto_nome": prodotto_nome}, {"_id": 0}).to_list(10000)
    
    # Exclude non-client entries
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    vendite_filtered = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    
    ultima_vendita = max([v.get('data', '') for v in vendite_filtered], default='N/A')
    
    # Monthly average (last 6 months)
    six_months_ago = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    recent_vendite = [v for v in vendite_filtered if v.get('data', '') >= six_months_ago]
    media_mensile = sum(abs(v.get('quantita', 0)) for v in recent_vendite) / 6 if recent_vendite else 0
    
    # Fatturato mensile medio (più utile del totale venduto)
    fatturato_mensile = sum(abs(v.get('totale', 0)) for v in recent_vendite) / 6 if recent_vendite else 0
    
    # Prezzo medio di vendita (calcolato dalle vendite effettive)
    prezzi_vendita = [v.get('prezzo_unitario', 0) for v in vendite_filtered if v.get('prezzo_unitario', 0) > 0]
    prezzo_medio_vendita = sum(prezzi_vendita) / len(prezzi_vendita) if prezzi_vendita else 0
    
    # Trend vendite (confronto ultimo mese vs mese precedente)
    now = datetime.now()
    last_month_start = (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
    last_month_end = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
    this_month_start = now.replace(day=1).strftime("%Y-%m-%d")
    
    vendite_last_month = sum(abs(v.get('totale', 0)) for v in vendite_filtered if last_month_start <= v.get('data', '') <= last_month_end)
    vendite_this_month = sum(abs(v.get('totale', 0)) for v in vendite_filtered if v.get('data', '') >= this_month_start)
    
    if vendite_last_month > 0:
        trend_percentuale = round(((vendite_this_month - vendite_last_month) / vendite_last_month) * 100, 1)
    else:
        trend_percentuale = 100 if vendite_this_month > 0 else 0
    
    # Top clienti - exclude non-real clients
    clienti_count = {}
    for v in vendite_filtered:
        cliente = v.get('cliente_nome', '')
        if cliente and cliente.upper() not in [c.upper() for c in EXCLUDED_CLIENTS]:
            clienti_count[cliente] = clienti_count.get(cliente, 0) + abs(v.get('quantita', 0))
    
    top_clienti = sorted(clienti_count.items(), key=lambda x: x[1], reverse=True)[:3]
    clienti_str = ', '.join([c[0] for c in top_clienti]) if top_clienti else 'Nessuno'
    
    # Numero clienti unici
    clienti_unici = len(set(v.get('cliente_nome', '') for v in vendite_filtered if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]))
    
    # Days until stock exhaustion
    prodotto = await db.prodotti.find_one({"nome": prodotto_nome}, {"_id": 0})
    quantita_attuale = prodotto.get('quantita', 0) if prodotto else 0
    prezzo_acquisto = prodotto.get('prezzo_medio', 0) if prodotto else 0
    giorni_esaurimento = int(quantita_attuale / media_mensile * 30) if media_mensile > 0 else 'N/A'
    
    return {
        "fatturatoMensile": round(fatturato_mensile, 2),
        "mediaMensile": round(media_mensile, 2),
        "ultimaVendita": ultima_vendita,
        "trendPercentuale": trend_percentuale,
        "clientiUnici": clienti_unici,
        "clientiPrincipali": clienti_str,
        "giorniEsaurimento": giorni_esaurimento,
        "prezzoMedioVendita": round(prezzo_medio_vendita, 2),
        "prezzoAcquisto": prezzo_acquisto
    }


@api_router.get("/prodotti/{prodotto_nome:path}/analisi-acquisti")
async def get_prodotto_analisi_acquisti(prodotto_nome: str):
    """Get detailed purchase analysis for a prodotto (from ordini/fornitori)"""
    from urllib.parse import unquote
    prodotto_nome = unquote(prodotto_nome)
    
    ordini = await db.ordini.find({"prodotto_nome": prodotto_nome}, {"_id": 0}).to_list(10000)
    
    if not ordini:
        return {
            "spesoMensile": 0,
            "mediaMensile": 0,
            "ultimoAcquisto": "N/A",
            "trendPercentuale": 0,
            "fornitoriUnici": 0,
            "fornitoriPrincipali": "Nessuno",
            "prezzoMedioAcquisto": 0,
            "ordiniUltimoMese": 0,
            "meseRiferimento": "N/A"
        }
    
    ultimo_acquisto = max([o.get('data', '') for o in ordini], default='N/A')
    
    # Monthly average (last 6 months)
    now = datetime.now()
    six_months_ago = (now - timedelta(days=180)).strftime("%Y-%m-%d")
    recent_ordini = [o for o in ordini if o.get('data', '') >= six_months_ago]
    media_mensile = sum(abs(o.get('quantita', 0)) for o in recent_ordini) / 6 if recent_ordini else 0
    
    # Speso mensile medio
    speso_mensile = sum(abs(o.get('totale', 0)) for o in recent_ordini) / 6 if recent_ordini else 0
    
    # Prezzo medio di acquisto
    prezzi_acquisto = [o.get('prezzo_unitario', 0) for o in ordini if o.get('prezzo_unitario', 0) > 0]
    prezzo_medio_acquisto = sum(prezzi_acquisto) / len(prezzi_acquisto) if prezzi_acquisto else 0
    
    # Ordini ultimo mese (o ultimo mese disponibile se il mese corrente è vuoto)
    this_month_start = now.replace(day=1).strftime("%Y-%m-%d")
    ordini_this_month = [o for o in ordini if o.get('data', '') >= this_month_start]
    
    if ordini_this_month:
        # Usa il mese corrente
        ordini_ultimo_mese = len(ordini_this_month)
        mese_riferimento = now.strftime("%B %Y")
    else:
        # Trova l'ultimo mese con ordini
        mesi_con_ordini = {}
        for o in ordini:
            data = o.get('data', '')[:7]  # YYYY-MM
            if data:
                mesi_con_ordini[data] = mesi_con_ordini.get(data, 0) + 1
        
        if mesi_con_ordini:
            ultimo_mese = max(mesi_con_ordini.keys())
            ordini_ultimo_mese = mesi_con_ordini[ultimo_mese]
            # Format mese_riferimento
            try:
                from datetime import datetime as dt
                mese_dt = dt.strptime(ultimo_mese, "%Y-%m")
                mesi_it = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
                          'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
                mese_riferimento = f"{mesi_it[mese_dt.month - 1]} {mese_dt.year}"
            except:
                mese_riferimento = ultimo_mese
        else:
            ordini_ultimo_mese = 0
            mese_riferimento = "N/A"
    
    # Trend acquisti (confronto ultimo mese vs mese precedente)
    last_month_start = (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
    last_month_end = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
    
    ordini_last_month_tot = sum(abs(o.get('totale', 0)) for o in ordini if last_month_start <= o.get('data', '') <= last_month_end)
    ordini_this_month_tot = sum(abs(o.get('totale', 0)) for o in ordini if o.get('data', '') >= this_month_start)
    
    if ordini_last_month_tot > 0:
        trend_percentuale = round(((ordini_this_month_tot - ordini_last_month_tot) / ordini_last_month_tot) * 100, 1)
    else:
        trend_percentuale = 100 if ordini_this_month_tot > 0 else 0
    
    # Top fornitori
    fornitori_count = {}
    for o in ordini:
        fornitore = o.get('fornitore_nome', '')
        if fornitore:
            fornitori_count[fornitore] = fornitori_count.get(fornitore, 0) + abs(o.get('quantita', 0))
    
    top_fornitori = sorted(fornitori_count.items(), key=lambda x: x[1], reverse=True)[:3]
    fornitori_str = ', '.join([f[0] for f in top_fornitori]) if top_fornitori else 'Nessuno'
    
    # Numero fornitori unici
    fornitori_unici = len(set(o.get('fornitore_nome', '') for o in ordini if o.get('fornitore_nome', '')))
    
    return {
        "spesoMensile": round(speso_mensile, 2),
        "mediaMensile": round(media_mensile, 2),
        "ultimoAcquisto": ultimo_acquisto,
        "trendPercentuale": trend_percentuale,
        "fornitoriUnici": fornitori_unici,
        "fornitoriPrincipali": fornitori_str,
        "prezzoMedioAcquisto": round(prezzo_medio_acquisto, 2),
        "ordiniUltimoMese": ordini_ultimo_mese,
        "meseRiferimento": mese_riferimento
    }


# ----- Vendite -----
@api_router.get("/vendite")
async def get_vendite(
    cliente: Optional[str] = None,
    prodotto: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    query = {}
    
    # General search: OR across cliente and prodotto
    if search:
        query["$or"] = [
            {"cliente_nome": {"$regex": search, "$options": "i"}},
            {"prodotto_nome": {"$regex": search, "$options": "i"}}
        ]
    else:
        if cliente:
            query["cliente_nome"] = {"$regex": cliente, "$options": "i"}
        if prodotto:
            query["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}
    
    if start_date:
        query.setdefault("data", {})["$gte"] = start_date
    if end_date:
        query.setdefault("data", {})["$lte"] = end_date
    
    vendite = await db.vendite.find(query, {"_id": 0}).sort("data", -1).skip(skip).limit(limit).to_list(limit)
    return vendite


@api_router.get("/vendite/count")
async def get_vendite_count():
    count = await db.vendite.count_documents({})
    return {"count": count}


@api_router.delete("/vendite/bulk-delete")
async def bulk_delete_vendite(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    delete_all: bool = False
):
    """Delete vendite by date range or all"""
    if delete_all:
        result = await db.vendite.delete_many({})
        return {"deleted": result.deleted_count, "message": f"Eliminate {result.deleted_count} vendite"}
    
    if not start_date and not end_date:
        raise HTTPException(status_code=400, detail="Specifica un periodo o seleziona 'Tutto'")
    
    query = {}
    if start_date:
        query.setdefault("data", {})["$gte"] = start_date
    if end_date:
        query.setdefault("data", {})["$lte"] = end_date
    
    result = await db.vendite.delete_many(query)
    return {"deleted": result.deleted_count, "message": f"Eliminate {result.deleted_count} vendite"}


@api_router.get("/statistiche/export")
async def export_statistiche(
    formato: str = "csv",
    tipo: str = "vendite",
    prodotto: Optional[str] = None,
    cliente: Optional[str] = None,
    fornitore: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Export statistics data as CSV or Excel"""
    from fastapi.responses import StreamingResponse
    import openpyxl
    
    collection = db.vendite if tipo == "vendite" else db.ordini
    entity_field = "cliente_nome" if tipo == "vendite" else "fornitore_nome"
    
    query = {}
    if prodotto:
        query["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}
    if cliente and tipo == "vendite":
        query["cliente_nome"] = {"$regex": cliente, "$options": "i"}
    if fornitore and tipo == "acquisti":
        query["fornitore_nome"] = {"$regex": fornitore, "$options": "i"}
    if start_date:
        query.setdefault("data", {})["$gte"] = start_date
    if end_date:
        query.setdefault("data", {})["$lte"] = end_date
    
    records = await collection.find(query, {"_id": 0}).sort("data", -1).to_list(100000)
    
    headers = ["Data", "Prodotto", entity_field.replace("_nome", "").title(), "Quantita", "Prezzo Unitario", "Totale"]
    rows = []
    for r in records:
        rows.append([
            r.get("data", ""),
            r.get("prodotto_nome", ""),
            r.get(entity_field, ""),
            abs(r.get("quantita", 0)),
            r.get("prezzo_unitario", 0),
            round(abs(r.get("quantita", 0) * r.get("prezzo_unitario", 0)), 2)
        ])
    
    if formato == "excel":
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = tipo.title()
        ws.append(headers)
        for row in rows:
            ws.append(row)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=flusso_{tipo}.xlsx"}
        )
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=flusso_{tipo}.csv"}
        )


# ----- Ordini -----
@api_router.get("/ordini")
async def get_ordini(
    fornitore: Optional[str] = None,
    prodotto: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    query = {}
    
    if fornitore:
        query["fornitore_nome"] = {"$regex": fornitore, "$options": "i"}
    if prodotto:
        query["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}
    if start_date:
        query.setdefault("data", {})["$gte"] = start_date
    if end_date:
        query.setdefault("data", {})["$lte"] = end_date
    
    ordini = await db.ordini.find(query, {"_id": 0}).sort("data", -1).skip(skip).limit(limit).to_list(limit)
    return ordini


@api_router.post("/ordini", response_model=Ordine)
async def create_ordine(data: OrdineCreate):
    # Calculate derived fields
    totale_kg = data.quantita * data.kg_per_pezzo
    totale = totale_kg * data.prezzo_unitario
    
    giorni_durata = 0
    if data.data_inizio and data.data_fine:
        try:
            start = datetime.strptime(data.data_inizio, "%Y-%m-%d")
            end = datetime.strptime(data.data_fine, "%Y-%m-%d")
            giorni_durata = (end - start).days
        except ValueError:
            pass
    
    ordine = Ordine(
        data=datetime.now().strftime("%Y-%m-%d"),
        fornitore_nome=data.fornitore_nome,
        prodotto_nome=data.prodotto_nome,
        quantita=data.quantita,
        kg_per_pezzo=data.kg_per_pezzo,
        totale_kg=totale_kg,
        prezzo_unitario=data.prezzo_unitario,
        totale=totale,
        data_inizio=data.data_inizio,
        data_fine=data.data_fine,
        giorni_durata=giorni_durata
    )
    
    doc = serialize_doc(ordine.model_dump())
    await db.ordini.insert_one(doc)
    return ordine


# ----- Statistiche -----
@api_router.get("/statistiche")
async def get_statistiche(
    prodotto: Optional[str] = None,
    cliente: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get filtered sales statistics"""
    
    query = {}
    if prodotto:
        query["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}
    if cliente:
        query["cliente_nome"] = {"$regex": cliente, "$options": "i"}
    if start_date:
        query.setdefault("data", {})["$gte"] = start_date
    if end_date:
        query.setdefault("data", {})["$lte"] = end_date
    
    vendite = await db.vendite.find(query, {"_id": 0}).to_list(100000)
    
    # Calculate KPIs - use absolute values since SCARICO has negative values
    totale_euro = sum(abs(v.get('totale', 0)) for v in vendite)
    totale_articoli = sum(abs(v.get('quantita', 0)) for v in vendite)
    clienti_attivi = len(set(v.get('cliente_nome', '') for v in vendite))
    
    # Use most recent date in database as reference (not system date)
    latest_sale = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", -1)])
    if latest_sale and latest_sale.get('data'):
        try:
            reference_date = datetime.strptime(latest_sale['data'], "%Y-%m-%d")
        except:
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()
    
    # Current month revenue (based on most recent data)
    current_month_start = reference_date.replace(day=1).strftime("%Y-%m-%d")
    current_month_vendite = [v for v in vendite if v.get('data', '') >= current_month_start]
    fatturato_mese = sum(abs(v.get('totale', 0)) for v in current_month_vendite)
    
    # Previous month revenue
    prev_month = reference_date.replace(day=1) - timedelta(days=1)
    prev_month_start = prev_month.replace(day=1).strftime("%Y-%m-%d")
    prev_month_end = prev_month.strftime("%Y-%m-%d")
    prev_month_vendite = [v for v in vendite if prev_month_start <= v.get('data', '') <= prev_month_end]
    fatturato_mese_prec = sum(abs(v.get('totale', 0)) for v in prev_month_vendite)
    
    # Percentage difference
    if fatturato_mese_prec > 0:
        diff_percentuale = ((fatturato_mese - fatturato_mese_prec) / fatturato_mese_prec) * 100
    else:
        diff_percentuale = 100 if fatturato_mese > 0 else 0
    
    # Monthly sales data - use absolute values
    vendite_mensili = {}
    for v in vendite:
        data = v.get('data', '')[:7]  # YYYY-MM
        vendite_mensili[data] = vendite_mensili.get(data, 0) + abs(v.get('totale', 0))
    
    monthly_data = [{"data": k, "totale": v} for k, v in sorted(vendite_mensili.items())]
    
    # Daily sales data (for detailed view)
    vendite_giornaliere = {}
    for v in vendite:
        data = v.get('data', '')
        vendite_giornaliere[data] = vendite_giornaliere.get(data, 0) + abs(v.get('totale', 0))
    
    daily_data = [{"data": k, "totale": v} for k, v in sorted(vendite_giornaliere.items())]
    
    # Top clienti - exclude "SCARICO VENDUTO" which is not a real client
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    clienti_fatturato = {}
    for v in vendite:
        cliente = v.get('cliente_nome', '')
        if cliente and cliente.upper() not in [c.upper() for c in EXCLUDED_CLIENTS]:
            clienti_fatturato[cliente] = clienti_fatturato.get(cliente, 0) + abs(v.get('totale', 0))
    
    top_clienti = [{"nome": k, "spesa": v} for k, v in sorted(clienti_fatturato.items(), key=lambda x: x[1], reverse=True)[:10]]
    
    # Top prodotti - aggregate by total euros, not quantity
    prodotti_totale = {}
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        prodotti_totale[prod] = prodotti_totale.get(prod, 0) + abs(v.get('totale', 0))
    
    top_prodotti = [{"nome": k, "totale_euro": round(v, 2)} for k, v in sorted(prodotti_totale.items(), key=lambda x: x[1], reverse=True)[:10]]
    
    return {
        "totaleEuro": totale_euro,
        "totaleArticoli": totale_articoli,
        "clientiAttivi": clienti_attivi,
        "fatturatoMese": fatturato_mese,
        "fatturatoMesePrec": fatturato_mese_prec,
        "diffPercentuale": round(diff_percentuale, 2),
        "venditeMensili": monthly_data,
        "venditeGiornaliere": daily_data,
        "topClienti": top_clienti,
        "topProdotti": top_prodotti
    }


@api_router.get("/statistiche/lists")
async def get_statistiche_lists():
    """Get unique products and clients for filter dropdowns"""
    
    prodotti = await db.prodotti.find({}, {"_id": 0, "nome": 1}).to_list(10000)
    clienti = await db.clienti.find({}, {"_id": 0, "nome": 1}).to_list(10000)
    
    return {
        "prodotti": [p.get('nome', '') for p in prodotti],
        "clienti": [c.get('nome', '') for c in clienti]
    }


@api_router.get("/statistiche/clienti-trend")
async def get_clienti_trend():
    """Get daily unique clients for the last 7 days"""
    
    # Get last 7 days
    today = datetime.now()
    days = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        days.append(day.strftime("%Y-%m-%d"))
    
    trend_data = []
    for day in days:
        # Count unique clients for this day
        vendite = await db.vendite.find({"data": day}, {"_id": 0, "cliente_nome": 1}).to_list(10000)
        unique_clients = len(set(v.get('cliente_nome', '') for v in vendite if v.get('cliente_nome')))
        
        # Format day for display (e.g., "Lun 15")
        day_date = datetime.strptime(day, "%Y-%m-%d")
        day_names = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
        day_label = f"{day_names[day_date.weekday()]} {day_date.day}"
        
        trend_data.append({
            "giorno": day_label,
            "data": day,
            "clienti": unique_clients
        })
    
    return trend_data


@api_router.get("/statistiche/acquisti")
async def get_statistiche_acquisti(
    prodotto: Optional[str] = None,
    fornitore: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get purchase statistics (mirror of vendite statistics but for ordini/fornitori)"""
    
    query = {}
    if prodotto:
        query["prodotto_nome"] = {"$regex": prodotto, "$options": "i"}
    if fornitore:
        query["fornitore_nome"] = {"$regex": fornitore, "$options": "i"}
    if start_date:
        query.setdefault("data", {})["$gte"] = start_date
    if end_date:
        query.setdefault("data", {})["$lte"] = end_date
    
    ordini = await db.ordini.find(query, {"_id": 0}).to_list(100000)
    
    # Calculate KPIs
    totale_euro = sum(abs(o.get('totale', 0)) for o in ordini)
    totale_articoli = sum(abs(o.get('quantita', 0)) for o in ordini)
    fornitori_attivi = len(set(o.get('fornitore_nome', '') for o in ordini))
    
    # Current month spending
    now = datetime.now()
    current_month_start = now.replace(day=1).strftime("%Y-%m-%d")
    current_month_ordini = [o for o in ordini if o.get('data', '') >= current_month_start]
    speso_mese = sum(abs(o.get('totale', 0)) for o in current_month_ordini)
    
    # Previous month spending
    prev_month = now.replace(day=1) - timedelta(days=1)
    prev_month_start = prev_month.replace(day=1).strftime("%Y-%m-%d")
    prev_month_end = prev_month.strftime("%Y-%m-%d")
    prev_month_ordini = [o for o in ordini if prev_month_start <= o.get('data', '') <= prev_month_end]
    speso_mese_prec = sum(abs(o.get('totale', 0)) for o in prev_month_ordini)
    
    # Percentage difference
    if speso_mese_prec > 0:
        diff_percentuale = ((speso_mese - speso_mese_prec) / speso_mese_prec) * 100
    else:
        diff_percentuale = 100 if speso_mese > 0 else 0
    
    # Monthly purchases data
    acquisti_mensili = {}
    for o in ordini:
        data = o.get('data', '')[:7]  # YYYY-MM
        acquisti_mensili[data] = acquisti_mensili.get(data, 0) + abs(o.get('totale', 0))
    
    monthly_data = [{"data": k, "totale": v} for k, v in sorted(acquisti_mensili.items())]
    
    # Top fornitori
    fornitori_spesa = {}
    for o in ordini:
        fornitore_nome = o.get('fornitore_nome', '')
        if fornitore_nome:
            fornitori_spesa[fornitore_nome] = fornitori_spesa.get(fornitore_nome, 0) + abs(o.get('totale', 0))
    
    top_fornitori = [{"nome": k, "spesa": v} for k, v in sorted(fornitori_spesa.items(), key=lambda x: x[1], reverse=True)[:10]]
    
    # Top prodotti acquistati
    prodotti_totale = {}
    for o in ordini:
        prod = o.get('prodotto_nome', '')
        prodotti_totale[prod] = prodotti_totale.get(prod, 0) + abs(o.get('totale', 0))
    
    top_prodotti = [{"nome": k, "totale_euro": round(v, 2)} for k, v in sorted(prodotti_totale.items(), key=lambda x: x[1], reverse=True)[:10]]
    
    return {
        "totaleEuro": totale_euro,
        "totaleArticoli": totale_articoli,
        "fornitoriAttivi": fornitori_attivi,
        "spesoMese": speso_mese,
        "spesoMesePrec": speso_mese_prec,
        "diffPercentuale": round(diff_percentuale, 2),
        "acquistiMensili": monthly_data,
        "topFornitori": top_fornitori,
        "topProdotti": top_prodotti
    }


@api_router.get("/statistiche/acquisti/lists")
async def get_statistiche_acquisti_lists():
    """Get unique products and fornitori for filter dropdowns"""
    
    prodotti = await db.prodotti.find({}, {"_id": 0, "nome": 1}).to_list(10000)
    fornitori = await db.fornitori.find({}, {"_id": 0, "nome": 1}).to_list(10000)
    
    return {
        "prodotti": [p.get('nome', '') for p in prodotti],
        "fornitori": [f.get('nome', '') for f in fornitori]
    }


@api_router.get("/statistiche/fornitori-trend")
async def get_fornitori_trend():
    """Get daily unique fornitori for the last 7 days"""
    
    today = datetime.now()
    days = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        days.append(day.strftime("%Y-%m-%d"))
    
    trend_data = []
    for day in days:
        ordini = await db.ordini.find({"data": day}, {"_id": 0, "fornitore_nome": 1}).to_list(10000)
        unique_fornitori = len(set(o.get('fornitore_nome', '') for o in ordini if o.get('fornitore_nome')))
        
        day_date = datetime.strptime(day, "%Y-%m-%d")
        day_names = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
        day_label = f"{day_names[day_date.weekday()]} {day_date.day}"
        
        trend_data.append({
            "giorno": day_label,
            "data": day,
            "fornitori": unique_fornitori
        })
    
    return trend_data


# ----- Dashboard Overview -----
@api_router.get("/dashboard")
async def get_dashboard():
    """Get dashboard overview data"""
    
    # Use most recent date in database as reference
    latest_sale = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", -1)])
    if latest_sale and latest_sale.get('data'):
        try:
            reference_date = datetime.strptime(latest_sale['data'], "%Y-%m-%d")
        except:
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()
    
    # Current month start and previous month dates
    current_month_start = reference_date.replace(day=1).strftime("%Y-%m-%d")
    prev_month_end = (reference_date.replace(day=1) - timedelta(days=1))
    prev_month_start = prev_month_end.replace(day=1).strftime("%Y-%m-%d")
    prev_month_end_str = prev_month_end.strftime("%Y-%m-%d")
    
    # Get current month vendite
    vendite_mese_corrente = await db.vendite.find(
        {"data": {"$gte": current_month_start}}, 
        {"_id": 0}
    ).sort("data", -1).to_list(50000)
    
    # Use abs() for fatturato since SCARICO has negative values
    fatturato_mese = sum(abs(v.get('totale', 0)) for v in vendite_mese_corrente)
    ordini_mese = len(vendite_mese_corrente)
    
    # Previous full month for comparison
    vendite_mese_prec = await db.vendite.find(
        {"data": {"$gte": prev_month_start, "$lte": prev_month_end_str}}, 
        {"_id": 0}
    ).to_list(50000)
    fatturato_mese_prec = sum(abs(v.get('totale', 0)) for v in vendite_mese_prec)
    
    # Calculate growth percentage
    if fatturato_mese_prec > 0:
        crescita_percentuale = round(((fatturato_mese - fatturato_mese_prec) / fatturato_mese_prec) * 100, 1)
    else:
        crescita_percentuale = 100.0 if fatturato_mese > 0 else 0.0
    
    # New clienti this month
    nuovi_clienti = await db.clienti.count_documents({
        "created_at": {"$gte": current_month_start}
    })
    
    # Prodotti da ordinare
    prodotti_stats = await get_prodotti_stats()
    
    # Recent activity - use current month vendite
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    attivita_recenti = []
    
    # First try current month vendite
    vendite_for_activity = [v for v in vendite_mese_corrente if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    
    # If not enough recent data, fetch more historical data
    if len(vendite_for_activity) < 10:
        all_vendite = await db.vendite.find({}, {"_id": 0}).sort("data", -1).limit(100).to_list(100)
        vendite_for_activity = [v for v in all_vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    
    for v in vendite_for_activity[:10]:
        attivita_recenti.append({
            "tipo": "vendita",
            "descrizione": f"Vendita a {v.get('cliente_nome', 'N/A')}",
            "valore": abs(v.get('totale', 0)),
            "data": v.get('data', ''),
            "prodotto": v.get('prodotto_nome', '')
        })
    
    return {
        "fatturatoMese": fatturato_mese,
        "fatturatoMesePrec": fatturato_mese_prec,
        "crescitaPercentuale": crescita_percentuale,
        "ordiniMese": ordini_mese,
        "nuoviClienti": nuovi_clienti,
        "prodottiOrdinare": prodotti_stats.get('ordinare_count', 0),
        "prodottiScadenza": prodotti_stats.get('scadenza_count', 0),
        "attivitaRecenti": attivita_recenti
    }


# ----- AI Business Suggestions -----
@api_router.get("/ai-suggestion")
async def get_ai_suggestion():
    """Generate weekly AI business suggestion based on sales data"""
    import hashlib
    
    # Get current week number to cache suggestion per week
    now = datetime.now()
    week_num = now.isocalendar()[1]
    year = now.year
    week_key = f"{year}-W{week_num}"
    
    # Check if we have a cached suggestion for this week
    cached = await db.ai_suggestions.find_one({"week_key": week_key}, {"_id": 0})
    if cached:
        return cached
    
    # Gather business data for analysis
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    
    # Get all vendite for the last 90 days
    ninety_days_ago = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    vendite = await db.vendite.find({"data": {"$gte": ninety_days_ago}}, {"_id": 0}).to_list(10000)
    vendite = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    
    # Get products and clients
    prodotti = await db.prodotti.find({}, {"_id": 0}).to_list(1000)
    clienti = await db.clienti.find({}, {"_id": 0}).to_list(1000)
    
    # Analyze data
    # 1. Top selling products by revenue
    prodotti_revenue = {}
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        prodotti_revenue[prod] = prodotti_revenue.get(prod, 0) + abs(v.get('totale', 0))
    top_products = sorted(prodotti_revenue.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # 2. Products with low stock
    low_stock = [p for p in prodotti if p.get('quantita', 0) > 0 and p.get('quantita_minima', 0) > 0 and p.get('quantita', 0) <= p.get('quantita_minima', 0)]
    
    # 3. Best clients by spending
    clienti_spending = {}
    for v in vendite:
        cliente = v.get('cliente_nome', '')
        if cliente:
            clienti_spending[cliente] = clienti_spending.get(cliente, 0) + abs(v.get('totale', 0))
    top_clients = sorted(clienti_spending.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # 4. Inactive clients (haven't bought in 30+ days)
    thirty_days_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    recent_clients = set(v.get('cliente_nome', '') for v in vendite if v.get('data', '') >= thirty_days_ago)
    all_clients = set(v.get('cliente_nome', '') for v in vendite)
    inactive_clients = all_clients - recent_clients
    
    # 5. Calculate margins if we have purchase prices
    # For now, estimate based on typical 20-30% markup
    
    # 6. Seasonality - compare this month to same month last year (if data available)
    
    # Generate suggestions based on analysis
    suggestions = []
    
    # Suggestion based on top products
    if top_products:
        top_prod_name = top_products[0][0]
        suggestions.append({
            "tipo": "prodotto_star",
            "titolo": "Prodotto Star",
            "messaggio": f"'{top_prod_name}' è il tuo prodotto più venduto. Considera di negoziare un prezzo migliore con il fornitore per aumentare il margine.",
            "azione": "Contatta il fornitore per sconti volume"
        })
    
    # Suggestion based on low stock
    if low_stock:
        low_stock_names = [p.get('nome', '') for p in low_stock[:3]]
        suggestions.append({
            "tipo": "riordino",
            "titolo": "Riordino Urgente",
            "messaggio": f"Prodotti sotto scorta minima: {', '.join(low_stock_names)}. Ordina subito per evitare rotture di stock.",
            "azione": "Vai alla sezione Acquisti"
        })
    
    # Suggestion based on inactive clients
    if len(inactive_clients) > 5:
        suggestions.append({
            "tipo": "clienti_dormienti",
            "titolo": "Clienti da Riattivare",
            "messaggio": f"Hai {len(inactive_clients)} clienti che non ordinano da 30+ giorni. Una promozione mirata potrebbe riattivare le vendite.",
            "azione": "Considera sconti personalizzati o contatto diretto"
        })
    
    # Suggestion based on best clients
    if top_clients:
        best_client = top_clients[0][0]
        suggestions.append({
            "tipo": "fidelizzazione",
            "titolo": "Cliente VIP",
            "messaggio": f"'{best_client}' è il tuo miglior cliente. Offri un programma fedeltà o sconti esclusivi per mantenerlo.",
            "azione": "Crea offerta personalizzata"
        })
    
    # Weekly rotating suggestion based on week number
    rotating_suggestions = [
        {
            "tipo": "marketing",
            "titolo": "Suggerimento Marketing",
            "messaggio": "Considera di creare un listino prezzi settimanale da inviare ai clienti via WhatsApp per aumentare gli ordini.",
            "azione": "Prepara listino PDF"
        },
        {
            "tipo": "analisi",
            "titolo": "Analisi Prezzi",
            "messaggio": "Verifica i prezzi dei concorrenti sul mercato. Piccoli aggiustamenti possono migliorare significativamente i margini.",
            "azione": "Confronta prezzi mercato"
        },
        {
            "tipo": "efficienza",
            "titolo": "Ottimizza Consegne",
            "messaggio": "Raggruppa le consegne per zona geografica per ridurre i costi di trasporto e aumentare l'efficienza.",
            "azione": "Pianifica percorsi ottimali"
        },
        {
            "tipo": "cross_selling",
            "titolo": "Cross-Selling",
            "messaggio": "Proponi prodotti complementari ai clienti. Chi compra frutta secca potrebbe essere interessato anche a semi e granelle.",
            "azione": "Crea bundle di prodotti"
        }
    ]
    
    # Pick one rotating suggestion based on week
    rotating_idx = week_num % len(rotating_suggestions)
    suggestions.append(rotating_suggestions[rotating_idx])
    
    # Pick the most relevant suggestion (first one with data-driven insight)
    main_suggestion = suggestions[0] if suggestions else rotating_suggestions[rotating_idx]
    
    result = {
        "week_key": week_key,
        "generated_at": now.isoformat(),
        "suggestion": main_suggestion,
        "all_suggestions": suggestions[:3]  # Return top 3 suggestions
    }
    
    # Cache for the week
    await db.ai_suggestions.update_one(
        {"week_key": week_key},
        {"$set": result},
        upsert=True
    )
    
    return result


@api_router.post("/ai-suggestion/refresh")
async def refresh_ai_suggestion():
    """Force regenerate AI suggestion (ignores cache)"""
    import random
    
    now = datetime.now()
    
    # Gather business data for analysis
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    
    # Get all vendite for the last 90 days
    ninety_days_ago = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    vendite = await db.vendite.find({"data": {"$gte": ninety_days_ago}}, {"_id": 0}).to_list(10000)
    vendite = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    
    # Get products and clients
    prodotti = await db.prodotti.find({}, {"_id": 0}).to_list(1000)
    
    # All suggestions pool
    all_suggestions = []
    
    # 1. Top selling products
    prodotti_revenue = {}
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        prodotti_revenue[prod] = prodotti_revenue.get(prod, 0) + abs(v.get('totale', 0))
    top_products = sorted(prodotti_revenue.items(), key=lambda x: x[1], reverse=True)[:5]
    
    if top_products:
        for i, (prod, rev) in enumerate(top_products[:3]):
            all_suggestions.append({
                "tipo": "prodotto_star",
                "titolo": f"Prodotto Top #{i+1}",
                "messaggio": f"'{prod}' genera molto fatturato. Negozia prezzi migliori o aumenta il margine.",
                "azione": "Contatta fornitore"
            })
    
    # 2. Low stock products
    low_stock = [p for p in prodotti if p.get('quantita', 0) > 0 and p.get('quantita_minima', 0) > 0 and p.get('quantita', 0) <= p.get('quantita_minima', 0)]
    if low_stock:
        for p in low_stock[:2]:
            all_suggestions.append({
                "tipo": "riordino",
                "titolo": "Scorta Bassa",
                "messaggio": f"'{p.get('nome', '')}' è sotto la quantità minima. Riordina per evitare rotture.",
                "azione": "Ordina subito"
            })
    
    # 3. Inactive clients
    thirty_days_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    recent_clients = set(v.get('cliente_nome', '') for v in vendite if v.get('data', '') >= thirty_days_ago)
    all_clients = set(v.get('cliente_nome', '') for v in vendite)
    inactive_clients = list(all_clients - recent_clients)
    
    if inactive_clients:
        sample_inactive = random.sample(inactive_clients, min(3, len(inactive_clients)))
        all_suggestions.append({
            "tipo": "clienti_dormienti",
            "titolo": "Clienti Inattivi",
            "messaggio": f"Ricontatta: {', '.join(sample_inactive)}. Non ordinano da 30+ giorni.",
            "azione": "Invia offerta"
        })
    
    # 4. Marketing suggestions
    marketing_tips = [
        {"titolo": "WhatsApp Marketing", "messaggio": "Invia il listino settimanale via WhatsApp ai tuoi clienti migliori.", "azione": "Crea broadcast"},
        {"titolo": "Promozione Bundle", "messaggio": "Crea pacchetti di prodotti complementari per aumentare lo scontrino medio.", "azione": "Definisci bundle"},
        {"titolo": "Programma Fedeltà", "messaggio": "Premia i clienti più fedeli con sconti progressivi sul volume.", "azione": "Imposta sconti"},
        {"titolo": "Consegna Gratuita", "messaggio": "Offri consegna gratuita sopra una certa soglia per incentivare ordini più grandi.", "azione": "Definisci soglia"},
        {"titolo": "Stagionalità", "messaggio": "Promuovi prodotti di stagione con margini migliori.", "azione": "Aggiorna listino"},
    ]
    for tip in marketing_tips:
        all_suggestions.append({"tipo": "marketing", **tip})
    
    # Pick a random suggestion
    if all_suggestions:
        main_suggestion = random.choice(all_suggestions)
    else:
        main_suggestion = marketing_tips[0]
    
    return {
        "week_key": f"refresh-{now.isoformat()}",
        "generated_at": now.isoformat(),
        "suggestion": main_suggestion,
        "all_suggestions": random.sample(all_suggestions, min(3, len(all_suggestions))) if all_suggestions else [main_suggestion]
    }


# ----- Alert Gestione -----
@api_router.get("/alerts")
async def get_management_alerts():
    """Get management alerts: low stock, inactive clients, expiring products"""
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    
    alerts = {
        "prodottiSottoScorta": [],
        "clientiInattivi": [],
        "prodottiInEsaurimento": []
    }
    
    # 1. Products below minimum quantity
    prodotti = await db.prodotti.find({}, {"_id": 0}).to_list(1000)
    for p in prodotti:
        quantita = p.get('quantita', 0)
        quantita_min = p.get('quantita_minima', 0)
        if quantita_min > 0 and quantita <= quantita_min:
            alerts["prodottiSottoScorta"].append({
                "nome": p.get('nome', ''),
                "quantita": quantita,
                "quantita_minima": quantita_min,
                "urgenza": "alta" if quantita <= 0 else "media"
            })
    
    # Sort by urgency
    alerts["prodottiSottoScorta"].sort(key=lambda x: (0 if x['urgenza'] == 'alta' else 1, x['quantita']))
    alerts["prodottiSottoScorta"] = alerts["prodottiSottoScorta"][:8]
    
    # 2. Inactive clients (no orders in 30+ days but had orders before)
    # Use most recent date in the database as reference, not current date
    latest_sale = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", -1)])
    if latest_sale and latest_sale.get('data'):
        try:
            reference_date = datetime.strptime(latest_sale['data'], "%Y-%m-%d")
        except:
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()
    
    ninety_days_ago = (reference_date - timedelta(days=90)).strftime("%Y-%m-%d")
    thirty_days_ago = (reference_date - timedelta(days=30)).strftime("%Y-%m-%d")
    
    vendite = await db.vendite.find({"data": {"$gte": ninety_days_ago}}, {"_id": 0}).to_list(10000)
    vendite = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    
    # Get clients with last order date
    client_last_order = {}
    client_total = {}
    for v in vendite:
        cliente = v.get('cliente_nome', '')
        if cliente:
            data = v.get('data', '')
            if cliente not in client_last_order or data > client_last_order[cliente]:
                client_last_order[cliente] = data
            client_total[cliente] = client_total.get(cliente, 0) + abs(v.get('totale', 0))
    
    for cliente, last_order in client_last_order.items():
        if last_order < thirty_days_ago:
            days_inactive = (reference_date - datetime.strptime(last_order, "%Y-%m-%d")).days
            alerts["clientiInattivi"].append({
                "nome": cliente,
                "ultimo_ordine": last_order,
                "giorni_inattivo": days_inactive,
                "fatturato_90gg": round(client_total.get(cliente, 0), 2)
            })
    
    # Sort by value (highest spending inactive clients first)
    alerts["clientiInattivi"].sort(key=lambda x: -x['fatturato_90gg'])
    alerts["clientiInattivi"] = alerts["clientiInattivi"][:8]
    
    # 3. Products running out soon (based on consumption rate)
    six_months_ago = (reference_date - timedelta(days=180)).strftime("%Y-%m-%d")
    vendite_6m = await db.vendite.find({"data": {"$gte": six_months_ago}}, {"_id": 0}).to_list(10000)
    
    prodotto_consumption = {}
    for v in vendite_6m:
        prod = v.get('prodotto_nome', '')
        prodotto_consumption[prod] = prodotto_consumption.get(prod, 0) + abs(v.get('quantita', 0))
    
    for p in prodotti:
        nome = p.get('nome', '')
        quantita = p.get('quantita', 0)
        if quantita > 0 and nome in prodotto_consumption:
            monthly_consumption = prodotto_consumption[nome] / 6
            if monthly_consumption > 0:
                days_left = int(quantita / monthly_consumption * 30)
                if days_left <= 14:
                    alerts["prodottiInEsaurimento"].append({
                        "nome": nome,
                        "quantita": quantita,
                        "consumo_mensile": round(monthly_consumption, 0),
                        "giorni_rimanenti": days_left
                    })
    
    # Sort by days remaining
    alerts["prodottiInEsaurimento"].sort(key=lambda x: x['giorni_rimanenti'])
    alerts["prodottiInEsaurimento"] = alerts["prodottiInEsaurimento"][:8]
    
    return alerts


# ----- Notizie -----

def parse_rss_date(date_str: str) -> datetime:
    """Parse RSS date string to datetime for sorting"""
    if not date_str:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    # Fallback: try common formats
    for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime(2000, 1, 1, tzinfo=timezone.utc)


ITALIAN_MONTHS = {
    'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04',
    'mag': '05', 'giu': '06', 'lug': '07', 'ago': '08',
    'set': '09', 'ott': '10', 'nov': '11', 'dic': '12',
}


def parse_italian_news_date(date_str: str) -> datetime:
    """Parse Italian date like '12 feb 2026' to datetime"""
    if not date_str:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)
    parts = date_str.strip().split()
    if len(parts) >= 3:
        day = parts[0].zfill(2)
        month = ITALIAN_MONTHS.get(parts[1][:3].lower(), '01')
        year = parts[2]
        try:
            return datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime(2000, 1, 1, tzinfo=timezone.utc)


async def fetch_rss_feed(source: dict) -> List[dict]:
    """Fetch and parse an RSS feed"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(source["url"], follow_redirects=True)
            if response.status_code != 200:
                return []
            
            root = ET.fromstring(response.content)
            ns = {'content': 'http://purl.org/rss/1.0/modules/content/'}
            items = []
            
            for item in root.findall('.//item')[:10]:
                title = item.find('title')
                link = item.find('link')
                description = item.find('description')
                pub_date = item.find('pubDate')
                
                image_url = None
                enclosure = item.find('enclosure')
                if enclosure is not None and enclosure.get('type', '').startswith('image'):
                    image_url = enclosure.get('url')
                
                media_content = item.find('.//{http://search.yahoo.com/mrss/}content')
                if media_content is not None and not image_url:
                    image_url = media_content.get('url')
                
                desc_text = description.text if description is not None else ''
                if not image_url and desc_text:
                    soup = BeautifulSoup(desc_text, 'html.parser')
                    img = soup.find('img')
                    if img and img.get('src'):
                        image_url = img.get('src')
                    desc_text = soup.get_text()[:200]
                
                # Try content:encoded for image if still none
                if not image_url:
                    content_encoded = item.find('content:encoded', ns)
                    if content_encoded is not None and content_encoded.text:
                        soup = BeautifulSoup(content_encoded.text, 'html.parser')
                        img = soup.find('img')
                        if img and img.get('src'):
                            image_url = img.get('src')
                        if not desc_text or len(desc_text) < 20:
                            desc_text = soup.get_text()[:200]
                
                pub_date_str = pub_date.text if pub_date is not None else ""
                parsed_dt = parse_rss_date(pub_date_str)
                
                items.append({
                    "titolo": title.text if title is not None else "Senza titolo",
                    "descrizione": desc_text[:300] if desc_text else "",
                    "url": link.text if link is not None else "",
                    "immagine_url": image_url,
                    "fonte": source["name"],
                    "categoria": source["categoria"],
                    "data_pubblicazione": pub_date_str[:25] if pub_date_str else "",
                    "_sort_date": parsed_dt.isoformat()
                })
            
            return items
    except Exception as e:
        logger.error(f"Error fetching RSS from {source['name']}: {e}")
        return []


async def scrape_myfruit_news() -> List[dict]:
    """Scrape news from myfruit.it (no RSS available)"""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http_client:
            resp = await http_client.get(
                MYFRUIT_NEWS_URL,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            if resp.status_code != 200:
                logger.warning(f"Myfruit scrape failed: HTTP {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = []
            seen_urls = set()
            
            # Find blog-card-details divs which contain title and description
            cards = soup.find_all('div', class_='blog-card-details')
            
            for card in cards:
                # Get the parent <a> tag for the URL
                parent_a = card.find_parent('a', href=True)
                if not parent_a:
                    continue
                
                href = parent_a['href']
                if href in seen_urls or not href.startswith('https://www.myfruit.it/news/'):
                    continue
                if '/category/' in href or '/news-page/' in href:
                    continue
                seen_urls.add(href)
                
                # Title from h5
                h5 = card.find('h5', class_='post-title-heading')
                title = h5.get_text(strip=True) if h5 else ''
                if not title or len(title) < 5:
                    continue
                
                # Description
                desc_div = card.find('div', class_='post-description')
                description = desc_div.get_text(strip=True)[:300] if desc_div else ''
                
                # Image from sibling <a> tag (the image link is a sibling of the details link)
                image_url = None
                blog_card = parent_a.parent
                if blog_card:
                    img = blog_card.find('img')
                    if img:
                        image_url = img.get('src') or img.get('data-src')
                
                # Category from parent container
                col_div = blog_card.parent if blog_card else None
                categoria_text = "ortofrutta"
                
                # Date not available in static HTML; use index-based offset from today
                today = datetime.now(timezone.utc)
                offset_date = today - timedelta(hours=len(items) * 6)
                
                items.append({
                    "titolo": title,
                    "descrizione": description,
                    "url": href,
                    "immagine_url": image_url,
                    "fonte": "Myfruit",
                    "categoria": categoria_text,
                    "data_pubblicazione": offset_date.strftime("%a, %d %b %Y"),
                    "_sort_date": offset_date.isoformat()
                })
                
                if len(items) >= 10:
                    break
            
            logger.info(f"Myfruit: scraped {len(items)} articles")
            return items
    except Exception as e:
        logger.error(f"Error scraping Myfruit: {e}")
        return []


async def refresh_notizie():
    """Fetch news from all sources and update database"""
    all_news = []
    
    # Fetch RSS feeds + myfruit scrape in parallel
    tasks = [fetch_rss_feed(source) for source in RSS_SOURCES]
    tasks.append(scrape_myfruit_news())
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, list):
            all_news.extend(result)
    
    # Sort chronologically (newest first) using the parsed sort date
    all_news.sort(key=lambda x: x.get('_sort_date', ''), reverse=True)
    
    # Clear old news and insert new ones
    if all_news:
        await db.notizie.delete_many({})
        for news in all_news:
            # Remove internal sort key before storing
            sort_date = news.pop('_sort_date', '')
            notizia = Notizia(**news)
            doc = serialize_doc(notizia.model_dump())
            doc['sort_date'] = sort_date
            await db.notizie.insert_one(doc)
    
    return len(all_news)


@api_router.get("/notizie")
async def get_notizie(limit: int = 50, categoria: Optional[str] = None):
    """Get news, optionally filtered by category, sorted chronologically"""
    query = {}
    if categoria and categoria != "all":
        query["categoria"] = categoria
    
    notizie = await db.notizie.find(query, {"_id": 0}).sort("sort_date", -1).limit(limit).to_list(limit)
    
    # If no news, try to fetch them
    if len(notizie) == 0:
        count = await refresh_notizie()
        logger.info(f"Refreshed {count} news articles")
        notizie = await db.notizie.find(query, {"_id": 0}).sort("sort_date", -1).limit(limit).to_list(limit)
    
    # Remove internal sort_date from response
    for n in notizie:
        n.pop('sort_date', None)
    
    return notizie


@api_router.post("/notizie/refresh")
async def trigger_refresh_notizie(background_tasks: BackgroundTasks):
    """Manually trigger a news refresh"""
    background_tasks.add_task(refresh_notizie)
    return {"message": "Aggiornamento notizie avviato in background"}


@api_router.get("/notizie/categorie")
async def get_categorie_notizie():
    """Get unique news categories"""
    categorie = await db.notizie.distinct("categoria")
    return categorie


@api_router.post("/notizie")
async def create_notizia(data: NotiziaCreate):
    notizia = Notizia(**data.model_dump())
    doc = serialize_doc(notizia.model_dump())
    await db.notizie.insert_one(doc)
    return notizia


# ----- Prezzi Mercati (scraping dinamico da FreshPlaza) -----

async def scrape_freshplaza_market_links():
    """Scrape latest market price links from FreshPlaza like the original Google Script"""
    global _market_price_cache
    
    BASE_URL = "https://www.freshplaza.it"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http_client:
            # Step 1: Get homepage
            resp = await http_client.get(BASE_URL + "/", headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return _market_price_cache.get("links", [])
            
            homepage_html = resp.text
            
            # Step 2: Find the article link for "Ultimi prezzi ortofrutticoli"
            anchor_text = "Ultimi prezzi ortofrutticoli"
            anchor_idx = homepage_html.find(anchor_text)
            
            if anchor_idx == -1:
                logger.warning("FreshPlaza: anchor text not found on homepage")
                return _market_price_cache.get("links", [])
            
            # Find the <a href="..."> before this text
            link_start_str = '<a href="'
            link_start_idx = homepage_html.rfind(link_start_str, 0, anchor_idx)
            if link_start_idx == -1:
                return _market_price_cache.get("links", [])
            
            url_start = link_start_idx + len(link_start_str)
            url_end = homepage_html.find('"', url_start)
            relative_url = homepage_html[url_start:url_end]
            article_url = BASE_URL + relative_url if relative_url.startswith('/') else relative_url
            
            logger.info(f"FreshPlaza article URL: {article_url}")
            
            # Step 3: Fetch the article page
            article_resp = await http_client.get(article_url, headers={"User-Agent": "Mozilla/5.0"})
            if article_resp.status_code != 200:
                return _market_price_cache.get("links", [])
            
            article_html = article_resp.text
            
            # Step 4: Extract market price links
            start_marker = '<main'
            text_start = article_html.find(start_marker)
            if text_start == -1:
                start_marker = '<article'
                text_start = article_html.find(start_marker)
            
            if text_start == -1:
                return _market_price_cache.get("links", [])
            
            article_block = article_html[text_start:]
            
            # Parse with BeautifulSoup for robustness
            soup = BeautifulSoup(article_block, 'html.parser')
            links = []
            
            for a_tag in soup.find_all('a', href=True):
                text = a_tag.get_text(strip=True)
                href = a_tag['href']
                
                # Look for market price links
                if "prezzi all'ingrosso" in text.lower() or "prezzi all&#39;ingrosso" in text.lower():
                    city_name = text.split(':')[0].strip()
                    if city_name:
                        links.append({"nome": city_name, "url": href})
                elif "listino" in href.lower() or "prezzi" in href.lower():
                    # Also catch direct price links
                    if text and len(text) < 60:
                        links.append({"nome": text.split(':')[0].strip(), "url": href})
            
            if links:
                _market_price_cache["links"] = links
                _market_price_cache["last_updated"] = datetime.now(timezone.utc)
                logger.info(f"FreshPlaza: found {len(links)} market links")
                return links
            
            return _market_price_cache.get("links", [])
            
    except Exception as e:
        logger.error(f"Error scraping FreshPlaza market prices: {e}")
        return _market_price_cache.get("links", [])


@api_router.get("/prezzi-mercati")
async def get_prezzi_mercati():
    """Get list of market price links scraped from FreshPlaza"""
    # Check cache (refresh every 6 hours)
    cache_valid = (
        _market_price_cache.get("last_updated") and 
        _market_price_cache.get("links") and
        (datetime.now(timezone.utc) - _market_price_cache["last_updated"]).total_seconds() < 21600
    )
    
    if cache_valid:
        return _market_price_cache["links"]
    
    links = await scrape_freshplaza_market_links()
    
    # If scraping failed and we have no cache, return a helpful message
    if not links:
        return [
            {"nome": "FreshPlaza - Prezzi Ingrosso", "url": "https://www.freshplaza.it/"}
        ]
    
    return links


# ----- Meteo (usando Open-Meteo API gratuita) -----
@api_router.get("/meteo")
async def get_meteo(lat: float = 44.4949, lon: float = 11.3426):
    """Get weather data for a location (default: Bologna)"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=Europe/Rome"
            response = await http_client.get(url)
            if response.status_code == 200:
                return response.json()
            return {"error": "Dati meteo non disponibili"}
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return {"error": str(e)}



# ----- Ticker News (fonti esterne diverse) -----
@api_router.get("/ticker-news")
async def get_ticker_news():
    """Get fresh news from Google News RSS for fruit & dried fruit sector"""
    import asyncio
    
    # Check cache (1 hour TTL)
    cache = await db.cache.find_one({"key": "ticker_news"}, {"_id": 0})
    if cache:
        from datetime import timezone as tz
        cached_at = cache.get("cached_at")
        if cached_at:
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=tz.utc)
            if (datetime.now(tz.utc) - cached_at).total_seconds() < 3600:
                return cache.get("data", [])
    
    def fetch_ticker():
        import feedparser
        
        google_feeds = [
            "https://news.google.com/rss/search?q=frutta+secca+mercato+italia&hl=it&gl=IT&ceid=IT:it",
            "https://news.google.com/rss/search?q=ortofrutta+prezzi+mercato&hl=it&gl=IT&ceid=IT:it",
        ]
        
        seen_titles = set()
        items = []
        
        for feed_url in google_feeds:
            try:
                d = feedparser.parse(feed_url)
                for entry in d.entries[:15]:
                    title = entry.get("title", "").strip()
                    # Rimuovi il suffisso " - NomeFonte" aggiunto da Google News
                    clean_title = title.rsplit(" - ", 1)[0].strip() if " - " in title else title
                    
                    if clean_title.lower() in seen_titles:
                        continue
                    seen_titles.add(clean_title.lower())
                    
                    source = entry.get("source", {}).get("title", "")
                    link = entry.get("link", "")
                    published = entry.get("published", "")
                    
                    items.append({
                        "titolo": clean_title,
                        "fonte": source,
                        "url": link,
                        "data": published,
                    })
            except Exception as e:
                logger.error(f"Error fetching ticker feed: {e}")
        
        return items[:20]
    
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, fetch_ticker)
    
    from datetime import timezone as tz
    await db.cache.update_one(
        {"key": "ticker_news"},
        {"$set": {"key": "ticker_news", "data": data, "cached_at": datetime.now(tz.utc)}},
        upsert=True
    )
    
    return data


# ----- Google Trends Frutta Secca -----
@api_router.get("/trends-frutta-secca")
async def get_trends_frutta_secca():
    """Get Google Trends data for dried fruits/nuts keywords (Italy)"""
    import asyncio
    from functools import partial

    keywords = ["pistacchi", "mandorle", "noci", "nocciole", "anacardi"]
    
    # Check cache first (cache for 6 hours)
    cache = await db.cache.find_one({"key": "trends_frutta_secca"}, {"_id": 0})
    if cache:
        from datetime import timezone as tz
        cached_at = cache.get("cached_at")
        if cached_at:
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=tz.utc)
            if (datetime.now(tz.utc) - cached_at).total_seconds() < 21600:
                return cache.get("data", [])

    def fetch_trends():
        try:
            from pytrends.request import TrendReq
            pytrend = TrendReq(hl='it-IT', tz=60)
            pytrend.build_payload(kw_list=keywords, timeframe='today 3-m', geo='IT')
            df = pytrend.interest_over_time()
            if df.empty:
                return []
            
            results = []
            for kw in keywords:
                if kw not in df.columns:
                    continue
                values = df[kw].tolist()
                current = values[-1] if values else 0
                avg = sum(values) / len(values) if values else 0
                
                # Confronto ultime 2 settimane vs 2 precedenti (direzione recente)
                if len(values) >= 4:
                    recent = sum(values[-2:]) / 2
                    prior = sum(values[-4:-2]) / 2
                    change = ((recent - prior) / max(prior, 1)) * 100
                else:
                    change = 0.0
                
                # Last 12 points per sparkline
                sparkline = values[-12:] if len(values) >= 12 else values
                
                results.append({
                    "keyword": kw.capitalize(),
                    "current_interest": int(current),
                    "avg_interest": round(avg, 1),
                    "change_pct": round(change, 1),
                    "sparkline": sparkline,
                    "trend": "up" if change > 5 else "down" if change < -5 else "stable"
                })
            
            results.sort(key=lambda x: x["current_interest"], reverse=True)
            return results
        except Exception as e:
            logger.error(f"Error fetching Google Trends: {e}")
            return []

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, fetch_trends)
    
    # Cache result
    from datetime import timezone
    await db.cache.update_one(
        {"key": "trends_frutta_secca"},
        {"$set": {"key": "trends_frutta_secca", "data": data, "cached_at": datetime.now(timezone.utc)}},
        upsert=True
    )
    
    return data


# ----- AI Reports -----
@api_router.get("/ai-reports")
async def get_ai_reports():
    """Get all AI-generated reports"""
    reports = await db.ai_reports.find({}, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    return reports


@api_router.get("/ai-reports/{report_id}")
async def get_ai_report(report_id: str):
    """Get a specific AI report"""
    report = await db.ai_reports.find_one({"id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report non trovato")
    return report


@api_router.delete("/ai-reports/{report_id}")
async def delete_ai_report(report_id: str):
    """Delete a specific AI report"""
    result = await db.ai_reports.delete_one({"id": report_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Report non trovato")
    return {"success": True, "message": "Report eliminato"}


@api_router.post("/ai-reports/generate")
async def generate_ai_report(report_type: str = Query("settimanale", enum=["settimanale", "mensile"])):
    """Generate a new AI business report"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    EXCLUDED_CLIENTS = ['SCARICO VENDUTO', 'CLIENTE CORRISPETTIVI', '']
    
    now = datetime.now()
    
    # Determine date range based on report type
    if report_type == "settimanale":
        start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        period_name = "Settimana"
    else:
        start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        period_name = "Mese"
    
    end_date = now.strftime("%Y-%m-%d")
    
    # Gather business data
    vendite = await db.vendite.find({"data": {"$gte": start_date}}, {"_id": 0}).to_list(10000)
    vendite = [v for v in vendite if v.get('cliente_nome', '').upper() not in [c.upper() for c in EXCLUDED_CLIENTS]]
    
    ordini = await db.ordini.find({"data": {"$gte": start_date}}, {"_id": 0}).to_list(5000)
    prodotti = await db.prodotti.find({}, {"_id": 0}).to_list(1000)
    clienti = await db.clienti.find({}, {"_id": 0}).to_list(1000)
    
    # Calculate metrics
    fatturato_totale = sum(abs(v.get('totale', 0)) for v in vendite)
    num_vendite = len(vendite)
    
    # Top products by revenue
    prodotti_revenue = {}
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        prodotti_revenue[prod] = prodotti_revenue.get(prod, 0) + abs(v.get('totale', 0))
    top_products = sorted(prodotti_revenue.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Top clients by spending
    clienti_spending = {}
    for v in vendite:
        cliente = v.get('cliente_nome', '')
        if cliente:
            clienti_spending[cliente] = clienti_spending.get(cliente, 0) + abs(v.get('totale', 0))
    top_clients = sorted(clienti_spending.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Products with low stock
    low_stock = [p for p in prodotti if p.get('quantita', 0) > 0 and p.get('quantita_minima', 0) > 0 and p.get('quantita', 0) <= p.get('quantita_minima', 0)]
    
    # Inactive clients
    recent_clients = set(v.get('cliente_nome', '') for v in vendite)
    all_historical_clients = set(c.get('nome', '') for c in clienti)
    inactive_clients = list(all_historical_clients - recent_clients)[:10]
    
    # Acquisti totali
    acquisti_totale = sum(abs(o.get('totale', 0)) for o in ordini)
    
    # Build data summary for AI
    data_summary = f"""
DATI AZIENDALI - {period_name} dal {start_date} al {end_date}

FATTURATO E VENDITE:
- Fatturato totale: €{fatturato_totale:,.2f}
- Numero transazioni: {num_vendite}
- Media per transazione: €{fatturato_totale/num_vendite if num_vendite > 0 else 0:,.2f}

TOP 5 PRODOTTI (per fatturato):
{chr(10).join([f"- {p[0]}: €{p[1]:,.2f}" for p in top_products]) if top_products else "- Nessun dato"}

TOP 5 CLIENTI (per spesa):
{chr(10).join([f"- {c[0]}: €{c[1]:,.2f}" for c in top_clients]) if top_clients else "- Nessun dato"}

MAGAZZINO:
- Prodotti totali: {len(prodotti)}
- Prodotti sotto scorta minima: {len(low_stock)}
{chr(10).join([f"  * {p.get('nome', '')}: {p.get('quantita', 0)}/{p.get('quantita_minima', 0)}" for p in low_stock[:5]]) if low_stock else ""}

ACQUISTI:
- Totale acquisti periodo: €{acquisti_totale:,.2f}

CLIENTI:
- Clienti attivi nel periodo: {len(recent_clients)}
- Clienti inattivi (da ricontattare): {len(inactive_clients)}
{chr(10).join([f"  * {c}" for c in inactive_clients[:5]]) if inactive_clients else ""}
"""

    # Generate AI report
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="API key LLM non configurata")
    
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"report-{uuid.uuid4()}",
            system_message="""Sei un analista business esperto nel settore ortofrutticolo italiano.
Il tuo compito è generare report aziendali chiari, professionali e actionable in italiano.
Usa un tono professionale ma accessibile. Struttura il report in sezioni chiare.
Fornisci sempre suggerimenti concreti e specifici basati sui dati."""
        ).with_model("openai", "gpt-4o")
        
        prompt = f"""Genera un report {report_type} professionale basato sui seguenti dati aziendali.

{data_summary}

Il report deve includere:
1. **Sommario Esecutivo** - panoramica rapida dei risultati chiave (2-3 frasi)
2. **Performance Vendite** - analisi del fatturato e trend
3. **Prodotti** - analisi dei best seller e suggerimenti
4. **Clienti** - analisi dei top clienti e strategia per clienti inattivi
5. **Magazzino** - alert scorte e suggerimenti di riordino
6. **Raccomandazioni** - 3-5 azioni concrete da intraprendere questa settimana

Formatta il report in markdown per una buona leggibilità.
Sii specifico nei suggerimenti, usando i nomi reali di prodotti e clienti dai dati."""

        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Save report to database
        report_id = str(uuid.uuid4())[:8]
        report = {
            "id": report_id,
            "tipo": report_type,
            "periodo_inizio": start_date,
            "periodo_fine": end_date,
            "contenuto": response,
            "metriche": {
                "fatturato": fatturato_totale,
                "num_vendite": num_vendite,
                "top_prodotti": [{"nome": p[0], "fatturato": p[1]} for p in top_products[:3]],
                "top_clienti": [{"nome": c[0], "spesa": c[1]} for c in top_clients[:3]],
                "prodotti_sotto_scorta": len(low_stock),
                "clienti_inattivi": len(inactive_clients)
            },
            "created_at": now.isoformat()
        }
        
        await db.ai_reports.insert_one(report)
        
        # Return without _id
        report.pop('_id', None)
        return report
        
    except Exception as e:
        logger.error(f"Error generating AI report: {e}")
        raise HTTPException(status_code=500, detail=f"Errore generazione report: {str(e)}")


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
