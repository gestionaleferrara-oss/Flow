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
    {"name": "FreshPlaza", "url": "https://www.freshplaza.it/rss/", "categoria": "ortofrutta"},
    {"name": "Italiafruit", "url": "https://www.italiafruit.net/rss.xml", "categoria": "ortofrutta"},
    {"name": "AgriSole", "url": "https://www.agrisole.it/rss/", "categoria": "agricoltura"},
    {"name": "ANSA Agricoltura", "url": "https://www.ansa.it/sito/notizie/economia/agroalimentare/agroalimentare_rss.xml", "categoria": "economia"},
]

# ======================= MARKET PRICE LINKS =======================
MARKET_PRICE_LINKS = [
    {"nome": "Bologna", "url": "https://www.cafrfruttaortaggi.it/listino/"},
    {"nome": "Milano", "url": "https://www.mercatomilano.it/quotazioni-frutta-verdura/"},
    {"nome": "Roma", "url": "https://www.carfruttaroma.it/listino/"},
    {"nome": "Torino", "url": "https://www.mercatoortofrutticolo.com/quotazioni/"},
    {"nome": "Verona", "url": "https://www.veronamercato.it/listino/"},
    {"nome": "Padova", "url": "https://www.mercatipavani.it/quotazioni/"},
]


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
    """Parse string to float, handling Italian number format"""
    if not value:
        return 0.0
    
    value = str(value).strip()
    # Remove currency symbols and spaces
    value = re.sub(r'[€\s]', '', value)
    # Handle Italian format (comma as decimal, dot as thousand separator)
    if ',' in value and '.' in value:
        value = value.replace('.', '').replace(',', '.')
    elif ',' in value:
        value = value.replace(',', '.')
    
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

async def process_csv_row(row: dict, stats: dict):
    """Process a single CSV row and update database"""
    
    movimento = row.get('Movimento', '').strip()
    data = parse_italian_date(row.get('Data', ''))
    codice_cliente_fornitore = row.get('Codice Cl./Fo.', '').strip()
    nome_cliente_fornitore = row.get('Decodifica Cl./Fo.', '').strip()
    codice_prodotto = row.get('Codice', '').strip()
    nome_prodotto = row.get('Decodifica', '').strip()
    quantita = parse_float(row.get('Quantità', row.get('Quantita', '0')))
    importo_unitario = parse_float(row.get('Importo Unitario', '0'))
    importo_totale = parse_float(row.get('Importo Totale', '0'))
    
    # Skip empty rows
    if not nome_prodotto and not nome_cliente_fornitore:
        return
    
    # Determine if it's a sale (Scarico) or purchase (Carico)
    is_vendita = movimento.upper() == 'SCARICO' or 'VEN' in str(row.get('Causale', '')).upper()
    
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


# ----- CSV Upload -----
@api_router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload and process CSV file"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Il file deve essere in formato CSV")
    
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
        'errors': []
    }
    
    try:
        content = await file.read()
        
        # Try different encodings
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
        
        for row in csv_reader:
            try:
                await process_csv_row(row, stats)
                stats['rows_processed'] += 1
            except Exception as e:
                stats['errors'].append(f"Riga {stats['rows_processed'] + 1}: {str(e)}")
        
        return {
            "success": True,
            "message": "File elaborato con successo",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
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
    
    # Calculate KPIs
    totale_euro = sum(v.get('totale', 0) for v in vendite)
    totale_articoli = sum(v.get('quantita', 0) for v in vendite)
    clienti_attivi = len(set(v.get('cliente_nome', '') for v in vendite))
    
    # Current month revenue
    now = datetime.now()
    current_month_start = now.replace(day=1).strftime("%Y-%m-%d")
    current_month_vendite = [v for v in vendite if v.get('data', '') >= current_month_start]
    fatturato_mese = sum(v.get('totale', 0) for v in current_month_vendite)
    
    # Previous month revenue
    prev_month = now.replace(day=1) - timedelta(days=1)
    prev_month_start = prev_month.replace(day=1).strftime("%Y-%m-%d")
    prev_month_end = prev_month.strftime("%Y-%m-%d")
    prev_month_vendite = [v for v in vendite if prev_month_start <= v.get('data', '') <= prev_month_end]
    fatturato_mese_prec = sum(v.get('totale', 0) for v in prev_month_vendite)
    
    # Percentage difference
    if fatturato_mese_prec > 0:
        diff_percentuale = ((fatturato_mese - fatturato_mese_prec) / fatturato_mese_prec) * 100
    else:
        diff_percentuale = 100 if fatturato_mese > 0 else 0
    
    # Monthly sales data
    vendite_mensili = {}
    for v in vendite:
        data = v.get('data', '')[:7]  # YYYY-MM
        vendite_mensili[data] = vendite_mensili.get(data, 0) + v.get('totale', 0)
    
    monthly_data = [{"data": k, "totale": v} for k, v in sorted(vendite_mensili.items())]
    
    # Daily sales data (for detailed view)
    vendite_giornaliere = {}
    for v in vendite:
        data = v.get('data', '')
        vendite_giornaliere[data] = vendite_giornaliere.get(data, 0) + v.get('totale', 0)
    
    daily_data = [{"data": k, "totale": v} for k, v in sorted(vendite_giornaliere.items())]
    
    # Top clienti
    clienti_fatturato = {}
    for v in vendite:
        cliente = v.get('cliente_nome', '')
        clienti_fatturato[cliente] = clienti_fatturato.get(cliente, 0) + v.get('totale', 0)
    
    top_clienti = [{"nome": k, "spesa": v} for k, v in sorted(clienti_fatturato.items(), key=lambda x: x[1], reverse=True)[:10]]
    
    # Top prodotti
    prodotti_quantita = {}
    for v in vendite:
        prod = v.get('prodotto_nome', '')
        prodotti_quantita[prod] = prodotti_quantita.get(prod, 0) + v.get('quantita', 0)
    
    top_prodotti = [{"nome": k, "quantita": v} for k, v in sorted(prodotti_quantita.items(), key=lambda x: x[1], reverse=True)[:10]]
    
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
    
    fatturato_mese = sum(v.get('totale', 0) for v in vendite_recenti)
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
            "valore": v.get('totale', 0),
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
@api_router.get("/notizie", response_model=List[Notizia])
async def get_notizie(limit: int = 20):
    notizie = await db.notizie.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return notizie


@api_router.post("/notizie", response_model=Notizia)
async def create_notizia(data: NotiziaCreate):
    notizia = Notizia(**data.model_dump())
    doc = serialize_doc(notizia.model_dump())
    await db.notizie.insert_one(doc)
    return notizia


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
