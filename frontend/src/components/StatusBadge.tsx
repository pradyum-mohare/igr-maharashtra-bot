"use client";

import type { JobStatus } from "@/lib/types";

const STATUS_STYLES: Record<JobStatus, string> = {
  PENDING: "bg-slate-100 text-slate-700 border-slate-200",
  PROCESSING: "bg-blue-50 text-blue-700 border-blue-200",
  AWAITING_CAPTCHA: "bg-amber-50 text-amber-800 border-amber-300",
  COMPLETED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  FAILED: "bg-rose-50 text-rose-700 border-rose-200",
  CANCELLED: "bg-zinc-100 text-zinc-600 border-zinc-200",
};

const STATUS_LABELS: Record<JobStatus, string> = {
  PENDING: "Pending",
  PROCESSING: "Processing",
  AWAITING_CAPTCHA: "Awaiting CAPTCHA",
  COMPLETED: "Completed",
  FAILED: "Failed",
  CANCELLED: "Cancelled",
};

export function StatusBadge({ status }: { status: JobStatus }) {
  const cls = STATUS_STYLES[status] || STATUS_STYLES.PENDING;
  const label = STATUS_LABELS[status] || status;
  const pulse = status === "PROCESSING" || status === "AWAITING_CAPTCHA";

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          status === "COMPLETED"
            ? "bg-emerald-500"
            : status === "FAILED"
              ? "bg-rose-500"
              : status === "AWAITING_CAPTCHA"
                ? "bg-amber-500 animate-pulse"
                : status === "PROCESSING"
                  ? "bg-blue-500 animate-pulse"
                  : "bg-slate-400"
        } ${pulse ? "animate-pulse" : ""}`}
      />
      {label}
    </span>
  );
}
