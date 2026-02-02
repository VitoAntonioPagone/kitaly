from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Shirt(db.Model):
    __tablename__ = 'shirts'
    
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), nullable=False)
    squadra = db.Column(db.String(100), nullable=False)
    campionato = db.Column(db.String(100), nullable=False)
    taglia = db.Column(db.String(10), nullable=False)
    colore = db.Column(db.String(50), nullable=False)
    stagione = db.Column(db.String(20), nullable=False)
    tipologia = db.Column(db.String(50), nullable=False)
    maniche = db.Column(db.String(50), nullable=True)
    player_issued = db.Column(db.Boolean, default=False)
    nazionale = db.Column(db.Boolean, default=False)
    prezzo_pagato = db.Column(db.Float, nullable=True)
    descrizione = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    images = db.relationship('ShirtImage', backref='shirt', cascade='all, delete-orphan', lazy=True)

    @property
    def cover_image(self):
        cover = ShirtImage.query.filter_by(shirt_id=self.id, is_cover=True).first()
        if not cover and self.images:
            return self.images[0]
        return cover

class ShirtImage(db.Model):
    __tablename__ = 'shirt_images'
    
    id = db.Column(db.Integer, primary_key=True)
    shirt_id = db.Column(db.Integer, db.ForeignKey('shirts.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    is_cover = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
