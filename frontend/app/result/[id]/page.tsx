"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Evaluation, api, pollEvaluation } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const BAR_COLORS: Record<string, string> = {
  blue:   "#3B82F6",
  green:  "#22C55E",
  yellow: "#EAB308",
  purple: "#A855F7",
};

function safeScore(val: unknown): number | null {
  if (val === null || val === undefined) return null;
  const n = typeof val === "string" ? parseFloat(val) : Number(val);
  return isNaN(n) || n === 0 ? null : n;
}

function ScoreBar({ label, score, color }: { label: string; score: number | null; color: string }) {
  const pct = score !== null ? Math.min((score / 9) * 100, 100) : 0;
  const display = score !== null ? score.toFixed(1) : "—";
  return (
    <div className="card-container p-4 flex flex-col gap-3">
      <div className="flex justify-between items-center">
        <span className="text-xs text-[#A3A3A3]">{label}</span>
        <span className="text-lg font-semibold text-white">{display}</span>
      </div>
      <div className="h-1 bg-[#404040] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function ResultPage() {
  const { user, getToken } = useAuth();
  const params = useParams();
  const router = useRouter();
  const id = Number(params?.id);

  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user || !id) return;
    (async () => {
      const token = await getToken();
      if (!token) return;
      const { data, error: fetchErr } = await api.getEvaluation(id, token);
      if (fetchErr || !data) { setError(fetchErr ?? "Evaluation not found."); setLoading(false); return; }
      setEvaluation(data);
      setLoading(false);
      if (data.status !== "completed" && data.status !== "failed") {
        await pollEvaluation(id, token, (ev) => setEvaluation(ev));
      }
    })();
  }, [user, id, getToken]);

  if (!user || loading) return null;
  if (error) return <div className="p-8 text-red-500">{error}</div>;
  if (!evaluation) return null;

  const handleDownloadPdf = async () => {
    const token = await getToken();
    if (!token) return;
    const blob = await api.exportPdf(evaluation.id, token);
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `t1t2-evaluation-${evaluation.id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formattedDate = new Date(evaluation.created_at).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });

  const overallBand = safeScore(evaluation.overall_band);

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-8 flex flex-col h-[calc(100vh-65px)]">
      {/* Top bar */}
      <div className="flex items-center gap-4 mb-6 flex-shrink-0">
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-1.5 text-[#A3A3A3] hover:text-white transition-colors text-sm"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Dashboard
        </button>
        <span className="text-[#404040]">|</span>
        <span
          className={`text-white text-[10px] font-bold px-2 py-0.5 rounded-full ${
            evaluation.task_type === "task1" ? "bg-[#2563EB]" : "bg-[#16A34A]"
          }`}
        >
          {evaluation.task_type === "task1" ? "Task 1" : "Task 2"}
        </span>
        <span className="text-[#A3A3A3] text-sm">{formattedDate}</span>
      </div>

      {/* Main 2-column grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 flex-1 min-h-0">

        {/* LEFT: Essay + Question (read-only) */}
        <div className="flex flex-col min-h-0 gap-4 overflow-y-auto">
          {evaluation.task_question && (
            <div>
              <h3 className="section-label mb-2">TASK QUESTION</h3>
              <div className="card-container p-4">
                <p className="text-sm text-[#D4D4D4] leading-relaxed whitespace-pre-wrap">
                  {evaluation.task_question}
                </p>
              </div>
            </div>
          )}

          <div className="flex-1 min-h-0 flex flex-col">
            <h3 className="section-label mb-2">ESSAY RESPONSE</h3>
            <div className="flex-1 card-container p-4 overflow-y-auto">
              <p className="text-sm text-[#D4D4D4] leading-relaxed whitespace-pre-wrap">
                {evaluation.essay_text || "No essay text available."}
              </p>
              <div className="mt-3 pt-3 border-t border-white/10 flex items-center justify-between">
                <span className="text-xs text-[#737373]">{evaluation.word_count} words</span>
                <span className="text-xs text-[#737373]">{evaluation.task_type === "task1" ? "Task 1 Academic" : "Task 2 Essay"}</span>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT: Scores + Feedback */}
        <div className="flex flex-col min-h-0 overflow-y-auto space-y-4 pr-1">

          {/* Overall band hero */}
          <div className="card-container p-5 flex items-center justify-between flex-shrink-0">
            <div>
              <div className="text-5xl font-medium text-white leading-none tracking-tight mb-1">
                {evaluation.status === "failed"
                  ? "Error"
                  : overallBand !== null
                  ? overallBand.toFixed(1)
                  : "—"}
              </div>
              <p className="text-xs text-[#A3A3A3]">
                {evaluation.status === "failed"
                  ? "Evaluation failed"
                  : `Overall band score · ${evaluation.task_type === "task1" ? "Task 1" : "Task 2"} · ${formattedDate}`}
              </p>
            </div>
            <div className="flex flex-col gap-2 items-end">
              <button
                className="btn-outline text-xs px-3 py-1.5"
                onClick={handleDownloadPdf}
                disabled={evaluation.status === "failed"}
              >
                Download PDF
              </button>
              <button
                className="btn-outline text-xs px-3 py-1.5"
                onClick={() => router.push(`/evaluate/${evaluation.task_type}`)}
              >
                Evaluate again
              </button>
            </div>
          </div>

          {evaluation.status === "failed" ? (
            <div className="card-container p-5 border-red-500/30 bg-red-500/5">
              <h2 className="text-red-400 font-semibold mb-2 text-sm">Evaluation Failed</h2>
              <p className="text-[#A3A3A3] text-xs mb-3">
                The AI was unable to complete this evaluation. Please try again.
              </p>
              {evaluation.error_message && (
                <div className="p-3 bg-black/40 rounded border border-neutral-800 font-mono text-xs text-red-500 overflow-x-auto whitespace-pre-wrap">
                  {evaluation.error_message}
                </div>
              )}
            </div>
          ) : (
            <>
              {/* Sub-scores */}
              <ScoreBar label="Task Achievement" score={safeScore(evaluation.scores?.task_response)} color={BAR_COLORS.blue} />
              <ScoreBar label="Coherence & Cohesion" score={safeScore(evaluation.scores?.coherence)} color={BAR_COLORS.green} />
              <ScoreBar label="Lexical Resource" score={safeScore(evaluation.scores?.lexical)} color={BAR_COLORS.yellow} />
              <ScoreBar label="Grammatical Range & Accuracy" score={safeScore(evaluation.scores?.grammar)} color={BAR_COLORS.purple} />

              {/* Feedback — all 4 criterion sections */}
              {evaluation.feedback && (
                <div className="card-container p-5 space-y-5">
                  {evaluation.feedback.task_response && (
                    <div>
                      <h3 className="section-label mb-2">{evaluation.task_type === "task1" ? "TASK ACHIEVEMENT" : "TASK RESPONSE"} — FEEDBACK</h3>
                      <p className="text-sm text-[#D4D4D4] leading-relaxed">{evaluation.feedback.task_response}</p>
                    </div>
                  )}
                  {evaluation.feedback.coherence && (
                    <div>
                      <h3 className="section-label mb-2">COHERENCE & COHESION — FEEDBACK</h3>
                      <p className="text-sm text-[#D4D4D4] leading-relaxed">{evaluation.feedback.coherence}</p>
                    </div>
                  )}
                  {evaluation.feedback.lexical && (
                    <div>
                      <h3 className="section-label mb-2">LEXICAL RESOURCE — FEEDBACK</h3>
                      <p className="text-sm text-[#D4D4D4] leading-relaxed">{evaluation.feedback.lexical}</p>
                    </div>
                  )}
                  {evaluation.feedback.grammar && (
                    <div>
                      <h3 className="section-label mb-2">GRAMMATICAL RANGE & ACCURACY — FEEDBACK</h3>
                      <p className="text-sm text-[#D4D4D4] leading-relaxed">{evaluation.feedback.grammar}</p>
                    </div>
                  )}
                  {evaluation.feedback.improvements && evaluation.feedback.improvements.length > 0 && (
                    <div>
                      <h3 className="section-label mb-2">TOP IMPROVEMENTS</h3>
                      <div className="flex flex-wrap gap-2">
                        {evaluation.feedback.improvements.map((tip, i) => (
                          <span
                            key={i}
                            className="px-3 py-1.5 text-xs text-[#FFFFFF] border border-[#FFFFFF]/10 rounded-full hover:bg-white/5 transition-colors"
                          >
                            {tip}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
