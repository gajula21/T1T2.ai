"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/lib/auth";
import { api, pollEvaluation, Evaluation } from "@/lib/api";
import { ImageUploader } from "@/components/ImageUploader";
import { EssayEditor } from "@/components/EssayEditor";



const BAR_COLORS: Record<string, string> = {
  blue:   "#3B82F6",
  green:  "#22C55E",
  yellow: "#EAB308",
  purple: "#A855F7",
};

function safeScore(val: unknown): number | null {
  if (val === null || val === undefined) return null;
  const n = typeof val === "string" ? parseFloat(val) : Number(val);
  return isNaN(n) ? null : n;
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

function FeedbackSection({ title, text }: { title: string; text: string }) {
  if (!text) return null;
  return (
    <div>
      <h3 className="section-label mb-2">{title}</h3>
      <p className="text-sm text-[#D4D4D4] leading-relaxed">{text}</p>
    </div>
  );
}

export default function Task1Page() {
  const { user, getToken } = useRequireAuth();
  const router = useRouter();

  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [essay, setEssay] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [quota, setQuota] = useState<{ remaining: number; limit: number } | null>(null);
  const [result, setResult] = useState<Evaluation | null>(null);
  const [showResult, setShowResult] = useState(false);

  useEffect(() => {
    if (user) {
      getToken().then((token) => {
        if (token) {
          api.getQuota(token).then((res) => {
            if (res.data) setQuota(res.data);
            else if (res.quota) setQuota(res.quota);
          });
        }
      });
    }
  }, [user, getToken]);

  const handleFileSelect = (file: File) => {
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const handleClear = () => {
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImageFile(null);
    setImagePreview(null);
  };


  const handleSubmit = async () => {
    setError(null);
    setResult(null);
    setShowResult(false);
    const wordCount = essay.trim().split(/\s+/).filter(Boolean).length;
    if (wordCount < 50) { setError("Essay must be at least 50 words."); return; }

    const token = await getToken();
    if (!token) return;

    setSubmitting(true);
    const formData = new FormData();
    formData.append("essay_text", essay);
    if (imageFile) formData.append("image", imageFile);

    const { data, error: submitErr } = await api.submitTask1(formData, token);
    if (submitErr || !data) {
      setError(submitErr ?? "Submission failed. Please check your connection and try again.");
      setSubmitting(false);
      return;
    }

    const evalResult = await pollEvaluation(data.id, token, (ev) => setResult(ev));
    setSubmitting(false);
    if (evalResult) {
      setResult(evalResult);
      setShowResult(true);
    } else {
      setError("Evaluation timed out. The server may be busy — please try again in a moment.");
    }
  };

  const handleReset = () => {
    setResult(null);
    setShowResult(false);
    setError(null);
  };

  const handleDownloadPdf = async () => {
    if (!result) return;
    const token = await getToken();
    if (!token) return;
    const blob = await api.exportPdf(result.id, token);
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `t1t2-evaluation-${result.id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const isEvaluateDisabled =
    submitting ||
    essay.trim().split(/\s+/).filter(Boolean).length < 50 ||
    (quota !== null && quota.remaining === 0);

  if (!user) return null;

  const overallBand = result ? safeScore(result.overall_band) : null;
  const formattedDate = result
    ? new Date(result.created_at).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "";

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
        <span className="bg-[#2563EB] text-white text-[10px] font-bold px-2 py-0.5 rounded-full">Task 1</span>
        <span className="text-[#A3A3A3] text-sm">Academic writing</span>

        {showResult && (
          <button
            onClick={handleReset}
            className="ml-auto flex items-center gap-1.5 text-[#A3A3A3] hover:text-white transition-colors text-sm border border-[#404040] rounded-lg px-3 py-1.5"
          >
            ← Evaluate again
          </button>
        )}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 flex-1 min-h-0">

        {/* LEFT: Chart uploader + Essay (frozen when result is shown) */}
        <div className="flex flex-col min-h-0 gap-4 overflow-y-auto">
          <ImageUploader
            onFileSelect={handleFileSelect}
            onClear={handleClear}
            previewUrl={imagePreview}
            disabled={submitting || showResult}
          />


          <div className="flex-1 min-h-0">
            <EssayEditor
              value={essay}
              onChange={setEssay}
              disabled={submitting || showResult}
              minWords={150}
            />
          </div>
        </div>

        {/* RIGHT: Result panel or empty state */}
        <div className="flex flex-col min-h-0">
          {!showResult && !submitting && (
            <div className="flex-1 flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-white/10 bg-[#1E1E1E] p-8 text-center transition-colors hover:border-white/20">
              <div className="w-16 h-16 mb-5 rounded-2xl bg-white/5 flex items-center justify-center shadow-inner">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-[#3B82F6]">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                </svg>
              </div>
              <h3 className="text-[15px] font-semibold text-white tracking-tight mb-2">Evaluation results will appear here</h3>
              <p className="text-[13px] text-[#A3A3A3] max-w-[260px] leading-relaxed">
                Upload your chart and write a detailed response on the left, then click Evaluate to get your band score.
              </p>
            </div>
          )}

          {submitting && (
            <div className="flex-1 flex flex-col items-center justify-center card-container">
              <div className="text-center space-y-4">
                <div className="relative w-16 h-16 mx-auto">
                  <div className="absolute inset-0 rounded-full border-4 border-[#333] animate-pulse" />
                  <div className="absolute inset-0 rounded-full border-4 border-t-[#2563EB] animate-spin" />
                </div>
                <p className="text-white text-sm font-medium">Evaluating your essay…</p>
                <p className="text-[#737373] text-xs">This may take 15–30 seconds</p>
              </div>
            </div>
          )}

          {showResult && result && (
            <div className="flex-1 overflow-y-auto space-y-5 pr-1">
              {/* Overall band hero */}
              <div className="card-container p-5 flex items-center justify-between">
                <div>
                  <div className="text-5xl font-medium text-white leading-none tracking-tight mb-1">
                    {result.status === "failed"
                      ? "Error"
                      : overallBand !== null
                      ? overallBand.toFixed(1)
                      : "—"}
                  </div>
                  <p className="text-xs text-[#A3A3A3]">
                    {result.status === "failed"
                      ? "Evaluation failed"
                      : `Overall band score · Task 1 · ${formattedDate}`}
                  </p>
                </div>
                <button
                  className="btn-outline text-xs px-3 py-1.5"
                  onClick={handleDownloadPdf}
                  disabled={result.status === "failed"}
                >
                  Download PDF
                </button>
              </div>

              {result.status === "failed" ? (
                <div className="card-container p-5 border-red-500/30 bg-red-500/5">
                  <h2 className="text-red-400 font-semibold mb-2 text-sm">Evaluation Failed</h2>
                  <p className="text-[#A3A3A3] text-xs mb-3">
                    The AI was unable to complete this evaluation. Please try again.
                  </p>
                  {result.error_message && (
                    <div className="p-3 bg-black/40 rounded border border-neutral-800 font-mono text-xs text-red-500 overflow-x-auto whitespace-pre-wrap">
                      {result.error_message}
                    </div>
                  )}
                </div>
              ) : (
                <>
                  {/* Sub-scores — all 4 criteria */}
                  <div className="grid grid-cols-1 gap-3">
                    <ScoreBar label="Task Achievement" score={safeScore(result.scores?.task_response)} color={BAR_COLORS.blue} />
                    <ScoreBar label="Coherence & Cohesion" score={safeScore(result.scores?.coherence)} color={BAR_COLORS.green} />
                    <ScoreBar label="Lexical Resource" score={safeScore(result.scores?.lexical)} color={BAR_COLORS.yellow} />
                    <ScoreBar label="Grammatical Range & Accuracy" score={safeScore(result.scores?.grammar)} color={BAR_COLORS.purple} />
                  </div>

                  {/* Feedback — all 4 criterion sections + improvements */}
                  {result.feedback && (
                    <div className="card-container p-5 space-y-5">
                      <FeedbackSection title="TASK ACHIEVEMENT — FEEDBACK" text={result.feedback.task_response} />
                      <FeedbackSection title="COHERENCE & COHESION — FEEDBACK" text={result.feedback.coherence} />
                      <FeedbackSection title="LEXICAL RESOURCE — FEEDBACK" text={result.feedback.lexical} />
                      <FeedbackSection title="GRAMMATICAL RANGE & ACCURACY — FEEDBACK" text={result.feedback.grammar} />
                      {result.feedback.improvements && result.feedback.improvements.length > 0 && (
                        <div>
                          <h3 className="section-label mb-2">TOP IMPROVEMENTS</h3>
                          <div className="flex flex-wrap gap-2">
                            {result.feedback.improvements.map((tip, i) => (
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
          )}
        </div>
      </div>

      {/* Footer actions */}
      {!showResult && (
        <div className="flex items-center justify-between border-t border-[#FFFFFF]/10 pt-5 mt-5 flex-shrink-0">
          <div>
            {quota && (
              <>
                <p className="text-xs text-[#A3A3A3] mb-1.5">
                  {quota.remaining} evaluations left today — resets midnight IST
                </p>
                <div className="flex gap-1.5 flex-wrap">
                  {Array.from({ length: quota.limit }).map((_, i) => (
                    <div
                      key={i}
                      className={`h-1.5 w-8 rounded-full ${
                        i < quota.limit - quota.remaining ? "bg-[#EAB308]" : "bg-[#262626]"
                      }`}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
          <div className="flex items-center gap-4">
            {error && <span className="text-red-400 text-sm">{error}</span>}
            <div className="relative group">
              <button
                className="btn-outline"
                onClick={handleSubmit}
                disabled={isEvaluateDisabled}
              >
                {submitting ? "Evaluating…" : "Evaluate essay"}
              </button>
              {quota !== null && quota.remaining === 0 && (
                <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 w-max px-2 py-1 bg-black text-xs text-red-500 rounded hidden group-hover:block border border-red-900 pointer-events-none">
                  Daily limit reached — resets midnight IST
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
