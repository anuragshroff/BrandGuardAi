"use client";

import type { Finding } from "@/lib/types";

const MARK_STYLES: Record<string, string> = {
  Critical: "bg-critical/20 text-red-50 decoration-critical/70",
  Warning: "bg-spark/20 text-amber-50 decoration-spark/70",
  Info: "bg-info/20 text-blue-50 decoration-info/70",
};

export default function HighlightedDraft({
  content,
  findings,
  selectedId,
  onSelect,
}: {
  content: string;
  findings: Finding[];
  selectedId: string | null;
  onSelect: (finding: Finding) => void;
}) {
  const marks = findings
    .filter(
      (finding) =>
        finding.status === "Unresolved" &&
        finding.start_index >= 0 &&
        finding.end_index > finding.start_index &&
        finding.end_index <= content.length,
    )
    .sort((a, b) => a.start_index - b.start_index);

  const nodes: React.ReactNode[] = [];
  let cursor = 0;

  marks.forEach((finding) => {
    if (finding.start_index < cursor) return; // skip overlapping mark
    if (finding.start_index > cursor) {
      nodes.push(<span key={`text-${cursor}`}>{content.slice(cursor, finding.start_index)}</span>);
    }
    nodes.push(
      <mark
        key={finding.id}
        data-selected={selectedId === finding.id}
        onClick={() => onSelect(finding)}
        className={`finding-mark border-b-2 ${MARK_STYLES[finding.severity]}`}
        title={`${finding.severity} · ${finding.issue_type}`}
      >
        {content.slice(finding.start_index, finding.end_index)}
      </mark>,
    );
    cursor = finding.end_index;
  });

  if (cursor < content.length) {
    nodes.push(<span key="tail">{content.slice(cursor)}</span>);
  }

  return (
    <article className="whitespace-pre-wrap font-[system-ui] text-[15px] leading-8 text-slate-300">
      {nodes}
    </article>
  );
}
