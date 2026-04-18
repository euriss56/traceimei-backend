"""
TraceIMEI-BJ — Backend Flask
Point d'entrée principal de l'API
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# Importer les routes
from imei import imei_bp
from auth import auth_bp
from ml import ml_bp
from stats import stats_bp
def create_app():
    app = Flask(__name__)

    # ── Configuration ──────────────────────────────────────────
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 86400  # 24 heures

    # ── Extensions ─────────────────────────────────────────────
    # CORS : autorise ton frontend Vercel à appeler cette API
    CORS(app, origins=[
        "https://traceimei-connect.vercel.app",
        "http://localhost:5173",  # dev local
        "http://localhost:3000",
    ])

    JWTManager(app)

    # ── Enregistrement des routes ───────────────────────────────
    app.register_blueprint(imei_bp,  url_prefix="/api/imei")
    app.register_blueprint(auth_bp,  url_prefix="/api/auth")
    app.register_blueprint(ml_bp,    url_prefix="/api/ml")
    app.register_blueprint(stats_bp, url_prefix="/api/stats")

    # ── Route de santé (pour Render.com) ───────────────────────
    @app.route("/")
    def health():
        return jsonify({
            "status": "ok",
            "service": "TraceIMEI-BJ API",
            "version": "1.0.0"
        })

    @app.route("/health")
    def health_check():
        return jsonify({"status": "healthy"}), 200

    return app


# Lancement de l'application
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
