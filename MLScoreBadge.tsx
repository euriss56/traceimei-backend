/**
 * MLScoreBadge.tsx
 * ─────────────────────────────────────────────────────────────
 * Composant qui affiche le score ML d'un IMEI de façon visuelle
 * Utilise Tailwind + shadcn/ui (déjà dans ton projet)
 *
 * UTILISATION :
 *   <MLScoreBadge score={result.ml_score} />
 */

import { MLScore } from "@/services/traceimei-api";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  AlertTriangle,
  CheckCircle,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
} from "lucide-react";

interface MLScoreBadgeProps {
  score: MLScore;
  showDetails?: boolean;
}

export function MLScoreBadge({ score, showDetails = true }: MLScoreBadgeProps) {
  // ── Couleur selon le niveau de risque ───────────────────────
  const riskConfig = {
    low: {
      color:      "bg-green-100 text-green-800 border-green-200",
      bar:        "bg-green-500",
      icon:       <ShieldCheck className="w-4 h-4 text-green-600" />,
      label:      "Risque faible",
      barColor:   "text-green-600",
    },
    medium: {
      color:      "bg-yellow-100 text-yellow-800 border-yellow-200",
      bar:        "bg-yellow-500",
      icon:       <AlertTriangle className="w-4 h-4 text-yellow-600" />,
      label:      "Risque modéré",
      barColor:   "text-yellow-600",
    },
    high: {
      color:      "bg-red-100 text-red-800 border-red-200",
      bar:        "bg-red-500",
      icon:       <ShieldAlert className="w-4 h-4 text-red-600" />,
      label:      "Risque élevé",
      barColor:   "text-red-600",
    },
    unknown: {
      color:      "bg-gray-100 text-gray-600 border-gray-200",
      bar:        "bg-gray-400",
      icon:       <ShieldQuestion className="w-4 h-4 text-gray-500" />,
      label:      "Score inconnu",
      barColor:   "text-gray-500",
    },
  };

  const cfg       = riskConfig[score.risk_level] ?? riskConfig.unknown;
  const probPct   = Math.round(score.theft_probability * 100);

  // ── Badge compact (sans détails) ────────────────────────────
  if (!showDetails) {
    return (
      <Badge
        variant="outline"
        className={`flex items-center gap-1 px-2 py-1 text-xs font-medium border ${cfg.color}`}
      >
        {cfg.icon}
        {cfg.label}
      </Badge>
    );
  }

  // ── Card complète avec détails ───────────────────────────────
  return (
    <div className={`rounded-xl border p-4 space-y-3 ${cfg.color}`}>
      {/* En-tête */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold text-sm">
          {cfg.icon}
          Analyse IA — {cfg.label}
        </div>
        <span className={`text-lg font-bold ${cfg.barColor}`}>
          {probPct}%
        </span>
      </div>

      {/* Barre de probabilité de vol */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs opacity-75">
          <span>Probabilité de vol</span>
          <span>{score.theft_percent}</span>
        </div>
        <div className="w-full bg-white/50 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${cfg.bar}`}
            style={{ width: `${probPct}%` }}
          />
        </div>
      </div>

      {/* Détails */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-white/40 rounded-lg p-2">
          <div className="opacity-60">Anomalie détectée</div>
          <div className="font-semibold mt-0.5">
            {score.is_anomaly ? "⚠️ Oui" : "✅ Non"}
          </div>
        </div>
        <div className="bg-white/40 rounded-lg p-2">
          <div className="opacity-60">Score d'anomalie</div>
          <div className="font-semibold mt-0.5 font-mono">
            {score.anomaly_score.toFixed(3)}
          </div>
        </div>
      </div>

      {/* Modèles utilisés */}
      <div className="text-xs opacity-60 pt-1 border-t border-current/10">
        🤖 Random Forest + Isolation Forest · scikit-learn
      </div>
    </div>
  );
}


// ── Composant résultat complet de vérification ─────────────────────────────

import { IMEIVerifyResult } from "@/services/traceimei-api";

interface IMEIResultCardProps {
  result: IMEIVerifyResult;
}

export function IMEIResultCard({ result }: IMEIResultCardProps) {
  return (
    <div className="space-y-4 p-4 border rounded-2xl bg-card shadow-sm">
      {/* Statut principal */}
      <div className="flex items-center gap-3">
        {result.is_stolen ? (
          <div className="flex items-center gap-2 text-red-600 font-bold text-lg">
            <ShieldAlert className="w-6 h-6" />
            IMEI SIGNALÉ VOLÉ
          </div>
        ) : (
          <div className="flex items-center gap-2 text-green-600 font-bold text-lg">
            <CheckCircle className="w-6 h-6" />
            IMEI PROPRE
          </div>
        )}
      </div>

      {/* IMEI */}
      <div className="font-mono text-sm bg-muted px-3 py-2 rounded-lg">
        {result.imei}
      </div>

      {/* Score ML */}
      {result.ml_score && (
        <MLScoreBadge score={result.ml_score} showDetails={true} />
      )}

      {/* Infos du signalement si volé */}
      {result.db_record && result.is_stolen && (
        <div className="text-sm space-y-1 text-muted-foreground border-t pt-3">
          <p><span className="font-medium text-foreground">Marque :</span> {String(result.db_record.brand ?? "—")}</p>
          <p><span className="font-medium text-foreground">Modèle :</span> {String(result.db_record.model ?? "—")}</p>
          <p><span className="font-medium text-foreground">Lieu :</span> {String(result.db_record.location ?? "—")}</p>
          <p><span className="font-medium text-foreground">Signalé le :</span> {String(result.db_record.reported_at ?? "—").slice(0, 10)}</p>
        </div>
      )}

      {/* Timestamp */}
      <p className="text-xs text-muted-foreground">
        Vérifié le {new Date(result.checked_at).toLocaleString("fr-FR")}
      </p>
    </div>
  );
}
