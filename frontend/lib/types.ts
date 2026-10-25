export type Severity = "Critical" | "Warning" | "Info";
export type FindingStatus = "Unresolved" | "Accepted" | "Overridden";
export type ScanStatus = "Pending" | "Flagged" | "Approved" | "Published";
export type Role = "Creator" | "Manager" | "Admin" | "Legal";
export type AgentKey = "tone" | "claim" | "visual" | "accessibility";

export interface Citation {
  guideline_id: string;
  code: string;
  title: string;
  section: string;
  category: string;
  quote: string;
}

export interface Finding {
  id: string;
  scan_id: string;
  guideline_id: string | null;
  agent: AgentKey;
  severity: Severity;
  issue_type: string;
  offending_segment: string;
  start_index: number;
  end_index: number;
  explanation: string;
  suggested_fix: string | null;
  status: FindingStatus;
  resolution_note: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  created_at: string;
  citation: Citation | null;
  ai_generated: boolean;
}

export interface ScanSummary {
  critical: number;
  warning: number;
  info: number;
  unresolved: number;
}

export interface Comment {
  id: string;
  scan_id: string;
  finding_id: string | null;
  author: string;
  role: string;
  body: string;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  actor: string;
  role: string;
  action: string;
  detail: string;
  created_at: string;
}

export interface Scan {
  id: string;
  organization_id: string;
  creator_id: string;
  document_title: string;
  raw_content: string;
  channel: string;
  audience: string;
  region: string;
  campaign: string;
  status: ScanStatus;
  compliance_score: number;
  created_at: string;
  updated_at: string;
  findings: Finding[];
  comments: Comment[];
  audit: AuditEvent[];
  summary: ScanSummary;
}

export interface ScanListItem {
  id: string;
  document_title: string;
  channel: string;
  status: ScanStatus;
  compliance_score: number;
  created_at: string;
  summary: ScanSummary;
}

export interface Guideline {
  id: string;
  code: string;
  title: string;
  category: string;
  section: string;
  content: string;
  tags: string;
  created_at: string;
  score?: number;
}

export interface ClarityRow {
  code: string;
  title: string;
  section: string;
  category: string;
  findings: number;
  overrides: number;
  clarity: number;
}

export interface TrendPoint {
  date: string;
  Critical: number;
  Warning: number;
  Info: number;
}

export interface Analytics {
  totals: {
    scans: number;
    compliance_rate: number;
    top_violation: string;
    top_violation_share: number;
    avg_resolution_minutes: number;
    open_findings: number;
    guideline_chunks: number;
  };
  severity: Record<Severity, number>;
  agents: Record<string, number>;
  trend: TrendPoint[];
  clarity: ClarityRow[];
  recent_scans: {
    id: string;
    title: string;
    channel: string;
    status: ScanStatus;
    compliance_score: number;
    created_at: string;
    unresolved: number;
  }[];
  knowledge_base: { total_chunks: number; by_category: Record<string, number> };
}
