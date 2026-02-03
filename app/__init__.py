import os
from flask import Flask, request, session, send_from_directory
from flask_migrate import Migrate
from flask_babel import Babel
from dotenv import load_dotenv
from app.models import db

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
        'Training Shirt': 'Maglia allenamento',
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

    @app.template_filter('display_name_localized')
    def display_name_localized_filter(shirt):
        locale = str(get_locale() or 'en')
        parts = []

        if locale == 'it':
            parts.append(type_label_or_shirt_filter(getattr(shirt, 'type', None)))
            if getattr(shirt, 'player_name', None):
                parts.append(shirt.player_name)
            if getattr(shirt, 'brand', None):
                parts.append(shirt.brand)
            if getattr(shirt, 'squadra', None):
                parts.append(shirt.squadra)
        else:
            if getattr(shirt, 'player_name', None):
                parts.append(shirt.player_name)
            if getattr(shirt, 'maniche', None):
                parts.append(shirt.maniche)
            if getattr(shirt, 'squadra', None):
                parts.append(shirt.squadra)
            tipologia = getattr(shirt, 'tipologia', None)
            if tipologia:
                parts.append(tipologia)
            parts.append(type_label_or_shirt_filter(getattr(shirt, 'type', None)))

        if locale == 'it':
            tipologia = getattr(shirt, 'tipologia', None)
            if tipologia:
                parts.append(tipologia)
            if getattr(shirt, 'maniche', None):
                parts.append(shirt.maniche)

        if getattr(shirt, 'stagione', None):
            stagione = shirt.stagione + ('*' if getattr(shirt, 'player_issued', False) else '')
            parts.append(stagione)

        return ' '.join([p for p in parts if p])

    return app
