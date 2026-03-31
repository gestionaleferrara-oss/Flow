from fastapi import APIRouter, BackgroundTasks
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import httpx
import re
import xml.etree.ElementTree as ET
import asyncio

from database import db, logger
from models import Notizia, NotiziaCreate
from utils import serialize_doc

router = APIRouter()

RSS_SOURCES = [
    {"name": "FreshPlaza", "url": "https://www.freshplaza.it/rss.xml", "categoria": "ortofrutta"},
    {"name": "Corriere Ortofrutticolo", "url": "https://www.corriereortofrutticolo.it/feed/", "categoria": "ortofrutta"},
]
MYFRUIT_NEWS_URL = "https://www.myfruit.it/news-page/1"
_market_price_cache = {"links": [], "last_updated": None}

ITALIAN_MONTHS = {'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'mag': '05', 'giu': '06', 'lug': '07', 'ago': '08', 'set': '09', 'ott': '10', 'nov': '11', 'dic': '12'}


def parse_rss_date(date_str: str) -> datetime:
    if not date_str:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime(2000, 1, 1, tzinfo=timezone.utc)


def parse_italian_news_date(date_str: str) -> datetime:
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
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http_client:
            resp = await http_client.get(MYFRUIT_NEWS_URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = []
            seen_urls = set()
            cards = soup.find_all('div', class_='blog-card-details')
            for card in cards:
                parent_a = card.find_parent('a', href=True)
                if not parent_a:
                    continue
                href = parent_a['href']
                if href in seen_urls or not href.startswith('https://www.myfruit.it/news/'):
                    continue
                if '/category/' in href or '/news-page/' in href:
                    continue
                seen_urls.add(href)
                h5 = card.find('h5', class_='post-title-heading')
                title = h5.get_text(strip=True) if h5 else ''
                if not title or len(title) < 5:
                    continue
                desc_div = card.find('div', class_='post-description')
                description = desc_div.get_text(strip=True)[:300] if desc_div else ''
                image_url = None
                blog_card = parent_a.parent
                if blog_card:
                    img = blog_card.find('img')
                    if img:
                        image_url = img.get('src') or img.get('data-src')
                today = datetime.now(timezone.utc)
                offset_date = today - timedelta(hours=len(items) * 6)
                items.append({
                    "titolo": title, "descrizione": description, "url": href,
                    "immagine_url": image_url, "fonte": "Myfruit", "categoria": "ortofrutta",
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
    all_news = []
    tasks = [fetch_rss_feed(source) for source in RSS_SOURCES]
    tasks.append(scrape_myfruit_news())
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, list):
            all_news.extend(result)
    all_news.sort(key=lambda x: x.get('_sort_date', ''), reverse=True)
    if all_news:
        await db.notizie.delete_many({})
        for news in all_news:
            sort_date = news.pop('_sort_date', '')
            notizia = Notizia(**news)
            doc = serialize_doc(notizia.model_dump())
            doc['sort_date'] = sort_date
            await db.notizie.insert_one(doc)
    return len(all_news)


@router.get("/notizie")
async def get_notizie(limit: int = 50, categoria: Optional[str] = None):
    query = {}
    if categoria and categoria != "all":
        query["categoria"] = categoria
    notizie = await db.notizie.find(query, {"_id": 0}).sort("sort_date", -1).limit(limit).to_list(limit)
    if len(notizie) == 0:
        count = await refresh_notizie()
        logger.info(f"Refreshed {count} news articles")
        notizie = await db.notizie.find(query, {"_id": 0}).sort("sort_date", -1).limit(limit).to_list(limit)
    for n in notizie:
        n.pop('sort_date', None)
    return notizie


@router.post("/notizie/refresh")
async def trigger_refresh_notizie(background_tasks: BackgroundTasks):
    background_tasks.add_task(refresh_notizie)
    return {"message": "Aggiornamento notizie avviato in background"}


@router.get("/notizie/categorie")
async def get_categorie_notizie():
    return await db.notizie.distinct("categoria")


@router.post("/notizie")
async def create_notizia(data: NotiziaCreate):
    notizia = Notizia(**data.model_dump())
    doc = serialize_doc(notizia.model_dump())
    await db.notizie.insert_one(doc)
    return notizia


# ===== Prezzi Mercati =====

@router.get("/prezzi-mercati")
async def get_prezzi_mercati():
    BASE_URL = "https://www.freshplaza.it"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            homepage_response = await client.get(BASE_URL + "/")
            homepage_html = homepage_response.text
            anchor_text = "<h3>Ultimi prezzi ortofrutticoli"
            anchor_index = homepage_html.find(anchor_text)
            if anchor_index == -1:
                logger.warning("FreshPlaza: Could not find anchor text, using fallback")
                return _get_fallback_prezzi_mercati()
            link_start_string = '<a href="'
            link_start_index = homepage_html.rfind(link_start_string, 0, anchor_index)
            url_start_index = link_start_index + len(link_start_string)
            url_end_index = homepage_html.find('"', url_start_index)
            relative_url = homepage_html[url_start_index:url_end_index]
            article_url = BASE_URL + relative_url
            logger.info(f"FreshPlaza: Found article URL: {article_url}")
            article_response = await client.get(article_url)
            article_html = article_response.text
            start_string = '<main itemprop="articleBody">'
            text_start_index = article_html.find(start_string)
            if text_start_index == -1:
                logger.warning("FreshPlaza: Could not find article content, using fallback")
                return _get_fallback_prezzi_mercati()
            article_text_block = article_html[text_start_index:]
            links_regex = re.compile(r'<a href="([^"]+)"[^>]*>([\s\S]*?)</a>', re.IGNORECASE)
            links = []
            seen_cities = set()
            target_cities = ['cesena', 'lusia', 'torino', 'verona', 'bologna', 'milano', 'padova', 'firenze', 'roma', 'napoli', 'bari']
            for match in links_regex.finditer(article_text_block):
                link_url = match.group(1)
                link_content = match.group(2)
                clean_content = re.sub(r'<[^>]*>', '', link_content).strip()
                if link_url.endswith('.pdf') or 'agfstorage' in link_url or 'caat.it' in link_url or 'mercato' in link_url:
                    city_name = None
                    for city in target_cities:
                        if city in clean_content.lower():
                            city_name = city.capitalize()
                            break
                    if city_name and city_name.lower() not in seen_cities:
                        seen_cities.add(city_name.lower())
                        links.append({"nome": city_name, "url": link_url, "tipo": "PDF" if link_url.endswith('.pdf') else "Web"})
            if links:
                logger.info(f"FreshPlaza: Found {len(links)} market links")
                return links
            else:
                logger.warning("FreshPlaza: No links found, using fallback")
                return _get_fallback_prezzi_mercati()
    except Exception as e:
        logger.error(f"FreshPlaza scraping error: {e}")
        return _get_fallback_prezzi_mercati()


def _get_fallback_prezzi_mercati():
    return [
        {"nome": "Cesena", "url": "https://www.freshplaza.it/article/9714986/cesena-prezzi-all-ingrosso-di-frutta-e-verdura/", "tipo": "Web"},
        {"nome": "Bologna", "url": "https://www.freshplaza.it/article/9714987/bologna-prezzi-all-ingrosso-di-frutta-e-verdura/", "tipo": "Web"},
        {"nome": "Milano", "url": "https://www.freshplaza.it/article/9714988/milano-prezzi-all-ingrosso-di-frutta-e-verdura/", "tipo": "Web"},
        {"nome": "Verona", "url": "https://www.freshplaza.it/article/9714989/verona-prezzi-all-ingrosso-di-frutta-e-verdura/", "tipo": "Web"},
        {"nome": "Torino", "url": "https://www.freshplaza.it/article/9714990/torino-prezzi-all-ingrosso-di-frutta-e-verdura/", "tipo": "Web"},
        {"nome": "Padova", "url": "https://www.freshplaza.it/article/9714991/padova-prezzi-all-ingrosso-di-frutta-e-verdura/", "tipo": "Web"},
    ]


# ===== Meteo =====

@router.get("/meteo")
async def get_meteo(lat: float = 44.4949, lon: float = 11.3426):
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


# ===== Ticker News =====

@router.get("/ticker-news")
async def get_ticker_news():
    cache = await db.cache.find_one({"key": "ticker_news"}, {"_id": 0})
    if cache:
        cached_at = cache.get("cached_at")
        if cached_at:
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - cached_at).total_seconds() < 3600:
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
                    clean_title = title.rsplit(" - ", 1)[0].strip() if " - " in title else title
                    if clean_title.lower() in seen_titles:
                        continue
                    seen_titles.add(clean_title.lower())
                    source = entry.get("source", {}).get("title", "")
                    link = entry.get("link", "")
                    published = entry.get("published", "")
                    items.append({"titolo": clean_title, "fonte": source, "url": link, "data": published})
            except Exception as e:
                logger.error(f"Error fetching ticker feed: {e}")
        return items[:20]

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, fetch_ticker)
    await db.cache.update_one({"key": "ticker_news"}, {"$set": {"key": "ticker_news", "data": data, "cached_at": datetime.now(timezone.utc)}}, upsert=True)
    return data


# ===== Trends Vendite =====

@router.get("/trends-vendite")
async def get_trends_vendite(periodo: str = "2w", ordina_per: str = "interest", limite: int = 5):
    latest_sale = await db.vendite.find_one({}, {"_id": 0, "data": 1}, sort=[("data", -1)])
    if latest_sale and latest_sale.get('data'):
        try:
            reference_date = datetime.strptime(latest_sale['data'], "%Y-%m-%d")
        except Exception:
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()

    periodo_days = {"1w": 7, "2w": 14, "1m": 30, "3m": 90}.get(periodo, 14)
    current_end = reference_date.strftime("%Y-%m-%d")
    current_start = (reference_date - timedelta(days=periodo_days)).strftime("%Y-%m-%d")
    prev_end = current_start
    prev_start = (reference_date - timedelta(days=periodo_days * 2)).strftime("%Y-%m-%d")

    current_sales = await db.vendite.find({"data": {"$gt": current_start, "$lte": current_end}}, {"_id": 0, "prodotto_nome": 1, "quantita": 1, "totale": 1, "prezzo_unitario": 1}).to_list(100000)
    prev_sales = await db.vendite.find({"data": {"$gt": prev_start, "$lte": prev_end}}, {"_id": 0, "prodotto_nome": 1, "quantita": 1, "totale": 1}).to_list(100000)
    
    # Get purchase prices for margin calculation
    prezzi_acquisto = {}
    prodotti = await db.prodotti.find({}, {"_id": 0, "nome": 1, "prezzo_medio": 1}).to_list(10000)
    for p in prodotti:
        if p.get('prezzo_medio', 0) > 0:
            prezzi_acquisto[p['nome']] = p['prezzo_medio']

    current_by_product = {}
    total_fatturato = 0
    for s in current_sales:
        prod = s.get('prodotto_nome', '')
        if prod:
            if prod not in current_by_product:
                current_by_product[prod] = {'qty': 0, 'totale': 0, 'richieste': 0, 'prezzo_vendita_sum': 0, 'prezzo_vendita_count': 0}
            current_by_product[prod]['qty'] += abs(s.get('quantita', 0))
            current_by_product[prod]['totale'] += abs(s.get('totale', 0))
            current_by_product[prod]['richieste'] += 1
            if s.get('prezzo_unitario', 0) > 0:
                current_by_product[prod]['prezzo_vendita_sum'] += s.get('prezzo_unitario', 0)
                current_by_product[prod]['prezzo_vendita_count'] += 1
            total_fatturato += abs(s.get('totale', 0))

    prev_by_product = {}
    for s in prev_sales:
        prod = s.get('prodotto_nome', '')
        if prod:
            if prod not in prev_by_product:
                prev_by_product[prod] = {'qty': 0, 'totale': 0, 'richieste': 0}
            prev_by_product[prod]['qty'] += abs(s.get('quantita', 0))
            prev_by_product[prod]['totale'] += abs(s.get('totale', 0))
            prev_by_product[prod]['richieste'] += 1

    trends = []
    for prod, curr_data in current_by_product.items():
        prev_data = prev_by_product.get(prod, {'qty': 0, 'totale': 0, 'richieste': 0})
        curr_qty = curr_data['qty']
        prev_qty = prev_data['qty']
        curr_totale = curr_data['totale']
        prev_totale = prev_data['totale']
        curr_richieste = curr_data['richieste']
        prev_richieste = prev_data.get('richieste', 0)
        qty_change = ((curr_qty - prev_qty) / prev_qty * 100) if prev_qty > 0 else (100.0 if curr_qty > 0 else 0.0)
        rev_change = ((curr_totale - prev_totale) / prev_totale * 100) if prev_totale > 0 else (100.0 if curr_totale > 0 else 0.0)
        rev_share = (curr_totale / total_fatturato * 100) if total_fatturato > 0 else 0
        interest_score = rev_share * (1 + min(abs(qty_change), 200) / 100)
        
        # Calculate margin percentage - correct formula
        # Prezzo vendita = Fatturato periodo / Quantità venduta periodo
        # Margine = (Prezzo Vendita - Prezzo Acquisto) / Prezzo Acquisto * 100
        prezzo_acquisto = prezzi_acquisto.get(prod, 0)
        prezzo_vendita_periodo = curr_totale / curr_qty if curr_qty > 0 else 0
        
        if prezzo_vendita_periodo > 0 and prezzo_acquisto > 0:
            margine_pct = ((prezzo_vendita_periodo - prezzo_acquisto) / prezzo_acquisto * 100)
            # Cap margin at reasonable values (-100 to 500)
            margine_pct = max(-100, min(500, margine_pct))
        else:
            margine_pct = 0
        
        trends.append({
            "prodotto": prod, "quantita_2w": round(curr_qty, 1), "quantita_prev": round(prev_qty, 1),
            "fatturato_2w": round(curr_totale, 2), "fatturato_prev": round(prev_totale, 2),
            "richieste": curr_richieste, "richieste_prev": prev_richieste,
            "margine_pct": round(margine_pct, 1),
            "variazione_qty_pct": round(qty_change, 1), "variazione_fatturato_pct": round(rev_change, 1),
            "quota_fatturato_pct": round(rev_share, 2), "interest_score": round(interest_score, 2),
            "trend": "up" if qty_change > 5 else "down" if qty_change < -5 else "stable"
        })

    sort_keys = {"interest": lambda x: x['interest_score'], "fatturato": lambda x: x['fatturato_2w'], "quantita": lambda x: x['quantita_2w'], "variazione": lambda x: abs(x['variazione_qty_pct']), "qty": lambda x: x['quantita_2w'], "revenue": lambda x: x['fatturato_2w'], "richieste": lambda x: x['richieste'], "margine": lambda x: x['margine_pct']}
    sort_fn = sort_keys.get(ordina_per, sort_keys["interest"])
    trends.sort(key=sort_fn, reverse=True)

    limite = min(limite, 50)
    top_products = trends[:limite]
    periodo_labels = {"1w": "1 settimana", "2w": "2 settimane", "1m": "1 mese", "3m": "3 mesi"}

    return {
        "periodo": periodo, "periodo_label": periodo_labels.get(periodo, periodo),
        "periodo_attuale": f"{current_start} - {current_end}", "periodo_precedente": f"{prev_start} - {prev_end}",
        "fatturato_totale": round(total_fatturato, 2), "ordina_per": ordina_per,
        "totale_prodotti": len(trends), "top_prodotti": top_products
    }


# ===== Google Trends =====

@router.get("/trends-frutta-secca")
async def get_trends_frutta_secca():
    keywords = ["pistacchi", "mandorle", "noci", "nocciole", "anacardi"]
    cache = await db.cache.find_one({"key": "trends_frutta_secca"}, {"_id": 0})
    if cache:
        cached_at = cache.get("cached_at")
        if cached_at:
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - cached_at).total_seconds() < 21600:
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
                if len(values) >= 4:
                    recent = sum(values[-2:]) / 2
                    prior = sum(values[-4:-2]) / 2
                    change = ((recent - prior) / max(prior, 1)) * 100
                else:
                    change = 0.0
                sparkline = values[-12:] if len(values) >= 12 else values
                results.append({"keyword": kw.capitalize(), "current_interest": int(current), "avg_interest": round(avg, 1), "change_pct": round(change, 1), "sparkline": sparkline, "trend": "up" if change > 5 else "down" if change < -5 else "stable"})
            results.sort(key=lambda x: x["current_interest"], reverse=True)
            return results
        except Exception as e:
            logger.error(f"Error fetching Google Trends: {e}")
            return []

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, fetch_trends)
    await db.cache.update_one({"key": "trends_frutta_secca"}, {"$set": {"key": "trends_frutta_secca", "data": data, "cached_at": datetime.now(timezone.utc)}}, upsert=True)
    return data


@router.get("/trends/{categoria}")
async def get_trends_by_category(categoria: str):
    categories = {
        "frutta-secca": ["pistacchi", "mandorle", "noci", "nocciole", "anacardi"],
        "frutta": ["mele", "pere", "arance", "banane", "kiwi"],
        "verdura": ["pomodori", "zucchine", "melanzane", "peperoni", "carote"],
        "spezie": ["zafferano", "pepe", "cannella", "curcuma", "origano"]
    }
    keywords = categories.get(categoria, categories["frutta-secca"])
    cache_key = f"trends_{categoria}"
    cache = await db.cache.find_one({"key": cache_key}, {"_id": 0})
    if cache:
        cached_at = cache.get("cached_at")
        if cached_at:
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - cached_at).total_seconds() < 21600:
                return {"categoria": categoria, "keywords": cache.get("data", [])}

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
                if len(values) >= 4:
                    recent = sum(values[-2:]) / 2
                    prior = sum(values[-4:-2]) / 2
                    change = ((recent - prior) / max(prior, 1)) * 100
                else:
                    change = 0.0
                sparkline = values[-12:] if len(values) >= 12 else values
                results.append({"keyword": kw.capitalize(), "current_interest": int(current), "avg_interest": round(avg, 1), "change_pct": round(change, 1), "sparkline": sparkline, "trend": "up" if change > 5 else "down" if change < -5 else "stable"})
            results.sort(key=lambda x: x["current_interest"], reverse=True)
            return results
        except Exception as e:
            logger.error(f"Error fetching Google Trends for {categoria}: {e}")
            return []

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, fetch_trends)
    await db.cache.update_one({"key": cache_key}, {"$set": {"key": cache_key, "data": data, "cached_at": datetime.now(timezone.utc)}}, upsert=True)
    return {"categoria": categoria, "keywords": data}
