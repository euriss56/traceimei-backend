"""
Routes Authentification — JWT maison
  POST /api/auth/register → inscription
  POST /api/auth/login    → connexion → retourne JWT
  GET  /api/auth/me       → profil utilisateur connecté
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
from datetime import datetime, timezone
import hashlib, os

from utils.supabase_client import get_supabase

auth_bp = Blueprint("auth", __name__)


def _hash_password(password: str) -> str:
    """Hash simple SHA-256 + sel. En production, utilise bcrypt."""
    salt = os.getenv("JWT_SECRET_KEY", "default-salt")
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


@auth_bp.route("/register", methods=["POST"])
def register():
    """Inscription d'un nouvel utilisateur."""
    data = request.get_json()

    required = ["email", "password", "full_name"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Champ requis : {field}"}), 400

    email    = data["email"].lower().strip()
    password = data["password"]

    if len(password) < 6:
        return jsonify({"error": "Mot de passe trop court (min 6 caractères)"}), 400

    supabase = get_supabase()

    # Vérifier si email déjà utilisé
    existing = supabase.table("users") \
                       .select("id") \
                       .eq("email", email) \
                       .execute()
    if existing.data:
        return jsonify({"error": "Cet email est déjà utilisé"}), 409

    # Créer l'utilisateur
    user = supabase.table("users").insert({
        "email":          email,
        "full_name":      data["full_name"],
        "password_hash":  _hash_password(password),
        "role":           data.get("role", "user"),  # "user" ou "dealer"
        "created_at":     datetime.now(timezone.utc).isoformat(),
    }).execute()

    user_data = user.data[0]

    # Générer le JWT
    token = create_access_token(identity=str(user_data["id"]))

    return jsonify({
        "success":      True,
        "token":        token,
        "user": {
            "id":       user_data["id"],
            "email":    user_data["email"],
            "name":     user_data["full_name"],
            "role":     user_data["role"],
        }
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """Connexion — retourne un JWT valide 24h."""
    data = request.get_json()

    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email et mot de passe requis"}), 400

    email    = data["email"].lower().strip()
    password = data["password"]

    supabase = get_supabase()

    # Chercher l'utilisateur
    result = supabase.table("users") \
                     .select("*") \
                     .eq("email", email) \
                     .eq("password_hash", _hash_password(password)) \
                     .execute()

    if not result.data:
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401

    user  = result.data[0]
    token = create_access_token(identity=str(user["id"]))

    return jsonify({
        "success":  True,
        "token":    token,
        "user": {
            "id":   user["id"],
            "email": user["email"],
            "name": user["full_name"],
            "role": user["role"],
        }
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_profile():
    """Retourne le profil de l'utilisateur connecté."""
    user_id  = get_jwt_identity()
    supabase = get_supabase()

    result = supabase.table("users") \
                     .select("id, email, full_name, role, created_at") \
                     .eq("id", user_id) \
                     .execute()

    if not result.data:
        return jsonify({"error": "Utilisateur introuvable"}), 404

    return jsonify({"user": result.data[0]}), 200
