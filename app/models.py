from datetime import datetime
import re
import unicodedata
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Shirt(db.Model):
    __tablename__ = 'shirts'
    
    id = db.Column(db.Integer, primary_key=True)
    player_name = db.Column(db.String(100), nullable=True)
    brand = db.Column(db.String(100), nullable=False)
    squadra = db.Column(db.String(100), nullable=False)
    campionato = db.Column(db.String(100), nullable=False)
    taglia = db.Column(db.String(10), nullable=False)
    colore = db.Column(db.String(50), nullable=False)
    stagione = db.Column(db.String(20), nullable=False)
    tipologia = db.Column(db.String(50), nullable=True)
    type = db.Column(db.String(50), nullable=True)
    maniche = db.Column(db.String(50), nullable=True)
    player_issued = db.Column(db.Boolean, default=False)
    nazionale = db.Column(db.Boolean, default=False)
    prezzo_pagato = db.Column(db.Float, nullable=True)
    descrizione = db.Column(db.Text, nullable=True)
    descrizione_ita = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    images = db.relationship('ShirtImage', backref='shirt', cascade='all, delete-orphan', lazy=True)

    @property
    def display_name(self):
        """Generate display name with player name first if present"""
        parts = []
        if self.player_name:
            parts.append(self.player_name)
        if self.maniche:
            parts.append(self.maniche)
        parts.append(self.squadra)
        if self.tipologia:
            parts.append(self.tipologia)
        parts.append(self.type or 'Shirt')
        parts.append(self.stagione + '*' if self.player_issued else self.stagione)
        return ' '.join([p for p in parts if p])

    @property
    def cover_image(self):
        cover = ShirtImage.query.filter_by(shirt_id=self.id, is_cover=True).first()
        if not cover and self.images:
            return self.images[0]
        return cover

    @property
    def slug(self):
        base = self.display_name or ""
        normalized = unicodedata.normalize("NFKD", base)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
        return slug or str(self.id)

class ShirtImage(db.Model):
    __tablename__ = 'shirt_images'
    
    id = db.Column(db.Integer, primary_key=True)
    shirt_id = db.Column(db.Integer, db.ForeignKey('shirts.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    is_cover = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
