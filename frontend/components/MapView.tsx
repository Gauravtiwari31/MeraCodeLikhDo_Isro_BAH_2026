"use client";

import { useEffect, useState, useRef } from "react";
import type { LayerType } from "@/app/page";
import { useLayerData } from "@/lib/hooks";

// Dynamically import react-leaflet components to avoid SSR window issues
import dynamic from "next/dynamic";
const MapContainer = dynamic(() => import("react-leaflet").then(mod => mod.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import("react-leaflet").then(mod => mod.TileLayer), { ssr: false });
const GeoJSON = dynamic(() => import("react-leaflet").then(mod => mod.GeoJSON), { ssr: false });
const Polygon = dynamic(() => import("react-leaflet").then(mod => mod.Polygon), { ssr: false });
const Pane = dynamic(() => import("react-leaflet").then(mod => mod.Pane), { ssr: false });

const MAP_CENTER: [number, number] = [30.75, 76.25]; // Lat, Lng for Bhakra Canal Command
const MAP_ZOOM = 10;

// Bbox for Bhakra Canal Command
const AOI_COORDS: [number, number][] = [
  [30.0, 75.5], [30.0, 77.0], [31.5, 77.0], [31.5, 75.5]
];

interface MapViewProps {
  activeLayer: LayerType;
  selectedDate: string;
  onFeatureClick: (feature: any) => void;
}

export default function MapView({ activeLayer, selectedDate, onFeatureClick }: MapViewProps) {
  const { data: layerData, loading } = useLayerData(activeLayer, selectedDate);
  const geoJsonRef = useRef<any>(null);

  // Re-render GeoJSON when data changes by changing key
  const geoJsonKey = layerData ? `${activeLayer}-${selectedDate}-${layerData.features?.length || 0}` : "empty";

  // Leaflet styles
  const styleFeature = (feature: any) => {
    return {
      fillColor: feature.properties.color || "#cccccc",
      weight: 0, // Remove stroke to make it look like a continuous raster
      opacity: 0,
      fillOpacity: 0.85, // Higher opacity for more solid color
    };
  };

  const onEachFeature = (feature: any, layer: any) => {
    layer.on({
      mouseover: (e: any) => {
        const target = e.target;
        target.setStyle({
          weight: 2,
          color: "#ffffff",
          fillOpacity: 0.9,
        });
        target.bringToFront();
      },
      mouseout: (e: any) => {
        geoJsonRef.current?.resetStyle(e.target);
      },
      click: () => {
        onFeatureClick(feature);
      },
    });
  };

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      {/* Wait for client mount to render map */}
      {typeof window !== "undefined" && (
        <MapContainer
          center={MAP_CENTER}
          zoom={MAP_ZOOM}
          style={{ width: "100%", height: "100%" }}
          zoomControl={false}
          attributionControl={false}
        >
          {/* CartoDB Dark Matter free tiles */}
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution="&copy; OpenStreetMap contributors &copy; CARTO"
          />

          <Pane name="aoi" style={{ zIndex: 399 }}>
            <Polygon 
              positions={AOI_COORDS} 
              pathOptions={{ color: "#3b82f6", weight: 2, dashArray: "4 2", fill: false }} 
            />
          </Pane>

          <Pane name="data" style={{ zIndex: 400 }}>
            {layerData && layerData.features && layerData.features.length > 0 && (
              <GeoJSON
                key={geoJsonKey}
                ref={geoJsonRef}
                data={layerData}
                style={styleFeature}
                onEachFeature={onEachFeature}
              />
            )}
          </Pane>
        </MapContainer>
      )}

      {/* Loading overlay */}
      {loading && (
        <div
          style={{
            position: "absolute",
            top: 12,
            left: 12,
            background: "rgba(10,22,40,0.85)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            padding: "7px 12px",
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 12,
            color: "var(--color-text-muted)",
            zIndex: 1000,
          }}
        >
          <div className="spinner" />
          Fetching satellite data…
        </div>
      )}

      {/* Map overlay — data info */}
      {!loading && layerData?.metadata && (
        <div
          style={{
            position: "absolute",
            top: 12,
            left: 12,
            background: "rgba(10,22,40,0.85)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            padding: "8px 12px",
            fontSize: 11,
            color: "var(--color-text-muted)",
            backdropFilter: "blur(8px)",
            maxWidth: 260,
            zIndex: 1000,
          }}
        >
          <div style={{ fontWeight: 700, color: "var(--color-primary)", marginBottom: 4 }}>
            {activeLayer === "advisory" ? "💧 Irrigation Advisory" :
             activeLayer === "stress"   ? "🌿 Moisture Stress"      :
                                          "🌾 Crop Type Map"}
          </div>
          <div>{layerData.metadata.aoi?.replace(/_/g, " ")}</div>
          {layerData.metadata.date && (
            <div style={{ color: "var(--color-accent-green)" }}>{layerData.metadata.date}</div>
          )}
          {layerData.metadata.simulated && (
            <div style={{ color: "var(--color-accent-amber)", marginTop: 4, fontSize: 10 }}>
              ⚠ Simulated data — live pipeline ready with GEE credentials
            </div>
          )}
        </div>
      )}
    </div>
  );
}
