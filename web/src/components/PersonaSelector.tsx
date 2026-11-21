"use client";

import React from "react";
import { Users, CheckSquare, Square, MessageSquarePlus } from "lucide-react";

export interface PersonaItem {
  id: string;
  name: string;
  tag: string;
  message: string;
  description: string;
  expected_rule: string;
}

interface PersonaSelectorProps {
  personas: PersonaItem[];
  selectedIds: string[];
  onToggle: (id: string) => void;
  customMessage: string;
  setCustomMessage: (msg: string) => void;
}

export function PersonaSelector({
  personas,
  selectedIds,
  onToggle,
  customMessage,
  setCustomMessage,
}: PersonaSelectorProps) {
  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-ink-secondary" />
          <h2 className="text-sm font-semibold text-ink-primary">
            Select Indian Buyer Personas
          </h2>
          <span className="text-xs text-ink-muted hidden sm:inline">
            — Toggle callers to stress-test prompts against
          </span>
        </div>
        <span className="text-xs font-mono text-ink-secondary">
          {selectedIds.length}/{personas.length} Selected
        </span>
      </div>

      {/* 5 Persona Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
        {personas.map((persona) => {
          const isSelected = selectedIds.includes(persona.id);
          return (
            <button
              key={persona.id}
              type="button"
              onClick={() => onToggle(persona.id)}
              className={`text-left p-3 rounded-lg border transition-all flex flex-col justify-between ${
                isSelected
                  ? "bg-white border-ink-primary/30 shadow-xs ring-1 ring-ink-primary/10"
                  : "bg-slate-50/70 border-slate-200 opacity-60 hover:opacity-90"
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-1.5 mb-1.5">
                  <span className="text-xs font-semibold text-ink-primary leading-tight">
                    {persona.name}
                  </span>
                  {isSelected ? (
                    <CheckSquare className="w-3.5 h-3.5 text-accent-emerald shrink-0 mt-0.5" />
                  ) : (
                    <Square className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                  )}
                </div>
                <span className="inline-block text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200 mb-2">
                  {persona.tag}
                </span>
                <p className="text-[11px] text-ink-secondary italic leading-snug line-clamp-3">
                  &ldquo;{persona.message}&rdquo;
                </p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Optional Custom Buyer Message Input */}
      <div className="flex items-center gap-2 pt-1">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-slate-400">
            <MessageSquarePlus className="w-3.5 h-3.5" />
          </div>
          <input
            type="text"
            value={customMessage}
            onChange={(e) => setCustomMessage(e.target.value)}
            placeholder="+ Test a custom buyer message (e.g. 'Arey bhai 1.1 Cr mein final karo na, kal token de dunga')..."
            className="w-full pl-8 pr-3 py-1.5 text-xs text-ink-primary bg-white border border-border rounded-md placeholder:text-slate-400 focus:outline-hidden focus:ring-1 focus:ring-ink-primary"
          />
        </div>
      </div>
    </div>
  );
}
