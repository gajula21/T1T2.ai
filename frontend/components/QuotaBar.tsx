"use client";

import { QuotaStatus } from "@/lib/api";
import clsx from "clsx";

interface QuotaBarProps {
  quota: QuotaStatus;
  compact?: boolean;
}

export function QuotaBar({ quota, compact = false }: QuotaBarProps) {
  const { limit, used, remaining } = quota;

  const isAmber = remaining === 1;
  const isRed = remaining === 0;

  if (compact) {
    return (
      <div className="flex items-center gap-2" title={`${remaining} / ${limit} evaluations left today`}>
        <div className="flex items-center gap-1">
          {Array.from({ length: limit }).map((_, i) => (
            <div
              key={i}
              className={clsx(
                "quota-pip",
                i < used
                  ? isRed
                    ? "bg-red-500"
                    : isAmber
                    ? "bg-amber-400"
                    : "bg-brand-400"
                  : "bg-gray-200"
              )}
            />
          ))}
        </div>
        <span
          className={clsx(
            "text-xs font-medium",
            isRed ? "text-red-600" : isAmber ? "text-amber-600" : "text-gray-500"
          )}
        >
          {remaining}/{limit}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-600">Daily evaluations</span>
        <span
          className={clsx(
            "text-sm font-semibold",
            isRed ? "text-red-600" : isAmber ? "text-amber-600" : "text-gray-900"
          )}
        >
          {remaining} / {limit} left
        </span>
      </div>

      <div className="flex items-center gap-1.5">
        {Array.from({ length: limit }).map((_, i) => (
          <div
            key={i}
            className={clsx(
              "flex-1 h-2 rounded-full transition-all duration-300",
              i < used
                ? isRed
                  ? "bg-red-500"
                  : isAmber
                  ? "bg-amber-400"
                  : "bg-brand-500"
                : "bg-gray-100"
            )}
          />
        ))}
      </div>

      {isRed && (
        <p className="text-xs text-red-600">
          Limit reached. Resets at midnight IST.
        </p>
      )}
      {isAmber && !isRed && (
        <p className="text-xs text-amber-600">1 evaluation remaining today.</p>
      )}
    </div>
  );
}
