import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MeraCodeLikhDo — AI Crop Monitoring & Irrigation Advisory | ISRO BAH 2026",
  description:
    "Satellite-driven precision agriculture platform. AI-powered crop type classification, " +
    "phenology-aware moisture stress detection, and irrigation advisory using fused " +
    "Sentinel-2, Landsat, and Sentinel-1 SAR data. Team MeraCodeLikhDo — ISRO BAH 2026.",
  keywords: [
    "ISRO", "satellite", "precision agriculture", "crop monitoring", "irrigation",
    "Sentinel-2", "SAR", "machine learning", "geospatial AI", "India",
  ],
  authors: [{ name: "Team MeraCodeLikhDo" }],
  openGraph: {
    title: "MeraCodeLikhDo — AI Crop & Irrigation Advisory",
    description: "Geospatial AI for satellite-driven precision agriculture. ISRO BAH 2026.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/favicon.ico" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossOrigin="" />
      </head>
      <body>{children}</body>
    </html>
  );
}
