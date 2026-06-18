"use client";

import { useState, useEffect } from "react";
import { generateAdvisoryText } from "@/lib/api";
import type { LayerType } from "@/app/page";

interface InfoPanelProps {
  feature: any;
  activeLayer: LayerType;
  onClose: () => void;
}

const CONFIDENCE_CLASS: Record<number, string> = {
  0: "confidence-high",
  1: "confidence-medium",
  2: "confidence-low",
};

const CONFIDENCE_LABEL: Record<number, string> = {
  0: "HIGH",
  1: "MEDIUM",
  2: "LOW",
};

// SHAP feature importance (simulated for demo)
const SHAP_FEATURES = [
  { name: "VCI",          sign: 1,  value: 0.32 },
  { name: "NDVI anomaly", sign: -1, value: 0.28 },
  { name: "SAR VH/VV",   sign: -1, value: 0.18 },
  { name: "NDWI",        sign: 1,  value: 0.12 },
  { name: "EVI",         sign: 1,  value: 0.07 },
];

export default function InfoPanel({ feature, activeLayer, onClose }: InfoPanelProps) {
  const p = feature?.properties ?? {};
  const [advisory, setAdvisory] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (activeLayer !== "advisory" || !p.advisory_label) return;
    setLoading(true);
    generateAdvisoryText({
      advisory_class: p.advisory_label?.toLowerCase().replace(/ /g, "_") ?? "monitor",
      crop_name: "paddy_rice",
      growth_stage: p.growth_stage ?? "vegetative",
      deficit_mm: p.deficit_mm ?? 20,
      confidence_label: CONFIDENCE_LABEL[p.confidence_flag ?? 0],
    })
      .then(setAdvisory)
      .catch(() => setAdvisory(null))
      .finally(() => setLoading(false));
  }, [feature, activeLayer]);

  return (
    <div className="info-panel fade-in">
      {/* Header */}
      <div className="info-panel-header">
        <span>📊 Pixel Detail</span>
        <div style={{ flex: 1 }} />
        <span
          style={{ cursor: "pointer", fontSize: 16, color: "var(--color-text-muted)" }}
          onClick={onClose}
          title="Close"
        >
          ×
        </span>
      </div>

      <div className="info-panel-body">
        {/* Date */}
        {p.date && (
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted">Date</span>
            <span className="text-xs font-bold" style={{ color: "var(--color-accent-green)" }}>{p.date}</span>
          </div>
        )}

        {/* Advisory layer */}
        {activeLayer === "advisory" && (
          <>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted">Advisory</span>
              <span
                className="text-xs font-bold"
                style={{ color: p.color ?? "#22c55e" }}
              >
                {p.advisory_label ?? "—"}
              </span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted">Deficit (8-day)</span>
              <span className="text-xs font-bold">{p.deficit_mm ?? 0} mm</span>
            </div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-muted">Confidence</span>
              <span className={`confidence-badge ${CONFIDENCE_CLASS[p.confidence_flag ?? 0]}`}>
                {CONFIDENCE_LABEL[p.confidence_flag ?? 0]}
              </span>
            </div>
            {p.outlet_id && (
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-muted">Canal Outlet</span>
                <span className="text-xs font-bold" style={{ color: "var(--color-primary)" }}>{p.outlet_id}</span>
              </div>
            )}
            {p.record_id && (
              <div className="mb-3" style={{ paddingTop: 8, borderTop: "1px solid var(--color-border)" }}>
                <div className="text-xs text-dim" style={{ marginBottom: 3 }}>PMFBY Audit Record</div>
                <div className="text-xs" style={{ fontFamily: "monospace", color: "var(--color-accent-violet)" }}>{p.record_id}</div>
              </div>
            )}
            {/* Multilingual advisory */}
            {loading && <div className="flex items-center gap-2 text-xs text-muted"><div className="spinner" />Generating advisory…</div>}
            {advisory && (
              <div style={{ paddingTop: 10, borderTop: "1px solid var(--color-border)" }}>
                <div className="text-xs text-dim mb-2">🌐 Multilingual Advisory (LLM)</div>
                <div className="advisory-card" style={{ padding: "10px 10px 10px 14px" }}>
                  <div className="advisory-card-severity" style={{ background: p.color ?? "#22c55e" }} />
                  <div style={{ paddingLeft: 4 }}>
                    <div className="advisory-lang-tag">🇮🇳 Hindi</div>
                    <div style={{ fontSize: 12, lineHeight: 1.6 }}>{advisory.messages?.hi}</div>
                    <div className="advisory-lang-tag" style={{ marginTop: 8 }}>🇬🇧 English</div>
                    <div style={{ fontSize: 11, color: "var(--color-text-muted)", lineHeight: 1.5 }}>{advisory.messages?.en}</div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* Stress layer */}
        {activeLayer === "stress" && (
          <>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted">Stress Level</span>
              <span className="text-xs font-bold" style={{ color: p.color }}>
                {p.stress_label ?? "—"}
              </span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted">Stress Index</span>
              <span className="text-xs font-bold">{p.stress_index?.toFixed(3) ?? 0}</span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted">Growth Stage</span>
              <span className="text-xs font-bold" style={{ color: "var(--color-accent-amber)" }}>
                {p.growth_stage?.replace(/_/g, " ") ?? "—"}
              </span>
            </div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-muted">Uncertainty</span>
              <span className="text-xs font-bold">{p.uncertainty?.toFixed(3) ?? 0}</span>
            </div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-muted">Confidence</span>
              <span className={`confidence-badge ${CONFIDENCE_CLASS[p.confidence_flag ?? 0]}`}>
                {CONFIDENCE_LABEL[p.confidence_flag ?? 0]}
              </span>
            </div>
            {/* SHAP explainability */}
            <div style={{ paddingTop: 10, borderTop: "1px solid var(--color-border)" }}>
              <div className="text-xs text-dim mb-2">🔍 SHAP Feature Attribution</div>
              {SHAP_FEATURES.map((f) => (
                <div className="shap-row" key={f.name}>
                  <div className="shap-feature">{f.name}</div>
                  <div className="shap-bar-track">
                    {f.sign > 0 ? (
                      <div className="shap-bar-pos" style={{ width: `${f.value * 100}%` }} />
                    ) : (
                      <div className="shap-bar-neg" style={{ width: `${f.value * 100}%` }} />
                    )}
                  </div>
                  <div className="shap-value" style={{ color: f.sign > 0 ? "#22c55e" : "#ef4444" }}>
                    {f.sign > 0 ? "+" : "−"}{f.value.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Crop layer */}
        {activeLayer === "crop" && (
          <>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted">Crop Type</span>
              <span className="text-xs font-bold" style={{ color: p.color }}>
                {p.crop_name?.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()) ?? "—"}
              </span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted">Confidence</span>
              <span className="text-xs font-bold">{p.confidence ? `${Math.round(p.confidence * 100)}%` : "—"}</span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted">Method</span>
              <span className="text-xs text-muted">Foundation + XGBoost</span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted">Season</span>
              <span className="text-xs font-bold">{p.season ?? "kharif_2025"}</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
