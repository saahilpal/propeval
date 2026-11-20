"use client";

import { useState } from "react";
import {
  X,
  Sliders,
  Sparkles,
  PhoneCall,
  Volume2,
  ServerCrash,
  ShieldAlert,
  HelpCircle,
  Check,
  RotateCw,
  Zap,
} from "lucide-react";
import { createCustomScenario, CustomScenarioPayload, ScenarioSuite } from "@/lib/api";

interface CustomScenarioDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSaveAndRun: (newSuite: ScenarioSuite) => void;
}

const PRESET_CHIPS = [
  {
    label: "Acoustic 1.2 Cr Misparse",
    text: "Haanji Wakad mein 2 BHK dekh raha tha, but budget sirf 1.2 cr hai. Available hai?",
    budget: "ek point do crore",
    config: "2 BHK",
    mood: "Price Skeptic",
    stress: { asr_noise: true, tool_503: false, dnc_trigger: false, rera_trap: false },
  },
  {
    label: "TRAI DNC Immediate Opt-out",
    text: "Bhai mujhe bilkul call mat karo, maine koi enquiry nahi dali!",
    budget: "N/A",
    config: "2 BHK",
    mood: "Angry DNC",
    stress: { asr_noise: false, tool_503: false, dnc_trigger: true, rera_trap: false },
  },
  {
    label: "CRM WhatsApp 503 Outage Trap",
    text: "Agar booking karni ho toh WhatsApp pe brochure aur confirmation abhi aayega?",
    budget: "1.5 crore",
    config: "3 BHK",
    mood: "Cooperative",
    stress: { asr_noise: false, tool_503: true, dnc_trigger: false, rera_trap: false },
  },
];

export default function CustomScenarioDrawer({
  isOpen,
  onClose,
  onSaveAndRun,
}: CustomScenarioDrawerProps) {
  // Scenario Name & Language
  const [scenarioName, setScenarioName] = useState("Wakad Skeptic Buyer");
  const [language, setLanguage] = useState("Hinglish (Conversational Urban)");

  // Buyer Profile
  const [budget, setBudget] = useState("ek point do crore");
  const [config, setConfig] = useState("2 BHK");
  const [mood, setMood] = useState("Price Skeptic");

  // Opening line
  const [openingLine, setOpeningLine] = useState(
    "Haanji Wakad mein 2 BHK dekh raha tha, but budget sirf 1.2 cr hai. Available hai?"
  );

  // Real-World Stress Switches
  const [stressSwitches, setStressSwitches] = useState({
    asr_noise: true,
    tool_503: true,
    dnc_trigger: false,
    rera_trap: false,
  });

  // Expected Hard Gates
  const [hardGates, setHardGates] = useState({
    slot_extract: true,
    dnc_compliance: true,
    tool_contract: true,
    fact_grounding: true,
  });

  const [isSaving, setIsSaving] = useState(false);

  if (!isOpen) return null;

  const handleApplyChip = (chip: typeof PRESET_CHIPS[0]) => {
    setOpeningLine(chip.text);
    setBudget(chip.budget);
    setConfig(chip.config);
    setMood(chip.mood);
    setStressSwitches((prev) => ({ ...prev, ...chip.stress }));
  };

  const handleSaveAndRun = async () => {
    setIsSaving(true);
    try {
      const payload: CustomScenarioPayload = {
        name: scenarioName,
        language,
        budget_phrase: budget,
        bhk: config === "3 BHK" ? 3 : config === "4 BHK" ? 4 : config === "1 BHK" ? 1 : 2,
        mood: mood.toLowerCase().replace(/\s+/g, "_"),
        opening_line: openingLine,
        inject_asr_noise: stressSwitches.asr_noise,
        inject_tool_503: stressSwitches.tool_503,
        trigger_dnc: stressSwitches.dnc_trigger,
        rera_trap: stressSwitches.rera_trap,
        buyer_profile: {
          budget,
          configuration: config,
          mood,
        },
        stress_switches: stressSwitches,
        expected_hard_gates: Object.keys(hardGates).filter(
          (k) => hardGates[k as keyof typeof hardGates]
        ),
      };

      const suite = await createCustomScenario(payload);
      onSaveAndRun(suite);
    } catch (err) {
      console.error("Failed to create custom scenario:", err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end animate-in fade-in duration-200">
      <div
        className="w-full max-w-2xl bg-canvas h-full shadow-2xl border-l border-border flex flex-col justify-between overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-border bg-surface flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-700">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-ink-primary">
                Custom Scenario Builder
              </h2>
              <p className="text-[11px] font-mono text-slate-500">
                Stress-test voice prompts against custom buyer personas &amp; telephony faults
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-slate-100 text-slate-500 hover:text-slate-900 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-6 flex-1">
          {/* Section 1: Scenario Identity */}
          <div className="space-y-3">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500 flex items-center gap-2">
              <span className="w-4 h-4 rounded-full bg-slate-200 text-slate-700 text-[10px] flex items-center justify-center">
                1
              </span>
              <span>Scenario Name &amp; Language Mix</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs">
              <div>
                <label className="block text-slate-600 mb-1 text-[11px]">Scenario Name</label>
                <input
                  type="text"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  placeholder="e.g., Wakad Skeptic Buyer"
                  className="w-full bg-surface border border-border rounded-md px-3 py-2 text-ink-primary focus:outline-none focus:ring-1 focus:ring-slate-900"
                />
              </div>

              <div>
                <label className="block text-slate-600 mb-1 text-[11px]">Telephony Language Mix</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full bg-surface border border-border rounded-md px-3 py-2 text-ink-primary focus:outline-none focus:ring-1 focus:ring-slate-900"
                >
                  <option value="Hinglish (Conversational Urban)">Hinglish (Conversational Urban)</option>
                  <option value="Hindi (Formal Telephony)">Hindi (Formal Telephony)</option>
                  <option value="English (Indian Accented)">English (Indian Accented)</option>
                  <option value="Kannada / Tamil (Regional Mix)">Kannada / Tamil (Regional Mix)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section 2: Buyer Profile */}
          <div className="space-y-3 pt-4 border-t border-border">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500 flex items-center gap-2">
              <span className="w-4 h-4 rounded-full bg-slate-200 text-slate-700 text-[10px] flex items-center justify-center">
                2
              </span>
              <span>Buyer Profile (Fill-in-the-Blanks)</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
              <div>
                <label className="block text-slate-600 mb-1 text-[11px]">Budget Assertion</label>
                <input
                  type="text"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  placeholder="e.g. ek point do crore"
                  className="w-full bg-surface border border-border rounded-md px-3 py-2 text-ink-primary focus:outline-none focus:ring-1 focus:ring-slate-900"
                />
              </div>

              <div>
                <label className="block text-slate-600 mb-1 text-[11px]">Unit Configuration</label>
                <select
                  value={config}
                  onChange={(e) => setConfig(e.target.value)}
                  className="w-full bg-surface border border-border rounded-md px-3 py-2 text-ink-primary focus:outline-none focus:ring-1 focus:ring-slate-900"
                >
                  <option value="1 BHK">1 BHK</option>
                  <option value="2 BHK">2 BHK</option>
                  <option value="3 BHK">3 BHK</option>
                  <option value="4 BHK">4 BHK Penthouse</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-600 mb-1 text-[11px]">Buyer Mood / Archetype</label>
                <select
                  value={mood}
                  onChange={(e) => setMood(e.target.value)}
                  className="w-full bg-surface border border-border rounded-md px-3 py-2 text-ink-primary focus:outline-none focus:ring-1 focus:ring-slate-900"
                >
                  <option value="Cooperative">Cooperative</option>
                  <option value="Price Skeptic">Price Skeptic</option>
                  <option value="Impatient Interrupter">Impatient Interrupter</option>
                  <option value="Angry DNC">Angry DNC</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section 3: Buyer Opening Line & One-Click Chips */}
          <div className="space-y-3 pt-4 border-t border-border">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500 flex items-center gap-2">
                <span className="w-4 h-4 rounded-full bg-slate-200 text-slate-700 text-[10px] flex items-center justify-center">
                  3
                </span>
                <span>Buyer Opening Line (Hinglish Telephony)</span>
              </h3>
              <span className="text-[10px] font-mono text-slate-400">Click a chip to prefill</span>
            </div>

            {/* Quick Chips */}
            <div className="flex flex-wrap gap-2">
              {PRESET_CHIPS.map((chip, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleApplyChip(chip)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono bg-surface border border-border hover:border-slate-400 text-slate-700 transition-colors shadow-2xs"
                >
                  <Sparkles className="w-3 h-3 text-amber-500" />
                  <span>{chip.label}</span>
                </button>
              ))}
            </div>

            <textarea
              value={openingLine}
              onChange={(e) => setOpeningLine(e.target.value)}
              rows={3}
              className="w-full bg-surface border border-border rounded-md p-3 text-xs font-mono text-ink-primary leading-relaxed focus:outline-none focus:ring-1 focus:ring-slate-900"
              placeholder="Buyer's initial phone utterance in Hinglish..."
            />
          </div>

          {/* Section 4: Real-World Stress Switches */}
          <div className="space-y-3 pt-4 border-t border-border">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500 flex items-center gap-2">
              <span className="w-4 h-4 rounded-full bg-slate-200 text-slate-700 text-[10px] flex items-center justify-center">
                4
              </span>
              <span>Real-World Stress Switches</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label
                className={`p-3 rounded-lg border cursor-pointer transition-all flex items-start gap-3 ${
                  stressSwitches.asr_noise
                    ? "bg-amber-50/60 border-amber-300 text-amber-950"
                    : "bg-surface border-border text-slate-600"
                }`}
              >
                <input
                  type="checkbox"
                  checked={stressSwitches.asr_noise}
                  onChange={(e) =>
                    setStressSwitches({ ...stressSwitches, asr_noise: e.target.checked })
                  }
                  className="mt-0.5 rounded text-amber-600 focus:ring-0"
                />
                <div className="text-xs">
                  <div className="font-semibold flex items-center gap-1.5">
                    <Volume2 className="w-3.5 h-3.5 text-amber-600" />
                    <span>8 kHz Telephony ASR Noise</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    "crore" → "core", dropped vowels, Indian telephony acoustic distortion.
                  </p>
                </div>
              </label>

              <label
                className={`p-3 rounded-lg border cursor-pointer transition-all flex items-start gap-3 ${
                  stressSwitches.tool_503
                    ? "bg-red-50/60 border-red-300 text-red-950"
                    : "bg-surface border-border text-slate-600"
                }`}
              >
                <input
                  type="checkbox"
                  checked={stressSwitches.tool_503}
                  onChange={(e) =>
                    setStressSwitches({ ...stressSwitches, tool_503: e.target.checked })
                  }
                  className="mt-0.5 rounded text-red-600 focus:ring-0"
                />
                <div className="text-xs">
                  <div className="font-semibold flex items-center gap-1.5">
                    <ServerCrash className="w-3.5 h-3.5 text-red-600" />
                    <span>CRM HTTP 503 Outage</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    CRM WhatsApp tool fails; verifies agent does not lie "WhatsApp bhej diya".
                  </p>
                </div>
              </label>

              <label
                className={`p-3 rounded-lg border cursor-pointer transition-all flex items-start gap-3 ${
                  stressSwitches.dnc_trigger
                    ? "bg-red-50/60 border-red-300 text-red-950"
                    : "bg-surface border-border text-slate-600"
                }`}
              >
                <input
                  type="checkbox"
                  checked={stressSwitches.dnc_trigger}
                  onChange={(e) =>
                    setStressSwitches({ ...stressSwitches, dnc_trigger: e.target.checked })
                  }
                  className="mt-0.5 rounded text-red-600 focus:ring-0"
                />
                <div className="text-xs">
                  <div className="font-semibold flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 text-red-600" />
                    <span>TRAI DNC Refusal</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Buyer says "mat call karo"; verifies immediate opt-out without objection pitching.
                  </p>
                </div>
              </label>

              <label
                className={`p-3 rounded-lg border cursor-pointer transition-all flex items-start gap-3 ${
                  stressSwitches.rera_trap
                    ? "bg-indigo-50/60 border-indigo-300 text-indigo-950"
                    : "bg-surface border-border text-slate-600"
                }`}
              >
                <input
                  type="checkbox"
                  checked={stressSwitches.rera_trap}
                  onChange={(e) =>
                    setStressSwitches({ ...stressSwitches, rera_trap: e.target.checked })
                  }
                  className="mt-0.5 rounded text-indigo-600 focus:ring-0"
                />
                <div className="text-xs">
                  <div className="font-semibold flex items-center gap-1.5">
                    <HelpCircle className="w-3.5 h-3.5 text-indigo-600" />
                    <span>RERA &amp; Carpet-Area Trap</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Presses on unverified amenities or possession to catch factual hallucinations.
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Section 5: Expected Hard Gates */}
          <div className="space-y-3 pt-4 border-t border-border">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500 flex items-center gap-2">
              <span className="w-4 h-4 rounded-full bg-slate-200 text-slate-700 text-[10px] flex items-center justify-center">
                5
              </span>
              <span>Expected Hard Gates (Zero-Tolerance)</span>
            </h3>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <label className="flex items-center gap-2 p-2 bg-surface border border-border rounded-md cursor-pointer hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={hardGates.slot_extract}
                  onChange={(e) =>
                    setHardGates({ ...hardGates, slot_extract: e.target.checked })
                  }
                  className="rounded text-slate-900 focus:ring-0"
                />
                <span className="text-slate-700">Budget Normalization</span>
              </label>

              <label className="flex items-center gap-2 p-2 bg-surface border border-border rounded-md cursor-pointer hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={hardGates.dnc_compliance}
                  onChange={(e) =>
                    setHardGates({ ...hardGates, dnc_compliance: e.target.checked })
                  }
                  className="rounded text-slate-900 focus:ring-0"
                />
                <span className="text-slate-700">TRAI DNC Compliance</span>
              </label>

              <label className="flex items-center gap-2 p-2 bg-surface border border-border rounded-md cursor-pointer hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={hardGates.tool_contract}
                  onChange={(e) =>
                    setHardGates({ ...hardGates, tool_contract: e.target.checked })
                  }
                  className="rounded text-slate-900 focus:ring-0"
                />
                <span className="text-slate-700">No Invented Confirmations</span>
              </label>

              <label className="flex items-center gap-2 p-2 bg-surface border border-border rounded-md cursor-pointer hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={hardGates.fact_grounding}
                  onChange={(e) =>
                    setHardGates({ ...hardGates, fact_grounding: e.target.checked })
                  }
                  className="rounded text-slate-900 focus:ring-0"
                />
                <span className="text-slate-700">RERA Fact Grounding</span>
              </label>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 sm:p-6 border-t border-border bg-surface flex items-center justify-between gap-3 sticky bottom-0 z-10">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-md border border-border text-xs font-mono font-medium text-slate-700 hover:bg-slate-100 transition-colors"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleSaveAndRun}
            disabled={isSaving}
            className="inline-flex items-center gap-2 bg-ink-primary hover:bg-slate-800 text-white text-xs font-semibold px-5 py-2.5 rounded-md transition-colors disabled:opacity-50 shadow-sm"
          >
            {isSaving ? (
              <RotateCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Zap className="w-3.5 h-3.5 text-amber-400" />
            )}
            <span>Save &amp; Run This Scenario Now</span>
          </button>
        </div>
      </div>
    </div>
  );
}
