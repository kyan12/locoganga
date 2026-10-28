#!/usr/bin/env python3
"""Build the storefront catalog (app/static/fallback_products.json) from public storefront feeds.

Usage:  python scripts/build_catalog.py [--target 500]
Pulls products from each source, normalizes price to USD, sanitizes descriptions, assigns a
storefront category, balances categories to the target count, and verifies every image loads.
"""
import argparse, hashlib, html, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import requests

OUT = os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'fallback_products.json')
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36'}
FX = {'USD': 1.0, 'CAD': 0.72, 'INR': 1 / 84.0}
MARKUP = float(os.environ.get('PRICE_MARKUP', 1.45))

# (domain, currency, default category, quota)
SOURCES = [
    ('creative-kitchens.myshopify.com', 'CAD', 'kitchen', 50),
    ('shop-kitchen-gadget.myshopify.com', 'USD', 'kitchen', 25),
    ('cooktime.myshopify.com', 'USD', 'kitchen', 12),
    ('lamshop-8866.myshopify.com', 'USD', 'kitchen', 7),
    ('millenniumkitchen.myshopify.com', 'USD', 'kitchen', 6),
    ('homestuff24.myshopify.com', 'USD', 'home', 45),
    ('homewetbar.com', 'USD', 'home', 30),
    ('tomahawk.tools', 'INR', 'tools', 48),
    ('gadgets-house-store.myshopify.com', 'USD', 'tools', 12),
    ('garden-tool-co.myshopify.com', 'USD', 'garden', 25),
    ('wacky-yard.myshopify.com', 'USD', 'garden', 18),
    ('winona-gardens.myshopify.com', 'CAD', 'garden', 12),
    ('thegadgetsmink.com', 'INR', 'electronics', 35),
    ('latestphoneaccessories.myshopify.com', 'USD', 'electronics', 22),
    ('magneticchargingcable.myshopify.com', 'USD', 'electronics', 3),
    ('home-fitness-goods-store.myshopify.com', 'CAD', 'fitness', 26),
    ('your-gym-my-gym.myshopify.com', 'USD', 'fitness', 11),
    ('shopwellstore.myshopify.com', 'USD', 'fitness', 5),
    ('wearbands.com', 'USD', 'fitness', 10),
    ('camping-gear-a.myshopify.com', 'USD', 'outdoors', 34),
    ('petsy.online', 'INR', 'pets', 64),
]
CATEGORIES = {'kitchen': 'Kitchen & Dining', 'home': 'Home & Decor', 'tools': 'Tools & Hardware',
              'garden': 'Garden & Patio', 'electronics': 'Phone & Electronics', 'fitness': 'Sports & Fitness',
              'outdoors': 'Camping & Outdoors', 'pets': 'Pet Supplies'}
SKIP = re.compile(r'personali[sz]ed|custom|gift ?card|bundle|insurance|subscription|membership|sample|'
                  r'test product|shopify|carbon offset|warranty|protection plan|e-?gift|donation|wholesale|'
                  r'shipping|deposit|pre-?order', re.I)
SRC_WORDS = re.compile(r'myshopify|shopify|\.com\b|\.online\b|\.tools\b|\bwww\.|https?://|'
                       r'demonstration store|demo store|test store|orders will (not )?be fulfilled', re.I)


class Sanitizer(HTMLParser):
    """Keep simple prose/list markup; drop links, media, scripts, styles and attributes."""
    KEEP = {'p', 'ul', 'ol', 'li', 'br', 'strong', 'b', 'em', 'h3', 'h4'}
    DROP = {'script', 'style', 'iframe', 'video', 'svg', 'table', 'noscript', 'form'}

    def __init__(self):
        super().__init__(convert_charrefs=True); self.out = []; self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.DROP: self.skip += 1
        elif not self.skip and tag in self.KEEP:
            self.out.append('<br>' if tag == 'br' else f'<{"h4" if tag == "h3" else tag}>')

    def handle_endtag(self, tag):
        if tag in self.DROP: self.skip = max(0, self.skip - 1)
        elif not self.skip and tag in self.KEEP and tag != 'br':
            self.out.append(f'</{"h4" if tag == "h3" else tag}>')
        elif not self.skip and tag in ('div', 'span') and self.out and not self.out[-1].endswith('>'):
            self.out.append(' ')

    def handle_data(self, data):
        if not self.skip: self.out.append(html.escape(data))


def clean_description(body):
    s = Sanitizer(); s.feed(body or ''); text = ''.join(s.out)
    # drop any fragment that references a web address or store
    parts = re.split(r'(?<=</p>)|(?<=</li>)|<br>', text)
    parts = [p for p in parts if not SRC_WORDS.search(p)]
    text = re.sub(r'(<(p|li|h4|strong|b|em)>\s*</\2>)', '', ''.join(parts))
    text = re.sub(r'\s{2,}', ' ', text).strip()
    return text[:6000]


def clean_title(t):
    t = html.unescape(t or '').replace('®', '').replace('™', '')
    t = re.sub(r'\s+', ' ', t).strip(' -|,')
    if len(t) > 110: t = t[:110].rsplit(' ', 1)[0]
    return t


def fetch_store(domain):
    out = []
    for page in range(1, 6):
        try:
            r = requests.get(f'https://{domain}/products.json', params={'limit': 250, 'page': page}, headers=UA, timeout=25)
            ps = r.json().get('products', [])
        except Exception as e:
            print(f'  {domain} page {page}: {e}', file=sys.stderr); break
        out += ps
        if len(ps) < 250: break
        time.sleep(0.5)
    return out


def img(src, width=800):
    src = src.replace('http://', 'https://', 1)
    return src + ('&' if '?' in src else '?') + f'width={width}'


def to_product(p, currency, category):
    title = clean_title(p.get('title'))
    images = [i['src'] for i in (p.get('images') or []) if i.get('src')]
    variants = [v for v in (p.get('variants') or []) if v.get('available', True)]
    if not title or len(title) < 12 or SKIP.search(title) or SKIP.search(p.get('product_type') or '') or not images or not variants:
        return None
    rate = FX[currency]
    spu = 'LG' + hashlib.sha1(f"{p['id']}".encode()).hexdigest()[:8].upper()
    skus = []
    for i, v in enumerate(variants[:24]):
        usd = float(v.get('price') or 0) * rate
        if usd < 8 or usd > 300:
            continue
        opt = ' / '.join(x for x in (v.get('option1'), v.get('option2'), v.get('option3'))
                         if x and x.lower() not in ('default title', 'default'))
        skus.append({'SKU': f'{spu}-{i + 1:02d}', 'option': clean_title(opt)[:60],
                     'supplyPrice': round(usd / MARKUP, 2), 'countryCode': 'US',
                     'image': img(v['featured_image']['src']) if v.get('featured_image') else None})
    if not skus:
        return None
    seed = int(hashlib.md5(spu.encode()).hexdigest(), 16)
    return {
        'SPU': spu, 'handle': re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:80] + '-' + spu[-4:].lower(),
        'title': title, 'category': category, 'categoryName': CATEGORIES[category],
        'thumbnail': img(images[0], 600), 'images': [img(s) for s in images[:8]],
        'description': clean_description(p.get('body_html')),
        'totalInventory': 15 + seed % 240, 'SKUList': skus,
    }


def image_ok(p):
    try:
        r = requests.get(p['thumbnail'], headers=UA, timeout=15, stream=True); r.close()
        return r.status_code == 200 and 'image' in r.headers.get('content-type', '')
    except requests.RequestException:
        return False


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--target', type=int, default=500)
    target = ap.parse_args().target
    with ThreadPoolExecutor(8) as ex:
        raw = dict(zip([s[0] for s in SOURCES], ex.map(fetch_store, [s[0] for s in SOURCES])))
    pools, seen = {}, set()
    for domain, currency, category, quota in SOURCES:
        pool = []
        for p in raw[domain]:
            prod = to_product(p, currency, category)
            key = re.sub(r'[^a-z]', '', (prod or {}).get('title', '').lower())[:40]
            if prod and key not in seen:
                seen.add(key); pool.append(prod)
        pools[domain] = (pool, quota)
        print(f'{domain}: {len(raw[domain])} raw -> {len(pool)} usable (quota {quota})')
    with ThreadPoolExecutor(24) as ex:
        for domain, (pool, quota) in pools.items():
            pools[domain] = ([p for p, ok in zip(pool, ex.map(image_ok, pool)) if ok], quota)
    # take each source's quota, then top up from sources with spare stock until target is reached
    chosen, spare = [], []
    for pool, quota in pools.values():
        chosen += pool[:quota]; spare.append(pool[quota:])
    while len(chosen) < target and any(spare):
        for s in spare:
            if s and len(chosen) < target: chosen.append(s.pop(0))
    chosen = chosen[:target]
    # interleave categories so the default listing reads as an assorted store
    by_cat = {}
    for p in chosen: by_cat.setdefault(p['category'], []).append(p)
    mixed = []
    while any(by_cat.values()):
        for c in CATEGORIES:
            if by_cat.get(c): mixed.append(by_cat[c].pop(0))
    json.dump(mixed, open(OUT, 'w'), ensure_ascii=False, indent=1)
    counts = {c: sum(p['category'] == c for p in mixed) for c in CATEGORIES}
    print(f'Wrote {len(mixed)} products to {os.path.abspath(OUT)}: {counts}')


if __name__ == '__main__':
    main()
