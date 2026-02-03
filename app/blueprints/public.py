from flask import Blueprint, render_template, request, redirect, url_for, Response
from flask_babel import get_locale
from app.models import Shirt, db
from app.openrouter import get_or_translate_description

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
@public_bp.route('/catalogue')
def catalog():
    query = Shirt.query.filter_by(status='active')
    
    # Filter logic
    q = request.args.get('q')
    brand = request.args.get('brand')
    squadra = request.args.get('squadra')
    campionato = request.args.get('campionato')
    colore = request.args.get('colore')
    stagione = request.args.get('stagione')
    sort = request.args.get('sort', 'newest')

    if q:
        query = query.filter(
            (Shirt.squadra.ilike(f'%{q}%')) | 
            (Shirt.brand.ilike(f'%{q}%')) | 
            (Shirt.campionato.ilike(f'%{q}%')) |
            (Shirt.descrizione.ilike(f'%{q}%'))
        )
    if brand:
        query = query.filter(Shirt.brand == brand)
    if squadra:
        query = query.filter(Shirt.squadra.ilike(f'%{squadra}%'))
    if campionato:
        query = query.filter(Shirt.campionato == campionato)
    if colore:
        query = query.filter(Shirt.colore == colore)
    if stagione:
        query = query.filter(Shirt.stagione == stagione)

    if sort == 'newest':
        query = query.order_by(Shirt.created_at.desc())
    elif sort == 'oldest':
        query = query.order_by(Shirt.created_at.asc())

    shirts = query.all()
    
    # Get unique values for filters
    brands = db.session.query(Shirt.brand).distinct().all()
    campionati = db.session.query(Shirt.campionato).distinct().all()
    colori = db.session.query(Shirt.colore).distinct().all()
    stagioni = db.session.query(Shirt.stagione).distinct().all()

    return render_template('public/catalog.html', 
                           shirts=shirts,
                           brands=[b[0] for b in brands],
                           campionati=[c[0] for c in campionati],
                           colori=[col[0] for col in colori],
                           stagioni=[s[0] for s in stagioni])

@public_bp.route('/catalog')
def catalog_redirect():
    return redirect(url_for('public.catalog'))

@public_bp.route('/sitemap.xml')
def sitemap():
    shirts = Shirt.query.order_by(Shirt.created_at.desc()).all()
    url_root = request.url_root.rstrip('/')

    urls = [
        {
            "loc": f"{url_root}{url_for('public.catalog')}",
            "lastmod": None,
        }
    ]

    for shirt in shirts:
        urls.append(
            {
                "loc": f"{url_root}{url_for('public.shirt_detail', shirt_id=shirt.id, slug=shirt.slug)}",
                "lastmod": shirt.created_at.date().isoformat() if shirt.created_at else None,
            }
        )

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for entry in urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{entry['loc']}</loc>")
        if entry["lastmod"]:
            xml_lines.append(f"    <lastmod>{entry['lastmod']}</lastmod>")
        xml_lines.append("  </url>")
    xml_lines.append("</urlset>")

    return Response("\n".join(xml_lines), mimetype="application/xml")

@public_bp.route('/robots.txt')
def robots():
    url_root = request.url_root.rstrip('/')
    content = f"""User-agent: *
Allow: /

Sitemap: {url_root}{url_for('public.sitemap')}
"""
    return Response(content, mimetype="text/plain")

@public_bp.route('/shirt/<int:shirt_id>')
@public_bp.route('/shirt/<int:shirt_id>-<slug>')
def shirt_detail(shirt_id, slug=None):
    shirt = Shirt.query.get_or_404(shirt_id)
    canonical_slug = shirt.slug
    if slug != canonical_slug:
        return redirect(url_for('public.shirt_detail', shirt_id=shirt.id, slug=canonical_slug), code=301)

    locale = str(get_locale() or 'en')
    if locale == 'it':
        display_description = get_or_translate_description(shirt)
    else:
        display_description = shirt.descrizione

    return render_template(
        'public/shirt.html',
        shirt=shirt,
        display_description=display_description
    )

# Security Honeypots - Redirect common admin guesses to the catalog
@public_bp.route('/admin')
@public_bp.route('/login')
@public_bp.route('/wp-admin')
@public_bp.route('/administrator')
@public_bp.route('/manager')
def honeypot():
    return redirect(url_for('public.catalog'))
