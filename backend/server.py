from fastapi import FastAPI, APIRouter, UploadFile
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import asyncio

from database import db, logger


async def create_indexes_background():
    """Create database indexes in background to not block startup"""
    try:
        # Add small delay to let the app fully start
        await asyncio.sleep(2)
        await db.vendite.create_index([("data", -1)], background=True)
        await db.vendite.create_index([("cliente_nome", 1)], background=True)
        await db.vendite.create_index([("prodotto_nome", 1)], background=True)
        await db.vendite.create_index([("cliente_id", 1)], background=True)
        await db.vendite.create_index([("data", 1), ("prodotto_nome", 1)], background=True)
        await db.vendite.create_index([("data", 1), ("cliente_nome", 1)], background=True)
        await db.ordini.create_index([("data", -1)], background=True)
        await db.ordini.create_index([("fornitore_nome", 1)], background=True)
        await db.ordini.create_index([("prodotto_nome", 1)], background=True)
        await db.prodotti.create_index([("nome", 1)], background=True)
        await db.clienti.create_index([("nome", 1)], background=True)
        await db.fornitori.create_index([("nome", 1)], background=True)
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create indexes in background task (non-blocking)
    asyncio.create_task(create_indexes_background())
    yield
    # Shutdown: nothing to clean up


# Create the main app with lifespan
app = FastAPI(lifespan=lifespan)


# Health check endpoint for Kubernetes (MUST be at root level, not under /api)
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Gestio API v1.0"}


@api_router.post("/fix-prezzi")
async def fix_prezzi_vendite():
    """
    Fix incorrect prices in vendite records.
    If prezzo_unitario is way off from totale/quantita, recalculate it.
    """
    fixed_count = 0
    errors = []
    
    try:
        # Get all vendite with both totale and quantita
        vendite = await db.vendite.find(
            {"quantita": {"$ne": 0}, "totale": {"$ne": 0}},
            {"_id": 1, "id": 1, "quantita": 1, "prezzo_unitario": 1, "totale": 1, "prodotto_nome": 1}
        ).to_list(100000)
        
        for v in vendite:
            quantita = abs(v.get('quantita', 0))
            totale = abs(v.get('totale', 0))
            prezzo_attuale = v.get('prezzo_unitario', 0)
            
            if quantita > 0 and totale > 0:
                prezzo_calcolato = totale / quantita
                
                # If current price is more than 10x or less than 0.1x the calculated price, fix it
                if prezzo_attuale > 0:
                    ratio = prezzo_attuale / prezzo_calcolato
                    if ratio > 10 or ratio < 0.1:
                        # Fix the price
                        await db.vendite.update_one(
                            {"_id": v["_id"]},
                            {"$set": {"prezzo_unitario": round(prezzo_calcolato, 4)}}
                        )
                        fixed_count += 1
                elif prezzo_attuale == 0:
                    # Set missing price
                    await db.vendite.update_one(
                        {"_id": v["_id"]},
                        {"$set": {"prezzo_unitario": round(prezzo_calcolato, 4)}}
                    )
                    fixed_count += 1
        
        # Also fix ordini (purchases)
        ordini = await db.ordini.find(
            {"quantita": {"$ne": 0}, "totale": {"$ne": 0}},
            {"_id": 1, "quantita": 1, "prezzo_unitario": 1, "totale": 1}
        ).to_list(100000)
        
        ordini_fixed = 0
        for o in ordini:
            quantita = abs(o.get('quantita', 0))
            totale = abs(o.get('totale', 0))
            prezzo_attuale = o.get('prezzo_unitario', 0)
            
            if quantita > 0 and totale > 0:
                prezzo_calcolato = totale / quantita
                
                if prezzo_attuale > 0:
                    ratio = prezzo_attuale / prezzo_calcolato
                    if ratio > 10 or ratio < 0.1:
                        await db.ordini.update_one(
                            {"_id": o["_id"]},
                            {"$set": {"prezzo_unitario": round(prezzo_calcolato, 4)}}
                        )
                        ordini_fixed += 1
                elif prezzo_attuale == 0:
                    await db.ordini.update_one(
                        {"_id": o["_id"]},
                        {"$set": {"prezzo_unitario": round(prezzo_calcolato, 4)}}
                    )
                    ordini_fixed += 1
        
        return {
            "success": True,
            "vendite_fixed": fixed_count,
            "ordini_fixed": ordini_fixed,
            "message": f"Corretti {fixed_count} vendite e {ordini_fixed} ordini"
        }
    except Exception as e:
        logger.error(f"Error fixing prices: {e}")
        return {"success": False, "error": str(e)}


@api_router.post("/import-giacenze")
async def import_giacenze_excel(file: UploadFile):
    """
    Import stock levels from GiacenzediMagazzino.xlsx
    Updates existing products with correct stock quantities.
    """
    import pandas as pd
    from io import BytesIO
    
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents), header=1)
        
        # Expected column names
        cols = df.columns.tolist()
        
        updated = 0
        created = 0
        errors = []
        
        for _, row in df.iterrows():
            try:
                # Get product info - try different column name variants
                codice = str(row.get('Codice', row.get(cols[2], ''))).strip() if pd.notna(row.get('Codice', row.get(cols[2], ''))) else ''
                descrizione = str(row.get('Descrizione', row.get(cols[3], ''))).strip() if pd.notna(row.get('Descrizione', row.get(cols[3], ''))) else ''
                
                if not descrizione:
                    continue
                
                # Get stock data
                giacenza = float(row.get('Giacenza Prodotto', row.get(cols[25], 0)) or 0)
                scorta_minima = float(row.get('Scorta minima', row.get(cols[24], 0)) or 0)
                
                # Try to find existing product by name
                existing = await db.prodotti.find_one({"nome": {"$regex": f"^{descrizione[:20]}", "$options": "i"}})
                
                if existing:
                    # Update existing product
                    update_data = {
                        "quantita": max(0, giacenza),  # Don't allow negative
                        "quantita_minima": scorta_minima
                    }
                    if codice:
                        update_data["codice"] = codice
                    
                    await db.prodotti.update_one(
                        {"_id": existing["_id"]},
                        {"$set": update_data}
                    )
                    updated += 1
                else:
                    # Create new product
                    from models import Prodotto
                    from utils import serialize_doc
                    import uuid
                    
                    prodotto = {
                        "id": str(uuid.uuid4()),
                        "nome": descrizione,
                        "codice": codice,
                        "quantita": max(0, giacenza),
                        "quantita_minima": scorta_minima,
                        "prezzo_medio": 0,
                        "valore_scorte": 0
                    }
                    await db.prodotti.insert_one(prodotto)
                    created += 1
                    
            except Exception as e:
                errors.append(f"{descrizione}: {str(e)}")
        
        return {
            "success": True,
            "updated": updated,
            "created": created,
            "errors": errors[:10],  # First 10 errors
            "message": f"Aggiornati {updated} prodotti, creati {created} nuovi"
        }
    except Exception as e:
        logger.error(f"Error importing giacenze: {e}")
        return {"success": False, "error": str(e)}


# Import and include all route modules
from routes.upload import router as upload_router
from routes.entities import router as entities_router
from routes.prodotti import router as prodotti_router
from routes.vendite import router as vendite_router
from routes.dashboard import router as dashboard_router
from routes.news import router as news_router
from routes.pdf_export import router as pdf_export_router
from routes.forecast import router as forecast_router

api_router.include_router(upload_router)
api_router.include_router(entities_router)
api_router.include_router(prodotti_router)
api_router.include_router(vendite_router)
api_router.include_router(dashboard_router)
api_router.include_router(news_router)
api_router.include_router(pdf_export_router)
api_router.include_router(forecast_router)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
