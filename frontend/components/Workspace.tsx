"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { AgentKey, Finding, Role, Scan } from "@/lib/types";
import {
  acceptFinding,
  addComment,
  approveScan,
  createScan,
  getScan,
  overrideFinding,
  publishScan,
} from "@/lib/api";
import { AUDIENCES, CAMPAIGNS, CHANNELS, REGIONS, SAMPLE_DRAFT, SAMPLE_TITLE } from "@/lib/sample";
import AppHeader from "./AppHeader";
import FindingsPanel from "./FindingsPanel";
import HighlightedDraft from "./HighlightedDraft";
import { Spinner, StatusChip } from "./ui";

const ACTOR = "Dhanraj Sonar";

export default function Workspace() {
  const [role, setRole] = useState<Role>("Creator");
  const [title, setTitle] = useState(SAMPLE_TITLE);
  const [content, setContent] = useState(SAMPLE_DRAFT);
  const [channel, setChannel] = useState(CHANNELS[0]);
  const [audience, setAudience] = useState(AUDIENCES[0]);
  const [region, setRegion] = useState(REGIONS[0]);
  const [campaign, setCampaign] = useState(CAMPAIGNS[0]);

  const [scan, setScan] = useState<Scan | null>(null);
  const [mode, setMode] = useState<"edit" | "review">("edit");
  const [activeTab, setActiveTab] = useState<AgentKey>("claim");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingScan, setLoadingScan] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("scan");
    if (!id) return;
    setLoadingScan(true);
    getScan(id)
      .then((loaded) => {
        setScan(loaded);
        setContent(loaded.raw_content);
        setTitle(loaded.document_title);
        setChannel(loaded.channel || CHANNELS[0]);
        setAudience(loaded.audience || AUDIENCES[0]);
        setRegion(loaded.region || REGIONS[0]);
        setCampaign(loaded.campaign || CAMPAIGNS[0]);
        setMode("review");
        focusFirst(loaded);
      })
      .catch((cause: Error) => setError(cause.message))
      .finally(() => setLoadingScan(false));
  }, []);

  const stats = useMemo(() => {
    const words = content.trim() ? content.trim().split(/\s+/).length : 0;
    return { words, characters: content.length };
  }, [content]);

  const dirty = scan !== null && content !== scan.raw_content;

  function focusFirst(target: Scan) {
    const open = target.findings.filter((finding) => finding.status === "Unresolved");
    const critical = open.find((finding) => finding.severity === "Critical");
    const next = critical ?? open[0];
    if (next) {
      setActiveTab(next.agent);
      setSelectedId(next.id);
    } else {
      setSelectedId(null);
    }
  }

  async function apply(operation: () => Promise<Scan>) {
    setBusy(true);
    setError(null);
    try {
      const updated = await operation();
      setScan(updated);
      setContent(updated.raw_content);
      return updated;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Something went wrong.");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function inspect() {
    if (!content.trim()) {
      setError("Add some draft content before running an inspection.");
      return;
    }
    const updated = await apply(() =>
      createScan({ title, content, channel, audience, region, campaign, actor: ACTOR, role }),
    );
    if (updated) {
      setMode("review");
      const open = updated.findings.filter((finding) => finding.status === "Unresolved");
      if (open.length > 0) {
        const first = open[0];
        setActiveTab(first.agent);
        setSelectedId(first.id);
      }
    }
  }

  function selectFinding(finding: Finding) {
    setSelectedId(finding.id);
    setActiveTab(finding.agent);
    setTimeout(() => {
      document
        .getElementById(`finding-${finding.id}`)
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, 40);
  }

  function loadFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!/\.(md|markdown|txt)$/i.test(file.name)) {
      setError("The demo reader supports Markdown and plain text files. Paste DOCX/PDF content instead.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setContent(String(reader.result ?? ""));
      setTitle(file.name.replace(/\.(md|markdown|txt)$/i, ""));
      setScan(null);
      setMode("edit");
      setSelectedId(null);
      setError(null);
    };
    reader.readAsText(file);
    event.target.value = "";
  }

  return (
    <div className="min-h-screen">
      <AppHeader role={role} onRoleChange={setRole} active="workspace" />

      <main className="mx-auto max-w-[1800px] px-3 py-3 lg:px-6 lg:py-4">
        <div className="grid gap-3 lg:h-[calc(100vh-5.5rem)] lg:grid-cols-[minmax(0,1fr)_430px] xl:grid-cols-[minmax(0,1fr)_470px]">
          <section className="flex min-h-[72vh] min-w-0 flex-col overflow-hidden rounded-2xl border border-edge bg-panel/85 backdrop-blur lg:min-h-0">
            <div className="flex items-start gap-3 border-b border-edge px-4 py-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-signal/15 text-signal">
                    <DocIcon />
                  </span>
                  <input
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    aria-label="Document title"
                    className="min-w-0 flex-1 truncate rounded-md border border-transparent bg-transparent px-1 py-0.5 text-sm font-bold text-white outline-none transition hover:border-edge focus:border-signal/60"
                  />
                  {scan && <StatusChip status={scan.status} />}
                  {dirty && (
                    <span className="chip border-spark/40 bg-spark/10 text-spark">Unsaved changes</span>
                  )}
                </div>
                <p className="mt-0.5 pl-9 text-[11px] text-slate-500">
                  {stats.words.toLocaleString()} words · {stats.characters.toLocaleString()} chars
                  {scan && <> · inspected {new Date(scan.created_at).toLocaleString()}</>}
                </p>
              </div>

              <div className="flex shrink-0 items-center gap-1.5">
                <div className="flex rounded-lg border border-edge bg-ink/60 p-0.5">
                  <button
                    onClick={() => setMode("edit")}
                    className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition ${
                      mode === "edit" ? "bg-white/10 text-white" : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    Draft
                  </button>
                  <button
                    onClick={() => scan && setMode("review")}
                    disabled={!scan}
                    className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition disabled:opacity-40 ${
                      mode === "review" ? "bg-white/10 text-white" : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    Review
                  </button>
                </div>
                <button onClick={() => fileRef.current?.click()} className="btn-ghost px-2.5 py-1.5 text-[11px]" title="Upload Markdown or text">
                  <UploadIcon />
                  Upload
                </button>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".md,.markdown,.txt"
                  onChange={loadFile}
                  className="hidden"
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-1.5 border-b border-edge bg-ink/30 px-4 py-2">
              <TagSelect label="Channel" value={channel} onChange={setChannel} options={CHANNELS} />
              <TagSelect label="Audience" value={audience} onChange={setAudience} options={AUDIENCES} />
              <TagSelect label="Region" value={region} onChange={setRegion} options={REGIONS} />
              <TagSelect label="Campaign" value={campaign} onChange={setCampaign} options={CAMPAIGNS} />
              <button
                onClick={() => {
                  setTitle(SAMPLE_TITLE);
                  setContent(SAMPLE_DRAFT);
                  setScan(null);
                  setMode("edit");
                  setSelectedId(null);
                  setError(null);
                }}
                className="ml-auto text-[10px] font-semibold uppercase tracking-wider text-slate-500 transition hover:text-signal"
              >
                Load sample draft
              </button>
            </div>

            <div className="relative min-h-0 flex-1 overflow-y-auto">
              <div className="mx-auto max-w-3xl px-5 py-6 sm:px-8">
                {loadingScan ? (
                  <p className="flex items-center gap-2 text-sm text-slate-400">
                    <Spinner /> Loading scan…
                  </p>
                ) : mode === "review" && scan ? (
                  <HighlightedDraft
                    content={scan.raw_content}
                    findings={scan.findings}
                    selectedId={selectedId}
                    onSelect={selectFinding}
                  />
                ) : (
                  <textarea
                    value={content}
                    onChange={(event) => setContent(event.target.value)}
                    spellCheck={false}
                    placeholder="Paste or write your draft here. Try the sample draft, then run the inspection."
                    className="h-full min-h-[42vh] w-full resize-none border-0 bg-transparent font-[system-ui] text-[15px] leading-8 text-slate-200 outline-none placeholder:text-slate-600"
                  />
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 border-t border-edge bg-ink/40 px-4 py-2.5">
              <div className="hidden items-center gap-1.5 text-[10px] text-slate-500 sm:flex">
                <span className="h-1.5 w-1.5 rounded-full bg-success" />
                Human-in-the-loop · nothing publishes automatically
              </div>
              {error && (
                <p role="alert" className="max-w-[45%] truncate text-[11px] text-red-300" title={error}>
                  {error}
                </p>
              )}
              <div className="ml-auto flex items-center gap-2">
                {dirty && (
                  <span className="hidden text-[10px] text-spark sm:inline">
                    Draft differs from last scan
                  </span>
                )}
                <button onClick={inspect} disabled={busy} className="btn-primary px-4 py-2 text-xs">
                  {busy ? <Spinner className="h-3.5 w-3.5" /> : <SparkIcon />}
                  {scan ? "Run new inspection" : "Run inspection"}
                </button>
              </div>
            </div>
          </section>

          {scan ? (
            <FindingsPanel
              scan={scan}
              role={role}
              activeTab={activeTab}
              onTabChange={setActiveTab}
              selectedId={selectedId}
              onSelect={selectFinding}
              busy={busy}
              error={error}
              onAccept={(finding) =>
                apply(() => acceptFinding(scan.id, finding, ACTOR, role))
              }
              onOverride={(finding, note) =>
                apply(() => overrideFinding(scan.id, finding.id, note, ACTOR, role))
              }
              onComment={(finding, body) =>
                apply(() => addComment(scan.id, body, ACTOR, role, finding?.id))
              }
              onApprove={() => apply(() => approveScan(scan.id, "Brand Manager", role))}
              onPublish={() => apply(() => publishScan(scan.id, "Brand Manager", role))}
              onRescan={inspect}
            />
          ) : (
            <AgentPreview content={content} onInspect={inspect} busy={busy} />
          )}
        </div>
      </main>
    </div>
  );
}

function AgentPreview({
  content,
  onInspect,
  busy,
}: {
  content: string;
  onInspect: () => void;
  busy: boolean;
}) {
  const agents = [
    { title: "Tone & Vocabulary", detail: "Reading grade, hype words, banned vocabulary", icon: "T" },
    { title: "Fact & Claims", detail: "RAG over approved facts, retired metrics, legal", icon: "F" },
    { title: "Visual Compliance", detail: "Logo clear space, palette, approved imagery", icon: "V" },
    { title: "Accessibility", detail: "Alt text, contrast, WCAG 2.1 AA link purpose", icon: "A" },
  ];

  return (
    <aside className="flex min-h-[60vh] flex-col overflow-hidden rounded-2xl border border-edge bg-panel/85 backdrop-blur lg:min-h-0">
      <div className="border-b border-edge px-4 py-3.5">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-bold text-white">AI Inspection Engine</h2>
          <span className="chip border-success/30 bg-success/10 text-success">Ready</span>
        </div>
        <p className="mt-0.5 text-[11px] text-slate-500">
          Four specialist agents run in parallel before publication.
        </p>
      </div>

      <div className="flex-1 space-y-2.5 overflow-y-auto p-4">
        {agents.map((agent) => (
          <div key={agent.title} className="flex items-start gap-3 rounded-xl border border-edge bg-white/[0.02] p-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-signal/10 text-xs font-bold text-signal ring-1 ring-signal/20">
              {agent.icon}
            </span>
            <div>
              <p className="text-xs font-bold text-slate-200">{agent.title}</p>
              <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{agent.detail}</p>
            </div>
          </div>
        ))}

        <div className="rounded-xl border border-dashed border-edge bg-ink/30 p-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">How it works</p>
          <ol className="mt-1.5 space-y-1.5 text-[11px] leading-relaxed text-slate-400">
            <li>1. Submit a draft with its channel, audience and region.</li>
            <li>2. Findings are matched to the exact guideline clause and approved fact.</li>
            <li>3. Accept a non-destructive fix, or override with a written justification.</li>
            <li>4. A Manager, Admin or Legal reviewer passes the approval gate.</li>
          </ol>
        </div>
      </div>

      <div className="border-t border-edge bg-ink/40 p-4">
        <div className="mb-2.5 flex items-center justify-between text-[11px]">
          <span className="text-slate-500">Draft length</span>
          <span className="font-semibold text-slate-300">
            {content.trim() ? content.trim().split(/\s+/).length.toLocaleString() : 0} words
          </span>
        </div>
        <button onClick={onInspect} disabled={busy} className="btn-primary w-full py-2.5 text-xs">
          {busy ? <Spinner className="h-3.5 w-3.5" /> : <SparkIcon />}
          Run multi-agent inspection
        </button>
        <p className="mt-2 text-center text-[10px] text-slate-600">
          Deterministic demo engine · no data leaves your machine
        </p>
      </div>
    </aside>
  );
}

function TagSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
}) {
  return (
    <label className="flex items-center gap-1.5 rounded-lg border border-edge bg-white/[0.02] px-2 py-1 text-[10px]">
      <span className="uppercase tracking-wider text-slate-500">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="max-w-[150px] bg-transparent text-[11px] font-semibold text-slate-200 outline-none"
      >
        {options.map((option) => (
          <option key={option} value={option} className="bg-panel">
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function DocIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M6 3h8l4 4v14H6V3Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M14 3v5h5M9 12h6M9 16h6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SparkIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M18.5 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2Z" fill="currentColor" />
    </svg>
  );
}
