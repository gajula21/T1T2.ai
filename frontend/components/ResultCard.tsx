"use client";

import React from "react";

interface ResultCardProps {
  label: string;
  score: number | null;
  barColor: "bg-bar-blue" | "bg-bar-green" | "bg-bar-yellow" | "bg-bar-purple";
}

export function ResultCard({ label, score, barColor }: ResultCardProps) {
  const numScore = typeof score === "string" ? parseFloat(score) : score;
  const displayScore = (numScore !== null && !isNaN(numScore as number)) ? (numScore as number).toFixed(1) : "—";
  const pct = (numScore !== null && !isNaN(numScore as number)) ? Math.min(((numScore as number) / 9) * 100, 100) : 0;

  return (
    <div className="card-container p-6 flex flex-col justify-between h-[120px]">
      <span className="text-xs text-[#FFFFFF]">{label}</span>
      <div className="flex flex-col gap-3">
        <span className="text-2xl font-medium text-white leading-none">
          {displayScore}
        </span>
        <div className="h-1 bg-[#525252] w-full rounded-full overflow-hidden">
          <div className={`h-full ${barColor} rounded-full`} style={{ width: `${pct}%` }} />
        </div>
      </div>
    </div>
  );
}
