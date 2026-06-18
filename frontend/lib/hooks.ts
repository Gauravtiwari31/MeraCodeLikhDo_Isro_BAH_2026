// Custom React hooks for data fetching

import { useState, useEffect } from "react";
import {
  fetchPipelineStatus,
  fetchCropMap,
  fetchStressMap,
  fetchAdvisoryMap,
  fetchCanalOutlets,
  fetchAdvisorySummary,
  fetchStressSummary,
  fetchCropSummary,
} from "./api";

export function usePipelineStatus() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPipelineStatus()
      .then(setStatus)
      .catch(() => setStatus({ status: "backend_offline" }))
      .finally(() => setLoading(false));
  }, []);

  return { status, loading };
}

export function useLayerData(activeLayer: string, date: string) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const fetcher =
      activeLayer === "crop"
        ? fetchCropMap()
        : activeLayer === "stress"
        ? fetchStressMap(date)
        : fetchAdvisoryMap(date);

    fetcher
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [activeLayer, date]);

  return { data, loading, error };
}

export function useCanalOutlets(date: string) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchCanalOutlets(date)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [date]);

  return { data, loading };
}

export function useAdvisorySummary(date: string) {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    fetchAdvisorySummary(date)
      .then(setData)
      .catch(() => setData(null));
  }, [date]);
  return { data };
}

export function useStressSummary(date: string) {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    fetchStressSummary(date)
      .then(setData)
      .catch(() => setData(null));
  }, [date]);
  return { data };
}

export function useCropSummary() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    fetchCropSummary()
      .then(setData)
      .catch(() => setData(null));
  }, []);
  return { data };
}
