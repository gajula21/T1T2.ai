"use client";

import { useCallback } from "react";

interface EssayEditorProps {
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  minWords?: number;
}

export function EssayEditor({
  value,
  onChange,
  disabled = false,
  minWords = 250,
}: EssayEditorProps) {
  const wordCount = value.trim() === "" ? 0 : value.trim().split(/\s+/).length;
  const charCount = value.length;
  const pct = Math.min((wordCount / minWords) * 100, 100);
  const isReady = wordCount >= minWords;

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
  };

  return (
    <div className="w-full h-full flex flex-col gap-2">
      {/* Label row */}
      <div className="flex items-center justify-between">
        <h3 className="section-label">YOUR ESSAY</h3>
        <div className="flex items-center gap-3">
          <span
            className={`text-[11px] font-semibold tabular-nums transition-colors ${
              isReady ? "text-[#22C55E]" : "text-[#A3A3A3]"
            }`}
          >
            {wordCount} / {minWords}+ words
          </span>
          <span className="text-[11px] text-[#525252] tabular-nums">
            {charCount} chars
          </span>
        </div>
      </div>

      {/* Editor card */}
      <div
        className={`flex-1 flex flex-col rounded-lg border transition-colors duration-200 ${
          disabled
            ? "bg-[#2A2A2A] border-white/5"
            : "bg-[#1E1E1E] border-white/10 focus-within:border-white/20"
        }`}
        style={{ minHeight: "320px" }}
      >
        <textarea
          className="flex-1 w-full bg-transparent resize-none text-[#E5E5E5] text-sm leading-7 p-5 outline-none placeholder:text-[#525252] font-sans"
          value={value}
          onChange={handleChange}
          placeholder={
            minWords === 150
              ? "Describe the chart/graph in your own words. Aim for at least 150 words..."
              : "Write your argumentative essay here. Aim for at least 250 words..."
          }
          disabled={disabled}
          spellCheck={false}
          style={{ minHeight: "280px" }}
        />

        {/* Bottom bar */}
        <div className="px-5 pb-4 pt-2 flex items-center gap-3 border-t border-white/5">
          {/* Progress bar */}
          <div className="flex-1 h-1 bg-[#2A2A2A] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${pct}%`,
                backgroundColor: isReady ? "#22C55E" : "#EAB308",
              }}
            />
          </div>
          <span
            className={`text-[10px] font-medium shrink-0 transition-colors ${
              isReady ? "text-[#22C55E]" : "text-[#EAB308]"
            }`}
          >
            {isReady ? "✓ Ready" : `${minWords - wordCount} words to go`}
          </span>
        </div>
      </div>
    </div>
  );
}
