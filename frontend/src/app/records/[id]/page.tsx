"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Code2, Download, FileText, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { PropertyRecordDetail } from "@/lib/types";

export default function RecordDetailPage() {
  const params = useParams<{ id: string }>();
  const [record, setRecord] = useState<PropertyRecordDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRawHtml, setShowRawHtml] = useState(false);

  useEffect(() => {
    if (!params?.id) return;
    api
      .getRecordDetail(params.id)
      .then(setRecord)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load record"))
      .finally(() => setLoading(false));
  }, [params?.id]);

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Dashboard
        </Link>
      </div>

      {loading ? (
        <div className="flex items-center justify-center rounded-xl border border-slate-200 bg-white p-12 text-sm text-slate-500">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Loading registration record...
        </div>
      ) : error || !record ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
          {error || "Record not found"}
        </div>
      ) : (
        <div className="space-y-6">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                  Index-II Property Registration Record
                </p>
                <h1 className="mt-1 text-xl font-bold text-slate-900">
                  Document #{record.document_number} ({record.registration_year})
                </h1>
                <p className="mt-0.5 text-sm text-slate-600">
                  {record.sro_name}
                  {record.district ? ` • ${record.district}` : ""}
                  {record.tahsil_or_village ? ` • ${record.tahsil_or_village}` : ""}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                {record.documents.map((doc) => (
                  <a
                    key={doc.id}
                    href={api.getDocumentDownloadUrl(doc.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
                  >
                    <Download className="h-3.5 w-3.5" />
                    {doc.file_name}
                  </a>
                ))}
              </div>
            </div>

            <dl className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-lg bg-slate-50 p-3">
                <dt className="text-[11px] font-medium uppercase text-slate-500">Registration Date</dt>
                <dd className="mt-1 text-sm font-semibold text-slate-900">
                  {record.registration_date || "Not parsed"}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <dt className="text-[11px] font-medium uppercase text-slate-500">Article / Doc Type</dt>
                <dd className="mt-1 text-sm font-semibold text-slate-900">
                  {record.article_type || "Not parsed"}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <dt className="text-[11px] font-medium uppercase text-slate-500">Survey / CTS Number</dt>
                <dd className="mt-1 text-sm font-semibold text-slate-900">
                  {record.survey_cts_number || "Not parsed"}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <dt className="text-[11px] font-medium uppercase text-slate-500">Consideration Amount</dt>
                <dd className="mt-1 text-sm font-semibold text-slate-900">
                  {record.consideration_amount != null
                    ? `₹ ${record.consideration_amount.toLocaleString("en-IN")}`
                    : "Not parsed"}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <dt className="text-[11px] font-medium uppercase text-slate-500">Market Value</dt>
                <dd className="mt-1 text-sm font-semibold text-slate-900">
                  {record.market_value != null
                    ? `₹ ${record.market_value.toLocaleString("en-IN")}`
                    : "Not parsed"}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <dt className="text-[11px] font-medium uppercase text-slate-500">Linked Search Jobs</dt>
                <dd className="mt-1 font-mono text-xs text-slate-700">
                  {record.job_ids.length} job(s)
                </dd>
              </div>
            </dl>

            <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-slate-200 p-4">
                <h2 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <FileText className="h-3.5 w-3.5" />
                  Party Details
                </h2>
                {record.party_details ? (
                  <pre className="whitespace-pre-wrap text-xs text-slate-700">
                    {JSON.stringify(record.party_details, null, 2)}
                  </pre>
                ) : (
                  <p className="text-xs text-slate-500">No structured party details available.</p>
                )}
              </div>

              <div className="rounded-lg border border-slate-200 p-4">
                <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Property Description
                </h2>
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-700">
                  {record.property_details || "No property description extracted."}
                </p>
              </div>
            </div>

            {record.raw_html_snapshot && (
              <div className="mt-6">
                <button
                  type="button"
                  onClick={() => setShowRawHtml((v) => !v)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  <Code2 className="h-3.5 w-3.5" />
                  {showRawHtml ? "Hide Raw HTML Snapshot" : "View Raw HTML Snapshot"}
                </button>
                {showRawHtml && (
                  <pre className="mt-3 max-h-96 overflow-auto rounded-lg bg-slate-950 p-4 font-mono text-[11px] text-slate-200">
                    {record.raw_html_snapshot}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
