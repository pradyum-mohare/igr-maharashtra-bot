"use client";

import { useState } from "react";
import { Building2, FileText, Loader2, Play } from "lucide-react";
import type { DistrictOption, RegionType, SearchType } from "@/lib/types";

interface SearchFormProps {
  districts: DistrictOption[];
  onSubmit: (payload: { search_type: SearchType; criteria: Record<string, unknown> }) => Promise<void>;
}

const YEARS = Array.from({ length: 42 }, (_, idx) => String(2026 - idx));

export function SearchForm({ districts, onSubmit }: SearchFormProps) {
  const [searchType, setSearchType] = useState<SearchType>("PROPERTY");
  const [region, setRegion] = useState<RegionType>("MUMBAI");
  const [year, setYear] = useState("2024");
  const [district, setDistrict] = useState("Mumbai City");
  const [tahsil, setTahsil] = useState("");
  const [areaName, setAreaName] = useState("");
  const [village, setVillage] = useState("");
  const [propertyNumber, setPropertyNumber] = useState("");
  const [docType, setDocType] = useState("Regular");
  const [sro, setSro] = useState("");
  const [documentNumber, setDocumentNumber] = useState("");
  const [partyName, setPartyName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegionChange = (nextRegion: RegionType) => {
    setRegion(nextRegion);
    if (nextRegion === "MUMBAI") {
      setDistrict("Mumbai City");
    } else if (district.toLowerCase().includes("mumbai")) {
      setDistrict("Pune");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const criteria: Record<string, unknown> = {
      year,
      district: district.trim() || undefined,
      party_name: partyName.trim() || undefined,
    };

    if (searchType === "PROPERTY") {
      criteria.region = region;
      if (region === "MUMBAI") {
        if (!areaName.trim() && !village.trim()) {
          setError("For Mumbai property search, enter at least 3 English characters for Village/Area name.");
          return;
        }
        criteria.area_name = areaName.trim() || village.trim();
        criteria.village = village.trim() || areaName.trim();
      } else {
        if (!district.trim()) {
          setError("Select or enter a District for Rest of Maharashtra / Urban search.");
          return;
        }
        criteria.tahsil = tahsil.trim() || undefined;
        criteria.village = village.trim() || undefined;
      }
      if (!propertyNumber.trim()) {
        setError("Enter a Property / Survey / CTS / Gat / Plot Number.");
        return;
      }
      criteria.property_number = propertyNumber.trim();
    } else {
      if (!district.trim() || !sro.trim() || !documentNumber.trim()) {
        setError("District, Sub-Registrar Office (SRO), and Document Number are required for Document Number search.");
        return;
      }
      criteria.doc_type = docType;
      criteria.sro = sro.trim();
      criteria.document_number = documentNumber.trim();
    }

    setSubmitting(true);
    try {
      await onSubmit({ search_type: searchType, criteria });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to queue search job");
    } finally {
      setSubmitting(false);
    }
  };

  const districtOptions =
    searchType === "PROPERTY" && region === "MUMBAI"
      ? [
          { english: "Mumbai City", marathi: "मुंबई जिल्हा" },
          { english: "Mumbai Suburban", marathi: "मुंबई उपनगर जिल्हा" },
        ]
      : districts;

  return (
    <form onSubmit={handleSubmit} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Initiate IGR Free Search</h2>
          <p className="text-xs text-slate-500">
            Automates <span className="font-mono">freesearchigrservice.maharashtra.gov.in</span>
          </p>
        </div>
        <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
          <button
            type="button"
            onClick={() => setSearchType("PROPERTY")}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition ${
              searchType === "PROPERTY"
                ? "bg-indigo-600 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Building2 className="h-3.5 w-3.5" />
            Property Details
          </button>
          <button
            type="button"
            onClick={() => setSearchType("DOCUMENT")}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition ${
              searchType === "DOCUMENT"
                ? "bg-indigo-600 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <FileText className="h-3.5 w-3.5" />
            Document Number
          </button>
        </div>
      </div>

      {searchType === "PROPERTY" && (
        <div className="mb-4 grid grid-cols-3 gap-2">
          {(
            [
              { id: "MUMBAI", label: "Mumbai" },
              { id: "REST", label: "Rest of Maharashtra" },
              { id: "URBAN", label: "Urban Areas" },
            ] as const
          ).map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => handleRegionChange(r.id)}
              className={`rounded-lg border px-3 py-2 text-xs font-medium transition ${
                region === r.id
                  ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      )}

      {searchType === "DOCUMENT" && (
        <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {["Regular", "eFiling", "eRegistration", "iSarita 2.0"].map((dt) => (
            <button
              key={dt}
              type="button"
              onClick={() => setDocType(dt)}
              className={`rounded-lg border px-3 py-2 text-xs font-medium transition ${
                docType === dt
                  ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {dt}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-700">Registration Year</label>
          <select
            value={year}
            onChange={(e) => setYear(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
          >
            {YEARS.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-700">District</label>
          <input
            list="igr-districts"
            value={district}
            onChange={(e) => setDistrict(e.target.value)}
            placeholder="e.g., Pune or पुणे"
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
          />
          <datalist id="igr-districts">
            {districtOptions.map((d) => (
              <option key={d.english} value={d.english}>
                {d.marathi}
              </option>
            ))}
          </datalist>
        </div>

        {searchType === "PROPERTY" && region === "MUMBAI" && (
          <>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">
                Village Search Prefix (min 3 English chars)
              </label>
              <input
                type="text"
                value={areaName}
                onChange={(e) => setAreaName(e.target.value)}
                placeholder="e.g., Dadar, Bandra, Andheri"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">
                Select Village / Area (optional exact match)
              </label>
              <input
                type="text"
                value={village}
                onChange={(e) => setVillage(e.target.value)}
                placeholder="Optional exact Marathi/English village"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </>
        )}

        {searchType === "PROPERTY" && region !== "MUMBAI" && (
          <>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">Tahsil</label>
              <input
                type="text"
                value={tahsil}
                onChange={(e) => setTahsil(e.target.value)}
                placeholder="e.g., Haveli"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">Village</label>
              <input
                type="text"
                value={village}
                onChange={(e) => setVillage(e.target.value)}
                placeholder="e.g., Baner"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </>
        )}

        {searchType === "PROPERTY" ? (
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Property / Survey / CTS / Gat / Plot No.
            </label>
            <input
              type="text"
              value={propertyNumber}
              onChange={(e) => setPropertyNumber(e.target.value)}
              placeholder="e.g., 101 or 101/2"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
            />
          </div>
        ) : (
          <>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">Sub-Registrar Office (SRO)</label>
              <input
                type="text"
                value={sro}
                onChange={(e) => setSro(e.target.value)}
                placeholder="e.g., Joint S.R. Haveli 5 or Haveli 5 (Pimpri)"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">Document Number</label>
              <input
                type="text"
                value={documentNumber}
                onChange={(e) => setDocumentNumber(e.target.value)}
                placeholder="e.g., 4521"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </>
        )}

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-700">
            Party Name Filter (optional)
          </label>
          <input
            type="text"
            value={partyName}
            onChange={(e) => setPartyName(e.target.value)}
            placeholder="Filter extracted results by buyer/seller name"
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
          />
        </div>
      </div>

      {error && (
        <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          {error}
        </div>
      )}

      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-[11px] text-slate-500">
          CAPTCHA pauses automatically for manual verification without losing session state.
        </p>
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-xs transition hover:bg-indigo-700 disabled:opacity-60"
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          Launch Search Job
        </button>
      </div>
    </form>
  );
}
