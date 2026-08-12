"use client";

import { useState } from "react";
import type { useTaggingSession } from "./useTaggingSession";

type TaggingHook = ReturnType<typeof useTaggingSession>;

export default function TaggingPanel({
  routeName,
  tagging,
  onExit,
}: {
  routeName: string;
  tagging: TaggingHook;
  onExit: () => void;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);

  if (tagging.status === "idle") {
    return (
      <div className="space-y-2">
        <p className="text-xs text-[var(--gmaps-text-secondary)]">
          Koridor: <strong>{routeName}</strong>
        </p>
        {tagging.hasSavedSession && (
          <div className="rounded-md bg-[var(--gmaps-surface-hover)] p-2 text-xs">
            <p className="mb-2">Ada sesi tagging tersimpan untuk koridor ini.</p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={tagging.resumeSession}
                className="flex-1 rounded-md bg-[var(--gmaps-blue)] px-2 py-1.5 font-medium text-white"
              >
                Lanjutkan
              </button>
              <button
                type="button"
                onClick={tagging.discardSession}
                className="flex-1 rounded-md border border-[var(--gmaps-border)] px-2 py-1.5"
              >
                Mulai Ulang
              </button>
            </div>
          </div>
        )}
        {!tagging.hasSavedSession && (
          <button
            type="button"
            onClick={tagging.startSession}
            className="w-full rounded-md bg-[var(--gmaps-blue)] px-3 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Mulai Sesi Tagging
          </button>
        )}
        <button
          type="button"
          onClick={onExit}
          className="w-full rounded-md border border-[var(--gmaps-border)] px-3 py-1.5 text-sm text-[var(--gmaps-text-secondary)]"
        >
          Keluar Mode Edit
        </button>
      </div>
    );
  }

  const isReview = tagging.status === "review";

  return (
    <div className="space-y-3">
      <p className="text-xs text-[var(--gmaps-text-secondary)]">
        Koridor: <strong>{routeName}</strong> · {isReview ? "Review" : "Sesi berjalan"}
      </p>

      {tagging.geoError && (
        <p className="text-xs text-[var(--gmaps-red)]">{tagging.geoError}</p>
      )}

      {!isReview && (
        <>
          <div className="text-xs text-[var(--gmaps-text-secondary)]">
            {tagging.currentPosition
              ? `Akurasi GPS saat ini: ${tagging.currentPosition.accuracy.toFixed(1)}m${
                  tagging.currentPosition.accuracy > tagging.accuracyWarningMeters ? " (kurang presisi)" : ""
                }`
              : "Menunggu sinyal GPS..."}
          </div>
          <button
            type="button"
            onClick={tagging.tagCurrentPosition}
            disabled={!tagging.currentPosition}
            className="w-full rounded-md bg-[var(--gmaps-blue)] px-3 py-3 text-base font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            Tag Halte ({tagging.points.length})
          </button>
        </>
      )}

      <ul className="max-h-64 space-y-1 overflow-y-auto">
        {tagging.points.map((p, i) => (
          <li
            key={p.id}
            className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-xs ${
              p.accuracy > tagging.accuracyWarningMeters ? "bg-yellow-50" : "bg-[var(--gmaps-surface-hover)]"
            }`}
          >
            <span className="w-4 shrink-0 text-center font-semibold">{i + 1}</span>
            {editingId === p.id ? (
              <input
                autoFocus
                defaultValue={p.name}
                onBlur={(e) => {
                  tagging.renamePoint(p.id, e.target.value || p.name);
                  setEditingId(null);
                }}
                className="min-w-0 flex-1 rounded border border-[var(--gmaps-border)] px-1 py-0.5"
              />
            ) : (
              <button
                type="button"
                onClick={() => setEditingId(p.id)}
                className="min-w-0 flex-1 truncate text-left"
                title="Klik untuk ganti nama"
              >
                {p.name}
              </button>
            )}
            <button type="button" onClick={() => tagging.movePoint(p.id, "up")} className="px-1 text-[var(--gmaps-text-secondary)]">
              ↑
            </button>
            <button type="button" onClick={() => tagging.movePoint(p.id, "down")} className="px-1 text-[var(--gmaps-text-secondary)]">
              ↓
            </button>
            <button type="button" onClick={() => tagging.removePoint(p.id)} className="px-1 text-[var(--gmaps-red)]">
              ✕
            </button>
          </li>
        ))}
      </ul>

      {!isReview && (
        <button
          type="button"
          onClick={tagging.finishSession}
          disabled={tagging.points.length < 2}
          className="w-full rounded-md border border-[var(--gmaps-blue)] px-3 py-2 text-sm font-medium text-[var(--gmaps-blue)] disabled:opacity-50"
        >
          Selesai Keliling ({tagging.points.length} titik)
        </button>
      )}

      {isReview && (
        <>
          <p className="text-xs text-[var(--gmaps-text-secondary)]">
            Klik peta untuk tambah titik yang kelewat. Simpan akan MENGGANTI seluruh data halte koridor ini.
          </p>
          {tagging.saveError && <p className="text-xs text-[var(--gmaps-red)]">{tagging.saveError}</p>}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={tagging.backToSession}
              disabled={tagging.saving}
              className="flex-1 rounded-md border border-[var(--gmaps-border)] px-3 py-2 text-sm disabled:opacity-50"
            >
              Kembali
            </button>
            <button
              type="button"
              onClick={async () => {
                const ok = await tagging.save();
                if (ok) onExit();
              }}
              disabled={tagging.saving || tagging.points.length < 2}
              className="flex-1 rounded-md bg-[var(--gmaps-blue)] px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {tagging.saving ? "Menyimpan..." : "Simpan ke Server"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
