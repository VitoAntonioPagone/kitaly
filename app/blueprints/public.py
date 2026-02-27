import os
import random
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, Response, current_app
from flask_babel import get_locale
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from app.models import Shirt
from app.openrouter import get_or_translate_description
from app.utils import build_shirt_slug, size_sort_key, team_name_localized_value

public_bp = Blueprint('public', __name__)
CANONICAL_BASE_URL = os.getenv('CANONICAL_BASE_URL', 'https://kitaly-official.com').rstrip('/')
EXCLUDED_LEAGUES = {"mls", "saudi pro league", "champions league", "europa league"}


def resolve_product_code_or_fallback(shirt):
    if getattr(shirt, 'product_code', None):
        return str(shirt.product_code)
    fallback = str(uuid.uuid5(uuid.NAMESPACE_URL, f"kitaly-shirt:{shirt.id}"))
    current_app.logger.error(
        "Missing product_code for shirt_id=%s. Falling back to UUID=%s",
        shirt.id,
        fallback,
    )
    return fallback

def normalize_sleeve_group(value):
    if not value:
        return None
    key = str(value).strip().lower()
    if key in {'l/s', 'ls', 'long sleeve', 'long sleeves', 'long-sleeve', 'long-sleeves', 'maniche lunghe'}:
        return 'long'
    if key in {'s/s', 'ss', 'short sleeve', 'short sleeves', 'short-sleeve', 'short-sleeves', 'maniche corte'}:
        return 'short'
    if 'lunghe' in key or 'long' in key:
        return 'long'
    if 'corte' in key or 'short' in key:
        return 'short'
    return None

@public_bp.route('/')
@public_bp.route('/catalogue')
def catalog():
    locale = str(get_locale() or 'en')
    query = Shirt.query.options(selectinload(Shirt.images)).filter_by(status='active')
    active_scope = Shirt.query.filter_by(status='active')

    def get_multi_arg(name):
        values = [v.strip() for v in request.args.getlist(name) if v and v.strip()]
        if values:
            return values
        fallback = request.args.get(name)
        if fallback and fallback.strip():
            return [fallback.strip()]
        return []

    # Filter logic
    q = (request.args.get('q') or '').strip()
    brands = get_multi_arg('brand')
    squadre = get_multi_arg('squadra')
    campionati = get_multi_arg('campionato')
    colori = get_multi_arg('colore')
    stagioni = get_multi_arg('stagione')
    tipologie = get_multi_arg('tipologia')
    shirt_types = get_multi_arg('type')
    maniche_values = get_multi_arg('maniche')
    taglie = get_multi_arg('taglia')
    player_names = get_multi_arg('player_name')
    sort = request.args.get('sort')
    if sort not in {'newest', 'oldest', 'random'}:
        sort = 'random'
    seed = request.args.get('seed', type=int)
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = 24

    if q:
        conditions = [
            Shirt.squadra.ilike(f'%{q}%'),
            Shirt.brand.ilike(f'%{q}%'),
            Shirt.campionato.ilike(f'%{q}%'),
            Shirt.descrizione.ilike(f'%{q}%'),
        ]
        if q.isdigit():
            conditions.append(Shirt.product_code == int(q))
        query = query.filter(or_(*conditions))
    if brands:
        query = query.filter(Shirt.brand.in_(brands))
    if squadre:
        query = query.filter(or_(*[Shirt.squadra.ilike(f'%{sq}%') for sq in squadre]))
    if campionati:
        query = query.filter(Shirt.campionato.in_(campionati))
    if colori:
        query = query.filter(Shirt.colore.in_(colori))
    if stagioni:
        query = query.filter(Shirt.stagione.in_(stagioni))
    if tipologie:
        query = query.filter(Shirt.tipologia.in_(tipologie))
    if shirt_types:
        query = query.filter(Shirt.type.in_(shirt_types))
    if taglie:
        query = query.filter(Shirt.taglia.in_(taglie))
    if maniche_values:
        sleeve_clauses = []
        for maniche in maniche_values:
            sleeve_group = normalize_sleeve_group(maniche)
            if sleeve_group == 'long':
                sleeve_clauses.append(or_(
                    Shirt.maniche.ilike('%L/S%'),
                    Shirt.maniche.ilike('%Long%'),
                    Shirt.maniche.ilike('%lunghe%'),
                ))
            elif sleeve_group == 'short':
                sleeve_clauses.append(or_(
                    Shirt.maniche.ilike('%S/S%'),
                    Shirt.maniche.ilike('%Short%'),
                    Shirt.maniche.ilike('%corte%'),
                ))
            else:
                sleeve_clauses.append(Shirt.maniche == maniche)
        query = query.filter(or_(*sleeve_clauses))
    if player_names:
        query = query.filter(Shirt.player_name.in_(player_names))
    if request.args.get('player_issued'):
        query = query.filter(Shirt.player_issued.is_(True))
    if request.args.get('nazionale'):
        query = query.filter(Shirt.nazionale.is_(True))

    if sort == 'newest':
        query = query.order_by(Shirt.created_at.desc())
    elif sort == 'oldest':
        query = query.order_by(Shirt.created_at.asc())
    elif sort == 'random':
        if seed is None:
            seed = random.randint(1, 2_147_483_646)
        random_rank = ((Shirt.id * 1103515245) + seed) % 2147483647
        query = query.order_by(random_rank.asc(), Shirt.id.asc())
    else:
        query = query.order_by(Shirt.created_at.desc())

    shirts = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get unique values for filters
    filter_brands = active_scope.with_entities(Shirt.brand).filter(Shirt.brand.isnot(None)).distinct().all()
    filter_campionati = active_scope.with_entities(Shirt.campionato).filter(Shirt.campionato.isnot(None)).distinct().all()
    filter_colori = active_scope.with_entities(Shirt.colore).filter(Shirt.colore.isnot(None)).distinct().all()
    filter_stagioni = active_scope.with_entities(Shirt.stagione).filter(Shirt.stagione.isnot(None)).distinct().all()
    filter_squadre = active_scope.with_entities(Shirt.squadra).filter(Shirt.squadra.isnot(None)).distinct().all()
    filter_tipologie = active_scope.with_entities(Shirt.tipologia).filter(Shirt.tipologia.isnot(None)).distinct().all()
    filter_types = active_scope.with_entities(Shirt.type).filter(Shirt.type.isnot(None)).distinct().all()
    filter_maniche = active_scope.with_entities(Shirt.maniche).filter(Shirt.maniche.isnot(None)).distinct().all()
    filter_player_names = active_scope.with_entities(Shirt.player_name).filter(Shirt.player_name.isnot(None)).distinct().all()
    filter_taglie = active_scope.with_entities(Shirt.taglia).filter(Shirt.taglia.isnot(None)).distinct().all()

    base_args = request.args.to_dict(flat=False)
    if sort == 'random' and seed is not None:
        base_args['seed'] = [str(seed)]
    else:
        base_args.pop('seed', None)

    def catalog_url_for(**changes):
        args = {key: list(values) for key, values in base_args.items()}
        for key, value in changes.items():
            if value is None:
                args.pop(key, None)
            elif isinstance(value, list):
                args[key] = [str(v) for v in value if v is not None and str(v).strip()]
            else:
                args[key] = [str(value)]
        return url_for('public.catalog', **args)

    raw_squadre = sorted([sq[0] for sq in filter_squadre if sq[0]])
    squadre = [{'value': sq, 'label': team_name_localized_value(sq, locale)} for sq in raw_squadre]

    return render_template('public/catalog.html', 
                           shirts=shirts,
                           brands=sorted([b[0] for b in filter_brands if b[0]]),
                           campionati=sorted([
                               c[0] for c in filter_campionati
                               if c[0] and str(c[0]).strip().lower() not in EXCLUDED_LEAGUES
                           ]),
                           colori=sorted([col[0] for col in filter_colori if col[0]]),
                           stagioni=sorted([s[0] for s in filter_stagioni if s[0]]),
                           squadre=squadre,
                           tipologie=sorted([t[0] for t in filter_tipologie if t[0]]),
                           types=sorted([t[0] for t in filter_types if t[0]]),
                           maniche_values=sorted([m[0] for m in filter_maniche if m[0]]),
                           player_names=sorted([p[0] for p in filter_player_names if p[0]]),
                           taglie=sorted([t[0] for t in filter_taglie if t[0]], key=size_sort_key),
                           shuffle_seed=seed,
                           catalog_url_for=catalog_url_for)

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

    product_code = resolve_product_code_or_fallback(shirt)
    display_name = shirt.display_name or f"Product {shirt.id}"
    product_url = url_for('public.shirt_detail', shirt_id=shirt.id, slug=canonical_slug, lang=locale, _external=True)
    size_label = shirt.taglia or 'N/A'

    whatsapp_it = f"Ciao! Vorrei info su: {display_name} (Cod. {product_code}). Link: {product_url}"
    whatsapp_en = f"Hi! I'd like info about: {display_name} (Code {product_code}). Link: {product_url}"

    email_subject = f"Info request - Cod. {product_code} - {display_name}"
    email_body_it = (
        "Ciao,\n\n"
        "Vorrei informazioni su questo articolo.\n\n"
        f"Nome prodotto: {display_name}\n"
        f"Codice prodotto: Cod. {product_code}\n"
        f"Link prodotto: {product_url}\n"
        f"Taglia selezionata: {size_label}\n\n"
        "Messaggio cliente: [Scrivi qui il tuo messaggio]\n"
    )
    email_body_en = (
        "Hi,\n\n"
        "I'd like information about this item.\n\n"
        f"Product name: {display_name}\n"
        f"Product code: Cod. {product_code}\n"
        f"Product URL: {product_url}\n"
        f"Selected size: {size_label}\n\n"
        "Customer message: [Write your message here]\n"
    )

    return render_template(
        'public/shirt.html',
        shirt=shirt,
        display_description=display_description,
        whatsapp_message=(whatsapp_it if locale == 'it' else whatsapp_en),
        email_subject=email_subject,
        email_body=(email_body_it if locale == 'it' else email_body_en),
    )

# Security Honeypots - Redirect common admin guesses to the catalog
@public_bp.route('/admin')
@public_bp.route('/login')
@public_bp.route('/wp-admin')
@public_bp.route('/administrator')
@public_bp.route('/manager')
def honeypot():
    return redirect(url_for('public.catalog'))
