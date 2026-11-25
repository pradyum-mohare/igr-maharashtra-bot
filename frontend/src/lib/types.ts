export type JobStatus =
  | "PENDING"
  | "PROCESSING"
  | "AWAITING_CAPTCHA"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type SearchType = "PROPERTY" | "DOCUMENT";
export type RegionType = "MUMBAI" | "REST" | "URBAN";

export interface AutomationLog {
  id: number;
  level: string;
  step: string | null;
  message: string;
  created_at: string;
}

export interface DocumentFile {
  id: string;
  file_name: string;
  mime_type: string;
  file_size_bytes: number | null;
  downloaded_at: string;
}

export interface PropertyRecord {
  id: string;
  district: string | null;
  tahsil_or_village: string | null;
  sro_name: string;
  document_number: string;
  registration_year: number;
  registration_date: string | null;
  article_type: string | null;
  consideration_amount: number | null;
  market_value: number | null;
  party_details: {
    seller_or_first_party?: string;
    buyer_or_second_party?: string;
    summary_row?: string[];
  } | null;
  property_details: string | null;
  survey_cts_number: string | null;
  created_at: string | null;
  documents: DocumentFile[];
}

export interface PropertyRecordDetail extends PropertyRecord {
  raw_html_snapshot: string | null;
  job_ids: string[];
}

export interface JobSummary {
  id: string;
  search_type: SearchType;
  criteria: Record<string, unknown>;
  status: JobStatus;
  portal_notice: string | null;
  error_message: string | null;
  retry_count: number;
  created_at: string;
  updated_at: string;
  record_count: number;
}

export interface JobDetail extends JobSummary {
  captcha_image_base64: string | null;
  logs: AutomationLog[];
  records: PropertyRecord[];
}

export interface DistrictOption {
  english: string;
  marathi: string;
}
