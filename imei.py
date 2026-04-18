"""
Routes IMEI
  POST /api/imei/verify  → vérifie un IMEI + score ML
  POST /api/imei/report  → signale un vol
  GET  /api/imei/<imei>  → détails d'un IMEI
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone

from utils.imei_utils import validate_imei, extract_imei_features
from utils.supabase_client import get_supabase

imei_bp = Blueprint("imei", __name__)


@imei_bp.route("/verify", methods=["POST"])
def verify_imei():
    """
    Vérifie un IMEI :
    1. Validation format (Luhn)
    2. Consultation base de données (volé ou non)
    3. Score ML (Random Forest + Isolation Forest)
    """
    data = request.get_json()
    if not data or "imei" not in data:
        return jsonify({"error": "IMEI requis"}), 400

    imei = str(data["imei"]).strip()

    # ── Étape 1 : Validation format ────────────────────────────
    validation = validate_imei(imei)
    if not validation["is_valid"]:
        return jsonify({
            "imei":     imei,
            "valid":    False,
            "error":    validation["error"],
        }), 400

    # ── Étape 2 : Consultation Supabase ────────────────────────
    supabase = get_supabase()
    result = supabase.table("imei_records") \
                     .select("*") \
                     .eq("imei", imei) \
                     .execute()

    db_record = result.data[0] if result.data else None
    is_stolen = db_record["is_stolen"] if db_record else False
    status    = db_record["status"] if db_record else "unknown"

    # ── Étape 3 : Score ML ─────────────────────────────────────
    ml_result = _get_ml_score(imei)

    # ── Réponse complète ───────────────────────────────────────
    response = {
        "imei":             imei,
        "valid":            True,
        "is_stolen":        is_stolen,
        "status":           status,           # "clean", "stolen", "unknown"
        "ml_score": {
            "theft_probability":    ml_result["theft_probability"],
            "is_anomaly":           ml_result["is_anomaly"],
            "anomaly_score":        ml_result["anomaly_score"],
            "risk_level":           ml_result["risk_level"],  # "low","medium","high"
        },
        "db_record":        db_record,
        "checked_at":       datetime.now(timezone.utc).isoformat(),
    }

    # Enregistrer la consultation dans Supabase (optionnel)
    try:
        supabase.table("imei_checks").insert({
            "imei":              imei,
            "result_stolen":     is_stolen,
            "ml_risk_level":     ml_result["risk_level"],
            "checked_at":        datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass  # Non bloquant si la table n'existe pas encore

    return jsonify(response), 200


@imei_bp.route("/report", methods=["POST"])
@jwt_required()
def report_theft():
    """
    Signale un téléphone comme volé.
    Nécessite d'être authentifié (JWT).
    """
    user_id = get_jwt_identity()
    data    = request.get_json()

    required = ["imei", "brand", "model", "theft_date", "location"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Champ requis manquant : {field}"}), 400

    imei = str(data["imei"]).strip()

    # Validation IMEI
    validation = validate_imei(imei)
    if not validation["is_valid"]:
        return jsonify({"error": validation["error"]}), 400

    supabase = get_supabase()

    # Vérifier si déjà signalé
    existing = supabase.table("imei_records") \
                       .select("id") \
                       .eq("imei", imei) \
                       .execute()

    if existing.data:
        # Mettre à jour
        supabase.table("imei_records").update({
            "is_stolen":    True,
            "status":       "stolen",
            "updated_at":   datetime.now(timezone.utc).isoformat(),
        }).eq("imei", imei).execute()
        action = "updated"
    else:
        # Créer un nouveau signalement
        supabase.table("imei_records").insert({
            "imei":         imei,
            "brand":        data["brand"],
            "model":        data["model"],
            "theft_date":   data["theft_date"],
            "location":     data["location"],
            "description":  data.get("description", ""),
            "reporter_id":  user_id,
            "is_stolen":    True,
            "status":       "stolen",
            "reported_at":  datetime.now(timezone.utc).isoformat(),
        }).execute()
        action = "created"

    return jsonify({
        "success":  True,
        "action":   action,
        "imei":     imei,
        "message":  "Signalement enregistré avec succès",
    }), 201


@imei_bp.route("/<imei>", methods=["GET"])
def get_imei_details(imei: str):
    """Récupère les détails complets d'un IMEI."""
    validation = validate_imei(imei)
    if not validation["is_valid"]:
        return jsonify({"error": validation["error"]}), 400

    supabase = get_supabase()
    result   = supabase.table("imei_records") \
                       .select("*") \
                       .eq("imei", imei) \
                       .execute()

    if not result.data:
        return jsonify({
            "imei":     imei,
            "found":    False,
            "message":  "Aucun enregistrement trouvé pour cet IMEI",
        }), 404

    return jsonify({
        "imei":     imei,
        "found":    True,
        "record":   result.data[0],
    }), 200


# ── Helper : Score ML ──────────────────────────────────────────────────────

def _get_ml_score(imei: str) -> dict:
    """Appelle les modèles ML et retourne un score de risque."""
    try:
        import joblib, numpy as np
        import os

        models_dir = os.path.join(os.path.dirname(__file__), "..", "models")

        # Charger les modèles (mis en cache après le premier appel)
        rf_data = joblib.load(os.path.join(models_dir, "random_forest.pkl"))
        if_data = joblib.load(os.path.join(models_dir, "isolation_forest.pkl"))

        rf_model    = rf_data["model"]
        rf_features = rf_data["features"]
        if_model    = if_data["model"]
        if_scaler   = if_data["scaler"]
        if_features = if_data["features"]

        # Extraire les features
        feats = extract_imei_features(imei)
        X_rf  = np.array([[feats["tac"], feats["snr_numeric"],
                           feats["imei_sum"] / 15,  # digit_mean approx
                           feats["imei_variance"],
                           feats["tac_prefix"],
                           feats["imei_sum"],
                           feats["check_digit"]]])

        # Random Forest → probabilité de vol
        proba           = rf_model.predict_proba(X_rf)[0][1]  # proba classe "volé"
        theft_prob      = round(float(proba), 4)

        # Isolation Forest → anomalie
        X_if            = if_scaler.transform(X_rf)
        anomaly_score   = float(if_model.decision_function(X_if)[0])
        is_anomaly      = if_model.predict(X_if)[0] == -1

        # Niveau de risque combiné
        if theft_prob > 0.7 or is_anomaly:
            risk = "high"
        elif theft_prob > 0.4:
            risk = "medium"
        else:
            risk = "low"

        return {
            "theft_probability": theft_prob,
            "is_anomaly":        bool(is_anomaly),
            "anomaly_score":     round(anomaly_score, 4),
            "risk_level":        risk,
        }

    except FileNotFoundError:
        # Modèles pas encore entraînés → score neutre
        return {
            "theft_probability": 0.0,
            "is_anomaly":        False,
            "anomaly_score":     0.0,
            "risk_level":        "unknown",
            "note":              "Modèles ML non encore entraînés. Lance: python models/train.py",
        }
    except Exception as e:
        return {
            "theft_probability": 0.0,
            "is_anomaly":        False,
            "anomaly_score":     0.0,
            "risk_level":        "unknown",
            "error":             str(e),
        }
