"use client";

import type { RiskBand, TrustState } from "@/lib/api";
import { useLocale } from "@/lib/locale";

const STYLE: Record<RiskBand, string> = {
  insufficient_data: "bg-risk-insufficient/10 text-risk-insufficient",
  stable: "bg-risk-stable/10 text-risk-stable",
  watch: "bg-risk-watch/10 text-risk-watch",
  high_risk: "bg-risk-high/10 text-risk-high",
};

export function RiskBadge({ band }: { band: RiskBand }) {
  const { t } = useLocale();
  return <span className={`risk-pill ${STYLE[band]}`}>{t.risk[band]}</span>;
}

const TRUST_STYLE: Record<TrustState, string> = {
  alert: "bg-risk-high/10 text-risk-high",
  watch: "bg-risk-watch/10 text-risk-watch",
  verify_data: "bg-accent/10 text-accent",
  abstain: "bg-risk-insufficient/10 text-risk-insufficient",
};

export function TrustBadge({ state }: { state: TrustState }) {
  const { t } = useLocale();
  return <span className={`risk-pill ${TRUST_STYLE[state]}`}>TrustGate: {t.trust[state]}</span>;
}
