import os
import uuid
import shutil
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from app.models import db, Shirt, ShirtImage, NATIONAL_TEAMS
from app.auth import login_required
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin', __name__)

DEFAULT_BRANDS = ["Nike", "Adidas", "Puma", "Kappa", "Macron", "Joma", "Umbro", "New Balance", "Mizuno", "Castore", "Lotto", "Diadora"]
DEFAULT_LEAGUES = ["Serie A", "Premier League", "La Liga", "Bundesliga", "Ligue 1", "Eredivisie", "Primeira Liga", "MLS", "Saudi Pro League", "Champions League", "Europa League", "Nazionali"]
DEFAULT_COLORS = ["Black", "White", "Red", "Blue", "Yellow", "Green", "Purple", "Orange", "Grey", "Gold", "Silver", "Navy", "Burgundy"]

from werkzeug.security import check_password_hash

def get_shirt_dir(shirt):
    return os.path.join(
        secure_filename(shirt.campionato),
        secure_filename(shirt.brand),
        secure_filename(shirt.squadra),
        f"{shirt.id}_{secure_filename(shirt.taglia)}"
    )

def get_next_image_index(folder_path):
    if not os.path.exists(folder_path):
        return 1
    indices = []
    for f in os.listdir(folder_path):
        name = os.path.splitext(f)[0]
        if name.isdigit():
            indices.append(int(name))
    return max(indices) + 1 if indices else 1

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        admin_password_hash = os.getenv('ADMIN_PASSWORD_HASH')
        
        if admin_password_hash and check_password_hash(admin_password_hash, password):
            session['logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        flash('Invalid password', 'error')
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('public.catalog'))

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    query = Shirt.query

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

    brands = db.session.query(Shirt.brand).distinct().all()
    campionati = db.session.query(Shirt.campionato).distinct().all()
    colori = db.session.query(Shirt.colore).distinct().all()
    stagioni = db.session.query(Shirt.stagione).distinct().all()
    squadre = db.session.query(Shirt.squadra).distinct().all()

    return render_template(
        'admin/dashboard.html',
        shirts=shirts,
        brands=[b[0] for b in brands],
        campionati=[c[0] for c in campionati],
        colori=[col[0] for col in colori],
        stagioni=[s[0] for s in stagioni],
        squadre=[sq[0] for sq in squadre],
        national_teams=NATIONAL_TEAMS,
    )

@admin_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_shirt():
    if request.method == 'POST':
        try:
            brand = request.form.get('brand')
            squadra = request.form.get('squadra')
            campionato = request.form.get('campionato')
            taglia = request.form.get('taglia')
            
            shirt = Shirt(
                player_name=request.form.get('player_name') or None,
                brand=brand,
                squadra=squadra,
                campionato=campionato,
                taglia=taglia,
                colore=request.form.get('colore'),
                stagione=request.form.get('stagione'),
                tipologia=request.form.get('tipologia') or None,
                type=request.form.get('type'),
                maniche=request.form.get('maniche') or None,
                player_issued=bool(request.form.get('player_issued')),
                nazionale=bool(request.form.get('nazionale')),
                prezzo_pagato=float(request.form.get('prezzo_pagato')) if request.form.get('prezzo_pagato') else None,
                descrizione=request.form.get('descrizione'),
                status=request.form.get('status', 'active')
            )
            db.session.add(shirt)
            db.session.commit()

            files = request.files.getlist('images')
            cover_index = int(request.form.get('cover_index', 0))
            
            relative_dir = get_shirt_dir(shirt)
            absolute_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], relative_dir)
            if not os.path.exists(absolute_dir):
                os.makedirs(absolute_dir)

            for i, file in enumerate(files):
                if file and file.filename != '':
                    ext = os.path.splitext(file.filename)[1].lower()
                    unique_filename = f"{i + 1}{ext}"
                    file.save(os.path.join(absolute_dir, unique_filename))
                    
                    db_path = os.path.join(relative_dir, unique_filename)
                    
                    is_cover = (i == cover_index)
                    img = ShirtImage(shirt_id=shirt.id, file_path=db_path, is_cover=is_cover)
                    db.session.add(img)
            
            db.session.commit()
            flash('Shirt created successfully', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating shirt: {str(e)}', 'error')

    return render_template('admin/shirt_form.html', 
                           shirt=None, 
                           brands=DEFAULT_BRANDS, 
                           leagues=DEFAULT_LEAGUES, 
                           colors=DEFAULT_COLORS,
                           national_teams=NATIONAL_TEAMS)

@admin_bp.route('/edit/<int:shirt_id>', methods=['GET', 'POST'])
@login_required
def edit_shirt(shirt_id):
    shirt = Shirt.query.get_or_404(shirt_id)
    old_relative_dir = get_shirt_dir(shirt)
    old_descrizione = shirt.descrizione
    
    if request.method == 'POST':
        try:
            shirt.player_name = request.form.get('player_name') or None
            shirt.brand = request.form.get('brand')
            shirt.squadra = request.form.get('squadra')
            shirt.campionato = request.form.get('campionato')
            shirt.taglia = request.form.get('taglia')
            shirt.colore = request.form.get('colore')
            shirt.stagione = request.form.get('stagione')
            shirt.tipologia = request.form.get('tipologia') or None
            shirt.type = request.form.get('type') or None
            shirt.maniche = request.form.get('maniche') or None
            shirt.player_issued = bool(request.form.get('player_issued'))
            shirt.nazionale = bool(request.form.get('nazionale'))
            shirt.prezzo_pagato = float(request.form.get('prezzo_pagato')) if request.form.get('prezzo_pagato') else None
            new_descrizione = request.form.get('descrizione')
            new_descrizione_ita = request.form.get('descrizione_ita')
            shirt.descrizione = new_descrizione
            shirt.descrizione_ita = new_descrizione_ita
            shirt.status = request.form.get('status', 'active')

            if new_descrizione != old_descrizione and not new_descrizione_ita:
                shirt.descrizione_ita = None
            
            db.session.commit()
            
            new_relative_dir = get_shirt_dir(shirt)
            if old_relative_dir != new_relative_dir:
                old_absolute = os.path.join(current_app.config['UPLOAD_FOLDER'], old_relative_dir)
                new_absolute = os.path.join(current_app.config['UPLOAD_FOLDER'], new_relative_dir)
                
                if os.path.exists(old_absolute):
                    os.makedirs(os.path.dirname(new_absolute), exist_ok=True)
                    shutil.move(old_absolute, new_absolute)
                    
                    try:
                        os.removedirs(os.path.dirname(old_absolute))
                    except OSError:
                        pass
                    
                    for img in shirt.images:
                        filename = os.path.basename(img.file_path)
                        img.file_path = os.path.join(new_relative_dir, filename)
                    db.session.commit()
            
            files = request.files.getlist('images')
            if files and files[0].filename != '':
                relative_dir = get_shirt_dir(shirt)
                absolute_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], relative_dir)
                if not os.path.exists(absolute_dir):
                    os.makedirs(absolute_dir)

                next_num = get_next_image_index(absolute_dir)

                for i, file in enumerate(files):
                    if file and file.filename != '':
                        ext = os.path.splitext(file.filename)[1].lower()
                        unique_filename = f"{next_num + i}{ext}"
                        file.save(os.path.join(absolute_dir, unique_filename))
                        
                        db_path = os.path.join(relative_dir, unique_filename)
                        img = ShirtImage(shirt_id=shirt.id, file_path=db_path, is_cover=False)
                        db.session.add(img)
                db.session.commit()

            flash('Shirt updated successfully', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating shirt: {str(e)}', 'error')

    return render_template('admin/shirt_form.html', 
                           shirt=shirt, 
                           brands=DEFAULT_BRANDS, 
                           leagues=DEFAULT_LEAGUES, 
                           colors=DEFAULT_COLORS,
                           national_teams=NATIONAL_TEAMS)

@admin_bp.route('/delete/<int:shirt_id>', methods=['POST'])
@login_required
def delete_shirt(shirt_id):
    shirt = Shirt.query.get_or_404(shirt_id)
    try:
        if shirt.images:
            # All images for a shirt are in the same folder
            first_img_path = shirt.images[0].file_path
            folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.dirname(first_img_path))
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                try:
                    os.removedirs(os.path.dirname(folder_path))
                except OSError:
                    pass
        
        db.session.delete(shirt)
        db.session.commit()
        flash('Shirt deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting shirt: {str(e)}', 'error')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_image/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    img = ShirtImage.query.get_or_404(image_id)
    shirt_id = img.shirt_id
    try:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], img.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        db.session.delete(img)
        db.session.commit()
        flash('Image deleted', 'success')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"ok": True})
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting image: {str(e)}', 'error')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"ok": False, "error": str(e)}), 500
    
    return redirect(url_for('admin.edit_shirt', shirt_id=shirt_id))
