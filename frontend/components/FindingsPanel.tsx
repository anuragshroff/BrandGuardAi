"use client";

import { useState } from "react";
import type { AgentKey, Finding, Role, Scan } from "@/lib/types";
import { EmptyState, ResolutionChip, ScoreRing, SeverityChip, Spinner } from "./ui";

const TABS: { key: AgentKey; label: string; short: string }[] = [
  { key: "tone", label: "Tone & Vocab", short: "Tone" },
  { key: "claim", label: "Fact & Claims", short: "Claims" },
  { key: "visual", label: "Visual", short: "Visual" },
  { key: "accessibility", label: "Accessibility", short: "WCAG" },
];

export default function FindingsPanel({
  scan,
  role,
  activeTab,
  onTabChange,
  selectedId,
  onSelect,
  busy,
  error,
  onAccept,
  onOverride,
  onComment,
  onApprove,
  onPublish,
  onRescan,
}: {
  scan: Scan;
  role: Role;
  activeTab: AgentKey;
  onTabChange: (tab: AgentKey) => void;
  selectedId: string | null;
  onSelect: (finding: Finding) => void;
  busy: boolean;
  error: string | null;
  onAccept: (finding: Finding) => void;
  onOverride: (finding: Finding, note: string) => void;
  onComment: (finding: Finding | null, body: string) => void;
  onApprove: () => void;
  onPublish: () => void;
  onRescan: () => void;
}) {
  const [view, setView] = useState<"findings" | "activity">("findings");

  const unresolved = scan.findings.filter((finding) => finding.status === "Unresolved");
  const visible = scan.findings
    .filter((finding) => finding.agent === activeTab)
    .sort((a, b) => {
      const resolvedDiff = Number(a.status !== "Unresolved") - Number(b.status !== "Unresolved");
      if (resolvedDiff !== 0) return resolvedDiff;
      const order = { Critical: 0, Warning: 1, Info: 2 } as const;
      return order[a.severity] - order[b.severity] || a.start_index - b.start_index;
    });

  const openInTab = unresolved.filter((finding) => finding.agent === activeTab).length;
  const canApprove = role !== "Creator" && scan.status !== "Approved" && scan.status !== "Published";
  const canPublish = role !== "Creator" && scan.status === "Approved";

  return (
    <aside className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-edge bg-panel/85 backdrop-blur">
      <div className="flex items-center gap-3 border-b border-edge px-4 py-3.5">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-white">AI Findings</h2>
            <span className="chip border-signal/30 bg-signal/10 text-signal">4 agents</span>
          </div>
          <p className="mt-0.5 truncate text-[11px] text-slate-500">
            {unresolved.length} open · {scan.findings.length} total · every flag is cited
          </p>
        </div>
        <ScoreRing score={scan.compliance_score} size={62} />
      </div>

      <div className="flex border-b border-edge" role="tablist" aria-label="Inspection agents">
        {TABS.map((tab) => {
          const count = unresolved.filter((finding) => finding.agent === tab.key).length;
          const isActive = activeTab === tab.key && view === "findings";
          return (
            <button
              key={tab.key}
              role="tab"
              aria-selected={isActive}
              onClick={() => {
                setView("findings");
                onTabChange(tab.key);
              }}
              className={`flex-1 border-b-2 px-1 py-2.5 text-[11px] font-semibold transition ${
                isActive
                  ? "border-signal text-white"
                  : "border-transparent text-slate-500 hover:bg-white/[0.03] hover:text-slate-300"
              }`}
              title={tab.label}
            >
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="sm:hidden">{tab.short}</span>
              <span
                className={`ml-1.5 rounded-full px-1.5 py-0.5 text-[10px] ${
                  count > 0 ? "bg-white/10 text-slate-200" : "bg-success/10 text-success"
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      <div className="flex items-center justify-between border-b border-edge bg-ink/30 px-3 py-1.5">
        <div className="flex gap-1">
          <button
            onClick={() => setView("findings")}
            className={`rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-wider ${
              view === "findings" ? "bg-white/10 text-white" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            Findings
          </button>
          <button
            onClick={() => setView("activity")}
            className={`rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-wider ${
              view === "activity" ? "bg-white/10 text-white" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            Activity ({scan.comments.length})
          </button>
        </div>
        <button
          onClick={onRescan}
          disabled={busy}
          className="btn-subtle px-2 py-1 text-[10px] uppercase tracking-wider"
        >
          {busy ? <Spinner className="h-3 w-3" /> : <RefreshIcon />}
          Re-scan
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {view === "activity" ? (
          <Activity scan={scan} busy={busy} onComment={onComment} />
        ) : visible.length === 0 ? (
          <EmptyState
            title="No findings in this agent"
            body={
              openInTab === 0
                ? "This inspection lens is clear for the current draft."
                : "No issues match the current filter."
            }
          />
        ) : (
          <div className="space-y-3">
            {visible.map((finding) => (
              <FindingCard
                key={finding.id}
                finding={finding}
                selected={selectedId === finding.id}
                busy={busy}
                onSelect={() => onSelect(finding)}
                onAccept={() => onAccept(finding)}
                onOverride={(note) => onOverride(finding, note)}
                onComment={(body) => onComment(finding, body)}
              />
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-edge bg-ink/40 px-4 py-3">
        {error && (
          <p role="alert" className="mb-2 rounded-lg border border-critical/40 bg-critical/10 px-3 py-2 text-[11px] leading-relaxed text-red-200">
            {error}
          </p>
        )}
        <div className="flex items-center gap-2">
          <div className="min-w-0 flex-1">
            <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Sign-off gate</p>
            <p className="truncate text-xs font-semibold text-slate-200">
              {scan.status === "Approved" || scan.status === "Published"
                ? `${scan.status} by manager`
                : role === "Creator"
                  ? "Manager approval required"
                  : `${role} can approve this draft`}
            </p>
          </div>
          {scan.status === "Approved" || scan.status === "Published" ? (
            <button onClick={onPublish} disabled={!canPublish || busy} className="btn-primary px-3 py-2 text-xs">
              {busy ? <Spinner className="h-3 w-3" /> : null}
              {scan.status === "Published" ? "Published" : "Publish"}
            </button>
          ) : (
            <button onClick={onApprove} disabled={!canApprove || busy} className="btn-primary px-3 py-2 text-xs">
              {busy ? <Spinner className="h-3 w-3" /> : null}
              Approve draft
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}

function FindingCard({
  finding,
  selected,
  busy,
  onSelect,
  onAccept,
  onOverride,
  onComment,
}: {
  finding: Finding;
  selected: boolean;
  busy: boolean;
  onSelect: () => void;
  onAccept: () => void;
  onOverride: (note: string) => void;
  onComment: (body: string) => void;
}) {
  const [formOpen, setFormOpen] = useState(false);
  const [note, setNote] = useState("");
  const resolved = finding.status !== "Unresolved";

  return (
    <div
      id={`finding-${finding.id}`}
      onClick={onSelect}
      className={`animate-fade-up cursor-pointer rounded-xl border p-3.5 transition ${
        selected
          ? "border-signal/60 bg-signal/[0.06] shadow-glow"
          : "border-edge bg-white/[0.02] hover:border-slate-600"
      } ${resolved ? "opacity-70" : ""}`}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <SeverityChip severity={finding.severity} />
        <span className="chip border-white/10 bg-white/[0.04] text-slate-400">AI Suggested</span>
        <div className="ml-auto">
          <ResolutionChip status={finding.status} />
        </div>
      </div>

      <h3 className="mt-2 text-[13px] font-bold text-white">{finding.issue_type}</h3>

      <p className="mt-2 rounded-lg border-l-2 border-edge bg-ink/60 px-2.5 py-1.5 text-xs italic text-slate-300">
        “{finding.offending_segment.length > 140
          ? `${finding.offending_segment.slice(0, 140)}…`
          : finding.offending_segment}”
      </p>

      <p className="mt-2 text-xs leading-relaxed text-slate-400">{finding.explanation}</p>

      {finding.citation && (
        <div className="mt-2.5 rounded-lg border border-signal/25 bg-signal/[0.06] p-2.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="rounded bg-signal/20 px-1.5 py-0.5 text-[9px] font-bold tracking-wider text-blue-200">
              {finding.citation.code}
            </span>
            <span className="text-[10px] font-semibold text-slate-300">{finding.citation.section}</span>
          </div>
          <p className="mt-1 text-[10px] font-semibold text-slate-400">{finding.citation.title}</p>
          <p className="mt-1 line-clamp-3 text-[11px] leading-relaxed text-slate-400">
            “{finding.citation.quote}”
          </p>
        </div>
      )}

      {finding.suggested_fix && (
        <div className="mt-2.5 rounded-lg border border-success/25 bg-success/[0.05] px-2.5 py-2">
          <p className="text-[9px] font-bold uppercase tracking-[0.14em] text-success">Proposed fix</p>
          <p className="mt-0.5 break-words text-xs font-medium text-emerald-100">
            {finding.suggested_fix}
          </p>
        </div>
      )}

      {resolved ? (
        <div className="mt-2.5 rounded-lg border border-edge bg-ink/40 px-2.5 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            {finding.status} by {finding.resolved_by ?? "reviewer"}
          </p>
          {finding.resolution_note && (
            <p className="mt-0.5 text-[11px] text-slate-400">{finding.resolution_note}</p>
          )}
        </div>
      ) : (
        <>
          <div className="mt-2.5 flex flex-wrap gap-1.5" onClick={(event) => event.stopPropagation()}>
            {finding.suggested_fix && (
              <button
                onClick={onAccept}
                disabled={busy}
                className="btn-success flex-1 px-2.5 py-1.5 text-[11px]"
              >
                {busy ? <Spinner className="h-3 w-3" /> : <CheckIcon />}
                Accept suggestion
              </button>
            )}
            <button
              onClick={() => setFormOpen((open) => !open)}
              className="btn-ghost flex-1 px-2.5 py-1.5 text-[11px]"
            >
              Override / Comment
            </button>
          </div>

          {formOpen && (
            <div
              className="mt-2 space-y-1.5"
              onClick={(event) => event.stopPropagation()}
            >
              <textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                rows={2}
                placeholder="Add context for the reviewer…"
                className="input text-xs"
              />
              <div className="flex gap-1.5">
                <button
                  onClick={() => {
                    if (!note.trim()) return;
                    onOverride(note.trim());
                    setNote("");
                    setFormOpen(false);
                  }}
                  disabled={busy || !note.trim()}
                  className="btn-ghost flex-1 px-2 py-1 text-[10px]"
                >
                  Submit override
                </button>
                <button
                  onClick={() => {
                    if (!note.trim()) return;
                    onComment(note.trim());
                    setNote("");
                    setFormOpen(false);
                  }}
                  disabled={busy || !note.trim()}
                  className="btn-subtle flex-1 px-2 py-1 text-[10px]"
                >
                  Comment only
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Activity({
  scan,
  busy,
  onComment,
}: {
  scan: Scan;
  busy: boolean;
  onComment: (finding: Finding | null, body: string) => void;
}) {
  const [body, setBody] = useState("");

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <p className="label">Comments</p>
        {scan.comments.length === 0 ? (
          <p className="rounded-lg border border-dashed border-edge px-3 py-3 text-[11px] text-slate-500">
            No comments yet. Ask a reviewer or leave context on a finding.
          </p>
        ) : (
          scan.comments.map((comment) => (
            <div key={comment.id} className="rounded-lg border border-edge bg-white/[0.02] p-2.5">
              <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                <span className="font-semibold text-slate-300">{comment.author}</span>
                <span className="rounded bg-white/5 px-1 py-0.5 uppercase tracking-wider">
                  {comment.role}
                </span>
                <span className="ml-auto">{new Date(comment.created_at).toLocaleString()}</span>
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-slate-300">{comment.body}</p>
            </div>
          ))
        )}
        <textarea
          value={body}
          onChange={(event) => setBody(event.target.value)}
          rows={2}
          placeholder="Leave a general comment on this draft…"
          className="input text-xs"
        />
        <button
          onClick={() => {
            if (!body.trim()) return;
            onComment(null, body.trim());
            setBody("");
          }}
          disabled={busy || !body.trim()}
          className="btn-ghost w-full py-1.5 text-[11px]"
        >
          Post comment
        </button>
      </div>

      <div className="space-y-1.5">
        <p className="label">Audit trail</p>
        {scan.audit.length === 0 && (
          <p className="text-[11px] text-slate-500">No events recorded yet.</p>
        )}
        {[...scan.audit].reverse().map((event) => (
          <div key={event.id} className="flex gap-2 rounded-lg border border-edge/70 px-2.5 py-1.5">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-signal" />
            <div className="min-w-0">
              <p className="text-[11px] font-semibold text-slate-300">
                {event.action.replaceAll(".", " ")}
              </p>
              <p className="truncate text-[10px] text-slate-500">
                {event.actor} · {event.role} · {new Date(event.created_at).toLocaleString()}
              </p>
              {event.detail && <p className="mt-0.5 text-[10px] text-slate-400">{event.detail}</p>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RefreshIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M20 12a8 8 0 1 1-2.3-5.6M20 4v5h-5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="m5 13 4.5 4.5L19 7" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
