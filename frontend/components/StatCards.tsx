"use client";

import { useAdvisorySummary, useStressSummary, useCropSummary } from "@/lib/hooks";

interface StatCardsProps {
  date: string;
  activeLayer: string;
}

export default function StatCards({ date, activeLayer }: StatCardsProps) {
  const { data: advSummary } = useAdvisorySummary(date);
  const { data: stressSummary } = useStressSummary(date);
  const { data: cropSummary } = useCropSummary();

  const irrigateNowPct = advSummary?.irrigate_now_pct ?? "…";
  const stressedPct = stressSummary?.stressed_area_pct ?? "…";
  const meanDeficit = advSummary?.mean_deficit_mm ?? "…";
  const modelAccuracy = cropSummary
    ? `${Math.round(cropSummary.model_accuracy * 100)}%`
    : "…";

  const cards = [
    {
      value: irrigateNowPct !== "…" ? `${irrigateNowPct}%` : "…",
      label: "Irrigate Now",
      trend: "⚠ Critical area",
      color: "#ef4444",
    },
    {
      value: stressedPct !== "…" ? `${stressedPct}%` : "…",
      label: "Stressed Area",
      trend: "Moderate + Severe",
      color: "#f97316",
    },
    {
      value: meanDeficit !== "…" ? `${meanDeficit} mm` : "…",
      label: "Mean Deficit (8-day)",
      trend: "FAO-56 ETc method",
      color: "#3b82f6",
    },
    {
      value: modelAccuracy,
      label: "Classifier Accuracy",
      trend: `κ=${cropSummary ? cropSummary.kappa.toFixed(2) : "…"}`,
      color: "#22c55e",
    },
  ];

  return (
    <div className="stat-cards">
      {cards.map((card) => (
        <div className="stat-card" key={card.label}>
          <div className="stat-value" style={{ color: card.color }}>
            {card.value}
          </div>
          <div className="stat-label">{card.label}</div>
          <div className="stat-trend" style={{ color: card.color }}>
            {card.trend}
          </div>
        </div>
      ))}
    </div>
  );
}
