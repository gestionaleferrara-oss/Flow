from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid


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
