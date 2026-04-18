"""
Routes ML — endpoints dédiés aux modèles
  POST /api/ml/predict       → prédiction sur un IMEI
  POST /api/ml/batch-predict → prédiction sur plusieurs IMEI
  GET  /api/ml/model-info    → infos sur les modèles chargés
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
import numpy as np
import os, joblib

from utils.imei_utils import validate_imei, extract_imei_features

ml_bp = Blueprint("ml", __name__)

# Cache des modèles (chargés une seule fois au démarrage)
_models_cache = {}

def _load_models():
    """Charge les modèles ML depuis le disque (avec cache)."""
    global _models_cache
    if _models_cache:
        return _models_cache

    models_dir = os.path.join(os.path.dirname(__file__), "..", "models")

    try:
        _models_cache["rf"] = joblib.load(
            os.path.join(models_dir, "random_forest.pkl")
        )
        _models_cache["if"] = joblib.load(
            os.path.join(models_dir, "isolation_forest.pkl")
        )
        _models_cache["loaded"] = True
    except FileNotFoundError:
        _models_cache["loaded"] = False

    return _models_cache


def _predict_single(imei: str) -> dict:
    """Prédit le risque pour un seul IMEI."""
    models = _load_models()

    if not models.get("loaded"):
        return {"error": "Modèles non disponibles. Lance: python models/train.py"}

    feats = extract_imei_features(imei)
    X = np.array([[
        feats["tac"],
        feats["snr_numeric"],
        feats["imei_sum"] / 15,
        feats["imei_variance"],
        feats["tac_prefix"],
        feats["imei_sum"],
        feats["check_digit"],
    ]])

    # Random Forest
    rf      = models["rf"]["model"]
    proba   = rf.predict_proba(X)[0][1]

    # Isolation Forest
    ifo     = models["if"]["model"]
    scaler  = models["if"]["scaler"]
    X_sc    = scaler.transform(X)
    anom_sc = float(ifo.decision_function(X_sc)[0])
    is_anom = ifo.predict(X_sc)[0] == -1

    # Niveau de risque
    if proba > 0.7 or is_anom:
        risk = "high"
    elif proba > 0.4:
        risk = "medium"
    else:
        risk = "low"

    return {
        "imei":                 imei,
        "theft_probability":    round(float(proba), 4),
        "theft_percent":        f"{proba*100:.1f}%",
        "is_anomaly":           bool(is_anom),
        "anomaly_score":        round(anom_sc, 4),
        "risk_level":           risk,
        "features_used":        feats,
    }


@ml_bp.route("/predict", methods=["POST"])
def predict():
    """Prédiction ML pour un IMEI unique."""
    data = request.get_json()

    if not data or "imei" not in data:
        return jsonify({"error": "IMEI requis"}), 400

    imei = str(data["imei"]).strip()

    # Validation
    v = validate_imei(imei)
    if not v["is_valid"]:
        return jsonify({"error": v["error"]}), 400

    result = _predict_single(imei)
    return jsonify(result), 200


@ml_bp.route("/batch-predict", methods=["POST"])
@jwt_required()
def batch_predict():
    """
    Prédiction ML pour une liste d'IMEI (max 100).
    Réservé aux utilisateurs authentifiés (dealers).
    """
    data  = request.get_json()
    imeis = data.get("imeis", [])

    if not imeis:
        return jsonify({"error": "Liste d'IMEI requise"}), 400

    if len(imeis) > 100:
        return jsonify({"error": "Maximum 100 IMEI par requête"}), 400

    results  = []
    errors   = []

    for imei in imeis:
        v = validate_imei(str(imei))
        if not v["is_valid"]:
            errors.append({"imei": imei, "error": v["error"]})
            continue
        results.append(_predict_single(str(imei)))

    # Résumé statistique
    if results:
        high_risk   = sum(1 for r in results if r.get("risk_level") == "high")
        medium_risk = sum(1 for r in results if r.get("risk_level") == "medium")
        low_risk    = sum(1 for r in results if r.get("risk_level") == "low")
        avg_proba   = np.mean([r["theft_probability"] for r in results])
    else:
        high_risk = medium_risk = low_risk = 0
        avg_proba = 0.0

    return jsonify({
        "total":        len(imeis),
        "processed":    len(results),
        "errors":       errors,
        "summary": {
            "high_risk":            high_risk,
            "medium_risk":          medium_risk,
            "low_risk":             low_risk,
            "avg_theft_probability": round(float(avg_proba), 4),
        },
        "results": results,
    }), 200


@ml_bp.route("/model-info", methods=["GET"])
def model_info():
    """Retourne les informations sur les modèles chargés."""
    models = _load_models()

    if not models.get("loaded"):
        return jsonify({
            "loaded":   False,
            "message":  "Modèles non entraînés. Lance: python models/train.py",
        }), 503

    rf = models["rf"]["model"]

    return jsonify({
        "loaded":   True,
        "models": {
            "random_forest": {
                "type":             "RandomForestClassifier",
                "version":          models["rf"]["version"],
                "n_estimators":     rf.n_estimators,
                "features":         models["rf"]["features"],
                "task":             "Classification vol (0=légitime, 1=volé)",
            },
            "isolation_forest": {
                "type":             "IsolationForest",
                "version":          models["if"]["version"],
                "features":         models["if"]["features"],
                "task":             "Détection d'anomalies IMEI suspects",
            },
        }
    }), 200
