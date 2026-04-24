"use client";

import { EvaluationListItem } from "@/lib/api";
import Link from "next/link";

interface HistoryTableProps {
  evaluations: EvaluationListItem[];
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
  onDownloadPdf: (id: number) => void;
}

function formatDateDisplay(dateStr: string) {
  const d = new Date(dateStr);
  const now = new Date();
  const time = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  
  const isToday = d.toDateString() === now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = d.toDateString() === yesterday.toDateString();

  if (isToday) {
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.round(diffMs / 60000);
    if (diffMins < 60) return `Today · ${diffMins} min ago`;
    const diffHrs = Math.round(diffMins / 60);
    return `Today · ${diffHrs} hr ago`;
  }
  
  if (isYesterday) return `Yesterday · ${time}`;
  return `${d.toLocaleDateString("en-US", { month: "short", day: "numeric" })} · ${time}`;
}

export function HistoryTable({ evaluations, hasMore, loadingMore, onLoadMore, onDownloadPdf }: HistoryTableProps) {
  if (evaluations.length === 0) {
    return <div className="text-center py-10 text-[#A3A3A3] text-sm">No evaluations found.</div>;
  }

  return (
    <div className="w-full flex flex-col gap-2">
      {evaluations.map((evalItem) => {
        const isTask1 = evalItem.task_type === "task1";
        const band = evalItem.overall_band !== null && evalItem.overall_band !== undefined
          ? (typeof evalItem.overall_band === "string" ? parseFloat(evalItem.overall_band) : evalItem.overall_band)
          : null;
        const displayBand = band !== null && !isNaN(band) && band > 0 ? band.toFixed(1) : "—";
        const title = evalItem.essay_excerpt
          ? evalItem.essay_excerpt.slice(0, 60) + (evalItem.essay_excerpt.length > 60 ? "…" : "")
          : (isTask1 ? "Task 1 Response" : "Task 2 Essay");

        return (
          <div
            key={evalItem.id}
            className="flex items-center justify-between p-4 group transition-colors border-b border-[#FFFFFF]/5 last:border-0 hover:bg-[#383838]"
          >
            <div className="flex items-center gap-4 flex-1 min-w-0">
               {/* Badge */}
               <span className={`text-[10px] font-bold text-white px-2 py-0.5 rounded-full flex-shrink-0 ${isTask1 ? 'bg-[#2563EB]' : 'bg-[#16A34A]'}`}>
                 {isTask1 ? 'Task 1' : 'Task 2'}
               </span>
               <div className="flex flex-col min-w-0">
                 <span className="text-sm font-medium text-white truncate">{title}</span>
                 <span className="text-[11px] text-[#A3A3A3]">{formatDateDisplay(evalItem.created_at)} · {evalItem.word_count} words</span>
               </div>
            </div>

            <div className="flex items-center gap-6 flex-shrink-0">
              <span className="text-lg font-medium text-white">{displayBand}</span>
              <div className="flex items-center gap-2">
                <Link href={`/result/${evalItem.id}`} className="btn-outline px-3 py-1 text-xs">View</Link>
                <button onClick={() => onDownloadPdf(evalItem.id)} className="btn-outline px-3 py-1 text-xs">PDF</button>
              </div>
            </div>
          </div>
        );
      })}

      {hasMore && (
        <button 
          onClick={onLoadMore}
          disabled={loadingMore}
          className="mt-4 text-[#A3A3A3] text-sm hover:text-white transition-colors"
        >
          {loadingMore ? "Loading..." : "Load older evaluations"}
        </button>
      )}
    </div>
  );
}
