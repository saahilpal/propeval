"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Navbar } from "@/components/Navbar";
import { PromptEditorPair } from "@/components/PromptEditorPair";
import { PersonaSelector, PersonaItem } from "@/components/PersonaSelector";
import { ExpectedBehaviorList, ExpectedRuleItem } from "@/components/ExpectedBehaviorList";
import { ComparisonVerdict } from "@/components/ComparisonVerdict";
import { SideBySideCallView, TurnComparisonData } from "@/components/SideBySideCallView";
import { Play, RotateCw, AlertCircle, Sparkles } from "lucide-react";

interface CompareApiResponse {
  score_a: number;
  status_a: string;
  score_b: number;
  status_b: string;
  winner: string;
  summary_bullets: string[];
  comparisons: TurnComparisonData[];
  latency_ms: number;
  run_id: string;
}

export default function IndianCustomerPromptSimulator() {
  const [promptA, setPromptA] = useState<string>("");
  const [promptB, setPromptB] = useState<string>("");
  const [personas, setPersonas] = useState<PersonaItem[]>([]);
  const [selectedPersonaIds, setSelectedPersonaIds] = useState<string[]>([]);
  const [rules, setRules] = useState<ExpectedRuleItem[]>([]);
  const [customBuyerMessage, setCustomBuyerMessage] = useState<string>("");
  const [customRule, setCustomRule] = useState<string>("");

  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [progressText, setProgressText] = useState<string>("");
  const [verdict, setVerdict] = useState<CompareApiResponse | null>(null);
  const [activePersonaId, setActivePersonaId] = useState<string>("angry_dnc");
  const [error, setError] = useState<string | null>(null);

  // 1. Initial Load: Fetch Personas, Default Prompts, and Rules
  useEffect(() => {
    async function loadInitialData() {
      try {
        const res = await fetch("/api/v1/personas");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        setPromptA(data.default_prompt_a);
        setPromptB(data.default_prompt_b);
        setPersonas(data.personas);
        setSelectedPersonaIds(data.personas.map((p: PersonaItem) => p.id));
        setRules(data.default_expected_behaviors);

        // Immediate first-run simulation for instant feedback
        runSimulation(
          data.default_prompt_a,
          data.default_prompt_b,
          data.personas.map((p: PersonaItem) => p.id),
          ""
        );
      } catch (err: any) {
        setError(`Failed to load initial persona configuration: ${err.message}`);
      }
    }
    loadInitialData();
  }, []);

  // 2. Simulation Runner
  const runSimulation = async (
    pA: string,
    pB: string,
    personaIds: string[],
    customMsg: string
  ) => {
    if (!pA.trim() || !pB.trim()) {
      setError("Both Prompt A and Prompt B must be non-empty.");
      return;
    }
    if (personaIds.length === 0 && !customMsg.trim()) {
      setError("Please select at least one customer persona.");
      return;
    }

    setIsSimulating(true);
    setError(null);
    setProgressText("Simulating customer interactions & evaluating rules...");

    try {
      const res = await fetch("/api/v1/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt_a: pA,
          prompt_b: pB,
          persona_ids: personaIds,
          custom_buyer_message: customMsg.trim() || null,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `HTTP ${res.status}`);
      }

      const data: CompareApiResponse = await res.json();
      setVerdict(data);
      if (data.comparisons.length > 0) {
        // Keep current active persona if still in results, else pick first
        if (!data.comparisons.some((c) => c.persona_id === activePersonaId)) {
          setActivePersonaId(data.comparisons[0].persona_id);
        }
      }
    } catch (err: any) {
      setError(`Simulation failed: ${err.message}`);
    } finally {
      setIsSimulating(false);
      setProgressText("");
    }
  };

  // 3. User Trigger: Simulate & Judge
  const handleSimulate = useCallback(() => {
    runSimulation(promptA, promptB, selectedPersonaIds, customBuyerMessage);
  }, [promptA, promptB, selectedPersonaIds, customBuyerMessage]);

  // 4. Keyboard Shortcut: ⌘+Enter or Ctrl+Enter to trigger simulation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        handleSimulate();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleSimulate]);

  // Handlers for Persona & Rule Toggles
  const handleTogglePersona = (id: string) => {
    setSelectedPersonaIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const handleToggleRule = (id: string) => {
    setRules((prev) =>
      prev.map((r) => (r.id === id ? { ...r, checked: !r.checked } : r))
    );
  };

  const handleAddCustomRule = () => {
    if (!customRule.trim()) return;
    const newRuleItem: ExpectedRuleItem = {
      id: `rule_custom_${Date.now()}`,
      label: customRule.trim(),
      description: "Custom user-defined behavior expectation.",
      checked: true,
    };
    setRules((prev) => [...prev, newRuleItem]);
    setCustomRule("");
  };

  const handleResetDefaults = async () => {
    try {
      const res = await fetch("/api/v1/personas");
      if (res.ok) {
        const data = await res.json();
        setPromptA(data.default_prompt_a);
        setPromptB(data.default_prompt_b);
        setSelectedPersonaIds(data.personas.map((p: PersonaItem) => p.id));
        setCustomBuyerMessage("");
        runSimulation(
          data.default_prompt_a,
          data.default_prompt_b,
          data.personas.map((p: PersonaItem) => p.id),
          ""
        );
      }
    } catch {}
  };

  return (
    <div className="min-h-screen bg-canvas text-ink-primary flex flex-col font-sans">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Header & Mission Statement */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-ink-primary flex items-center gap-2">
              <span>Indian Customer Prompt Simulator</span>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                Hinglish Voice-AI
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-ink-secondary mt-1">
              Compare two voice-agent prompts side by side against realistic Indian buyer personas.
              Inspect rule breaches and verify compliance before production deployment.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSimulate}
              disabled={isSimulating}
              className="w-full sm:w-auto px-5 py-2.5 bg-ink-primary hover:bg-slate-800 text-white text-xs sm:text-sm font-semibold rounded-md shadow-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              {isSimulating ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Simulating...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Simulate &amp; Judge</span>
                  <span className="hidden sm:inline text-[10px] font-mono bg-white/20 px-1.5 py-0.2 rounded text-slate-200 ml-1">
                    ⌘↵
                  </span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error notification banner */}
        {error && (
          <div className="p-3 rounded-md bg-red-50 border border-red-200 text-xs text-accent-crimson flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Live Simulation Progress Banner */}
        {isSimulating && progressText && (
          <div className="p-3 rounded-md bg-blue-50 border border-blue-200 text-xs text-blue-700 flex items-center gap-2">
            <RotateCw className="w-4 h-4 animate-spin text-blue-600 shrink-0" />
            <span className="font-medium">{progressText}</span>
          </div>
        )}

        {/* 1. Prompt Pair Editor */}
        <section aria-label="Prompt Editor">
          <PromptEditorPair
            promptA={promptA}
            setPromptA={setPromptA}
            promptB={promptB}
            setPromptB={setPromptB}
            onResetDefaults={handleResetDefaults}
          />
        </section>

        {/* 2. Indian Buyer Persona Selector */}
        <section aria-label="Customer Personas">
          <PersonaSelector
            personas={personas}
            selectedIds={selectedPersonaIds}
            onToggle={handleTogglePersona}
            customMessage={customBuyerMessage}
            setCustomMessage={setCustomBuyerMessage}
          />
        </section>

        {/* 3. Expected Behavior Rules */}
        <section aria-label="Expected Behaviors">
          <ExpectedBehaviorList
            rules={rules}
            onToggleRule={handleToggleRule}
            customRule={customRule}
            setCustomRule={setCustomRule}
            onAddCustomRule={handleAddCustomRule}
          />
        </section>

        {/* 4. Verdict & Side-by-Side Call Comparison */}
        {verdict && (
          <section aria-label="Comparison Results" className="space-y-4 pt-2">
            <ComparisonVerdict
              scoreA={verdict.score_a}
              statusA={verdict.status_a}
              scoreB={verdict.score_b}
              statusB={verdict.status_b}
              winner={verdict.winner}
              summaryBullets={verdict.summary_bullets}
              latencyMs={verdict.latency_ms}
              onReRun={handleSimulate}
              isSimulating={isSimulating}
            />

            <SideBySideCallView
              comparisons={verdict.comparisons}
              activePersonaId={activePersonaId}
              setActivePersonaId={setActivePersonaId}
            />
          </section>
        )}
      </main>

      <footer className="border-t border-border bg-surface py-3 px-4 sm:px-8 text-center text-[11px] font-mono text-slate-400">
        PropEval v1.0.0 · Local Indian Real-Estate Voice AI Prompt Evaluation · Zero Bloat
      </footer>
    </div>
  );
}
