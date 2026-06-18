"use client";

import { useCanalOutlets } from "@/lib/hooks";

interface BottomPanelProps {
  activeTab: "canal" | "advisory" | "ndvi";
  onTabChange: (tab: "canal" | "advisory" | "ndvi") => void;
  date: string;
}

function downloadCSV(data: any[], filename: string) {
  if (!data.length) return;
  const headers = Object.keys(data[0]).join(",");
  const rows = data.map((row) => Object.values(row).join(",")).join("\n");
  const blob = new Blob([`${headers}\n${rows}`], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function BottomPanel({ activeTab, onTabChange, date }: BottomPanelProps) {
  const { data: canalData, loading } = useCanalOutlets(date);
  const outlets: any[] = canalData?.outlets ?? [];
  const maxScore = outlets.length ? Math.max(...outlets.map((o) => o.priority_score), 1) : 1;

  return (
    <div className="bottom-panel">
      {/* Tab bar */}
      <div className="bottom-panel-tabs">
        {[
          { id: "canal" as const, label: "💧 Canal Command Optimizer" },
          { id: "advisory" as const, label: "📡 Advisory Summary" },
          { id: "ndvi" as const, label: "📈 NDVI Profile" },
        ].map((tab) => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => onTabChange(tab.id)}
            id={`tab-${tab.id}`}
          >
            {tab.label}
          </button>
        ))}

        <div style={{ flex: 1 }} />

        {/* Export */}
        <button
          className="btn btn-outline"
          style={{ margin: "5px 0", fontSize: 11, padding: "5px 12px" }}
          onClick={() => {
            if (activeTab === "canal" && outlets.length) {
              downloadCSV(outlets, `canal_priorities_${date}.csv`);
            }
          }}
          title="Export current data as CSV"
          id="export-csv-btn"
        >
          ⬇ Export CSV
        </button>
      </div>

      {/* Tab content */}
      <div className="tab-content">
        {/* ── Canal Command Optimizer (USP 4.5) ── */}
        {activeTab === "canal" && (
          <div className="fade-in">
            <div className="text-xs text-muted mb-2">
              Canal outlet priority ranking — {date} · Sorted by irrigation urgency (highest first)
            </div>
            {loading && <div className="flex items-center gap-2 text-xs text-muted"><div className="spinner" />Loading…</div>}
            {outlets.map((outlet, idx) => (
              <div key={outlet.outlet_id} className="canal-bar-item">
                <div style={{ width: 20, fontWeight: 700, fontSize: 11, color: "var(--color-primary)" }}>
                  #{idx + 1}
                </div>
                <div className="canal-bar-label" title={outlet.outlet_name}>
                  {outlet.outlet_name}
                </div>
                <div className="canal-bar-track">
                  <div
                    className="canal-bar-fill"
                    style={{ width: `${(outlet.priority_score / maxScore) * 100}%` }}
                  />
                </div>
                <div className="canal-bar-value">{outlet.priority_score.toFixed(0)}</div>
                <div
                  style={{
                    fontSize: 10,
                    color: "var(--color-accent-red)",
                    width: 50,
                    textAlign: "right",
                  }}
                >
                  {outlet.irrigate_now_pct}%🔴
                </div>
                <div
                  style={{
                    fontSize: 10,
                    color: "var(--color-text-dim)",
                    width: 70,
                    textAlign: "right",
                  }}
                >
                  {outlet.mean_deficit_mm} mm
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Advisory Summary ── */}
        {activeTab === "advisory" && (
          <AdvisorySummaryTab date={date} />
        )}

        {/* ── NDVI Profile ── */}
        {activeTab === "ndvi" && (
          <div className="fade-in" style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", textAlign: "center" }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📈</div>
              <div>Click any pixel on the map to view its NDVI time series</div>
              <div className="text-xs text-dim" style={{ marginTop: 4 }}>
                Showing historical vs. current season NDVI + phenological stage markers
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AdvisorySummaryTab({ date }: { date: string }) {
  const { useAdvisorySummary } = require("@/lib/hooks");
  const { data, loading } = useAdvisorySummary(date);
  
  const pctData = data?.distribution_pct || {
    no_action: 0, monitor: 0, irrigate_soon: 0, irrigate_now: 0
  };

  const chartData = [
    { label: "No Action",      color: "#22c55e", pct: pctData.no_action },
    { label: "Monitor",        color: "#fde047", pct: pctData.monitor },
    { label: "Irrigate Soon",  color: "#f97316", pct: pctData.irrigate_soon },
    { label: "Irrigate Now",   color: "#ef4444", pct: pctData.irrigate_now },
  ];

  return (
    <div className="fade-in" style={{ display: "flex", gap: 24 }}>
      <div style={{ flex: 1 }}>
        <div className="text-xs text-muted mb-2">
          Advisory distribution for {date} — FAO-56 ETc + Water Balance
        </div>
        {loading && <div className="flex items-center gap-2 text-xs text-muted"><div className="spinner" />Loading…</div>}
        {!loading && chartData.map((item) => (
          <div key={item.label} className="canal-bar-item" style={{ marginBottom: 10 }}>
            <div className="canal-bar-label">
              <span style={{ color: item.color }}>■</span> {item.label}
            </div>
            <div className="canal-bar-track">
              <div style={{ height: "100%", width: `${item.pct}%`, background: item.color, borderRadius: 4 }} />
            </div>
            <div className="canal-bar-value" style={{ color: item.color }}>{item.pct.toFixed(1)}%</div>
          </div>
        ))}
      </div>
      <div style={{ flex: 1, paddingLeft: 16, borderLeft: "1px solid var(--color-border)" }}>
        <div className="text-xs text-muted mb-2">Methodology</div>
        <div style={{ fontSize: 11, color: "var(--color-text-muted)", lineHeight: 1.8 }}>
          <div>📐 <b>FAO-56 Kc method</b> for ETc estimation</div>
          <div>🌧 IMD rainfall for effective precipitation</div>
          <div>📡 ERA5/CHIRPS reference ET</div>
          <div>🎯 Stage-specific deficit thresholds</div>
          <div>🛡 MC Dropout confidence flags on each cell</div>
          <div>📋 PMFBY audit trail: timestamped records</div>
        </div>
      </div>
    </div>
  );
}
