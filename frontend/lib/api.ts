// API client for MeraCodeLikhDo backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchCropMap(season = "kharif_2025") {
  const res = await fetch(`${API_BASE}/api/v1/crop-map/?season=${season}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Crop map fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchStressMap(date: string) {
  const res = await fetch(`${API_BASE}/api/v1/stress/?date=${date}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Stress map fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchAdvisoryMap(date: string) {
  const res = await fetch(`${API_BASE}/api/v1/advisory/map?date=${date}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Advisory map fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchCanalOutlets(date: string) {
  const res = await fetch(`${API_BASE}/api/v1/advisory/canal-outlets?date=${date}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Canal outlets fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchNdviTimeseries(row: number, col: number) {
  const res = await fetch(`${API_BASE}/api/v1/pipeline/ndvi-timeseries?row=${row}&col=${col}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`NDVI time series fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchPipelineStatus() {
  const res = await fetch(`${API_BASE}/api/v1/pipeline/status`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Pipeline status fetch failed: ${res.status}`);
  return res.json();
}

export async function generateAdvisoryText(params: {
  advisory_class: string;
  crop_name: string;
  growth_stage: string;
  deficit_mm: number;
  confidence_label: string;
}) {
  const res = await fetch(`${API_BASE}/api/v1/nlg/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`NLG generate failed: ${res.status}`);
  return res.json();
}

export async function fetchAdvisorySummary(date: string) {
  const res = await fetch(`${API_BASE}/api/v1/advisory/summary?date=${date}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Advisory summary fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchStressSummary(date: string) {
  const res = await fetch(`${API_BASE}/api/v1/stress/summary?date=${date}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Stress summary fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchCropSummary() {
  const res = await fetch(`${API_BASE}/api/v1/crop-map/summary`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Crop summary fetch failed: ${res.status}`);
  return res.json();
}
