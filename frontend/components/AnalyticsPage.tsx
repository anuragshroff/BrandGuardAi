"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import type { Role, TrendPoint } from "@/lib/types";
import { getAnalytics, getGuidelines, uploadGuideline } from "@/lib/api";
import AppHeader from "./AppHeader";
import { Modal, SeverityChip, Spinner, StatusChip } from "./ui";

const CATEGORIES = ["Tone", "Vocabulary", "Claim", "Visual", "Accessibility"];

export default function AnalyticsPage() {
  const [role, setRole] = useState<Role>("Manager");
  const [uploadOpen, setUploadOpen] = useState(false);
  const queryClient = useQueryClient();

  const analyticsQuery = useQuery({ queryKey: ["analytics"], queryFn: getAnalytics });
  const guidelinesQuery = useQuery({ queryKey: ["guidelines"], queryFn: getGuidelines });

  const analytics = analyticsQuery.data;
  const guidelines = guidelinesQuery.data;

  const documents = useMemo(() => {
    const map = new Map<
      string,
      { title: string; category: string; chunks: number; latest: string; codes: string[] }
    >();
    for (const guideline of guidelines?.items ?? []) {
      const key = `${guideline.title}|${guideline.category}`;
      const current = map.get(key);
      if (current) {
        current.chunks += 1;
        current.codes.push(guideline.code);
        if (guideline.created_at > current.latest) current.latest = guideline.created_at;
      } else {
        map.set(key, {
          title: guideline.title,
          category: guideline.category,
          chunks: 1,
          latest: guideline.created_at,
          codes: [guideline.code],
        });
      }
    }
    return [...map.values()].sort((a, b) => b.chunks - a.chunks);
  }, [guidelines]);

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ["analytics"] });
    queryClient.invalidateQueries({ queryKey: ["guidelines"] });
  }

  return (
    <div className="min-h-screen">
      <AppHeader role={role} onRoleChange={setRole} active="analytics" />

      <main className="mx-auto max-w-[1600px] space-y-4 px-3 py-4 lg:px-6 lg:py-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="label">Governance insights</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-white">
              Brand health at a glance
            </h1>
            <p className="mt-1 max-w-2xl text-xs leading-relaxed text-slate-500">
              Overrides and recurring corrections expose ambiguous guidelines. Every metric below
              is computed from live scan and finding records.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={refresh} className="btn-ghost px-3 py-2 text-xs">
              <RefreshIcon />
              Refresh
            </button>
            <button onClick={() => setUploadOpen(true)} className="btn-primary px-3.5 py-2 text-xs">
              <PlusIcon />
              Upload policy
            </button>
          </div>
        </div>

        {analyticsQuery.isLoading && (
          <div className="panel flex items-center gap-3 px-5 py-10 text-sm text-slate-400">
            <Spinner /> Loading governance metrics…
          </div>
        )}

        {analyticsQuery.isError && (
          <div className="panel border-critical/30 px-5 py-6 text-sm text-red-200">
            Could not reach the BrandGuard API. Start the FastAPI service on port 8000 and refresh.
            <button onClick={refresh} className="btn-ghost ml-3 px-2 py-1 text-[11px]">
              Retry
            </button>
          </div>
        )}

        {analytics && (
          <>
            <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Kpi
                label="Total scans"
                value={analytics.totals.scans.toLocaleString()}
                hint={`${analytics.totals.open_findings} open findings`}
                accent="text-white"
              />
              <Kpi
                label="Compliance rate"
                value={`${analytics.totals.compliance_rate}%`}
                hint="Average across all scans"
                accent="text-success"
              />
              <Kpi
                label="Top violation"
                value={analytics.totals.top_violation}
                hint={`${analytics.totals.top_violation_share}% of all findings`}
                accent="text-critical"
              />
              <Kpi
                label="Avg resolution time"
                value={`${analytics.totals.avg_resolution_minutes} min`}
                hint={`${analytics.totals.guideline_chunks} guideline clauses indexed`}
                accent="text-spark"
              />
            </section>

            <section className="grid gap-3 xl:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
              <div className="panel p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="label">Rule violations over time</p>
                    <p className="text-sm font-semibold text-white">Last 30 days</p>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] font-semibold uppercase tracking-wider">
                    <Legend color="bg-critical" label="Critical" />
                    <Legend color="bg-spark" label="Warning" />
                    <Legend color="bg-info" label="Info" />
                  </div>
                </div>
                <TrendChart trend={analytics.trend} />
                <div className="mt-2 flex justify-between text-[10px] text-slate-600">
                  <span>{formatDay(analytics.trend[0]?.date)}</span>
                  <span>{formatDay(analytics.trend[Math.floor(analytics.trend.length / 2)]?.date)}</span>
                  <span>{formatDay(analytics.trend[analytics.trend.length - 1]?.date)}</span>
                </div>
              </div>

              <div className="panel p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="label">Inspector load</p>
                    <p className="text-sm font-semibold text-white">Findings by agent</p>
                  </div>
                  <span className="chip border-white/10 bg-white/[0.04] text-slate-400">
                    {Object.values(analytics.agents).reduce((sum, value) => sum + value, 0)} total
                  </span>
                </div>
                <AgentBars agents={analytics.agents} />
                <div className="mt-4 grid grid-cols-3 gap-2 border-t border-edge pt-3">
                  {(["Critical", "Warning", "Info"] as const).map((severity) => (
                    <div key={severity} className="rounded-lg border border-edge bg-white/[0.02] p-2">
                      <SeverityChip severity={severity} />
                      <p className="mt-1.5 text-lg font-bold text-white">
                        {analytics.severity[severity]}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="grid gap-3 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
              <div className="panel overflow-hidden">
                <div className="flex items-center justify-between border-b border-edge px-4 py-3">
                  <div>
                    <p className="label">Guideline clarity index</p>
                    <p className="text-sm font-semibold text-white">Rules most often overridden</p>
                  </div>
                  <span className="text-[10px] text-slate-500">clarity = 100 − override rate</span>
                </div>
                <div className="max-h-[340px] space-y-2 overflow-y-auto p-3">
                  {analytics.clarity.slice(0, 8).map((row) => (
                    <div
                      key={row.code}
                      className="rounded-xl border border-edge bg-white/[0.02] px-3 py-2.5"
                    >
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-white/5 px-1.5 py-0.5 text-[9px] font-bold tracking-wider text-slate-400">
                          {row.code}
                        </span>
                        <span className="truncate text-[11px] font-semibold text-slate-200">
                          {row.section}
                        </span>
                        <span className="ml-auto text-[11px] font-bold text-white">{row.clarity}</span>
                      </div>
                      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/5">
                        <div
                          className={`h-full rounded-full ${
                            row.clarity >= 90 ? "bg-success" : row.clarity >= 70 ? "bg-spark" : "bg-critical"
                          }`}
                          style={{ width: `${Math.max(2, row.clarity)}%` }}
                        />
                      </div>
                      <p className="mt-1 text-[10px] text-slate-500">
                        {row.findings} findings · {row.overrides} overrides · {row.category}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="panel overflow-hidden">
                <div className="flex items-center justify-between border-b border-edge px-4 py-3">
                  <div>
                    <p className="label">Recent scans</p>
                    <p className="text-sm font-semibold text-white">Latest submissions</p>
                  </div>
                  <Link href="/" className="text-[11px] font-semibold text-signal hover:underline">
                    Open workspace
                  </Link>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-ink/40 text-[9px] uppercase tracking-[0.14em] text-slate-500">
                      <tr>
                        <th className="px-4 py-2 font-semibold">Draft</th>
                        <th className="px-2 py-2 font-semibold">Status</th>
                        <th className="px-2 py-2 font-semibold">Score</th>
                        <th className="px-4 py-2 text-right font-semibold">Open</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analytics.recent_scans.map((scan) => (
                        <tr key={scan.id} className="table-row">
                          <td className="max-w-[240px] px-4 py-2.5">
                            <Link href={`/?scan=${scan.id}`} className="block truncate font-semibold text-slate-200 hover:text-signal">
                              {scan.title}
                            </Link>
                            <span className="text-[10px] text-slate-500">
                              {scan.channel} · {new Date(scan.created_at).toLocaleDateString()}
                            </span>
                          </td>
                          <td className="px-2 py-2.5">
                            <StatusChip status={scan.status} />
                          </td>
                          <td className="px-2 py-2.5">
                            <span
                              className={`font-bold ${
                                scan.compliance_score >= 85
                                  ? "text-success"
                                  : scan.compliance_score >= 60
                                    ? "text-spark"
                                    : "text-critical"
                              }`}
                            >
                              {scan.compliance_score}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-right font-semibold text-slate-300">
                            {scan.unresolved}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>

            <section className="panel overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-edge px-4 py-3">
                <div>
                  <p className="label">Brand knowledge base</p>
                  <p className="text-sm font-semibold text-white">Vector index manager</p>
                  <p className="mt-0.5 text-[10px] text-slate-500">
                    {guidelines?.total_chunks ?? analytics.totals.guideline_chunks} clauses indexed
                    across {documents.length} sources · {analytics.knowledge_base.by_category.Claim ?? 0} claim rules
                  </p>
                </div>
                <button onClick={() => setUploadOpen(true)} className="btn-ghost px-3 py-1.5 text-[11px]">
                  <PlusIcon /> Add guideline
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-ink/40 text-[9px] uppercase tracking-[0.14em] text-slate-500">
                    <tr>
                      <th className="px-4 py-2.5 font-semibold">Source</th>
                      <th className="px-3 py-2.5 font-semibold">Category</th>
                      <th className="px-3 py-2.5 font-semibold">Vector chunks</th>
                      <th className="px-3 py-2.5 font-semibold">Index status</th>
                      <th className="px-4 py-2.5 text-right font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map((document) => (
                      <tr key={`${document.title}-${document.category}`} className="table-row">
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/5 text-[10px] font-bold text-slate-400">
                              {document.title.slice(0, 2).toUpperCase()}
                            </span>
                            <div className="min-w-0">
                              <p className="truncate font-semibold text-slate-200">{document.title}</p>
                              <p className="truncate text-[10px] text-slate-500">
                                {document.codes.slice(0, 3).join(", ")}
                                {document.codes.length > 3 ? ` +${document.codes.length - 3}` : ""}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-3 py-2.5 text-slate-400">{document.category}</td>
                        <td className="px-3 py-2.5 font-semibold text-slate-300">{document.chunks}</td>
                        <td className="px-3 py-2.5">
                          <span className="chip border-success/40 bg-success/10 text-success">
                            Indexed
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <button
                            onClick={refresh}
                            className="text-[11px] font-semibold text-signal hover:underline"
                          >
                            Re-sync
                          </button>
                        </td>
                      </tr>
                    ))}
                    {documents.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                          No guidelines indexed yet. Upload a policy document to begin.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            <p className="pb-2 text-center text-[10px] text-slate-600">
              Tenant-isolated · zero retraining on customer content · every action is audit-logged
            </p>
          </>
        )}
      </main>

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUploaded={() => {
          refresh();
          setUploadOpen(false);
        }}
      />
    </div>
  );
}

function Kpi({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint: string;
  accent: string;
}) {
  return (
    <div className="panel relative overflow-hidden p-4">
      <div className="absolute -right-6 -top-6 h-20 w-20 rounded-full bg-signal/10 blur-2xl" />
      <p className="label">{label}</p>
      <p className={`mt-1.5 truncate text-xl font-bold tracking-tight ${accent}`} title={value}>
        {value}
      </p>
      <p className="mt-1 text-[10px] text-slate-500">{hint}</p>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-slate-500">
      <span className={`h-1.5 w-3 rounded-full ${color}`} />
      {label}
    </span>
  );
}

function TrendChart({ trend }: { trend: TrendPoint[] }) {
  const width = 720;
  const height = 210;
  const padX = 26;
  const padY = 18;
  const max = Math.max(
    4,
    ...trend.map((point) => Math.max(point.Critical, point.Warning, point.Info)),
  );

  const x = (index: number) => padX + (index * (width - padX * 2)) / Math.max(1, trend.length - 1);
  const y = (value: number) => height - padY - (value / max) * (height - padY * 2);

  const line = (key: keyof Omit<TrendPoint, "date">) =>
    trend.map((point, index) => `${x(index)},${y(point[key])}`).join(" ");

  const grid = [0, 0.25, 0.5, 0.75, 1];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="mt-3 w-full" role="img" aria-label="Violations over the last 30 days">
      <defs>
        <linearGradient id="criticalFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FF6B6B" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#FF6B6B" stopOpacity="0" />
        </linearGradient>
      </defs>
      {grid.map((fraction) => (
        <line
          key={fraction}
          x1={padX}
          x2={width - padX}
          y1={padY + fraction * (height - padY * 2)}
          y2={padY + fraction * (height - padY * 2)}
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="1"
        />
      ))}
      <polygon
        points={`${padX},${height - padY} ${line("Critical")} ${width - padX},${height - padY}`}
        fill="url(#criticalFill)"
      />
      <polyline points={line("Info")} fill="none" stroke="#63A4FF" strokeWidth="1.6" strokeOpacity="0.8" />
      <polyline points={line("Warning")} fill="none" stroke="#F5B700" strokeWidth="1.8" />
      <polyline points={line("Critical")} fill="none" stroke="#FF6B6B" strokeWidth="2.2" />
    </svg>
  );
}

function AgentBars({ agents }: { agents: Record<string, number> }) {
  const max = Math.max(1, ...Object.values(agents));
  const colors = ["bg-signal", "bg-critical", "bg-spark", "bg-success"];
  return (
    <div className="mt-4 space-y-3">
      {Object.entries(agents).map(([label, value], index) => (
        <div key={label}>
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-semibold text-slate-300">{label}</span>
            <span className="text-slate-500">{value}</span>
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-white/5">
            <div
              className={`h-full rounded-full ${colors[index % colors.length]}`}
              style={{ width: `${Math.max(2, (value / max) * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function UploadModal({
  open,
  onClose,
  onUploaded,
}: {
  open: boolean;
  onClose: () => void;
  onUploaded: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState("Tone");
  const [title, setTitle] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const mutation = useMutation({
    mutationFn: () =>
      uploadGuideline(file as File, category, title || file?.name?.replace(/\.[^.]+$/, "") || "Uploaded policy"),
    onSuccess: () => {
      setFile(null);
      setTitle("");
      onUploaded();
    },
  });

  return (
    <Modal open={open} onClose={onClose} title="Upload policy document">
      <div className="space-y-3">
        <button
          onClick={() => fileRef.current?.click()}
          className="flex w-full flex-col items-center gap-1.5 rounded-xl border border-dashed border-edge bg-white/[0.02] px-4 py-8 text-center transition hover:border-signal/50 hover:bg-white/[0.04]"
        >
          <UploadIcon />
          <span className="text-xs font-semibold text-slate-200">
            {file ? file.name : "Drop a file or click to browse"}
          </span>
          <span className="text-[10px] text-slate-500">
            Markdown, TXT and plain-text policies are chunked by heading
          </span>
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".md,.markdown,.txt"
          className="hidden"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-1">
            <span className="label">Source title</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Global Brand Guidelines 2027"
              className="input"
            />
          </label>
          <label className="space-y-1">
            <span className="label">Category</span>
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              className="input"
            >
              {CATEGORIES.map((item) => (
                <option key={item} value={item} className="bg-panel">
                  {item}
                </option>
              ))}
            </select>
          </label>
        </div>

        {mutation.isError && (
          <p className="rounded-lg border border-critical/40 bg-critical/10 px-3 py-2 text-[11px] text-red-200">
            {(mutation.error as Error).message}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onClose} className="btn-ghost px-3 py-2 text-xs">
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!file || mutation.isPending}
            className="btn-primary px-3.5 py-2 text-xs"
          >
            {mutation.isPending ? <Spinner /> : <UploadIcon />}
            Index document
          </button>
        </div>
      </div>
    </Modal>
  );
}

function formatDay(value?: string) {
  if (!value) return "";
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function RefreshIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M20 12a8 8 0 1 1-2.3-5.6M20 4v5h-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden className="text-signal">
      <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
