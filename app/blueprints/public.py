import os
from flask import Blueprint, render_template, request, redirect, url_for, Response
from flask_babel import get_locale
from app.models import Shirt, db
from app.openrouter import get_or_translate_description
from app.utils import build_shirt_slug

public_bp = Blueprint('public', __name__)
CANONICAL_BASE_URL = os.getenv('CANONICAL_BASE_URL', 'https://kitaly-official.com').rstrip('/')

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
    tipologia = request.args.get('tipologia')
    shirt_type = request.args.get('type')
    maniche = request.args.get('maniche')
    player_name = request.args.get('player_name')
    nazionale = request.args.get('nazionale')
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
    if tipologia:
        query = query.filter(Shirt.tipologia == tipologia)
    if shirt_type:
        query = query.filter(Shirt.type == shirt_type)
    if maniche:
        query = query.filter(Shirt.maniche == maniche)
    if player_name:
        query = query.filter(Shirt.player_name == player_name)
    if nazionale:
        query = query.filter(Shirt.nazionale.is_(True))

    if sort == 'newest':
        query = query.order_by(Shirt.created_at.desc())
    elif sort == 'oldest':
        query = query.order_by(Shirt.created_at.asc())

    shirts = query.all()
    
    # Get unique values for filters
    brands = db.session.query(Shirt.brand).filter(Shirt.brand.isnot(None)).distinct().all()
    campionati = db.session.query(Shirt.campionato).filter(Shirt.campionato.isnot(None)).distinct().all()
    colori = db.session.query(Shirt.colore).filter(Shirt.colore.isnot(None)).distinct().all()
    stagioni = db.session.query(Shirt.stagione).filter(Shirt.stagione.isnot(None)).distinct().all()
    squadre = db.session.query(Shirt.squadra).filter(Shirt.squadra.isnot(None)).distinct().all()
    tipologie = db.session.query(Shirt.tipologia).filter(Shirt.tipologia.isnot(None)).distinct().all()
    types = db.session.query(Shirt.type).filter(Shirt.type.isnot(None)).distinct().all()
    maniche_values = db.session.query(Shirt.maniche).filter(Shirt.maniche.isnot(None)).distinct().all()
    player_names = db.session.query(Shirt.player_name).filter(Shirt.player_name.isnot(None)).distinct().all()

    return render_template('public/catalog.html', 
                           shirts=shirts,
                           brands=sorted([b[0] for b in brands if b[0]]),
                           campionati=sorted([c[0] for c in campionati if c[0]]),
                           colori=sorted([col[0] for col in colori if col[0]]),
                           stagioni=sorted([s[0] for s in stagioni if s[0]]),
                           squadre=sorted([sq[0] for sq in squadre if sq[0]]),
                           tipologie=sorted([t[0] for t in tipologie if t[0]]),
                           types=sorted([t[0] for t in types if t[0]]),
                           maniche_values=sorted([m[0] for m in maniche_values if m[0]]),
                           player_names=sorted([p[0] for p in player_names if p[0]]))

@public_bp.route('/catalog')
def catalog_redirect():
    return redirect(url_for('public.catalog'))

@public_bp.route('/sitemap.xml')
def sitemap():
    shirts = Shirt.query.order_by(Shirt.created_at.desc()).all()
    url_root = CANONICAL_BASE_URL

    urls = [
        {
            "loc": f"{url_root}{url_for('public.catalog')}?lang=en",
            "lastmod": None,
        }
    ]
    urls.append(
        {
            "loc": f"{url_root}{url_for('public.catalog')}?lang=it",
            "lastmod": None,
        }
    )

    for shirt in shirts:
        lastmod = shirt.created_at.date().isoformat() if shirt.created_at else None
        for locale in ['en', 'it']:
            slug = build_shirt_slug(shirt, locale)
            urls.append(
                {
                    "loc": f"{url_root}{url_for('public.shirt_detail', shirt_id=shirt.id, slug=slug)}?lang={locale}",
                    "lastmod": lastmod,
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
    url_root = CANONICAL_BASE_URL
    content = f"""User-agent: *
Allow: /

Sitemap: {url_root}{url_for('public.sitemap')}
"""
    return Response(content, mimetype="text/plain")

@public_bp.route('/shirt/<int:shirt_id>')
@public_bp.route('/shirt/<int:shirt_id>-<slug>')
def shirt_detail(shirt_id, slug=None):
    shirt = Shirt.query.get_or_404(shirt_id)
    locale = str(get_locale() or 'en')
    canonical_slug = build_shirt_slug(shirt, locale)
    if slug != canonical_slug:
        return redirect(url_for('public.shirt_detail', shirt_id=shirt.id, slug=canonical_slug), code=301)

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
