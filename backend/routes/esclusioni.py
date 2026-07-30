from fastapi import APIRouter
from typing import List

from database import db

router = APIRouter()

SETTINGS_KEY = "prodotti_esclusi"


async def get_prodotti_esclusi() -> List[str]:
    """Return the list of product names excluded from all calculations."""
    doc = await db.settings.find_one({"key": SETTINGS_KEY})
    return doc.get("nomi", []) if doc else []


async def get_prodotti_esclusi_set() -> set:
    return set(await get_prodotti_esclusi())


@router.get("/esclusioni")
async def list_esclusioni():
    nomi = await get_prodotti_esclusi()
    return {"nomi": nomi, "count": len(nomi)}


@router.put("/esclusioni")
async def set_esclusioni(data: dict):
    nomi = [str(n) for n in data.get("nomi", []) if n]
    await db.settings.update_one(
        {"key": SETTINGS_KEY},
        {"$set": {"key": SETTINGS_KEY, "nomi": nomi}},
        upsert=True
    )
    return {"success": True, "count": len(nomi)}
