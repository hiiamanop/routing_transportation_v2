"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface TaggedPoint {
  id: string;
  name: string;
  lat: number;
  lon: number;
  accuracy: number;
}

interface StoredSession {
  points: TaggedPoint[];
  status: "session" | "review";
}

type Status = "idle" | "session" | "review";

const ACCURACY_WARNING_METERS = 2.5;

function storageKey(routeName: string) {
  return `tagging_session_v1_${routeName}`;
}

// Hook mandiri: mengelola satu sesi tagging GPS utk SATU koridor (routeName).
// Dipanggil ulang dgn routeName berbeda saat user ganti koridor di halaman
// Jaringan -- state di-reset otomatis krn key localStorage beda per koridor.
export function useTaggingSession(routeName: string | null) {
  const [status, setStatus] = useState<Status>("idle");
  const [points, setPoints] = useState<TaggedPoint[]>([]);
  const [currentPosition, setCurrentPosition] = useState<
    { lat: number; lon: number; accuracy: number } | null
  >(null);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [hasSavedSession, setHasSavedSession] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const watchIdRef = useRef<number | null>(null);

  // Cek localStorage tiap kali koridor berganti -- tawarkan resume kalau ada
  // sesi tersimpan sebelumnya utk koridor itu.
  useEffect(() => {
    setStatus("idle");
    setPoints([]);
    setCurrentPosition(null);
    setGeoError(null);
    setSaveError(null);
    if (!routeName) {
      setHasSavedSession(false);
      return;
    }
    const raw = localStorage.getItem(storageKey(routeName));
    setHasSavedSession(!!raw);
  }, [routeName]);

  // Simpan progres ke localStorage tiap kali daftar titik berubah, SELAMA
  // sesi berjalan/direview -- supaya refresh/HP terkunci di tengah
  // perjalanan tidak menghilangkan hasil keliling.
  useEffect(() => {
    if (!routeName || status === "idle") return;
    const payload: StoredSession = { points, status };
    localStorage.setItem(storageKey(routeName), JSON.stringify(payload));
  }, [routeName, points, status]);

  const stopWatch = useCallback(() => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
  }, []);

  useEffect(() => stopWatch, [stopWatch]);

  const beginWatch = useCallback(() => {
    if (!("geolocation" in navigator)) {
      setGeoError("Browser ini tidak mendukung geolocation.");
      return;
    }
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        setGeoError(null);
        setCurrentPosition({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
      },
      (err) => setGeoError(`Gagal mengakses lokasi: ${err.message}`),
      { enableHighAccuracy: true, maximumAge: 0, timeout: 15000 }
    );
  }, []);

  const startSession = useCallback(() => {
    setPoints([]);
    setStatus("session");
    beginWatch();
  }, [beginWatch]);

  const resumeSession = useCallback(() => {
    if (!routeName) return;
    const raw = localStorage.getItem(storageKey(routeName));
    if (!raw) return;
    const stored: StoredSession = JSON.parse(raw);
    setPoints(stored.points);
    setStatus(stored.status);
    if (stored.status === "session") beginWatch();
  }, [routeName, beginWatch]);

  const discardSession = useCallback(() => {
    if (routeName) localStorage.removeItem(storageKey(routeName));
    setHasSavedSession(false);
    setPoints([]);
    setStatus("idle");
    stopWatch();
  }, [routeName, stopWatch]);

  const tagCurrentPosition = useCallback(() => {
    if (!currentPosition) return;
    setPoints((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        name: `Halte ${prev.length + 1}`,
        lat: currentPosition.lat,
        lon: currentPosition.lon,
        accuracy: currentPosition.accuracy,
      },
    ]);
  }, [currentPosition]);

  const addManualPoint = useCallback((lat: number, lon: number) => {
    setPoints((prev) => [
      ...prev,
      { id: crypto.randomUUID(), name: `Halte ${prev.length + 1}`, lat, lon, accuracy: 0 },
    ]);
  }, []);

  const removePoint = useCallback((id: string) => {
    setPoints((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const renamePoint = useCallback((id: string, name: string) => {
    setPoints((prev) => prev.map((p) => (p.id === id ? { ...p, name } : p)));
  }, []);

  const movePoint = useCallback((id: string, direction: "up" | "down") => {
    setPoints((prev) => {
      const index = prev.findIndex((p) => p.id === id);
      const swapWith = direction === "up" ? index - 1 : index + 1;
      if (index === -1 || swapWith < 0 || swapWith >= prev.length) return prev;
      const next = [...prev];
      [next[index], next[swapWith]] = [next[swapWith], next[index]];
      return next;
    });
  }, []);

  const finishSession = useCallback(() => {
    setStatus("review");
    stopWatch();
  }, [stopWatch]);

  const backToSession = useCallback(() => {
    setStatus("session");
    beginWatch();
  }, [beginWatch]);

  const save = useCallback(async (): Promise<boolean> => {
    if (!routeName || points.length < 2) {
      setSaveError("Minimal 2 titik dibutuhkan sebelum menyimpan.");
      return false;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const res = await fetch(
        `/api/network/corridor/${encodeURIComponent(routeName)}/stops`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            stops: points.map((p) => ({ name: p.name, lat: p.lat, lon: p.lon })),
          }),
        }
      );
      const data = await res.json();
      if (!res.ok || !data.success) {
        setSaveError(data.error || "Gagal menyimpan ke server.");
        return false;
      }
      localStorage.removeItem(storageKey(routeName));
      setHasSavedSession(false);
      setPoints([]);
      setStatus("idle");
      return true;
    } catch {
      setSaveError("Gagal menghubungi server.");
      return false;
    } finally {
      setSaving(false);
    }
  }, [routeName, points]);

  return {
    status,
    points,
    currentPosition,
    geoError,
    hasSavedSession,
    saving,
    saveError,
    startSession,
    resumeSession,
    discardSession,
    tagCurrentPosition,
    addManualPoint,
    removePoint,
    renamePoint,
    movePoint,
    finishSession,
    backToSession,
    save,
    accuracyWarningMeters: ACCURACY_WARNING_METERS,
  };
}
