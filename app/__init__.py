import os
from flask import Flask, request, session, send_from_directory
from flask_migrate import Migrate
from flask_babel import Babel
from dotenv import load_dotenv
from app.models import db, map_national_team

load_dotenv()

def get_locale():
    lang = request.args.get('lang')
    if lang in ['en', 'it']:
        session['lang'] = lang
        return lang
    
    if 'lang' in session:
        return session['lang']
    
    return request.accept_languages.best_match(['en', 'it'])

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
    
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app.config['UPLOAD_FOLDER'] = os.path.join(basedir, os.getenv('UPLOAD_FOLDER', 'uploads'))
    
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)
    Migrate(app, db)

    from app.blueprints.public import public_bp
    from app.blueprints.admin import admin_bp
    
    app.register_blueprint(public_bp)
    
    admin_prefix = os.getenv('ADMIN_URL_PREFIX', 'admin')
    app.register_blueprint(admin_bp, url_prefix=f'/{admin_prefix}')

    from flask import send_from_directory
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.context_processor
    def inject_globals():
        return {
            'whatsapp_number': os.getenv('WHATSAPP_NUMBER'),
            'instagram_handle': os.getenv('INSTAGRAM_HANDLE'),
            'official_email': os.getenv('OFFICIAL_EMAIL')
        }

    type_labels_it = {
        'Shirt': 'Maglia',
        'Training Top': 'Maglia Allenamento',
        'Polo Shirt': 'Polo',
        'T-Shirt': 'Maglietta',
        'Sweatshirt': 'Felpa',
        'Hoodie': 'Felpa con cappuccio',
        'Jacket': 'Giacca',
        '1/4 Zip': '1/4 zip',
        'Full Zip': 'Zip',
        'Tracksuit': 'Tuta',
        'Trousers': 'Pantaloni',
        'Shorts': 'Pantaloncini',
        'Gilet': 'Gilet',
        'Vest': 'Canottiera',
        'Accessories': 'Accessori',
    }

    @app.template_filter('type_label')
    def type_label_filter(value):
        if not value:
            return ''
        if value == 'Training Shirt':
            value = 'Training Top'
        locale = str(get_locale() or 'en')
        if locale == 'it':
            return type_labels_it.get(value, value)
        return value

    @app.template_filter('type_label_or_shirt')
    def type_label_or_shirt_filter(value):
        locale = str(get_locale() or 'en')
        if value:
            return type_label_filter(value)
        return 'Maglia' if locale == 'it' else 'Shirt'

    @app.template_filter('sleeve_label')
    def sleeve_label_filter(value):
        if not value:
            return ''
        locale = str(get_locale() or 'en')
        if locale == 'it':
            return {
                'L/S': 'Maniche Lunghe',
                'S/S': 'Maniche Corte',
            }.get(value, value)
        return {
            'L/S': 'Long Sleeve',
            'S/S': 'Short Sleeve',
        }.get(value, value)

    @app.template_filter('color_label')
    def color_label_filter(value):
        if not value:
            return ''
        locale = str(get_locale() or 'en')
        if locale != 'it':
            return value
        key = value.strip().lower()
        return {
            'black': 'Nero',
            'white': 'Bianco',
            'red': 'Rosso',
            'blue': 'Blu',
            'yellow': 'Giallo',
            'green': 'Verde',
            'purple': 'Viola',
            'orange': 'Arancione',
            'grey': 'Grigio',
            'gray': 'Grigio',
            'gold': 'Oro',
            'silver': 'Argento',
            'navy': 'Blu Navy',
            'burgundy': 'Bordeaux',
        }.get(key, value)

    @app.template_filter('display_name_localized')
    def display_name_localized_filter(shirt):
        locale = str(get_locale() or 'en')
        parts = []
        team_name = getattr(shirt, 'squadra', None)
        if locale == 'it' and getattr(shirt, 'nazionale', False):
            team_name = map_national_team(team_name)

        if locale == 'it':
            parts.append(type_label_or_shirt_filter(getattr(shirt, 'type', None)))
            tipologia = getattr(shirt, 'tipologia', None)
            if tipologia:
                parts.append(tipologia)
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
            if getattr(shirt, 'maniche', None):
                parts.append(shirt.maniche)
            if team_name:
                parts.append(team_name)
            if getattr(shirt, 'brand', None):
                parts.append(shirt.brand)
            tipologia = getattr(shirt, 'tipologia', None)
            if tipologia:
                parts.append(tipologia)
            parts.append(type_label_or_shirt_filter(getattr(shirt, 'type', None)))

        if getattr(shirt, 'stagione', None):
            stagione = shirt.stagione
            parts.append(stagione)

        return ' '.join([p for p in parts if p])

    @app.template_filter('team_name_localized')
    def team_name_localized_filter(shirt):
        team_name = getattr(shirt, 'squadra', None)
        if not team_name:
            return team_name
        locale = str(get_locale() or 'en')
        if locale == 'it' and getattr(shirt, 'nazionale', False):
            return map_national_team(team_name)
        return team_name

    @app.template_filter('competition_label_localized')
    def competition_label_localized_filter(value):
        locale = str(get_locale() or 'en')
        campionato = getattr(value, 'campionato', value)
        if not campionato:
            return campionato
        key = str(campionato).strip().lower()
        is_national = getattr(value, 'nazionale', False) or key in ['nazionali', 'nazionale', 'national teams', 'national team']
        if locale == 'en' and is_national:
            return 'National Team'
        if locale == 'it' and key in ['national teams', 'national team']:
            return 'Nazionali'
        return campionato

    return app
