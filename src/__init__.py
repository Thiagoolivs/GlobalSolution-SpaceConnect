import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()


def _migrate():
    """Migração leve e idempotente: adiciona a coluna `classificacao` se faltar
    (preserva bancos existentes) e faz backfill das linhas antigas.
    Funciona em SQLite e PostgreSQL (ALTER TABLE ... ADD COLUMN)."""
    try:
        cols = [c["name"] for c in inspect(db.engine).get_columns("ciclo_telemetria")]
    except Exception:
        return  # tabela ainda não existe (será criada por create_all)
    if "classificacao" not in cols:
        db.session.execute(text("ALTER TABLE ciclo_telemetria ADD COLUMN classificacao VARCHAR(20)"))
        db.session.commit()
    # Backfill das linhas sem classificação
    from .models import CicloTelemetria
    from .services import classificar_missao
    pendentes = CicloTelemetria.query.filter(CicloTelemetria.classificacao.is_(None)).all()
    for c in pendentes:
        c.classificacao = classificar_missao(c.risco)
    if pendentes:
        db.session.commit()


def _database_uri():
    """Resolve a URI do banco por variável de ambiente.

    - Produção: DATABASE_URL (ex.: postgresql://...). Railway/Heroku às vezes
      entregam o prefixo legado `postgres://`, que o SQLAlchemy 2.x não aceita,
      então normalizamos para `postgresql://`.
    - Desenvolvimento: sem DATABASE_URL, usa SQLite local (missao.db).
    A troca de ambiente é só por env var — sem alterar código.
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return f"sqlite:///{os.path.join(base_dir, 'missao.db')}"


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["SQLALCHEMY_DATABASE_URI"] = _database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "mission-control-secret")

    db.init_app(app)

    from .routes import bp
    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()
        _migrate()

    return app
