from flask import Blueprint, render_template, request, redirect, url_for
from app.models import Shirt, db

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
@public_bp.route('/catalog')
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

@public_bp.route('/shirt/<int:shirt_id>')
def shirt_detail(shirt_id):
    shirt = Shirt.query.get_or_404(shirt_id)
    return render_template('public/shirt.html', shirt=shirt)

# Security Honeypots - Redirect common admin guesses to the catalog
@public_bp.route('/admin')
@public_bp.route('/login')
@public_bp.route('/wp-admin')
@public_bp.route('/administrator')
@public_bp.route('/manager')
def honeypot():
    return redirect(url_for('public.catalog'))
