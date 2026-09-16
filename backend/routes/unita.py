"""Conversione in kg delle quantita' vendute, ricavata dal formato dell'articolo."""
import re

_LIQUIDI = re.compile(r'(\b(ML|LT|L)\.?\s*\d|\b\d+(,\d+)?\s*(ML|LT|L)\b)', re.I)
_GRAMMI = re.compile(r'\bGR\.?\s*(\d+(?:,\d+)?)', re.I)
_DECIMALE = re.compile(r'(?<![\d/+])(\d+,\d+)\s*[Xx]\s*\d')
_INTERO = re.compile(r'(?<![\d/+])(\d{2,3})\s*[Xx]\s*\d')


def kg_per_unita(nome: str):
    """Kg per unita' venduta. 1.0 = la quantita' e' gia' espressa in kg.
    None per i liquidi, dove il peso non ha senso."""
    n = nome or ""
    if _LIQUIDI.search(n):
        return None
    if re.search(r'\bKG', n, re.I):
        return 1.0          # articolo a peso: il venduto e' gia' in kg
    m = _GRAMMI.search(n)
    if m:
        return float(m.group(1).replace(',', '.')) / 1000
    m = _DECIMALE.search(n)
    if m:
        return float(m.group(1).replace(',', '.'))
    m = _INTERO.search(n)
    if m:
        return int(m.group(1)) / 1000
    return 1.0


def unita(nome: str) -> str:
    """'kg' se la quantita' registrata e' un peso, altrimenti 'pz' (confezioni)."""
    return 'kg' if kg_per_unita(nome) == 1.0 else 'pz'


def etichetta_qta(nome: str, qta) -> str:
    """Quantita' con la sua unita': '356 kg' oppure '269 pz'."""
    if qta is None:
        return '-'
    return f"{qta:,.0f}".replace(',', '.') + f" {unita(nome)}"


def etichetta_kg(nome: str, qta) -> str:
    """Es. '67 kg (x0,25)' oppure '356 kg' se la quantita' e' gia' a peso."""
    f = kg_per_unita(nome)
    if f is None or not qta:
        return '-'
    tot = f"{qta * f:,.0f}".replace(',', '.')
    if f == 1.0:
        return f"{tot} kg"
    return f"{tot} kg (x{str(round(f, 3)).replace('.', ',')})"


def kg(nome: str, qta) -> float:
    """Quantita' convertita in kg (0 se l'articolo non ha un peso)."""
    f = kg_per_unita(nome)
    if f is None or not qta:
        return 0.0
    return round(qta * f, 1)
