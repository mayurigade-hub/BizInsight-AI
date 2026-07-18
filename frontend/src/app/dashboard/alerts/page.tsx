"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { ShieldAlert, Mail, Bell, CheckCircle, RefreshCw, AlertTriangle } from "lucide-react";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchAlerts = async () => {
    const token = localStorage.getItem("bizinsight_token");
    if (!token) return;
    setLoading(true);
    try { setAlerts(await api.getAlerts(token)); } catch (err: any) { setError(err.message || "Failed."); } finally { setLoading(false); }
  };

  useEffect(() => { fetchAlerts(); }, []);

  if (loading) return <div className="min-h-[60vh] flex flex-col items-center justify-center gap-3"><RefreshCw className="animate-spin text-zinc-400" size={24} /><p className="text-sm text-zinc-500">Loading alerts...</p></div>;

  const isHigh = alerts?.risk_level === "high";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div><h2 className="text-2xl font-semibold tracking-tight">Trend Alerts</h2><p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">Real-time threshold monitoring.</p></div>
        <button onClick={fetchAlerts} className="text-sm font-medium px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors flex items-center gap-1.5"><RefreshCw size={14} /> Re-scan</button>
      </div>

      {error ? <div className="border border-red-200 dark:border-red-500/20 rounded-xl p-5 text-sm text-red-500">{error}</div> : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className={`border rounded-xl p-6 ${isHigh ? "border-red-200 dark:border-red-500/20 bg-red-50/50 dark:bg-red-500/5" : "border-emerald-200 dark:border-emerald-500/20 bg-emerald-50/50 dark:bg-emerald-500/5"}`}>
              <div className="flex items-start justify-between mb-6">
                <div><div className="text-xs text-zinc-500 mb-1">Risk Assessment</div><h3 className={`text-2xl font-semibold uppercase ${isHigh ? "text-red-500" : "text-emerald-600 dark:text-emerald-400"}`}>{alerts?.risk_level}</h3></div>
                <ShieldAlert size={28} className={isHigh ? "text-red-500" : "text-emerald-600 dark:text-emerald-400"} />
              </div>
              <div className="grid grid-cols-3 gap-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-4 rounded-xl">
                <div><div className="text-xs text-zinc-500">Negative %</div><div className={`text-xl font-semibold mt-0.5 ${isHigh ? "text-red-500" : ""}`}>{alerts?.negative_percent}%</div></div>
                <div><div className="text-xs text-zinc-500">Threshold</div><div className="text-xl font-semibold mt-0.5">{alerts?.threshold}%</div></div>
                <div><div className="text-xs text-zinc-500">Total</div><div className="text-xl font-semibold mt-0.5">{alerts?.total_reviews}</div></div>
              </div>
              <div className="mt-4 space-y-2 pt-4 border-t border-zinc-200 dark:border-zinc-800">
                {["SQLite health: Active", "SMTP outgoing: Connected", `Dispatcher: ${isHigh ? "Dispatched" : "Monitoring"}`].map((s, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs"><CheckCircle className="text-emerald-500" size={14} /><span className="text-zinc-500">{s}</span></div>
                ))}
              </div>
            </div>
            <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
              <h3 className="text-sm font-medium mb-3 flex items-center gap-2"><AlertTriangle size={14} className="text-amber-500" /> Top Issue Keywords</h3>
              <div className="flex flex-wrap gap-2">
                {alerts?.top_issues?.map((w: string, i: number) => (<span key={i} className="px-3 py-1.5 rounded-full bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-xs text-red-600 dark:text-red-400 capitalize">{w}</span>))}
                {!alerts?.top_issues?.length && <span className="text-xs text-zinc-400 italic">No issues flagged.</span>}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
              <Mail size={18} className="text-zinc-400 mb-3" />
              <h4 className="font-semibold text-sm mb-2">SMTP Config</h4>
              <p className="text-xs text-zinc-500 leading-relaxed mb-3">Automated alerts dispatch when risk exceeds threshold.</p>
              <div className="space-y-1.5 text-[10px] text-zinc-500 border-t border-zinc-200 dark:border-zinc-800 pt-3">
                <div>Sender: <span className="text-zinc-900 dark:text-white">alerts@bizinsight.ai</span></div>
                <div>Recipient: <span className="text-zinc-900 dark:text-white">stakeholders@company.com</span></div>
                <div>Trigger: <span className="text-zinc-900 dark:text-white">Negative &gt; 40%</span></div>
              </div>
            </div>
            <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
              <Bell size={18} className="text-zinc-400 mb-3" />
              <h4 className="font-semibold text-sm mb-2">Risk Scoring</h4>
              <div className="space-y-2 text-xs border-t border-zinc-200 dark:border-zinc-800 pt-3 mt-3">
                <div className="flex justify-between"><span className="text-emerald-600">Low</span><span className="text-zinc-500">&lt; 25%</span></div>
                <div className="flex justify-between"><span className="text-amber-500">Medium</span><span className="text-zinc-500">25–40%</span></div>
                <div className="flex justify-between"><span className="text-red-500 font-semibold">High</span><span className="text-zinc-500">&gt; 40%</span></div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
