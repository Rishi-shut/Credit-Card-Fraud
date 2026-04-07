"""
SQLAlchemy models — User and Prediction tables.
"""
from datetime import datetime
import json
from api.database import db


class User(db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    clerk_id      = db.Column(db.String(128), unique=True, nullable=False, index=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin      = db.Column(db.Boolean, default=False)


    predictions = db.relationship(
        'Prediction', backref='user', lazy=True, cascade='all, delete-orphan'
    )

    def to_dict(self):
        return {
            'id':               self.id,
            'email':            self.email,
            'created_at':       self.created_at.isoformat(),
            'is_admin':         self.is_admin,
        }


class Prediction(db.Model):
    __tablename__ = 'predictions'

    id                     = db.Column(db.Integer, primary_key=True)
    user_id                = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    timestamp              = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    amount                 = db.Column(db.Float, nullable=True)
    prediction             = db.Column(db.Integer, nullable=False)   # 0 = legit, 1 = fraud
    prediction_label       = db.Column(db.String(20), nullable=False)
    fraud_probability      = db.Column(db.Float, nullable=False)
    legitimate_probability = db.Column(db.Float, nullable=False)
    confidence             = db.Column(db.Float, nullable=False)
    features_json          = db.Column(db.Text, nullable=True)
    shap_values_json       = db.Column(db.Text, nullable=True)
    ip_address             = db.Column(db.String(50), nullable=True)
    source                 = db.Column(db.String(20), default='manual')  # manual | batch | csv

    def to_dict(self):
        return {
            'id':                     self.id,
            'user_id':                self.user_id,
            'timestamp':              self.timestamp.isoformat(),
            'amount':                 self.amount,
            'prediction':             self.prediction,
            'prediction_label':       self.prediction_label,
            'fraud_probability':      round(self.fraud_probability, 4),
            'legitimate_probability': round(self.legitimate_probability, 4),
            'confidence':             round(self.confidence, 4),
            'source':                 self.source,
            'shap_values':            json.loads(self.shap_values_json) if self.shap_values_json else None,
        }
