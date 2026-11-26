"use client";

import { useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Download,
  ExternalLink,
  RefreshCw,
  RotateCcw,
  Send,
  ShieldCheck,
  Terminal,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import type { JobDetail } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

interface ActiveJobPanelProps {
  job: JobDetail | null;
  onRefresh: () => Promise<void>;
}

export function ActiveJobPanel({ job, onRefresh }: ActiveJobPanelProps) {
  const [captchaText, setCaptchaText] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  if (!job) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white/70 p-8 text-center">
        <Terminal className="mb-3 h-8 w-8 text-slate-400" />
        <p className="text-sm font-medium text-slate-700">No job selected</p>
        <p className="mt-1 max-w-xs text-xs text-slate-500">
          Launch a new IGR search or click any job in the history list to monitor live automation logs and CAPTCHA verification.
        </p>
      </div>
    );
  }

  const handleSubmitCaptcha = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!captchaText.trim()) return;
    setBusy(true);
    setActionError(null);
    try {
      await api.submitCaptcha(job.id, captchaText.trim());
      setCaptchaText("");
      await onRefresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to submit CAPTCHA");
    } finally {
      setBusy(false);
    }
  };

  const handleRefreshCaptcha = async () => {
    setBusy(true);
    setActionError(null);
    try {
      await api.refreshCaptcha(job.id);
      await onRefresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to request CAPTCHA refresh");
    } finally {
      setBusy(false);
    }
  };

  const handleCancel = async () => {
    setBusy(true);
    setActionError(null);
    try {
      await api.cancelJob(job.id);
      await onRefresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to cancel job");
    } finally {
      setBusy(false);
    }
  };

  const handleRetry = async () => {
    setBusy(true);
    setActionError(null);
    try {
      await api.retryJob(job.id);
      await onRefresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to retry job");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-slate-900">Live Automation Monitor</h2>
            <StatusBadge status={job.status} />
          </div>
          <p className="mt-0.5 font-mono text-[11px] text-slate-500">
            Job ID: {job.id} • Type: {job.search_type} • Retries: {job.retry_count}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {(job.status === "PENDING" || job.status === "PROCESSING" || job.status === "AWAITING_CAPTCHA") && (
            <button
              type="button"
              disabled={busy}
              onClick={handleCancel}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <XCircle className="h-3.5 w-3.5 text-rose-500" />
              Cancel
            </button>
          )}
          {(job.status === "FAILED" || job.status === "CANCELLED") && (
            <button
              type="button"
              disabled={busy}
              onClick={handleRetry}
              className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Retry Job
            </button>
          )}
        </div>
      </div>

      {actionError && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          {actionError}
        </div>
      )}

      {job.status === "AWAITING_CAPTCHA" && (
        <div className="rounded-xl border border-amber-300 bg-amber-50/70 p-4">
          <div className="mb-3 flex items-center gap-2 text-amber-900">
            <ShieldCheck className="h-4 w-4 text-amber-700" />
            <h3 className="text-sm font-semibold">Manual CAPTCHA Verification Required</h3>
          </div>
          <p className="mb-3 text-xs text-amber-800">
            The Playwright browser session is paused with all form fields preserved. Enter the{" "}
            <strong>exact case-sensitive</strong> characters shown (IGR CAPTCHAs use uppercase A–F and 0–9), or type &amp; click Search directly in the visible browser window.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            {job.captcha_image_base64 ? (
              <img
                src={`data:image/png;base64,${job.captcha_image_base64}`}
                alt="IGR Portal CAPTCHA"
                style={{ imageRendering: "pixelated" }}
                className="h-16 w-auto rounded-md border border-amber-300 bg-white p-1.5 shadow-xs"
              />
            ) : (
              <div className="flex h-14 w-36 items-center justify-center rounded-md border border-amber-200 bg-white text-xs text-slate-400">
                Loading image...
              </div>
            )}
            <form onSubmit={handleSubmitCaptcha} className="flex flex-1 flex-wrap items-center gap-2">
              <input
                type="text"
                value={captchaText}
                onChange={(e) => setCaptchaText(e.target.value)}
                placeholder="Type CAPTCHA text"
                autoFocus
                className="min-w-[160px] flex-1 rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm font-mono tracking-wider text-slate-900 focus:border-amber-600 focus:outline-none"
              />
              <button
                type="submit"
                disabled={busy || !captchaText.trim()}
                className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
              >
                <Send className="h-3.5 w-3.5" />
                Submit & Resume
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={handleRefreshCaptcha}
                title="Refresh CAPTCHA image"
                className="inline-flex items-center gap-1 rounded-lg border border-amber-300 bg-white px-2.5 py-2 text-xs font-medium text-amber-900 hover:bg-amber-100 disabled:opacity-50"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Refresh
              </button>
            </form>
          </div>
        </div>
      )}

      {job.portal_notice && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-800">
          {job.portal_notice}
        </div>
      )}

      {job.error_message && (
        <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{job.error_message}</span>
        </div>
      )}

      <div>
        <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Execution Logs ({job.logs.length})
        </h3>
        <div className="max-h-48 overflow-y-auto rounded-lg border border-slate-200 bg-slate-950 p-3 font-mono text-[11px] text-slate-200">
          {job.logs.length === 0 ? (
            <p className="text-slate-400">Waiting for worker logs...</p>
          ) : (
            job.logs.map((log) => (
              <div key={log.id} className="mb-1 flex gap-2 leading-relaxed">
                <span className="shrink-0 text-slate-500">
                  {new Date(log.created_at).toLocaleTimeString()}
                </span>
                <span
                  className={`shrink-0 font-semibold ${
                    log.level === "ERROR"
                      ? "text-rose-400"
                      : log.level === "WARNING"
                        ? "text-amber-400"
                        : "text-emerald-400"
                  }`}
                >
                  [{log.step || log.level}]
                </span>
                <span className="break-all text-slate-100">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {job.records.length > 0 && (
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Extracted Records ({job.records.length})
          </h3>
          <div className="space-y-2">
            {job.records.map((rec) => (
              <div
                key={rec.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"
              >
                <div>
                  <p className="text-xs font-semibold text-slate-900">
                    Doc #{rec.document_number} ({rec.registration_year}) — {rec.sro_name}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {rec.article_type || "Registration Record"}
                    {rec.survey_cts_number ? ` • Survey/CTS: ${rec.survey_cts_number}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {rec.documents.map((doc) => (
                    <a
                      key={doc.id}
                      href={api.getDocumentDownloadUrl(doc.id)}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-white px-2.5 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-50"
                    >
                      <Download className="h-3 w-3" />
                      Download
                    </a>
                  ))}
                  <Link
                    href={`/records/${rec.id}`}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Details
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
