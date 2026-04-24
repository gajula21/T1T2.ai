"use client";

import { EvaluationFeedback } from "@/lib/api";

interface FeedbackPanelProps {
  feedback: EvaluationFeedback;
  taskType: "task1" | "task2";
}

export function FeedbackPanel({ feedback, taskType }: FeedbackPanelProps) {
  return (
    <div className="space-y-12">
      {/* Lexical Resource Feedback text */}
      <div>
        <h3 className="section-label mb-3">LEXICAL RESOURCE — FEEDBACK</h3>
        <p className="text-sm text-[#FFFFFF] leading-relaxed">
          {feedback.lexical || "No feedback available."}
        </p>
      </div>
      
      {/* Top Improvements Tags */}
      <div>
        <h3 className="section-label mb-3">TOP IMPROVEMENTS</h3>
        <div className="flex flex-wrap gap-2">
          {feedback.improvements?.map((tip, i) => (
            <span 
              key={i} 
              className="px-3 py-1.5 text-xs text-[#FFFFFF] border border-[#FFFFFF]/10 rounded-full hover:bg-white/5 transition-colors"
            >
              {tip}
            </span>
          ))}
          {(!feedback.improvements || feedback.improvements.length === 0) && (
            <span className="text-xs text-[#A3A3A3]">No suggestions provided.</span>
          )}
        </div>
      </div>
    </div>
  );
}
