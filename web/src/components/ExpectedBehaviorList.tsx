"use client";

import React from "react";
import { ShieldCheck, Plus, Check } from "lucide-react";

export interface ExpectedRuleItem {
  id: string;
  label: string;
  description: string;
  checked: boolean;
}

interface ExpectedBehaviorListProps {
  rules: ExpectedRuleItem[];
  onToggleRule: (id: string) => void;
  customRule: string;
  setCustomRule: (rule: string) => void;
  onAddCustomRule: () => void;
}

export function ExpectedBehaviorList({
  rules,
  onToggleRule,
  customRule,
  setCustomRule,
  onAddCustomRule,
}: ExpectedBehaviorListProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      onAddCustomRule();
    }
  };

  return (
    <div className="space-y-2 bg-surface border border-border rounded-lg p-3.5 shadow-xs">
      <div className="flex items-center gap-2">
        <ShieldCheck className="w-4 h-4 text-ink-secondary" />
        <h2 className="text-sm font-semibold text-ink-primary">
          Expected Behavior Rules
        </h2>
        <span className="text-xs text-ink-muted hidden sm:inline">
          — Hard non-compensatory gates enforced by Layer 1 & 2
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        {rules.map((rule) => (
          <label
            key={rule.id}
            className={`flex items-start gap-2.5 p-2 rounded-md border text-xs cursor-pointer transition-colors ${
              rule.checked
                ? "bg-emerald-50/40 border-emerald-200 text-ink-primary"
                : "bg-slate-50 border-slate-200 text-slate-500"
            }`}
          >
            <input
              type="checkbox"
              checked={rule.checked}
              onChange={() => onToggleRule(rule.id)}
              className="mt-0.5 rounded border-slate-300 text-accent-emerald focus:ring-accent-emerald"
            />
            <span className="leading-snug select-none">{rule.label}</span>
          </label>
        ))}
      </div>

      {/* Add custom rule input */}
      <div className="flex items-center gap-2 pt-1">
        <input
          type="text"
          value={customRule}
          onChange={(e) => setCustomRule(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="+ Add your own expected behavior (e.g. 'Always answer in polite Hinglish under 3 sentences')..."
          className="flex-1 px-3 py-1.5 text-xs text-ink-primary bg-white border border-border rounded-md placeholder:text-slate-400 focus:outline-hidden focus:ring-1 focus:ring-ink-primary"
        />
        <button
          type="button"
          onClick={onAddCustomRule}
          disabled={!customRule.trim()}
          className="px-3 py-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-ink-primary rounded-md disabled:opacity-40 transition-colors flex items-center gap-1 shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add Rule</span>
        </button>
      </div>
    </div>
  );
}
