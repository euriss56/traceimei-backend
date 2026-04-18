/**
 * traceimei-api.ts
 * ─────────────────────────────────────────────────────────────
 * Service centralisé pour appeler le backend Flask (Render.com)
 * 
 * UTILISATION :
 *   import { traceIMEIApi } from "@/services/traceimei-api";
 *   const result = await traceIMEIApi.verifyIMEI("356938035643809");
 */

// ── URL de base ────────────────────────────────────────────────────────────
// En développement → http://localhost:5000
// En production    → ton URL Render.com
const BASE_URL = import.meta.env.VITE_FLASK_API_URL
  ?? "https://traceimei-backend.onrender.com";

// ── Types ──────────────────────────────────────────────────────────────────

export interface MLScore {
  theft_probability: number;   // 0.0 → 1.0
  theft_percent: string;       // "23.5%"
  is_anomaly: boolean;
  anomaly_score: number;
  risk_level: "low" | "medium" | "high" | "unknown";
}

export interface IMEIVerifyResult {
  imei: string;
  valid: boolean;
  is_stolen: boolean;
  status: "clean" | "stolen" | "unknown";
  ml_score: MLScore;
  db_record: Record<string, unknown> | null;
  checked_at: string;
  error?: string;
}

export interface IMEIReportPayload {
  imei: string;
  brand: string;
  model: string;
  theft_date: string;   // format "YYYY-MM-DD"
  location: string;
  description?: string;
}

export interface AuthResponse {
  success: boolean;
  token: string;
  user: {
    id: string;
    email: string;
    name: string;
    role: "user" | "dealer" | "admin";
  };
}

export interface StatsOverview {
  total_imei_registered: number;
  total_stolen: number;
  checks_today: number;
  total_users: number;
  recovery_rate: string;
}

// ── Helper fetch ───────────────────────────────────────────────────────────

async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("flask_jwt_token");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> ?? {}),
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error ?? `Erreur API : ${response.status}`);
  }

  return data as T;
}

// ── API TraceIMEI ──────────────────────────────────────────────────────────

export const traceIMEIApi = {

  // ── IMEI ────────────────────────────────────────────────────────────────

  /**
   * Vérifie un IMEI : format + base de données + score ML
   * Ne nécessite pas d'être connecté
   */
  verifyIMEI: (imei: string) =>
    apiFetch<IMEIVerifyResult>("/api/imei/verify", {
      method: "POST",
      body: JSON.stringify({ imei }),
    }),

  /**
   * Signale un téléphone comme volé
   * Nécessite d'être connecté (JWT)
   */
  reportTheft: (payload: IMEIReportPayload) =>
    apiFetch<{ success: boolean; message: string }>("/api/imei/report", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  /**
   * Récupère les détails complets d'un IMEI
   */
  getIMEIDetails: (imei: string) =>
    apiFetch<{ imei: string; found: boolean; record: Record<string, unknown> }>(
      `/api/imei/${imei}`
    ),

  // ── ML ──────────────────────────────────────────────────────────────────

  /**
   * Score ML uniquement (sans consultation base de données)
   */
  getMLScore: (imei: string) =>
    apiFetch<MLScore & { imei: string; features_used: Record<string, number> }>(
      "/api/ml/predict",
      {
        method: "POST",
        body: JSON.stringify({ imei }),
      }
    ),

  /**
   * Score ML sur plusieurs IMEI (dealers uniquement)
   */
  batchPredict: (imeis: string[]) =>
    apiFetch<{
      total: number;
      processed: number;
      summary: Record<string, number | string>;
      results: MLScore[];
    }>("/api/ml/batch-predict", {
      method: "POST",
      body: JSON.stringify({ imeis }),
    }),

  /**
   * Infos sur les modèles ML déployés
   */
  getModelInfo: () =>
    apiFetch<{ loaded: boolean; models: Record<string, unknown> }>(
      "/api/ml/model-info"
    ),

  // ── Auth ────────────────────────────────────────────────────────────────

  /**
   * Connexion → reçoit un JWT stocké dans localStorage
   */
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const data = await apiFetch<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (data.token) {
      localStorage.setItem("flask_jwt_token", data.token);
    }
    return data;
  },

  /**
   * Inscription
   */
  register: async (
    email: string,
    password: string,
    full_name: string,
    role = "user"
  ): Promise<AuthResponse> => {
    const data = await apiFetch<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name, role }),
    });
    if (data.token) {
      localStorage.setItem("flask_jwt_token", data.token);
    }
    return data;
  },

  /**
   * Déconnexion — supprime le JWT du localStorage
   */
  logout: () => {
    localStorage.removeItem("flask_jwt_token");
  },

  /**
   * Profil utilisateur connecté
   */
  getProfile: () =>
    apiFetch<{ user: AuthResponse["user"] }>("/api/auth/me"),

  // ── Stats ────────────────────────────────────────────────────────────────

  /**
   * Chiffres clés pour le dashboard
   */
  getStats: () =>
    apiFetch<StatsOverview>("/api/stats/overview"),

  /**
   * Derniers signalements de vol
   */
  getRecentReports: (limit = 10) =>
    apiFetch<{ reports: Record<string, unknown>[]; count: number }>(
      `/api/stats/recent?limit=${limit}`
    ),

  /**
   * Répartition par région (pour la carte Leaflet)
   */
  getStatsByRegion: () =>
    apiFetch<{ regions: { region: string; count: number }[]; total: number }>(
      "/api/stats/by-region"
    ),

  // ── Utilitaire ───────────────────────────────────────────────────────────

  /**
   * Vérifie si l'API Flask est disponible
   */
  healthCheck: () =>
    apiFetch<{ status: string; service: string; version: string }>("/"),

  /**
   * Retourne true si l'utilisateur a un JWT stocké
   */
  isAuthenticated: () => !!localStorage.getItem("flask_jwt_token"),
};
