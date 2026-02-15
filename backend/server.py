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
    {"name": "FreshPoint Magazine", "url": "https://www.freshpointmagazine.it/feed/", "categoria": "ortofrutta"},
]

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


async def process_csv_row(row: dict, stats: dict, col_mapping: dict):
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
    
    causale = row.get(col_mapping['causale'] or 'Causale', '')
    
    # Skip empty rows
    if not nome_prodotto and not nome_cliente_fornitore:
        return
    
    # Determine if it's a sale (Scarico) or purchase (Carico)
    is_vendita = movimento.upper() == 'SCARICO' or 'VEN' in str(causale).upper()
    
    if is_vendita and nome_cliente_fornitore:
        # Process as sale - create/update cliente
        existing_cliente = await db.clienti.find_one({"nome": nome_cliente_fornitore})
        if not existing_cliente:
            cliente = Cliente(
                nome=nome_cliente_fornitore,
                codice=codice_cliente_fornitore
            )
            await db.clienti.insert_one(serialize_doc(cliente.model_dump()))
            stats['new_clienti'] += 1
            cliente_id = cliente.id
        else:
            cliente_id = existing_cliente.get('id')
            stats['existing_clienti'] += 1
        
        # Create vendita record
        vendita = Vendita(
            data=data,
            cliente_id=cliente_id,
            cliente_nome=nome_cliente_fornitore,
            prodotto_nome=nome_prodotto,
            quantita=quantita,
            prezzo_unitario=importo_unitario,
            totale=importo_totale,
            movimento=movimento
        )
        await db.vendite.insert_one(serialize_doc(vendita.model_dump()))
        stats['vendite_created'] += 1
        
        # Update cliente fatturato
        await db.clienti.update_one(
            {"nome": nome_cliente_fornitore},
            {"$inc": {"fatturato_totale": importo_totale}}
        )
        
    elif not is_vendita and nome_cliente_fornitore:
        # Process as purchase - create/update fornitore
        existing_fornitore = await db.fornitori.find_one({"nome": nome_cliente_fornitore})
        if not existing_fornitore:
            fornitore = Fornitore(
                nome=nome_cliente_fornitore,
                codice=codice_cliente_fornitore
            )
            await db.fornitori.insert_one(serialize_doc(fornitore.model_dump()))
            stats['new_fornitori'] += 1
            fornitore_id = fornitore.id
        else:
            fornitore_id = existing_fornitore.get('id')
            stats['existing_fornitori'] += 1
        
        # Create ordine record
        ordine = Ordine(
            data=data,
            fornitore_id=fornitore_id,
            fornitore_nome=nome_cliente_fornitore,
            prodotto_nome=nome_prodotto,
            quantita=quantita,
            prezzo_unitario=importo_unitario,
            totale=importo_totale
        )
        await db.ordini.insert_one(serialize_doc(ordine.model_dump()))
        stats['ordini_created'] += 1
        
        # Update fornitore fatturato
        await db.fornitori.update_one(
            {"nome": nome_cliente_fornitore},
            {"$inc": {"fatturato_totale": importo_totale}}
        )
    
    # Create/update prodotto
    if nome_prodotto:
        existing_prodotto = await db.prodotti.find_one({"nome": nome_prodotto})
        if not existing_prodotto:
            prodotto = Prodotto(
                nome=nome_prodotto,
                codice=codice_prodotto,
                prezzo_medio=importo_unitario
            )
            await db.prodotti.insert_one(serialize_doc(prodotto.model_dump()))
            stats['new_prodotti'] += 1
        else:
            stats['existing_prodotti'] += 1
            # Update quantity based on movement
            qty_change = quantita if not is_vendita else -quantita
            await db.prodotti.update_one(
                {"nome": nome_prodotto},
                {"$inc": {"quantita": qty_change}}
            )


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
            headers = list(df.columns)
            rows = df.fillna('').to_dict('records')
            # Convert all values to strings for consistency
            for row in rows:
                for k, v in row.items():
                    if pd.notna(v) and not isinstance(v, str):
                        row[k] = str(v)
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
        
        for row in rows:
            try:
                await process_csv_row(row, stats, col_mapping)
                stats['rows_processed'] += 1
            except Exception as e:
                stats['errors'].append(f"Riga {stats['rows_processed'] + 1}: {str(e)}")
        
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
    
    # Calculate derived fields
    for p in prodotti:
        quantita = p.get('quantita', 0)
        kg_pz = p.get('kg_per_pezzo', 0)
        prezzo = p.get('prezzo_medio', 0)
        minima = p.get('quantita_minima', 0)
        
        p['kg_rimanenti'] = quantita * kg_pz
        p['valore_scorte'] = quantita * prezzo
        
        if quantita <= 0:
            p['stato'] = 'non_disponibile'
        elif quantita > 0 and minima > 0 and quantita <= minima:
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


@api_router.get("/prodotti/{prodotto_nome}/analisi")
async def get_prodotto_analisi(prodotto_nome: str):
    """Get detailed analysis for a prodotto"""
    vendite = await db.vendite.find({"prodotto_nome": prodotto_nome}, {"_id": 0}).to_list(1000)
    
    totale_venduto = sum(v.get('quantita', 0) for v in vendite)
    ultima_vendita = max([v.get('data', '') for v in vendite], default='N/A')
    
    # Monthly average (last 6 months)
    six_months_ago = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    recent_vendite = [v for v in vendite if v.get('data', '') >= six_months_ago]
    media_mensile = sum(v.get('quantita', 0) for v in recent_vendite) / 6 if recent_vendite else 0
    
    # Top clienti
    clienti_count = {}
    for v in vendite:
        cliente = v.get('cliente_nome', '')
        clienti_count[cliente] = clienti_count.get(cliente, 0) + v.get('quantita', 0)
    
    top_clienti = sorted(clienti_count.items(), key=lambda x: x[1], reverse=True)[:3]
    clienti_str = ', '.join([c[0] for c in top_clienti]) if top_clienti else 'Nessuno'
    
    # Days until stock exhaustion
    prodotto = await db.prodotti.find_one({"nome": prodotto_nome}, {"_id": 0})
    quantita_attuale = prodotto.get('quantita', 0) if prodotto else 0
    giorni_esaurimento = int(quantita_attuale / media_mensile * 30) if media_mensile > 0 else 'N/A'
    
    return {
        "totaleVenduto": totale_venduto,
        "ultimaVendita": ultima_vendita,
        "mediaMensile": round(media_mensile, 2),
        "clientiPrincipali": clienti_str,
        "giorniEsaurimento": giorni_esaurimento
    }


# ----- Vendite -----
@api_router.get("/vendite")
async def get_vendite(
    cliente: Optional[str] = None,
    prodotto: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    query = {}
    
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
    
    # Current month revenue
    now = datetime.now()
    current_month_start = now.replace(day=1).strftime("%Y-%m-%d")
    current_month_vendite = [v for v in vendite if v.get('data', '') >= current_month_start]
    fatturato_mese = sum(abs(v.get('totale', 0)) for v in current_month_vendite)
    
    # Previous month revenue
    prev_month = now.replace(day=1) - timedelta(days=1)
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
    
    # Top clienti
    clienti_fatturato = {}
    for v in vendite:
        cliente = v.get('cliente_nome', '')
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


# ----- Dashboard Overview -----
@api_router.get("/dashboard")
async def get_dashboard():
    """Get dashboard overview data"""
    
    now = datetime.now()
    thirty_days_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Get recent vendite
    vendite_recenti = await db.vendite.find(
        {"data": {"$gte": thirty_days_ago}}, 
        {"_id": 0}
    ).sort("data", -1).to_list(100)
    
    # Use abs() for fatturato since SCARICO has negative values
    fatturato_mese = sum(abs(v.get('totale', 0)) for v in vendite_recenti)
    ordini_mese = len(vendite_recenti)
    
    # New clienti this month
    nuovi_clienti = await db.clienti.count_documents({
        "created_at": {"$gte": thirty_days_ago}
    })
    
    # Prodotti da ordinare
    prodotti_stats = await get_prodotti_stats()
    
    # Recent activity
    attivita_recenti = []
    for v in vendite_recenti[:10]:
        attivita_recenti.append({
            "tipo": "vendita",
            "descrizione": f"Vendita a {v.get('cliente_nome', 'N/A')}",
            "valore": abs(v.get('totale', 0)),
            "data": v.get('data', '')
        })
    
    return {
        "fatturatoMese": fatturato_mese,
        "ordiniMese": ordini_mese,
        "nuoviClienti": nuovi_clienti,
        "prodottiOrdinare": prodotti_stats.get('ordinare_count', 0),
        "prodottiScadenza": prodotti_stats.get('scadenza_count', 0),
        "attivitaRecenti": attivita_recenti
    }


# ----- Notizie -----

async def fetch_rss_feed(source: dict) -> List[dict]:
    """Fetch and parse an RSS feed"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(source["url"], follow_redirects=True)
            if response.status_code != 200:
                return []
            
            root = ET.fromstring(response.content)
            items = []
            
            # Standard RSS format
            for item in root.findall('.//item')[:10]:
                title = item.find('title')
                link = item.find('link')
                description = item.find('description')
                pub_date = item.find('pubDate')
                
                # Try to extract image
                image_url = None
                enclosure = item.find('enclosure')
                if enclosure is not None and enclosure.get('type', '').startswith('image'):
                    image_url = enclosure.get('url')
                
                # Try media:content
                media_content = item.find('.//{http://search.yahoo.com/mrss/}content')
                if media_content is not None and not image_url:
                    image_url = media_content.get('url')
                
                # Parse description for image if still none
                desc_text = description.text if description is not None else ''
                if not image_url and desc_text:
                    soup = BeautifulSoup(desc_text, 'html.parser')
                    img = soup.find('img')
                    if img and img.get('src'):
                        image_url = img.get('src')
                    desc_text = soup.get_text()[:200]
                
                items.append({
                    "titolo": title.text if title is not None else "Senza titolo",
                    "descrizione": desc_text[:300] if desc_text else "",
                    "url": link.text if link is not None else "",
                    "immagine_url": image_url,
                    "fonte": source["name"],
                    "categoria": source["categoria"],
                    "data_pubblicazione": pub_date.text[:20] if pub_date is not None else ""
                })
            
            return items
    except Exception as e:
        logger.error(f"Error fetching RSS from {source['name']}: {e}")
        return []


async def refresh_notizie():
    """Fetch news from all RSS sources and update database"""
    all_news = []
    
    tasks = [fetch_rss_feed(source) for source in RSS_SOURCES]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, list):
            all_news.extend(result)
    
    # Clear old news and insert new ones
    if all_news:
        await db.notizie.delete_many({})
        for news in all_news:
            notizia = Notizia(**news)
            await db.notizie.insert_one(serialize_doc(notizia.model_dump()))
    
    return len(all_news)


@api_router.get("/notizie")
async def get_notizie(limit: int = 50, categoria: Optional[str] = None):
    """Get news, optionally filtered by category"""
    query = {}
    if categoria and categoria != "all":
        query["categoria"] = categoria
    
    notizie = await db.notizie.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    # If no news, try to fetch them
    if len(notizie) == 0:
        count = await refresh_notizie()
        logger.info(f"Refreshed {count} news articles")
        notizie = await db.notizie.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
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
