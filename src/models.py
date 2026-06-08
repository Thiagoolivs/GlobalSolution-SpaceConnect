from . import db
from datetime import datetime


class CicloTelemetria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ciclo = db.Column(db.Integer, nullable=False)
    temperatura = db.Column(db.Float, nullable=False)
    comunicacao = db.Column(db.Float, nullable=False)
    bateria_solar = db.Column(db.Float, nullable=False)
    consumo_o2 = db.Column(db.Float, nullable=False)
    matriz = db.Column(db.Float, nullable=False)
    risco = db.Column(db.Integer, nullable=False)
    classificacao = db.Column(db.String(20))   # MISSÃO ESTÁVEL | EM ATENÇÃO | CRÍTICA
    alerta_evacuacao = db.Column(db.Boolean, default=False)
    ia_insight = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class MensagemChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
