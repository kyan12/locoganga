#!/usr/bin/env python3
"""Pull a real, US-warehouse-stocked catalog from CJ Dropshipping into app/static/fallback_products.json.

Usage:  CJ_API_KEY=... python scripts/sync_cj_catalog.py [--target 500]
The site serves this snapshot (same schema the Winit feed used). Re-run to refresh.
"""
import argparse, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests

BASE = 'https://developers.cjdropshipping.com/api2.0/v1'
OUT = os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'fallback_products.json')
KEYWORDS = ['', 'home', 'kitchen', 'phone', 'led', 'pet', 'car', 'fitness', 'garden', 'tool',
            'bag', 'watch', 'toy', 'storage', 'lamp', 'beauty', 'camping', 'desk', 'cable', 'organizer']


def price_of(v):
    m = re.search(r'\d+(?:\.\d+)?', str(v or ''))
    return float(m.group()) if m else 0.0


def get_token(api_key):
    r = requests.post(f'{BASE}/authentication/getAccessToken', json={'apiKey': api_key}, timeout=30).json()
    if not r.get('result'):
        sys.exit(f"CJ auth failed: {r.get('code')} {r.get('message')}")
    return r['data']['accessToken']


def fetch(token, keyword, page, size=100):
    for attempt in range(4):
        r = requests.get(f'{BASE}/product/listV2', headers={'CJ-Access-Token': token}, timeout=40,
                         params={'page': page, 'size': size, 'keyWord': keyword, 'countryCode': 'US',
                                 'startWarehouseInventory': 5, 'verifiedWarehouse': 1,
                                 'startSellPrice': 4, 'endSellPrice': 120}).json()
        if r.get('result'):
            return r['data'].get('content') or []
        time.sleep(1.5 * (attempt + 1))  # CJ rate limit is ~1 qps
    return []


def to_product(p):
    sku = p.get('sku') or p.get('spu')
    price = price_of(p.get('nowPrice') or p.get('sellPrice'))
    inv = p.get('warehouseInventoryNum') or p.get('listedNum') or 0
    img = p.get('bigImage') or ''
    title = (p.get('nameEn') or '').strip()
    if not (sku and title and img.startswith('http') and price >= 4):
        return None
    return {'pid': p.get('id'), 'title': title, 'thumbnail': img.replace('http://', 'https://', 1),
            'totalInventory': int(inv) if str(inv).isdigit() else 10, 'SPU': p.get('spu') or sku,
            'category': p.get('threeCategoryName') or p.get('twoCategoryName') or '',
            'SKUList': [{'SKU': sku, 'supplyPrice': price, 'countryCode': 'US'}]}


def image_ok(p):
    try:
        r = requests.head(p['thumbnail'], timeout=8, allow_redirects=True)
        return r.status_code == 200 and 'image' in r.headers.get('content-type', '')
    except requests.RequestException:
        return False


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--target', type=int, default=500)
    target = ap.parse_args().target
    key = os.environ.get('CJ_API_KEY') or sys.exit('Set CJ_API_KEY')
    token = get_token(key)
    seen, out = set(), []
    for kw in KEYWORDS:
        for page in (1, 2):
            time.sleep(1.1)
            for group in fetch(token, kw, page):
                for raw in (group.get('productList') if isinstance(group, dict) and 'productList' in group else [group]):
                    prod = to_product(raw)
                    if prod and prod['SPU'] not in seen:
                        seen.add(prod['SPU']); out.append(prod)
        print(f'{kw or "(all)"}: {len(out)} so far')
        if len(out) >= target * 1.3:
            break
    with ThreadPoolExecutor(16) as ex:
        out = [p for p, ok in zip(out, ex.map(image_ok, out)) if ok][:target]
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(f'Wrote {len(out)} US-stocked products to {os.path.abspath(OUT)}')


if __name__ == '__main__':
    main()
