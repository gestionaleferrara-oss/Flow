"""Previsione con media ponderata: 70% anno base + 30% anno precedente."""
import json

PESO_BASE = 0.7
PESO_PREC = 0.3


def pondera(v_base: float, v_prec: float) -> float:
    """Media ponderata 70/30. Se l'anno precedente non ha dati resta il solo anno base."""
    v_base = v_base or 0
    v_prec = v_prec or 0
    return PESO_BASE * v_base + PESO_PREC * v_prec if v_prec > 0 else v_base


def _k(v) -> str:
    return json.dumps(v, sort_keys=True, default=str)


async def agg_ponderata(coll, base: dict, s1: str, e1: str, s2: str, e2: str,
                        group: dict, campi, limit: int = 20000) -> list:
    """Stesso $group sulle due finestre storiche; i campi numerici indicati
    vengono fusi con media ponderata 60% finestra base / 40% finestra precedente.
    Restano solo le chiavi presenti nella finestra base."""
    async def run(s, e):
        return await coll.aggregate([
            {"$match": {**base, "data": {"$gte": s, "$lte": e}}},
            {"$group": group},
        ]).to_list(limit)

    righe = await run(s1, e1)
    prec = {_k(r['_id']): r for r in await run(s2, e2)}
    for r in righe:
        p = prec.get(_k(r['_id']))
        for c in campi:
            r[c] = pondera(r.get(c), p.get(c) if p else 0)
    return righe


def anno_prec(data: str) -> str:
    """Stessa data dell'anno precedente (365 giorni)."""
    from datetime import datetime, timedelta
    return (datetime.strptime(data, "%Y-%m-%d") - timedelta(days=365)).strftime("%Y-%m-%d")
