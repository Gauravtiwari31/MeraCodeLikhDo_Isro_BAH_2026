"use client";

import type { LayerType } from "@/app/page";

interface SidebarProps {
  activeLayer: LayerType;
  onLayerChange: (layer: LayerType) => void;
}

const LAYERS = [
  {
    id: "advisory" as LayerType,
    label: "Irrigation Advisory",
    icon: "💧",
    description: "FAO-56 water deficit + advisory class",
    color: "#3b82f6",
  },
  {
    id: "stress" as LayerType,
    label: "Moisture Stress",
    icon: "🌿",
    description: "Stage-aware SAR+Optical fusion",
    color: "#22c55e",
  },
  {
    id: "crop" as LayerType,
    label: "Crop Type Map",
    icon: "🌾",
    description: "Foundation model + XGBoost classifier",
    color: "#a78bfa",
  },
];

const ADVISORY_LEGEND = [
  { color: "#22c55e", label: "No Action" },
  { color: "#fde047", label: "Monitor" },
  { color: "#f97316", label: "Irrigate Soon" },
  { color: "#ef4444", label: "Irrigate Now" },
];

const STRESS_LEGEND = [
  { color: "#22c55e", label: "No Stress" },
  { color: "#fde047", label: "Mild" },
  { color: "#f97316", label: "Moderate" },
  { color: "#ef4444", label: "Severe" },
];

const CROP_LEGEND = [
  { color: "#22c55e", label: "Paddy Rice" },
  { color: "#EAB308", label: "Wheat" },
  { color: "#f97316", label: "Cotton" },
  { color: "#84CC16", label: "Maize" },
  { color: "#a78bfa", label: "Sugarcane" },
  { color: "#FB923C", label: "Groundnut" },
  { color: "#34D399", label: "Vegetables" },
  { color: "#6B7280", label: "Non-Crop" },
];

export default function Sidebar({ activeLayer, onLayerChange }: SidebarProps) {
  const legend =
    activeLayer === "advisory"
      ? ADVISORY_LEGEND
      : activeLayer === "stress"
      ? STRESS_LEGEND
      : CROP_LEGEND;

  return (
    <aside className="sidebar">
      {/* Layer selector */}
      <div className="sidebar-section">
        <div className="sidebar-label">Map Layers</div>
        {LAYERS.map((layer) => (
          <button
            key={layer.id}
            className={`layer-btn ${activeLayer === layer.id ? "active" : ""}`}
            onClick={() => onLayerChange(layer.id)}
          >
            <span className="layer-dot" style={{ background: layer.color }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>{layer.icon} {layer.label}</div>
              <div style={{ fontSize: 10, color: "var(--color-text-dim)", marginTop: 1 }}>
                {layer.description}
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Legend */}
      <div className="sidebar-section">
        <div className="sidebar-label">Legend</div>
        <div className="legend">
          {legend.map((item) => (
            <div className="legend-item" key={item.label}>
              <span className="legend-swatch" style={{ background: item.color }} />
              {item.label}
            </div>
          ))}
        </div>
      </div>

      {/* USPs */}
      <div className="sidebar-section" style={{ flex: 1 }}>
        <div className="sidebar-label">USPs Active</div>
        {[
          { icon: "🤖", text: "Foundation Model Embeddings" },
          { icon: "🔀", text: "Stage-Level SAR+Optical Fusion" },
          { icon: "🎯", text: "MC Dropout Confidence" },
          { icon: "🌐", text: "Multilingual LLM Delivery" },
          { icon: "💧", text: "Canal Command Optimizer" },
          { icon: "🛰️", text: "NISAR-Ready Adapter" },
          { icon: "📋", text: "PMFBY Audit Trail" },
          { icon: "🆓", text: "Zero License Cost" },
        ].map(({ icon, text }) => (
          <div
            key={text}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 11,
              color: "var(--color-text-muted)",
              marginBottom: 6,
            }}
          >
            <span style={{ fontSize: 13 }}>{icon}</span> {text}
          </div>
        ))}
      </div>

      {/* Team */}
      <div
        className="sidebar-section"
        style={{ marginTop: "auto" }}
      >
        <div className="sidebar-label">Team MeraCodeLikhDo</div>
        {[
          "Gaurav Tiwari · Leader",
          "Shubham Singh · Data Eng",
          "Prajjwal Singh · AI/ML",
          "Krishna Gupta · Full-Stack",
        ].map((member) => (
          <div
            key={member}
            style={{ fontSize: 11, color: "var(--color-text-muted)", marginBottom: 4 }}
          >
            {member}
          </div>
        ))}
      </div>
    </aside>
  );
}
