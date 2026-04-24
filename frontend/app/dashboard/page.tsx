"use client";

import { useEffect, useState, useCallback } from "react";
import { HistoryTable } from "@/components/HistoryTable";
import { useRequireAuth } from "@/lib/auth";
import { api, EvaluationListItem } from "@/lib/api";

interface Stats {
  total_evaluations: number;
  average_band: number | null;
  best_band: number | null;
}

export default function DashboardPage() {
  const { user, getToken, loading } = useRequireAuth();
  
  const [evaluations, setEvaluations] = useState<EvaluationListItem[]>([]);
  const [stats, setStats]       = useState<Stats | null>(null);
  const [page, setPage]         = useState(1);
  const [totalCount, setTotal]  = useState(0);
  const [loadingData, setLoadingData]   = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const loadEvaluations = useCallback(
    async (pageNum: number, append = false) => {
      if (!user) return;
      const token = await getToken();
      if (!token) return;
      if (!append) setLoadingData(true); else setLoadingMore(true);
      
      const { data } = await api.listEvaluations(pageNum, token);
      if (data) {
        setEvaluations((prev) => append ? [...prev, ...data.results] : data.results);
        setStats(data.stats);
        setTotal(data.count);
        setPage(pageNum);
      }
      
      if (!append) setLoadingData(false); else setLoadingMore(false);
    },
    [user, getToken]
  );

  useEffect(() => {
    if (!loading && user) loadEvaluations(1);
  }, [loading, user, loadEvaluations]);

  const handleDownloadPdf = async (id: number) => {
    const token = await getToken();
    if (!token) return;
    const blob = await api.exportPdf(id, token);
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a   = document.createElement("a");
    a.href     = url;
    a.download = `t1t2-evaluation-${id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!user || loadingData) return null;

  return (
    <div className="max-w-[1000px] mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-white">Evaluation History</h1>
        <button className="btn-outline px-4 py-1.5 text-xs">Filter</button>
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="card-container p-4 flex flex-col justify-between h-24">
            <span className="text-xs text-[#A3A3A3]">Total evaluations</span>
            <span className="text-2xl font-medium">{stats.total_evaluations}</span>
          </div>
          <div className="card-container p-4 flex flex-col justify-between h-24">
            <span className="text-xs text-[#A3A3A3]">Average band</span>
            <span className="text-2xl font-medium">{stats.average_band?.toFixed(1) ?? "—"}</span>
          </div>
          <div className="card-container p-4 flex flex-col justify-between h-24">
            <span className="text-xs text-[#A3A3A3]">Best score</span>
            <span className="text-2xl font-medium">{stats.best_band?.toFixed(1) ?? "—"}</span>
          </div>
        </div>
      )}

      {/* History Table */}
      <HistoryTable
        evaluations={evaluations}
        hasMore={evaluations.length < totalCount}
        loadingMore={loadingMore}
        onLoadMore={() => loadEvaluations(page + 1, true)}
        onDownloadPdf={handleDownloadPdf}
      />
    </div>
  );
}
