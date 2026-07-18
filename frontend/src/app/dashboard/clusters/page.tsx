"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api-client";
import { Layers, RefreshCw, ChevronDown, ChevronUp, AlertCircle, MessageSquare } from "lucide-react";

const ClusterRow = ({ cluster }: { cluster: any }) => {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 hover:shadow-lg transition-shadow">
      <div onClick={() => setExpanded(!expanded)} className="flex items-center justify-between cursor-pointer">
        <div><h4 className="font-medium text-sm capitalize">{cluster.name.replace(/^\d+_\s*/, "")}</h4><span className="text-[10px] text-zinc-500">ID: {cluster.id} · {cluster.count} comments</span></div>
        <div className="flex items-center gap-3">
          <div className="text-right"><span className="text-xs font-semibold">{cluster.percentage}%</span><div className="w-20 bg-zinc-100 dark:bg-zinc-800 h-1.5 rounded-full mt-1 overflow-hidden"><div className="bg-zinc-900 dark:bg-white h-full rounded-full" style={{ width: `${cluster.percentage}%` }} /></div></div>
          {expanded ? <ChevronUp size={14} className="text-zinc-400" /> : <ChevronDown size={14} className="text-zinc-400" />}
        </div>
      </div>
      {expanded && (
        <div className="border-t border-zinc-100 dark:border-zinc-800 pt-3 mt-3 space-y-2">
          <span className="text-[10px] text-zinc-500 uppercase flex items-center gap-1"><MessageSquare size={10} /> Sample reviews:</span>
          {cluster.example_reviews?.map((q: string, i: number) => (<div key={i} className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800 text-xs italic leading-relaxed">&ldquo;{q}&rdquo;</div>))}
        </div>
      )}
    </div>
  );
};

export default function ClustersPage() {
  const [mode, setMode] = useState<"negative" | "positive">("negative");
  const [job, setJob] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "failed") return;
    const id = setInterval(async () => {
      const token = localStorage.getItem("bizinsight_token");
      if (!token) return;
      try {
        const s = await api.getClusteringStatus(token, job.job_id);
        setJob(s);
        if (s.status === "completed") { setResult(await api.getClusteringResults(token, job.job_id)); setLoading(false); clearInterval(id); }
        else if (s.status === "failed") { setError(s.message || "Failed."); setLoading(false); clearInterval(id); }
      } catch (e: any) { setError(e.message); setLoading(false); clearInterval(id); }
    }, 2000);
    return () => clearInterval(id);
  }, [job]);

  const start = async () => {
    const token = localStorage.getItem("bizinsight_token");
    if (!token) return;
    setLoading(true); setError(""); setResult(null); setJob(null);
    try { setJob(await api.startClustering(token, mode)); } catch (e: any) { setError(e.message || "Failed."); setLoading(false); }
  };

  return (
    <div>
      <div className="mb-6"><h2 className="text-2xl font-semibold tracking-tight">Smart Clustering</h2><p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">Auto-group feedback using HDBSCAN + BERTopic.</p></div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-4">
          <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 space-y-4">
            <div><h3 className="font-semibold text-sm">Run Topic Modeling</h3><p className="text-xs text-zinc-500 mt-1 leading-relaxed">Vectorize feedback, reduce with UMAP, group with HDBSCAN.</p></div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-2">Sentiment subset</label>
              <div className="grid grid-cols-2 gap-1 p-1 rounded-lg bg-zinc-100 dark:bg-zinc-800">
                <button onClick={() => setMode("negative")} disabled={loading} className={`py-2 text-xs font-medium rounded-md transition ${mode === "negative" ? "bg-white dark:bg-zinc-700 shadow text-red-500" : "text-zinc-500"}`}>Negative</button>
                <button onClick={() => setMode("positive")} disabled={loading} className={`py-2 text-xs font-medium rounded-md transition ${mode === "positive" ? "bg-white dark:bg-zinc-700 shadow text-emerald-600" : "text-zinc-500"}`}>Positive</button>
              </div>
            </div>
            <button onClick={start} disabled={loading} className="w-full bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-lg py-2.5 text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2">
              {loading ? <><RefreshCw className="animate-spin" size={14} /> Running...</> : <><Layers size={14} /> Map Complaints</>}
            </button>
          </div>
          {job && (
            <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 space-y-2 text-xs">
              <div className="flex justify-between"><span className="text-zinc-500">Job ID</span><span className="font-mono">{job.job_id?.slice(0, 8)}...</span></div>
              <div className="flex justify-between"><span className="text-zinc-500">Status</span><span className={`px-2 py-0.5 rounded uppercase text-[10px] font-medium ${job.status === "completed" ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400" : job.status === "failed" ? "bg-red-50 text-red-500" : "bg-amber-50 text-amber-500 animate-pulse"}`}>{job.status}</span></div>
              <div className="p-2 bg-zinc-50 dark:bg-zinc-800 rounded-lg text-center text-zinc-500">{job.message}</div>
            </div>
          )}
          {error && <div className="p-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-xs text-red-500 flex items-start gap-2"><AlertCircle size={14} className="mt-0.5 shrink-0" />{error}</div>}
        </div>

        <div className="lg:col-span-2 space-y-4">
          {loading ? (
            <div className="min-h-[300px] flex flex-col items-center justify-center gap-3"><RefreshCw className="animate-spin text-zinc-400" size={28} /><div className="text-center"><h4 className="font-medium text-sm">Running ML Pipeline</h4><p className="text-xs text-zinc-500 mt-1">This may take up to a minute...</p></div></div>
          ) : result ? (
            <div className="space-y-4">
              <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 flex items-center justify-between">
                <div><div className="text-xs text-zinc-500">Results</div><h3 className="font-semibold">{result.n_clusters} clusters found</h3></div>
                <div className="text-right"><div className="text-xs text-zinc-500">Noise</div><div className="text-lg font-semibold text-amber-500">{result.noise_percentage}%</div></div>
              </div>
              {result.clusters?.map((c: any) => <ClusterRow key={c.id} cluster={c} />)}
              {!result.clusters?.length && <div className="py-12 text-center text-zinc-400">No clusters detected.</div>}
            </div>
          ) : (
            <div className="min-h-[300px] border-2 border-dashed border-zinc-200 dark:border-zinc-700 rounded-xl flex flex-col items-center justify-center text-center text-zinc-400 gap-2 p-8">
              <Layers size={28} /><h4 className="text-sm font-medium text-zinc-900 dark:text-white">No Active Session</h4><p className="text-xs max-w-xs">Run the clustering engine to identify topic groups.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
