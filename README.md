# TraceIMEI-BJ — Backend Flask

API backend pour le système de traçabilité des téléphones volés au Bénin.

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Framework | Flask 3.0 |
| ML        | scikit-learn (Random Forest + Isolation Forest) |
| Base de données | Supabase (PostgreSQL) |
| Auth | JWT (flask-jwt-extended) |
| Hébergement | Render.com (plan gratuit) |

## Architecture

```
React Frontend (Vercel)
        ↓ HTTP
Flask API (Render.com)
    ├── /api/imei    → vérification IMEI
    ├── /api/auth    → authentification JWT
    ├── /api/ml      → prédictions ML
    └── /api/stats   → données dashboard
        ↓
Supabase PostgreSQL
        +
Modèles ML (Random Forest + Isolation Forest)
```

## Installation locale

### 1. Cloner et installer
```bash
git clone https://github.com/TON_USERNAME/traceimei-backend.git
cd traceimei-backend
pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement
```bash
cp .env.example .env
# Remplis .env avec tes vraies valeurs Supabase
```

### 3. Créer les tables Supabase
- Va sur ton dashboard Supabase
- Ouvre l'éditeur SQL
- Copie et exécute le contenu de `supabase_schema.sql`

### 4. Entraîner les modèles ML
```bash
python models/train.py
```
Cette commande génère 10 000 IMEI synthétiques et entraîne :
- `models/random_forest.pkl` — classification vol
- `models/isolation_forest.pkl` — détection d'anomalies

### 5. Lancer le serveur
```bash
python app.py
```
API disponible sur : http://localhost:5000

## Endpoints principaux

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| GET | `/` | Santé de l'API | Non |
| POST | `/api/imei/verify` | Vérifier un IMEI | Non |
| POST | `/api/imei/report` | Signaler un vol | JWT |
| GET | `/api/imei/<imei>` | Détails d'un IMEI | Non |
| POST | `/api/auth/register` | Inscription | Non |
| POST | `/api/auth/login` | Connexion | Non |
| GET | `/api/auth/me` | Profil connecté | JWT |
| POST | `/api/ml/predict` | Score ML d'un IMEI | Non |
| POST | `/api/ml/batch-predict` | Score ML (lot) | JWT |
| GET | `/api/ml/model-info` | Info modèles | Non |
| GET | `/api/stats/overview` | Stats globales | Non |
| GET | `/api/stats/recent` | Derniers signalements | Non |

## Déploiement sur Render.com

1. Push ce repo sur GitHub
2. Va sur [render.com](https://render.com) → New Web Service
3. Connecte ton repo GitHub
4. Render détecte automatiquement le `render.yaml`
5. Ajoute les variables d'environnement dans le dashboard Render :
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
6. Deploy !

URL finale : `https://traceimei-backend.onrender.com`

## Connexion avec le frontend React

Dans ton projet React, appelle l'API Flask :

```js
// Vérification IMEI avec score ML
const response = await fetch(
  "https://traceimei-backend.onrender.com/api/imei/verify",
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ imei: "356938035643809" })
  }
);
const data = await response.json();
console.log(data.ml_score.risk_level); // "low" | "medium" | "high"
```
