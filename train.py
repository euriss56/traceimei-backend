"""
TraceIMEI-BJ — Génération de données synthétiques et entraînement ML
--------------------------------------------------------------------
Lance ce script UNE SEULE FOIS pour créer les modèles :
    python models/train.py

Modèles créés :
  - Random Forest   → prédit si un IMEI est probablement volé
  - Isolation Forest → détecte les comportements/IMEI suspects (anomalies)
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import StandardScaler

# Ajouter le dossier parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 1. Génération des données synthétiques ─────────────────────────────────

def generate_imei(n: int) -> list[str]:
    """Génère n numéros IMEI valides aléatoires (avec checksum Luhn)."""
    imeis = []
    # TACs réalistes (préfixes de vrais fabricants)
    real_tacs = ["356938", "352099", "013852", "867179", "490154",
                 "358432", "012207", "354688", "869716", "351756"]

    for _ in range(n):
        tac = np.random.choice(real_tacs)
        snr = str(np.random.randint(0, 99999999)).zfill(8)
        base = tac + snr
        check = _luhn_check_digit(base)
        imeis.append(base + str(check))

    return imeis


def _luhn_check_digit(partial: str) -> int:
    """Calcule le chiffre de contrôle Luhn pour un IMEI partiel (14 chiffres)."""
    total = 0
    for i, digit in enumerate(reversed(partial)):
        n = int(digit)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return (10 - (total % 10)) % 10


def extract_features(imei: str) -> list:
    """Extrait les features ML d'un IMEI."""
    digits     = [int(d) for d in imei]
    tac        = int(imei[:6])
    snr        = int(imei[6:14])
    mean       = np.mean(digits)
    variance   = np.var(digits)
    tac_prefix = int(imei[:2])

    return [tac, snr, mean, variance, tac_prefix, sum(digits), int(imei[14])]


def generate_dataset(n_samples: int = 10000) -> pd.DataFrame:
    """
    Génère un dataset synthétique réaliste.

    Features utilisées :
      - tac          : Type Allocation Code (identifie fabricant/modèle)
      - snr          : Numéro de série
      - digit_mean   : Moyenne des chiffres de l'IMEI
      - digit_var    : Variance des chiffres
      - tac_prefix   : 2 premiers chiffres du TAC
      - digit_sum    : Somme des chiffres
      - check_digit  : Chiffre de contrôle

    Label :
      - is_stolen    : 1 = volé, 0 = légitime
      - anomaly_score: score de comportement suspect (pour Isolation Forest)
    """
    print(f"⏳ Génération de {n_samples} IMEI synthétiques...")
    imeis = generate_imei(n_samples)

    rows = []
    for imei in imeis:
        feats = extract_features(imei)
        tac_prefix = int(imei[:2])

        # ── Règles synthétiques pour simuler des vols ──────────────
        # (logique métier simplifiée pour l'entraînement)
        stolen_prob = 0.15  # 15% de base

        # IMEI avec SNR très faible → suspect (séquence fabriquée)
        snr = int(imei[6:14])
        if snr < 1000:
            stolen_prob += 0.40

        # Certains TAC préfixes plus ciblés par les voleurs
        if tac_prefix in [35, 86]:
            stolen_prob += 0.10

        # Variance très faible = chiffres répétitifs = IMEI cloné
        if feats[3] < 2.0:
            stolen_prob += 0.25

        # Somme des chiffres anormalement basse
        if feats[5] < 40:
            stolen_prob += 0.15

        is_stolen = 1 if np.random.random() < min(stolen_prob, 0.90) else 0

        # Score d'anomalie (pour Isolation Forest — non supervisé)
        anomaly = (
            (1 if snr < 1000 else 0) +
            (1 if feats[3] < 2.0 else 0) +
            (1 if feats[5] < 40 else 0)
        )

        rows.append({
            "imei":          imei,
            "tac":           feats[0],
            "snr":           feats[1],
            "digit_mean":    round(feats[2], 4),
            "digit_var":     round(feats[3], 4),
            "tac_prefix":    feats[4],
            "digit_sum":     feats[5],
            "check_digit":   feats[6],
            "is_stolen":     is_stolen,
            "anomaly_level": anomaly,
        })

    df = pd.DataFrame(rows)
    print(f"✅ Dataset généré : {len(df)} lignes")
    print(f"   Volés : {df['is_stolen'].sum()} ({df['is_stolen'].mean()*100:.1f}%)")
    return df


# ── 2. Entraînement Random Forest ──────────────────────────────────────────

def train_random_forest(df: pd.DataFrame):
    """
    Random Forest — Classification supervisée
    Prédit : cet IMEI est-il probablement volé ? (0 ou 1)
    """
    print("\n🌲 Entraînement Random Forest...")

    FEATURES = ["tac", "snr", "digit_mean", "digit_var",
                "tac_prefix", "digit_sum", "check_digit"]

    X = df[FEATURES]
    y = df["is_stolen"]

    # Split train/test (80% / 20%)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=100,       # 100 arbres de décision
        max_depth=10,           # profondeur max pour éviter overfitting
        min_samples_split=5,
        class_weight="balanced", # compense le déséquilibre volé/non-volé
        random_state=42,
        n_jobs=-1               # utilise tous les cores CPU
    )

    model.fit(X_train, y_train)

    # Évaluation
    y_pred    = model.predict(X_test)
    accuracy  = accuracy_score(y_test, y_pred)
    print(f"   Accuracy : {accuracy*100:.2f}%")
    print("\n   Rapport détaillé :")
    print(classification_report(y_test, y_pred,
                                 target_names=["Légitime", "Volé"]))

    # Importance des features
    importances = dict(zip(FEATURES, model.feature_importances_))
    print("   Importance des features :")
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        print(f"     {feat:15s} : {imp:.4f}")

    return model, FEATURES


# ── 3. Entraînement Isolation Forest ───────────────────────────────────────

def train_isolation_forest(df: pd.DataFrame):
    """
    Isolation Forest — Détection d'anomalies non supervisée
    Détecte les IMEI avec des patterns inhabituels (potentiellement clonés/suspects)
    """
    print("\n🔍 Entraînement Isolation Forest...")

    FEATURES = ["tac", "snr", "digit_mean", "digit_var",
                "tac_prefix", "digit_sum", "check_digit"]

    X = df[FEATURES]

    scaler  = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=100,
        contamination=0.15,   # on suppose 15% d'anomalies dans les données
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_scaled)

    # Test rapide
    scores  = model.decision_function(X_scaled)
    preds   = model.predict(X_scaled)
    n_anomalies = (preds == -1).sum()
    print(f"   Anomalies détectées : {n_anomalies} ({n_anomalies/len(df)*100:.1f}%)")
    print(f"   Score moyen : {scores.mean():.4f}")

    return model, scaler, FEATURES


# ── 4. Sauvegarde des modèles ──────────────────────────────────────────────

def save_models(rf_model, rf_features, if_model, if_scaler, if_features):
    """Sauvegarde les modèles entraînés sur disque."""
    models_dir = os.path.dirname(os.path.abspath(__file__))

    joblib.dump({
        "model":    rf_model,
        "features": rf_features,
        "version":  "1.0.0"
    }, os.path.join(models_dir, "random_forest.pkl"))

    joblib.dump({
        "model":    if_model,
        "scaler":   if_scaler,
        "features": if_features,
        "version":  "1.0.0"
    }, os.path.join(models_dir, "isolation_forest.pkl"))

    print("\n💾 Modèles sauvegardés :")
    print(f"   → {models_dir}/random_forest.pkl")
    print(f"   → {models_dir}/isolation_forest.pkl")


# ── 5. Main ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  TraceIMEI-BJ — Entraînement des modèles ML")
    print("=" * 60)

    # Générer les données
    df = generate_dataset(n_samples=10000)

    # Entraîner les modèles
    rf_model, rf_features               = train_random_forest(df)
    if_model, if_scaler, if_features    = train_isolation_forest(df)

    # Sauvegarder
    save_models(rf_model, rf_features, if_model, if_scaler, if_features)

    print("\n✅ Entraînement terminé avec succès !")
    print("   Tu peux maintenant lancer : python app.py")
    print("=" * 60)
