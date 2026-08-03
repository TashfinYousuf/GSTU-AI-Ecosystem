"use client";

import { useEffect, useState } from "react";
import { Users, FileText, MessageSquare, Activity, ShieldCheck, Clock, TrendingUp } from "lucide-react";
import { createClient } from "../../utils/supabase/client";

export default function FacultyDashboard() {
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    const fetchStats = async () => {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      
      if (session?.access_token) {
        try {
          const res = await fetch("http://localhost:8000/api/v1/admin/stats", {
            headers: { "Authorization": `Bearer ${session.access_token}` }
          });
          if (res.ok) setStats(await res.json());
        } catch (error) {
          console.error("Failed to fetch admin stats", error);
        }
      }
    };
    fetchStats();
  }, []);

  if (!stats) return <div className="flex h-screen items-center justify-center bg-[#121212] text-white">Loading OS Telemetry...</div>;

  return (
    <div className="min-h-screen bg-[#121212] text-white p-8 md:p-12 lg:p-16 transition-all duration-300">
      
      {/* Header */}
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <ShieldCheck className="w-8 h-8 text-indigo-500" />
          Faculty & Chairman Control Center
        </h1>
        <p className="text-gray-400 mt-2">GSTU AI Operating System - Real-time Departmental Telemetry</p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
        <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-blue-500/10 rounded-full blur-2xl group-hover:bg-blue-500/20 transition-all"></div>
          <div className="flex items-center justify-between mb-4"><p className="text-gray-400 font-medium">Active Students</p><Users className="w-5 h-5 text-blue-400" /></div>
          <h2 className="text-4xl font-bold text-white">{stats.metrics.active_students}</h2>
        </div>

        <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-purple-500/10 rounded-full blur-2xl group-hover:bg-purple-500/20 transition-all"></div>
          <div className="flex items-center justify-between mb-4"><p className="text-gray-400 font-medium">Knowledge Base (PDFs)</p><FileText className="w-5 h-5 text-purple-400" /></div>
          <h2 className="text-4xl font-bold text-white">{stats.metrics.knowledge_base_files}</h2>
        </div>

        <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl group-hover:bg-emerald-500/20 transition-all"></div>
          <div className="flex items-center justify-between mb-4"><p className="text-gray-400 font-medium">AI Interactions</p><MessageSquare className="w-5 h-5 text-emerald-400" /></div>
          <h2 className="text-4xl font-bold text-white">{stats.metrics.total_ai_interactions}</h2>
        </div>

        <div className="bg-[#1e1e1e] border border-white/5 p-6 rounded-2xl relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-amber-500/10 rounded-full blur-2xl group-hover:bg-amber-500/20 transition-all"></div>
          <div className="flex items-center justify-between mb-4"><p className="text-gray-400 font-medium">System Health</p><Activity className="w-5 h-5 text-amber-400" /></div>
          <h2 className="text-2xl font-bold text-white mt-2">{stats.metrics.system_health}</h2>
        </div>
      </div>

      {/* Activity Log (Timeline) */}
      <div className="bg-[#1e1e1e] border border-white/5 rounded-2xl p-6">
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2"><TrendingUp className="w-5 h-5 text-indigo-400" /> Departmental AI Activity Log</h3>
        
        <div className="space-y-4">
          {stats.recent_activities.map((act: any) => (
            <div key={act.id} className="flex items-center justify-between p-4 bg-[#252525] rounded-xl border border-white/5 hover:border-white/10 transition-colors">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-[#121212] rounded-lg border border-white/5">
                  {act.module === "Academic Copilot" ? <ShieldCheck className="w-5 h-5 text-purple-400" /> : 
                   act.module === "Knowledge Base" ? <FileText className="w-5 h-5 text-blue-400" /> : 
                   <MessageSquare className="w-5 h-5 text-emerald-400" />}
                </div>
                <div>
                  <p className="text-white font-medium">{act.action}</p>
                  <p className="text-sm text-gray-500 mt-0.5">Module: {act.module}</p>
                </div>
              </div>
              
              <div className="text-right">
                <p className="text-sm text-gray-400 flex items-center gap-1 justify-end"><Clock className="w-3.5 h-3.5" /> {act.time}</p>
                <span className={`text-xs font-semibold px-2 py-1 rounded-full mt-2 inline-block ${act.status === 'Success' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                  {act.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}