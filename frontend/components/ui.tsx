"use client";

import type { ScanStatus, Severity } from "@/lib/types";

export function SeverityChip({ severity }: { severity: Severity }) {
  const styles: Record<Severity, string> = {
    Critical: "border-critical/40 bg-critical/10 text-critical",
    Warning: "border-spark/40 bg-spark/10 text-spark",
    Info: "border-info/40 bg-info/10 text-info",
  };
  const dot: Record<Severity, string> = {
    Critical: "bg-critical",
    Warning: "bg-spark",
    Info: "bg-info",
  };
  return (
    <span className={`chip ${styles[severity]}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dot[severity]}`} />
      {severity}
    </span>
  );
}

export function StatusChip({ status }: { status: ScanStatus }) {
  const styles: Record<ScanStatus, string> = {
    Pending: "border-slate-500/40 bg-slate-500/10 text-slate-300",
    Flagged: "border-critical/40 bg-critical/10 text-critical",
    Approved: "border-success/40 bg-success/10 text-success",
    Published: "border-info/40 bg-info/10 text-info",
  };
  return <span className={`chip ${styles[status]}`}>{status}</span>;
}

export function ResolutionChip({ status }: { status: string }) {
  const styles: Record<string, string> = {
    Unresolved: "border-edge bg-white/[0.04] text-slate-400",
    Accepted: "border-success/40 bg-success/10 text-success",
    Overridden: "border-spark/40 bg-spark/10 text-spark",
  };
  return <span className={`chip ${styles[status] ?? styles.Unresolved}`}>{status}</span>;
}

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function ScoreRing({ score, size = 76 }: { score: number; size?: number }) {
  const radius = (size - 10) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(100, Math.max(0, score)) / 100) * circumference;
  const tone = score >= 85 ? "#3DDC97" : score >= 60 ? "#F5B700" : "#FF6B6B";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="7"
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={tone}
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          fill="none"
          style={{ transition: "stroke-dashoffset 500ms ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-lg font-bold text-white">{Math.round(score)}</span>
        <span className="text-[9px] uppercase tracking-widest text-slate-500">score</span>
      </div>
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
  width = "max-w-2xl",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  width?: string;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 p-4 pt-24 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
    >
      <div
        className={`w-full ${width} animate-fade-up rounded-2xl border border-edge bg-panel shadow-2xl`}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-edge px-5 py-4">
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-300">{title}</h2>
          <button className="btn-subtle h-8 w-8 rounded-lg p-0" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-edge px-6 py-10 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-success/10 text-success">
        ✓
      </div>
      <p className="text-sm font-semibold text-slate-200">{title}</p>
      <p className="max-w-xs text-xs leading-relaxed text-slate-500">{body}</p>
    </div>
  );
}
