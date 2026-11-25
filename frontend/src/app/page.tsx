"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Activity,
  Database,
  Download,
  ExternalLink,
  FileDown,
  History,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldAlert,
} from "lucide-react";
import { ActiveJobPanel } from "@/components/ActiveJobPanel";
import { SearchForm } from "@/components/SearchForm";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import type { DistrictOption, JobDetail, JobSummary, PropertyRecord, SearchType } from "@/lib/types";

export default function DashboardPage() {
  const [apiHealthy, setApiHealthy] = useState<boolean | null>(null);
  const [districts, setDistricts] = useState<DistrictOption[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [records, setRecords] = useState<PropertyRecord[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<JobDetail | null>(null);
  const [activeTab, setActiveTab] = useState<"jobs" | "records">("jobs");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [recordQuery, setRecordQuery] = useState("");
  const [recordYear, setRecordYear] = useState("");
  const [loading, setLoading] = useState(true);

  const loadOverview = useCallback(async () => {
    try {
      const [healthRes, jobsRes, recordsRes] = await Promise.all([
        api.health().then(() => true).catch(() => false),
        api.listJobs({ status: statusFilter }),
        api.listRecords({ q: recordQuery || undefined, year: recordYear || undefined }),
      ]);
      setApiHealthy(healthRes);
      setJobs(jobsRes);
      setRecords(recordsRes);
      if (!selectedJobId && jobsRes.length > 0) {
        setSelectedJobId(jobsRes[0].id);
      }
    } finally {
      setLoading(false);
    }
  }, [statusFilter, recordQuery, recordYear, selectedJobId]);

  const loadSelectedJob = useCallback(async () => {
    if (!selectedJobId) {
      setSelectedJob(null);
      return;
    }
    try {
      const detail = await api.getJobDetail(selectedJobId);
      setSelectedJob(detail);
    } catch {
      setSelectedJob(null);
    }
  }, [selectedJobId]);

  useEffect(() => {
    api.listDistricts().then(setDistricts).catch(() => {});
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    loadSelectedJob();
  }, [loadSelectedJob]);

  // Poll every 2s whenever any job is active or selected job is active
  useEffect(() => {
    const hasActive =
      jobs.some((j) => ["PENDING", "PROCESSING", "AWAITING_CAPTCHA"].includes(j.status)) ||
      (selectedJob && ["PENDING", "PROCESSING", "AWAITING_CAPTCHA"].includes(selectedJob.status));

    if (!hasActive) return;
    const timer = setInterval(() => {
      loadOverview();
      loadSelectedJob();
    }, 2000);
    return () => clearInterval(timer);
  }, [jobs, selectedJob, loadOverview, loadSelectedJob]);

  const handleCreateJob = async (payload: { search_type: SearchType; criteria: Record<string, unknown> }) => {
    const created = await api.createJob(payload);
    setSelectedJobId(created.id);
    setActiveTab("jobs");
    await Promise.all([loadOverview(), api.getJobDetail(created.id).then(setSelectedJob)]);
  };

  const stats = useMemo(() => {
    const awaitingCaptcha = jobs.filter((j) => j.status === "AWAITING_CAPTCHA").length;
    const activeCount = jobs.filter((j) => ["PENDING", "PROCESSING"].includes(j.status)).length;
    const docCount = records.reduce((acc, r) => acc + r.documents.length, 0);
    return {
      totalJobs: jobs.length,
      activeCount,
      awaitingCaptcha,
      totalRecords: records.length,
      docCount,
    };
  }, [jobs, records]);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div>
            <h1 className="text-lg font-bold tracking-tight text-slate-900">
              IGR Maharashtra Free Search Automation
            </h1>
            <p className="text-xs text-slate-500">
              Playwright Portal Agent • FastAPI Job Queue • PostgreSQL Index-II Storage
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${
                apiHealthy
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : apiHealthy === false
                    ? "border-rose-200 bg-rose-50 text-rose-700"
                    : "border-slate-200 bg-slate-50 text-slate-500"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  apiHealthy ? "bg-emerald-500" : apiHealthy === false ? "bg-rose-500" : "bg-slate-400"
                }`}
              />
              {apiHealthy ? "FastAPI Connected" : apiHealthy === false ? "Backend Offline" : "Checking API..."}
            </span>
            <button
              type="button"
              onClick={() => {
                loadOverview();
                loadSelectedJob();
              }}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        {/* KPI Strip */}
        <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-xs font-medium">Search Jobs</span>
              <History className="h-4 w-4" />
            </div>
            <p className="mt-2 text-2xl font-bold text-slate-900">{stats.totalJobs}</p>
            <p className="text-[11px] text-slate-500">{stats.activeCount} currently running</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
            <div className="flex items-center justify-between text-amber-600">
              <span className="text-xs font-medium">CAPTCHA Queue</span>
              <ShieldAlert className="h-4 w-4" />
            </div>
            <p className="mt-2 text-2xl font-bold text-slate-900">{stats.awaitingCaptcha}</p>
            <p className="text-[11px] text-slate-500">Paused awaiting verification</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
            <div className="flex items-center justify-between text-indigo-600">
              <span className="text-xs font-medium">Saved Records</span>
              <Database className="h-4 w-4" />
            </div>
            <p className="mt-2 text-2xl font-bold text-slate-900">{stats.totalRecords}</p>
            <p className="text-[11px] text-slate-500">Deduplicated in PostgreSQL</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
            <div className="flex items-center justify-between text-emerald-600">
              <span className="text-xs font-medium">Documents Stored</span>
              <FileDown className="h-4 w-4" />
            </div>
            <p className="mt-2 text-2xl font-bold text-slate-900">{stats.docCount}</p>
            <p className="text-[11px] text-slate-500">Index-II PDF / HTML files</p>
          </div>
        </section>

        {/* Top Workspace: Search Form + Live Monitor */}
        <section className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="lg:col-span-6">
            <SearchForm districts={districts} onSubmit={handleCreateJob} />
          </div>
          <div className="lg:col-span-6">
            <ActiveJobPanel
              job={selectedJob}
              onRefresh={async () => {
                await Promise.all([loadOverview(), loadSelectedJob()]);
              }}
            />
          </div>
        </section>

        {/* History & Extracted Records */}
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-3">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setActiveTab("jobs")}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "jobs"
                    ? "bg-slate-900 text-white"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <Activity className="h-3.5 w-3.5" />
                Job Queue & History ({jobs.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("records")}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "records"
                    ? "bg-slate-900 text-white"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <Database className="h-3.5 w-3.5" />
                Extracted Property Records ({records.length})
              </button>
            </div>

            {activeTab === "jobs" ? (
              <div className="flex items-center gap-2">
                <label className="text-xs text-slate-500">Status:</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-800"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="PENDING">Pending</option>
                  <option value="PROCESSING">Processing</option>
                  <option value="AWAITING_CAPTCHA">Awaiting CAPTCHA</option>
                  <option value="COMPLETED">Completed</option>
                  <option value="FAILED">Failed</option>
                  <option value="CANCELLED">Cancelled</option>
                </select>
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={recordQuery}
                    onChange={(e) => setRecordQuery(e.target.value)}
                    placeholder="Filter doc #, SRO, CTS, details..."
                    className="rounded-lg border border-slate-300 bg-white py-1 pr-3 pl-8 text-xs text-slate-800 focus:border-indigo-500 focus:outline-none"
                  />
                </div>
                <input
                  type="text"
                  value={recordYear}
                  onChange={(e) => setRecordYear(e.target.value.replace(/\D/g, "").slice(0, 4))}
                  placeholder="Year"
                  className="w-20 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-800 focus:border-indigo-500 focus:outline-none"
                />
              </div>
            )}
          </div>

          {loading ? (
            <div className="p-8 text-center text-xs text-slate-500">Loading dashboard data...</div>
          ) : activeTab === "jobs" ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-200 bg-slate-50 text-[11px] font-semibold uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Search Mode</th>
                    <th className="px-4 py-3">Criteria</th>
                    <th className="px-4 py-3">Records</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {jobs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                        No search jobs yet. Use the form above to start your first IGR search.
                      </td>
                    </tr>
                  ) : (
                    jobs.map((job) => (
                      <tr
                        key={job.id}
                        onClick={() => setSelectedJobId(job.id)}
                        className={`cursor-pointer transition hover:bg-slate-50 ${
                          selectedJobId === job.id ? "bg-indigo-50/40" : ""
                        }`}
                      >
                        <td className="px-4 py-3">
                          <StatusBadge status={job.status} />
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-800">
                          {job.search_type}
                          {job.criteria?.region ? ` (${String(job.criteria.region)})` : ""}
                        </td>
                        <td className="max-w-md truncate px-4 py-3 font-mono text-[11px] text-slate-600">
                          {JSON.stringify(job.criteria)}
                        </td>
                        <td className="px-4 py-3 font-semibold text-slate-800">{job.record_count}</td>
                        <td className="px-4 py-3 text-slate-500">
                          {new Date(job.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="inline-flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => setSelectedJobId(job.id)}
                              className="rounded-md border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-100"
                            >
                              Inspect
                            </button>
                            {(job.status === "FAILED" || job.status === "CANCELLED") && (
                              <button
                                type="button"
                                onClick={async () => {
                                  await api.retryJob(job.id);
                                  setSelectedJobId(job.id);
                                  await loadOverview();
                                }}
                                className="inline-flex items-center gap-1 rounded-md bg-slate-900 px-2 py-1 text-[11px] font-medium text-white hover:bg-slate-800"
                              >
                                <RotateCcw className="h-3 w-3" />
                                Retry
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-200 bg-slate-50 text-[11px] font-semibold uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Doc No.</th>
                    <th className="px-4 py-3">Year / Date</th>
                    <th className="px-4 py-3">SRO / District</th>
                    <th className="px-4 py-3">Article & Parties</th>
                    <th className="px-4 py-3">Survey / CTS</th>
                    <th className="px-4 py-3 text-right">Documents & View</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {records.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                        No extracted records match your filter.
                      </td>
                    </tr>
                  ) : (
                    records.map((rec) => (
                      <tr key={rec.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 font-semibold text-slate-900">{rec.document_number}</td>
                        <td className="px-4 py-3 text-slate-700">
                          <div>{rec.registration_year}</div>
                          {rec.registration_date && (
                            <div className="text-[11px] text-slate-500">{rec.registration_date}</div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-700">
                          <div className="font-medium">{rec.sro_name}</div>
                          {rec.district && <div className="text-[11px] text-slate-500">{rec.district}</div>}
                        </td>
                        <td className="max-w-xs px-4 py-3 text-slate-700">
                          <div className="font-medium">{rec.article_type || "—"}</div>
                          {(rec.party_details?.seller_or_first_party ||
                            rec.party_details?.buyer_or_second_party) && (
                            <div className="truncate text-[11px] text-slate-500">
                              {rec.party_details?.seller_or_first_party || "?"} →{" "}
                              {rec.party_details?.buyer_or_second_party || "?"}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-700">{rec.survey_cts_number || "—"}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="inline-flex items-center gap-1.5">
                            {rec.documents.map((doc) => (
                              <a
                                key={doc.id}
                                href={api.getDocumentDownloadUrl(doc.id)}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2 py-1 text-[11px] font-medium text-indigo-700 hover:bg-indigo-100"
                              >
                                <Download className="h-3 w-3" />
                                PDF
                              </a>
                            ))}
                            <Link
                              href={`/records/${rec.id}`}
                              className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-100"
                            >
                              <ExternalLink className="h-3 w-3" />
                              Details
                            </Link>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
