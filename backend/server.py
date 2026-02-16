from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
import os

from database import db, logger

# Create the main app
app = FastAPI()


@app.on_event("startup")
async def startup_event():
    try:
        await db.vendite.create_index([("data", -1)])
        await db.vendite.create_index([("cliente_nome", 1)])
        await db.vendite.create_index([("prodotto_nome", 1)])
        await db.vendite.create_index([("cliente_id", 1)])
        await db.vendite.create_index([("data", 1), ("prodotto_nome", 1)])
        await db.vendite.create_index([("data", 1), ("cliente_nome", 1)])
        await db.ordini.create_index([("data", -1)])
        await db.ordini.create_index([("fornitore_nome", 1)])
        await db.ordini.create_index([("prodotto_nome", 1)])
        await db.prodotti.create_index([("nome", 1)])
        await db.clienti.create_index([("nome", 1)])
        await db.fornitori.create_index([("nome", 1)])
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")


# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Gestio API v1.0"}


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
