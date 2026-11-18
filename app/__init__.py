import os
from urllib.parse import urlparse
from flask import Flask, request, session, send_from_directory
from flask_migrate import Migrate
from flask_babel import Babel, format_currency
from dotenv import load_dotenv
from sqlalchemy.orm import selectinload
from app.models import db, Shirt, StorePage
from app.utils import (
    build_shirt_slug,
    color_label,
    competition_label_localized,
    feature_label,
    sleeve_label,
    team_name_localized,
    type_label,
    type_label_or_shirt,
)

load_dotenv()

DEFAULT_WHATSAPP_NUMBER = '447756919137'


def whatsapp_number_for_url(value=None):
    raw = value if value is not None else DEFAULT_WHATSAPP_NUMBER
    digits = ''.join(ch for ch in str(raw) if ch.isdigit())
    return digits or DEFAULT_WHATSAPP_NUMBER


def instagram_handle_for_url(value=None):
    if not value:
        return None

    raw = str(value).strip()
    if '://' in raw:
        parsed = urlparse(raw)
        raw = parsed.path

    handle = raw.strip().strip('/').lstrip('@')
    return handle or None

def get_locale():
    if request.endpoint and request.endpoint.startswith('admin.'):
        return 'en'

    if request.cookies.get('appearance_preferences') != 'v1:on':
        session.pop('lang', None)
    lang = request.args.get('lang')
    if lang in ['en', 'it']:
        if request.cookies.get('appearance_preferences') == 'v1:on':
            session['lang'] = lang
        return lang
    
    if session.get('lang') in ['en', 'it']:
        return session['lang']
    
    return 'en'

def create_app():
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = '../translations'
    
    babel = Babel(app, locale_selector=get_locale)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config.update(
        STRIPE_ENABLED=os.getenv('STRIPE_ENABLED', '').lower() == 'true',
        STRIPE_SECRET_KEY=os.getenv('STRIPE_SECRET_KEY', ''),
        STRIPE_WEBHOOK_SECRET=os.getenv('STRIPE_WEBHOOK_SECRET', ''),
        PUBLIC_BASE_URL=os.getenv('PUBLIC_BASE_URL', os.getenv('CANONICAL_BASE_URL', 'https://kitaly-official.com')),
        STRIPE_SHIPPING_COUNTRIES=os.getenv('STRIPE_SHIPPING_COUNTRIES', ''),
        STRIPE_SHIPPING_RATES=os.getenv('STRIPE_SHIPPING_RATES', '{}'),
        ROYAL_MAIL_CHECKOUT=os.getenv('ROYAL_MAIL_CHECKOUT', 'true').lower() == 'true',
        SHIPPING_PACKAGING_GRAMS=os.getenv('SHIPPING_PACKAGING_GRAMS', ''),
    )
    
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app.config['UPLOAD_FOLDER'] = os.path.join(basedir, os.getenv('UPLOAD_FOLDER', 'uploads'))
    
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)
    app.config.update({name: os.getenv(name, '') for name in (
        'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_FROM',
        'SMTP_OAUTH_CLIENT_ID', 'SMTP_OAUTH_CLIENT_SECRET', 'SMTP_OAUTH_TOKEN_FILE')})
    app.config['SMTP_OAUTH_TENANT'] = os.getenv('SMTP_OAUTH_TENANT', 'consumers')
    Migrate(app, db)

    from app.blueprints.public import public_bp
    from app.blueprints.admin import admin_bp
    
    app.register_blueprint(public_bp)
    from app.payments import payments_bp, register_payment_commands
    app.register_blueprint(payments_bp)
    register_payment_commands(app)
    
    admin_prefix = os.getenv('ADMIN_URL_PREFIX', 'admin')
    app.register_blueprint(admin_bp, url_prefix=f'/{admin_prefix}')

    from flask import send_from_directory
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/media/<variant>/<path:filename>')
    def product_image(variant, filename):
        from flask import abort, send_file
        from app.image_utils import (IMAGE_VARIANTS, product_image_preview,
                                     product_image_source, product_image_version)
        if variant not in IMAGE_VARIANTS:
            abort(404)
        try:
            source = product_image_source(app.config['UPLOAD_FOLDER'], filename)
        except (ValueError, FileNotFoundError):
            abort(404)
        try:
            preview = product_image_preview(app.config['UPLOAD_FOLDER'], filename, variant)
        except (OSError, ValueError):
            app.logger.exception('Could not create product preview')
            return send_file(source, conditional=True)
        version_matches = request.args.get('v') == product_image_version(source)
        response = send_file(preview, mimetype='image/webp', conditional=True,
                             max_age=31536000 if version_matches else 3600)
        if version_matches:
            response.cache_control.immutable = True
        return response

    @app.template_filter('product_image_url')
    def product_image_url(filename, variant='card'):
        from flask import url_for
        from app.image_utils import product_image_source, product_image_version
        try:
            source = product_image_source(app.config['UPLOAD_FOLDER'], filename)
            version = product_image_version(source)
        except (ValueError, FileNotFoundError):
            return url_for('uploaded_file', filename=filename)
        return url_for('product_image', variant=variant, filename=filename, v=version)

    @app.context_processor
    def inject_globals():
        def language_url(lang):
            from flask import url_for
            args = request.args.to_dict(flat=False)
            args['lang'] = lang
            return url_for(request.endpoint, **(request.view_args or {}), **args)
        import secrets
        if request.endpoint and request.endpoint.startswith('public.') and 'preferences_csrf' not in session:
            session['preferences_csrf'] = secrets.token_urlsafe(32)
        player_issue_shirts = []
        if not (request.endpoint and request.endpoint.startswith('admin.')):
            candidates = (
                Shirt.query.options(selectinload(Shirt.images))
                .filter_by(status='active', player_issued=True)
                .all()
            )
            unsold_with_cover = [shirt for shirt in candidates if not shirt.sold and shirt.cover_image]
            pool = unsold_with_cover or [shirt for shirt in candidates if shirt.cover_image]
            player_issue_shirts = [
                {
                    'src': product_image_url(shirt.cover_image.file_path, variant='card'),
                    'alt': display_name_localized_filter(shirt),
                }
                for shirt in pool
            ]
        return {
            'language_url': language_url,
            'footer_pages': StorePage.query.filter_by(published=True).order_by(StorePage.position, StorePage.id).all(),
            'navigation_player_issue_shirts': player_issue_shirts,
            'whatsapp_number': whatsapp_number_for_url(os.getenv('WHATSAPP_NUMBER') or DEFAULT_WHATSAPP_NUMBER),
            'instagram_handle': instagram_handle_for_url(os.getenv('INSTAGRAM_HANDLE')),
            'official_email': os.getenv('OFFICIAL_EMAIL')
        }

    app.add_template_filter(format_currency, 'money_in_currency')

    @app.template_filter('storefront_price')
    def storefront_price_filter(amount, currency):
        return format_currency(amount, 'EUR' if get_locale() == 'it' else currency)

    @app.template_filter('public_price')
    def public_price_filter(shirt):
        if shirt.public_price is None:
            return 'Prezzo su richiesta' if get_locale() == 'it' else 'Price on request'
        if app.config['ROYAL_MAIL_CHECKOUT'] and app.config['STRIPE_ENABLED'] and shirt.price_currency == 'GBP':
            return format_currency(shirt.public_price, 'GBP')
        return storefront_price_filter(shirt.public_price, shirt.price_currency or 'EUR')

    @app.template_filter('type_label')
    def type_label_filter(value):
        locale = str(get_locale() or 'en')
        return type_label(value, locale)

    @app.template_filter('type_label_or_shirt')
    def type_label_or_shirt_filter(value):
        locale = str(get_locale() or 'en')
        return type_label_or_shirt(value, locale)

    @app.template_filter('sleeve_label')
    def sleeve_label_filter(value):
        locale = str(get_locale() or 'en')
        return sleeve_label(value, locale)

    @app.template_filter('color_label')
    def color_label_filter(value):
        locale = str(get_locale() or 'en')
        return color_label(value, locale)

    @app.template_filter('feature_label')
    def feature_label_filter(value):
        locale = str(get_locale() or 'en')
        return feature_label(value, locale)

    @app.template_filter('display_name_localized')
    def display_name_localized_filter(shirt):
        locale = str(get_locale() or 'en')
        parts = []
        team_name = team_name_localized(shirt, locale)

        if locale == 'it':
            parts.append(type_label_or_shirt(getattr(shirt, 'type', None), locale))
            tipologia = getattr(shirt, 'tipologia', None)
            if tipologia:
                parts.append(feature_label(tipologia, locale))
            if getattr(shirt, 'player_name', None):
                parts.append(shirt.player_name)
            # Sleeve type stays a filter-only attribute; omit from Italian display titles.
            if getattr(shirt, 'brand', None):
                parts.append(shirt.brand)
            if team_name:
                parts.append(team_name)
        else:
            if getattr(shirt, 'player_name', None):
                parts.append(shirt.player_name)
            if team_name:
                parts.append(team_name)
            if getattr(shirt, 'brand', None):
                parts.append(shirt.brand)
            tipologia = getattr(shirt, 'tipologia', None)
            if tipologia:
                parts.append(feature_label(tipologia, locale))
            parts.append(type_label_or_shirt(getattr(shirt, 'type', None), locale))

        if getattr(shirt, 'stagione', None):
            stagione = shirt.stagione
            parts.append(stagione)

        return ' '.join([p for p in parts if p])

    @app.template_filter('team_name_localized')
    def team_name_localized_filter(shirt):
        locale = str(get_locale() or 'en')
        return team_name_localized(shirt, locale)

    @app.template_filter('competition_label_localized')
    def competition_label_localized_filter(value):
        locale = str(get_locale() or 'en')
        return competition_label_localized(value, locale)

    @app.template_filter('shirt_slug_localized')
    def shirt_slug_localized_filter(shirt):
        locale = str(get_locale() or 'en')
        return build_shirt_slug(shirt, locale)

    return app
