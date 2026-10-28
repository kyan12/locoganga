from flask import Blueprint, render_template, current_app, request, abort
from ..services.product_service import ProductService, Catalog

bp = Blueprint('main', __name__)

SORTS = {'': 'Featured', 'price-asc': 'Price: low to high', 'price-desc': 'Price: high to low', 'name': 'Name: A to Z'}


@bp.route('/')
def index():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = current_app.config.get('PRODUCT_PAGE_SIZE', 20)
    category = request.args.get('category') or None
    q = (request.args.get('q') or '').strip()[:80]
    sort = request.args.get('sort') if request.args.get('sort') in SORTS else ''

    if current_app.config.get('WINIT_ENABLED') and not (category or q or sort):
        products, pagination = ProductService(current_app).get_products(page=page, items_per_page=per_page)
        total = None
    else:
        items = Catalog.query(category=category, q=q, sort=sort)
        total = len(items)
        products = items[(page - 1) * per_page: page * per_page]
        pagination = {'page': page, 'total_pages': max((total + per_page - 1) // per_page, 1)}

    categories = Catalog.categories()
    current = next((c for c in categories if c['slug'] == category), None)
    return render_template('main/index.html', products=products, pagination=pagination, total=total,
                           categories=categories, current_category=current, q=q, sort=sort, sorts=SORTS,
                           show_hero=not (category or q or sort) and page == 1)


@bp.route('/product/<handle>')
def product(handle):
    p = Catalog.by_handle(handle)
    if not p:
        abort(404)
    return render_template('main/product.html', product=p, related=Catalog.related(p))
