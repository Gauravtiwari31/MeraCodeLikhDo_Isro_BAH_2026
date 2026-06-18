"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import Topbar from "@/components/Topbar";
import Sidebar from "@/components/Sidebar";
import StatCards from "@/components/StatCards";
import TimeSlider from "@/components/TimeSlider";
import InfoPanel from "@/components/InfoPanel";
import BottomPanel from "@/components/BottomPanel";

// Dynamically import map (avoids SSR issues with Mapbox)
const MapView = dynamic(() => import("@/components/MapView"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        flex: 1,
        background: "#050b14",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} />
      <p className="text-muted text-sm">Loading satellite map…</p>
    </div>
  ),
});

export type LayerType = "crop" | "stress" | "advisory";

const COMPOSITE_DATES = [
  "2025-06-01","2025-06-09","2025-06-17","2025-06-25",
  "2025-07-03","2025-07-11","2025-07-19","2025-07-27",
  "2025-08-04","2025-08-12","2025-08-20","2025-08-28",
  "2025-09-05","2025-09-13","2025-09-21","2025-09-29",
  "2025-10-07","2025-10-15","2025-10-23","2025-10-31",
];

export default function DashboardPage() {
  const [activeLayer, setActiveLayer] = useState<LayerType>("advisory");
  const [selectedDateIdx, setSelectedDateIdx] = useState(COMPOSITE_DATES.length - 1);
  const [selectedFeature, setSelectedFeature] = useState<any>(null);
  const [bottomTab, setBottomTab] = useState<"canal" | "advisory" | "ndvi">("canal");

  const selectedDate = COMPOSITE_DATES[selectedDateIdx];

  const handleFeatureClick = useCallback((feature: any) => {
    setSelectedFeature(feature);
  }, []);

  return (
    <div className="app-layout">
      {/* ── Top bar ── */}
      <Topbar />

      {/* ── Stat cards ── */}
      <StatCards date={selectedDate} activeLayer={activeLayer} />

      {/* ── Main body: sidebar + map ── */}
      <div className="dashboard-layout" style={{ flex: 1, minHeight: 0 }}>
        <Sidebar
          activeLayer={activeLayer}
          onLayerChange={setActiveLayer}
        />

        <div className="map-container">
          <MapView
            activeLayer={activeLayer}
            selectedDate={selectedDate}
            onFeatureClick={handleFeatureClick}
          />

          {/* Time slider */}
          <TimeSlider
            dates={COMPOSITE_DATES}
            selectedIdx={selectedDateIdx}
            onChange={setSelectedDateIdx}
          />

          {/* Info panel (click-through) */}
          {selectedFeature && (
            <InfoPanel
              feature={selectedFeature}
              activeLayer={activeLayer}
              onClose={() => setSelectedFeature(null)}
            />
          )}
        </div>
      </div>

      {/* ── Bottom panel: canal optimizer, advisory, NDVI ── */}
      <BottomPanel
        activeTab={bottomTab}
        onTabChange={setBottomTab}
        date={selectedDate}
      />
    </div>
  );
}
