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

    return app
