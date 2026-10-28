from datetime import date
from flask import Blueprint, render_template, Response, url_for, current_app

bp = Blueprint('pages', __name__)


@bp.route('/about')
def about():
    return render_template('pages/about.html')


@bp.route('/contact')
def contact():
    return render_template('pages/contact.html')


@bp.route('/shipping')
def shipping():
    return render_template('pages/shipping.html')


@bp.route('/returns')
def returns():
    return render_template('pages/returns.html')


@bp.route('/privacy')
def privacy():
    return render_template('pages/privacy.html')


@bp.route('/terms')
def terms():
    return render_template('pages/terms.html')


@bp.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('favicon.svg'), 200, {'Content-Type': 'image/svg+xml'}


@bp.route('/robots.txt')
def robots():
    body = "User-agent: *\nAllow: /\nDisallow: /cart\nDisallow: /checkout\n\nSitemap: {}\n".format(
        url_for('pages.sitemap', _external=True))
    return Response(body, mimetype='text/plain')


@bp.route('/sitemap.xml')
def sitemap():
    urls = [url_for(e, _external=True) for e in (
        'main.index', 'pages.about', 'pages.contact', 'pages.shipping',
        'pages.returns', 'pages.privacy', 'pages.terms')]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += ''.join('  <url><loc>{}</loc></url>\n'.format(u) for u in urls) + '</urlset>\n'
    return Response(xml, mimetype='application/xml')
