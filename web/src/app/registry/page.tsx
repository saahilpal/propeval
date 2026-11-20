"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchPrompts, fetchFixtures, PromptVersion, ProjectFixture } from "@/lib/api";
import { FileText, Shield, ArrowLeft } from "lucide-react";

export default function RegistryPage() {
  const [prompts, setPrompts] = useState<PromptVersion[]>([]);
  const [fixtures, setFixtures] = useState<ProjectFixture[]>([]);
  const [activeTab, setActiveTab] = useState<"prompts" | "fixtures">("prompts");

  const [v1Prompt, setV1Prompt] = useState<PromptVersion | null>(null);
  const [v2Prompt, setV2Prompt] = useState<PromptVersion | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [pList, fList] = await Promise.all([fetchPrompts(), fetchFixtures()]);
        setPrompts(pList);
        setFixtures(fList);

        if (pList.length >= 2) {
          setV1Prompt(pList[0]);
          setV2Prompt(pList[1]);
        } else if (pList.length === 1) {
          setV1Prompt(pList[0]);
          setV2Prompt(pList[0]);
        }
      } catch (err) {
        console.error("Failed to load registry:", err);
      }
    }
    loadData();
  }, []);

  return (
    <div className="flex-1 flex flex-col p-6 max-w-7xl mx-auto w-full gap-6">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs font-mono text-ink-secondary hover:text-ink-primary px-2 py-1 rounded border border-border bg-surface"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Workbench</span>
          </Link>
          <h1 className="text-sm font-mono font-bold text-ink-primary uppercase tracking-wide">
            Prompt &amp; RERA Project Registry
          </h1>
        </div>

        {/* Tab switch */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <button
            onClick={() => setActiveTab("prompts")}
            className={`px-3 py-1.5 rounded border transition-colors ${
              activeTab === "prompts"
                ? "bg-ink-primary text-white border-ink-primary"
                : "bg-surface text-ink-secondary border-border hover:bg-gray-100"
            }`}
          >
            Prompt Versions ({prompts.length})
          </button>
          <button
            onClick={() => setActiveTab("fixtures")}
            className={`px-3 py-1.5 rounded border transition-colors ${
              activeTab === "fixtures"
                ? "bg-ink-primary text-white border-ink-primary"
                : "bg-surface text-ink-secondary border-border hover:bg-gray-100"
            }`}
          >
            RERA Fixtures ({fixtures.length})
          </button>
        </div>
      </div>

      {activeTab === "prompts" && (
        <div className="flex flex-col gap-6">
          {/* Side-by-Side Prompt Diff Section */}
          <section className="bg-surface border border-border rounded-md p-6 shadow-sm flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <h2 className="text-xs font-mono uppercase font-bold text-ink-secondary tracking-wider">
                Side-by-Side Prompt Version Diff
              </h2>
              <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
                <div className="flex items-center gap-2">
                  <span className="text-ink-secondary">V1:</span>
                  <select
                    value={v1Prompt?.id || ""}
                    onChange={(e) => setV1Prompt(prompts.find((p) => p.id === e.target.value) || null)}
                    className="border border-border rounded px-2 py-1 bg-canvas max-w-[200px] truncate"
                  >
                    {prompts.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.version_tag})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-ink-secondary">V2:</span>
                  <select
                    value={v2Prompt?.id || ""}
                    onChange={(e) => setV2Prompt(prompts.find((p) => p.id === e.target.value) || null)}
                    className="border border-border rounded px-2 py-1 bg-canvas max-w-[200px] truncate"
                  >
                    {prompts.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.version_tag})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-border rounded p-4 bg-canvas flex flex-col gap-2">
                <div className="flex items-center justify-between text-xs font-mono font-semibold text-ink-primary border-b border-border pb-1">
                  <span>{v1Prompt?.name || "V1 Prompt"}</span>
                  <span className="text-[11px] text-ink-secondary">{v1Prompt?.version_tag}</span>
                </div>
                <pre className="text-xs font-mono text-ink-secondary whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto">
                  {v1Prompt?.system_prompt || "No prompt registered"}
                </pre>
              </div>

              <div className="border border-border rounded p-4 bg-canvas flex flex-col gap-2">
                <div className="flex items-center justify-between text-xs font-mono font-semibold text-ink-primary border-b border-border pb-1">
                  <span>{v2Prompt?.name || "V2 Prompt"}</span>
                  <span className="text-[11px] text-ink-secondary">{v2Prompt?.version_tag}</span>
                </div>
                <pre className="text-xs font-mono text-ink-secondary whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto">
                  {v2Prompt?.system_prompt || "No prompt registered"}
                </pre>
              </div>
            </div>
          </section>

          {/* Prompt List */}
          <section className="bg-surface border border-border rounded-md shadow-sm overflow-hidden">
            <div className="overflow-x-auto w-full">
              <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-border bg-canvas text-ink-secondary font-mono text-[11px]">
                  <th className="py-2.5 px-4">Name</th>
                  <th className="py-2.5 px-4">Tag</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Model Provider</th>
                  <th className="py-2.5 px-4">Model ID</th>
                  <th className="py-2.5 px-4">SHA-256</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-mono">
                {prompts.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="py-2.5 px-4 font-semibold text-ink-primary">{p.name}</td>
                    <td className="py-2.5 px-4">{p.version_tag}</td>
                    <td className="py-2.5 px-4">
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-gray-100 text-ink-secondary border border-border">
                        {p.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-4">{p.model_provider}</td>
                    <td className="py-2.5 px-4">{p.model_id}</td>
                    <td className="py-2.5 px-4 text-ink-secondary text-[11px]">
                      {p.content_sha256.substring(0, 12)}...
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </section>
        </div>
      )}

      {activeTab === "fixtures" && (
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {fixtures.map((f) => (
            <div key={f.id} className="bg-surface border border-border rounded-md p-6 shadow-sm flex flex-col gap-3">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <div>
                  <h3 className="text-sm font-mono font-bold text-ink-primary">{f.project_name}</h3>
                  <p className="text-xs text-ink-secondary font-mono">{f.city}</p>
                </div>
                <div className="text-right">
                  <span className="text-xs font-mono font-bold text-accent-cobalt px-2 py-0.5 rounded bg-accent-cobaltBg border border-accent-cobalt/20">
                    {f.rera_id}
                  </span>
                  <div className="text-[10px] font-mono text-ink-secondary mt-1">
                    Effective: {f.effective_from}
                  </div>
                </div>
              </div>

              <pre className="text-xs font-mono bg-canvas border border-border rounded p-3 text-ink-secondary overflow-x-auto">
                {JSON.stringify(f.facts_json, null, 2)}
              </pre>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
