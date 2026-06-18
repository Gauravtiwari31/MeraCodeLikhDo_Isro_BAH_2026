"use client";

import { usePipelineStatus } from "@/lib/hooks";

export default function Topbar() {
  const { status } = usePipelineStatus();
  const isOnline = status?.status === "operational";

  return (
    <header className="topbar">
      <div className="topbar-logo">
        <div style={{ width: 32, height: 32, background: "var(--color-primary)", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: 18 }}>🛰️</span>
        </div>
        <div>
          <div style={{ fontWeight: 800, letterSpacing: 0.5, fontSize: 18 }}>MeraCodeLikhDo</div>
          <div style={{ fontSize: 11, color: "var(--color-text-dim)", letterSpacing: 1 }}>AI CROP & IRRIGATION ADVISORY</div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div className="flex items-center gap-2">
            <span style={{ color: "var(--color-accent-red)" }}>📍</span>
            <select style={{ background: "transparent", border: "none", color: "white", fontWeight: 600, fontSize: 14, outline: "none", cursor: "pointer", padding: 0 }}>
              <option value="punjab" style={{ background: "var(--color-surface)" }}>Punjab (Bhakra Canal Pilot)</option>
              <option value="maharashtra" disabled style={{ background: "var(--color-surface)", color: "gray" }}>Maharashtra (Pending GEE Sync)</option>
              <option value="karnataka" disabled style={{ background: "var(--color-surface)", color: "gray" }}>Karnataka (Pending GEE Sync)</option>
            </select>
          </div>
          <div style={{ fontSize: 11, color: "var(--color-text-dim)" }}>
            Kharif 2025 · 87,500 ha
          </div>
        </div>
      </div>

      <div className="topbar-spacer" />

      {/* Data sources */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {["Sentinel-2", "Sentinel-1 SAR", "EOS-04 Ready", "NISAR Adapter"].map((src) => (
          <span
            key={src}
            style={{
              fontSize: 10,
              fontWeight: 600,
              padding: "3px 8px",
              background: "var(--color-surface-2)",
              border: "1px solid var(--color-border)",
              borderRadius: 100,
              color: "var(--color-text-muted)",
            }}
          >
            {src}
          </span>
        ))}
      </div>

      {/* Status badge */}
      <div className="topbar-badge" style={{ marginLeft: 12 }}>
        <span className="topbar-badge-dot" />
        {isOnline ? "Pipeline Active" : "Demo Mode"}
      </div>

      {/* ISRO BAH badge */}
      <div
        style={{
          marginLeft: 10,
          padding: "5px 10px",
          background: "rgba(167,139,250,0.12)",
          border: "1px solid rgba(167,139,250,0.3)",
          borderRadius: "var(--radius-sm)",
          fontSize: 11,
          fontWeight: 700,
          color: "var(--color-accent-violet)",
        }}
      >
        ISRO BAH 2026
      </div>
    </header>
  );
}
