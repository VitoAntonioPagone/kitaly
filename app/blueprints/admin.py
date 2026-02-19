import os
import uuid
import shutil
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from sqlalchemy import func
from app.models import db, Shirt, ShirtImage, NATIONAL_TEAMS
from app.openrouter import get_or_translate_description
from app.auth import login_required
from app.utils import season_sort_key
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
    shirt_type = request.args.get('type')
    sort = request.args.get('sort', 'chronological')

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
    if shirt_type:
        query = query.filter(Shirt.type == shirt_type)

    if sort == 'newest':
        shirts = query.order_by(Shirt.created_at.desc()).all()
    elif sort in {'oldest', 'chronological'}:
        shirts = sorted(
            query.all(),
            key=lambda shirt: (season_sort_key(shirt.stagione), shirt.created_at or datetime.min),
        )
    elif sort == 'reverse_chronological':
        shirts = sorted(
            query.all(),
            key=lambda shirt: (season_sort_key(shirt.stagione), shirt.created_at or datetime.min),
            reverse=True,
        )
    else:
        shirts = sorted(
            query.all(),
            key=lambda shirt: (season_sort_key(shirt.stagione), shirt.created_at or datetime.min),
        )

    brand_counts = dict(
        db.session.query(Shirt.brand, func.count(Shirt.id))
        .filter(Shirt.brand.isnot(None), Shirt.brand != '')
        .group_by(Shirt.brand)
        .all()
    )
    league_counts = dict(
        db.session.query(Shirt.campionato, func.count(Shirt.id))
        .filter(Shirt.campionato.isnot(None), Shirt.campionato != '')
        .group_by(Shirt.campionato)
        .all()
    )
    color_counts = dict(
        db.session.query(Shirt.colore, func.count(Shirt.id))
        .filter(Shirt.colore.isnot(None), Shirt.colore != '')
        .group_by(Shirt.colore)
        .all()
    )
    types = db.session.query(Shirt.type).filter(
        Shirt.type.isnot(None),
        Shirt.type != '',
        func.lower(Shirt.type) != 'none',
    ).distinct().all()

    season_counts = dict(
        db.session.query(Shirt.stagione, func.count(Shirt.id))
        .filter(Shirt.stagione.isnot(None), Shirt.stagione != '')
        .group_by(Shirt.stagione)
        .all()
    )
    type_counts = dict(
        db.session.query(Shirt.type, func.count(Shirt.id))
        .filter(
            Shirt.type.isnot(None),
            Shirt.type != '',
            func.lower(Shirt.type) != 'none',
        )
        .group_by(Shirt.type)
        .all()
    )
    team_counts = dict(
        db.session.query(Shirt.squadra, func.count(Shirt.id))
        .filter(Shirt.squadra.isnot(None), Shirt.squadra != '')
        .group_by(Shirt.squadra)
        .all()
    )

    stagioni = sorted([s for s in season_counts.keys() if s], key=season_sort_key)
    squadre = sorted([sq for sq in team_counts.keys() if sq])
    brands = sorted([b for b in brand_counts.keys() if b])
    campionati = sorted([c for c in league_counts.keys() if c])
    colori = sorted([col for col in color_counts.keys() if col])
    season_totals = [(s, season_counts[s]) for s in stagioni]
    type_totals = sorted(type_counts.items(), key=lambda item: (-item[1], str(item[0]).lower()))
    team_totals = sorted(team_counts.items(), key=lambda item: (-item[1], str(item[0]).lower()))
    brand_totals = sorted(brand_counts.items(), key=lambda item: (-item[1], str(item[0]).lower()))
    league_totals = sorted(league_counts.items(), key=lambda item: (-item[1], str(item[0]).lower()))
    color_totals = sorted(color_counts.items(), key=lambda item: (-item[1], str(item[0]).lower()))

    return render_template(
        'admin/dashboard.html',
        shirts=shirts,
        brands=brands,
        campionati=campionati,
        colori=colori,
        types=sorted([t[0] for t in types if t[0]]),
        stagioni=stagioni,
        squadre=squadre,
        brand_counts=brand_counts,
        league_counts=league_counts,
        color_counts=color_counts,
        season_counts=season_counts,
        type_counts=type_counts,
        team_counts=team_counts,
        season_totals=season_totals,
        type_totals=type_totals,
        team_totals=team_totals,
        brand_totals=brand_totals,
        league_totals=league_totals,
        color_totals=color_totals,
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
                descrizione_ita=None,
                status=request.form.get('status', 'active')
            )
            new_descrizione_ita = request.form.get('descrizione_ita')
            if new_descrizione_ita and new_descrizione_ita.strip().lower() != 'none':
                shirt.descrizione_ita = new_descrizione_ita
            db.session.add(shirt)
            db.session.commit()

            if shirt.descrizione and not shirt.descrizione_ita:
                get_or_translate_description(shirt)

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
            if new_descrizione_ita and new_descrizione_ita.strip().lower() == 'none':
                new_descrizione_ita = ''
            shirt.descrizione = new_descrizione
            shirt.descrizione_ita = new_descrizione_ita
            shirt.status = request.form.get('status', 'active')

            if new_descrizione != old_descrizione and not new_descrizione_ita:
                shirt.descrizione_ita = None
            
            db.session.commit()

            if shirt.descrizione and not shirt.descrizione_ita:
                get_or_translate_description(shirt)
            
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
