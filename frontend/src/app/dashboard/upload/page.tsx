"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api-client";
import { Upload, FileText, CheckCircle, AlertCircle, ArrowRight, ChevronLeft, ChevronRight, RefreshCw, Trash2 } from "lucide-react";
import Link from "next/link";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [clearing, setClearing] = useState(false);
  const [reviews, setReviews] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loadingReviews, setLoadingReviews] = useState(false);

  const fetchReviews = async () => {
    const token = localStorage.getItem("bizinsight_token");
    if (!token) return;
    setLoadingReviews(true);
    try { const res = await api.getReviews(token, page, 8); setReviews(res.reviews); setTotal(res.total); } catch {} finally { setLoadingReviews(false); }
  };

  useEffect(() => { fetchReviews(); }, [page]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true); setError(""); setResult(null);
    const token = localStorage.getItem("bizinsight_token");
    if (!token) return;
    try { const res = await api.uploadReviews(token, file); setResult(res); setFile(null); setPage(1); fetchReviews(); } catch (err: any) { setError(err.message || "Upload failed."); } finally { setUploading(false); }
  };

  const handleClear = async () => {
    if (!confirm("Clear all reviews? This is permanent.")) return;
    setClearing(true);
    const token = localStorage.getItem("bizinsight_token");
    if (!token) return;
    try { await api.clearReviews(token); setReviews([]); setTotal(0); setPage(1); setResult(null); } catch (err: any) { setError(err.message || "Failed."); } finally { setClearing(false); }
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold tracking-tight">Data Upload</h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">Upload reviews as CSV. Requires a column named <code className="font-mono bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded text-xs">review</code>.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload */}
        <div className="space-y-4">
          <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl p-6">
            <form onSubmit={handleUpload} className="space-y-4">
              <div className="border-2 border-dashed border-zinc-200 dark:border-zinc-700 rounded-xl p-10 flex flex-col items-center justify-center">
                <input type="file" id="csv-input" className="hidden" accept=".csv" onChange={e => { if (e.target.files?.[0]) { setFile(e.target.files[0]); setError(""); setResult(null); } }} />
                {file ? (
                  <div className="text-center"><p className="text-sm font-semibold">{file.name}</p><p className="text-xs text-zinc-500 mt-1">{(file.size / 1024).toFixed(1)} KB</p></div>
                ) : (
                  <label htmlFor="csv-input" className="cursor-pointer text-center"><Upload size={20} className="mx-auto mb-3 text-zinc-400" /><p className="text-sm font-medium">Drop CSV here or <span className="text-zinc-900 dark:text-white underline">browse</span></p><p className="text-xs text-zinc-400 mt-1">CSV format only</p></label>
                )}
              </div>
              {error && <div className="p-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-xs text-red-600 dark:text-red-400 flex items-start gap-2"><AlertCircle size={14} className="mt-0.5 shrink-0" />{error}</div>}
              {file && (
                <div className="flex gap-2">
                  <button type="submit" disabled={uploading} className="flex-1 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-lg py-2.5 text-sm font-medium hover:opacity-90 disabled:opacity-50">{uploading ? "Processing..." : "Upload & Analyze"}</button>
                  <button type="button" onClick={() => setFile(null)} disabled={uploading} className="px-4 py-2.5 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm hover:bg-zinc-50 dark:hover:bg-zinc-800">Clear</button>
                </div>
              )}
            </form>
          </div>

          {result && (
            <div className="border border-emerald-200 dark:border-emerald-500/20 rounded-xl p-5 bg-emerald-50/50 dark:bg-emerald-500/5">
              <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 mb-3"><CheckCircle size={16} /><h3 className="font-semibold text-sm">Upload Complete</h3></div>
              <div className="grid grid-cols-4 gap-3 text-center text-xs mb-4">
                <div><div className="text-zinc-500">Processed</div><div className="text-lg font-semibold mt-0.5">{result.total_processed}</div></div>
                <div><div className="text-zinc-500">Positive</div><div className="text-lg font-semibold text-emerald-600 mt-0.5">{result.positive}</div></div>
                <div><div className="text-zinc-500">Negative</div><div className="text-lg font-semibold text-red-500 mt-0.5">{result.negative}</div></div>
                <div><div className="text-zinc-500">Risk</div><div className={`text-lg font-semibold mt-0.5 ${result.alert_triggered ? "text-red-500" : ""}`}>{result.negative_percent}%</div></div>
              </div>
              {result.alert_triggered && <div className="p-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-xs text-red-600 dark:text-red-400 mb-3">⚠️ Spike Alert: Negative ratio exceeds 40% threshold.</div>}
              <Link href="/dashboard" className="block w-full text-center bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-lg py-2.5 text-sm font-medium hover:opacity-90">View Dashboard →</Link>
            </div>
          )}
        </div>

        {/* Database */}
        <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-sm">Reviews Database</h3>
            <span className="text-xs text-zinc-500">{total} items</span>
          </div>
          {loadingReviews ? (
            <div className="h-64 flex items-center justify-center"><RefreshCw className="animate-spin text-zinc-400" size={20} /></div>
          ) : reviews.length > 0 ? (
            <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {reviews.map((r, i) => (
                <div key={i} className="py-3">
                  <p className="text-xs leading-relaxed line-clamp-2 italic">&ldquo;{r.review}&rdquo;</p>
                  <div className="flex justify-between text-[10px] mt-1.5">
                    <span className={r.sentiment > 0 ? "text-emerald-600" : r.sentiment < 0 ? "text-red-500" : "text-zinc-400"}>VADER: {r.sentiment > 0 ? "+" : ""}{r.sentiment.toFixed(2)}</span>
                    <span className="text-zinc-400">{r.date?.split(" ")[0]}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-zinc-400 gap-2"><FileText size={24} /><span className="text-xs">Database empty. Upload a CSV above.</span></div>
          )}
          {total > 8 && (
            <div className="flex items-center justify-between pt-3 border-t border-zinc-100 dark:border-zinc-800 mt-3">
              <div className="flex gap-1">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="p-1.5 rounded border border-zinc-200 dark:border-zinc-700 disabled:opacity-30"><ChevronLeft size={14} /></button>
                <button onClick={() => setPage(p => p + 1)} disabled={page * 8 >= total} className="p-1.5 rounded border border-zinc-200 dark:border-zinc-700 disabled:opacity-30"><ChevronRight size={14} /></button>
              </div>
              <span className="text-xs text-zinc-500">Page {page} of {Math.ceil(total / 8)}</span>
            </div>
          )}
          {reviews.length > 0 && (
            <div className="mt-3 pt-3 border-t border-zinc-100 dark:border-zinc-800 flex justify-end">
              <button onClick={handleClear} disabled={clearing} className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-lg border border-red-200 dark:border-red-500/20 text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10"><Trash2 size={13} /> Clear Database</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
